"""Estrazione dati da legapallacanestro.com.

- Calendario: endpoint JSON interno lnpstat.domino.it (task=schedule).
- Box score: pagina HTML /wp/match/{gameid}/{league}/{season} (generata lato server).
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from . import config
from .client import RateLimitedClient

# Colonne della tabella statistiche del box score, nell'ordine del sito
STAT_COLUMNS = [
    "punti", "minuti", "falli_commessi", "falli_subiti",
    "t2m", "t2a", None, "t3m", "t3a", None, "tlm", "tla", None,
    "rimb_off", "rimb_dif", "rimb_tot", "stoppate", "stoppate_subite",
    "perse", "recuperate", "assist", "valutazione", "oer",
]


class ParseError(Exception):
    """La pagina non ha la struttura attesa: il sito potrebbe essere cambiato."""


# ---------------------------------------------------------------- calendario

def fetch_schedule(client: RateLimitedClient, league: str, giornata: int,
                   season: str = config.STAGIONE) -> list[dict] | None:
    """Partite di una giornata; None se la giornata non esiste."""
    resp = client.get(config.DOMINO_URL, params={
        "task": "schedule", "year": season, "league": league, "round": giornata,
    })
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        return None
    return parse_schedule(data, league, season)


def parse_schedule(data: list[dict], league: str, season: str) -> list[dict]:
    games = []
    for g in data:
        data_iso = None
        if g.get("date"):
            data_iso = datetime.strptime(g["date"], "%d/%m/%Y").date().isoformat()
        ora = f'{g["time"]}' if g.get("time") else None
        games.append({
            "gameid": g["gameid"],
            "campionato": league,
            "stagione": season,
            "giornata": int(g["round"]),
            "data": data_iso,
            "ora": ora,
            "squadra_casa_id": int(g["teamid_home"]),
            "squadra_casa": g["teamname_home"],
            "squadra_ospite_id": int(g["teamid_away"]),
            "squadra_ospite": g["teamname_away"],
            "punti_casa": _int(g.get("score_home")),
            "punti_ospite": _int(g.get("score_away")),
            "palazzetto": g.get("arena"),
            "stato": g.get("game_status"),
            "stream_url": g.get("stream_url"),
        })
    return games


# ---------------------------------------------------------------- box score

def boxscore_url(gameid: str, league: str, season: str = config.STAGIONE) -> str:
    return f"{config.SITE_BASE}/wp/match/{gameid}/{league}/{season}"


def fetch_boxscore(client: RateLimitedClient, gameid: str, league: str,
                   season: str = config.STAGIONE) -> dict:
    resp = client.get(boxscore_url(gameid, league, season))
    resp.raise_for_status()
    return parse_boxscore(resp.text)


def parse_boxscore(html: str) -> dict:
    """Restituisce {'casa': {...}, 'ospite': {...}, 'parziali': [...]}.

    Ogni squadra: id, nome, giocatori (lista di dict), riga_squadra, totali.
    """
    soup = BeautifulSoup(html, "lxml")

    header = {}
    for side, css in (("casa", "match-team--home"), ("ospite", "match-team--away")):
        box = soup.select_one(f".{css}")
        if box is None:
            raise ParseError(f"intestazione squadra {side} non trovata")
        name = box.select_one(".team-name").get_text(strip=True)
        logo = box.select_one(".team-logo img")
        team_id = None
        if logo is not None:
            m = re.search(r"team_logo/(\d+)\.", logo.get("src", ""))
            team_id = int(m.group(1)) if m else None
        header[side] = {"id": team_id, "nome": name}

    wrapper = soup.select_one("#boxscore-ajax-wrapper")
    if wrapper is None:
        raise ParseError("contenitore del box score non trovato")
    titles = [h.get_text(strip=True) for h in wrapper.select("h3")]
    blocks = wrapper.select("div.table-wrapper-evo")
    if len(blocks) != 2 or len(titles) != 2:
        raise ParseError(f"attese 2 tabelle squadra, trovate {len(blocks)}")

    teams = [_parse_team_block(b) for b in blocks]
    # Associa i blocchi a casa/ospite tramite il nome (di solito casa è il primo)
    order = ["casa", "ospite"]
    if titles[0] == header["ospite"]["nome"] and titles[1] == header["casa"]["nome"]:
        order = ["ospite", "casa"]
    result = {}
    for side, team in zip(order, teams):
        result[side] = {**header[side], **team}

    result["parziali"] = _parse_periods(soup, result)
    return result


def _parse_team_block(block) -> dict:
    left = block.select_one("td.table-left table")
    right = block.select_one("td.table-right table")
    if left is None or right is None:
        raise ParseError("struttura tabella squadra inattesa")
    name_rows = left.select("tbody > tr")
    stat_rows = right.select("tbody > tr")
    if len(name_rows) != len(stat_rows):
        raise ParseError("righe nomi e statistiche non allineate")
    header = [th.get_text(strip=True) for th in right.select("thead tr")[-1].select("th")]
    if header[:2] != ["Pun", "Min"] or len(header) != len(STAT_COLUMNS):
        raise ParseError(f"colonne statistiche inattese: {header}")

    giocatori, riga_squadra, totali = [], None, None
    for nr, sr in zip(name_rows, stat_rows):
        ncells = nr.select("td")
        stats = _parse_stats([td.get_text(strip=True) for td in sr.select("td")])
        link = ncells[2].select_one("a")
        label = ncells[2].get_text(strip=True)
        if link is None:
            if label.lower() == "squadra":
                riga_squadra = stats
            elif label.lower() == "totali":
                totali = stats
            continue
        m = re.search(r"/giocatore/wp/([^/?#]+)", link.get("href", ""))
        giocatori.append({
            "giocatore_id": m.group(1) if m else label,
            "nome": _clean_name(label),
            "numero": ncells[0].get_text(strip=True) or None,
            "quintetto": ncells[1].get_text(strip=True) == "*",
            **stats,
        })
    if totali is None:
        raise ParseError("riga Totali non trovata")
    return {"giocatori": giocatori, "riga_squadra": riga_squadra, "totali": totali}


def _parse_stats(cells: list[str]) -> dict:
    if len(cells) != len(STAT_COLUMNS):
        raise ParseError(f"riga con {len(cells)} celle invece di {len(STAT_COLUMNS)}")
    out = {}
    for key, raw in zip(STAT_COLUMNS, cells):
        if key is None:
            continue
        if key == "minuti":
            out[key] = _minutes(raw)
        elif key == "oer":
            out[key] = _float(raw)
        else:
            out[key] = _int(raw)
    return out


def _parse_periods(soup, result) -> list[dict]:
    """Punteggi per periodo. Le colonne si attribuiscono confrontando le somme
    con il punteggio finale (le etichette della tabella sul sito non sono affidabili)."""
    table = soup.select_one(".match-result-periods table")
    if table is None:
        return []
    rows = []
    for tr in table.select("tbody tr"):
        vals = [_int(td.get_text(strip=True)) for td in tr.select("td")]
        if len(vals) == 2 and None not in vals:
            rows.append(vals)
    if not rows:
        return []
    pts_casa = result["casa"]["totali"]["punti"]
    sum0 = sum(r[0] for r in rows)
    swap = sum0 != pts_casa and sum(r[1] for r in rows) == pts_casa
    return [
        {"periodo": i + 1, "casa": r[1] if swap else r[0], "ospite": r[0] if swap else r[1]}
        for i, r in enumerate(rows)
    ]


# ---------------------------------------------------------------- utilità

def _int(raw) -> int | None:
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw in ("", "-"):
        return None
    try:
        return int(float(raw.replace(",", ".")))
    except ValueError:
        return None


def _float(raw) -> float | None:
    raw = (raw or "").strip().replace(",", ".")
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def _minutes(raw: str) -> float | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if ":" in raw:
        mm, ss = raw.split(":", 1)
        return int(mm) + int(ss) / 60
    return _float(raw)


def _clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


# ---------------------------------------------------------------- play-by-play

# testo azione -> (tipo normalizzato, zona di tiro)
PBP_TIPI = [
    ("Tiro realizzato da 3 punti", "tiro3_fatto", "tre"),
    ("Tiro sbagliato da 3 punti", "tiro3_sbagliato", "tre"),
    ("Tiro realizzato da 2 punti da fuori area", "tiro2_fatto", "fuori_area"),
    ("Tiro realizzato dall'area", "tiro2_fatto", "area"),
    ("Tiro sbagliato da fuori area", "tiro2_sbagliato", "fuori_area"),
    ("Tiro sbagliato dall'area", "tiro2_sbagliato", "area"),
    ("Schiacciata", "tiro2_fatto", "schiacciata"),
    ("Tiro libero segnato", "tl_fatto", None),
    ("Tiro libero sbagliato", "tl_sbagliato", None),
    ("Rimbalzo offensivo", "rimb_off", None),
    ("Rimbalzo difensivo", "rimb_dif", None),
    ("Assist", "assist", None),
    ("Palla persa", "persa", None),
    ("Palla recuperata", "recupero", None),
    ("Stoppata Subita", "stoppata_subita", None),
    ("Stoppata", "stoppata", None),
    ("Fallo tecnico", "fallo_tecnico", None),
    ("Fallo commesso", "fallo", None),
    ("Fallo subito", "fallo_subito", None),
    ("Cambio", "cambio", None),
    ("Timeout", "timeout", None),
]


def pbp_url(gameid: str, league: str, season: str = config.STAGIONE) -> str:
    return boxscore_url(gameid, league, season) + "/play-by-play"


def fetch_pbp(client: RateLimitedClient, gameid: str, league: str,
              season: str = config.STAGIONE) -> dict:
    resp = client.get(pbp_url(gameid, league, season))
    resp.raise_for_status()
    return parse_pbp(resp.text)


def classify_action(text: str) -> tuple[str, str | None, bool]:
    """(tipo, zona, di_squadra) a partire dal testo dell'azione."""
    di_squadra = "di squadra" in text
    base = text.replace(" di squadra", "").strip()
    for prefix, tipo, zona in PBP_TIPI:
        if base.startswith(prefix):
            return tipo, zona, di_squadra
    return "altro", None, di_squadra


def parse_pbp(html: str) -> dict:
    """Cronaca: {'squadre': [nome_casa, nome_ospite], 'eventi': [...]}.

    Ogni evento: n, periodo, secondi (trascorsi dall'inizio partita), lato ('casa'/'ospite'),
    giocatore_id, tipo, zona, di_squadra, testo, punti_casa, punti_ospite."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.sticky-table") or soup.select_one(".play-by-play-content table")
    if table is None:
        raise ParseError("tabella play-by-play non trovata")
    head = [th.get_text(strip=True) for th in table.select("thead th")]
    if len(head) != 5 or head[0] != "Minuto":
        raise ParseError(f"intestazione play-by-play inattesa: {head}")
    eventi, nomi = [], {}
    for tr in table.select("tbody tr"):
        td = tr.select("td")
        if len(td) != 5:
            continue
        clock = td[0].get_text(strip=True)
        score = td[2].get_text(strip=True)
        m = re.match(r"(\d+)-(\d+)", score)
        secondi = _clock(clock)
        for lato, cell in (("casa", td[1]), ("ospite", td[4])):
            text = cell.get_text(" ", strip=True)
            if not text:
                continue
            link = cell.select_one("a")
            gid = None
            if link is not None:
                mm = re.search(r"/giocatore/wp/([^/?#]+)", link.get("href", ""))
                gid = mm.group(1) if mm else None
                if gid:
                    nomi[gid] = link.get_text(" ", strip=True)
                azione = text.split(",", 1)[1].strip() if "," in text else text
            else:
                azione = text
            tipo, zona, di_squadra = classify_action(azione)
            eventi.append({
                "n": len(eventi), "periodo": _int(tr.get("data-period")), "secondi": secondi,
                "lato": lato, "giocatore_id": gid, "tipo": tipo, "zona": zona,
                "di_squadra": di_squadra or gid is None, "testo": azione,
                "punti_casa": int(m.group(1)) if m else None,
                "punti_ospite": int(m.group(2)) if m else None,
            })
    if not eventi:
        raise ParseError("play-by-play vuoto")
    return {"squadre": [head[1], head[4]], "eventi": eventi, "nomi": nomi}


def _clock(raw: str) -> int | None:
    m = re.match(r"(\d+):(\d+)", raw or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


# ---------------------------------------------------------------- anagrafica giocatore

def player_url(giocatore_id: str) -> str:
    return f"{config.SITE_BASE}/giocatore/wp/{giocatore_id}"


def fetch_player(client: RateLimitedClient, giocatore_id: str) -> dict:
    resp = client.get(player_url(giocatore_id))
    resp.raise_for_status()
    return parse_player(resp.text)


def parse_player(html: str) -> dict:
    """Anagrafica: data_nascita (ISO), nazionalita, altezza_cm, peso_kg, societa."""
    soup = BeautifulSoup(html, "lxml")
    specs = {}
    for li in soup.select(".player-mini-specs li"):
        label = li.select_one(".spec-label")
        value = li.select_one(".spec-value")
        if label and value:
            specs[label.get_text(strip=True).rstrip(":").lower()] = value.get_text(" ", strip=True)
    if not specs:
        raise ParseError("anagrafica giocatore non trovata")
    nascita = None
    if specs.get("data di nascita"):
        try:
            nascita = datetime.strptime(specs["data di nascita"], "%d/%m/%Y").date().isoformat()
        except ValueError:
            nascita = None
    return {
        "data_nascita": nascita,
        "nazionalita": (specs.get("nazionalità") or "").upper() or None,
        "altezza_cm": _int(re.sub(r"[^\d]", "", specs.get("altezza", "")) or None),
        "peso_kg": _int(re.sub(r"[^\d]", "", specs.get("peso", "")) or None),
        "societa": specs.get("società"),
    }
