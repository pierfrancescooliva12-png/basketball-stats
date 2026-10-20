"""Tabelle del sito: dati passati al componente (ordinamento, colori, chiavi)."""

import json
import re

import pandas as pd
import pytest

pytest.importorskip("streamlit")


def _payload(monkeypatch, df, **k):
    from dashboard import tabella as TB
    preso = {}
    monkeypatch.setattr(TB.components, "html", lambda html, height, scrolling: preso.update(html=html, h=height))
    TB.render(df, **k)
    m = re.search(r'<script type="application/json" id="dati">(.*?)</script>', preso["html"], re.S)
    return json.loads(m.group(1).replace("<\\/", "</")), preso["h"]


def test_tabella(monkeypatch):
    df = pd.DataFrame({"Giocatore": ["Andrea De nicolao", "B", "C", "D", "E"],
                       "Data": ["21/10/2026", "03/09/2026", None, "01/01/2027", "15/10/2026"],
                       "Punti": [10.0, 20.0, None, 5.0, 7.5], "PG": [4, 3, 2, 1, 4],
                       "Diff": [3, -2, 0, 1, 5], "Quota": ["18,3% (13,2)", "9,0% (2,0)", "–", "1", "2"]})
    p, h = _payload(monkeypatch, df, colori={"Punti": True}, progress={"Punti": (0, None)})
    cols = {c["l"]: c for c in p["cols"]}
    assert p["rows"][0][0] == "Andrea De Nicolao" and p["rows"][2][2] is None
    assert cols["PG"]["d"] == 0 and cols["Punti"]["d"] == 1 and cols["Diff"]["segno"] == 1
    assert cols["Punti"]["hi"] == 20.0 and cols["Punti"]["lo"] == 5.0 and cols["Punti"]["bar"] == [0.0, 20.0]
    # date e testi con numeri si ordinano con una chiave a parte
    k = cols["Data"]["k"]
    assert p["rows"][0][k] == "20261021" and p["rows"][3][k] == "20270101"
    assert p["rows"][0][cols["Quota"]["k"]] == 18.3 and p["rows"][2][5] is None
    assert p["rows"][0][-1] is False and h == 44 + 38 * 5 + 53 + 33 + 4
    assert not p["cerca"]


def test_tabella_mia_e_rif(monkeypatch):
    import streamlit as st
    st.session_state["_tema_tabelle"] = {"mia_nome": "Luiss Roma", "sids": {}}
    df = pd.DataFrame({"Squadra": ["Luiss Roma", "Altra Squadra"], "TS%": [55.0, 48.0]})
    p, _ = _payload(monkeypatch, df, colori={"TS%": True}, rif={"TS%": pd.Series(range(40, 60))})
    assert [r[-1] for r in p["rows"]] == [True, False] and "la tua squadra" in p["legenda"]
    c = p["cols"][1]
    assert c["suf"] == "%" and c["hi"] > 55 and "del campionato" in p["legenda"]
    assert p["sigle"]["Altra Squadra"] == "SQU"
    del st.session_state["_tema_tabelle"]
