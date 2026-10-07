"""Chiavi per vincere: su quali fattori lo staff può lavorare per alzare la probabilità di
vittoria contro una squadra precisa.

Quattro analisi, tutte espresse nella stessa unità (probabilità di vittoria della propria
squadra secondo il modello di previsione):

- leve(): i Four Factors della partita (attacco di una squadra contro la difesa dell'altra),
  con l'obiettivo realistico e quanto vale in probabilità raggiungerlo;
- quando_perdono(): in cosa cambia la squadra tra vittorie e sconfitte;
- ritmo(): effetto di una partita più lenta o più veloce;
- giocatori_chiave(): "quando X segna meno di Y punti", misurato come scarto rispetto al
  margine previsto prima di ogni partita (così conta anche la forza dell'avversario), con
  restringimento verso zero quando le partite sono poche.

Sono associazioni osservate nei dati, non rapporti di causa: indicano dove guardare.
"""

import math

import numpy as np
import pandas as pd

from . import previsioni as F

# Peso di ogni fattore sul Net rating di una partita (punti per 100 possessi per un punto
# del fattore). Regressione sulle 4.000 righe squadra-partita di A2 e B Nazionale 2024/25–
# 2026/27 (R² 0,95): un punto di eFG% vale 1,5 punti per 100 possessi, uno di palle perse
# 1,4, uno di rimbalzi offensivi 0,5, uno di frequenza ai liberi (liberi segnati ogni 100
# tiri dal campo) 0,27.
PESI = {"efg": 1.48, "tov": -1.39, "orb": 0.51, "ftr": 27.1}

# nome del fattore visto dalla propria difesa
NOMI_DIFESA = {"efg": "Tiro concesso (eFG%)", "tov": "Palle perse forzate %",
               "orb": "Rimbalzi offensivi concessi %", "ftr": "Tiri liberi concessi"}
NOMI_BREVI = {("efg", "In attacco"): "Tiro", ("efg", "In difesa"): "Tiro concesso",
              ("tov", "In attacco"): "Palle perse", ("tov", "In difesa"): "Palle perse forzate",
              ("orb", "In attacco"): "Rimbalzi offensivi",
              ("orb", "In difesa"): "Rimbalzi concessi",
              ("ftr", "In attacco"): "Tiri liberi", ("ftr", "In difesa"): "Liberi concessi"}

# fattore: (nome, attacco, difesa concessa)
FATTORI = {
    "efg": ("Tiro (eFG%)", "efg_pct", "opp_efg_pct"),
    "tov": ("Palle perse %", "tov_pct", "opp_tov_pct"),
    "orb": ("Rimbalzi offensivi %", "orb_pct", None),       # difesa: 100 − drb_pct
    "ftr": ("Tiri liberi (segnati per tiro)", "ft_rate", "opp_ft_rate"),
}

PARTITE_MIN_PER_LATO = 4   # partite minime sotto e sopra la soglia di un giocatore
SD_SCARTO = 12.0           # dispersione dello scarto partita per partita (punti)
SD_EFFETTO = 4.0           # dispersione attesa degli effetti veri (restringimento)
PARTITE_RESTRINGIMENTO = 6.0  # con g partite lo scostamento di squadra pesa g/(g+6)


def _attacco(r, f):
    return float(r[FATTORI[f][1]])


def _difesa(r, f):
    """Valore che la squadra concede in quel fattore."""
    if f == "orb":
        return 100.0 - float(r["drb_pct"])
    return float(r[FATTORI[f][2]])


def _peso(r) -> float:
    """Affidabilità dello scostamento di una squadra: con poche partite i Four Factors sono
    rumorosi e vengono avvicinati alla media del campionato."""
    g = float(r.get("partite", PARTITE_RESTRINGIMENTO) or 0)
    return g / (g + PARTITE_RESTRINGIMENTO)


def _media(profile, f):
    return float(profile[FATTORI[f][1]].mean())


def _sd(profile, f):
    return float(profile[FATTORI[f][1]].std())


def _prob(margine: float) -> float:
    return F._phi(margine / F.SIGMA)


def _margine_noi(forze, mia, avv, casa_mia: bool, hca: float) -> tuple[float, float]:
    casa, ospite = (mia, avv) if casa_mia else (avv, mia)
    p = F.predict(forze, casa, ospite, hca)
    m = p["margine"] if casa_mia else -p["margine"]
    return m, p["possessi"]


def leve(profile: pd.DataFrame, forze: pd.DataFrame, mia: int, avv: int, casa_mia: bool,
         hca: float) -> pd.DataFrame:
    """Una riga per fattore e lato del campo: valore atteso nella partita, obiettivo e
    probabilità di vittoria se lo si raggiunge.

    Valore atteso = media del campionato + scostamento dell'attacco + scostamento della
    difesa che lo affronta (ciascuno pesato g/(g+6) con g partite giocate). Obiettivo: se il fattore è a sfavore, riportarlo alla media del
    campionato; se è già a favore, migliorarlo di mezza deviazione tra squadre (circa quanto
    separa una squadra media da una buona in quel fattore)."""
    pr = profile.set_index("squadra_id")
    noi, loro = pr.loc[mia], pr.loc[avv]
    m0, poss = _margine_noi(forze, mia, avv, casa_mia, hca)
    p0 = _prob(m0)
    righe = []
    for f, (nome, _, _) in FATTORI.items():
        lg, sd, w = _media(profile, f), _sd(profile, f), PESI[f]
        for lato, att, dif in (("In attacco", noi, loro), ("In difesa", loro, noi)):
            atteso = lg + _peso(att) * (_attacco(att, f) - lg) + \
                _peso(dif) * (_difesa(dif, f) - lg)
            # segno: quanto il fattore aiuta la propria squadra (+ = meglio per noi)
            verso = (1 if w > 0 else -1) * (1 if lato == "In attacco" else -1)
            sfavore = max(0.0, -verso * (atteso - lg))
            passo = sfavore if sfavore > 0 else 0.5 * sd
            obiettivo = atteso + verso * passo
            d_net = abs(w) * passo
            p1 = _prob(m0 + d_net * poss / 100)
            righe.append({
                "fattore": nome if lato == "In attacco" else NOMI_DIFESA[f],
                "breve": NOMI_BREVI[(f, lato)], "chiave": f, "lato": lato,
                "loro": _attacco(loro, f) if lato == "In difesa" else _difesa(loro, f),
                "voi": _attacco(noi, f) if lato == "In attacco" else _difesa(noi, f),
                "media": lg, "atteso": atteso, "obiettivo": obiettivo,
                "situazione": "a vostro sfavore" if sfavore > 0 else "a vostro favore",
                "prob_ora": 100 * p0, "prob_obiettivo": 100 * p1,
                "guadagno": 100 * (p1 - p0)})
    return pd.DataFrame(righe).sort_values("guadagno", ascending=False).reset_index(drop=True)


def ritmo(forze: pd.DataFrame, mia: int, avv: int, casa_mia: bool, hca: float,
          variazioni=(-6, -3, 0, 3, 6)) -> pd.DataFrame:
    """Probabilità di vittoria con più o meno possessi. Il divario tra le squadre cresce
    con i possessi, la casualità solo con la loro radice: le partite lente favoriscono la
    squadra sfavorita, quelle veloci la favorita."""
    m0, poss = _margine_noi(forze, mia, avv, casa_mia, hca)
    h = hca if casa_mia else -hca
    forza = (m0 - h) / poss * 100
    righe = []
    for dv in variazioni:
        p = poss + dv
        m = forza * p / 100 + h
        righe.append({"possessi": p, "variazione": dv,
                      "prob": 100 * F._phi(m / (F.SIGMA * math.sqrt(p / poss)))})
    return pd.DataFrame(righe)


def quando_perdono(bs: pd.DataFrame, squadra_id: int) -> pd.DataFrame:
    """Four Factors, ritmo e tiro da 3 nelle vittorie e nelle sconfitte della squadra,
    ordinati per quanto la differenza pesa sul Net rating."""
    g = bs[bs["squadra_id"] == squadra_id]
    if "efg_pct" not in g:
        from . import analysis as A
        g = A.team_ratings(g)
    v, p = g[g["vinta"] == 1], g[g["vinta"] == 0]
    if len(v) < 3 or len(p) < 3:
        return pd.DataFrame()
    g = g.assign(t3a_rate=100 * g["t3a"] / (g["t2a"] + g["t3a"]),
                 drb_conc=100 - g["drb_pct"])
    voci = [("Tiro (eFG%)", "efg_pct", PESI["efg"]),
            ("Palle perse %", "tov_pct", PESI["tov"]),
            ("Rimbalzi offensivi %", "orb_pct", PESI["orb"]),
            ("Tiri liberi (segnati per tiro)", "ft_rate", PESI["ftr"]),
            ("Tiro concesso (eFG%)", "opp_efg_pct", -PESI["efg"]),
            ("Palle perse forzate %", "opp_tov_pct", -PESI["tov"]),
            ("Rimbalzi offensivi concessi %", "drb_conc", -PESI["orb"]),
            ("Tiri liberi concessi", "opp_ft_rate", -PESI["ftr"]),
            ("Ritmo (possessi)", "pace", 0.0),
            ("Quota di tiri da 3", "t3a_rate", 0.0)]
    vv, pp = g[g["vinta"] == 1], g[g["vinta"] == 0]
    righe = []
    for nome, col, w in voci:
        a, b = float(vv[col].mean()), float(pp[col].mean())
        righe.append({"voce": nome, "colonna": col, "vittorie": a, "sconfitte": b,
                      "differenza": b - a, "peso_net": w * (b - a),
                      "vinte": len(vv), "perse": len(pp)})
    out = pd.DataFrame(righe)
    out["ordine"] = out["peso_net"].abs()
    return out.sort_values("ordine", ascending=False).drop(columns="ordine").reset_index(drop=True)


# ------------------------------------------------------------------ giocatori chiave

STAT_GIOCATORE = {"punti": "punti", "assist": "assist", "rimb_tot": "rimbalzi"}


def _scarti(bt: pd.DataFrame, squadra_id: int) -> pd.Series:
    """Scarto rispetto al previsto (punti, dal punto di vista della squadra) per partita."""
    c = bt[bt["casa_id"] == squadra_id]
    o = bt[bt["ospite_id"] == squadra_id]
    s = pd.concat([c.set_index("partita_id").eval("margine_reale - margine_previsto"),
                   -o.set_index("partita_id").eval("margine_reale - margine_previsto")])
    return s


def _restringi(diff: float, n1: int, n2: int) -> float:
    se2 = SD_SCARTO ** 2 * (1 / n1 + 1 / n2)
    return diff * SD_EFFETTO ** 2 / (SD_EFFETTO ** 2 + se2)


def giocatori_chiave(bg: pd.DataFrame, bt: pd.DataFrame, squadra_id: int,
                     nomi: dict | None = None, minuti_min: float = 15.0) -> pd.DataFrame:
    """Per i giocatori più usati: soglia (mediana arrotondata), scarto medio rispetto al
    previsto quando il giocatore è sotto e sopra la soglia, effetto ristretto, chi
    compensa e scarto nelle partite senza di lui.

    effetto = quanto la squadra fa meglio del previsto quando il giocatore è sopra la
    soglia rispetto a quando è sotto (punti, ristretto verso 0 con pochi dati)."""
    nomi = nomi or {}
    scarti = _scarti(bt, squadra_id)
    if scarti.empty:
        return pd.DataFrame()
    g = bg[(bg["squadra_id"] == squadra_id) & bg["partita_id"].isin(scarti.index)]
    giocate = g[g["minuti"] > 0]
    if giocate.empty:
        return pd.DataFrame()
    mpg = giocate.groupby("giocatore_id")["minuti"].mean()
    chiave = mpg[mpg >= minuti_min].sort_values(ascending=False).index
    righe = []
    for gid in chiave:
        gg = giocate[giocate["giocatore_id"] == gid].set_index("partita_id")
        for col, etichetta in STAT_GIOCATORE.items():
            media = float(gg[col].mean())
            if col == "assist" and media < 3.5 or col == "rimb_tot" and media < 6.5:
                continue
            soglia = float(max(1, round(gg[col].median())))
            sotto = gg.index[gg[col] < soglia]
            sopra = gg.index[gg[col] >= soglia]
            if len(sotto) < PARTITE_MIN_PER_LATO or len(sopra) < PARTITE_MIN_PER_LATO:
                continue
            r_sotto, r_sopra = float(scarti[sotto].mean()), float(scarti[sopra].mean())
            eff = _restringi(r_sopra - r_sotto, len(sotto), len(sopra))
            # chi compensa: il compagno che segna di più quando lui resta sotto soglia
            comp, comp_d = None, 0.0
            altri = giocate[(giocate["giocatore_id"] != gid)]
            for aid, ag in altri.groupby("giocatore_id"):
                a1 = ag[ag["partita_id"].isin(sotto)]["punti"]
                a2 = ag[ag["partita_id"].isin(sopra)]["punti"]
                if len(a1) >= 3 and len(a2) >= 3 and a1.mean() - a2.mean() > comp_d:
                    comp, comp_d = aid, float(a1.mean() - a2.mean())
            # partite della squadra senza di lui, dopo il suo arrivo
            prima_data = gg["data"].min() if "data" in gg else None
            squadra_partite = g.drop_duplicates("partita_id")
            if prima_data is not None:
                squadra_partite = squadra_partite[squadra_partite["data"] >= prima_data]
            assenti = set(squadra_partite["partita_id"]) - set(gg.index)
            r_assente = float(scarti[list(assenti)].mean()) if len(assenti) >= 2 else np.nan
            righe.append({
                "giocatore_id": gid, "giocatore": nomi.get(gid, gid), "statistica": etichetta,
                "colonna": col, "media": media, "soglia": soglia,
                "partite_sotto": len(sotto), "partite_sopra": len(sopra),
                "scarto_sotto": r_sotto, "scarto_sopra": r_sopra, "effetto": eff,
                "quota_sopra": len(sopra) / (len(sotto) + len(sopra)),
                "compensa": nomi.get(comp, comp) if comp else None, "compensa_punti": comp_d,
                "partite_assente": len(assenti), "scarto_assente": r_assente})
    out = pd.DataFrame(righe)
    if out.empty:
        return out
    out["ordine"] = out["effetto"].abs()
    return out.sort_values("ordine", ascending=False).drop(columns="ordine").reset_index(drop=True)


def prob_giocatori(gc: pd.DataFrame, margine_noi: float, avversario: bool) -> pd.DataFrame:
    """Traduce gli effetti nella probabilità della partita. Per un giocatore avversario:
    probabilità se resta SOTTO la soglia; per un proprio giocatore: se va SOPRA."""
    if gc.empty:
        return gc
    gc = gc.copy()
    p0 = _prob(margine_noi)
    if avversario:
        # tenerlo sotto soglia: la sua squadra perde l'effetto per la quota di partite sopra
        delta = gc["effetto"] * gc["quota_sopra"]
    else:
        delta = gc["effetto"] * (1 - gc["quota_sopra"])
    gc["prob_ora"] = 100 * p0
    gc["prob_scenario"] = [100 * _prob(margine_noi + d) for d in delta]
    gc["guadagno"] = gc["prob_scenario"] - gc["prob_ora"]
    return gc


def _f(chiave: str, v: float) -> str:
    return (f"{v:.2f}" if chiave == "ftr" else f"{v:.1f}").replace(".", ",")


def frase_leva(r, avv: str) -> str:
    """Una riga leggibile per una leva."""
    if r["lato"] == "In attacco":
        if r["situazione"] == "a vostro sfavore":
            cosa = f"{r['breve']}: portarlo da {_f(r['chiave'], r['atteso'])} (atteso contro " \
                   f"{avv}) a {_f(r['chiave'], r['obiettivo'])}, la media del campionato"
        else:
            cosa = f"{r['breve']}: sfruttare il vantaggio, da {_f(r['chiave'], r['atteso'])} a " \
                   f"{_f(r['chiave'], r['obiettivo'])}"
    else:
        if r["situazione"] == "a vostro sfavore":
            cosa = f"{r['breve']}: tenere {avv} a {_f(r['chiave'], r['obiettivo'])} (media del " \
                   f"campionato) invece di {_f(r['chiave'], r['atteso'])}"
        else:
            cosa = f"{r['breve']}: allungare il vantaggio, da {_f(r['chiave'], r['atteso'])} a " \
                   f"{_f(r['chiave'], r['obiettivo'])}"
    return f"{cosa} → probabilità dal {r['prob_ora']:.0f}% al {r['prob_obiettivo']:.0f}%"


def frase_giocatore(r, avversario: bool) -> str:
    soglia = f"{r['soglia']:.0f} {r['statistica']}"
    if avversario:
        testo = f"Tenere {r['giocatore']} sotto {soglia}"
    else:
        testo = f"Portare {r['giocatore']} ad almeno {soglia}"
    if "prob_scenario" in r and pd.notna(r.get("prob_scenario")):
        testo += f" → probabilità dal {r['prob_ora']:.0f}% al {r['prob_scenario']:.0f}%"
    return testo + f" ({int(r['partite_sotto'])} partite sotto, {int(r['partite_sopra'])} sopra)"


def sintesi(lv: pd.DataFrame, gc_avv: pd.DataFrame, avv: str, n: int = 3) -> list[str]:
    """Le chiavi principali della partita in parole: le leve con il guadagno maggiore e il
    giocatore avversario con l'effetto più marcato."""
    out = [frase_leva(r, avv) for _, r in lv.head(n - (1 if not gc_avv.empty else 0)).iterrows()]
    if not gc_avv.empty:
        out.append(frase_giocatore(gc_avv.iloc[0], True))
    return out
