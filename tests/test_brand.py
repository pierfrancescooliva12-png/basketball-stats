import io

from PIL import Image, ImageDraw

from basket import brand as B


def _logo(c1, c2):
    im = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 10, 190, 190), fill=c1)
    d.ellipse((60, 60, 140, 140), fill=c2)
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def test_slug():
    assert B.slug("Luiss Roma") == "luiss-roma"
    assert B.slug("Unieuro Forlì") == "unieuro-forli"


def test_colori_dal_logo_e_contrasti():
    p, s = B.colori_da_logo(_logo((0, 40, 92), (80, 180, 232)))
    assert B.luminanza(p) < B.luminanza(s)            # il più scuro fa da fondo
    t = B.tema(1, "Prova", {"primario": p, "secondario": s}, scarica=False)
    assert B.contrasto(t.fondo, "#ffffff") >= 7          # testo bianco leggibile sulla fascia
    giallo = B.tema(2, "Prova", {"primario": "#c8141e", "secondario": "#f7ba05"}, scarica=False)
    assert giallo.testo_accento != "#ffffff"             # su un accento chiaro il testo è scuro
    assert B.colori_da_logo(None) is None and B.colori_da_logo(b"non un'immagine") is None


def test_senza_logo_restano_i_colori_assist(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "CACHE_LOGHI", tmp_path)
    def rete_giu(url, timeout):
        raise OSError("rete")
    monkeypatch.setattr(B, "_scarica", rete_giu)
    t = B.tema(9583, "Luiss Roma")
    assert t.logo is None and t.accento == B.ARANCIO and not t.da_logo
    assert not list(tmp_path.iterdir())                  # errore di rete: niente in cache, si riprova
    css = B.css(t)
    assert "--navy" in css and "url(" not in css
