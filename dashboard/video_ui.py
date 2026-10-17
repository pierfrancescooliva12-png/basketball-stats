"""Dal video alla lavagna: lo staff carica una clip, tocca 4 punti dell'area (solo la prima volta
in un palazzetto) e indica attacco e difesa in pochi momenti; l'analisi su Modal restituisce la
bozza del gioco, che finisce tra i giochi salvati, già sincronizzata con la clip.

La clip va al servizio solo per l'analisi; nel gioco restano il nome del file e i tempi delle fasi.
"""

import base64
import os
import time
import uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from .stato import App
from .ui import note_html

_tocchi = components.declare_component("tocchi_assist", path=str(Path(__file__).resolve().parent / "tocchi"))
DURATA_MAX = 20


def configurato() -> bool:
    if os.environ.get("ASSIST_VIDEO_LOCALE"):
        return True
    try:
        for k in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"):
            if k in st.secrets and not os.environ.get(k):
                os.environ[k] = str(st.secrets[k])
    except Exception:
        pass
    return bool(os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"))


@st.cache_resource(show_spinner=False)
def _servizio():
    """Pubblica il servizio la prima volta (o quando cambia versione) e lo tiene pronto."""
    if os.environ.get("ASSIST_VIDEO_LOCALE"):                 # sviluppo: analisi sul computer
        from video import servizio_locale as S
    else:
        from video import servizio_modal as S
    S.pubblica()
    return S


def _attendi(chiamata, testo: str, stima: int):
    import modal
    barra = st.progress(0.0, text=testo)
    t0 = time.time()
    while True:
        try:
            out = chiamata.get(timeout=2)
            barra.progress(1.0, text=testo)
            return out
        except (TimeoutError, modal.exception.TimeoutError):
            passati = time.time() - t0
            barra.progress(min(0.95, passati / stima), text=f"{testo} · {int(passati)} s")


def _url(jpg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode()


def _club(a: App) -> str:
    return "".join(c for c in str(a.club or "demo") if c.isalnum() or c in "-_") or "demo"


def render(a: App, riferimento, contesto: str, nome_squadra: str):
    chiave = f"video_{contesto}_{riferimento}"
    S = st.session_state.setdefault(chiave, {"passo": "carica", "giro": 0})
    aperto = S["passo"] != "carica"
    with st.expander("🎬 Dal video · crea la bozza di un gioco da una clip", expanded=aperto):
        if not configurato():
            st.info("Il servizio di analisi video non è configurato: servono MODAL_TOKEN_ID e "
                    "MODAL_TOKEN_SECRET nei Secrets dell'app.")
            return
        try:
            _passo(a, S, chiave, riferimento, contesto, nome_squadra)
        except Exception as e:                                   # servizio non raggiungibile, clip illeggibile…
            st.error(f"Analisi non riuscita: {e}")
            if st.button("Ricomincia", key=f"{chiave}_errore"):
                st.session_state[chiave] = {"passo": "carica", "giro": S["giro"] + 1}
                st.rerun()


def _passo(a: App, S: dict, chiave: str, riferimento, contesto: str, nome_squadra: str):
    if S["passo"] == "carica":
        note_html("Carica una clip di un'azione (fino a 20 secondi). La prima volta in un palazzetto "
                  "tocchi i 4 angoli dell'area; poi indichi attacco e difesa in pochi momenti e la "
                  "piattaforma ricostruisce percorsi, passaggi, difesa e tempi delle fasi.")
        f = st.file_uploader("Clip", type=["mp4", "mov", "m4v"], key=f"{chiave}_file_{S['giro']}")
        c1, c2, c3 = st.columns([2, 1, 1])
        nome = c1.text_input("Nome del gioco", value=f"{nome_squadra} · dal video", key=f"{chiave}_nome")
        inizio = c2.number_input("Da secondo", min_value=0.0, value=0.0, step=0.5, key=f"{chiave}_inizio")
        durata = c3.number_input("Durata (s)", min_value=3.0, max_value=float(DURATA_MAX), value=15.0, step=1.0,
                                 key=f"{chiave}_durata")
        if f is not None and st.button("Analizza la clip", type="primary", key=f"{chiave}_via"):
            with st.spinner("Preparo il servizio di analisi (solo la prima volta, qualche minuto)…"):
                srv = _servizio()
            lavoro = uuid.uuid4().hex
            chiamata = srv.funzione("rileva").spawn(lavoro, _club(a), f.getvalue(), Path(f.name).suffix.lower() or ".mp4",
                                                   float(inizio), float(durata))
            out = _attendi(chiamata, "Riconosco giocatori e palla, seguo la telecamera…", 90)
            S.update(lavoro=lavoro, clip=f.name, nome=nome, rileva=out)
            if out.get("auto"):
                S.update(passo="verifica", controllo=out["controllo"], momenti=out["momenti"],
                         campo=f"Campo riconosciuto: {out['auto']['nome']}")
            else:
                S["passo"] = "punti"
            st.rerun()

    elif S["passo"] == "punti":
        out = S["rileva"]
        palazzetto = st.text_input("Nome del palazzetto (resta memorizzato: la prossima volta niente tocchi)",
                                   value=S.get("palazzetto", ""), key=f"{chiave}_palazzetto")
        v = _tocchi(modo="punti", img=_url(out["ancora"]), larghezza=out["dim"][0], altezza=out["dim"][1],
                    key=f"{chiave}_punti_{S['giro']}", default=None)
        if isinstance(v, dict) and v.get("punti") and v.get("t") != S.get("t"):
            S["t"] = v["t"]
            srv = _servizio()
            r = _attendi(srv.funzione("calibra").spawn(S["lavoro"], _club(a), v["punti"], palazzetto),
                         "Calibro il campo…", 20)
            S.update(passo="verifica", controllo=r["controllo"], momenti=r["momenti"], palazzetto=palazzetto,
                     campo="Campo calibrato con i tuoi 4 tocchi")
            st.rerun()

    elif S["passo"] == "verifica":
        st.markdown(f"**{S['campo']}.** Le righe verdi devono stare sopra quelle del parquet.")
        st.image(S["controllo"], use_container_width=True)
        c1, c2 = st.columns(2)
        if c1.button("Sì, il campo è giusto", type="primary", key=f"{chiave}_ok"):
            S["passo"] = "squadre"; st.rerun()
        if c2.button("No, tocco io i 4 punti", key=f"{chiave}_rifai"):
            S["passo"] = "punti"; S["giro"] += 1; st.rerun()

    elif S["passo"] == "squadre":
        momenti = [{**m, "img": _url(m["img"])} for m in S["momenti"]]
        dim = S["rileva"]["dim"]
        v = _tocchi(modo="squadre", momenti=momenti, larghezza=dim[0], altezza=dim[1],
                    key=f"{chiave}_squadre_{S['giro']}", default=None)
        if isinstance(v, dict) and v.get("marcature") and v.get("t") != S.get("t"):
            S["t"] = v["t"]
            srv = _servizio()
            tipo = "nostro" if contesto == "nostro" else "avversaria"
            gioco, qualita = _attendi(srv.funzione("costruisci").spawn(S["lavoro"], v["marcature"], S["nome"],
                                                                        S["clip"], tipo), "Ricostruisco il gioco…", 30)
            a.archivio.save_play(a.club, riferimento, gioco, a.autore)
            st.session_state[f"lavagna_apri_{contesto}_{riferimento}"] = gioco["id"]     # si apre nella lavagna
            S.update(passo="fatto", gioco=gioco["nome"], fasi=len(gioco["fasi"]), qualita=qualita)
            st.rerun()

    elif S["passo"] == "fatto":
        q = S["qualita"]
        st.success(f"Bozza salvata: **{S['gioco']}**, {S['fasi']} fasi.")
        note_html(f"Palla riconosciuta in {q['palla']} fotogrammi su {q['fotogrammi']}: dove è poca, "
                  "controlla chi ha la palla e i passaggi. Il gioco è aperto nella lavagna qui sotto: "
                  "correggi quello che serve e salvalo; con Video e la stessa clip li vedi scorrere insieme.")
        if st.button("Analizza un'altra clip", key=f"{chiave}_nuova"):
            st.session_state[chiave] = {"passo": "carica", "giro": S["giro"] + 1}
            st.rerun()
