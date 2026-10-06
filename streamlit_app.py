"""LNP Stats: piattaforma di scouting per Serie A2 e Serie B Nazionale.

Ottimizzata per iPad: filtri in alto (sempre visibili, anche in verticale), schede a
griglia che si adattano alla larghezza, grafici leggibili al tocco, pulsanti "?" con la
spiegazione delle statistiche. Accesso per club configurabile nei secrets di Streamlit.
"""

import streamlit as st

from basket import accesso, config, scouting
from dashboard import nuove, schede
from dashboard.stato import (App, archivio, archivio_url, contesto, secrets,
                             stagioni_disponibili)
from dashboard.ui import esc, hero, inject_css, tip

st.set_page_config(page_title="LNP Stats", page_icon="🏀", layout="wide",
                   initial_sidebar_state="collapsed")
inject_css()

if not config.DB_PATH.exists():
    st.error("Database non trovato (data/lnp.sqlite). Esegui prima il workflow di aggiornamento.")
    st.stop()

# ------------------------------------------------------------------ accesso

utenti = {k.lower(): dict(v) for k, v in (secrets().get("utenti") or {}).items()}
if utenti:
    if "utente" not in st.session_state:
        hero("Piattaforma di scouting", "LNP Stats", "Accedi con le credenziali del tuo club")
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

# ------------------------------------------------------------------ dati e filtri

mtime = config.DB_PATH.stat().st_mtime
stagioni = stagioni_disponibili()
testata = st.empty()
f0, f1, f2, f3 = st.columns([1, 1.3, 1.5, 1.6])
stagione = f0.selectbox("Stagione", stagioni, format_func=config.STAGIONI.get)
ctx = contesto(mtime, stagione)
bs = ctx.bs
if bs.empty:
    st.warning("Nessuna partita nel database per la stagione scelta.")
    st.stop()

# Squadra del club dell'utente
if utente.get("club") and "squadra_id" not in utente:
    trovate = scouting.find_team(ctx.conn, utente["club"])
    utente["squadra_id"] = trovate[0][0] if len(trovate) == 1 else None

camp_disp = [c for c in config.CAMPIONATI if c in set(bs["campionato_id"])]
camp_default = 0
if utente.get("squadra_id") in set(bs["squadra_id"]):
    mio_camp = bs.loc[bs["squadra_id"] == utente["squadra_id"], "campionato_id"].iloc[0]
    camp_default = camp_disp.index(mio_camp)
camp = f1.selectbox("Campionato", camp_disp, index=camp_default,
                    format_func=lambda c: config.CAMPIONATI[c])
players = ctx.players[ctx.players["campionato_id"] == camp]
profile = ctx.profile[ctx.profile["campionato_id"] == camp]
squadre = profile.sort_values("squadra")
sq_names = dict(zip(squadre["squadra_id"], squadre["squadra"]))
sq = f2.selectbox("Squadra", [None] + list(sq_names),
                  format_func=lambda s: "Tutte" if s is None else sq_names[s])
pool = (players if sq is None else players[players["squadra_id"] == sq]).sort_values("giocatore")
g_names = {(r.giocatore_id, r.squadra_id): f"{r.giocatore} ({r.squadra})"
           for r in pool.itertuples()}
gsel = f3.selectbox("Giocatore", [None] + list(g_names),
                    format_func=lambda g: "Tutti" if g is None else g_names[g])

a = App(ctx=ctx, mtime=mtime, stagione=stagione, camp=camp, sq=sq, gsel=gsel, utente=utente,
        archivio=archivio(archivio_url()), players=players, profile=profile,
        bs_c=bs[bs["campionato_id"] == camp], bg_c=ctx.bg[ctx.bg["campionato_id"] == camp])

agg = ctx.conn.execute("SELECT MAX(scaricata_il) FROM partite").fetchone()[0]
chi = (f" · {esc(utente['username'])} ({esc(utente['club'] or '')})"
       if not utente.get("demo") else " · modalità demo")
with testata.container():
    hero(f"Stagione {config.STAGIONI.get(stagione, stagione)} · {config.CAMPIONATI[camp]}",
         "LNP Stats",
         f"{a.bs_c['partita_id'].nunique()} partite · fino alla {int(a.bs_c['giornata'].max())}ª "
         f"giornata · aggiornato {esc(str(agg)[:10])} · fonte legapallacanestro.com{chi}")
    if not utente.get("demo"):
        if st.button("Esci", key="logout"):
            st.session_state.pop("utente", None)
            st.rerun()

n_incomplete = a.bs_c.loc[~a.bs_c["affidabile"], "partita_id"].nunique()
if n_incomplete:
    st.markdown(f'<div class="note">{n_incomplete} partite con box score ufficiale incompleto: '
                'contano per risultati e totali, non per percentuali e metriche avanzate.'
                f'{tip("incompleto")}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ schede

nomi_tab = ["Panoramica", "Classifica", "Squadre", "Giocatori", "Giocatore", "Scouting",
            "Anteprima", "Mercato", "Avvisi", "La mia squadra", "Partite"]
tabs = dict(zip(nomi_tab, st.tabs(nomi_tab)))

with tabs["Panoramica"]:
    schede.render_panoramica(a)
with tabs["Classifica"]:
    schede.render_classifica(a)
with tabs["Squadre"]:
    schede.render_squadre(a)
with tabs["Giocatori"]:
    schede.render_giocatori(a)
with tabs["Giocatore"]:
    schede.render_giocatore(a)
    nuove.giocatore_extra(a)
with tabs["Scouting"]:
    schede.render_scouting(a)
    nuove.scouting_extra(a)
with tabs["Anteprima"]:
    nuove.render_anteprima(a)
with tabs["Mercato"]:
    nuove.render_mercato(a)
with tabs["Avvisi"]:
    nuove.render_avvisi(a)
with tabs["La mia squadra"]:
    nuove.render_mia_squadra(a)
with tabs["Partite"]:
    nuove.partita_extra(a, schede.render_partite(a))
