"""Figurine dei giocatori: per ogni giocatore di rotazione foto, numero, ruolo, il valore di
impatto (percentile tra i giocatori dello stesso ruolo e campionato), sei barre di confronto
con il ruolo e quattro numeri a partita scelti per ruolo.

I dati vengono dalle schede giocatore (foto, maglia, ruolo, anagrafica) e dal profilo per
ruolo del confronto giocatori (percentili per dimensione)."""

import pandas as pd

from . import confronto as CF
from . import scheda_giocatori as SG

BARRE = [("Realizzazione", "Realizzazione"), ("Creazione", "Creazione"),
         ("Tiro da fuori", "Tiro da fuori"), ("Rimbalzo", "Rimbalzo"),
         ("Difesa e attività", "Difesa"), ("Impatto", "Impatto")]
SIGLA_RUOLO = {"Play / guardia": "PLAY", "Esterno / ala": "ALA", "Lungo": "LUNGO"}
PLURALE_RUOLO = {"Play / guardia": "play e guardie", "Esterno / ala": "esterni e ali", "Lungo": "lunghi"}


def _it(v, d=1) -> str:
    return "–" if v is None or pd.isna(v) else f"{float(v):.{d}f}".replace(".", ",")


PARTICELLE = {"de", "di", "da", "del", "della", "dalla", "dal", "dei", "degli", "lo", "la", "le", "li",
              "van", "von", "der", "den", "mc", "mac", "st.", "el", "al", "ben", "dos", "das", "du"}


def maiuscole(nome):
    """Nomi propri con le maiuscole giuste: "Andrea De nicolao" → "Andrea De Nicolao"."""
    if not isinstance(nome, str):
        return nome
    parti = nome.split()
    return " ".join(p[:1].upper() + p[1:] if p.islower() and (i == 0 or p not in PARTICELLE) else p
                    for i, p in enumerate(parti))


def dividi_nome(completo: str) -> tuple[str, str]:
    """Nome e cognome, con le particelle nel cognome: "Andrea De Nicolao" → ("Andrea", "De Nicolao")."""
    parti = str(completo).split()
    if len(parti) < 2:
        return "", str(completo)
    i = len(parti) - 1
    while i > 1 and parti[i - 1].lower() in PARTICELLE:
        i -= 1
    return " ".join(parti[:i]), " ".join(parti[i:])


def _numeri(r: pd.Series, ruolo: str) -> list[tuple[str, str]]:
    """Quattro numeri a partita, scelti per ruolo."""
    base = [("PT", _it(r.get("punti_pg"))), ("RIM", _it(r.get("rimb_tot_pg"))), ("AST", _it(r.get("assist_pg")))]
    if ruolo == "Lungo":
        return base + [("TS%", _it(r.get("ts_pct")))]
    return base + [("3P%", _it(r.get("t3_pct")))]


def carte(ctx, hist: pd.DataFrame, sid: int, massimo: int = 8, minuti: float = 10.0,
          foto: bool = True) -> list[dict]:
    """Figurine dei giocatori di rotazione di una squadra, per minuti giocati."""
    out = []
    for s in SG.schede(ctx, sid, foto=foto, minuti=minuti, massimo=massimo):
        p = CF.scheda(hist, s["giocatore_id"], ctx.stagione)
        if p is None:
            continue
        r, ruolo = p["riga"], p["ruolo"]
        dims = {etichetta: p["dimensioni"].get(chiave) for chiave, etichetta in BARRE}
        nome, cognome = dividi_nome(maiuscole(s["nome"]))
        out.append({
            "giocatore_id": s["giocatore_id"], "nome": nome, "cognome": cognome, "maglia": s.get("maglia"),
            "ruolo_sito": s.get("ruolo"), "ruolo": ruolo, "sigla": SIGLA_RUOLO.get(ruolo, ruolo.upper()),
            "meta": SG.meta(s), "foto": s.get("foto"), "impatto": dims.get("Impatto"),
            "barre": dims, "numeri": _numeri(r, ruolo),
            "piede": f"Confronto con {p['pool']} {PLURALE_RUOLO.get(ruolo, ruolo.lower())} di {p['scala']} · "
                     f"{int(r['partite'])} partite, {_it(r['minuti_pg'])} minuti",
            "pochi_dati": bool(p["pochi_dati"])})
    return out
