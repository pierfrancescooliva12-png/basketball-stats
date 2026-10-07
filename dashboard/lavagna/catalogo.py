"""Catalogo degli schemi pronti: quelli di base più l'archivio per situazione."""

from . import archivio_movimento, archivio_pnr, archivio_rimesse, archivio_zona, schemi

# ordine delle categorie nel menu della lavagna e nel PDF dell'archivio
CATEGORIE = ["Metà campo", "Pick and roll", "Contro i cambi", "Tiratori", "Gioco in post",
             "Transizione", "Contro la zona", "Giochi avanzati", "Rimesse dal fondo",
             "Rimesse laterali", "Fine quarto", "Fine partita"]

SCHEMI = sorted(schemi.SCHEMI + archivio_pnr.SCHEMI + archivio_movimento.SCHEMI
                + archivio_zona.SCHEMI + archivio_rimesse.SCHEMI,
                key=lambda s: CATEGORIE.index(s["categoria"]))
