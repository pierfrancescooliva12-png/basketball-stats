"""Report prepartita: scouting dei singoli giocatori e visione di squadra."""

from types import SimpleNamespace as NS

import pandas as pd

from basket import scheda_giocatori as SG
from basket import sintesi as SI

RIF = pd.DataFrame({"usg_pct": [15, 18, 20, 22, 24], "ft_rate": [0.1, 0.2, 0.25, 0.3, 0.35],
                    "ast_pct": [8, 10, 12, 15, 18], "tov_pct": [10, 12, 14, 16, 18],
                    "orb_pct": [2, 4, 6, 8, 10]})


def _p(**k):
    base = dict(t3a_pg=1.0, t3m_pg=0.3, t3_pct=30.0, usg_pct=18, minuti_pg=25, tla_pg=1.0, tla=4,
                ft_rate=0.2, tl_pct=75.0, assist_pg=1.0, ast_pct=10, perse_pg=1.0, tov_pct=12,
                orb_pct=4, rimb_off_pg=0.5, ts_pct=52.0, on_off=0.0, fga_pg=6.0, tlm=3, t3m=1, t3a=3,
                partite=4)
    base.update(k)
    return NS(**base)


def test_cosa_fa_meglio_e_peggio():
    forza, deboli = SG.caratteristiche(_p(t3a_pg=5.0, t3m_pg=2.2, t3_pct=44.0, usg_pct=30), RIF)
    assert forza[0].startswith("Prima opzione") and "Tiratore da 3 (2,2/5 a partita, 44%)" in forza
    assert deboli == []
    forza, deboli = SG.caratteristiche(_p(tl_pct=50.0, tla=10, perse_pg=3.0, tov_pct=20), RIF,
                                       falli={"partite_problemi": 3}, finali={"fga": 5, "quota_tiri": 40})
    assert "Uomo dei finali (5 tiri negli ultimi 5' punto a punto, 40% di quelli della squadra)" in forza
    assert deboli[0] == "Debole ai liberi (50% su 10)" and len(deboli) == 3
    assert not any("difend" in x.lower() for x in forza + deboli)


def test_sempre_almeno_due_informazioni_chiave():
    rif = RIF.assign(punti_pg=[4, 6, 8, 10, 12], rimb_tot_pg=[2, 3, 4, 5, 6])
    forza, _ = SG.caratteristiche(_p(punti_pg=11.0, rimb_tot_pg=2.5), rif)
    assert len(forza) == 2 and forza[0].startswith("11 punti a partita (meglio del")


def test_foto_in_cache_e_iniziali(tmp_path, monkeypatch):
    monkeypatch.setattr(SG, "CACHE_FOTO", tmp_path)
    (tmp_path / "A1.jpg").write_bytes(b"\xff\xd8\xffdati")
    assert SG.scarica_foto("A1", "http://non.usato/") == b"\xff\xd8\xffdati"
    (tmp_path / "A2.jpg").write_bytes(b"")                        # nessuna foto sul sito
    assert SG.scarica_foto("A2", "http://non.usato/") is None
    assert SG.foto_url("A3", {}, "x2627").endswith("/x2627/A3.jpg")
    from basket import report_pdf as R
    assert R._foto(None, "Mario Rossi", 20, 30).contents         # riquadro con le iniziali


def test_azione_dal_consiglio():
    assert SI.azione("Forti a rimbalzo offensivo (35,2%, 3° su 20): tagliafuori su ogni tiro") == \
        "Tagliafuori su ogni tiro"
    assert SI.azione("Occasione · Tiro da 3: voi 45% (2° su 20): spaziature larghe. Pericolosi: X") == \
        "Spaziature larghe"


def test_report_word_e_pdf(tmp_path, monkeypatch):
    import io
    import zipfile
    from basket import config, db, update
    from basket.contesto import Contesto
    from basket.report_pdf import build_pdf
    from basket.report_word import build_docx
    from tests.test_pbp import Client
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    ctx = Contesto(conn, "x2627")
    doc = build_docx(ctx, 10050, 100118, foto=False)
    testo = zipfile.ZipFile(io.BytesIO(doc)).read("word/document.xml").decode()
    assert "SCOUTING DEI GIOCATORI" in testo and "Note dello staff" in testo
    assert "difenderlo" not in testo and "Nessuna caratteristica" not in testo
    assert build_pdf(ctx, 10050, 100118, foto=False)[:4] == b"%PDF"


def test_aree_di_miglioramento_con_obiettivo():
    from basket import sviluppo as SV
    pari = pd.DataFrame({"tl_pct": [60, 65, 70, 72, 75, 78, 80, 82, 85, 88],
                         "tov_pct": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]})
    p = _p(tl_pct=55.0, tla=12, tla_pg=4.0, tov_pct=11.0, perse_pg=2.0, fga_pg=8.0, gruppo="esterni")
    aree, forza = SV.aree(p, pari)
    assert aree[0]["voce"] == "Tiri liberi" and aree[0]["obiettivo"] == "76%"
    assert abs(aree[0]["punti_pg"] - (76.5 - 55) / 100 * 4) < 1e-9
    assert not any(a["voce"].startswith("Palle perse") for a in aree)
    assert SV.gruppo("Play", None) == "esterni" and SV.gruppo(None, 206) == "lunghi"
    assert SV.gruppo("Ala grande", 200) == "lunghi" and SV.gruppo(None, 196) == "ali"


def test_report_sviluppo(tmp_path, monkeypatch):
    from basket import config, db, update
    from basket.contesto import Contesto
    from basket.report_pdf import build_sviluppo
    from tests.test_pbp import Client
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    assert build_sviluppo(Contesto(conn, "x2627"), 10050, foto=False)[:4] == b"%PDF"


def test_anagrafica_con_valori_mancanti():
    import math
    info = SG.pulisci({"ruolo": math.nan, "maglia": 7.0, "nazionalita": "ITA", "altezza_cm": math.nan,
                       "foto_url": None})
    assert info == {"maglia": "7", "nazionalita": "ITA"}
    assert SG.meta({"ruolo": math.nan, "altezza": None, "eta": 24, "nazionalita": "ITA"}) == "24 anni · ITA"
