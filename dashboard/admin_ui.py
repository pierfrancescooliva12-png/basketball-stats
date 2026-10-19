"""Amministrazione (solo admin): utenti attivi e creazione degli accessi per i club.

Gli utenti stanno nei Secrets di Streamlit, che il sito può leggere ma non scrivere: qui si
prepara il blocco da incollare, con una password iniziale generata a caso da comunicare al
club. La password si vede una volta sola e non viene salvata da nessuna parte."""

import pandas as pd
import streamlit as st

from basket import accesso, config

from .stato import App, secrets
from .ui import note_html, section, show

PASSI = ("Apri share.streamlit.io › la tua app › Settings › Secrets.",
         "Incolla il blocco in fondo, sotto gli utenti già presenti, e salva.",
         "Comunica al club utente e password per un canale riservato (telefono o di persona, "
         "meglio non nella stessa email).")


def _utenti() -> dict:
    return {k.lower(): dict(v) for k, v in (secrets().get("utenti") or {}).items()}


def _squadre(a: App) -> list[str]:
    nomi = a.ctx.bs.drop_duplicates("squadra_id")[["squadra", "campionato_id"]]
    nomi = nomi.assign(c=nomi["campionato_id"].map(config.CAMPIONATI))
    return [f"{r.squadra} · {r.c}" for r in nomi.sort_values(["c", "squadra"]).itertuples()]


def _risultato(utente: str, password: str, blocco: str, nuovo: bool):
    st.success(("Accesso preparato" if nuovo else "Nuova password preparata") + f" per «{utente}».")
    c1, c2 = st.columns([1, 2])
    c1.markdown("**Utente**")
    c1.code(utente, language=None)
    c1.markdown("**Password iniziale**")
    c1.code(password, language=None)
    c2.markdown("**Blocco per i Secrets**" + ("" if nuovo else " (sostituisce quello di questo utente)"))
    c2.code(blocco, language="toml", wrap_lines=True)
    st.markdown("".join(f"{i}. {p}\n" for i, p in enumerate(PASSI, 1)))
    note_html("La password compare solo qui: chiudendo la pagina non si recupera più "
              "(se serve, se ne genera una nuova).")


def render(a: App):
    if a.utente.get("ruolo") != "admin" or a.utente.get("demo"):
        st.error("Pagina riservata all'amministratore.")
        return
    utenti = _utenti()
    section("Utenti attivi", "letti dai Secrets di Streamlit")
    if utenti:
        show(pd.DataFrame([{"Utente": u, "Club": d.get("club") or "– (tutte le squadre)",
                            "Ruolo": d.get("ruolo", "staff")} for u, d in sorted(utenti.items())]),
             voci=[])
    else:
        note_html("Nessun utente nei Secrets: il sito è in modalità demo.")

    section("Nuovo accesso per un club", "password iniziale generata a caso")
    squadre = _squadre(a)
    with st.form("nuovo_utente", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1.2, 1])
        squadra = c1.selectbox("Squadra", squadre, index=None, placeholder="Scegli la squadra…")
        nome = c2.text_input("Utente", placeholder="es. forli-staff")
        ruolo = c3.selectbox("Ruolo", ["staff", "admin"],
                             help="staff: vede la piattaforma con la sua squadra; admin: vede "
                                  "anche questa pagina.")
        crea = st.form_submit_button("Prepara l'accesso", type="primary")
    if crea:
        errore = accesso.errore_nome(nome, utenti)
        if squadra is None:
            st.error("Scegli la squadra del club.")
        elif errore:
            st.error(f"Utente: {errore}.")
        else:
            club = squadra.rsplit(" · ", 1)[0]
            pw = accesso.genera_password()
            u = nome.strip().lower()
            _risultato(u, pw, accesso.blocco_toml(u, pw, club, ruolo), nuovo=True)

    section("Nuova password per un utente", "se l'ha dimenticata o va cambiata")
    if not utenti:
        note_html("Nessun utente da aggiornare.")
        return
    with st.form("reset_password", clear_on_submit=True):
        chi = st.selectbox("Utente", sorted(utenti), index=None, placeholder="Scegli l'utente…")
        reset = st.form_submit_button("Genera una nuova password")
    if reset and chi:
        d = utenti[chi]
        pw = accesso.genera_password()
        _risultato(chi, pw, accesso.blocco_toml(chi, pw, d.get("club"), d.get("ruolo", "staff")),
                   nuovo=False)
