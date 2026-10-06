"""Aggiornamento incrementale del database.

Esempi:
    python -m basket.update                                # tutti i campionati, tutte le giornate
    python -m basket.update --campionati ita2 --giornate 1-2
"""

import argparse
import logging
import sys

from . import config, db
from .client import RateLimitedClient
from .scraper import ParseError, boxscore_url, fetch_boxscore, fetch_schedule

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


def update_league(conn, client, league: str, season: str, giornate: set[int] | None) -> dict:
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
            if missing_in_a_row >= 2:
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
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    giornate = parse_giornate(args.giornate)
    client = RateLimitedClient()
    conn = db.connect(args.db)
    errori = []
    for league in [c.strip() for c in args.campionati.split(",") if c.strip()]:
        s = update_league(conn, client, league, args.stagione, giornate)
        log.info("%s: %d giornate, %d partite nuove, %d errori",
                 league, s["giornate"], s["nuove"], len(s["errori"]))
        errori += s["errori"]
    conn.close()
    log.info("Richieste HTTP effettuate: %d", client.n_requests)
    if errori:
        log.error("Partite non importate (%d):\n  %s", len(errori), "\n  ".join(errori))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
