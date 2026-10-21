"""Schermata di accesso nello stile dei report (fascia blu notte, scheda bianca) e, finché
non c'è nessun utente, lo strumento per creare le credenziali dell'amministratore."""

import time

import streamlit as st

from basket import accesso, config

from .ui import esc

CSS = """
<style>
header[data-testid="stHeader"] {display: none;}
.block-container {padding-top: 2.2rem; max-width: 1180px;}
.accesso-hero {position: relative; overflow: hidden; border-radius: 16px; background: var(--navy);
  color: #fff; padding: 34px 32px 64px; min-height: 420px;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 34px), 0 100%);}
.accesso-hero::before, .accesso-hero::after {content: ""; position: absolute; top: -10%; bottom: -10%;
  transform: skewX(-22deg);}
.accesso-hero::before {left: 84%; width: 16px; background: var(--accent);}
.accesso-hero::after {left: calc(84% + 16px); right: -40%; background: var(--navy-2);}
.accesso-hero > * {position: relative; z-index: 1;}
.accesso-hero .campo-bg {position: absolute; right: 18%; bottom: -40px; width: 380px; height: auto;
  opacity: .09; z-index: 0; pointer-events: none;}
.accesso-hero svg {width: 64px; height: 64px; border-radius: 14px;}
.accesso-hero .marchio {font: italic 700 3.4rem/1 var(--cond); letter-spacing: .06em; margin-top: 18px;
  text-transform: uppercase;}
.accesso-hero .slogan {font: 600 .74rem 'Barlow', sans-serif; letter-spacing: .16em;
  text-transform: uppercase; color: var(--accent); margin-top: 8px;}
.accesso-hero ul {list-style: none; padding: 0; margin: 28px 0 0; max-width: 80%;}
.accesso-hero li {color: var(--on-navy); font-size: 1rem; margin: 10px 0; padding-left: 18px;
  position: relative;}
.accesso-hero li::before {content: ""; position: absolute; left: 0; top: .5em; width: 8px; height: 8px;
  background: var(--accent); transform: skewX(-14deg);}
.accesso-titolo {font: italic 700 2.1rem/1 var(--cond); text-transform: uppercase; color: var(--navy);
  margin: 6px 0 4px;}
.accesso-sotto {color: var(--text-2); font-size: .95rem; margin-bottom: 14px;}
[data-testid="stForm"] {background: var(--surface); border: 1px solid var(--line) !important;
  border-top: 4px solid var(--accent) !important; border-radius: 14px; padding: 22px 22px 14px;
  box-shadow: var(--shadow);}
.accesso-piede {color: var(--muted); font-size: .8rem; margin-top: 12px;}
@media (max-width: 760px) {.accesso-hero {min-height: 0; padding: 22px 20px 46px;}
  .accesso-hero::before, .accesso-hero::after, .accesso-hero ul {display: none;}
  .accesso-hero .marchio {font-size: 2.6rem; margin-top: 12px;}}
</style>
"""

PUNTI = ["Scouting dell'avversaria e report pre-partita in PDF e Word",
         "Chiavi della partita e verifica dopo la gara",
         "Sviluppo dei tuoi giocatori, obiettivi e mercato",
         "Previsioni e dati di Serie A2 e B Nazionale aggiornati ogni giorno"]


# mezzo campo stilizzato, appena visibile sullo sfondo della testata
CAMPO = ('<svg class="campo-bg" viewBox="0 0 300 280" fill="none" stroke="#ffffff" stroke-width="3" '
         'aria-hidden="true"><path d="M0 2 H300"/><rect x="100" y="2" width="100" height="120"/>'
         '<circle cx="150" cy="122" r="36"/><path d="M22 2 V60 A128 128 0 0 0 278 60 V2"/>'
         '<circle cx="150" cy="30" r="9"/><path d="M128 18 H172"/></svg>')


def _hero(tema=None):
    punti = "".join(f"<li>{esc(p)}</li>" for p in PUNTI)
    if tema is not None:
        logo = f'<img class="club-logo" src="{tema.logo}" alt="">' if tema.logo else ""
        st.markdown(f'<div class="accesso-hero">{CAMPO}{logo}<div class="marchio">{esc(tema.nome)}</div>'
                    f'<div class="slogan">Area staff · con {esc(config.BRAND)}</div><ul>{punti}</ul></div>',
                    unsafe_allow_html=True)
        return
    mark = (config.LOGO_DIR / "assist-mark.svg").read_text(encoding="utf-8")
    st.markdown(f'<div class="accesso-hero">{CAMPO}{mark}<div class="marchio">{esc(config.BRAND)}</div>'
                f'<div class="slogan">{esc(config.BRAND_TAGLINE)}</div><ul>{punti}</ul></div>',
                unsafe_allow_html=True)


def club_da_link(voluto: str | None = None) -> tuple[int, str] | None:
    """La squadra del link di accesso del club (?club=luiss-roma), se esiste."""
    voluto = (voluto or st.query_params.get("club") or "").strip().lower()
    if not voluto:
        return None
    from basket import brand, db
    try:
        conn = db.connect(config.DB_PATH, readonly=True)
        righe = conn.execute("SELECT squadra_id, nome FROM squadre ORDER BY stagione DESC").fetchall()
    except Exception:
        return None
    for sid, nome in righe:
        if brand.slug(nome) == voluto or str(sid) == voluto:
            return int(sid), nome
    return None


def _tema_link(voluto: str | None = None):
    club = club_da_link(voluto)
    if club is None:
        return None
    import json
    from basket import brand
    from .stato import brand_club, tema_club
    try:
        tema = tema_club(club[0], club[1], json.dumps(brand_club(club[0]), sort_keys=True))
    except Exception:
        return None
    st.markdown(brand.css(tema), unsafe_allow_html=True)
    return tema


def login(utenti: dict, arch=None) -> None:
    """Mostra la schermata di accesso e ferma la pagina finché le credenziali non sono giuste."""
    st.markdown(CSS, unsafe_allow_html=True)
    tema = _tema_link()                   # pagina di accesso con il brand del club
    from . import intro
    intro.mostra(tema)                    # intro animata, una volta per sessione
    stato = st.session_state.setdefault("_accesso", {})
    c1, _, c2 = st.columns([1.25, 0.08, 1], vertical_alignment="center")
    with c1:
        _hero(tema)
    with c2:
        st.markdown('<div class="accesso-titolo">Accedi</div><div class="accesso-sotto">'
                    'Area riservata agli staff tecnici.</div>', unsafe_allow_html=True)
        attesa = accesso.attesa(stato, time.time())
        with st.form("login"):
            u = st.text_input("Utente", autocomplete="username")
            p = st.text_input("Password", type="password", autocomplete="current-password")
            entra = st.form_submit_button("Accedi", type="primary", width="stretch")
        if entra:
            if attesa:
                st.error(f"Troppi tentativi sbagliati: riprova tra {attesa} secondi.")
            else:
                ok = accesso.authenticate(utenti, u, p)
                st.session_state["_accesso"] = accesso.registra(stato, bool(ok), time.time())
                if ok:
                    for k in [k for k in st.session_state if k != "_accesso"]:
                        del st.session_state[k]     # filtri e scelte di prima non valgono più
                    st.query_params.clear()
                    st.session_state["utente"] = ok
                    if ok.get("fonte") == "database" and arch is not None:
                        try:
                            arch.touch_login(ok["username"])
                        except Exception:
                            pass
                    st.rerun()
                time.sleep(1)                      # rallenta i tentativi automatici
                st.error("Utente o password non corretti.")
        elif attesa:
            st.warning(f"Troppi tentativi sbagliati: riprova tra {attesa} secondi.")
        st.markdown('<div class="accesso-piede">Credenziali personali e non cedibili. '
                    f'Per un nuovo accesso scrivi a <a href="mailto:{config.CONTATTO}">{config.CONTATTO}</a>.</div>',
                    unsafe_allow_html=True)
    st.stop()


def primo_accesso() -> None:
    """Finché non c'è nessun utente (modalità demo): crea il blocco da incollare nei secrets.
    La password resta in questa pagina: nei secrets va solo l'hash."""
    with st.expander("Amministratore · crea le credenziali di accesso"):
        st.markdown('<div class="note">Il sito è aperto a tutti finché nei <b>Secrets</b> di '
                    'Streamlit non c\'è almeno un utente. Scegli utente e password: qui sotto '
                    'compare il testo da incollare in <b>'
                    + ('Render › il servizio › Environment › Secret Files › secrets.toml' if config.SU_RENDER
                       else 'share.streamlit.io › la tua app › Settings › Secrets') + '</b>. Contiene solo l\'impronta cifrata della password, '
                    'non la password. Dopo il salvataggio il sito chiede l\'accesso.</div>',
                    unsafe_allow_html=True)
        with st.form("primo_accesso", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            u = c1.text_input("Utente", autocomplete="off")
            p1 = c2.text_input("Password", type="password", autocomplete="new-password")
            p2 = c3.text_input("Ripeti la password", type="password", autocomplete="new-password")
            fatto = st.form_submit_button("Crea il blocco per i Secrets", type="primary")
        if fatto:
            if accesso.errore_nome(u, []):
                st.error(f"Utente: {accesso.errore_nome(u, [])}.")
            elif len(p1) < 10:
                st.error("La password deve avere almeno 10 caratteri.")
            elif p1 != p2:
                st.error("Le due password non coincidono.")
            else:
                st.code(accesso.blocco_toml(u, p1, None, "admin"), language="toml")
                st.markdown('<div class="note">Copia il testo, incollalo nei Secrets e salva. '
                            'Ruolo admin senza club: vedi tutte le squadre e scegli dalla Home '
                            'quella da seguire.</div>', unsafe_allow_html=True)


def _nuova_password(utente: dict, arch, chiave: str, vecchia_richiesta: bool) -> bool:
    """Modulo per la nuova password; True se è stata salvata."""
    with st.form(chiave, clear_on_submit=True):
        vecchia = st.text_input("Password attuale", type="password",
                                autocomplete="current-password") if vecchia_richiesta else None
        nuova = st.text_input("Nuova password (almeno 10 caratteri)", type="password",
                              autocomplete="new-password")
        ripeti = st.text_input("Ripeti la nuova password", type="password",
                               autocomplete="new-password")
        salva = st.form_submit_button("Salva la nuova password", type="primary", width="stretch")
    if not salva:
        return False
    if vecchia_richiesta:
        attuale = (arch.users().get(utente["username"]) or {}).get("password_hash", "")
        if not accesso.verify_password(vecchia or "", attuale):
            st.error("La password attuale non è corretta.")
            return False
    errore = accesso.errore_password(nuova, ripeti, vecchia)
    if errore:
        st.error(f"Nuova password: {errore}.")
        return False
    arch.set_password(utente["username"], accesso.hash_password(nuova), cambio=False)
    return True


def cambio_obbligatorio(utente: dict, arch) -> None:
    """Primo accesso con la password iniziale: prima di entrare si sceglie la propria."""
    st.markdown(CSS, unsafe_allow_html=True)
    from basket import brand
    tema = _tema_link(brand.slug(utente["club"])) if utente.get("club") else None
    c1, _, c2 = st.columns([1.25, 0.08, 1], vertical_alignment="center")
    with c1:
        _hero(tema)
    with c2:
        st.markdown('<div class="accesso-titolo">Scegli la tua password</div><div class="accesso-sotto">'
                    f'Primo accesso di «{esc(utente["username"])}»: la password ricevuta è '
                    'provvisoria. Scegline una tua: la conosci solo tu.</div>', unsafe_allow_html=True)
        if _nuova_password(utente, arch, "pw_primo", vecchia_richiesta=False):
            st.session_state["utente"] = {**utente, "cambio": False}
            st.rerun()
    st.stop()


@st.dialog("Cambia la password")
def cambia_password(utente: dict, arch) -> None:
    if _nuova_password(utente, arch, "pw_cambio", vecchia_richiesta=True):
        st.success("Password aggiornata: vale dal prossimo accesso.")
