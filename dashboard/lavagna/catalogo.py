"""Catalogo degli schemi pronti: quelli di base più l'archivio per situazione."""

from . import archivio_pnr, archivio_zona, schemi

SCHEMI = schemi.SCHEMI + archivio_pnr.SCHEMI + archivio_zona.SCHEMI
