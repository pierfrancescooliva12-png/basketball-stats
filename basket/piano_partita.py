"""Piano partita: consigli concreti su come affrontare una squadra, ricavati dai dati delle due
squadre.

Ogni consiglio nasce da una regola esplicita. Una voce lontana dalla media del campionato
(almeno SOGLIA_Z deviazioni standard) diventa un'indicazione, con il numero che la giustifica.
Con la propria squadra le regole mettono a confronto le due squadre sulla stessa voce:

- sfida chiave: un loro punto forte contro un vostro punto debole (o il contrario, in attacco);
- occasione: un vostro punto forte contro un loro punto debole;
- neutralizzata: un loro punto forte dove però siete forti anche voi;
- forza contro forza: in attacco, un vostro punto forte contro un loro punto forte;
- vostro punto forte: un'arma vostra che la loro difesa non toglie;
- da curare: un vostro punto debole che loro possono sfruttare anche senza eccellere.

I consigli sono divisi in quattro gruppi e ordinati per importanza (somma delle distanze dalla
media delle due squadre). Sono associazioni osservate nei dati, non certezze.
"""

import numpy as np
import pandas as pd

SOGLIA_Z = 0.6          # distanza minima dalla media del campionato, in deviazioni standard
MAX_PER_GRUPPO = 6

GRUPPI = ["In difesa · contro il loro attacco", "In attacco · contro la loro difesa",
          "Ritmo, rotazioni e momenti", "Finali punto a punto"]
D, A, R, F = GRUPPI


def _it(v, d=1, signed=False) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    s = f"{v:+.{d}f}" if signed else f"{v:.{d}f}"
    return s.replace(".", ",")


def _volte(n: int) -> str:
    return "1 volta" if n == 1 else f"{n} volte"


def _cognome(nome: str) -> str:
    return nome.split()[-1] if isinstance(nome, str) and " " in nome else str(nome)


def _con_tiri_concessi(lega: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge 3P% concessa e quota di tiri da 3 concessi."""
    lega = lega.copy()
    if {"opp_t3m", "opp_t3a", "opp_t2a"} <= set(lega.columns):
        lega["opp_t3_pct"] = 100 * lega["opp_t3m"] / lega["opp_t3a"].where(lega["opp_t3a"] > 0)
        lega["opp_quota_3"] = 100 * lega["opp_t3a"] / (lega["opp_t2a"] + lega["opp_t3a"])
    if {"t3a", "t2a"} <= set(lega.columns):
        lega["quota_tiri_3"] = 100 * lega["t3a"] / (lega["t2a"] + lega["t3a"])
    return lega


class _Lega:
    """Valore, posizione e distanza dalla media di una squadra per ogni voce."""

    def __init__(self, lega: pd.DataFrame, sid):
        self.lega = lega.set_index("squadra_id")
        self.sid = sid
        self.n = len(self.lega)
        self.ok = sid is not None and sid in self.lega.index

    def v(self, col):
        if not self.ok or col not in self.lega:
            return np.nan
        return self.lega.loc[self.sid, col]

    def z(self, col) -> float:
        if not self.ok or col not in self.lega:
            return 0.0
        s = self.lega[col].astype(float)
        sd, v = s.std(), self.v(col)
        return 0.0 if pd.isna(v) or not sd or pd.isna(sd) else float((v - s.mean()) / sd)

    def pg(self, col):
        """Valore totale della stagione diviso per le partite giocate."""
        g = self.v("partite")
        return self.v(col) / g if g and not pd.isna(g) else np.nan

    def media(self, col):
        return float(self.lega[col].mean())

    def pos(self, col, alto_primo=True) -> str:
        if not self.ok or col not in self.lega or pd.isna(self.v(col)):
            return "–"
        r = self.lega[col].rank(ascending=not alto_primo, method="min")[self.sid]
        return f"{int(r)}° su {self.n}"


class _Piano:
    def __init__(self):
        self.gruppi = {g: [] for g in GRUPPI}

    def add(self, g, peso, testo, tipo=""):
        etichetta = {"sfida": "<b>Sfida chiave</b> · ", "occasione": "<b>Occasione</b> · ",
                     "neutra": "<b>Neutralizzata</b> · ", "curare": "<b>Da curare</b> · ",
                     "forza": "<b>Forza contro forza</b> · ",
                     "forte": "<b>Vostro punto forte</b> · "}
        self.gruppi[g].append((abs(peso), etichetta.get(tipo, "") + testo))

    def duello(self, g, zl, zn, loro, entrambi=None, neutra=None, curare=None, forza=None,
               tipo_curare=None):
        """zl: quanto la voce è marcata per loro (positivo = loro punto forte in attacco, o loro
        debolezza difensiva da sfruttare); zn: quanto è marcata per voi nella stessa direzione
        (in difesa positivo = vostro punto debole; in attacco positivo = vostro punto forte).
        forza: in attacco, vostro punto forte contro un loro punto forte."""
        if zl >= SOGLIA_Z and zn >= SOGLIA_Z and entrambi:
            self.add(g, zl + zn + 1, entrambi, "sfida" if g == D else "occasione")
        elif zl <= -SOGLIA_Z and zn >= SOGLIA_Z and forza:
            self.add(g, (zn - zl) * 0.7, forza, "forza")
        elif zl >= SOGLIA_Z and zn <= -SOGLIA_Z and neutra:
            self.add(g, (zl - zn) * 0.5, neutra, "neutra")
        elif zl >= SOGLIA_Z and loro:
            self.add(g, zl, loro)
        elif zn >= 1.0 and zl > -SOGLIA_Z and curare:
            self.add(g, zn * 0.8, curare, tipo_curare or ("curare" if g == D else "forte"))


def _n(X: "_Lega", tipo: str) -> float:
    """Numero a partita. Palle perse sulle azioni (possessi delle partite con box score
    completo + rimbalzi offensivi), così coincidono con la percentuale; rimbalzi dai box score."""
    if tipo == "perse":         # azioni = possessi + rimbalzi offensivi
        return X.v("tov_pct") / 100 * (X.v("pace") + X.pg("rimb_off"))
    if tipo == "forzate":
        return X.v("opp_tov_pct") / 100 * (X.v("pace") + X.pg("opp_rimb_off"))
    return X.pg({"orb": "rimb_off", "orb_concessi": "opp_rimb_off", "drb": "rimb_dif"}[tipo])


def _q(X: "_Lega", tipo: str) -> str:
    """Numero a partita con la percentuale (più facile da usare come obiettivo in panchina)."""
    n = _it(_n(X, tipo))
    if tipo == "perse":
        return f"{n} palle perse a partita, il {_it(X.v('tov_pct'))}% delle azioni"
    if tipo == "forzate":
        return f"{n} palle perse a partita agli avversari, il {_it(X.v('opp_tov_pct'))}% delle loro azioni"
    if tipo == "orb":
        return f"{n} rimbalzi offensivi a partita, il {_it(X.v('orb_pct'))}% dei tiri sbagliati"
    if tipo == "orb_concessi":
        return (f"{n} rimbalzi offensivi concessi a partita, il "
                f"{_it(100 - X.v('drb_pct'))}% dei tiri sbagliati avversari")
    if tipo == "drb":
        return (f"{n} rimbalzi difensivi a partita, il {_it(X.v('drb_pct'))}% dei tiri "
                "sbagliati avversari")
    raise ValueError(tipo)


def consigli(ctx, avv: int, mia: int | None = None, rt: pd.DataFrame | None = None
             ) -> dict[str, list[str]]:
    """Consigli per affrontare avv, divisi per gruppo. Con mia (stessa lega) ogni voce
    dell'avversaria è messa a confronto con la stessa voce della propria squadra; rt (da
    chiavi.ritmo) aggiunge il ritmo che conviene."""
    prof = ctx.profile
    camp = prof.set_index("squadra_id").loc[avv, "campionato_id"]
    lega = _con_tiri_concessi(prof[prof["campionato_id"] == camp])
    if mia is not None and (mia == avv or mia not in set(lega["squadra_id"])):
        mia = None
    L, N = _Lega(lega, avv), _Lega(lega, mia)
    noi = mia is not None
    P = _Piano()

    pl_all = ctx.players[ctx.players["minuti_pg"] >= 10]
    pl = pl_all[pl_all["squadra_id"] == avv]
    pn = pl_all[pl_all["squadra_id"] == mia] if noi else pl.iloc[0:0]
    lega_pl = pl_all[pl_all["campionato_id"] == camp]
    t3_lega = lega_pl["t3m"].sum() / max(1, lega_pl["t3a"].sum()) * 100
    tl_lega = lega_pl["tlm"].sum() / max(1, lega_pl["tla"].sum()) * 100
    oc = ctx.origini_concesse
    oc = oc[oc["campionato_id"] == camp] if oc is not None and not oc.empty else pd.DataFrame()
    Lo, No = _Lega(oc, avv) if not oc.empty else None, _Lega(oc, mia) if not oc.empty else None

    def zc(Lx, col):
        return Lx.z(col) if Lx is not None else 0.0

    # ================================================ in difesa (loro attacco, vostra difesa)
    tiratori = pl[(pl["t3a_pg"] >= 2.5) & (pl["t3_pct"] >= t3_lega - 2)].sort_values(
        "t3m_pg", ascending=False).head(3)
    chi3 = ", ".join(f"{_cognome(x.giocatore)} ({_it(x.t3m_pg)}/{_it(x.t3a_pg)}, "
                     f"{_it(x.t3_pct, 0)}%)" for x in tiratori.itertuples())
    chi3 = f". Pericolosi: {chi3}" if chi3 else ""
    q3 = f"{_it(L.v('quota_punti_3'), 0)}% dei punti da 3, {L.pos('quota_punti_3')}" if L.ok \
        else ""
    c3 = f"{_it(N.v('opp_t3_pct'), 1)}% da 3 concesso, {N.pos('opp_t3_pct', False)}" if noi \
        else ""
    P.duello(D, L.z("quota_punti_3"), N.z("opp_t3_pct"),
             f"Vivono del tiro da 3 ({q3}): chiusure aggressive, niente aiuti lunghi dal lato "
             f"forte{chi3}",
             f"Il tiro da 3 è la loro arma ({q3}) e il vostro punto debole in difesa ({c3}): "
             f"chiusure in anticipo, cambiare sui blocchi lontano dalla palla{chi3}",
             f"Tirano molto da 3 ({q3}), ma voi difendete bene il perimetro ({c3}): restare "
             f"attaccati ai tiratori e non concedere penetrazioni{chi3}",
             f"Concedete molto da 3 ({c3}): anche contro una squadra che non ne vive, chiusure "
             "sui loro tiratori migliori")
    if L.z("quota_punti_3") <= -SOGLIA_Z:
        P.add(D, -L.z("quota_punti_3"),
              f"Tirano poco da 3 ({q3}): difesa più stretta, aiuti presto sulle penetrazioni e "
              "protezione dell'area")

    P.duello(D, L.z("orb_pct"), -N.z("drb_pct"),
             f"Forti a rimbalzo offensivo ({_q(L, 'orb')}, {L.pos('orb_pct')}): tagliafuori "
             "su ogni tiro, anche degli esterni",
             f"Rimbalzo difensivo: loro prendono {_q(L, 'orb')} ({L.pos('orb_pct')}), voi "
             f"concedete {_q(N, 'orb_concessi')} ({N.pos('drb_pct')} in difesa). Obiettivo: "
             f"tenerli sotto i {_it(_n(N, 'orb_concessi'), 0)} a partita con il tagliafuori di "
             "tutti e cinque, nessuno parte in contropiede prima del rimbalzo",
             f"Forti a rimbalzo offensivo ({_q(L, 'orb')}), ma voi siete tra i migliori a "
             f"rimbalzo difensivo ({_q(N, 'drb')}, {N.pos('drb_pct')}): mantenere il "
             "tagliafuori e il vantaggio è vostro",
             f"Concedete troppi rimbalzi offensivi ({_q(N, 'orb_concessi')}, "
             f"{N.pos('drb_pct')} a rimbalzo difensivo): tagliafuori come priorità della "
             "settimana")

    caccia = pl.sort_values("falli_subiti_pg", ascending=False).head(2)
    chi_ft = " e ".join(f"{_cognome(x.giocatore)} ({_it(x.falli_subiti_pg)} falli subiti a "
                        "partita)" for x in caccia.itertuples())
    P.duello(D, L.z("ft_rate"), N.z("opp_ft_rate"),
             f"Vanno spesso in lunetta (liberi/tiri {_it(L.v('ft_rate'), 2)}, "
             f"{L.pos('ft_rate')}): difendere con i piedi; chi cerca il contatto: {chi_ft}",
             f"Lunetta: loro ci vanno spesso ({_it(L.v('ft_rate'), 2)}, "
             f"{L.pos('ft_rate')}) e voi fate molti falli ({_it(N.v('opp_ft_rate'), 2)} "
             f"concessi, {N.pos('opp_ft_rate')}): niente mani addosso, aiuti in verticalità; "
             f"chi cerca il contatto: {chi_ft}",
             f"Vanno spesso in lunetta ({_it(L.v('ft_rate'), 2)}), ma voi concedete pochi liberi "
             f"({N.pos('opp_ft_rate', False)} per meno liberi): continuare a difendere senza "
             "fallo",
             f"Fate molti falli ({_it(N.v('opp_ft_rate'), 2)} liberi concessi per tiro, "
             f"{N.pos('opp_ft_rate')}): occhio al bonus, difendere con i piedi")

    if Lo is not None and Lo.ok:
        P.duello(D, L.z("punti_contropiede_pg"), zc(No, "concessi_contropiede_pg"),
                 f"Pericolosi in transizione ({_it(L.v('punti_contropiede_pg'))} punti a partita "
                 "in contropiede): due giocatori sempre pronti a rientrare dopo il tiro",
                 f"Transizione: loro segnano {_it(L.v('punti_contropiede_pg'))} "
                 f"punti in contropiede ({L.pos('punti_contropiede_pg')}) e voi ne concedete "
                 f"{_it(No.v('concessi_contropiede_pg'))} a partita: rientro di tutti e cinque, "
                 "fermare il primo passaggio, fallo tattico se serve",
                 f"Corrono molto ({_it(L.v('punti_contropiede_pg'))} punti in contropiede), ma voi "
                 "rientrate bene: mantenere l'equilibrio dopo il tiro",
                 f"Concedete molti punti in contropiede "
                 f"({_it(No.v('concessi_contropiede_pg'))} a partita): equilibrio difensivo dopo "
                 "ogni tiro")
    P.duello(D, L.z("punti_da_perse_pg"), N.z("tov_pct"),
             f"Puniscono le palle perse ({_it(L.v('punti_da_perse_pg'))} punti a partita, "
             f"{L.pos('punti_da_perse_pg')}): attacco ordinato, niente passaggi in mezzo al "
             "traffico",
             f"Palle perse: loro segnano {_it(L.v('punti_da_perse_pg'))} punti a partita dalle "
             f"palle perse avversarie e voi ne perdete {_q(N, 'perse')}, {N.pos('tov_pct')}. "
             f"Obiettivo: sotto le {_it(_n(N, 'perse') - 2, 0)}, con passaggi semplici e la "
             "palla al portatore più sicuro",
             None,
             f"Perdete molti palloni ({_q(N, 'perse')}, {N.pos('tov_pct')}): contro di loro "
             "costano punti, priorità alla gestione della palla")
    P.duello(D, L.z("tov_pct"), N.z("opp_tov_pct"),
             f"Perdono molti palloni ({_q(L, 'perse')}, {L.pos('tov_pct')}): pressione sul "
             "portatore e sulle linee di passaggio",
             f"Pressione: loro perdono {_q(L, 'perse')} ({L.pos('tov_pct')}) e voi ne forzate "
             f"{_q(N, 'forzate')} ({N.pos('opp_tov_pct')}). Obiettivo: almeno "
             f"{_it(max(_n(L, 'perse'), _n(N, 'forzate')) + 1, 0)} palle perse loro, con "
             "trappole sul portatore e pressione a tutto campo nei momenti giusti")

    if L.z("quota_top2") >= SOGLIA_Z and not pl.empty:
        top = pl.sort_values("punti_pg", ascending=False).head(2)
        chi = " e ".join(f"{_cognome(x.giocatore)} ({_it(x.punti_pg)} punti)"
                         for x in top.itertuples())
        P.add(D, L.z("quota_top2"), f"Due giocatori fanno il {_it(L.v('quota_top2'), 0)}% dei "
                                    f"punti: {chi}. Difesa dedicata su di loro e far prendere i "
                                    "tiri agli altri")
    elif L.z("quota_top2") <= -SOGLIA_Z:
        P.add(D, L.z("quota_top2"), f"Punti distribuiti tra molti giocatori (i primi due fanno "
                                    f"il {_it(L.v('quota_top2'), 0)}%): difesa di squadra più "
                                    "che marcature speciali")
    mig, peg = _quintetti(ctx, avv)
    if not mig.empty:
        q = mig.iloc[0]
        P.add(D, 0.7, f"Il loro quintetto migliore ({q['giocatori']}, "
                      f"{_it(q['net_rtg'], 0, True)} di Net rating in {_it(q['minuti'], 0)}') "
                      "va spezzato: preparare i cambi difensivi per quando entra")

    # ================================================ in attacco (vostro attacco, loro difesa)
    vs = "la vostra eFG%" if noi else ""
    P.duello(A, L.z("opp_efg_pct"), N.z("efg_pct"),
             f"Concedono tiri facili (eFG% concessa {_it(L.v('opp_efg_pct'))}%, "
             f"{L.pos('opp_efg_pct', False)} per difesa): muovere la palla e prendere tiri "
             "aperti, senza fretta",
             f"Tiro: il vostro attacco è tra i più efficaci ({vs} {_it(N.v('efg_pct'))}%, "
             f"{N.pos('efg_pct')}) e la loro difesa concede molto "
             f"({_it(L.v('opp_efg_pct'))}%, {L.pos('opp_efg_pct', False)}): giocare il vostro "
             "attacco abituale, cercare i tiri migliori",
             curare=f"Il vostro tiro è tra i migliori del campionato (eFG% "
                    f"{_it(N.v('efg_pct'))}%, {N.pos('efg_pct')}): costruire tiri per chi è in "
                    "forma e non accontentarsi del primo tiro")
    if L.z("opp_efg_pct") <= -SOGLIA_Z:
        tt = (f", contro il vostro attacco al {_it(N.v('efg_pct'))}% ({N.pos('efg_pct')})"
              if noi else "")
        P.add(A, -L.z("opp_efg_pct") + max(0, N.z("efg_pct")),
              f"Difesa che concede poco al tiro (eFG% concessa {_it(L.v('opp_efg_pct'))}%, "
              f"{L.pos('opp_efg_pct', False)}){tt}: pazienza, extra-passaggio, cercare la "
              "lunetta e i rimbalzi offensivi", "sfida" if N.z("efg_pct") >= SOGLIA_Z else "")
    tir = pn[(pn["t3a_pg"] >= 2.5)].sort_values("t3_pct", ascending=False).head(2)
    nostri3 = ", ".join(f"{_cognome(x.giocatore)} ({_it(x.t3_pct, 0)}%)"
                        for x in tir.itertuples())
    P.duello(A, L.z("opp_t3_pct"), N.z("t3_pct"),
             f"Concedono molto da 3 ({_it(L.v('opp_t3_pct'))}% ai loro avversari, "
             f"{L.pos('opp_t3_pct')}): cercare i tiratori dopo la penetrazione e lo scarico",
             f"Tiro da 3: voi tirate con il {_it(N.v('t3_pct'))}% ({N.pos('t3_pct')}) e loro ne "
             f"concedono il {_it(L.v('opp_t3_pct'))}% ({L.pos('opp_t3_pct')}): spaziature "
             f"larghe e palla ai tiratori" + (f" ({nostri3})" if nostri3 else ""),
             curare=f"Tirate bene da 3 ({_it(N.v('t3_pct'))}%, {N.pos('t3_pct')}): "
                    "spaziature larghe e scarichi dopo la penetrazione"
                    + (f" ({nostri3})" if nostri3 else ""),
             forza=f"Tiro da 3: voi tirate con il {_it(N.v('t3_pct'))}% "
                   f"({N.pos('t3_pct')}), loro concedono solo il {_it(L.v('opp_t3_pct'))}% "
                   f"({L.pos('opp_t3_pct', False)} per difesa): tiri da 3 solo dopo "
                   "ribaltamento o extra-passaggio")
    P.duello(A, -L.z("drb_pct"), N.z("orb_pct"),
             f"Soffrono a rimbalzo difensivo (concedono "
             f"{_it(_n(L, 'orb_concessi'))} rimbalzi offensivi a partita, {L.pos('drb_pct')}): "
             "mandare a rimbalzo offensivo anche un'ala",
             f"Rimbalzo offensivo: voi prendete {_q(N, 'orb')} ({N.pos('orb_pct')}) e loro ne "
             f"concedono {_it(_n(L, 'orb_concessi'))} a partita ({L.pos('drb_pct')} a rimbalzo "
             f"difensivo). Obiettivo: almeno {_it(max(_n(N, 'orb'), _n(L, 'orb_concessi')) + 1, 0)} "
             "rimbalzi offensivi, crash con quattro giocatori",
             curare=f"Il rimbalzo offensivo è una vostra arma ({_q(N, 'orb')}, "
                    f"{N.pos('orb_pct')}): continuare a mandare i lunghi e un'ala a rimbalzo",
             forza=f"Rimbalzo offensivo: voi prendete {_q(N, 'orb')} ({N.pos('orb_pct')}), loro "
                   f"sono tra i migliori a rimbalzo difensivo ({_q(L, 'drb')}, "
                   f"{L.pos('drb_pct')}): chi va a rimbalzo deve muoversi prima del tiro, gli "
                   "altri rientrano")
    P.duello(A, L.z("opp_ft_rate"), N.z("ft_rate"),
             f"Fanno molti falli (liberi concessi/tiri {_it(L.v('opp_ft_rate'), 2)}, "
             f"{L.pos('opp_ft_rate')}): attaccare il ferro e il corpo del difensore",
             f"Lunetta: voi ci andate spesso ({_it(N.v('ft_rate'), 2)}, {N.pos('ft_rate')}) e "
             f"loro fanno molti falli ({_it(L.v('opp_ft_rate'), 2)}, {L.pos('opp_ft_rate')}): "
             "attaccare il canestro dal primo minuto per mandarli presto in bonus",
             curare=f"Andate spesso in lunetta ({_it(N.v('ft_rate'), 2)}, {N.pos('ft_rate')}): "
                    "continuare ad attaccare il ferro",
             forza=f"Lunetta: voi ci andate spesso "
                   f"({_it(N.v('ft_rate'), 2)}, {N.pos('ft_rate')}), loro fanno pochi falli "
                   f"({L.pos('opp_ft_rate', False)} per meno liberi concessi): servono "
                   "penetrazioni decise e contatto con il corpo")
    P.duello(A, L.z("opp_tov_pct"), N.z("tov_pct"),
             f"Difesa aggressiva: forzano {_q(L, 'forzate')} ({L.pos('opp_tov_pct')}): due "
             "portatori, passaggi corti, contro la pressione attaccare in fretta il centro del "
             "campo",
             f"Palle perse: la loro difesa ne forza {_q(L, 'forzate')} ({L.pos('opp_tov_pct')}) "
             f"e voi ne perdete {_q(N, 'perse')} ({N.pos('tov_pct')}). Obiettivo: non più di "
             f"{_it(_n(N, 'perse') - 2, 0)}, con due portatori, nessun palleggio in mezzo all'area "
             "e l'uscita dalla pressione preparata",
             f"La loro difesa forza {_q(L, 'forzate')}, ma voi ne perdete poche "
             f"({_q(N, 'perse')}, {N.pos('tov_pct', False)} per meno palle perse): attaccare la "
             "pressione, dietro di loro c'è spazio",
             f"Perdete molti palloni ({_q(N, 'perse')}, {N.pos('tov_pct')}): due portatori e "
             "passaggi semplici", tipo_curare="curare")
    if L.z("opp_tov_pct") <= -SOGLIA_Z:
        P.add(A, -L.z("opp_tov_pct"), f"Forzano poche palle perse ({_q(L, 'forzate')}): si può "
                                      "attaccare in uno contro uno e in pick and roll senza "
                                      "grandi rischi")
    if Lo is not None and Lo.ok:
        P.duello(A, zc(Lo, "concessi_contropiede_pg"), N.z("punti_contropiede_pg"),
                 f"Rientrano male in difesa ({_it(Lo.v('concessi_contropiede_pg'))} punti "
                 "concessi in contropiede): correre dopo ogni rimbalzo e palla recuperata",
                 f"Contropiede: è un vostro punto forte ({_it(N.v('punti_contropiede_pg'))} punti "
                 f"a partita, {N.pos('punti_contropiede_pg')}) e loro rientrano male "
                 f"({_it(Lo.v('concessi_contropiede_pg'))} concessi): correre sempre, rimesse "
                 "veloci",
                 curare=f"Il contropiede è un vostro punto forte "
                        f"({_it(N.v('punti_contropiede_pg'))} punti a partita, "
                        f"{N.pos('punti_contropiede_pg')}): correre dopo ogni rimbalzo difensivo")
        P.duello(A, zc(Lo, "concessi_seconda_occasione_pg"), 0.0,
                 f"Concedono seconde occasioni ({_it(Lo.v('concessi_seconda_occasione_pg'))} "
                 "punti a partita): insistere a rimbalzo offensivo")
    if not pd.isna(L.v("minuto_medio_bonus")) and -L.z("minuto_medio_bonus") >= SOGLIA_Z:
        P.add(A, -L.z("minuto_medio_bonus"),
              f"Vanno in bonus presto (5° fallo di squadra in media al "
              f"{_it(L.v('minuto_medio_bonus'))}' del quarto): nella seconda metà dei quarti "
              "attaccare il canestro per andare in lunetta")
    fo = ctx.fouls
    if fo is not None and not fo.empty:
        f = fo[(fo["squadra_id"] == avv) & (fo["partite_problemi"] > 0)].sort_values(
            "partite_problemi", ascending=False).head(2)
        if not f.empty:
            chi = ", ".join(f"{_cognome(x.giocatore)} ({_volte(int(x.partite_problemi))})"
                            for x in f.itertuples())
            P.add(A, 0.8, f"Spesso in difficoltà con i falli: {chi}. Attaccarli dal primo "
                          "quarto in post e in uno contro uno")
    if not peg.empty:
        q = peg.iloc[0]
        P.add(A, 0.7, f"Quando giocano con {q['giocatori']} ({_it(q['net_rtg'], 0, True)} di "
                      f"Net rating in {_it(q['minuti'], 0)}') rendono peggio: è il momento di "
                      "spingere")

    # ================================================ ritmo, rotazioni e momenti
    if rt is not None and not rt.empty and noi:
        lento, veloce = rt.iloc[0], rt.iloc[-1]
        meglio = lento if lento["prob"] >= veloce["prob"] else veloce
        altro = veloce if meglio is lento else lento
        tipo = "più lenta" if meglio is lento else "più veloce"
        P.add(R, 1 + abs(lento["prob"] - veloce["prob"]) / 5,
              f"Conviene una partita {tipo}: {_it(meglio['prob'], 0)}% di probabilità con "
              f"{_it(meglio['possessi'], 0)} possessi contro {_it(altro['prob'], 0)}%. "
              f"Ritmo medio: voi {_it(N.v('pace'))}, loro {_it(L.v('pace'))} possessi per 40'"
              + (" — attacchi lunghi e rimesse senza fretta" if meglio is lento else
                 " — correre dopo ogni rimbalzo, rimesse veloci"))
    elif abs(L.z("pace")) >= SOGLIA_Z:
        P.add(R, L.z("pace"), f"Il loro ritmo è {'alto' if L.z('pace') > 0 else 'basso'} "
                              f"({_it(L.v('pace'))} possessi per 40', {L.pos('pace')})")
    m = ctx.momenti
    if m is not None and not m.empty and avv in set(m["squadra_id"]):
        mm = m[m["squadra_id"] == avv].set_index("momento")
        mn = m[m["squadra_id"] == mia].set_index("momento") if noi else None
        peg_m = mm.sort_values("diff_pg").iloc[0]
        mig_m = mm.sort_values("diff_pg").iloc[-1]
        if peg_m["diff_pg"] < -1.5:
            nostro = mn["diff_pg"].get(peg_m.name) if mn is not None else None
            if nostro is not None and nostro > 1:
                P.add(R, (nostro - peg_m["diff_pg"]) / 3,
                      f"{peg_m['etichetta']}: è il loro momento peggiore "
                      f"({_it(peg_m['diff_pg'], 1, True)} a partita) e uno dei vostri migliori "
                      f"({_it(nostro, 1, True)}): spingere lì per prendere vantaggio",
                      "occasione")
            else:
                P.add(R, -peg_m["diff_pg"] / 3,
                      f"Calano in: {peg_m['etichetta'].lower()} ({_it(peg_m['diff_pg'], 1, True)} "
                      f"a partita, {peg_m['posizione']}° su {peg_m['squadre']}): è lì che si "
                      "può fare la differenza")
        if mig_m["diff_pg"] > 1.5:
            nostro = mn["diff_pg"].get(mig_m.name) if mn is not None else None
            if nostro is not None and nostro < -1:
                P.add(R, (mig_m["diff_pg"] - nostro) / 3,
                      f"{mig_m['etichetta']}: è il loro momento migliore "
                      f"({_it(mig_m['diff_pg'], 1, True)}) e uno dei vostri peggiori "
                      f"({_it(nostro, 1, True)}): preparare quei minuti (quintetto, timeout "
                      "presto)", "sfida")
            else:
                P.add(R, mig_m["diff_pg"] / 3,
                      f"Partono forte in: {mig_m['etichetta'].lower()} "
                      f"({_it(mig_m['diff_pg'], 1, True)} a partita): attenzione in quel "
                      "momento, timeout presto se allungano")
    rot = ctx.rotazioni["squadre"] if ctx.rotazioni else pd.DataFrame()
    if not rot.empty and avv in set(rot["squadra_id"]):
        rl = rot[rot["squadra_id"].isin(L.lega.index)].set_index("squadra_id")
        s = rl.loc[avv]
        sd = rl["giocatori_rotazione"].std() or 1
        zr = (s["giocatori_rotazione"] - rl["giocatori_rotazione"].mean()) / sd
        nostra = rl["giocatori_rotazione"].get(mia) if noi else None
        if zr <= -SOGLIA_Z:
            extra = (f" Voi ruotate {_it(nostra)} giocatori: la profondità è un vostro "
                     "vantaggio" if nostra is not None and nostra >= s["giocatori_rotazione"] + 1
                     else "")
            P.add(R, -zr + (0.5 if extra else 0),
                  f"Rotazione corta ({_it(s['giocatori_rotazione'])} giocatori con almeno 5'): "
                  "alzare l'intensità per stancare i titolari nel secondo tempo." + extra,
                  "occasione" if extra else "")
        P.add(R, 0.4, f"Primo cambio in media al minuto {_it(s['minuto_primo_cambio'])}; "
                      f"quintetto base nel {_it(s['quota_quintetto_base'], 0)}% delle partite")
    P.duello(R, -L.z("quota_punti_panchina"), N.z("quota_punti_panchina"),
             f"Panchina poco produttiva ({_it(L.v('quota_punti_panchina'), 0)}% dei punti): "
             "spingere quando riposano i titolari",
             f"Panchine: la vostra produce il {_it(N.v('quota_punti_panchina'), 0)}% dei punti, "
             f"la loro solo il {_it(L.v('quota_punti_panchina'), 0)}%: i minuti delle seconde "
             "linee sono a vostro favore, allungare le rotazioni")
    if L.z("break_fatti_pg") >= SOGLIA_Z:
        P.add(R, L.z("break_fatti_pg"),
              f"Fanno parziali ({_it(L.v('break_fatti_pg'))} break da 8-0 a partita, massimo "
              f"{_it(L.v('max_fatto'), 0)}-0): fermarli subito con un timeout")
    if L.z("diff_dopo") >= SOGLIA_Z:
        P.add(R, L.z("diff_dopo"),
              f"Escono bene dai loro timeout ({_it(L.v('diff_dopo'), 1, True)} punti nei 2' "
              "successivi): attenzione alla prima azione dopo il timeout")

    # ================================================ finali
    ct, cp = ctx.clutch_teams, ctx.clutch_players
    rec = {}
    if ct is not None and not ct.empty:
        cti = ct.set_index("squadra_id")
        for sid in (avv, mia):
            if sid is not None and sid in cti.index:
                rec[sid] = cti.loc[sid]
    if avv in rec:
        c = rec[avv]
        n = int(c["partite_clutch"])
        testo = f"Finali punto a punto: loro {c['record_clutch']} in {n} " \
                f"{'partita' if n == 1 else 'partite'}"
        if mia in rec:
            testo += f", voi {rec[mia]['record_clutch']}"
        P.add(F, 1, testo)
        chi = cp[cp["squadra_id"] == avv].sort_values("quota_tiri", ascending=False) \
            if cp is not None and not cp.empty else pd.DataFrame()
        if not chi.empty and chi["quota_tiri"].iloc[0] >= 25:
            x = chi.iloc[0]
            P.add(F, 1, f"Nei finali la palla va a {_cognome(x['giocatore'])} "
                        f"({_it(x['quota_tiri'], 0)}% dei tiri, {int(x['fgm'])}/{int(x['fga'])}): "
                        "anticipare la ricezione e raddoppiare in uscita dai blocchi")
    scarsi = pl[(pl["minuti_pg"] >= 20) & (pl["tla"] >= 8) & (pl["tl_pct"] < tl_lega - 12)]
    if not scarsi.empty:
        x = scarsi.sort_values("tl_pct").iloc[0]
        P.add(F, 0.9, f"In vantaggio nel finale si può mandare in lunetta "
                      f"{_cognome(x['giocatore'])} ({_it(x['tl_pct'], 0)}% ai liberi, media "
                      f"{_it(tl_lega, 0)}%)")
    bravi = pl[(pl["minuti_pg"] >= 15) & (pl["tla"] >= 8)].sort_values("tl_pct", ascending=False)
    if not bravi.empty and bravi["tl_pct"].iloc[0] >= 85:
        x = bravi.iloc[0]
        P.add(F, 0.6, f"Da non mandare in lunetta: {_cognome(x['giocatore'])} "
                      f"({_it(x['tl_pct'], 0)}% ai liberi)")
    if noi:
        nostri = pn[(pn["minuti_pg"] >= 15) & (pn["tla"] >= 6)].sort_values("tl_pct",
                                                                           ascending=False)
        if not nostri.empty:
            x = nostri.iloc[0]
            P.add(F, 0.8, f"Da voi, nel finale la palla in mano a chi tira bene i liberi: "
                          f"{_cognome(x['giocatore'])} ({_it(x['tl_pct'], 0)}%)"
                          + (f"; evitare che la riceva {_cognome(nostri.iloc[-1]['giocatore'])} "
                             f"({_it(nostri.iloc[-1]['tl_pct'], 0)}%)"
                             if len(nostri) > 2 and nostri.iloc[-1]["tl_pct"] < tl_lega - 10
                             else ""))

    return {g: [t for _, t in sorted(v, key=lambda p: -p[0])][:MAX_PER_GRUPPO]
            for g, v in P.gruppi.items()}


def _quintetti(ctx, sid):
    from . import miglioramento as M
    mig, peg, _ = M.quintetti_estremi(ctx.lineups, sid, n=1)
    return mig, peg
