"""Analisi delle clip: geometria del campo, proposta di squadre e costruzione della bozza su una
clip sintetica (senza modello né video: i rilevamenti sono costruiti a mano)."""

import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("scipy")
import numpy as np  # noqa: E402

from video import analisi as A  # noqa: E402


def _G(lato="sinistra"):
    # una "telecamera" qualsiasi: pixel = campo × 8 + spostamento, prospettiva leggera
    pix = {"sinistra": [[400, 300], [300, 700], [880, 320], [800, 720]],
           "destra": [[1500, 300], [1600, 700], [1020, 320], [1100, 720]]}[lato]
    return cv2.getPerspectiveTransform(np.float32(A.AREA[lato]), np.float32(pix)), pix


def test_tocchi_lato_e_geometria():
    for lato in ("sinistra", "destra"):
        G, pix = _G(lato)
        l, G2 = A.da_tocchi(pix)
        assert l == lato
        p = cv2.perspectiveTransform(np.float32([[A.AREA[lato][0]]]), G2)[0, 0]
        assert np.allclose(p, pix[0], atol=1e-3)


def test_semplifica_tiene_le_curve():
    t = np.linspace(0, 1, 50)
    retta = np.stack([t * 100, t * 0], 1)
    assert len(A._semplifica(retta, 2)) == 2
    angolo = np.vstack([np.stack([t * 50, 0 * t], 1), np.stack([50 + 0 * t, t * 50], 1)])
    assert len(A._semplifica(angolo, 2)) == 3


def _hist(colore):
    h = np.zeros(432, np.float32); h[colore] = 1.0
    return h


def _stato_sintetico():
    """10 giocatori: l'attacco (colore 10) lontano dal canestro, la difesa (colore 200) davanti;
    il portatore o1 palleggia verso destra e passa a un compagno a metà clip."""
    N, G = 60, np.eye(3)
    att0 = [(75, 100), (120, 80), (30, 80), (135, 25), (15, 25)]
    dif0 = [(x + (75 - x) * 0.15, y - 10) for x, y in att0]
    candidati, rilevamenti, per = [], [], []
    for i in range(N):
        rr, det = [], []
        for n, (x, y) in enumerate(att0):
            xx = x + (i * 0.6 if n == 0 else 0)
            rr.append({"box": [xx * 10 - 20, y * 10 - 80, xx * 10 + 20, y * 10], "h": _hist(10), "x": xx, "y": y})
        for x, y in dif0:
            rr.append({"box": [x * 10 - 20, y * 10 - 80, x * 10 + 20, y * 10], "h": _hist(200), "x": x, "y": y})
        portatore = rr[0] if i < 30 else rr[1]
        b = portatore["box"]
        det.append([b[2] - 6, b[1] + 30, b[2] + 6, b[1] + 42, 0.6, 32])
        per.append(rr); candidati.append(rr); rilevamenti.append(det)
    momenti = [0, 30, 59]
    return {"n": N, "inizio": 2.0, "G": G, "M": [G] * N, "per": per, "candidati": candidati,
            "rilevamenti": rilevamenti, "momenti": momenti}


def test_proposta_squadre_e_bozza():
    st = _stato_sintetico()
    prop = A.proponi_squadre({k: st["per"][k] for k in st["momenti"]})
    for k in st["momenti"]:
        assert prop[k][:5] == ["A"] * 5 and prop[k][5:] == ["D"] * 5     # attacco = più lontani dal canestro
    marc = {k: {"A": [j for j, v in enumerate(prop[k]) if v == "A"],
                "D": [j for j, v in enumerate(prop[k]) if v == "D"]} for k in st["momenti"]}
    g, q = A.costruisci(st, marc, "Prova", "clip.mp4")
    assert g["video"]["tempi"][0] == 2.0 and g["video"]["tempi"][-1] == round(2.0 + 59 / A.FPS, 2)
    assert len({p["id"] for p in g["fasi"][0]["giocatori"]}) == 10
    linee = [l for f in g["fasi"] for l in f["linee"]]
    assert any(l["tipo"] == "palleggio" and l["da"] == "o1" for l in linee)
    assert any(l["tipo"] == "passaggio" and l["da"] == "o1" for l in linee)
    assert g["fasi"][0]["palla"] == "o1" and g["fasi"][-1]["palla"] != "o1"
    assert q["palla"] == 60 and g["difesaTipo"] == "manuale"
