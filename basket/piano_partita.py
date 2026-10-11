"""Piano partita: consigli concreti su come affrontare una squadra, ricavati dai suoi dati.

Ogni consiglio nasce da una regola esplicita: una voce della squadra lontana dalla media del
campionato (almeno SOGLIA_Z deviazioni standard) diventa un'indicazione per lo staff, con il
numero che la giustifica. I consigli sono divisi in quattro gruppi (difesa, attacco, ritmo e
momenti, finali) e ordinati per quanto la voce si discosta dalla media.

Come le chiavi per vincere, sono associazioni osservate nei dati, non certezze.
"""

import re

import numpy as np
import pandas as pd

SOGLIA_Z = 0.6          # distanza minima dalla media del campionato, in deviazioni standard
MAX_PER_GRUPPO = 6

GRUPPI = ["In difesa · contro il loro attacco", "In attacco · contro la loro difesa",
          "Ritmo, rotazioni e momenti", "Finali punto a punto"]


def _it(v, d=1, signed=False) -> str:
    s = f"{v:+.{d}f}" if signed else f"{v:.{d}f}"
    return s.replace(".", ",")


def _volte(n: int) -> str:
    return "1 volta" if n == 1 else f"{n} volte"


def _cognome(nome: str) -> str:
    return nome.split()[-1] if isinstance(nome, str) and " " in nome else str(nome)


class _Lega:
    """Posizione e distanza dalla media di una squadra per ogni voce del profilo."""

    def __init__(self, lega: pd.DataFrame, sid: int):
        self.lega = lega.set_index("squadra_id")
        self.sid = sid
        self.n = len(self.lega)

    def v(self, col):
        return self.lega.loc[self.sid].get(col, np.nan) if col in self.lega else np.nan

    def z(self, col) -> float:
        if col not in self.lega:
            return 0.0
        s = self.lega[col].astype(float)
        sd = s.std()
        v = self.v(col)
        return 0.0 if pd.isna(v) or not sd or pd.isna(sd) else float((v - s.mean()) / sd)

    def media(self, col):
        return float(self.lega[col].mean())

    def pos(self, col, alto_primo=True) -> str:
        r = self.lega[col].rank(ascending=not alto_primo, method="min")[self.sid]
        return f"{int(r)}° su {self.n}"


def consigli(ctx, avv: int, mia: int | None = None, rt: pd.DataFrame | None = None
             ) -> dict[str, list[str]]:
    """Consigli per affrontare avv, divisi per gruppo. rt (da chiavi.ritmo) aggiunge il ritmo
    che conviene alla propria squadra."""
    prof = ctx.profile
    camp = prof.set_index("squadra_id").loc[avv, "campionato_id"]
    L = _Lega(prof[prof["campionato_id"] == camp], avv)
    nome = ctx.nomi_squadre.get(avv, str(avv))
    breve = _cognome(nome)
    gruppi = {g: [] for g in GRUPPI}

    def add(g, peso, testo):
        gruppi[g].append((abs(peso), testo))

    pl = ctx.players[(ctx.players["squadra_id"] == avv) & (ctx.players["minuti_pg"] >= 10)]
    lega_pl = ctx.players[(ctx.players["campionato_id"] == camp) &
                          (ctx.players["minuti_pg"] >= 10)]
    D, A, R, F = GRUPPI

    # ------------------------------------------------ in difesa
    z3 = L.z("quota_punti_3")
    if z3 >= SOGLIA_Z:
        t3_lega = lega_pl["t3m"].sum() / max(1, lega_pl["t3a"].sum()) * 100
        tiratori = pl[(pl["t3a_pg"] >= 2.5) & (pl["t3_pct"] >= t3_lega - 2)].sort_values(
            "t3m_pg", ascending=False).head(3)
        chi = ", ".join(f"{_cognome(x.giocatore)} ({_it(x.t3m_pg)}/{_it(x.t3a_pg)} a partita, "
                        f"{_it(x.t3_pct, 0)}%)" for x in tiratori.itertuples())
        add(D, z3, f"Vivono del tiro da 3 ({_it(L.v('quota_punti_3'), 0)}% dei punti, "
                   f"{L.pos('quota_punti_3')}): chiusure aggressive e niente aiuti lunghi dal "
                   f"lato forte" + (f". Pericolosi: {chi}" if chi else ""))
    elif z3 <= -SOGLIA_Z:
        add(D, z3, f"Tirano poco da 3 ({_it(L.v('quota_punti_3'), 0)}% dei punti, media "
                   f"{_it(L.media('quota_punti_3'), 0)}%): difesa più stretta, aiuti presto "
                   "sulle penetrazioni e protezione dell'area")
    z = L.z("orb_pct")
    if z >= SOGLIA_Z:
        add(D, z, f"Forti a rimbalzo offensivo ({_it(L.v('orb_pct'))}%, {L.pos('orb_pct')}): "
                  "tagliafuori su ogni tiro, anche degli esterni, e niente uscite in contropiede "
                  "prima di avere la palla")
    z = L.z("ft_rate")
    if z >= SOGLIA_Z:
        caccia = pl.sort_values("falli_subiti_pg", ascending=False).head(2)
        chi = " e ".join(f"{_cognome(x.giocatore)} ({_it(x.falli_subiti_pg)} falli subiti a "
                         "partita)" for x in caccia.itertuples())
        add(D, z, f"Vanno spesso in lunetta (liberi/tiri {_it(L.v('ft_rate'), 2)}, "
                  f"{L.pos('ft_rate')}): difendere con i piedi, niente falli sulle penetrazioni"
                  + (f"; chi cerca il contatto: {chi}" if chi else ""))
    z = L.z("punti_contropiede_pg")
    if z >= SOGLIA_Z:
        add(D, z, f"Pericolosi in transizione ({_it(L.v('punti_contropiede_pg'))} punti a "
                  f"partita in contropiede, {L.pos('punti_contropiede_pg')}): due giocatori "
                  "sempre pronti a rientrare dopo il tiro, fermare il primo passaggio")
    z = L.z("punti_da_perse_pg")
    if z >= SOGLIA_Z:
        add(D, z, f"Puniscono le palle perse ({_it(L.v('punti_da_perse_pg'))} punti a partita, "
                  f"{L.pos('punti_da_perse_pg')}): attacco ordinato, niente passaggi in mezzo "
                  "al traffico")
    z = L.z("quota_top2")
    if z >= SOGLIA_Z and not pl.empty:
        top = pl.sort_values("punti_pg", ascending=False).head(2)
        chi = " e ".join(f"{_cognome(x.giocatore)} ({_it(x.punti_pg)} punti)"
                         for x in top.itertuples())
        add(D, z, f"Due giocatori fanno il {_it(L.v('quota_top2'), 0)}% dei punti: {chi}. "
                  "Difesa dedicata su di loro e far prendere i tiri agli altri")
    elif z <= -SOGLIA_Z:
        add(D, z, f"Punti distribuiti tra molti giocatori (i primi due fanno solo il "
                  f"{_it(L.v('quota_top2'), 0)}%): difesa di squadra più che marcature "
                  "speciali")
    z = L.z("ast_su_canestri")
    if z >= SOGLIA_Z:
        add(D, z, f"Squadra che passa molto ({_it(L.v('ast_su_canestri'), 0)}% di canestri "
                  "assistiti): pressione sulle linee di passaggio e sul portatore")
    elif z <= -SOGLIA_Z:
        add(D, z, f"Giocano molto in uno contro uno ({_it(L.v('ast_su_canestri'), 0)}% di "
                  "canestri assistiti): aiuti pronti e costringere i palleggiatori verso il "
                  "lato debole")
    mig = _quintetti(ctx, avv)[0]
    if not mig.empty:
        q = mig.iloc[0]
        add(D, 0.7, f"Il loro quintetto migliore ({q['giocatori']}, "
                    f"{_it(q['net_rtg'], 0, True)} di Net rating in {_it(q['minuti'], 0)}') va "
                    "spezzato: preparare i cambi difensivi per quando entra")

    # ------------------------------------------------ in attacco
    z = L.z("opp_efg_pct")
    if z >= SOGLIA_Z:
        add(A, z, f"Concedono tiri facili (eFG% concessa {_it(L.v('opp_efg_pct'))}%, "
                  f"{L.pos('opp_efg_pct', False)} per difesa): muovere la palla e prendere "
                  "tiri aperti, senza fretta")
    elif z <= -SOGLIA_Z:
        add(A, z, f"Difesa che concede poco al tiro (eFG% concessa "
                  f"{_it(L.v('opp_efg_pct'))}%, {L.pos('opp_efg_pct', False)}): pazienza, "
                  "extra-passaggio e cercare la lunetta e i rimbalzi offensivi")
    z = L.z("opp_tov_pct")
    if z >= SOGLIA_Z:
        add(A, z, f"Difesa aggressiva che forza palle perse ({_it(L.v('opp_tov_pct'))}%, "
                  f"{L.pos('opp_tov_pct')}): due portatori, passaggi corti, contro la pressione "
                  "attaccare in fretta il centro del campo")
    elif z <= -SOGLIA_Z:
        add(A, z, f"Forzano poche palle perse ({_it(L.v('opp_tov_pct'))}%): si può attaccare "
                  "in uno contro uno e in pick and roll senza grandi rischi")
    z = -L.z("drb_pct")
    if z >= SOGLIA_Z:
        add(A, z, f"Soffrono a rimbalzo difensivo ({_it(L.v('drb_pct'))}%, "
                  f"{L.pos('drb_pct')}): mandare a rimbalzo offensivo anche un'ala, ogni "
                  "secondo tiro vale")
    z = L.z("opp_ft_rate")
    if z >= SOGLIA_Z:
        add(A, z, f"Fanno molti falli (liberi concessi/tiri {_it(L.v('opp_ft_rate'), 2)}, "
                  f"{L.pos('opp_ft_rate')}): attaccare il ferro e il corpo del difensore")
    z = -L.z("minuto_medio_bonus")
    if z >= SOGLIA_Z and pd.notna(L.v("minuto_medio_bonus")):
        add(A, z, f"Vanno in bonus presto (5° fallo di squadra in media al "
                  f"{_it(L.v('minuto_medio_bonus'))}' del quarto): nella seconda metà dei "
                  "quarti attaccare il canestro per andare in lunetta")
    oc = ctx.origini_concesse
    if oc is not None and not oc.empty and avv in set(oc["squadra_id"]):
        lega_oc = oc[oc["campionato_id"] == camp]
        Lo = _Lega(lega_oc, avv)
        z = Lo.z("concessi_contropiede_pg")
        if z >= SOGLIA_Z:
            add(A, z, f"Rientrano male in difesa ({_it(Lo.v('concessi_contropiede_pg'))} punti "
                      "concessi in contropiede a partita): correre dopo ogni rimbalzo e palla "
                      "recuperata")
        z = Lo.z("concessi_seconda_occasione_pg")
        if z >= SOGLIA_Z:
            add(A, z, f"Concedono seconde occasioni "
                      f"({_it(Lo.v('concessi_seconda_occasione_pg'))} punti a partita): "
                      "insistere a rimbalzo offensivo")
    fo = ctx.fouls
    if fo is not None and not fo.empty:
        f = fo[(fo["squadra_id"] == avv) & (fo["partite_problemi"] > 0)].sort_values(
            "partite_problemi", ascending=False).head(2)
        if not f.empty:
            chi = ", ".join(f"{_cognome(x.giocatore)} ({_volte(int(x.partite_problemi))})"
                            for x in f.itertuples())
            add(A, 0.8, f"Spesso in difficoltà con i falli: {chi}. Attaccarli dal primo quarto "
                        "in post e in uno contro uno")
    pegg = _quintetti(ctx, avv)[1]
    if not pegg.empty:
        q = pegg.iloc[0]
        add(A, 0.7, f"Quando giocano con {q['giocatori']} ({_it(q['net_rtg'], 0, True)} di Net "
                    f"rating in {_it(q['minuti'], 0)}') rendono peggio: è il momento di "
                    "spingere")

    # ------------------------------------------------ ritmo, rotazioni e momenti
    if rt is not None and not rt.empty and mia is not None:
        lento, veloce = rt.iloc[0], rt.iloc[-1]
        meglio = lento if lento["prob"] >= veloce["prob"] else veloce
        tipo = "più lenta" if meglio is lento else "più veloce"
        diff = abs(lento["prob"] - veloce["prob"])
        add(R, 1 + diff / 5, f"Conviene una partita {tipo}: {_it(meglio['prob'], 0)}% di "
                             f"probabilità con {_it(meglio['possessi'], 0)} possessi contro "
                             f"{_it((veloce if meglio is lento else lento)['prob'], 0)}%"
                             + (" (attacchi lunghi, rimessa in gioco senza fretta)"
                                if meglio is lento else " (correre dopo ogni rimbalzo, "
                                                        "rimesse veloci)"))
    z = L.z("pace")
    if abs(z) >= SOGLIA_Z:
        add(R, z, f"Il loro ritmo è {'alto' if z > 0 else 'basso'} ({_it(L.v('pace'))} possessi "
                  f"per 40', {L.pos('pace')})")
    m = ctx.momenti
    if m is not None and not m.empty and avv in set(m["squadra_id"]):
        mm = m[m["squadra_id"] == avv]
        peg = mm.sort_values("diff_pg").iloc[0]
        mig_ = mm.sort_values("diff_pg").iloc[-1]
        if peg["diff_pg"] < -1.5:
            add(R, -peg["diff_pg"] / 3, f"Calano in: {peg['etichetta'].lower()} "
                                        f"({_it(peg['diff_pg'], 1, True)} a partita, "
                                        f"{peg['posizione']}° su {peg['squadre']}): è lì che si "
                                        "può fare la differenza")
        if mig_["diff_pg"] > 1.5:
            add(R, mig_["diff_pg"] / 3, f"Partono forte in: {mig_['etichetta'].lower()} "
                                        f"({_it(mig_['diff_pg'], 1, True)} a partita): "
                                        "attenzione in quel momento, timeout presto se allungano")
    rot = ctx.rotazioni["squadre"] if ctx.rotazioni else pd.DataFrame()
    if not rot.empty and avv in set(rot["squadra_id"]):
        s = rot.set_index("squadra_id").loc[avv]
        lega_rot = rot[rot["squadra_id"].isin(L.lega.index)]
        zr = (s["giocatori_rotazione"] - lega_rot["giocatori_rotazione"].mean()) / \
            (lega_rot["giocatori_rotazione"].std() or 1)
        if zr <= -SOGLIA_Z:
            add(R, zr, f"Rotazione corta ({_it(s['giocatori_rotazione'])} giocatori con almeno "
                       "5'): alzare l'intensità e il ritmo per stancare i titolari nel secondo "
                       "tempo")
        add(R, 0.5, f"Primo cambio in media al minuto {_it(s['minuto_primo_cambio'])}; "
                    f"quintetto base nel {_it(s['quota_quintetto_base'], 0)}% delle partite")
    z = -L.z("quota_punti_panchina")
    if z >= SOGLIA_Z:
        add(R, z, f"Panchina poco produttiva ({_it(L.v('quota_punti_panchina'), 0)}% dei punti): "
                  "spingere quando riposano i titolari")
    z = L.z("break_fatti_pg")
    if z >= SOGLIA_Z:
        add(R, z, f"Fanno parziali ({_it(L.v('break_fatti_pg'))} break da 8-0 a partita, "
                  f"massimo {_it(L.v('max_fatto'), 0)}-0): fermarli subito con un timeout")
    z = L.z("diff_dopo")
    if z >= SOGLIA_Z:
        add(R, z, f"Escono bene dai loro timeout ({_it(L.v('diff_dopo'), 1, True)} punti nei 2' "
                  "successivi): attenzione alla prima azione dopo il timeout, chiamare la "
                  "difesa prima di rientrare")

    # ------------------------------------------------ finali punto a punto
    ct, cp = ctx.clutch_teams, ctx.clutch_players
    if ct is not None and not ct.empty and avv in set(ct["squadra_id"]):
        c = ct.set_index("squadra_id").loc[avv]
        add(F, 1, f"Finali punto a punto: record {c['record_clutch']} in "
                  f"{int(c['partite_clutch'])} {'partita' if int(c['partite_clutch']) == 1 else 'partite'}")
        if cp is not None and not cp.empty:
            chi = cp[cp["squadra_id"] == avv].sort_values("quota_tiri", ascending=False)
            if not chi.empty and chi["quota_tiri"].iloc[0] >= 25:
                x = chi.iloc[0]
                add(F, 1, f"Nei finali la palla va a {_cognome(x['giocatore'])} "
                          f"({_it(x['quota_tiri'], 0)}% dei tiri, {int(x['fgm'])}/{int(x['fga'])}"
                          "): anticipare la ricezione e raddoppiare in uscita dai blocchi")
    tl_lega = lega_pl["tlm"].sum() / max(1, lega_pl["tla"].sum()) * 100
    scarsi = pl[(pl["minuti_pg"] >= 20) & (pl["tla"] >= 8) & (pl["tl_pct"] < tl_lega - 12)]
    if not scarsi.empty:
        x = scarsi.sort_values("tl_pct").iloc[0]
        add(F, 0.9, f"In vantaggio nel finale si può mandare in lunetta "
                    f"{_cognome(x['giocatore'])} ({_it(x['tl_pct'], 0)}% ai liberi, media "
                    f"{_it(tl_lega, 0)}%)")
    bravi = pl[(pl["minuti_pg"] >= 15) & (pl["tla"] >= 8)].sort_values("tl_pct", ascending=False)
    if not bravi.empty and bravi["tl_pct"].iloc[0] >= 85:
        x = bravi.iloc[0]
        add(F, 0.6, f"Da non mandare in lunetta nel finale: {_cognome(x['giocatore'])} "
                    f"({_it(x['tl_pct'], 0)}% ai liberi)")

    return {g: [t for _, t in sorted(v, key=lambda p: -p[0])][:MAX_PER_GRUPPO]
            for g, v in gruppi.items()}


def _quintetti(ctx, sid):
    from . import miglioramento as M
    mig, peg, _ = M.quintetti_estremi(ctx.lineups, sid, n=1)
    return mig, peg


def testo_semplice(t: str) -> str:
    """Spazi singoli (le frasi sono composte da più pezzi)."""
    return re.sub(r"\s+", " ", t).strip()
