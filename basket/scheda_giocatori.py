"""Scouting breve dei singoli giocatori per il report prepartita: anagrafica e foto dal sito,
numeri chiave, caratteristiche e come difenderlo. Le caratteristiche nascono dal confronto con
i giocatori di rotazione dello stesso campionato (percentili), ognuna con il dato che la
giustifica.

Le foto restano sul sito LNP: si scaricano quando si prepara il PDF e si tengono solo nella
cache locale (non vanno nel repository)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
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


def scarica_foto(gid: str, url: str, timeout: float = 4.0) -> bytes | None:
    """Foto dal sito (in cache locale); None se non c'è o non risponde."""
    path = CACHE_FOTO / f"{gid}.jpg"
    if path.exists():
        dati = path.read_bytes()
        return dati or None
    try:
        with urlopen(Request(url, headers={"User-Agent": "ASSIST scouting"}), timeout=timeout) as r:
            dati = r.read(2_000_000)
            tipo = r.headers.get("Content-Type", "")
        ok = dati[:3] == b"\xff\xd8\xff" or dati[:8] == b"\x89PNG\r\n\x1a\n" or tipo.startswith("image/")
        dati = dati if ok else b""
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


def caratteristiche(p, rif: pd.DataFrame, tiro=None, falli=None, finali=None) -> tuple[list, list]:
    """(caratteristiche, come difenderlo): frasi brevi, ognuna con il suo dato."""
    car, dif = [], []    # (priorità, testo)
    t3a, t3p = p.t3a_pg or 0, p.t3_pct
    if p.usg_pct is not None and pd.notna(p.usg_pct) and _pct(rif["usg_pct"], p.usg_pct) >= 85:
        car.append((1, f"Prima opzione dell'attacco ({_it(p.usg_pct)}% dei possessi finiti da lui)"))
    if t3a >= 3 and pd.notna(t3p) and t3p >= 36:
        car.append((2, f"Tiratore da 3 ({_it(p.t3m_pg)}/{_it(t3a)} a partita, {_it(t3p, 0)}%)"))
        dif.append((1, "Mai libero sugli scarichi: chiusura forte e mano alta"))
    elif t3a >= 2.5 and pd.notna(t3p) and t3p < 30:
        car.append((5, f"Tira da 3 ma con poca precisione ({_it(t3p, 0)}% su {_it(t3a)} tentativi)"))
        dif.append((3, "Si può concedere il tiro da 3: passare sotto i blocchi"))
    elif t3a < 0.7 and (p.minuti_pg or 0) >= 15:
        car.append((6, "Quasi mai da 3"))
        dif.append((4, "Difesa più staccata, proteggere l'area"))
    if tiro is not None and pd.notna(tiro.get("quota_area")) and tiro.get("tiri", 0) >= 10:
        if tiro["quota_area"] >= 55:
            car.append((3, f"Attacca il ferro ({_it(tiro['quota_area'], 0)}% dei tiri in area, "
                           f"{_it(tiro.get('area_pct'), 0)}% realizzati)"))
            dif.append((2, "Contenere la penetrazione, aiuto pronto dal lato debole"))
    if (p.tla_pg or 0) >= 3 and _pct(rif["ft_rate"], p.ft_rate) >= 80:
        car.append((4, f"Va spesso in lunetta ({_it(p.tla_pg)} liberi a partita)"))
        dif.append((3, "Mani dietro, niente falli facili sulle penetrazioni"))
    if pd.notna(p.tl_pct) and (p.tla or 0) >= 6 and p.tl_pct < 62:
        car.append((5, f"Debole ai liberi ({_it(p.tl_pct, 0)}%)"))
        dif.append((4, "Nel finale si può mandarlo in lunetta"))
    if (p.assist_pg or 0) >= 3 and _pct(rif["ast_pct"], p.ast_pct) >= 80:
        car.append((2, f"Crea per i compagni ({_it(p.assist_pg)} assist a partita)"))
        dif.append((2, "Pressione sulla palla e anticipo sulle linee di passaggio"))
    if (p.perse_pg or 0) >= 2 and _pct(rif["tov_pct"], p.tov_pct) >= 80:
        car.append((4, f"Perde palloni ({_it(p.perse_pg)} a partita)"))
        dif.append((2, "Raddoppio sul palleggio, costringerlo a decidere in fretta"))
    if _pct(rif["orb_pct"], p.orb_pct) >= 85 and (p.rimb_off_pg or 0) >= 1.5:
        car.append((3, f"Rimbalzista offensivo ({_it(p.rimb_off_pg)} a partita)"))
        dif.append((2, "Tagliafuori sempre su di lui"))
    if pd.notna(p.ts_pct) and p.ts_pct >= 60 and _pct(rif["usg_pct"], p.usg_pct) >= 50:
        car.append((3, f"Molto efficiente al tiro ({_it(p.ts_pct)}% di tiro reale)"))
    if pd.notna(getattr(p, "on_off", None)) and p.on_off >= 10 and (p.minuti_pg or 0) >= 15:
        car.append((3, f"Con lui in campo rendono molto meglio ({_it(p.on_off, 0)} di Net rating)"))
    if falli is not None and falli.get("partite_problemi", 0) >= 2:
        car.append((5, f"Problemi di falli ({int(falli['partite_problemi'])} partite)"))
        dif.append((2, "Attaccarlo subito per caricarlo di falli"))
    if finali is not None and finali.get("fga", 0) >= 3 and (finali.get("quota_tiri") or 0) >= 30:
        car.append((2, f"Uomo dei finali ({_it(finali['quota_tiri'], 0)}% dei tiri negli ultimi 5')"))
        dif.append((3, "Nei finali togliergli la palla: anticipo e cambi sui blocchi"))
    car = [t for _, t in sorted(car)][:4]
    dif = [t for _, t in sorted(dif)][:2]
    return car, dif


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
        car, dif = caratteristiche(p, rif, riga(ctx.shots, p.giocatore_id), riga(ctx.fouls, p.giocatore_id),
                                   riga(ctx.clutch_players, p.giocatore_id))
        out.append({
            "giocatore_id": p.giocatore_id, "nome": p.giocatore,
            "maglia": info.get("maglia"), "ruolo": info.get("ruolo"),
            "altezza": int(info["altezza_cm"]) if pd.notna(info.get("altezza_cm")) else None, "eta": _eta(info.get("data_nascita")),
            "nazionalita": info.get("nazionalita"),
            "foto_url": foto_url(p.giocatore_id, info, ctx.stagione),
            "numeri": [("MIN", _it(p.minuti_pg)), ("PT", _it(p.punti_pg)), ("RIM", _it(p.rimb_tot_pg)),
                       ("AS", _it(p.assist_pg)), ("PP", _it(p.perse_pg))],
            "tiro": f"Da 3: {_it(p.t3m_pg)}/{_it(p.t3a_pg)} ({_it(p.t3_pct, 0)}%) · Liberi {_it(p.tl_pct, 0)}% · "
                    f"Tiro reale {_it(p.ts_pct)}%",
            "caratteristiche": car, "difesa": dif, "foto": None})
    if foto and out:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for s, dati in zip(out, ex.map(lambda s: scarica_foto(s["giocatore_id"], s["foto_url"]), out)):
                s["foto"] = dati
    return out
