"""Catalogo degli schemi pronti: quelli di base più l'archivio per situazione."""

from . import archivio_zona, schemi

SCHEMI = schemi.SCHEMI + archivio_zona.SCHEMI
