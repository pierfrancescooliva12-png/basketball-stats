"""Lavagna sul video: il video resta sul dispositivo e niente torna alla piattaforma."""

from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "dashboard" / "telestrator" / "index.html"


def test_il_video_non_lascia_il_dispositivo():
    s = HTML.read_text()
    assert "URL.createObjectURL" in s and "URL.revokeObjectURL" in s
    # nessun invio: niente rete e nessun valore restituito a Streamlit
    for vietato in ("fetch(", "XMLHttpRequest", "sendBeacon", "streamlit:setComponentValue", "localStorage",
                    "indexedDB", "FormData"):
        assert vietato not in s, vietato


def test_strumenti_disponibili():
    s = HTML.read_text()
    for t in ("penna", "percorso", "freccia", "passaggio", "blocco", "linea", "cerchio", "riflettore", "area",
              "testo", "gomma"):
        assert f'data-t="{t}"' in s, t
    for id_ in ("annulla", "ripeti", "pulisci", "indietro1", "avanti1", "schermo", "velocita"):
        assert f'id="{id_}"' in s, id_
