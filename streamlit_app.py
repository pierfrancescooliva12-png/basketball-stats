"""ASSIST: piattaforma di scouting per Serie A2 e Serie B Nazionale.

Ottimizzata per iPad: navigazione in alto per aree (Home, Avversaria, Giocatori, La mia
squadra, Campionato), filtri compatti sempre visibili, pagine calcolate solo quando aperte,
pulsanti "?" con la spiegazione delle statistiche, link condivisibili (la pagina e i filtri
sono nell'indirizzo). Accesso per club configurabile nei secrets di Streamlit.
"""

import streamlit as st

from basket import accesso, config, scouting
from dashboard import pagine
from dashboard.stato import (App, archivio, archivio_url, brand_club, contesto, secrets,
                             stagioni_disponibili, tema_club)
from dashboard.ui import esc, inject_css, tip, topbar

st.set_page_config(page_title=config.BRAND, page_icon=str(config.LOGO_DIR / "assist-mark-128.png"),
                   layout="wide",
                   initial_sidebar_state="collapsed")
inject_css()

if not config.DB_PATH.exists():
    st.error("Database non trovato (data/lnp.sqlite). Esegui prima il workflow di aggiornamento.")
    st.stop()

# ------------------------------------------------------------------ accesso

arch = archivio(archivio_url())
try:
    utenti_db = arch.users()
except Exception:                         # database non raggiungibile: restano i Secrets
    utenti_db = {}
utenti = accesso.unisci(secrets().get("utenti") or {}, utenti_db)
if utenti:
    from dashboard import accesso_ui
    if "utente" not in st.session_state:
        accesso_ui.login(utenti, arch)      # si ferma qui finché l'accesso non riesce
    utente = dict(st.session_state["utente"])
    # utente del database disattivato nel frattempo: fuori
    if utente.get("fonte") == "database" and utente["username"] not in utenti:
        st.session_state.clear()
        st.rerun()
    if utente.get("cambio"):
        accesso_ui.cambio_obbligatorio(utente, arch)   # primo accesso: nuova password
else:
    utente = {"username": "demo", "club": None, "ruolo": "admin", "demo": True}

# ------------------------------------------------------------------ filtri (dall'indirizzo)

# l'area Amministrazione c'è solo per gli admin veri (non in modalità demo)
nav = st.navigation(pagine.mappa(admin=utente.get("ruolo") == "admin" and not utente.get("demo"),
                                 club=bool(utente.get("club")) and not utente.get("demo")),
                    position="top")
qp = st.query_params
mtime = config.DB_PATH.stat().st_mtime
stagioni = stagioni_disponibili()
if "f_stag" not in st.session_state and qp.get("stagione") in stagioni:
    st.session_state["f_stag"] = qp["stagione"]

barra = st.container()
f0, f1, f2, f3, f4 = st.columns([1, 1.25, 1.6, 1.8, 0.9], vertical_alignment="bottom")
stagione = f0.selectbox("Stagione", stagioni, format_func=config.STAGIONI.get, key="f_stag")
ctx = contesto(mtime, stagione)
bs = ctx.bs
if bs.empty:
    st.warning("Nessuna partita nel database per la stagione scelta.")
    st.stop()

# Squadra del club dell'utente
if utente.get("club") and "squadra_id" not in utente:
    trovate = scouting.find_team(ctx.conn, utente["club"])
    utente["squadra_id"] = trovate[0][0] if len(trovate) == 1 else None
# demo e amministratore senza club: la squadra si sceglie nella Home
if (utente.get("demo") or not utente.get("club")) and st.session_state.get("mia_demo") is not None:
    utente["squadra_id"] = st.session_state["mia_demo"]

camp_disp = [c for c in config.CAMPIONATI if c in set(bs["campionato_id"])]
mia_id = utente.get("squadra_id")
mia_camp = (bs.loc[bs["squadra_id"] == mia_id, "campionato_id"].iloc[0]
            if mia_id in set(bs["squadra_id"]) else None)
pagina = nav.url_path
entrata = st.session_state.get("_pagina") != pagina
st.session_state["_pagina"] = pagina
esplicita = st.session_state.pop("_scelta", False)
# utente di un club: il campionato è sempre quello della sua squadra; per demo e admin che
# seguono una squadra la Home si riapre comunque sul campionato di quella squadra
club_fisso = bool(utente.get("club")) and not utente.get("demo") and mia_camp is not None
if club_fisso or (mia_camp is not None and pagina in ("", "home") and entrata):
    st.session_state["f_camp"] = mia_camp
if st.session_state.get("f_camp") not in camp_disp:
    camp_default = camp_disp[0]
    if qp.get("campionato") in camp_disp and not club_fisso:
        camp_default = qp["campionato"]
    elif utente.get("squadra_id") in set(bs["squadra_id"]):
        camp_default = bs.loc[bs["squadra_id"] == utente["squadra_id"], "campionato_id"].iloc[0]
    st.session_state["f_camp"] = camp_default
camp = f1.selectbox("Campionato", camp_disp, format_func=lambda c: config.CAMPIONATI[c],
                    key="f_camp", disabled=club_fisso,
                    help="Il campionato della tua squadra." if club_fisso else None)
players = ctx.players[ctx.players["campionato_id"] == camp]
profile = ctx.profile[ctx.profile["campionato_id"] == camp]
squadre = profile.sort_values("squadra")
sq_names = dict(zip(squadre["squadra_id"], squadre["squadra"]))
opzioni_sq = [None] + list(sq_names)
if "f_sq" not in st.session_state and qp.get("squadra"):
    try:
        st.session_state["f_sq"] = int(qp["squadra"])
    except ValueError:
        pass
if st.session_state.get("f_sq") not in opzioni_sq:
    st.session_state["f_sq"] = None
# esperienza della squadra del club (o di quella scelta nella Home da demo/admin):
# - pagine della propria squadra: sempre e solo quella, filtro bloccato
# - scouting e lavagna dell'avversaria: la propria squadra è fissa, il filtro diventa
#   "Avversaria" (senza la propria squadra) e si apre sulla prossima avversaria
mia_ok = mia_id in sq_names
solo_mia = mia_ok and pagina in pagine.MIE
su_avversaria = mia_ok and pagina in pagine.AVVERSARIA
etichetta_sq, aiuto_sq = "Squadra", None
if solo_mia:
    st.session_state["f_sq"] = mia_id
    aiuto_sq = "Questa pagina riguarda la tua squadra."
elif su_avversaria:
    ng = ctx.next_game(mia_id)
    avv = (ng["ospite_id"] if ng["casa_id"] == mia_id else ng["casa_id"]) if ng else None
    avv = avv if avv in sq_names else None
    opzioni_sq = ([] if avv is not None else [None]) + [s for s in sq_names if s != mia_id]
    if st.session_state.get("f_sq") not in opzioni_sq or (entrata and not esplicita):
        st.session_state["f_sq"] = avv if avv is not None else opzioni_sq[0]
    etichetta_sq = "Avversaria"
    aiuto_sq = (f"La tua squadra ({sq_names[mia_id]}) è fissa: qui scegli solo l'avversaria. "
                "Di base è la prossima.")
sq = f2.selectbox(etichetta_sq, opzioni_sq, key="f_sq", disabled=solo_mia, help=aiuto_sq,
                  format_func=lambda s: "Tutte" if s is None else
                  sq_names[s] + (" · prossima" if su_avversaria and s == avv else ""))
pool = (players if sq is None else players[players["squadra_id"] == sq]).sort_values("giocatore")
g_names = {(r.giocatore_id, r.squadra_id): f"{r.giocatore} ({r.squadra})"
           for r in pool.itertuples()}
opzioni_g = [None] + list(g_names)
if "f_g" not in st.session_state and qp.get("giocatore"):
    trovati = [k for k in g_names if k[0] == qp["giocatore"]]
    if trovati:
        st.session_state["f_g"] = trovati[0]
if st.session_state.get("f_g") not in opzioni_g:
    st.session_state["f_g"] = None
gsel = f3.selectbox("Giocatore", opzioni_g, key="f_g",
                    format_func=lambda g: "Tutti" if g is None else g_names[g])
esperto = f4.toggle("Esperto", key="esperto",
                    help="Vista esperto: tutte le colonne e le metriche avanzate. "
                         "Spenta: solo le voci essenziali, con nomi per esteso.")

# filtri nell'indirizzo: la pagina si può condividire così com'è
nuovi = {"stagione": stagione, "campionato": camp}
if sq is not None:
    nuovi["squadra"] = str(sq)
if gsel is not None:
    nuovi["giocatore"] = gsel[0]
for k in ("squadra", "giocatore"):
    if k not in nuovi and k in qp:
        del qp[k]
for k, v in nuovi.items():
    if qp.get(k) != v:
        qp[k] = v

# brand del club: logo e colori della squadra (anche per demo e admin che la seguono)
tema = None
if mia_ok:
    import json
    try:
        tema = tema_club(int(mia_id), sq_names[mia_id], json.dumps(brand_club(mia_id), sort_keys=True))
    except Exception:                     # il brand non deve mai bloccare la piattaforma
        tema = None
if tema is not None:
    from basket import brand
    st.markdown(brand.css(tema), unsafe_allow_html=True)
# tabelle: colori del club, la propria squadra evidenziata e i loghi accanto ai nomi
_tt = {"sids": {v: k for k, v in sq_names.items()}, "mia_nome": sq_names.get(mia_id) if mia_ok else None}
if tema is not None:
    from basket import brand
    _tt.update(accent=tema.accento, navy=tema.fondo, navy2=brand.mescola(tema.fondo, "#ffffff", 0.82),
               mia=brand.mescola(tema.accento, "#ffffff", 0.12))
st.session_state["_tema_tabelle"] = _tt
# icona sulla schermata Home di iPhone e Android: il logo del club (o il marchio ASSIST)
from dashboard import icona_app
icona_app.imposta(tema)

a = App(ctx=ctx, mtime=mtime, stagione=stagione, camp=camp, sq=sq, gsel=gsel, utente=utente,
        archivio=arch, players=players, profile=profile,
        bs_c=bs[bs["campionato_id"] == camp], bg_c=ctx.bg[ctx.bg["campionato_id"] == camp],
        esperto=esperto, tema=tema)

agg = ctx.conn.execute("SELECT MAX(scaricata_il) FROM partite").fetchone()[0]
chi = (" · modalità demo" if utente.get("demo") else
       f" · {esc(utente['username'])} ({esc(utente['club'] or 'amministratore')})")
n_incomplete = a.bs_c.loc[~a.bs_c["affidabile"], "partita_id"].nunique()
with barra:
    c1, c2 = st.columns([6, 1], vertical_alignment="center")
    with c1:
        meta = (f"{config.STAGIONI.get(stagione, stagione)} · {config.CAMPIONATI[camp]} · "
                f"{a.bs_c['partita_id'].nunique()} partite, fino alla "
                f"{int(a.bs_c['giornata'].max())}ª giornata · aggiornato "
                f"{esc(pagine.data_it(agg))}{chi}")
        if n_incomplete:
            meta += (f' · {n_incomplete} box score incompleti{tip("incompleto")}')
        topbar(meta)
    if not utente.get("demo"):
        b1, b2 = c2.columns(2)
        if utente.get("fonte") == "database" and b1.button("Password", key="cambia_pw",
                                                           help="Cambia la tua password"):
            accesso_ui.cambia_password(utente, arch)
        if b2.button("Esci", key="logout"):
            st.session_state.clear()        # niente filtri o scelte del precedente utente
            st.query_params.clear()
            st.rerun()

# ------------------------------------------------------------------ pagine

pagine.APP = a
nav.run()
