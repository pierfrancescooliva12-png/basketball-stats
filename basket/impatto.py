"""Quali prestazioni dei singoli spostano il risultato della squadra, e gli obiettivi sui
giocatori avversari per limitarne l'impatto.

Per ogni giocatore si guardano le sue partite (stagione in corso e precedente, anche in un'altra
squadra) e lo scarto della sua squadra rispetto al margine previsto prima della partita
(validazione retrospettiva). Per punti, triple, assist, rimbalzi e palle perse: con la soglia
(mediana delle sue partite) si confronta lo scarto quando è sopra e quando è sotto. La
differenza, ristretta verso zero con poche partite, è l'effetto: quanti punti di margine vale
per la sua squadra una sua partita sopra la soglia. Sotto le 3 partite per lato si usa la
stima generale del campionato (quanto vale in media una tripla, un assist, ... in più).

Impatto medio sul margine di una unità in più rispetto alla propria media (giocatori da almeno
18 minuti, 27.844 partite di A2 e B Nazionale 2024/25-2025/26): punto 0,31, tripla segnata
1,34, assist 1,14, rimbalzo 0,52, palla persa -0,73."""

import numpy as np
import pandas as pd

from . import analysis as A
from . import chiavi as C
from . import config

VALORE_UNITA = {"punti": 0.31, "t3m": 1.34, "assist": 1.14, "rimb_tot": 0.52, "perse": -0.73}
NOMI = {"punti": "punti", "t3m": "triple segnate", "assist": "assist", "rimb_tot": "rimbalzi",
        "perse": "palle perse"}
SINGOLARE = {"punti": "punto", "t3m": "tripla", "assist": "assist", "rimb_tot": "rimbalzo",
             "perse": "pallone perso"}
SOGLIA_MIN = {"punti": 8, "t3m": 2, "assist": 3, "rimb_tot": 6, "perse": 2}   # obiettivi non banali
PASSO = {"punti": 5, "t3m": 1, "assist": 2, "rimb_tot": 3}    # di quanto abbassarlo nella stima generale
MIN_PER_LATO = 3
EFFETTO_MIN = 1.0          # punti di margine perché un obiettivo sia "provato dai dati"
MINUTI_MIN = 15.0


def _scarti(bt: pd.DataFrame) -> pd.DataFrame:
    """Scarto rispetto al previsto per (partita, squadra), dal punto di vista della squadra."""
    d = bt["margine_reale"] - bt["margine_previsto"]
    casa = pd.DataFrame({"partita_id": bt["partita_id"], "squadra_id": bt["casa_id"], "scarto": d})
    osp = pd.DataFrame({"partita_id": bt["partita_id"], "squadra_id": bt["ospite_id"], "scarto": -d})
    return pd.concat([casa, osp], ignore_index=True)


def storico(ctx) -> pd.DataFrame:
    """Partite dei giocatori (stagione in corso e precedente) con lo scarto della squadra
    (calcolato una volta per contesto)."""
    if "_storico_impatto" in ctx.__dict__:
        return ctx.__dict__["_storico_impatto"]
    ctx.__dict__["_storico_impatto"] = out = _storico(ctx)
    return out


def _storico(ctx) -> pd.DataFrame:
    from . import validazione as V
    bt = V.carica()
    if bt.empty:
        return pd.DataFrame()
    prec = [s for s in sorted(config.STAGIONI) if s < ctx.stagione][-1:]
    parti = [ctx.bg]
    for s in prec:
        try:
            parti.append(A.load_box_giocatore(ctx.conn, s))
        except Exception:
            pass
    bg = pd.concat(parti, ignore_index=True)
    bg = bg[bg["minuti"].fillna(0) > 0]
    return bg.merge(_scarti(bt), on=["partita_id", "squadra_id"], how="inner")


def _it(x, d=1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _seg(x, d=1) -> str:
    return f"{x:+.{d}f}".replace(".", ",").replace("-", "−")


def giocatore(st: pd.DataFrame, gid: str, stagione: str) -> list[dict]:
    """Per ogni statistica: soglia, scarto della squadra sopra e sotto, effetto ristretto."""
    g = st[st["giocatore_id"] == gid]
    if g.empty:
        return []
    ora = g[g["stagione"] == stagione] if "stagione" in g else g
    out = []
    for col in VALORE_UNITA:
        base = ora if len(ora) >= 3 else g
        soglia = float(max(1, round(base[col].median())))
        if soglia < SOGLIA_MIN[col]:
            continue
        sopra, sotto = g[g[col] >= soglia], g[g[col] < soglia]
        if len(sopra) < MIN_PER_LATO or len(sotto) < MIN_PER_LATO:
            continue
        diff = float(sopra["scarto"].mean() - sotto["scarto"].mean())
        out.append({"colonna": col, "soglia": soglia, "media": float(ora[col].mean() if len(ora) else g[col].mean()),
                    "partite_sopra": len(sopra), "partite_sotto": len(sotto),
                    "scarto_sopra": float(sopra["scarto"].mean()), "scarto_sotto": float(sotto["scarto"].mean()),
                    "effetto": C._restringi(diff, len(sopra), len(sotto)), "partite": len(g),
                    "stagioni": int(g["stagione"].nunique()) if "stagione" in g else 1})
    return out


def obiettivi(ctx, sid: int, n: int = 5, st: pd.DataFrame | None = None, avversaria: bool = True) -> list[dict]:
    """Obiettivi sui giocatori più importanti di sid. Per l'avversaria: limitarne l'impatto
    (tenerlo sotto la soglia, o fargli perdere palloni); per la propria squadra: le prestazioni
    che spostano di più il risultato."""
    st = storico(ctx) if st is None else st
    pl = ctx.players[(ctx.players["squadra_id"] == sid) & (ctx.players["minuti_pg"] >= MINUTI_MIN)]
    pl = pl.sort_values("minuti", ascending=False).head(n)
    out = []
    for p in pl.itertuples():
        voci = giocatore(st, p.giocatore_id, ctx.stagione) if not st.empty else []
        # una voce conta se va nel verso atteso: più punti/triple/assist/rimbalzi = squadra meglio,
        # più palle perse = squadra peggio
        buone = [v for v in voci if (v["effetto"] >= EFFETTO_MIN if v["colonna"] != "perse"
                                    else v["effetto"] <= -EFFETTO_MIN)]
        if buone:
            v = max(buone, key=lambda v: abs(v["effetto"]))
            prova = True
        else:
            # stima generale: la sua voce principale e quanto vale in media nel campionato
            col = max(("punti", "t3m", "assist", "rimb_tot"),
                      key=lambda c: abs(VALORE_UNITA[c]) * (getattr(p, f"{c}_pg", 0) or 0)
                      if (getattr(p, f"{c}_pg", 0) or 0) >= SOGLIA_MIN[c] else -1)
            media = float(getattr(p, f"{col}_pg", 0) or 0)
            if media < SOGLIA_MIN[col] + PASSO[col]:
                continue                      # nessuna voce abbastanza grande da farne un obiettivo
            v = {"colonna": col, "soglia": float(max(1, round(media - PASSO[col]))), "media": media,
                 "effetto": np.nan, "partite": int(p.partite), "stagioni": 1}
            prova = False
        col, soglia = v["colonna"], v["soglia"]
        nome = NOMI[col]
        if col == "perse":
            obiettivo = (f"fargli perdere almeno {soglia:.0f} palloni" if avversaria
                         else f"meno di {soglia:.0f} palle perse")
        else:
            obiettivo = (f"tenerlo sotto {soglia:.0f} {nome}" if avversaria
                         else f"almeno {soglia:.0f} {nome}")
        if prova:
            perche = (f"con almeno {soglia:.0f} {nome} la sua squadra è andata {_seg(v['scarto_sopra'])} punti "
                      f"rispetto al previsto ({v['partite_sopra']} partite), sotto i {soglia:.0f} "
                      f"{_seg(v['scarto_sotto'])} ({v['partite_sotto']} partite)")
            vale = abs(v["effetto"])
        else:
            passo = v["media"] - soglia
            vale = abs(VALORE_UNITA[col]) * passo
            perche = (f"media {_it(v['media'])} {nome}; le sue partite non bastano ancora per misurarne l'effetto: "
                      f"in media nel campionato ogni {SINGOLARE[col]} in meno vale {_it(abs(VALORE_UNITA[col]), 2)} "
                      f"punti di margine")
        out.append({"giocatore_id": p.giocatore_id, "giocatore": p.giocatore, "colonna": col, "statistica": nome,
                    "soglia": soglia, "media": v["media"], "obiettivo": obiettivo, "perche": perche,
                    "effetto": v.get("effetto"), "vale": vale, "provato": prova, "partite": v.get("partite"),
                    "stagioni": v.get("stagioni", 1), "minuti": float(p.minuti_pg)})
    out.sort(key=lambda o: (not o["provato"], -(o["vale"] or 0)))
    return out


def testo_vale(o: dict) -> str:
    """Quanto vale l'obiettivo, in punti di margine per la propria squadra."""
    return f"circa {_it(o['vale'])} punti di margine" + ("" if o["provato"] else " (stima generale)")
