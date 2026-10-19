"""Scouting breve dei singoli giocatori per il report prepartita: anagrafica e foto dal sito,
numeri chiave, cosa fa meglio e cosa fa peggio (solo se evidente). Tutto nasce dal confronto
con i giocatori di rotazione dello stesso campionato (percentili), ogni frase con il dato che
la giustifica. Niente indicazioni su come difendere: quelle sono dello staff.

Le foto restano sul sito LNP: si scaricano quando si prepara il PDF e si tengono solo nella
cache locale (non vanno nel repository)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd

from . import config

CACHE_FOTO = config.ROOT / ".cache" / "foto"
MINUTI_ROTAZIONE = 10.0
MAX_GIOCATORI = 10


def _it(v, d=1) -> str:
    if v is None or pd.isna(v):
        return "–"
    v = round(float(v), d)
    return (str(int(v)) if v.is_integer() else f"{v:.{d}f}").replace(".", ",")


def anagrafica(conn) -> pd.DataFrame:
    """Anagrafica dei giocatori (con ruolo, maglia e foto quando già scaricati)."""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(giocatori_info)")}
    except Exception:
        return pd.DataFrame()
    if not cols:
        return pd.DataFrame()
    voci = [c for c in ("giocatore_id", "data_nascita", "nazionalita", "altezza_cm", "ruolo",
                        "maglia", "foto_url") if c in cols]
    return pd.read_sql_query(f"SELECT {', '.join(voci)} FROM giocatori_info", conn).set_index("giocatore_id")


def foto_url(gid: str, info: dict, stagione: str) -> str:
    """Indirizzo della foto: quello letto dalla pagina del giocatore o lo schema del sito."""
    return info.get("foto_url") or f"http://lnp.webpont.com/team/images/player/{stagione}/{gid}.jpg"


def _scarica(url: str, timeout: float) -> bytes:
    """Byte dell'immagine; b"" se all'indirizzo non c'è un'immagine; eccezione se la rete non
    risponde. Prova anche https quando l'indirizzo è http."""
    ultimo = None
    for u in dict.fromkeys([url, url.replace("http://", "https://", 1)]):
        try:
            with urlopen(Request(u, headers={"User-Agent": "Mozilla/5.0 (ASSIST scouting)"}),
                         timeout=timeout) as r:
                dati = r.read(2_000_000)
            if dati[:3] == b"\xff\xd8\xff" or dati[:8] == b"\x89PNG\r\n\x1a\n":
                return dati
            return b""
        except HTTPError as exc:
            if exc.code == 404:
                return b""
            ultimo = exc
        except Exception as exc:          # rete
            ultimo = exc
    raise ultimo or OSError("foto non raggiungibile")


def scarica_foto(gid: str, url: str, timeout: float = 4.0) -> bytes | None:
    """Foto dal sito (in cache locale); None se non c'è o non risponde."""
    path = CACHE_FOTO / f"{gid}.jpg"
    if path.exists():
        dati = path.read_bytes()
        return dati or None
    try:
        dati = _scarica(url, timeout)
    except Exception:
        return None                      # errore di rete: si riprova la prossima volta
    try:
        CACHE_FOTO.mkdir(parents=True, exist_ok=True)
        path.write_bytes(dati)           # anche vuota: "nessuna foto", non si richiede ancora
    except OSError:
        pass
    return dati or None


def _eta(nascita) -> int | None:
    try:
        d = date.fromisoformat(str(nascita)[:10])
    except ValueError:
        return None
    oggi = date.today()
    return oggi.year - d.year - ((oggi.month, oggi.day) < (d.month, d.day))


def _pct(serie: pd.Series, v) -> float:
    """Percentile di v tra i giocatori di rotazione (0-100)."""
    s = serie.dropna()
    if s.empty or v is None or pd.isna(v):
        return 50.0
    return 100.0 * (s < v).mean() + 50.0 * (s == v).mean()


# Voci per completare i punti di forza quando nessuna regola scatta: (colonna, testo)
VOCI_CHIAVE = [("punti_pg", "{v} punti a partita"), ("rimb_tot_pg", "{v} rimbalzi a partita"),
               ("assist_pg", "{v} assist a partita"), ("t3m_pg", "{v} triple a partita"),
               ("recuperate_pg", "{v} palloni recuperati a partita"),
               ("stoppate_pg", "{v} stoppate a partita"), ("falli_subiti_pg", "{v} falli subiti a partita"),
               ("ts_pct", "{v}% di tiro reale")]


def _meglio(pct: float) -> str:
    n = int(round(pct / 5) * 5)
    art = "dell'" if str(n).startswith("8") or n == 11 else "del "
    return f"meglio {art}{n}% dei giocatori di rotazione"


def caratteristiche(p, rif: pd.DataFrame, tiro=None, falli=None, finali=None,
                    altezza=None) -> tuple[list, list]:
    """(cosa fa meglio, cosa fa peggio): frasi brevi, ognuna con il suo dato. Le cose che fa
    meglio sono sempre almeno due; quelle che fa peggio compaiono solo se evidenti."""
    forza, deboli = [], []    # (priorità, testo)
    t3a, t3p = p.t3a_pg or 0, p.t3_pct
    usg = _pct(rif["usg_pct"], p.usg_pct)
    if pd.notna(p.usg_pct) and usg >= 85:
        forza.append((1, f"Prima opzione dell'attacco ({_it(p.usg_pct)}% dei possessi finiti da lui)"))
    if t3a >= 3 and pd.notna(t3p) and t3p >= 36:
        forza.append((2, f"Tiratore da 3 ({_it(p.t3m_pg)}/{_it(t3a)} a partita, {_it(t3p, 0)}%)"))
    elif t3a >= 2.5 and pd.notna(t3p) and t3p < 30:
        deboli.append((2, f"Poco preciso da 3 ({_it(t3p, 0)}% su {_it(t3a)} tentativi a partita)"))
    elif t3a < 0.7 and (p.minuti_pg or 0) >= 15:
        deboli.append((4, f"Quasi mai al tiro da 3 ({_it(t3a)} tentativi a partita)"))
    if tiro is not None and (tiro.get("tiri") or 0) >= 10 and pd.notna(tiro.get("quota_area")):
        if tiro["quota_area"] >= 55:
            forza.append((3, f"Attacca il ferro ({_it(tiro['quota_area'], 0)}% dei tiri in area, "
                             f"{_it(tiro.get('area_pct'), 0)}% realizzati)"))
        if (tiro.get("area_t") or 0) >= 10 and pd.notna(tiro.get("area_pct")) and tiro["area_pct"] < 45:
            deboli.append((3, f"Fatica a concludere in area ({_it(tiro['area_pct'], 0)}% su "
                              f"{int(tiro['area_t'])} tiri)"))
    if (p.tla_pg or 0) >= 3 and _pct(rif["ft_rate"], p.ft_rate) >= 80:
        forza.append((4, f"Va spesso in lunetta ({_it(p.tla_pg)} liberi a partita)"))
    if pd.notna(p.tl_pct) and (p.tla or 0) >= 6:
        if p.tl_pct < 62:
            deboli.append((2, f"Debole ai liberi ({_it(p.tl_pct, 0)}% su {int(p.tla)})"))
        elif p.tl_pct >= 85 and (p.tla or 0) >= 10:
            forza.append((5, f"Sicuro ai liberi ({_it(p.tl_pct, 0)}%)"))
    if (p.assist_pg or 0) >= 3 and _pct(rif["ast_pct"], p.ast_pct) >= 80:
        forza.append((2, f"Crea per i compagni ({_it(p.assist_pg)} assist a partita)"))
    if (p.perse_pg or 0) >= 2 and _pct(rif["tov_pct"], p.tov_pct) >= 85:
        deboli.append((2, f"Perde molti palloni ({_it(p.perse_pg)} a partita)"))
    if _pct(rif["orb_pct"], p.orb_pct) >= 85 and (p.rimb_off_pg or 0) >= 1.5:
        forza.append((3, f"Rimbalzista offensivo ({_it(p.rimb_off_pg)} a partita)"))
    if pd.notna(p.ts_pct) and usg >= 50:
        if p.ts_pct >= 60:
            forza.append((3, f"Molto efficiente al tiro ({_it(p.ts_pct)}% di tiro reale)"))
        elif p.ts_pct < 47:
            deboli.append((3, f"Poco efficiente per quanto tira ({_it(p.ts_pct)}% di tiro reale)"))
    if altezza and altezza >= 203 and "trb_pct" in rif and \
            _pct(rif["trb_pct"], getattr(p, "trb_pct", None)) <= 25:
        deboli.append((4, f"Pochi rimbalzi per la sua taglia ({_it(p.rimb_tot_pg)} a partita, {altezza} cm)"))
    if pd.notna(getattr(p, "on_off", None)) and (p.minuti_pg or 0) >= 15:
        if p.on_off >= 10:
            forza.append((3, f"Con lui in campo rendono molto meglio (+{_it(p.on_off, 0)} di Net rating)"))
        elif p.on_off <= -10:
            deboli.append((4, f"Con lui in campo rendono peggio ({_it(p.on_off, 0)} di Net rating)"))
    if falli is not None and (falli.get("partite_problemi") or 0) >= 2:
        deboli.append((3, f"Problemi di falli ({int(falli['partite_problemi'])} partite con 2 falli nel "
                          f"1° quarto o 3 all'intervallo)"))
    if finali is not None and (finali.get("fga") or 0) >= 3 and (finali.get("quota_tiri") or 0) >= 30:
        forza.append((2, f"Uomo dei finali ({_it(finali['quota_tiri'], 0)}% dei tiri negli ultimi 5')"))
    forza = [t for _, t in sorted(forza)][:4]
    if len(forza) < 2:                 # sempre almeno due informazioni chiave
        cand = []
        for col, testo in VOCI_CHIAVE:
            v = getattr(p, col, None)
            if col in rif and v is not None and pd.notna(v) and v > 0:
                cand.append((_pct(rif[col], v), col, testo.format(v=_it(v))))
        for pct, col, testo in sorted(cand, reverse=True):
            if len(forza) >= 2:
                break
            if not any(testo.split(" ", 1)[1] in f for f in forza):
                forza.append(f"{testo[:1].upper()}{testo[1:]} ({_meglio(pct)})" if pct >= 50 else
                             f"{testo[:1].upper()}{testo[1:]}")
    deboli = [t for _, t in sorted(deboli)][:3]
    return forza, deboli


def schede(ctx, sid: int, foto: bool = True) -> list[dict]:
    """Una scheda per ogni giocatore di rotazione (almeno 10 minuti a partita)."""
    pl = ctx.players
    camp = pl.loc[pl["squadra_id"] == sid, "campionato_id"]
    if camp.empty:
        return []
    camp = camp.iloc[0]
    rif = pl[(pl["campionato_id"] == camp) & (pl["minuti_pg"] >= MINUTI_ROTAZIONE)]
    mine = pl[(pl["squadra_id"] == sid) & (pl["minuti_pg"] >= MINUTI_ROTAZIONE)] \
        .sort_values("minuti_pg", ascending=False).head(MAX_GIOCATORI)
    ana = anagrafica(ctx.conn)

    def riga(df, gid):
        if df is None or df.empty:
            return None
        x = df[df["giocatore_id"] == gid]
        return x.iloc[0].to_dict() if not x.empty else None
    out = []
    for p in mine.itertuples():
        info = ana.loc[p.giocatore_id].to_dict() if not ana.empty and p.giocatore_id in ana.index else {}
        alt = int(info["altezza_cm"]) if pd.notna(info.get("altezza_cm")) else None
        forza, deboli = caratteristiche(p, rif, riga(ctx.shots, p.giocatore_id), riga(ctx.fouls, p.giocatore_id),
                                        riga(ctx.clutch_players, p.giocatore_id), alt)
        out.append({
            "giocatore_id": p.giocatore_id, "nome": p.giocatore,
            "maglia": info.get("maglia"), "ruolo": info.get("ruolo"),
            "altezza": alt, "eta": _eta(info.get("data_nascita")),
            "nazionalita": info.get("nazionalita"),
            "foto_url": foto_url(p.giocatore_id, info, ctx.stagione),
            "numeri": [("MIN", _it(p.minuti_pg)), ("PT", _it(p.punti_pg)), ("RIM", _it(p.rimb_tot_pg)),
                       ("AS", _it(p.assist_pg)), ("PP", _it(p.perse_pg))],
            "tiro": f"Da 3: {_it(p.t3m_pg)}/{_it(p.t3a_pg)} ({_it(p.t3_pct, 0)}%) · Liberi {_it(p.tl_pct, 0)}% · "
                    f"Tiro reale {_it(p.ts_pct)}%",
            "forza": forza, "deboli": deboli, "foto": None})
    if foto and out:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for s, dati in zip(out, ex.map(lambda s: scarica_foto(s["giocatore_id"], s["foto_url"]), out)):
                s["foto"] = dati
    return out


def main(argv=None) -> int:
    """Verifica che le foto del sito siano raggiungibili (non salva nulla nel repository).

        python -m basket.scheda_giocatori --verifica 12
    """
    import argparse
    from .contesto import open_readonly
    ap = argparse.ArgumentParser(description="Verifica delle foto dei giocatori")
    ap.add_argument("--verifica", type=int, default=12, help="quanti giocatori provare")
    args = ap.parse_args(argv)
    ctx = open_readonly()
    ana = anagrafica(ctx.conn)
    pl = ctx.players.sort_values("minuti", ascending=False).head(args.verifica)
    trovate = 0
    for p in pl.itertuples():
        info = ana.loc[p.giocatore_id].to_dict() if not ana.empty and p.giocatore_id in ana.index else {}
        url = foto_url(p.giocatore_id, info, ctx.stagione)
        try:
            dati = _scarica(url, 8.0)
            esito = f"foto ({len(dati) // 1024} kB)" if dati else "nessuna foto"
            trovate += bool(dati)
        except Exception as exc:
            esito = f"non raggiungibile: {exc}"
        print(f"{p.giocatore:30s} {esito:28s} {url}")
    print(f"Foto trovate: {trovate} su {len(pl)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
