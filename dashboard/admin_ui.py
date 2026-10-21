"""Amministrazione (solo admin): utenti, accessi dei club e brand.

Con il database permanente collegato (Secrets: [database] url = "postgresql+psycopg2://...")
utenti e brand si gestiscono direttamente da qui: si crea l'utenza con una password
provvisoria (da cambiare al primo accesso), la si disattiva, si reimposta la password, si
salvano i colori del club. Senza database si prepara il blocco da incollare nei Secrets.
Gli utenti dei Secrets (l'amministratore) restano come accesso di riserva.
La password provvisoria si vede una volta sola e non viene salvata da nessuna parte."""

import json

import pandas as pd
import streamlit as st

from basket import accesso, brand, config

from .stato import App, brand_club, secrets, tema_club
from .ui import esc, note_html, section, show

PASSI_SECRETS = (("Apri dashboard.render.com › il servizio ASSIST › Environment › Secret Files › secrets.toml."
                  if config.SU_RENDER else "Apri share.streamlit.io › la tua app › Settings › Secrets."),
                 "Incolla il blocco in fondo, sotto gli utenti già presenti, e salva"
                 + (" (Render riavvia il servizio da solo)." if config.SU_RENDER else "."))
CONSEGNA = ("Comunica al club utente e password per un canale riservato (telefono o di persona, "
            "meglio non nella stessa email). Al primo accesso il sito chiede di sceglierne una nuova.")
SITO = config.APP_URL


def _sito() -> str:
    try:
        u = str(st.context.url or "")
        return u.split("?")[0].rstrip("/").rsplit("/", 1)[0] if u.count("/") > 2 else SITO
    except Exception:
        return SITO


def _squadre(a: App) -> list[str]:
    nomi = a.ctx.bs.drop_duplicates("squadra_id")[["squadra", "campionato_id"]]
    nomi = nomi.assign(c=nomi["campionato_id"].map(config.CAMPIONATI))
    return [f"{r.squadra} · {r.c}" for r in nomi.sort_values(["c", "squadra"]).itertuples()]


def _password_mostrata(utente: str, password: str, blocco: str | None = None):
    c1, c2 = st.columns([1, 2])
    c1.markdown("**Utente**")
    c1.code(utente, language=None)
    c1.markdown("**Password provvisoria**")
    c1.code(password, language=None)
    if blocco:
        c2.markdown("**Blocco per i Secrets**")
        c2.code(blocco, language="toml", wrap_lines=True)
        st.markdown("".join(f"{i}. {p}\n" for i, p in enumerate(PASSI_SECRETS, 1)))
    st.markdown(CONSEGNA)
    note_html("La password compare solo qui: chiudendo la pagina non si recupera più "
              "(se serve, se ne genera una nuova).")


def _stato_database(a: App):
    if a.archivio.permanente:
        st.markdown('<div class="frase"><b>Database permanente collegato</b>Utenti, note, osservati, '
                    'obiettivi, giochi e brand restano salvati anche dopo i riavvii dell\'app.</div>',
                    unsafe_allow_html=True)
    else:
        st.warning("Database temporaneo: note, osservati e giochi si perdono a ogni riavvio dell'app "
                   "e gli utenti dei club si gestiscono incollando blocchi nei Secrets. Collega un "
                   "database PostgreSQL (per esempio Neon, gratuito) aggiungendo ai Secrets "
                   "[database] url = \"…la connection string di Neon, così com'è…\".")


# ------------------------------------------------------------------ utenti

def _utenti_attivi(a: App, da_secrets: dict, da_db: dict):
    section("Utenti", "chi può entrare nella piattaforma")
    righe = [{"Utente": u, "Club": d.get("club") or "– (tutte le squadre)", "Ruolo": d.get("ruolo", "staff"),
              "Dove": "Secrets (riserva)", "Stato": "attivo", "Ultimo accesso": "–"}
             for u, d in sorted(da_secrets.items())]
    righe += [{"Utente": u, "Club": d.get("club") or "– (tutte le squadre)", "Ruolo": d.get("ruolo"),
               "Dove": "database", "Stato": ("da attivare (password provvisoria)" if d["cambio_password"]
                                             else "attivo") if d["attivo"] else "disattivato",
               "Ultimo accesso": (d.get("ultimo_accesso") or "–")[:16].replace("T", " ")}
              for u, d in sorted(da_db.items()) if u not in da_secrets]
    if righe:
        show(pd.DataFrame(righe), voci=[])
    else:
        note_html("Nessun utente: il sito è in modalità demo.")


def _nuovo_accesso(a: App, esistenti: dict):
    section("Nuovo accesso per un club", "password provvisoria generata a caso")
    with st.form("nuovo_utente", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1.2, 1])
        squadra = c1.selectbox("Squadra", _squadre(a), index=None, placeholder="Scegli la squadra…")
        nome = c2.text_input("Utente", placeholder="es. forli-staff")
        ruolo = c3.selectbox("Ruolo", ["staff", "admin"],
                             help="staff: vede la piattaforma con la sua squadra; admin: vede "
                                  "anche questa pagina.")
        crea = st.form_submit_button("Crea l'accesso" if a.archivio.permanente else "Prepara l'accesso",
                                     type="primary")
    if not crea:
        return
    errore = accesso.errore_nome(nome, esistenti)
    if squadra is None:
        st.error("Scegli la squadra del club.")
        return
    if errore:
        st.error(f"Utente: {errore}.")
        return
    club = squadra.rsplit(" · ", 1)[0]
    pw = accesso.genera_password()
    u = nome.strip().lower()
    if a.archivio.permanente:
        a.archivio.add_user(u, accesso.hash_password(pw), club, ruolo, a.autore)
        st.success(f"Accesso creato per «{u}» ({club}): può entrare subito.")
        _password_mostrata(u, pw)
    else:
        st.success(f"Accesso preparato per «{u}».")
        _password_mostrata(u, pw, accesso.blocco_toml(u, pw, club, ruolo))


def _gestisci(a: App, da_secrets: dict, da_db: dict):
    section("Gestisci un utente", "nuova password, disattivazione")
    tutti = sorted(set(da_secrets) | set(da_db))
    if not tutti:
        note_html("Nessun utente da gestire.")
        return
    chi = st.selectbox("Utente", tutti, index=None, placeholder="Scegli l'utente…", key="gest_u")
    if chi is None:
        return
    if chi in da_secrets:
        d = da_secrets[chi]
        note_html("Utente dei Secrets (accesso di riserva): si modifica solo nei Secrets.")
        if st.button("Genera un nuovo blocco con una nuova password", key="pw_secrets"):
            pw = accesso.genera_password()
            st.success(f"Nuova password preparata per «{chi}»: sostituisci il suo blocco nei Secrets.")
            _password_mostrata(chi, pw, accesso.blocco_toml(chi, pw, d.get("club"), d.get("ruolo", "staff")))
        return
    d = da_db[chi]
    c1, c2 = st.columns(2)
    if c1.button("Nuova password provvisoria", key=f"pw_{chi}"):
        pw = accesso.genera_password()
        a.archivio.set_password(chi, accesso.hash_password(pw), cambio=True)
        st.success(f"Nuova password per «{chi}»: al prossimo accesso dovrà sceglierne una sua.")
        _password_mostrata(chi, pw)
    if d["attivo"]:
        if c2.button("Disattiva l'accesso", key=f"off_{chi}",
                     help="Non può più entrare; note e dati del club restano."):
            a.archivio.set_active(chi, False)
            st.rerun()
    elif c2.button("Riattiva l'accesso", key=f"on_{chi}"):
        a.archivio.set_active(chi, True)
        st.rerun()


# ------------------------------------------------------------------ brand

def _brand(a: App):
    section("Brand dei club", "logo e colori della squadra sulla piattaforma e sull'accesso")
    nomi = dict(a.ctx.bs.drop_duplicates("squadra_id")[["squadra_id", "squadra"]].values.tolist())
    ordine = sorted(nomi, key=lambda s: nomi[s])
    mia = a.utente.get("squadra_id")
    sid = st.selectbox("Squadra", ordine, index=ordine.index(mia) if mia in ordine else None,
                       format_func=nomi.get, placeholder="Scegli la squadra…", key="brand_sq")
    if sid is None:
        return
    correzioni = brand_club(sid)
    t = tema_club(int(sid), nomi[sid], json.dumps(correzioni, sort_keys=True))
    link = f"{_sito()}/?club={brand.slug(nomi[sid])}"
    c1, c2 = st.columns([1, 2])
    with c1:
        if t.logo:
            st.markdown(f'<div style="background:{t.fondo};border-radius:12px;padding:18px;'
                        f'text-align:center"><img src="{t.logo}" style="max-height:110px;max-width:100%">'
                        '</div>', unsafe_allow_html=True)
        else:
            note_html("Logo non raggiungibile dal sito della Lega in questo momento: si riprova da "
                      "solo. Si può indicare un altro indirizzo per il logo qui sotto.")
    with c2:
        origine = ("corretti dall'Amministrazione" if correzioni.get("primario") or correzioni.get("secondario")
                   else "ricavati dal logo" if t.da_logo else "predefiniti di ASSIST")
        st.markdown(f'Colori {origine}: '
                    + "".join(f'<span style="display:inline-block;width:26px;height:26px;border-radius:6px;'
                              f'background:{c};vertical-align:middle;margin:0 6px;border:1px solid #cfd6e2">'
                              f'</span><code>{esc(c)}</code>' for c in (t.fondo, t.accento)),
                    unsafe_allow_html=True)
        st.markdown("**Link di accesso del club** (la pagina di accesso con logo e colori):")
        st.code(link, language=None)
    with st.form(f"brand_{sid}"):
        k1, k2 = st.columns(2)
        primario = k1.color_picker("Colore principale (fascia in alto, scuro)", t.fondo)
        secondario = k2.color_picker("Colore di accento (pulsanti e strisce)", t.accento)
        logo_url = st.text_input("Indirizzo del logo (facoltativo)", correzioni.get("logo_url", ""),
                                 placeholder="lascia vuoto per quello del sito della Lega")
        fatto = st.form_submit_button("Salva il brand" if a.archivio.permanente
                                      else "Prepara il blocco per i Secrets")
    if not fatto:
        return
    valori = {"primario": primario, "secondario": secondario, "logo_url": logo_url.strip() or None}
    if a.archivio.permanente:
        a.archivio.set_brand(int(sid), valori, a.autore)
        tema_club.clear()
        if valori["logo_url"]:
            (brand.CACHE_LOGHI / f"{int(sid)}.png").unlink(missing_ok=True)
        st.success("Brand salvato: vale subito per tutti gli utenti del club.")
        st.rerun()
    righe = [f"[brand.{int(sid)}]", f'primario = "{primario}"', f'secondario = "{secondario}"']
    if valori["logo_url"]:
        righe.append(f'logo_url = "{valori["logo_url"]}"')
    st.code("\n".join(righe), language="toml")
    note_html("Incollalo nei Secrets (sostituendo un eventuale blocco [brand] della stessa "
              "squadra) e salva: i colori cambiano per tutti gli utenti del club.")


def render(a: App):
    if a.utente.get("ruolo") != "admin" or a.utente.get("demo"):
        st.error("Pagina riservata all'amministratore.")
        return
    _stato_database(a)
    da_secrets = {k.lower(): dict(v) for k, v in (secrets().get("utenti") or {}).items()}
    try:
        da_db = a.archivio.users(anche_disattivi=True) if a.archivio.permanente else {}
    except Exception:
        da_db = {}
        st.error("Database non raggiungibile in questo momento: riprova tra poco.")
    _utenti_attivi(a, da_secrets, da_db)
    _nuovo_accesso(a, {**da_secrets, **da_db})
    _gestisci(a, da_secrets, da_db)
    _brand(a)
