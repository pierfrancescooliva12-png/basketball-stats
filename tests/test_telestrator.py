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


def test_strumenti_disponibili():
    s = HTML.read_text()
    for t in ("penna", "percorso", "freccia", "passaggio", "blocco", "linea", "cerchio", "riflettore", "area",
              "testo", "gomma", "mano"):
        assert f'data-t="{t}"' in s, t
    for id_ in ("annulla", "ripeti", "pulisci", "indietro1", "avanti1", "schermo", "velocita",
                "zoomPiu", "zoomMeno", "zoomRiporta", "tasti-tag", "seq-tag", "lista-tag",
                "lista-cronaca", "qui", "seq-cronaca", "tara", "posiziona", "crea-gioco"):
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
