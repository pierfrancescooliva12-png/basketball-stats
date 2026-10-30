"""Lavagna sul video: il video resta sul dispositivo; alla piattaforma tornano solo le segnalazioni dello
staff con la sincronizzazione (tempi, mai il video), le etichette del club e i giochi creati dalle posizioni
sul fotogramma."""

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
    # un solo punto da cui un valore torna a Streamlit: segnalazioni e sincronizzazione, etichette, giochi
    assert s.count("streamlit:setComponentValue") == 1
    assert re.search(r"function invia\(valore\) \{\s*if \(IN_APP\) window\.parent\.postMessage\("
                     r"\{ isStreamlitMessage: true, type: \"streamlit:setComponentValue\"", s)
    azioni = re.findall(r"invia\(\{ azione: \"(\w+)\"", s)
    assert sorted(azioni) == ["etichette", "gioco", "video"], azioni
    # dei fotogrammi si legge solo il cronometro: nessuna immagine esce dal lettore
    assert "drawImage(video" in s and "getImageData" in s


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
                "zoomPiu", "zoomMeno", "zoomRiporta", "tasti-tag", "nuovo-tag", "tasti-schemi", "nuovo-schema",
                "modifica-tag", "lista",
                "qui", "seq", "sincronizza", "ferma-sync", "palla-a-due", "da", "tara", "posiziona",
                "crea-gioco"):
        assert f'id="{id_}"' in s, id_
    # pochi comandi: niente riquadro da disegnare a mano attorno al cronometro, una sola lista
    for vecchio in ("ocr-zona", "ocr-avvia", "c-da", "p-azioni", "lista-cronaca"):
        assert f'id="{vecchio}"' not in s, vecchio
    for p in ("cronaca", "gioco"):
        assert f'data-p="{p}"' in s, p


def test_cronaca_per_il_componente(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import pytest
    pytest.importorskip("streamlit")           # l'aggiornamento dati gira senza la dashboard

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


def _funzione(s: str, nome: str) -> str:
    """Testo di una funzione JavaScript del componente (dalla firma alla graffa che la chiude)."""
    i = s.index(f"function {nome}(")
    j = s.index("{", i)
    livello = 0
    for k in range(j, len(s)):
        livello += {"{": 1, "}": -1}.get(s[k], 0)
        if livello == 0:
            return s[i:k + 1]
    raise AssertionError(nome)


def _node(codice: str):
    import json
    import shutil
    import subprocess

    import pytest
    if not shutil.which("node"):
        pytest.skip("node non disponibile")
    out = subprocess.run(["node", "-e", codice], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(out.stdout)


def test_lettura_del_tempo_e_periodi():
    s = HTML.read_text()
    js = "\n".join(_funzione(s, n) for n in ("leggiTesto", "assegnaPeriodi"))
    r = _node("const durataQuarto = (p) => p <= 4 ? 600 : 300;\n" + js + """
      const testi = ["08:27", "8:27", "45.3", ":08:27.", "0827", "20:45", "12:61", ""].map(leggiTesto);
      // video da metà del 1° quarto: il cronometro scende, a 10:00 riparte il 2°; una lettura sbagliata
      const campioni = [[0, 300], [30, 280], [60, 255], [90, 400], [120, 230], [150, 60], [180, 0], [210, 600],
                        [240, 590], [270, 560], [300, null], [330, 530]];
      console.log(JSON.stringify({ testi, periodi: assegnaPeriodi(campioni, 1) }));""")
    assert r["testi"] == [507, 507, 45.3, 507, None, None, None, None]
    assert [x[0] for x in r["periodi"]["1"]] == [300, 320, 345, 370, 540, 600]
    assert r["periodi"]["2"] == [[0, 210], [10, 240], [40, 270], [70, 330]]


def test_cronometro_fermo_nel_secondo_dell_azione():
    s = HTML.read_text()
    js = "\n".join(_funzione(s, n) for n in ("intervallo", "gruppo", "fermaCronometro", "stimaGrafica"))
    r = _node("""const durataQuarto = (p) => p <= 4 ? 600 : 300; const reale = (e) => e.m;
      const cronaca = { eventi: [
        { n: 1, p: 1, s: 100, m: 140, tipo: "tiro2_fatto" },
        { n: 2, p: 1, s: 200, m: 300, tipo: "fallo" }, { n: 3, p: 1, s: 200, m: 312, tipo: "tl_fatto" },
        { n: 4, p: 1, s: 200, m: 330, tipo: "tl_sbagliato" }, { n: 5, p: 1, s: 200, m: 348, tipo: "rimb_dif" },
        { n: 6, p: 1, s: 300, m: 500, tipo: "tiro3_sbagliato" }, { n: 7, p: 1, s: 400, m: 700, tipo: "tiro2_fatto" }] };
      // il cronometro passa da 100 a 101 senza fermarsi; si ferma a 200 dal video 1000 al 1060;
      // a 300 si ferma 20 secondi senza che l'abbia fermato l'azione (palla fuori non scritta)
      const letture = { 1: [[99, 498.6], [100, 499.6], [101, 500.6], [199, 999], [200, 1000], [200, 1059.8],
                            [201, 1060.8], [299, 1199], [300, 1200], [300, 1219.5], [301, 1220.5]] };
      """ + js + """
      const st = (n) => Math.round(stimaGrafica(cronaca.eventi.find((e) => e.n === n)).t * 10) / 10;
      console.log(JSON.stringify([1, 2, 3, 4, 5, 6].map(st)));""")
    canestro, fallo, libero1, libero2, rimbalzo, tiro = r
    assert abs(canestro - 500.1) < 0.6                      # a metà del secondo
    assert abs(fallo - 1000.5) < 0.6                        # appena prima della fermata
    assert fallo < libero1 < libero2 < rimbalzo             # i liberi dentro la fermata, in ordine
    assert abs(rimbalzo - 1059.8) < 1.5                     # il rimbalzo alla ripresa del gioco
    assert abs(tiro - 1219.5) < 1.5                         # nessuna azione l'ha fermato: alla ripresa


def test_archivio_della_lavagna_sul_video(tmp_path):
    from basket.note import Archivio
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    assert a.video_dati("club", "etichette") is None
    a.set_video_dati("club", "etichette", ["Pick and roll centrale", "Horns 45"])
    memoria = {"segnalazioni": [{"id": "a1", "et": "Horns 45", "t": 1500.2, "fp": "gara.mp4|123", "p": 2, "gs": 168}],
               "video": {"gara.mp4|123": {"letture": {"1": [[0, 50], [30, 90]]}, "inizi": {"1": 49.7}}}}
    a.set_video_dati("club", "partita:p1", memoria)
    a.set_video_dati("club", "partita:p1", memoria)          # salvare di nuovo sostituisce
    assert a.video_dati("club", "etichette") == ["Pick and roll centrale", "Horns 45"]
    assert a.video_dati("club", "partita:p1") == memoria
    assert a.video_dati("altro", "partita:p1") is None       # un club non vede i dati di un altro


def test_dati_dal_componente():
    import pytest
    pytest.importorskip("streamlit")
    from types import SimpleNamespace

    from dashboard import telestrator_ui as TU
    assert TU.pulisci_etichette({"azioni": [" Pick and roll ", "Pick and roll", "", "x" * 50, 3],
                                 "schemi": ["Horns 45"]}) == {"azioni": ["Pick and roll", "x" * 30, "3"],
                                                              "schemi": ["Horns 45"]}
    # elenco salvato prima dei due livelli: sono tipi di azione
    assert TU.pulisci_etichette(["Horns 45"]) == {"azioni": ["Horns 45"], "schemi": []}
    assert TU.pulisci_etichette("non una lista") == {"azioni": [], "schemi": []}

    salvati = {}
    a = SimpleNamespace(club="club", archivio=SimpleNamespace(set_video_dati=lambda c, k, d: salvati.update({k: d})))
    assert TU.salva_memoria(a, "p1", {"segnalazioni": [], "video": {}})
    assert not TU.salva_memoria(a, "p2", {"segnalazioni": "no"})
    assert not TU.salva_memoria(a, "p3", {"segnalazioni": [], "video": {"x": "y" * TU.MAX_DATI}})
    assert list(salvati) == ["partita:p1"]


def test_azione_e_schema_nella_stessa_situazione():
    s = HTML.read_text()
    js = _funzione(s, "segnala").replace("async function", "function").replace("const tg = await tempoDiGioco(t);", "const tg = null;")
    r = _node("""let url = 'x', scan = null, impronta = 'f', ultima = null, segnalazioni = [];
      const occupato = { attivo: false }, UNISCI = 8, video = { currentTime: 0 };
      const avviso = () => {}, aggiornaTag = () => {}, aggiornaLista = () => {}, salvaPresto = () => {}, orario = String;
      const nomeSegn = (s) => [s.azione, s.schema].filter(Boolean).join(" · ");
      """ + js + """
      video.currentTime = 100; segnala("azione", "Pick and roll centrale");
      video.currentTime = 104; segnala("schema", "Horns 45");          // stessa situazione
      video.currentTime = 106; segnala("schema", "Spain");             // schema già dato: situazione nuova
      video.currentTime = 200; segnala("schema", "Horns 45");          // solo lo schema
      video.currentTime = 203; segnala("azione", "Post basso");        // si aggiunge allo schema
      video.currentTime = 300; segnala("azione", "Transizione");
      video.currentTime = 320; segnala("schema", "Horns 45");          // troppo tardi: situazione nuova
      console.log(JSON.stringify(segnalazioni.map((x) => [x.t, x.azione, x.schema])));""")
    assert r == [[100, "Pick and roll centrale", "Horns 45"], [106, None, "Spain"], [200, "Post basso", "Horns 45"],
                 [300, "Transizione", None], [320, None, "Horns 45"]]
