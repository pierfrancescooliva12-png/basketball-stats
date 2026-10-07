"""Affidabilità delle previsioni: validazione retrospettiva e registro delle previsioni.

Validazione retrospettiva ("backtest"): per ogni partita in archivio si ricalcola la
previsione usando SOLO le informazioni disponibili prima di quella partita (partite già
giocate nella stagione, stagione precedente, vantaggio del campo stimato fino a quel momento)
e la si confronta con il risultato. Nessuna informazione dal futuro entra nella stima.

Registro: ogni lunedì, dopo l'aggiornamento, si salvano le previsioni delle partite non
ancora giocate (tabella `previsioni`). La previsione di una partita resta quella dell'ultimo
salvataggio prima della partita: il registro documenta previsioni fatte davvero in anticipo.

    python -m basket.validazione            # stampa il riepilogo della validazione
    python -m basket.validazione --salva     # ricalcola e salva data/validazione.csv
    python -m basket.validazione --registra  # salva le previsioni delle prossime partite
"""

import argparse
import math
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import analysis as A
from . import config, db
from . import previsioni as F

FILE_VALIDAZIONE = config.ROOT / "data" / "validazione.csv"

FASCE = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]


# ------------------------------------------------------------------ validazione retrospettiva

def _hca_storico(partite: pd.DataFrame) -> dict:
    """Vantaggio del campo per campionato, stimato con le sole partite precedenti a ogni data:
    {(campionato, data): hca}."""
    out = {}
    for camp, g in partite.sort_values("data").groupby("campionato_id"):
        diff = (g["punti_casa"] - g["punti_ospite"]).to_numpy(float)
        date = g["data"].to_numpy()
        somma, n = 0.0, 0
        prev = None
        for d, x in zip(date, diff):
            if d != prev:
                w = min(1.0, n / 300) if n >= 30 else 0.0
                out[(camp, d)] = w * (somma / n if n else 0) + (1 - w) * \
                    F.VANTAGGIO_CAMPO_DEFAULT
                prev = d
            somma += x
            n += 1
    return out


def carica() -> pd.DataFrame:
    """Validazione salvata dall'aggiornamento settimanale."""
    if not FILE_VALIDAZIONE.exists():
        return pd.DataFrame()
    return pd.read_csv(FILE_VALIDAZIONE)


def backtest(conn, stagioni: list[str] | None = None) -> pd.DataFrame:
    """Una riga per partita giocata: probabilità prevista per la squadra di casa (con i soli
    dati precedenti) e risultato reale."""
    stagioni = sorted(stagioni or [s for s in config.STAGIONI])
    partite = pd.read_sql_query(
        "SELECT partita_id, campionato_id, stagione, giornata, data, squadra_casa_id, "
        "squadra_ospite_id, punti_casa, punti_ospite FROM partite", conn)
    hca = _hca_storico(partite)
    righe = []
    for stag in stagioni:
        bs_all = A.load_box_squadra(conn, stag)
        if bs_all.empty:
            continue
        prior = F.prior_from_previous(conn, stag)
        for camp, bs in bs_all.groupby("campionato_id"):
            pc = partite[(partite["stagione"] == stag) & (partite["campionato_id"] == camp)]
            for data, gg in pc.sort_values("data").groupby("data"):
                prima = bs[bs["data"] < data]
                if prima.empty:
                    forze = pd.DataFrame(columns=["squadra_id", "forza", "pace_stima"])
                else:
                    forze = F.strengths(prima, prior)
                f = forze.set_index("squadra_id") if not forze.empty else forze
                pace_medio = float(prima["pace_partita"].mean()) if not prima.empty and \
                    "pace_partita" in prima else 72.0
                if not np.isfinite(pace_medio):
                    pace_medio = 72.0
                for r in gg.itertuples():
                    fc = _forza(f, r.squadra_casa_id, prior)
                    fo = _forza(f, r.squadra_ospite_id, prior)
                    pc_ = _pace(f, r.squadra_casa_id, pace_medio)
                    po_ = _pace(f, r.squadra_ospite_id, pace_medio)
                    poss = (pc_ + po_) / 2
                    h = hca.get((camp, data), F.VANTAGGIO_CAMPO_DEFAULT)
                    margine = (fc - fo) * poss / 100 + h
                    p = F._phi(margine / F.SIGMA)
                    righe.append({
                        "partita_id": r.partita_id, "stagione": stag, "campionato_id": camp,
                        "giornata": r.giornata, "data": data, "casa_id": r.squadra_casa_id,
                        "ospite_id": r.squadra_ospite_id, "prob_casa": p,
                        "margine_previsto": margine,
                        "margine_reale": r.punti_casa - r.punti_ospite,
                        "vince_casa": r.punti_casa > r.punti_ospite,
                        "partite_note": int(len(prima) / max(1, prima["squadra_id"].nunique()))
                        if not prima.empty else 0})
    return pd.DataFrame(righe)


def _forza(f, sid, prior) -> float:
    if not isinstance(f, pd.DataFrame) or f.empty or sid not in f.index:
        # nessuna partita giocata: si parte dalla stagione precedente, ridotta
        return float(prior.get(sid, 0.0))
    return float(f.loc[sid, "forza"])


def _pace(f, sid, default) -> float:
    if not isinstance(f, pd.DataFrame) or f.empty or sid not in f.index:
        return default
    v = f.loc[sid, "pace_stima"]
    return float(v) if pd.notna(v) else default


# ------------------------------------------------------------------ metriche

def metriche(bt: pd.DataFrame) -> dict:
    """Accuratezza, Brier score, log loss, errore sul margine e confronto con riferimenti
    semplici."""
    if bt.empty:
        return {}
    p = bt["prob_casa"].clip(1e-6, 1 - 1e-6)
    y = bt["vince_casa"].astype(float)
    favorita = np.where(p >= 0.5, y, 1 - y)
    casa_rate = y.mean()
    return {
        "partite": int(len(bt)),
        "accuratezza": 100 * float(favorita.mean()),
        "brier": float(((p - y) ** 2).mean()),
        "brier_riferimento": float(((casa_rate - y) ** 2).mean()),
        "log_loss": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
        "errore_margine": float((bt["margine_previsto"] - bt["margine_reale"]).abs().mean()),
        "rif_sempre_casa": 100 * float(casa_rate),
        "rif_record_migliore": 100 * float(_rif_record(bt)),
    }


def _rif_record(bt: pd.DataFrame) -> float:
    """Riferimento: vince la squadra con la percentuale di vittorie migliore fino a quel
    momento (a parità, la squadra di casa)."""
    ok, n = 0, 0
    for (stag, camp), g in bt.sort_values("data").groupby(["stagione", "campionato_id"]):
        v, p = {}, {}
        for data, gg in g.groupby("data"):
            for r in gg.itertuples():
                pc = v.get(r.casa_id, 0) / max(1, p.get(r.casa_id, 0))
                po = v.get(r.ospite_id, 0) / max(1, p.get(r.ospite_id, 0))
                scelta_casa = pc >= po
                ok += int(scelta_casa == r.vince_casa)
                n += 1
            for r in gg.itertuples():
                for sid, w in ((r.casa_id, r.vince_casa), (r.ospite_id, not r.vince_casa)):
                    v[sid] = v.get(sid, 0) + int(w)
                    p[sid] = p.get(sid, 0) + 1
    return ok / n if n else float("nan")


def calibrazione(bt: pd.DataFrame) -> pd.DataFrame:
    """Per fasce di probabilità della favorita: quante volte la favorita ha vinto davvero."""
    if bt.empty:
        return pd.DataFrame()
    pf = np.maximum(bt["prob_casa"], 1 - bt["prob_casa"])
    vinta = np.where(bt["prob_casa"] >= 0.5, bt["vince_casa"], ~bt["vince_casa"].astype(bool))
    righe = []
    for lo, hi in FASCE:
        m = (pf >= lo) & (pf < hi)
        if m.sum() == 0:
            continue
        righe.append({"fascia": f"{int(lo * 100)}–{min(100, int(round(hi * 100)))}%",
                      "partite": int(m.sum()), "prevista": 100 * float(pf[m].mean()),
                      "reale": 100 * float(vinta[m].mean())})
    return pd.DataFrame(righe)


def per_gruppo(bt: pd.DataFrame, colonna: str) -> pd.DataFrame:
    righe = []
    for k, g in bt.groupby(colonna, observed=True, sort=True):
        m = metriche(g)
        righe.append({colonna: str(k), "partite": m["partite"], "accuratezza": m["accuratezza"],
                      "brier": m["brier"], "errore_margine": m["errore_margine"]})
    return pd.DataFrame(righe)


def fase_stagione(bt: pd.DataFrame) -> pd.Series:
    return pd.cut(bt["giornata"], [0, 5, 15, 100],
                  labels=["Giornate 1-5", "Giornate 6-15", "Dalla 16ª"])


# ------------------------------------------------------------------ registro dal vivo

SCHEMA_REGISTRO = """
CREATE TABLE IF NOT EXISTS previsioni (
    partita_id      TEXT PRIMARY KEY,
    stagione        TEXT,
    campionato_id   TEXT,
    giornata        INTEGER,
    data_partita    TEXT,
    casa_id         INTEGER,
    ospite_id       INTEGER,
    prob_casa       REAL,
    margine         REAL,
    registrata_il   TEXT
)"""


def registra(conn, stagione: str = config.STAGIONE) -> int:
    """Salva (o aggiorna) la previsione di ogni partita non ancora giocata. Le partite già
    giocate non vengono più toccate: resta l'ultima previsione fatta prima della partita."""
    conn.execute(SCHEMA_REGISTRO)
    from .contesto import Contesto
    ctx = Contesto(conn, stagione)
    cal = pd.read_sql_query(
        "SELECT c.partita_id, c.campionato_id, c.giornata, c.data, c.squadra_casa_id, "
        "c.squadra_ospite_id FROM calendario c WHERE c.stagione = ? AND c.stato != 'finished' "
        "AND c.partita_id NOT IN (SELECT partita_id FROM partite)", conn, params=(stagione,))
    ora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n = 0
    for camp, g in cal.groupby("campionato_id"):
        if ctx.bs[ctx.bs["campionato_id"] == camp].empty:
            continue
        forze = ctx.forze(camp)
        hca = ctx.hca(camp)
        for r in g.itertuples():
            try:
                pv = F.predict(forze, r.squadra_casa_id, r.squadra_ospite_id, hca)
            except KeyError:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO previsioni VALUES (?,?,?,?,?,?,?,?,?,?)",
                (r.partita_id, stagione, camp, r.giornata, r.data, r.squadra_casa_id,
                 r.squadra_ospite_id, pv["prob_casa"], pv["margine"], ora))
            n += 1
    conn.commit()
    return n


def registro(conn) -> pd.DataFrame:
    """Previsioni registrate prima delle partite, con il risultato quando disponibile."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='previsioni'").fetchone():
        return pd.DataFrame()
    return pd.read_sql_query(
        """SELECT v.*, p.punti_casa, p.punti_ospite, sc.nome AS casa, so.nome AS ospite
           FROM previsioni v
           LEFT JOIN partite p USING (partita_id)
           LEFT JOIN squadre sc ON sc.squadra_id = v.casa_id
           LEFT JOIN squadre so ON so.squadra_id = v.ospite_id
           ORDER BY v.data_partita DESC""", conn)


# ------------------------------------------------------------------ riga di comando

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Affidabilità delle previsioni")
    ap.add_argument("--registra", action="store_true",
                    help="salva le previsioni delle partite non ancora giocate")
    ap.add_argument("--salva", action="store_true",
                    help="ricalcola la validazione e la salva in data/validazione.csv")
    args = ap.parse_args(argv)
    if args.registra or args.salva:
        if args.salva:
            bt = backtest(db.connect(config.DB_PATH, readonly=True))
            bt.round(4).to_csv(FILE_VALIDAZIONE, index=False)
            print("Validazione salvata:", len(bt), "partite,",
                  f"accuratezza {metriche(bt)['accuratezza']:.1f}%")
        if args.registra:
            print("Previsioni registrate:", registra(db.connect(config.DB_PATH)))
        return 0
    conn = db.connect(config.DB_PATH, readonly=True)
    bt = backtest(conn)
    m = metriche(bt)
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in m.items()})
    print(calibrazione(bt).round(1).to_string(index=False))
    print(per_gruppo(bt.assign(fase=fase_stagione(bt)), "fase").round(3).to_string(index=False))
    print(per_gruppo(bt, "campionato_id").round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
