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
                orb_pct=4, rimb_off_pg=0.5, ts_pct=52.0, on_off=0.0)
    base.update(k)
    return NS(**base)


def test_caratteristiche_con_il_loro_dato():
    car, dif = SG.caratteristiche(_p(t3a_pg=5.0, t3m_pg=2.2, t3_pct=44.0, usg_pct=30), RIF)
    assert car[0].startswith("Prima opzione") and any("Tiratore da 3 (2,2/5 a partita, 44%)" == c for c in car)
    assert dif[0].startswith("Mai libero")
    car, dif = SG.caratteristiche(_p(tl_pct=50.0, tla=10, perse_pg=3.0, tov_pct=20), RIF,
                                  falli={"partite_problemi": 3},
                                  finali={"fga": 5, "quota_tiri": 40})
    testi = " ".join(car + dif)
    assert "Debole ai liberi (50%)" in testi and "Uomo dei finali (40%" in testi
    assert len(car) <= 4 and len(dif) <= 2
    assert SG.caratteristiche(_p(), RIF) == ([], [])


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
