"""Report individuale del giocatore: tono rivolto al giocatore e PDF completo."""

import pytest

from basket import config
from basket import report_giocatore as RG


def test_tono_e_nomi():
    assert RG.tu("Con lui in campo la squadra va meglio rispetto a quando è fuori") == \
        "Con te in campo la squadra va meglio rispetto a quando sei fuori"
    assert RG.tu("le sue partite non bastano") == "le tue partite non bastano"
    assert RG._breve("Crifo Wines Ruvo di Puglia") == "Ruvo di Puglia"
    assert RG._breve("Sella Cento") == "Cento"
    assert RG._breve("Halley Campania Avellino Basket") == "Avellino"


@pytest.mark.skipif(not config.DB_PATH.exists(), reason="database non disponibile")
def test_due_pagine_report_e_statistiche_avanzate():
    import io
    PdfReader = pytest.importorskip("pypdf").PdfReader
    from basket import db, mercato, sviluppo as SV
    from basket.contesto import Contesto
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    sid = list(ctx.profile["squadra_id"])[0]
    g = SV.squadra(ctx, sid, foto=False)[0]
    pdf = RG.build(ctx, sid, g["giocatore_id"], mercato.season_lines(ctx.conn), foto=False)
    pagine = PdfReader(io.BytesIO(pdf)).pages
    # la scheda resta su una pagina; la seconda è quella delle statistiche avanzate
    assert pdf[:4] == b"%PDF" and len(pagine) == 2
    testo = pagine[1].extract_text().upper()
    assert "STATISTICHE AVANZATE" in testo and "PIE" in testo and "USG%" in testo
