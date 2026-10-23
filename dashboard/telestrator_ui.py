"""Lavagna sul video (telestrator): si apre un video dal dispositivo, lo si ferma e si disegna sul
fotogramma, come nelle trasmissioni NBA.

Il video non passa mai dal server: il componente lo apre nel browser (URL locale del file) e
non restituisce niente alla piattaforma. Disegni e momenti vivono solo nella pagina aperta e
spariscono quando la si chiude: nulla viene salvato.
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from .ui import note_html

_lavagna_video = components.declare_component(
    "telestrator_assist", path=str(Path(__file__).resolve().parent / "telestrator"))


def render():
    note_html("Apri un video della partita o dell'allenamento: fermalo e disegna sul fotogramma (tagli, passaggi, "
              "blocchi, cerchi sotto i giocatori, riflettore, aree, testo). Ogni fermo-immagine disegnato diventa "
              "un momento della sessione, da richiamare con un tocco durante la riunione video. Il video non viene "
              "caricato su ASSIST e niente viene salvato: chiudendo la pagina sparisce tutto.")
    _lavagna_video(key="telestrator", default=None)
    st.caption("Consiglio: sul telefono gira lo schermo in orizzontale; su computer usa lo schermo intero e la "
               "tastiera (spazio, frecce, Z).")
