"""Icona per la schermata Home: quadrato pieno nel colore del club con il logo, e manifest."""

import io
import json

from PIL import Image

from basket import icona


def _logo():
    im = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
    im.paste((255, 255, 255, 255), (50, 50, 250, 150))
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def test_icona_e_manifest(tmp_path):
    v = icona.prepara("Luiss Roma", "Luiss Roma", _logo(), "#123456", cartella=tmp_path)
    assert v["apple"].startswith("/app/static/club/luiss-roma-180-") and v["titolo"] == "Luiss Roma"
    png = Image.open(tmp_path / v["apple"].rsplit("/", 1)[1])
    assert png.size == (180, 180) and png.mode == "RGB"            # niente trasparenza (iOS)
    assert png.getpixel((2, 2)) == (0x12, 0x34, 0x56)               # bordo nel colore del club
    assert png.getpixel((90, 90)) == (255, 255, 255)                # logo al centro
    m = json.loads((tmp_path / v["manifest"].rsplit("/", 1)[1]).read_text())
    assert m["start_url"] == "/?club=luiss-roma" and m["display"] == "standalone"
    assert [i["sizes"] for i in m["icons"]] == ["192x192", "512x512"]
    # logo o colore diversi: file diversi (le icone già installate non restano vecchie)
    assert icona.prepara("Luiss Roma", "Luiss Roma", _logo(), "#654321", cartella=tmp_path)["apple"] != v["apple"]
    assert icona.prepara("Consultinvest Loreto Pesaro", "Consultinvest Loreto Pesaro", None, "#000000",
                         cartella=tmp_path)["titolo"] == "ASSIST"
