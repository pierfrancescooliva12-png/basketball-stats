"""Schermata di accesso nello stile dei report (fascia blu notte, scheda bianca) e, finché
non c'è nessun utente, lo strumento per creare le credenziali dell'amministratore."""

import time

import streamlit as st

from basket import accesso, config

from .ui import esc

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');
:root {--crema: #faf9f5; --carta: #f3f1ea; --pill: #f0eee6; --linea: #e3e0d4; --ink: #141413; --ink-2: #3d3d3a;
  --grigio: #6f6d66; --acc: #e8631c; --sans: 'Instrument Sans', system-ui, sans-serif; --serif: 'Newsreader', Georgia, serif;}
header[data-testid="stHeader"] {display: none;}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {background: var(--crema) !important;}
.block-container {padding-top: 1.4rem; max-width: 1240px;}
.accesso-barra {display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 0 0 54px;}
.accesso-barra .marchio {display: flex; align-items: center; gap: 10px; color: var(--ink);}
.accesso-barra .marchio svg {height: 20px; width: auto; border-radius: 0;}
.accesso-barra .marchio img {height: 30px; width: auto; max-width: 120px; object-fit: contain;}
.accesso-barra a.pillola {display: inline-flex; align-items: center; height: 30px; padding: 0 14px; border-radius: 999px;
  background: var(--pill); border: 1px solid var(--linea); font: 500 14px var(--sans); color: var(--ink) !important;
  text-decoration: none;}
.accesso-hero {color: var(--ink); padding: 0 0 20px;}
.accesso-hero .club-logo {height: 76px; width: auto; max-width: 180px; object-fit: contain; margin-bottom: 22px;}
.accesso-hero h1 {font: 400 clamp(30px, 3.3vw, 46px)/1.16 var(--serif) !important; letter-spacing: -.012em; margin: 0 0 30px;
  color: var(--ink); padding: 0;}
.accesso-hero h1 b {font: 600 1em/1.16 var(--sans); letter-spacing: -.025em;}
.accesso-hero ul {list-style: none; padding: 0; margin: 0; border-top: 1px solid var(--linea);}
.accesso-hero li {display: grid; grid-template-columns: 34px 1fr; gap: 10px; padding: 13px 0; border-bottom: 1px solid var(--linea);
  font: 400 16px/1.45 var(--sans); color: var(--ink-2);}
.accesso-hero li span {font: 500 13px var(--sans); color: var(--acc); padding-top: 2px;}
.accesso-titolo {font: 400 44px/1.05 var(--serif); color: var(--ink); margin: 6px 0 6px; letter-spacing: -.01em;}
.accesso-sotto {color: var(--grigio); font: 400 16px/1.5 var(--sans); margin-bottom: 16px;}
[data-testid="stForm"] {background: var(--carta); border: 1px solid var(--linea) !important; border-radius: 14px;
  padding: 24px 24px 16px; box-shadow: none;}
[data-testid="stForm"] label p {font: 500 14px var(--sans) !important; color: var(--ink) !important; letter-spacing: 0 !important;
  text-transform: none !important;}
[data-testid="stForm"] [data-baseweb="input"] {background: #fff !important; border: 1px solid var(--linea) !important;
  border-radius: 10px !important;}
[data-testid="stForm"] [data-baseweb="input"]:focus-within {border-color: var(--ink) !important;}
[data-testid="stForm"] input {font: 400 16px var(--sans) !important; color: var(--ink) !important; background: #fff !important;}
[data-testid="stForm"] button[kind="primaryFormSubmit"], [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--ink) !important; border: 1px solid var(--ink) !important; color: var(--crema) !important;
  border-radius: 999px !important; font: 500 16px var(--sans) !important; min-height: 46px;}
[data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"]:hover {background: #2b2b29 !important;}
[data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] p {font: 500 16px var(--sans) !important; color: var(--crema) !important;}
.accesso-piede {color: var(--grigio); font: 400 14px/1.5 var(--sans); margin-top: 14px;}
.accesso-piede a {color: var(--ink) !important;}
.accesso-hero h1, .accesso-hero h1 b {text-transform: none !important;}
.accesso-hero ul {padding-left: 0 !important; margin-left: 0 !important;}
.accesso-hero li {margin: 0 !important; list-style: none !important;}
.accesso-hero li::marker {content: none;}
.accesso-hero h1 a, .accesso-barra a svg[class*="Icon"] {display: none !important;}
[data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] {box-shadow: none !important;}
/* su telefono prima il modulo di accesso, poi la presentazione */
@media (max-width: 640px) {[data-testid="stHorizontalBlock"] {flex-direction: column-reverse !important;}}
@media (max-width: 760px) {.accesso-barra {margin-bottom: 26px;} .accesso-titolo {font-size: 36px;}
  .accesso-hero .club-logo {height: 56px;}}
</style>
"""

def _scritta(altezza: int = 20) -> str:
    """La scritta ΛSSIST (nuovo logo) all'altezza data."""
    import re
    svg = (config.LOGO_DIR / "assist-scritta.svg").read_text(encoding="utf-8")
    return re.sub(r' width="\d+" height="\d+"', f' height="{altezza}"', svg, count=1)

PUNTI = ["Scouting dell'avversaria e report pre-partita in PDF e Word",
         "Chiavi della partita e verifica dopo la gara",
         "Sviluppo dei tuoi giocatori, obiettivi e mercato",
         "Previsioni e dati di Serie A2 e B Nazionale aggiornati ogni giorno"]


def _barra(tema=None):
    """Barra in alto: marchio ASSIST (o logo e nome del club) e il link alla pagina pubblica."""
    if tema is not None and tema.logo:
        sx = f'<img src="{tema.logo}" alt="">{_scritta()}'
    else:
        sx = _scritta()
    st.markdown(f'<div class="accesso-barra"><div class="marchio">{sx}</div>'
                f'<a class="pillola" href="https://{config.SITO}" target="_blank" rel="noopener">{esc(config.SITO)} ↗</a></div>',
                unsafe_allow_html=True)


def _hero(tema=None):
    punti = "".join(f"<li><span>{i:02d}</span>{esc(p)}</li>" for i, p in enumerate(PUNTI, 1))
    if tema is not None:
        st.markdown(f'<div class="accesso-hero"><h1><b>{esc(tema.nome)}.</b> L\'area dello staff tecnico, con '
                    f'{esc(config.BRAND)}: la prossima avversaria, le chiavi della partita e la crescita dei vostri '
                    f'giocatori, aggiornate ogni giorno.</h1><ul>{punti}</ul></div>', unsafe_allow_html=True)
        return
    st.markdown(f'<div class="accesso-hero"><h1><b>Area riservata agli staff tecnici.</b> Scouting dell\'avversaria, '
                'chiavi della partita, sviluppo dei giocatori e mercato per la Serie A2 e la B Nazionale, aggiornati '
                f'ogni giorno.</h1><ul>{punti}</ul></div>', unsafe_allow_html=True)


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
    tema = _tema_link()                   # pagina di accesso con il brand del club
    st.markdown(CSS, unsafe_allow_html=True)   # dopo il brand: fondo crema e pulsante scuro restano
    from . import icona_app
    icona_app.imposta(tema)               # "Aggiungi a Home" dal link del club: il suo logo
    from . import intro
    intro.mostra(tema)                    # intro animata, una volta per sessione
    _barra(tema)
    stato = st.session_state.setdefault("_accesso", {})
    c1, _, c2 = st.columns([1.2, 0.12, 0.9], vertical_alignment="top")
    with c1:
        _hero(tema)
    with c2:
        st.markdown('<div class="accesso-titolo">Accedi</div><div class="accesso-sotto">'
                    'Con le credenziali ricevute dal tuo club.</div>', unsafe_allow_html=True)
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
    from basket import brand
    tema = _tema_link(brand.slug(utente["club"])) if utente.get("club") else None
    st.markdown(CSS, unsafe_allow_html=True)
    from . import icona_app
    icona_app.imposta(tema)
    _barra(tema)
    c1, _, c2 = st.columns([1.2, 0.12, 0.9], vertical_alignment="top")
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
