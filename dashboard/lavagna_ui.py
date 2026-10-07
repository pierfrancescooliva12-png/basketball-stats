"""Lavagna: disegno dei giochi (propri e delle avversarie) dentro la dashboard.

La lavagna è una pagina HTML a sé (dashboard/lavagna/lavagna.html) usata come componente
Streamlit: riceve i giochi salvati del club e restituisce le azioni dello staff (salva,
elimina). I giochi sono salvati nell'archivio del club e disegnati fase per fase nei PDF.
"""

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from basket.report_pdf import build_giochi, slug

from .lavagna.catalogo import SCHEMI
from .stato import App
from .ui import note_html, section

BASE = Path(__file__).resolve().parent / "lavagna"
CARTELLA = BASE / "componente"


def pagina_componente() -> str:
    """index.html del componente: la lavagna in modalità Streamlit."""
    corpo = (BASE / "lavagna.html").read_text()
    return ('<!doctype html><html lang="it" class="in-app"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<script>window.LAVAGNA_MODALITA = "streamlit";</script></head><body>'
            + corpo + "</body></html>\n")


def _prepara():
    f = CARTELLA / "index.html"
    testo = pagina_componente()
    try:
        CARTELLA.mkdir(exist_ok=True)
        if not f.exists() or f.read_text() != testo:
            f.write_text(testo)
    except OSError:
        pass


_prepara()
_lavagna = components.declare_component("lavagna_assist", path=str(CARTELLA))


@st.cache_data(show_spinner=False)
def _pdf_archivio() -> bytes:
    return build_giochi(SCHEMI, "Archivio schemi ASSIST")


def giochi(a: App, riferimento) -> list[dict]:
    return a.archivio.plays(a.club, riferimento)


def render(a: App, riferimento: int, contesto: str, titolo: str, nome_squadra: str):
    """Lavagna con i giochi della squadra riferimento ("nostro" o "avversaria")."""
    valore = _lavagna(giochi=giochi(a, riferimento), contesto=contesto, titolo=titolo,
                      schemi=SCHEMI, tema="dark", key=f"lavagna_{contesto}_{riferimento}",
                      default=None)
    chiave = f"lavagna_ultima_{contesto}_{riferimento}"
    if isinstance(valore, dict) and valore.get("t") != st.session_state.get(chiave):
        st.session_state[chiave] = valore.get("t")
        if valore.get("azione") == "salva" and valore.get("gioco"):
            a.archivio.save_play(a.club, riferimento, valore["gioco"], a.autore)
        elif valore.get("azione") == "elimina" and valore.get("id"):
            a.archivio.delete_play(a.club, valore["id"])
        st.rerun()        # la lavagna riceve subito l'elenco aggiornato
    salvati = giochi(a, riferimento)
    if not a.archivio.permanente:
        note_html("Archivio di prova: i giochi restano finché l'app non viene riavviata. Con "
                  "l'archivio permanente del club restano salvati e condivisi con lo staff.")
    if salvati:
        st.download_button(f"⬇ PDF dei giochi ({len(salvati)})",
                           build_giochi(salvati, nome_squadra),
                           file_name=f"giochi_{slug(nome_squadra)}.pdf", mime="application/pdf",
                           key=f"pdf_giochi_{contesto}_{riferimento}")
    return salvati


def render_nostri(a: App):
    st.download_button(f"⬇ Archivio degli schemi pronti in PDF ({len(SCHEMI)})", _pdf_archivio(),
                       file_name="archivio_schemi_assist.pdf", mime="application/pdf",
                       key="pdf_archivio_schemi")
    sid = a.mia_squadra
    if sid is None:
        st.info("Scegli la tua squadra nella Home per disegnare i vostri giochi.")
        return
    nome = a.profile.set_index("squadra_id").loc[sid, "squadra"]
    note_html("Disegna i vostri giochi: scegli lo strumento, trascina il dito dal giocatore "
              "lungo il percorso, poi \"+ Fase successiva\". Salvati, finiscono nel PDF dei giochi "
              "con tutte le fasi.")
    render(a, sid, "nostro", f"Giochi di {nome}", nome)


def render_avversaria(a: App, sid: int):
    nome = a.profile.set_index("squadra_id").loc[sid, "squadra"]
    section("Giochi dell'avversaria", "disegnati dallo staff sulla lavagna; finiscono nel PDF "
            "di scouting, fase per fase", key="lavagna")
    n = len(giochi(a, sid))
    with st.expander(f"Apri la lavagna · {n} giochi salvati di {nome}" if n else
                     f"Apri la lavagna per disegnare i giochi di {nome}", expanded=False):
        render(a, sid, "avversaria", f"Giochi di {nome}", nome)


def giochi_json(a: App, sid) -> str:
    """Giochi dell'avversaria per il PDF di scouting (stringa, per la cache del PDF)."""
    try:
        return json.dumps(giochi(a, sid))
    except Exception:
        return "[]"
