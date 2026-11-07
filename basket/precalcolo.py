"""Analisi della stagione preparate prima che arrivino gli utenti.

Ogni aggiornamento dei dati ripubblica la piattaforma, e il primo utente dopo il riavvio
aspettava qualche secondo mentre si calcolavano cronaca, quintetti, On-Off e profili delle
squadre. All'avvio (render_start.sh) questo modulo li calcola per la stagione in corso e li
salva su disco: la piattaforma li legge in pochi decimi di secondo. Il file vale solo per lo
stesso database e la stessa versione del codice di analisi; altrimenti si ricalcola come prima.
"""

import hashlib
import pickle
import sys
import time
from pathlib import Path

from . import config, db
from .contesto import Contesto

CARTELLA = config.ROOT / ".cache" / "contesto"
# analisi che servono appena si entra (Home, Scouting, La mia squadra)
DA_PREPARARE = ("players", "profile", "lineups", "shots", "clutch_players", "assists", "fouls")
_CODICE = ("analysis.py", "pbp.py", "contesto.py", "db.py", "approfondimenti.py")


def _chiave(stagione: str) -> str:
    h = hashlib.sha256()
    st = config.DB_PATH.stat()
    h.update(f"{st.st_size}:{st.st_mtime_ns}:{stagione}".encode())
    for nome in _CODICE:                      # codice cambiato: i risultati salvati non valgono più
        h.update((Path(__file__).parent / nome).read_bytes())
    return h.hexdigest()[:20]


def _file(stagione: str) -> Path:
    return CARTELLA / f"{stagione}-{_chiave(stagione)}.pkl"


def prepara(stagione: str = config.STAGIONE) -> Path:
    """Calcola e salva le analisi della stagione; restituisce il file."""
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), stagione)
    for nome in DA_PREPARARE:
        getattr(ctx, nome)
    dati = {k: v for k, v in vars(ctx).items() if k not in ("conn", "stagione")}
    CARTELLA.mkdir(parents=True, exist_ok=True)
    for vecchio in CARTELLA.glob(f"{stagione}-*.pkl"):
        vecchio.unlink(missing_ok=True)
    f = _file(stagione)
    tmp = f.with_suffix(".tmp")
    with open(tmp, "wb") as out:
        pickle.dump(dati, out, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(f)
    return f


def carica(ctx: Contesto) -> bool:
    """Mette nel contesto le analisi salvate, se sono dello stesso database e codice."""
    try:
        f = _file(ctx.stagione)
        if not f.exists():
            return False
        with open(f, "rb") as inp:
            dati = pickle.load(inp)
    except Exception:  # noqa: BLE001  (file rovinato o di un'altra versione: si ricalcola)
        return False
    for k, v in dati.items():
        ctx.__dict__.setdefault(k, v)
    return True


if __name__ == "__main__":
    stagioni = sys.argv[1:] or [config.STAGIONE]
    for s in stagioni:
        t = time.time()
        try:
            f = prepara(s)
            print(f"Analisi {s} pronte in {time.time() - t:.1f} s ({f.stat().st_size / 1e6:.1f} MB)")
        except Exception as e:  # noqa: BLE001  (l'avvio non deve fermarsi: si calcola al primo accesso)
            print(f"Analisi {s} non preparate: {e}")
