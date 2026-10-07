"""Aggiornamento incrementale del database.

Esempi:
    python -m basket.update                                # tutti i campionati, tutte le giornate
    python -m basket.update --campionati ita2 --giornate 1-2
"""

import argparse
import logging
import sys

import requests

from . import config, db
from . import pbp as P
from .client import RateLimitedClient
from .scraper import (ParseError, boxscore_url, fetch_boxscore, fetch_pbp, fetch_player,
                      fetch_schedule)

log = logging.getLogger("basket.update")


def parse_giornate(spec: str | None) -> set[int] | None:
    """'1-2' -> {1, 2}; '1,3,5-7' -> {1, 3, 5, 6, 7}; None -> tutte."""
    if not spec:
        return None
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def _round_complete(conn, league: str, season: str, giornata: int) -> list[dict] | None:
    """Se la giornata è già tutta giocata e scaricata, restituisce le partite dal DB
    (così non si interroga di nuovo il sito)."""
    rows = conn.execute(
        "SELECT c.partita_id, c.stato, p.partita_id IS NOT NULL FROM calendario c "
        "LEFT JOIN partite p USING (partita_id) "
        "WHERE c.campionato_id = ? AND c.stagione = ? AND c.giornata = ?",
        (league, season, giornata),
    ).fetchall()
    if rows and all(stato == "finished" and done for _, stato, done in rows):
        return [{"partita_id": r[0]} for r in rows]
    return None


GIORNATE_MANCANTI_STOP = 4


def update_league(conn, client, league: str, season: str, giornate: set[int] | None,
                  with_pbp: bool = True) -> dict:
    stats = {"giornate": 0, "nuove": 0, "errori": []}
    db.upsert_campionato(conn, league, season, config.CAMPIONATI.get(league, league))
    conn.commit()
    already = db.downloaded_ids(conn)
    missing_in_a_row = 0
    last = max(giornate) if giornate else config.MAX_GIORNATE

    for giornata in range(1, last + 1):
        if giornate and giornata not in giornate:
            continue
        if _round_complete(conn, league, season, giornata):
            log.info("%s giornata %d: già completa, salto", league, giornata)
            stats["giornate"] += 1
            continue

        games = fetch_schedule(client, league, giornata, season)
        if not games:
            missing_in_a_row += 1
            log.info("%s giornata %d: non presente", league, giornata)
            # alcune stagioni hanno buchi nella numerazione delle giornate (soste, turni
            # spostati): ci si ferma solo dopo 4 giornate consecutive non presenti
            if missing_in_a_row >= GIORNATE_MANCANTI_STOP:
                break
            continue
        missing_in_a_row = 0
        stats["giornate"] += 1
        db.save_calendario(conn, games)
        conn.commit()

        for g in games:
            pid = db.partita_id(season, g["gameid"])
            if g["stato"] != "finished" or pid in already:
                continue
            url = boxscore_url(g["gameid"], league, season)
            try:
                box = fetch_boxscore(client, g["gameid"], league, season)
                _check_score(g, box)
                db.save_partita(conn, g, box, url)
                if with_pbp:
                    import_pbp(conn, client, pid, g["gameid"], league, season,
                               g["squadra_casa_id"], g["squadra_ospite_id"], box)
            except (ParseError, ValueError) as exc:
                log.error("%s: %s", pid, exc)
                stats["errori"].append(f"{pid}: {exc}")
                continue
            already.add(pid)
            stats["nuove"] += 1
            log.info("%s giornata %d: %s %s-%s %s", league, giornata, g["squadra_casa"],
                     box["casa"]["totali"]["punti"], box["ospite"]["totali"]["punti"],
                     g["squadra_ospite"])
    return stats


def import_pbp(conn, client, pid: str, gameid: str, league: str, season: str,
               home_id: int, away_id: int, box: dict) -> dict | None:
    """Scarica la cronaca, ricostruisce i quintetti e salva. Errori non bloccanti."""
    try:
        cr = fetch_pbp(client, gameid, league, season)
    except (ParseError, RuntimeError, requests.RequestException) as exc:
        log.warning("%s: cronaca non disponibile (%s)", pid, exc)
        return None
    ev = cr["eventi"]
    non_abbinati = P.align_ids(ev, box, cr.get("nomi", {}))
    starters = {lato: {g["giocatore_id"] for g in box[lato]["giocatori"] if g["quintetto"]}
                for lato in ("casa", "ospite")}
    minuti = {g["giocatore_id"]: g["minuti"] or 0 for lato in ("casa", "ospite")
              for g in box[lato]["giocatori"]}
    qual = P.quality(ev, (box["casa"]["totali"]["punti"], box["ospite"]["totali"]["punti"]))
    stints, q2 = [], {"quintetti_ok": False, "errore_minuti": None}
    if all(len(v) == 5 for v in starters.values()):
        stints, q2 = P.reconstruct_best(ev, starters, minuti)
    ids = {"casa": home_id, "ospite": away_id}
    for s_ in stints:
        s_["squadra_id"] = ids[s_["lato"]]
    qual |= {"quintetti_ok": bool(q2["quintetti_ok"] and qual["punteggio_ok"]
                                  and non_abbinati == 0),
             "errore_minuti": q2["errore_minuti"]}
    db.save_pbp(conn, pid, home_id, away_id, cr, stints, qual)
    return qual


def recompute_lineups(conn, base=None) -> dict:
    """Ricalcola i quintetti di tutte le partite dalle cronache già salvate (nessuna
    richiesta al sito). Utile quando migliora l'algoritmo di ricostruzione."""
    rows = conn.execute("SELECT p.partita_id, p.gameid, p.stagione, p.squadra_casa_id, "
                        "p.squadra_ospite_id FROM partite p JOIN pbp_qualita q "
                        "USING (partita_id)").fetchall()
    ok = 0
    for pid, gameid, stagione, home, away in rows:
        d = db.load_pbp_file(stagione, gameid, base)
        if not d:
            continue
        campi = d["eventi"]["campi"]
        ev = [dict(zip(campi, r)) for r in d["eventi"]["righe"]]
        for e in ev:
            e["lato"] = "casa" if e["squadra_id"] == home else "ospite"
        box = box_from_db(conn, pid)
        starters = {lato: {g["giocatore_id"] for g in box[lato]["giocatori"] if g["quintetto"]}
                    for lato in ("casa", "ospite")}
        minuti = {g["giocatore_id"]: g["minuti"] or 0 for lato in ("casa", "ospite")
                  for g in box[lato]["giocatori"]}
        qual = P.quality(ev, (box["casa"]["totali"]["punti"], box["ospite"]["totali"]["punti"]))
        stints, q2 = [], {"quintetti_ok": False, "errore_minuti": None}
        if all(len(v) == 5 for v in starters.values()):
            stints, q2 = P.reconstruct_best(ev, starters, minuti)
        ids = {"casa": home, "ospite": away}
        for s_ in stints:
            s_["squadra_id"] = ids[s_["lato"]]
        qual |= {"quintetti_ok": bool(q2["quintetti_ok"] and qual["punteggio_ok"]),
                 "errore_minuti": q2["errore_minuti"]}
        db.save_pbp(conn, pid, home, away, {"eventi": ev}, stints, qual, base)
        ok += qual["quintetti_ok"]
    return {"partite": len(rows), "quintetti_ok": ok}


def box_from_db(conn, pid: str) -> dict:
    """Ricostruisce dal database la struttura minima del box score usata dalla cronaca."""
    home, away = conn.execute("SELECT squadra_casa_id, squadra_ospite_id FROM partite "
                              "WHERE partita_id = ?", (pid,)).fetchone()
    out = {}
    for lato, sid in (("casa", home), ("ospite", away)):
        rows = conn.execute(
            "SELECT b.giocatore_id, g.nome, b.quintetto, b.minuti FROM box_giocatore b "
            "JOIN giocatori g USING (giocatore_id) WHERE partita_id = ? AND squadra_id = ?",
            (pid, sid)).fetchall()
        tot = conn.execute("SELECT punti FROM box_squadra WHERE partita_id = ? AND squadra_id = ?",
                           (pid, sid)).fetchone()[0]
        out[lato] = {"giocatori": [{"giocatore_id": r[0], "nome": r[1], "quintetto": bool(r[2]),
                                    "minuti": r[3]} for r in rows], "totali": {"punti": tot}}
    return out


def backfill_pbp(conn, client, league: str, season: str, limit: int) -> int:
    """Scarica la cronaca delle partite già in archivio che non la hanno."""
    rows = conn.execute(
        "SELECT p.partita_id, p.gameid, p.squadra_casa_id, p.squadra_ospite_id FROM partite p "
        "LEFT JOIN pbp_qualita q USING (partita_id) WHERE q.partita_id IS NULL "
        "AND p.campionato_id = ? AND p.stagione = ? ORDER BY p.partita_id LIMIT ?",
        (league, season, limit)).fetchall()
    for pid, gameid, home, away in rows:
        q = import_pbp(conn, client, pid, gameid, league, season, home, away, box_from_db(conn, pid))
        log.info("%s: cronaca %s", pid, "ok" if q and q["quintetti_ok"] else
                 "salvata (quintetti non verificati)" if q else "assente")
    return len(rows)


def update_players(conn, client, limit: int) -> int:
    """Anagrafica dei giocatori che non la hanno ancora (al massimo `limit` per esecuzione)."""
    todo = db.players_without_info(conn)[:limit]
    for gid in todo:
        try:
            db.save_player_info(conn, gid, fetch_player(client, gid))
        except (ParseError, RuntimeError, requests.RequestException) as exc:
            log.warning("anagrafica %s non disponibile: %s", gid, exc)
            db.save_player_info(conn, gid, {})
    return len(todo)


def _check_score(game: dict, box: dict):
    """Controllo di coerenza tra calendario e box score."""
    for side, key in (("casa", "punti_casa"), ("ospite", "punti_ospite")):
        tot = box[side]["totali"]["punti"]
        somma = sum(p["punti"] or 0 for p in box[side]["giocatori"])
        if somma != tot:
            raise ValueError(f"punti giocatori {side} ({somma}) diversi dal totale ({tot})")
        if game[key] is not None and game[key] != tot:
            raise ValueError(f"punteggio {side} nel box score ({tot}) diverso dal calendario "
                             f"({game[key]})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Aggiorna il database LNP")
    parser.add_argument("--campionati", default=",".join(config.CAMPIONATI),
                        help="codici separati da virgola (default: tutti)")
    parser.add_argument("--giornate", default=None, help="es. 1-2 oppure 1,3,5-7 (default: tutte)")
    parser.add_argument("--stagione", default=config.STAGIONE)
    parser.add_argument("--db", default=str(config.DB_PATH))
    parser.add_argument("--senza-cronaca", action="store_true",
                        help="non scaricare il play-by-play")
    parser.add_argument("--recupero-cronaca", type=int, default=150,
                        help="max partite già in archivio di cui scaricare la cronaca")
    parser.add_argument("--ricalcola-quintetti", action="store_true",
                        help="ricostruisce i quintetti dalle cronache salvate e termina")
    parser.add_argument("--anagrafica", type=int, default=200,
                        help="max giocatori di cui scaricare l'anagrafica")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    giornate = parse_giornate(args.giornate)
    client = RateLimitedClient()
    conn = db.connect(args.db)
    if args.ricalcola_quintetti:
        log.info("Quintetti ricalcolati: %s", recompute_lineups(conn))
        return 0
    errori = []
    for league in [c.strip() for c in args.campionati.split(",") if c.strip()]:
        s = update_league(conn, client, league, args.stagione, giornate,
                          with_pbp=not args.senza_cronaca)
        log.info("%s: %d giornate, %d partite nuove, %d errori",
                 league, s["giornate"], s["nuove"], len(s["errori"]))
        errori += s["errori"]
        if not args.senza_cronaca and args.recupero_cronaca:
            n = backfill_pbp(conn, client, league, args.stagione, args.recupero_cronaca)
            log.info("%s: cronaca recuperata per %d partite", league, n)
    if args.anagrafica:
        log.info("Anagrafica scaricata per %d giocatori", update_players(conn, client,
                                                                         args.anagrafica))
    conn.close()
    log.info("Richieste HTTP effettuate: %d", client.n_requests)
    if errori:
        log.error("Partite non importate (%d):\n  %s", len(errori), "\n  ".join(errori))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
