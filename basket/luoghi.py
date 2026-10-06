"""Città dei palazzetti e distanze delle trasferte.

Le coordinate sono quelle (approssimate) del centro città: bastano per stimare la lunghezza
di una trasferta. La città di una partita si ricava dal nome del palazzetto pubblicato dalla
Lega ("PalaDozza - Bologna"); quando manca si usa la città abituale della squadra di casa.
"""

import math
import re

import pandas as pd

CITTA = {
    "Agrigento": (37.31, 13.58), "Avellino": (40.91, 14.79), "Bari": (41.12, 16.87),
    "Bologna": (44.49, 11.34), "Brescia": (45.54, 10.21), "Brindisi": (40.63, 17.94),
    "Capo d'Orlando": (38.15, 14.74), "Casale Monferrato": (45.13, 8.45),
    "Casalnuovo di Napoli": (40.91, 14.35), "Caserta": (41.07, 14.33),
    "Casoria": (40.91, 14.29), "Castell'Arquato": (44.85, 9.87), "Castellanza": (45.61, 8.90),
    "Cento": (44.73, 11.29), "Chiusi": (43.02, 11.95), "Cisterna di Latina": (41.59, 12.83),
    "Cividale del Friuli": (46.09, 13.43), "Conegliano": (45.89, 12.30),
    "Cremona": (45.13, 10.02), "Desio": (45.62, 9.21), "Fabriano": (43.34, 12.90),
    "Faenza": (44.29, 11.88), "Ferentino": (41.69, 13.25), "Ferrara": (44.84, 11.62),
    "Fidenza": (44.87, 10.06), "Forlì": (44.22, 12.04), "Gravellona Toce": (45.93, 8.43),
    "Imola": (44.35, 11.71), "Jesi": (43.52, 13.24), "Livorno": (43.55, 10.31),
    "Lucca": (43.84, 10.50), "Lumezzane": (45.65, 10.26), "Mestre": (45.49, 12.24),
    "Milano": (45.46, 9.19), "Montecatini Terme": (43.88, 10.77), "Napoli": (40.85, 14.27),
    "Nocera Inferiore": (40.75, 14.64), "Orzinuovi": (45.40, 9.92), "Pesaro": (43.91, 12.91),
    "Piacenza": (45.05, 9.69), "Piazza Armerina": (37.38, 14.37), "Piombino": (42.93, 10.53),
    "Pistoia": (43.93, 10.92), "Porto Empedocle": (37.29, 13.53), "Ragusa": (36.93, 14.73),
    "Ravenna": (44.42, 12.20), "Reggio Calabria": (38.11, 15.65), "Rieti": (42.40, 12.86),
    "Rimini": (44.06, 12.57), "Roma": (41.90, 12.50), "Roseto degli Abruzzi": (42.68, 14.02),
    "Ruvo di Puglia": (41.12, 16.49), "San Giorgio su Legnano": (45.57, 8.91),
    "San Severo": (41.69, 15.38), "Sassari": (40.73, 8.56), "Scafati": (40.75, 14.53),
    "Siena": (43.32, 11.33), "Torino": (45.07, 7.69), "Treviglio": (45.52, 9.59),
    "Verona": (45.44, 10.99), "Veroli": (41.69, 13.42), "Vicenza": (45.55, 11.55),
    "Vigevano": (45.32, 8.86),
}

# Palazzetti pubblicati senza città (o con un nome diverso)
PALAZZETTI = {
    "paladozza": "Bologna", "palaserradimigni": "Sassari", "vitrifrigo arena": "Pesaro",
    "palapentassuglia": "Brindisi", "palaelachem": "Vigevano", "palapiccolo": "Caserta",
    "palaterme": "Montecatini Terme", "palaflorio": "Bari", "palacolombo": "Ruvo di Puglia",
    "palaleonessa": "Brescia", "giuseppe bondi arena": "Ferrara", "palaruggi": "Imola",
    "palarquato": "Castell'Arquato", "palapratizzoli": "Fidenza",
    "infodrive arena": "Capo d'Orlando", "palafantozzi": "Capo d'Orlando",
    "palabertelli": "San Giorgio su Legnano", "palabertocchi": "Orzinuovi",
    "pala a2a": "Lumezzane", "palamoncada": "Porto Empedocle",
    "palacalafiore": "Reggio Calabria", "palacipir di gravellona": "Gravellona Toce",
    "palamoretto": "Desio", "prealpi sanbiagio arena": "Conegliano",
    "soevis arena": "Castellanza", "palafacchetti": "Treviglio", "palabanca": "Piacenza",
    "palaestra": "Siena", "palatagliate": "Lucca", "palamacchia": "Livorno",
    "pala de andrè": "Ravenna", "paladennerlein": "Napoli", "palapania": "Chiusi",
    "pala del mauro": "Avellino", "pala gianni asti": "Torino", "baltur arena": "Cento",
    "palagesteco": "Cividale del Friuli", "unieuro arena": "Forlì",
    "palasport flaminio": "Rimini", "palaradi": "Cremona", "palasport taliercio": "Mestre",
    "amedeo modigliani forum": "Livorno", "palacarrara": "Pistoia",
    "palasojourner": "Rieti", "pala fitline": "Desio", "pala fit line": "Desio",
    "palalido allianz cloud": "Milano", "palamaggetti": "Roseto degli Abruzzi",
    "pala megabox": "Pesaro", "palacattani": "Faenza", "palasport tenda piombino": "Piombino",
    "palasport città di vicenza": "Vicenza", "palacoscioni": "Nocera Inferiore",
    "palatriccoli": "Jesi", "palacosta": "Ravenna", "palamangano": "Scafati",
    "pala agsm aim": "Verona", "palafranzanti": "Piacenza", "palaenergica": "Casale Monferrato",
    "pala lumenergia": "Lumezzane", "palapadua": "Ragusa", "palacoccia": "Veroli",
}

# Squadre il cui palazzetto ha un nome generico ("Palasport Comunale")
CITTA_SQUADRA = {34004: "Fabriano"}


def citta_palazzetto(palazzetto: str | None) -> str | None:
    """Città di un palazzetto dal nome pubblicato dalla Lega; None se non riconoscibile."""
    if not palazzetto or not isinstance(palazzetto, str):
        return None
    parti = re.split(r"\s+[-–]\s+", palazzetto.strip())
    if len(parti) > 1 and parti[-1].strip() in CITTA:
        return parti[-1].strip()
    nome = re.sub(r"[\"“”]", "", parti[0]).strip().lower()
    for chiave, citta in PALAZZETTI.items():
        if nome.startswith(chiave):
            return citta
    return None


def distanza_km(a: str | None, b: str | None) -> float | None:
    """Distanza in linea d'aria tra due città, aumentata del 25% per stimare quella su strada."""
    if a not in CITTA or b not in CITTA:
        return None
    (la1, lo1), (la2, lo2) = CITTA[a], CITTA[b]
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(1.25 * 2 * 6371 * math.asin(math.sqrt(h)), 0)


def citta_partite(partite: pd.DataFrame) -> pd.DataFrame:
    """Per ogni partita: città in cui si gioca e città abituale delle due squadre.

    partite: colonne partita_id, squadra_casa_id, squadra_ospite_id, palazzetto."""
    p = partite[["partita_id", "squadra_casa_id", "squadra_ospite_id", "palazzetto"]].copy()
    p["citta"] = p["palazzetto"].map(citta_palazzetto)
    casa = p.dropna(subset=["citta"]).groupby("squadra_casa_id")["citta"].agg(
        lambda s: s.value_counts().index[0])
    casa = pd.concat([pd.Series(CITTA_SQUADRA), casa[~casa.index.isin(CITTA_SQUADRA)]])
    p["citta"] = p["citta"].fillna(p["squadra_casa_id"].map(casa))
    p["citta_casa"] = p["squadra_casa_id"].map(casa)
    p["citta_ospite"] = p["squadra_ospite_id"].map(casa)
    return p
