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
def test_una_pagina():
    import io
    PdfReader = pytest.importorskip("pypdf").PdfReader
    from basket import db, mercato, sviluppo as SV
    from basket.contesto import Contesto
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    sid = list(ctx.profile["squadra_id"])[0]
    g = SV.squadra(ctx, sid, foto=False)[0]
    pdf = RG.build(ctx, sid, g["giocatore_id"], mercato.season_lines(ctx.conn), foto=False)
    assert pdf[:4] == b"%PDF" and len(PdfReader(io.BytesIO(pdf)).pages) == 1
