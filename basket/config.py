"""Configurazione: stagione, campionati, percorsi."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lnp.sqlite"
REPORTS_DIR = ROOT / "reports"

STAGIONE = "x2627"
STAGIONE_LABEL = "2026/27"

# codice lega sul sito -> nome leggibile
CAMPIONATI = {
    "ita2": "Serie A2",
    "ita3_a": "Serie B Nazionale - Girone A",
    "ita3_b": "Serie B Nazionale - Girone B",
}

SITE_BASE = "https://www.legapallacanestro.com"
DOMINO_URL = "https://lnpstat.domino.it/getstatisticsfiles"

# Al massimo una richiesta al secondo verso il sito
MIN_INTERVAL_S = 1.0
USER_AGENT = (
    "basketball-stats/1.0 (analisi statistica personale; "
    "https://github.com/pierfrancescooliva12-png/basketball-stats)"
)

# Limite di sicurezza sul numero di giornate da esplorare
MAX_GIORNATE = 60
