"""Sviluppo dei giocatori della propria squadra: cosa fanno bene, cosa fanno male e le aree di
miglioramento, con un obiettivo realistico per ognuna.

Ogni giocatore è confrontato con i giocatori di rotazione dello stesso campionato e dello stesso
gruppo di ruolo (esterni, ali, lunghi: dal ruolo sul sito o, se manca, dall'altezza). Un'area di
miglioramento è una voce sotto il 35° percentile del suo gruppo; l'obiettivo è la mediana del
gruppo, cioè quello che fa un giocatore "normale" del suo ruolo. Quando si può, si stima quanto
vale raggiungerlo in punti a partita, e le aree si ordinano così."""

import numpy as np
import pandas as pd

from . import scheda_giocatori as SG

MINUTI_MIN = 5.0
SOTTO = 35            # percentile sotto cui una voce è un'area di miglioramento
SOPRA = 80            # percentile sopra cui è un punto di forza del ruolo

GRUPPI = {"esterni": "esterni", "ali": "ali", "lunghi": "lunghi"}


def gruppo(ruolo, altezza) -> str | None:
    r = ruolo.lower() if isinstance(ruolo, str) else ""
    if any(k in r for k in ("play", "guardia", "playmaker")):
        return "esterni"
    if any(k in r for k in ("centro", "pivot", "ala grande", "ala/centro", "ala-centro")):
        return "lunghi"
    if "ala" in r:
        return "ali"
    if altezza and not pd.isna(altezza):
        return "esterni" if altezza < 193 else ("ali" if altezza < 202 else "lunghi")
    return None


def _tiri(p) -> float:
    return (p.fga_pg or 0) + 0.44 * (p.tla_pg or 0)


def _n(x, d=1) -> str:
    return f"{x:.{d}f}".rstrip("0").rstrip(".").replace(".", ",") if d else f"{x:.0f}"


def _per_partita(col40):
    """Valore a partita con i minuti del giocatore (il confronto resta per 40 minuti)."""
    return lambda v, p: v * (p.minuti_pg or 0) / 40


def _ogni(v, p):
    return 100 / v if v else np.nan          # palle perse: 1 ogni N possessi usati


def _per_tiro(v, p):
    return 2 * v / 100                        # tiro reale -> punti per tiro (liberi compresi)


# Ogni voce: confronto sulla colonna "col" (per 40 minuti o percentuale), mostrata in un'unità
# da allenatore ("mostra" la converte, "fmt" la scrive). "punti": punti a partita in gioco.
VOCI = [
    dict(voce="Tiri liberi", col="tl_pct", alto=True, volume=lambda p: (p.tla or 0) >= 6,
         fmt=lambda x, p: f"{_n(x, 0)}%", conti=lambda p: f" ({int(p.tlm)}/{int(p.tla)})",
         punti=lambda v, t, p: (t - v) / 100 * (p.tla_pg or 0)),
    dict(voce="Tiro da 3", col="t3_pct", alto=True, volume=lambda p: (p.t3a_pg or 0) >= 1.5,
         fmt=lambda x, p: f"{_n(x, 0)}%", conti=lambda p: f" ({int(p.t3m)}/{int(p.t3a)})",
         punti=lambda v, t, p: 3 * (t - v) / 100 * (p.t3a_pg or 0)),
    dict(voce="Punti per tiro (liberi compresi)", col="ts_pct", alto=True, volume=lambda p: (p.fga_pg or 0) >= 4,
         mostra=_per_tiro, fmt=lambda x, p: _n(x, 2), punti=lambda v, t, p: 2 * (t - v) / 100 * _tiri(p)),
    dict(voce="Palle perse", col="tov_pct", alto=False, volume=lambda p: (p.perse_pg or 0) >= 1,
         mostra=_ogni, fmt=lambda x, p: f"1 ogni {_n(x, 1)} azioni",
         punti=lambda v, t, p: (v - t) / 100 * (_tiri(p) + (p.perse_pg or 0)) * 1.05),
    dict(voce="Assist", col="assist_p40", alto=True, solo={"esterni"}, volume=lambda p: (p.minuti_pg or 0) >= 10,
         mostra=_per_partita("assist"), fmt=lambda x, p: f"{_n(x)} a partita"),
    dict(voce="Rimbalzi difensivi", col="rimb_dif_p40", alto=True, solo={"ali", "lunghi"},
         volume=lambda p: (p.minuti_pg or 0) >= 12, mostra=_per_partita("rimb_dif"),
         fmt=lambda x, p: f"{_n(x)} a partita"),
    dict(voce="Rimbalzi offensivi", col="rimb_off_p40", alto=True, solo={"lunghi"},
         volume=lambda p: (p.minuti_pg or 0) >= 12, mostra=_per_partita("rimb_off"),
         fmt=lambda x, p: f"{_n(x)} a partita"),
    dict(voce="Recuperi", col="recuperate_p40", alto=True, solo={"esterni", "ali"},
         volume=lambda p: (p.minuti_pg or 0) >= 12, mostra=_per_partita("recuperate"),
         fmt=lambda x, p: f"{_n(x)} a partita"),
    dict(voce="Stoppate", col="stoppate_p40", alto=True, solo={"lunghi"},
         volume=lambda p: (p.minuti_pg or 0) >= 12, mostra=_per_partita("stoppate"),
         fmt=lambda x, p: f"{_n(x)} a partita"),
    dict(voce="Falli commessi", col="falli_commessi_p40", alto=False,
         volume=lambda p: (p.minuti_pg or 0) >= 12, mostra=_per_partita("falli"),
         fmt=lambda x, p: f"{_n(x)} a partita"),
]


# parole che indicano lo stesso argomento, per non ripetere un punto di forza già scritto
TEMI = {"tl_pct": ("liberi",), "t3_pct": ("da 3", "triple"), "ts_pct": ("per tiro", "efficiente"),
        "tov_pct": ("palle perse", "palloni"), "assist_p40": ("assist", "compagni"), "rimb_dif_p40": ("rimbalz",),
        "rimb_off_p40": ("rimbalz",), "recuperate_p40": ("recuper",), "stoppate_p40": ("stoppat",),
        "falli_commessi_p40": ("falli",)}


def _it(testo: str) -> str:
    return testo.replace(".", ",")


def _gruppi_lega(rif: pd.DataFrame, ana: pd.DataFrame) -> pd.Series:
    def g(gid):
        info = ana.loc[gid] if not ana.empty and gid in ana.index else {}
        return gruppo(info.get("ruolo") if len(info) else None, info.get("altezza_cm") if len(info) else None)
    return rif["giocatore_id"].map(g)


def aree(p, pari: pd.DataFrame, gia: list[str] = ()) -> tuple[list[dict], list[str]]:
    """(aree di miglioramento, punti di forza del ruolo) di un giocatore rispetto ai pari. Il
    confronto è sulla colonna della voce (per 40 minuti o percentuale); valore e obiettivo sono
    scritti in un'unità da allenatore, a partita con i minuti del giocatore."""
    g = getattr(p, "gruppo", None)
    out, forza = [], []
    for x in VOCI:
        col, alto = x["col"], x["alto"]
        if x.get("solo") and g not in x["solo"]:
            continue
        v = getattr(p, col, None)
        if v is None or pd.isna(v) or not x["volume"](p) or col not in pari:
            continue
        s = pari[col].dropna()
        if len(s) < 8:
            continue
        pct = SG._pct(s, v) if alto else 100 - SG._pct(s, v)
        med = float(s.median())
        mostra = x.get("mostra", lambda y, p: y)
        da, a = mostra(v, p), mostra(med, p)
        if pd.isna(da) or pd.isna(a):
            continue
        conti = x["conti"](p) if "conti" in x else ""
        if pct <= SOTTO and (med > v if alto else med < v):
            punti = x["punti"](v, med, p) if "punti" in x else np.nan
            val, obi = x["fmt"](da, p), x["fmt"](a, p)
            out.append({"voce": x["voce"], "valore": val + conti, "obiettivo": obi, "percentile": pct,
                        "punti_pg": punti, "alto": alto if col != "tov_pct" else True, "da": float(da), "a": float(a),
                        "testo": f"{x['voce']}: {val}{conti} → obiettivo {obi}"
                                 + (f" (circa {_n(punti)} punti a partita)" if pd.notna(punti) and punti >= 0.3
                                    else "")})
        elif pct >= SOPRA and not any(t in " ".join(gia).lower() for t in TEMI.get(col, ())):
            forza.append(f"{x['voce']}: {x['fmt'](da, p)}{conti}, tra i migliori del ruolo")
    out.sort(key=lambda a: (-(a["punti_pg"] if pd.notna(a["punti_pg"]) else 0), a["percentile"]))
    return out, forza


def andamento(bg: pd.DataFrame, gid: str, ultime: int = 3) -> dict | None:
    """Ultime partite contro la media della stagione: punti, minuti, tiro reale."""
    x = bg[(bg["giocatore_id"] == gid) & (bg["minuti"].fillna(0) > 0)].sort_values("data")
    if len(x) < ultime + 2:
        return None

    def ts(d):
        tiri = d["t2a"].sum() + d["t3a"].sum() + 0.44 * d["tla"].sum()
        return 100 * d["punti"].sum() / (2 * tiri) if tiri else np.nan
    rec, tutte = x.tail(ultime), x
    out = {"partite": len(x), "ultime": ultime, "serie": x["punti"].tolist(), "date": x["data"].tolist()}
    for k, a, b in (("punti", rec["punti"].mean(), tutte["punti"].mean()),
                    ("minuti", rec["minuti"].mean(), tutte["minuti"].mean()),
                    ("tiro_reale", ts(rec), ts(tutte))):
        out[k] = (a, b)
    d = out["punti"][0] - out["punti"][1]
    out["tendenza"] = "in crescita" if d >= max(2, 0.2 * out["punti"][1]) else (
        "in calo" if d <= -max(2, 0.2 * out["punti"][1]) else "stabile")
    return out


def squadra(ctx, sid: int, foto: bool = True) -> list[dict]:
    """Una scheda di sviluppo per ogni giocatore della squadra con almeno 5 minuti a partita."""
    pl = ctx.players
    mine = pl[pl["squadra_id"] == sid]
    if mine.empty:
        return []
    camp = mine["campionato_id"].iloc[0]
    rif = pl[(pl["campionato_id"] == camp) & (pl["minuti_pg"] >= SG.MINUTI_ROTAZIONE)].copy()
    ana = SG.anagrafica(ctx.conn)
    rif["gruppo"] = _gruppi_lega(rif, ana)
    schede = {s["giocatore_id"]: s for s in SG.schede(ctx, sid, foto=foto, minuti=MINUTI_MIN, massimo=15)}
    mine = mine[mine["minuti_pg"] >= MINUTI_MIN].sort_values("minuti_pg", ascending=False).copy()
    mine["gruppo"] = _gruppi_lega(mine, ana)
    out = []
    for p in mine.itertuples():
        s = dict(schede.get(p.giocatore_id, {}))
        if not s:
            continue
        pari = rif[rif["gruppo"] == p.gruppo] if p.gruppo and (rif["gruppo"] == p.gruppo).sum() >= 8 else rif
        da_migliorare, forza_ruolo = aree(p, pari, s.get("forza", []))
        s.update({"gruppo": p.gruppo or "tutti", "aree": da_migliorare[:4],
                  "forza": (s.get("forza", []) + forza_ruolo)[:5],
                  "andamento": andamento(ctx.bg, p.giocatore_id), "partite": int(p.partite)})
        out.append(s)
    return out
