"""Scouting da template Excel (B Interregionale): template, lettura, analisi, PDF."""

import io

import pytest

from basket import scouting_excel as SX

openpyxl = pytest.importorskip("openpyxl")

SQ = [6, 78.5, 19.2, 38.0, 8.9, 26.1, 13.4, 18.9, 11.8, 24.0, 15.1, 11.0, 7.9, 2.4, 19.5]
AV = [6, 71.2, 17.0, 37.5, 7.3, 24.8, 11.4, 16.5, 10.2, 23.1, 12.0, 14.8, 6.1, 2.0, 20.4]
GIOC = [("7", "Mario Rossi", "Play", 6, 31.5, 17.8, 3.5, 7.0, 2.7, 6.5, 2.5, 3.2, 0.5, 3.0, 6.3, 2.1, 1.8, 0.1, 2.2),
        ("15", "Paolo Verdi", "Centro", 6, 26.0, 12.5, 5.5, 8.8, 0, 0, 1.5, 3.4, 3.4, 6.5, 0.8, 1.6, 0.5, 1.9, 4.1),
        ("4", "Andrea Neri", "Guardia", 5, 18.0, 6.1, 0.8, 2.6, 1.3, 4.8, 0.4, 0.6, 0.2, 1.4, 1.1, 1.0, 0.6, 0, 1.4)]


def _compila(squadra=SQ, avversari=AV, media=None, decimali_con_virgola=False) -> io.BytesIO:
    wb = openpyxl.load_workbook(io.BytesIO(SX.template()))
    ws = wb["Squadra"]
    ws["B3"], ws["B4"], ws["B5"] = "Squadra Esempio", "Serie B Interregionale", "D"
    for i, v in enumerate(squadra):
        ws.cell(row=9 + i, column=2, value=str(v).replace(".", ",") if decimali_con_virgola else v)
        if avversari:
            ws.cell(row=9 + i, column=3, value=avversari[i])
        if media:
            ws.cell(row=9 + i, column=4, value=media[i])
    g = wb["Giocatori"]
    for i, r in enumerate(GIOC, start=2):
        for j, v in enumerate(r, start=1):
            g.cell(row=i, column=j, value=v)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_template_e_lettura():
    wb = openpyxl.load_workbook(io.BytesIO(SX.template()))
    assert wb.sheetnames == ["Istruzioni", "Squadra", "Giocatori"]
    d = SX.leggi(_compila(decimali_con_virgola=True))
    assert d["intestazione"]["squadra"] == "Squadra Esempio"
    assert d["squadra"]["punti"] == 78.5 and d["squadra"]["t3a"] == 26.1 and d["avversari"]["to"] == 14.8
    assert [g["nome"] for g in d["giocatori"]] == ["Mario Rossi", "Paolo Verdi", "Andrea Neri"]
    assert d["giocatori"][0]["numero"] == "7" and d["giocatori"][0]["minuti"] == 31.5


def test_file_sbagliati():
    with pytest.raises(SX.ErroreTemplate, match="Excel"):
        SX.leggi(io.BytesIO(b"non un excel"))
    vuoto = _compila(squadra=[None] * 15, avversari=None)
    with pytest.raises(SX.ErroreTemplate, match="mancano"):
        SX.leggi(vuoto)


def test_indici_e_giudizi():
    d = SX.leggi(_compila())
    ind = SX.indici_completi(d)
    fga = 38.0 + 26.1
    assert ind["efg"] == pytest.approx(100 * (19.2 + 8.9 + 0.5 * 8.9) / fga)
    assert ind["perse"] == pytest.approx(100 * 11.0 / (fga - 11.8 + 11.0 + 0.44 * 18.9))
    assert ind["rimb_off"] == pytest.approx(100 * 11.8 / (11.8 + 23.1))
    assert "d_efg" in ind and "rimb_dif" in ind
    # riferimento: le medie scritte nel template vincono sulle altre squadre e sulla B Nazionale
    con_media = SX.leggi(_compila(media=AV))
    rif, fonte = SX.riferimento(con_media, [d] * 5, {"efg": 1.0})
    assert "template" in fonte
    rif, fonte = SX.riferimento(d, [d] * 4, {"efg": 1.0})
    assert "4 squadre" in fonte and rif["efg"] == pytest.approx(ind["efg"])
    rif, fonte = SX.riferimento(d, [d] * 3, {"efg": 40.0, "perse": 25.0})
    assert "B Nazionale" in fonte
    forza, debole, tab = SX.giudizio_squadra(ind, rif)
    assert any("Tiro effettivo" in x for x in forza) and any("Palle perse" in x for x in forza) and not debole
    assert set(tab["Giudizio"]) == {"punto di forza"}


def test_giocatori():
    d = SX.leggi(_compila())
    g = SX.giocatori(d).set_index("nome")
    assert "tiratore da 3 (42% su 6,5 a partita)" in g.loc["Mario Rossi", "forza"]
    assert "passatore affidabile" in g.loc["Mario Rossi", "forza"]
    assert "crea molto" not in g.loc["Mario Rossi", "forza"]
    assert "rimbalzista" in g.loc["Paolo Verdi", "forza"] and "tiro libero debole (44%)" in g.loc["Paolo Verdi", "debolezze"]
    assert "tiro da 3 poco preciso" in g.loc["Andrea Neri", "debolezze"]
    assert SX.chiave(SX.giocatori(d))["nome"].tolist() == ["Mario Rossi", "Paolo Verdi", "Andrea Neri"]


def test_pdf():
    d = SX.leggi(_compila())
    ind = SX.indici_completi(d)
    pdf = SX.pdf("Squadra Esempio", "Basket Roma", d, ind, ind, "prova", SX.giocatori(d), "note")
    assert pdf[:4] == b"%PDF" and len(pdf) > 5000


def test_riferimento_b_nazionale(tmp_path):
    from basket import config, db
    if not config.DB_PATH.exists():
        pytest.skip("database non presente")
    conn = db.connect(config.DB_PATH, readonly=True)
    stag = conn.execute("SELECT MAX(stagione) FROM partite").fetchone()[0]
    rif = SX.riferimento_lnp(conn, stag)
    assert 40 < rif["efg"] < 60 and 60 < rif["ritmo"] < 90 and 90 < rif["ortg"] < 120


def test_avversari_con_i_soli_punti():
    d = SX.leggi(_compila(avversari=[6, 65.0] + [None] * 13))
    ind = SX.indici_completi(d)
    assert d["avversari"] == {"partite": 6, "punti": 65.0}
    assert ind["ritmo"] == pytest.approx(ind["possessi"]) and "d_efg" not in ind
