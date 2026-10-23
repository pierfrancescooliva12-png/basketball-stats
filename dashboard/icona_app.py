"""Icona della piattaforma sulla schermata Home (iPhone e Android) con il logo del club.

La pagina di base la genera Streamlit, con la sua icona: qui un piccolo script nella pagina
sostituisce icona (apple-touch-icon), manifest, nome e colore della barra con quelli del club
(o del marchio ASSIST). iPhone e Android li leggono nel momento in cui si sceglie "Aggiungi a
Home", quindi basta aprire la piattaforma dal link del club o fare l'accesso prima di aggiungerla."""

import base64
import json

import streamlit as st
import streamlit.components.v1 as components

from basket import config, icona

JS = """
<script>
(function () {
  var d = window.parent.document, v = %s;
  function link(rel, href) {
    var e = d.querySelector('link[rel="' + rel + '"]');
    if (!e) { e = d.createElement("link"); e.rel = rel; d.head.appendChild(e); }
    if (e.getAttribute("href") !== href) e.setAttribute("href", href);
  }
  function meta(name, content) {
    var e = d.querySelector('meta[name="' + name + '"]');
    if (!e) { e = d.createElement("meta"); e.name = name; d.head.appendChild(e); }
    e.setAttribute("content", content);
  }
  link("apple-touch-icon", v.apple);
  link("manifest", v.manifest);
  meta("apple-mobile-web-app-title", v.titolo);
  meta("apple-mobile-web-app-capable", "yes");
  meta("mobile-web-app-capable", "yes");
  meta("theme-color", v.colore);
})();
</script>
"""

# l'elemento con lo script non deve occupare spazio nella pagina
CSS = """<style>.st-key-icona_app {display: none;}</style>"""


def _logo(tema) -> bytes | None:
    uri = getattr(tema, "logo", None) or ""
    if "," not in uri:
        return None
    try:
        return base64.b64decode(uri.split(",", 1)[1])
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=24 * 3600, max_entries=40)
def _file(chiave: str, nome: str, colore: str, logo: bytes | None, quota: float = 0.66) -> dict:
    return icona.prepara(chiave, nome, logo, colore, quota=quota)


def imposta(tema=None) -> None:
    """Icona del club (dal suo tema) o, senza club, il marchio ASSIST."""
    try:
        if tema is not None and getattr(tema, "nome", None):
            logo = _logo(tema)
            v = (_file(tema.nome, tema.nome, tema.fondo, logo) if logo else        # senza logo: il marchio
                 _file(tema.nome, tema.nome, tema.fondo, icona.marchio(), 0.9))
        else:
            v = _file(config.BRAND, config.BRAND, "#0b1220", icona.marchio(), 0.9)
    except Exception:                    # l'icona non deve mai bloccare la piattaforma
        return
    st.markdown(CSS, unsafe_allow_html=True)
    with st.container(key="icona_app"):
        components.html(JS % json.dumps(v), height=0)
