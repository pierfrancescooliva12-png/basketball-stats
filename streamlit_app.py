"""ASSIST: piattaforma di scouting per Serie A2 e Serie B Nazionale.

Ottimizzata per iPad: navigazione in alto per aree (Home, Avversaria, Giocatori, La mia
squadra, Campionato), filtri compatti sempre visibili, pagine calcolate solo quando aperte,
pulsanti "?" con la spiegazione delle statistiche, link condivisibili (la pagina e i filtri
sono nell'indirizzo). Accesso per club configurabile nei secrets di Streamlit.
"""

import streamlit as st

from basket import accesso, config, scouting
from dashboard import pagine
from dashboard.stato import (App, archivio, archivio_url, contesto, secrets,
                             stagioni_disponibili)
from dashboard.ui import brand_hero, esc, inject_css, tip, topbar

st.set_page_config(page_title=config.BRAND, page_icon=str(config.LOGO_DIR / "assist-mark-128.png"),
                   layout="wide",
                   initial_sidebar_state="collapsed")
inject_css()

if not config.DB_PATH.exists():
    st.error("Database non trovato (data/lnp.sqlite). Esegui prima il workflow di aggiornamento.")
    st.stop()

# ------------------------------------------------------------------ accesso

utenti = {k.lower(): dict(v) for k, v in (secrets().get("utenti") or {}).items()}
if utenti:
    if "utente" not in st.session_state:
        brand_hero("Piattaforma di scouting", "Accedi con le credenziali del tuo club")
        with st.form("login"):
            u = st.text_input("Utente")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Accedi", type="primary"):
                ok = accesso.authenticate(utenti, u, p)
                if ok:
                    st.session_state["utente"] = ok
                    st.rerun()
                st.error("Credenziali non valide")
        st.stop()
    utente = dict(st.session_state["utente"])
else:
    utente = {"username": "demo", "club": None, "ruolo": "admin", "demo": True}

# ------------------------------------------------------------------ filtri (dall'indirizzo)

nav = st.navigation(pagine.mappa(), position="top")
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
if utente.get("demo") and st.session_state.get("mia_demo") is not None:
    utente["squadra_id"] = st.session_state["mia_demo"]

camp_disp = [c for c in config.CAMPIONATI if c in set(bs["campionato_id"])]
if st.session_state.get("f_camp") not in camp_disp:
    camp_default = camp_disp[0]
    if qp.get("campionato") in camp_disp:
        camp_default = qp["campionato"]
    elif utente.get("squadra_id") in set(bs["squadra_id"]):
        camp_default = bs.loc[bs["squadra_id"] == utente["squadra_id"], "campionato_id"].iloc[0]
    st.session_state["f_camp"] = camp_default
camp = f1.selectbox("Campionato", camp_disp, format_func=lambda c: config.CAMPIONATI[c],
                    key="f_camp")
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
# Scouting senza squadra scelta: si apre sulla prossima avversaria della squadra del club
if nav.url_path == "scouting" and st.session_state.get("f_sq") is None \
        and utente.get("squadra_id"):
    ng = ctx.next_game(utente["squadra_id"])
    if ng:
        avv = ng["ospite_id"] if ng["casa_id"] == utente["squadra_id"] else ng["casa_id"]
        if avv in sq_names:
            st.session_state["f_sq"] = avv
sq = f2.selectbox("Squadra", opzioni_sq, key="f_sq",
                  format_func=lambda s: "Tutte" if s is None else sq_names[s])
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

a = App(ctx=ctx, mtime=mtime, stagione=stagione, camp=camp, sq=sq, gsel=gsel, utente=utente,
        archivio=archivio(archivio_url()), players=players, profile=profile,
        bs_c=bs[bs["campionato_id"] == camp], bg_c=ctx.bg[ctx.bg["campionato_id"] == camp],
        esperto=esperto)

agg = ctx.conn.execute("SELECT MAX(scaricata_il) FROM partite").fetchone()[0]
chi = (f" · {esc(utente['username'])} ({esc(utente['club'] or '')})"
       if not utente.get("demo") else " · modalità demo")
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
    if not utente.get("demo") and c2.button("Esci", key="logout"):
        st.session_state.pop("utente", None)
        st.rerun()

# ------------------------------------------------------------------ pagine

pagine.APP = a
nav.run()
