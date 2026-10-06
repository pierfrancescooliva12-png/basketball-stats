"""Configurazione: stagione, campionati, percorsi."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lnp.sqlite"
# Cronache (play-by-play): un file compresso per partita, scritto una volta e mai modificato,
# così il repository non cresce a ogni aggiornamento settimanale
CRONACA_DIR = ROOT / "data" / "cronaca"
REPORTS_DIR = ROOT / "reports"

STAGIONE = "x2627"
STAGIONE_LABEL = "2026/27"

# Stagioni in archivio (per mercato e storico). Codice sito -> etichetta
STAGIONI = {"x2627": "2026/27", "x2526": "2025/26", "x2425": "2024/25"}

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
