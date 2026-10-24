

def test_cronaca_non_ancora_pubblicata():
    import pytest

    from basket.scraper import NonDisponibile, ParseError, parse_pbp
    pagina = ("<html><body><div class='region-content'><h1>Casa VS Ospite</h1>"
              "<p>I dati di questa partita non sono ancora disponibili.</p></div></body></html>")
    with pytest.raises(NonDisponibile):
        parse_pbp(pagina)
    with pytest.raises(ParseError):
        parse_pbp("<html><body><p>pagina diversa</p></body></html>")
