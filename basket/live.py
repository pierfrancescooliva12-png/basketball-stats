"""Partita in diretta: stato dalla cronaca e suggerimenti per lo staff.

La cronaca arriva da legapallacanestro.com mentre si gioca (stessa pagina usata per le partite
finite, letta ogni ~30 secondi) oppure, per rivedere o allenarsi, da una partita in archivio
fermata a un minuto scelto. Dallo stato si ricavano: punteggio e probabilità di vittoria, falli e
bonus, timeout, parziali, Four Factors contro la media della stagione, chi è caldo, Leverage in
partita, e una lista di suggerimenti ordinati per urgenza, dal punto di vista della propria squadra.
"""

import pandas as pd

from . import leverage as L

BONUS = 4                    # FIBA: dal 5° fallo di squadra nel periodo si tirano i liberi
TIMEOUT_PRIMO_TEMPO, TIMEOUT_SECONDO_TEMPO, TIMEOUT_SUPPLEMENTARE = 2, 3, 1


# ------------------------------------------------------------------ cronaca

def da_cronaca(cr: dict, casa_id, ospite_id, partita_id="live") -> pd.DataFrame:
    """Eventi della pagina play-by-play (lato casa/ospite) nel formato dell'archivio."""
    ev = pd.DataFrame(cr["eventi"])
    if ev.empty:
        return ev
    ev["squadra_id"] = ev["lato"].map({"casa": casa_id, "ospite": ospite_id})
    return normalizza(ev, casa_id, ospite_id, partita_id)


def normalizza(ev: pd.DataFrame, casa_id, ospite_id, partita_id) -> pd.DataFrame:
    ev = ev.copy()
    ev["partita_id"] = partita_id
    ev["squadra_casa_id"], ev["squadra_ospite_id"] = casa_id, ospite_id
    ev["casa"] = ev["squadra_id"] == casa_id
    ev["avversario_id"] = ev["casa"].map({True: ospite_id, False: casa_id})
    ev["di_squadra"] = ev["di_squadra"].fillna(False).astype(bool)
    for c in ("punti_casa", "punti_ospite"):
        ev[c] = ev[c].ffill().fillna(0)
    return ev.sort_values("n").reset_index(drop=True)


def fino_a(ev: pd.DataFrame, secondi: float) -> pd.DataFrame:
    """La partita fermata a un certo istante (per rivederla come se fosse in diretta)."""
    return ev[ev["secondi"] <= secondi].copy()


# ------------------------------------------------------------------ stato

def _fattori(e: pd.DataFrame) -> dict:
    c = e["tipo"].value_counts()
    g = lambda k: int(c.get(k, 0))  # noqa: E731
    t2m, t3m = g("tiro2_fatto"), g("tiro3_fatto")
    fga = t2m + t3m + g("tiro2_sbagliato") + g("tiro3_sbagliato")
    fta, ftm = g("tl_fatto") + g("tl_sbagliato"), g("tl_fatto")
    tov, orb = g("persa"), g("rimb_off")
    poss = fga + 0.44 * fta + tov - orb
    return {"fga": fga, "sbagliati": fga - t2m - t3m, "efg": 100 * (t2m + 1.5 * t3m) / fga if fga else None,
            "tov": 100 * tov / poss if poss > 0 else None, "perse": tov, "rimb_off": orb,
            "ft_rate": 100 * ftm / fga if fga else None, "liberi": f"{ftm}/{fta}",
            "t3": f"{t3m}/{t3m + g('tiro3_sbagliato')}", "possessi": poss}


def stato(ev: pd.DataFrame, noi, attesa_noi: float = 0.0, nomi: dict | None = None) -> dict:
    """Situazione della partita dal punto di vista di `noi` (id della propria squadra)."""
    nomi = nomi or {}
    if ev.empty:
        return {"vuota": True}
    casa_id, osp_id = ev["squadra_casa_id"].iloc[0], ev["squadra_ospite_id"].iloc[0]
    loro = osp_id if noi == casa_id else casa_id
    ultimo = ev.iloc[-1]
    periodo, secondi = int(ultimo["periodo"]), float(ultimo["secondi"])
    pc, po = int(ultimo["punti_casa"]), int(ultimo["punti_ospite"])
    p_noi, p_loro = (pc, po) if noi == casa_id else (po, pc)
    resta = L.restante(periodo, secondi)
    fine_periodo = (600 * periodo if periodo <= 4 else 2400 + 300 * (periodo - 4))
    resta_periodo = max(0.0, fine_periodo - secondi)
    # falli di squadra nel periodo e personali
    nel_periodo = ev[(ev["periodo"] == periodo) & ev["tipo"].isin(["fallo", "fallo_tecnico"])]
    falli = {s: int((nel_periodo["squadra_id"] == s).sum()) for s in (noi, loro)}
    pers = ev[ev["tipo"].isin(["fallo", "fallo_tecnico"]) & ev["giocatore_id"].notna()]
    personali = pers.groupby(["squadra_id", "giocatore_id"]).size()
    # timeout rimasti
    to = ev[ev["tipo"] == "timeout"]
    def rimasti(s):
        t = to[to["squadra_id"] == s]
        if periodo <= 2: return TIMEOUT_PRIMO_TEMPO - int((t["periodo"] <= 2).sum())
        if periodo <= 4:
            usati = int(t["periodo"].between(3, 4).sum())
            r = TIMEOUT_SECONDO_TEMPO - usati
            if periodo == 4 and resta_periodo <= 120:     # negli ultimi 2' al massimo 2
                r = min(r, 2 - int(((t["periodo"] == 4) & (t["secondi"] >= 2280)).sum()))
            return max(0, r)
        return TIMEOUT_SUPPLEMENTARE - int((t["periodo"] == periodo).sum())
    # parziali: ultimi 3 minuti e serie in corso
    punti = ev[ev["punti"] > 0] if "punti" in ev else ev[ev["tipo"].isin(["tiro2_fatto", "tiro3_fatto", "tl_fatto"])]
    if "punti" not in ev:
        punti = punti.assign(punti=punti["tipo"].map({"tiro2_fatto": 2, "tiro3_fatto": 3, "tl_fatto": 1}))
    rec = punti[punti["secondi"] >= secondi - 180]
    parziale = {s: int(rec.loc[rec["squadra_id"] == s, "punti"].sum()) for s in (noi, loro)}
    serie = {noi: 0, loro: 0}
    for r in punti.iloc[::-1].itertuples():
        if serie[noi] and r.squadra_id == loro or serie[loro] and r.squadra_id == noi:
            break
        serie[r.squadra_id] += r.punti
    # giocatori in partita
    g = ev[ev["giocatore_id"].notna() & ~ev["di_squadra"]]
    pt = g[g["tipo"].isin(["tiro2_fatto", "tiro3_fatto", "tl_fatto"])].assign(
        p=lambda d: d["tipo"].map({"tiro2_fatto": 2, "tiro3_fatto": 3, "tl_fatto": 1}))
    per_g = pt.groupby(["squadra_id", "giocatore_id"])["p"].sum()
    tiri = g[g["tipo"].str.startswith("tiro")].groupby(["squadra_id", "giocatore_id"])["tipo"].agg(
        fatti=lambda s: int(s.str.endswith("fatto").sum()), tentati="size")
    giocatori = tiri.join(per_g.rename("punti"), how="outer").fillna(0).reset_index()
    giocatori["falli"] = [int(personali.get((s, x), 0)) for s, x in giocatori[["squadra_id", "giocatore_id"]].values]
    for (s, x), n in personali.items():
        if not ((giocatori["squadra_id"] == s) & (giocatori["giocatore_id"] == x)).any():
            giocatori.loc[len(giocatori)] = [s, x, 0, 0, 0, int(n)]
    giocatori["nome"] = giocatori["giocatore_id"].map(nomi).fillna(giocatori["giocatore_id"])
    # probabilità e leverage
    sw = L.swing(ev, {ev["partita_id"].iloc[0]: attesa_noi if noi == casa_id else -attesa_noi})
    wp_casa = float(sw["wp_casa"].dropna().iloc[-1]) if sw["wp_casa"].notna().any() else 0.5
    wp = wp_casa if noi == casa_id else 1 - wp_casa
    cr = L.crediti(sw)
    lev = cr.groupby(["squadra_id", "giocatore_id"])["leverage"].sum().reset_index() if not cr.empty else \
        pd.DataFrame(columns=["squadra_id", "giocatore_id", "leverage"])
    giocatori = giocatori.merge(lev, on=["squadra_id", "giocatore_id"], how="left")
    return {"vuota": False, "noi": noi, "loro": loro, "casa": casa_id, "periodo": periodo, "secondi": secondi,
            "resta": resta, "resta_periodo": resta_periodo, "punti": {noi: p_noi, loro: p_loro},
            "margine": p_noi - p_loro, "wp": wp, "falli": falli, "bonus": {s: falli[s] >= BONUS for s in falli},
            "timeout": {noi: rimasti(noi), loro: rimasti(loro)}, "parziale_3": parziale, "serie": serie,
            "fattori": {noi: _fattori(ev[ev["squadra_id"] == noi]), loro: _fattori(ev[ev["squadra_id"] == loro])},
            "giocatori": giocatori, "eventi": sw}


# ------------------------------------------------------------------ suggerimenti

def _orologio(resta_periodo):
    m, s = divmod(int(resta_periodo), 60)
    return f"{m}:{s:02d}"


def suggerimenti(s: dict, stagione: dict | None = None, giocatori_stagione: pd.DataFrame | None = None) -> list[dict]:
    """Suggerimenti ordinati per urgenza (3 = adesso, 2 = presto, 1 = da tenere d'occhio).
    stagione: {"noi": {...}, "loro": {...}} medie della stagione (efg_pct, tov_pct, orb_pct, drb_pct,
    opp_efg_pct, opp_tov_pct, opp_ft_rate); giocatori_stagione: giocatore_id, punti_pg, falli_pg."""
    if s.get("vuota"):
        return []
    noi, loro, out = s["noi"], s["loro"], []
    add = lambda u, cat, testo: out.append({"urgenza": u, "categoria": cat, "testo": testo})  # noqa: E731
    finale = s["periodo"] >= 4 and s["resta_periodo"] <= 120
    if s["periodo"] >= 4 and (s["wp"] > 0.98 or s["wp"] < 0.02):
        add(2, "Gestione", ("Partita in controllo" if s["wp"] > 0.5 else "Partita quasi persa") +
            f" (probabilità {100 * s['wp']:.0f}%): minuti alla panchina, proteggere chi ha falli o carichi alti.")
        return out
    m = s["margine"]
    # parziali e timeout
    serie_loro, parz = s["serie"][loro], s["parziale_3"]
    if (serie_loro >= 8 or parz[loro] - parz[noi] >= 8) and not finale:
        if s["timeout"][noi] > 0:
            add(3, "Timeout", f"Parziale avversario {parz[loro]}-{parz[noi]} negli ultimi 3' "
                f"(serie aperta di {serie_loro}): fermare la partita. Restano {s['timeout'][noi]} timeout.")
        else:
            add(3, "Parziale", f"Parziale avversario {parz[loro]}-{parz[noi]} e nessun timeout: cambio o difesa diversa.")
    if s["timeout"][noi] == 0 and s["periodo"] >= 3:
        add(1, "Timeout", "Nessun timeout rimasto in questo tempo.")
    # falli e bonus
    if s["bonus"][noi]:
        add(2, "Falli", f"{s['falli'][noi]} falli di squadra: ogni fallo manda l'avversario in lunetta fino alla fine "
            f"del periodo ({_orologio(s['resta_periodo'])}). Difendere senza mani.")
    elif s["falli"][noi] == BONUS - 1:
        add(1, "Falli", f"{s['falli'][noi]} falli di squadra: il prossimo manda in bonus l'avversario.")
    if s["bonus"][loro]:
        add(2, "Attacco", f"Avversario a {s['falli'][loro]} falli di squadra: attaccare il ferro, ogni contatto vale due liberi.")
    soglia = {1: 2, 2: 3, 3: 4}.get(s["periodo"], 4)
    gio = s["giocatori"]
    for r in gio[(gio["squadra_id"] == noi) & (gio["falli"] >= 5)].itertuples():
        add(1, "Falli", f"{r.nome} è uscito per 5 falli.")
    for r in gio[(gio["squadra_id"] == noi) & (gio["falli"] >= soglia) & (gio["falli"] < 5)].itertuples():
        add(3 if r.falli >= 4 else 2, "Falli", f"{r.nome} ha {int(r.falli)} falli nel {s['periodo']}° periodo: valutare la panchina "
            "o difesa senza contatto.")
    for r in gio[(gio["squadra_id"] == loro) & (gio["falli"] >= soglia) & (gio["falli"] < 5)].itertuples():
        add(2, "Attacco", f"{r.nome} (avversario) ha {int(r.falli)} falli: attaccarlo in uno contro uno.")
    # chi è caldo
    if giocatori_stagione is not None and not giocatori_stagione.empty:
        media = giocatori_stagione.set_index("giocatore_id")["punti_pg"]
        frazione = max(0.25, min(1.0, (2400 - s["resta"]) / 2400))
        for r in gio[gio["squadra_id"] == loro].itertuples():
            mp = media.get(r.giocatore_id)
            if mp is not None and r.punti >= 8 and r.punti > 1.5 * mp * frazione:
                add(2, "Difesa", f"{r.nome} è a {int(r.punti)} punti (media {f'{mp:.1f}'.replace('.', ',')} a partita): cambiare marcatura o "
                    "raddoppiare quando riceve.")
    # Four Factors contro la stagione
    if stagione:
        f, fl = s["fattori"][noi], s["fattori"][loro]
        sn, sl = stagione.get("noi", {}), stagione.get("loro", {})
        if f["fga"] >= 10:
            if f["tov"] is not None and sn.get("tov_pct") and f["tov"] > sn["tov_pct"] + 5:
                add(2, "Attacco", f"Palle perse al {f['tov']:.0f}% dei possessi (stagione {sn['tov_pct']:.0f}%): "
                    f"{f['perse']} perse, giocare più semplice e proteggere il primo passaggio.")
            attesi = (1 - (sn.get("drb_pct") or 70) / 100) * fl["sbagliati"]     # con la vostra % di rimbalzi difensivi
            if fl["rimb_off"] >= 4 and fl["rimb_off"] > 1.5 * attesi + 1:
                add(2, "Rimbalzo", f"{fl['rimb_off']} rimbalzi offensivi concessi: tagliafuori su tutti i tiri, anche delle guardie.")
            if fl["efg"] is not None and sn.get("opp_efg_pct") and fl["efg"] > sn["opp_efg_pct"] + 8 and fl["fga"] >= 10:
                add(2, "Difesa", f"Avversario al {fl['efg']:.0f}% di tiro effettivo (concedete di solito il "
                    f"{sn['opp_efg_pct']:.0f}%): chiudere l'area o contestare di più il tiro da fuori.")
            if f["efg"] is not None and sn.get("efg_pct") and f["efg"] < sn["efg_pct"] - 10:
                add(1, "Attacco", f"Tiro effettivo al {f['efg']:.0f}% (stagione {sn['efg_pct']:.0f}%): cercare tiri più vicini "
                    "al ferro o dal pick and roll.")
    # finale
    if finale or (s["periodo"] >= 4 and s["resta_periodo"] <= 180):
        poss = max(1, round(s["resta_periodo"] / 24))
        if m < 0 and -m > 3 * poss:
            add(3, "Finale", f"Sotto di {-m} con circa {poss} possessi per parte: servono falli subito e triple.")
        elif m < 0 and s["resta_periodo"] <= 60 and -m >= 4:
            add(3, "Finale", f"Sotto di {-m} a {_orologio(s['resta_periodo'])}: fallo sistematico sul peggior tiratore di liberi.")
        elif 0 < m <= 3 and s["resta_periodo"] <= 30:
            add(3, "Finale", f"Avanti di {m} a {_orologio(s['resta_periodo'])}: niente triple concesse"
                + (", valutare il fallo prima del tiro da 3." if m == 3 else ", difendere senza fallo."))
        elif -3 <= m <= 0 and s["resta_periodo"] <= 40:
            add(3, "Finale", f"{'Pari' if m == 0 else f'Sotto di {-m}'} a {_orologio(s['resta_periodo'])}: "
                + ("tiro per vincere, ultimo possesso." if m == 0 else "attaccare presto per avere un secondo possesso."))
        if s["timeout"][noi] and abs(m) <= 6:
            add(2, "Finale", f"{s['timeout'][noi]} timeout disponibili per il finale: tenerne uno per la rimessa in attacco.")
    # leverage
    top = gio[gio["squadra_id"] == loro].sort_values("leverage", ascending=False).head(1)
    if not top.empty and (top["leverage"].iloc[0] or 0) > 1.0:
        add(1, "Leverage", f"{top['nome'].iloc[0]} è chi sta spostando di più la partita per loro "
            f"({top['leverage'].iloc[0]:+.1f})".replace(".", ",") + ".")
    return sorted(out, key=lambda x: -x["urgenza"])


# ------------------------------------------------------------------ in diretta

def scarica(gameid: str, campionato: str, stagione: str) -> dict:
    """Cronaca della partita in corso dal sito della lega (una richiesta, senza attese)."""
    from .client import RateLimitedClient
    from .scraper import fetch_pbp
    return fetch_pbp(RateLimitedClient(min_interval=0, retries=2), gameid, campionato, stagione)


PRIMA, DURATA_MAX = 20, 150     # minuti: la diretta si apre 20' prima della palla a due e dura al massimo 2 ore e mezza
FUSO = "Europe/Rome"
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def adesso():
    """Ora italiana (il calendario della lega è in ora locale), senza fuso per i confronti."""
    return pd.Timestamp.now(tz=FUSO).tz_localize(None)


def calendario(conn, stagione: str, squadra=None, da=None, giorni: int = 400) -> pd.DataFrame:
    """Partite in calendario con inizio, apertura e chiusura della diretta e stato:
    'finita', 'in corso', 'oggi' (più tardi), 'in programma'."""
    q = ("SELECT c.partita_id, c.gameid, c.campionato_id, c.stagione, c.giornata, c.data, c.ora, c.stato, "
         "c.squadra_casa_id, c.squadra_ospite_id, sc.nome AS casa, so.nome AS ospite, c.palazzetto "
         "FROM calendario c JOIN squadre sc ON sc.squadra_id = c.squadra_casa_id "
         "JOIN squadre so ON so.squadra_id = c.squadra_ospite_id WHERE c.stagione = ?")
    par = [stagione]
    if squadra is not None:
        q += " AND (c.squadra_casa_id = ? OR c.squadra_ospite_id = ?)"; par += [int(squadra), int(squadra)]
    d = pd.read_sql_query(q, conn, params=par)
    if d.empty:
        return d
    d["inizio"] = pd.to_datetime(d["data"] + " " + d["ora"].fillna("18:00"), errors="coerce")
    d["apre"] = d["inizio"] - pd.Timedelta(minutes=PRIMA)
    d["chiude"] = d["inizio"] + pd.Timedelta(minutes=DURATA_MAX)
    ora = da if da is not None else adesso()
    def fase(r):
        if r.stato == "finished" or ora > r.chiude: return "finita"
        if ora >= r.apre: return "in corso"
        if r.inizio.date() == ora.date(): return "oggi"
        return "in programma"
    d["fase"] = [fase(r) for r in d.itertuples()]
    d["giorno"] = [f"{GIORNI[t.weekday()]} {t.strftime('%d/%m')}" for t in d["inizio"]]
    d = d[d["inizio"] <= ora + pd.Timedelta(days=giorni)]
    return d.sort_values("inizio").reset_index(drop=True)


def partite_di_oggi(conn, stagione: str, giorno: str) -> pd.DataFrame:
    """Partite in calendario nel giorno indicato (AAAA-MM-GG), anche quelle non ancora finite."""
    return pd.read_sql_query(
        "SELECT c.partita_id, c.gameid, c.campionato_id, c.stagione, c.data, c.ora, c.stato, "
        "c.squadra_casa_id, c.squadra_ospite_id, sc.nome AS casa, so.nome AS ospite "
        "FROM calendario c JOIN squadre sc ON sc.squadra_id = c.squadra_casa_id "
        "JOIN squadre so ON so.squadra_id = c.squadra_ospite_id "
        "WHERE c.stagione = ? AND c.data = ? ORDER BY c.ora", conn, params=(stagione, giorno))
