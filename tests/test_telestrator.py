"""Lavagna sul video: il video resta sul dispositivo; alla piattaforma tornano solo, su richiesta,
gli inizi dei quarti e i giochi creati dalle posizioni sul fotogramma."""

import re
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "dashboard" / "telestrator" / "index.html"


def test_il_video_non_lascia_il_dispositivo():
    s = HTML.read_text()
    assert "URL.createObjectURL" in s and "URL.revokeObjectURL" in s
    # nessun invio in rete né archiviazione nel browser
    for vietato in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "indexedDB", "FormData",
                    "toDataURL", "toBlob"):
        assert vietato not in s, vietato
    # un solo punto da cui un valore torna a Streamlit, e solo per inizi dei quarti e giochi
    assert s.count("streamlit:setComponentValue") == 1
    assert re.search(r"function invia\(valore\) \{\s*if \(IN_APP\) window\.parent\.postMessage\("
                     r"\{ isStreamlitMessage: true, type: \"streamlit:setComponentValue\"", s)
    azioni = re.findall(r"invia\(\{ azione: \"(\w+)\"", s)
    assert sorted(azioni) == ["gioco", "sync"], azioni


def test_lettura_della_grafica_sul_dispositivo():
    s = HTML.read_text()
    cartella = HTML.parent / "ocr"
    # l'OCR è servito dalla piattaforma insieme al componente, non da servizi esterni
    for f in ("tesseract.min.js", "worker.min.js", "tesseract-core-simd-lstm.wasm.js", "tesseract-core-lstm.wasm.js",
              "eng.traineddata.gz", "LICENSE-tesseract.js.md", "LICENSE-tesseract-core"):
        assert (cartella / f).exists(), f
    assert 'new URL("ocr/", location.href)' in s
    esterni = set(re.findall(r"https?://([\w.-]+)", s))
    assert esterni <= {"fonts.googleapis.com"}, esterni


def test_strumenti_disponibili():
    s = HTML.read_text()
    for t in ("penna", "percorso", "freccia", "passaggio", "blocco", "linea", "cerchio", "riflettore", "area",
              "testo", "gomma", "mano"):
        assert f'data-t="{t}"' in s, t
    for id_ in ("annulla", "ripeti", "pulisci", "indietro1", "avanti1", "schermo", "velocita",
                "zoomPiu", "zoomMeno", "zoomRiporta", "tasti-tag", "seq-tag", "lista-tag",
                "lista-cronaca", "qui", "seq-cronaca", "tara", "posiziona", "crea-gioco",
                "ocr-zona", "ocr-avvia", "ocr-ferma", "ocr-da"):
        assert f'id="{id_}"' in s, id_
    for p in ("azioni", "cronaca", "gioco"):
        assert f'data-p="{p}"' in s, p


def test_cronaca_per_il_componente(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from basket import config, db, update
    from basket.contesto import Contesto
    from dashboard import telestrator_ui as TU
    from tests.test_pbp import Client
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    ctx = Contesto(conn, "x2627")
    pid = ctx.ev["partita_id"].iloc[0]
    ev = TU.eventi(SimpleNamespace(ctx=ctx), pid)
    assert ev and all(e["tipo"] in TU.TESTI for e in ev)
    assert all(0 <= e["s"] <= 600 and re.fullmatch(r"\d\d:\d\d", e["cron"]) for e in ev if e["p"] <= 4)
    assert any(e["g"] for e in ev) and any(e["pt"] for e in ev)
    assert all(e["m"] >= 1.25 * e["s"] - 0.1 for e in ev)


def test_tempi_morti_dalla_cronaca():
    import pandas as pd

    from basket import tiri as T
    righe = [  # n, periodo, secondi (dall'inizio partita), tipo
        (0, 1, 10, "tiro2_fatto"), (1, 1, 30, "fallo"), (2, 1, 30, "tl_fatto"), (3, 1, 30, "tl_sbagliato"),
        (4, 1, 30, "cambio"), (5, 1, 60, "timeout"), (6, 1, 60, "cambio"), (7, 1, 60, "cambio"),
        (8, 1, 90, "cambio"), (9, 1, 90, "cambio"), (10, 1, 120, "persa"), (11, 1, 130, "persa"),
        (12, 1, 130, "recupero"), (13, 1, 200, "tiro3_fatto"), (14, 4, 2390, "tiro2_fatto"),
        (15, 4, 2395, "tiro2_fatto")]
    ev = pd.DataFrame(righe, columns=["n", "periodo", "secondi", "tipo"])
    m, fine = T.tempi_reali(ev)
    r = 1.25
    assert m[0] == r * 10
    assert m[1] == m[2] - 12 == r * 30                    # il primo libero dopo la pausa del fallo
    assert m[3] == r * 30 + 12 + 18
    assert m[5] == r * 60 + 12 + 36                       # il cambio a gioco già fermo non aggiunge nulla
    assert m[8] == r * 90 + 12 + 36 + 75                  # cambi allo stesso secondo: una sola fermata
    assert m[11] == r * 130 + 12 + 36 + 75 + 10 + 4      # palla persa a gioco fermo; il recupero no
    assert m[13] == r * 200 + 12 + 36 + 75 + 10 + 4
    assert fine[1] == r * 600 + 12 + 36 + 75 + 10 + 4
    # ultimi 2' dell'ultimo quarto: il cronometro si ferma dopo ogni canestro
    assert abs(m[15] - m[14] - (r * 5 + 8)) < 0.11


def test_video_dal_solo_salto_a_due():
    import pandas as pd

    from basket import tiri as T
    ev = pd.DataFrame([(0, 1, 100, "tiro2_fatto"), (1, 1, 300, "timeout"), (2, 2, 700, "tiro3_fatto"),
                       (3, 3, 1300, "tiro2_fatto")], columns=["n", "periodo", "secondi", "tipo"])
    _, fine = T.tempi_reali(ev)
    v = T.stime_video(ev, {1: 60})
    assert v[0] == 60 + 1.25 * 100 and fine[1] == 1.25 * 600 + 75
    assert v[2] == 60 + fine[1] + T.PAUSA_QUARTI + 1.25 * 100
    assert v[3] == v[2] - 1.25 * 100 + fine[2] + T.INTERVALLO + 1.25 * 100
    # l'inizio del 2° quarto segnato riscala il 1° sulla sua durata reale
    v2 = T.stime_video(ev, {1: 60, 2: 60 + 2 * fine[1] + T.PAUSA_QUARTI})
    assert v2[0] == 60 + 1.6 * 1.25 * 100           # rapporto limitato a 1,6
    assert T.stime_video(ev, {}) == {}
