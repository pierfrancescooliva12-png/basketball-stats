"""Programmi di allenamento della propria squadra: suggerimenti dai numeri e bozza delle sedute.

- priorita_squadra(): le voci dei Four Factors sotto la media, con le aree di lavoro;
- individuali(): le aree di miglioramento di ogni giocatore con gli esercizi adatti;
- quintetti(): i quintetti da consolidare e da correggere, le coppie che funzionano e quelle
  che no, e un quintetto da provare (le coppie migliori tra i giocatori più usati);
- carichi(): i minuti delle ultime partite rispetto alla stagione, per dosare le sedute;
- microciclo(): l'intensità consigliata per ogni giorno, dalla distanza dalla partita;
- bozza_seduta(): una seduta completa (fasi, esercizi, minuti) che lo staff poi modifica;
- nuovo_programma(): il programma della settimana con tutte le sedute.

Un programma è un dizionario serializzabile in JSON (si salva nell'archivio del club).
"""

import itertools
import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import esercizi as E
from . import miglioramento as M

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# quota della seduta per fase, per intensità (squadra); il collettivo assorbe gli arrotondamenti
QUOTE = {
    "alta": {"riscaldamento": .12, "tecnica": .22, "situazioni": .28, "collettivo": .28, "tiro": .05, "defaticamento": .05},
    "media": {"riscaldamento": .13, "tecnica": .25, "situazioni": .25, "collettivo": .25, "tiro": .07, "defaticamento": .05},
    "bassa": {"riscaldamento": .15, "tecnica": .20, "situazioni": .12, "collettivo": .38, "tiro": .10, "defaticamento": .05},
}
# seduta individuale (o di reparto): niente 5c5
QUOTE_INDIVIDUALE = {"riscaldamento": .15, "tecnica": .55, "situazioni": .10, "tiro": .15, "defaticamento": .05}

OBIETTIVO_INTENSITA = {
    "alta": "Seduta di carico: lavoro sulle priorità con contatto e ritmo alto.",
    "media": "Seduta di sviluppo: tecnica e situazioni sulle priorità, collettivo a metà campo.",
    "bassa": "Rifinitura: giochi e situazioni speciali per la partita, carico basso.",
}


def _cognome(nome: str) -> str:
    """Cognome con le maiuscole giuste e le particelle (De Nicolao, Di Pizzo)."""
    from . import figurine as FG
    try:
        return FG.dividi_nome(FG.maiuscole(str(nome)))[1] or str(nome)
    except Exception:
        parti = str(nome).split()
        return parti[-1] if parti else str(nome)


# ------------------------------------------------------------------ priorità e individuali

def priorita_squadra(ctx, sid: int, n: int = 3) -> list[dict]:
    """Le voci dei Four Factors sotto la media (le più importanti prima), con le aree di lavoro."""
    try:
        pri = M.priorita(ctx.profile, sid)
    except Exception:
        return []
    out = []
    for _, r in pri.iterrows():
        if not r["sotto_media"] or len(out) >= n:
            continue
        out.append({"voce": r["voce"], "lato": r["lato"], "colonna": r["colonna"],
                    "ora": M.leggibile(r, "valore"), "obiettivo": M.leggibile(r, "obiettivo"),
                    "posizione": f"{int(r['posizione'])}° su {int(r['squadre'])}",
                    "vittorie": float(r["vittorie"]), "aree": E.AREE_SQUADRA.get(r["colonna"], [])})
    return out


def individuali(ctx, sid: int, giocatori: list[str] | None = None) -> list[dict]:
    """Per ogni giocatore le aree di miglioramento (da basket.sviluppo) e due o tre esercizi."""
    from . import sviluppo as SV
    try:
        schede = SV.squadra(ctx, sid, foto=False)
    except Exception:
        return []
    out = []
    for g in schede:
        if giocatori and g["giocatore_id"] not in giocatori:
            continue
        aree = []
        for a in g["aree"]:
            for x in E.AREE_GIOCATORE.get(a["voce"], []):
                if x not in aree:
                    aree.append(x)
        esercizi = [e["id"] for e in E.per_aree(aree, "tecnica")[:2]] + \
            [e["id"] for e in E.per_aree(aree, "tiro")[:1] if set(e["aree"]) & set(aree)]
        from . import figurine as FG
        out.append({"giocatore_id": g["giocatore_id"], "nome": FG.maiuscole(g["nome"]), "gruppo": g.get("gruppo"),
                    "maglia": g.get("maglia"), "aree": g["aree"], "forza": g.get("forza", [])[:2],
                    "aree_lavoro": aree, "esercizi": esercizi if aree else ["t_tiro_5"]})
    return out


REPARTI = {"esterni": "Esterni", "ali": "Ali", "lunghi": "Lunghi", "tutti": "Altri"}


def reparti(individuali_: list[dict]) -> dict:
    """Giocatori divisi per reparto (esterni, ali, lunghi) per i lavori a stazioni."""
    out = {}
    for g in individuali_:
        out.setdefault(REPARTI.get(g.get("gruppo") or "tutti", "Altri"), []).append(_cognome(g["nome"]))
    return {k: out[k] for k in REPARTI.values() if k in out}


# ------------------------------------------------------------------ quintetti e coppie

def _nomi(ctx, sid: int) -> dict:
    pl = ctx.players[ctx.players["squadra_id"] == sid]
    return dict(zip(pl["giocatore_id"], pl["giocatore"]))


def _quintetto_txt(ids, nomi: dict) -> str:
    return " · ".join(_cognome(nomi.get(i, i)) for i in ids)


def coppie(lineups: pd.DataFrame, sid: int) -> pd.DataFrame:
    """Rendimento di ogni coppia di giocatori in campo insieme (somma dei quintetti in cui
    ci sono entrambi): minuti, punti fatti e subiti, Net rating e Net rating prudente."""
    q = lineups[lineups["squadra_id"] == sid] if lineups is not None and not lineups.empty else pd.DataFrame()
    acc = {}
    for r in q.itertuples():
        ids = sorted(str(r.quintetto).split(","))
        for a, b in itertools.combinations(ids, 2):
            x = acc.setdefault((a, b), [0.0, 0.0, 0.0, 0.0, 0.0])
            x[0] += r.minuti; x[1] += r.pf; x[2] += r.ps; x[3] += r.poss_f; x[4] += r.poss_s
    righe = []
    for (a, b), (mi, pf, ps, pof, pos) in acc.items():
        ortg = 100 * pf / pof if pof else np.nan
        drtg = 100 * ps / pos if pos else np.nan
        net = ortg - drtg
        righe.append({"a": a, "b": b, "minuti": mi, "pf": pf, "ps": ps, "net_rtg": net,
                      "net_stimato": net * mi / (mi + M.MINUTI_PRUDENZA) if pd.notna(net) else np.nan})
    return pd.DataFrame(righe)


def quintetti(ctx, sid: int) -> dict:
    """Suggerimenti sui quintetti da lavorare in allenamento, ognuno con il perché."""
    lu = ctx.lineups
    nomi = _nomi(ctx, sid)
    out = {"consolidare": [], "correggere": [], "coppie_si": [], "coppie_no": [], "provare": None, "soglia": 5.0}
    if lu is None or lu.empty or (lu["squadra_id"] == sid).sum() == 0:
        return out
    migliori, peggiori, soglia = M.quintetti_estremi(lu, sid)
    out["soglia"] = soglia
    for df, chiave in ((migliori, "consolidare"), (peggiori, "correggere")):
        for r in df.itertuples():
            out[chiave].append({"giocatori": _quintetto_txt(str(r.quintetto).split(","), nomi),
                                "minuti": float(r.minuti), "net": float(r.net_rtg)})
    cp = coppie(lu, sid)
    if cp.empty:
        return out
    soglia_c = max(10.0, soglia * 2)
    buone = cp[(cp["minuti"] >= soglia_c) & (cp["net_stimato"] > 0)].sort_values("net_stimato", ascending=False)
    cattive = cp[(cp["minuti"] >= soglia_c) & (cp["net_stimato"] < 0)].sort_values("net_stimato")
    for df, chiave, n in ((buone, "coppie_si", 4), (cattive, "coppie_no", 3)):
        for r in df.head(n).itertuples():
            out[chiave].append({"giocatori": f"{_cognome(nomi.get(r.a, r.a))} · {_cognome(nomi.get(r.b, r.b))}",
                                "minuti": float(r.minuti), "net": float(r.net_rtg)})
    # quintetto da provare: tra i 9 giocatori più usati, i 5 con le coppie migliori tra loro
    pl = ctx.players[ctx.players["squadra_id"] == sid].sort_values("minuti", ascending=False)
    rosa = [g for g in pl["giocatore_id"].head(9) if g in nomi]
    valore = {(r.a, r.b): (r.net_stimato if r.minuti >= soglia else 0.0) for r in cp.itertuples()}
    usati = {tuple(sorted(str(q).split(","))): m for q, m in
             lu[lu["squadra_id"] == sid][["quintetto", "minuti"]].itertuples(index=False)}
    migliore, punti = None, -1e9
    for cinque in itertools.combinations(sorted(rosa), 5):
        p = sum(valore.get(c, 0.0) for c in itertools.combinations(cinque, 2))
        if usati.get(cinque, 0) >= soglia * 2:
            continue                                  # già molto usato: non è una novità
        if p > punti:
            migliore, punti = cinque, p
    if migliore and punti > 0:
        out["provare"] = {"giocatori": _quintetto_txt(migliore, nomi), "minuti": float(usati.get(migliore, 0.0)),
                          "punteggio": float(punti)}
    return out


# ------------------------------------------------------------------ carichi e microciclo

def carichi(ctx, sid: int, ultime: int = 3) -> list[dict]:
    """Giocatori con minuti delle ultime partite molto sopra la media della stagione."""
    bg = ctx.bg[(ctx.bg["squadra_id"] == sid) & (ctx.bg["minuti"] > 0)]
    if bg.empty:
        return []
    date_ = sorted(bg["data"].dropna().unique())[-ultime:]
    out = []
    for gid, g in bg.groupby("giocatore_id"):
        rec = g[g["data"].isin(date_)]["minuti"]
        if len(rec) < min(2, len(date_)):
            continue
        m_rec, m_tot = float(rec.mean()), float(g["minuti"].mean())
        if m_rec >= 28 and m_rec >= 1.15 * m_tot:
            out.append({"nome": g["giocatore"].iloc[0], "recenti": m_rec, "stagione": m_tot,
                        "testo": f"{m_rec:.0f}' di media nelle ultime {len(rec)} partite (stagione {m_tot:.0f}'): "
                                 "carico da dosare, più tecnica e meno contatto".replace(".", ",")})
    return sorted(out, key=lambda x: -x["recenti"])


def microciclo(giorno: date, partita: date | None) -> tuple[str, str]:
    """(etichetta, intensità) per una seduta: MD-1 rifinitura, MD-2 sviluppo, MD-3 o prima
    carico; il giorno dopo la partita recupero."""
    if partita is None:
        return "", "media"
    d = (partita - giorno).days
    if d == 0:
        return "giorno partita", "bassa"
    if d < 0:
        return ("MD+1 · recupero", "bassa") if d == -1 else (f"MD+{-d}", "media")
    return f"MD-{d}", "bassa" if d == 1 else ("media" if d == 2 else "alta")


# ------------------------------------------------------------------ bozza delle sedute

def _arrotonda(minuti: float) -> int:
    return max(5, int(round(minuti / 5.0)) * 5)


def bozza_seduta(durata: int, intensita: str, aree: list[str], individuale: bool = False,
                 usati: set | None = None, quintetto: str = "", giochi: bool = False) -> list[dict]:
    """Blocchi di una seduta: per ogni fase l'esercizio più adatto alle aree (evitando quelli già
    usati nelle sedute precedenti, quando si può) e i minuti; il totale è la durata."""
    usati = set() if usati is None else usati
    quote = QUOTE_INDIVIDUALE if individuale else QUOTE[intensita]
    blocchi = []
    for fase, q in quote.items():
        # nelle rifiniture niente esercizi ad alta intensità; nelle altre sedute si sceglie per area
        cand = E.per_aree(aree, fase, intensita_max="media" if intensita == "bassa" else "alta")
        if not cand:
            cand = E.per_aree(aree, fase)
        if fase == "collettivo" and intensita == "bassa" and giochi:
            scelte = [E.PER_ID["c_rifinitura"]]
        else:
            nuovi = [e for e in cand if e["id"] not in usati]
            scelte = (nuovi or cand)[:2 if fase in ("tecnica", "situazioni") and q * durata >= 20 else 1]
        minuti = _arrotonda(q * durata / max(1, len(scelte)))
        for e in scelte:
            nota = ""
            if fase == "collettivo" and quintetto and e["id"] in ("c_quintetto", "c_tema", "c_rifinitura"):
                nota = f"Quintetto: {quintetto}"
            blocchi.append({"fase": fase, "esercizio": e["id"], "nome": e["nome"], "minuti": minuti,
                            "gruppi": "", "note": nota})
            usati.add(e["id"])
    # il totale torna alla durata: si corregge il collettivo (o il blocco più lungo)
    diff = durata - sum(b["minuti"] for b in blocchi)
    if blocchi and diff:
        coll = [b for b in blocchi if b["fase"] == "collettivo"]
        lungo = coll[-1] if coll else max(blocchi, key=lambda b: b["minuti"])
        lungo["minuti"] = max(5, lungo["minuti"] + diff)
    return blocchi


def orari(blocchi: list[dict], inizio: str = "") -> list[str]:
    """Orario di ogni blocco: "18:00–18:12" se c'è l'ora di inizio, altrimenti "0'–12'"."""
    try:
        h, m = (int(x) for x in inizio.split(":"))
        t0 = h * 60 + m
    except (ValueError, AttributeError):
        t0 = None
    out, t = [], 0
    for b in blocchi:
        d = int(b.get("minuti") or 0)
        if t0 is None:
            out.append(f"{t}'–{t + d}'")
        else:
            a, z = t0 + t, t0 + t + d
            out.append(f"{a // 60 % 24:02d}:{a % 60:02d}–{z // 60 % 24:02d}:{z % 60:02d}")
        t += d
    return out


def nuovo_programma(ctx, sid: int, nome: str, dal: date, giorni: list[int], durata: int = 90,
                    tipo: str = "squadra", giocatori: list[str] | None = None, aree: list[str] | None = None,
                    inizio: str = "18:00", giochi: list[str] | None = None) -> dict:
    """Programma della settimana che parte da `dal`: una seduta per ogni giorno scelto
    (0 = lunedì), con intensità dal microciclo e la bozza degli esercizi."""
    ng = ctx.next_game(sid) if hasattr(ctx, "next_game") else None
    partita = None
    if ng and ng.get("data"):
        try:
            partita = date.fromisoformat(str(ng["data"])[:10])
        except ValueError:
            partita = None
    if partita is not None and partita < dal:       # dati non ancora aggiornati: partita già giocata
        partita, ng = None, None
    individuale = tipo == "individuale"
    if aree is None:
        aree = []
        fonti = individuali(ctx, sid, giocatori) if individuale else priorita_squadra(ctx, sid)
        for x in fonti:
            for a in x.get("aree_lavoro", x.get("aree", [])):
                if isinstance(a, str) and a not in aree:
                    aree.append(a)
    q = quintetti(ctx, sid) if not individuale else {}
    da_lavorare = (q.get("provare") or {}).get("giocatori") or (q.get("consolidare") or [{}])[0].get("giocatori", "")
    usati, sedute = set(), []
    lunedi = dal - timedelta(days=dal.weekday())
    for g in sorted(giorni):
        giorno = lunedi + timedelta(days=g)
        if giorno < dal:
            giorno += timedelta(days=7)
        etichetta, intensita = microciclo(giorno, partita)
        if individuale:
            intensita = "media" if intensita == "alta" else intensita
        # si evitano solo gli esercizi della seduta prima: le priorità tornano ogni due sedute
        blocchi = bozza_seduta(durata, intensita, aree, individuale, set(usati), da_lavorare, bool(giochi))
        usati = {x["esercizio"] for x in blocchi}
        sedute.append({"giorno": giorno.isoformat(), "etichetta": etichetta, "intensita": intensita,
                       "durata": durata, "inizio": inizio, "obiettivo": OBIETTIVO_INTENSITA[intensita],
                       "blocchi": blocchi})
    sedute.sort(key=lambda s: s["giorno"])
    return {"id": uuid.uuid4().hex[:12], "nome": nome, "tipo": tipo, "squadra_id": int(sid),
            "giocatori": list(giocatori or []), "dal": dal.isoformat(), "aree": aree,
            "partita": ({"data": str(ng["data"])[:10], "casa": ng.get("casa"), "ospite": ng.get("ospite")}
                        if ng else None),
            "sedute": sedute, "giochi": list(giochi or []), "note": "",
            "includi": {"obiettivi": True, "sedute": True, "quintetti": not individuale, "individuali": True,
                        "avversaria": bool(ng) and not individuale, "carichi": not individuale,
                        "giochi": bool(giochi), "presenze": True, "esercizi": True}}


def giorno_it(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return str(iso)
    return f"{GIORNI[d.weekday()]} {d.strftime('%d/%m')}"
