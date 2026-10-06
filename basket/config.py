"""Configurazione: stagione, campionati, percorsi."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Percorsi sovrascrivibili (prove in locale): LNP_DB, LNP_CRONACA
DB_PATH = Path(os.environ.get("LNP_DB", ROOT / "data" / "lnp.sqlite"))
# Cronache (play-by-play): un file compresso per partita, scritto una volta e mai modificato,
# così il repository non cresce a ogni aggiornamento settimanale
CRONACA_DIR = Path(os.environ.get("LNP_CRONACA", ROOT / "data" / "cronaca"))
REPORTS_DIR = ROOT / "reports"

BRAND = "ASSIST"
BRAND_TAGLINE = "Analisi Statistica e Scouting Integrato per Staff Tecnici"
LOGO_DIR = ROOT / "assets" / "logo"

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

# Intervallo minimo tra le richieste: il robots.txt di legapallacanestro.com chiede
# "Crawl-delay: 10" (10 secondi), che va rispettato
MIN_INTERVAL_S = 10.0

# I termini di LNP Pass vietano i link diretti ai contenuti senza consenso scritto:
# i pulsanti verso le partite su LNP Pass restano disattivati finché non c'è un accordo
LINK_LNP_PASS = False
USER_AGENT = (
    "basketball-stats/1.0 (analisi statistica personale; "
    "https://github.com/pierfrancescooliva12-png/basketball-stats)"
)

# Limite di sicurezza sul numero di giornate da esplorare
MAX_GIORNATE = 60

# Zone della classifica per la simulazione della stagione: etichetta -> (da, a) posizioni.
# Valori indicativi: aggiornarli con la formula ufficiale del campionato.
ZONE_CLASSIFICA = {
    "ita2": {"1° posto": (1, 1), "Prime 4": (1, 4), "Prime 8": (1, 8),
             "Ultimi 3": (18, 20)},
    "ita3_a": {"1° posto": (1, 1), "Prime 4": (1, 4), "Prime 8": (1, 8),
               "Ultimi 3": (16, 18)},
    "ita3_b": {"1° posto": (1, 1), "Prime 4": (1, 4), "Prime 8": (1, 8),
               "Ultimi 3": (16, 18)},
}
