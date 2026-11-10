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
DA_PREPARARE = ("players", "profile", "lineups", "shots", "clutch_players", "assists", "fouls",
                "alerts", "_prior", "origini_partita", "rotazioni", "taglie", "momenti", "presenze")
# analisi pesanti (decine di MB) che servono solo ad alcune pagine: in un file a parte, letto
# la prima volta che servono, per non occupare memoria finché nessuno le apre
PIGRE = ("leverage_eventi", "leverage")
_CODICE = ("analysis.py", "pbp.py", "contesto.py", "db.py", "approfondimenti.py", "previsioni.py",
           "leverage.py", "avvisi.py", "mercato.py", "impatto.py", "verifica_chiavi.py", "chiavi.py", "validazione.py", "precalcolo.py")


def _chiave(stagione: str) -> str:
    h = hashlib.sha256()
    st = config.DB_PATH.stat()
    h.update(f"{st.st_size}:{st.st_mtime_ns}:{stagione}".encode())
    for nome in _CODICE:                      # codice cambiato: i risultati salvati non valgono più
        h.update((Path(__file__).parent / nome).read_bytes())
    return h.hexdigest()[:20]


def _file(stagione: str, parte: str = "") -> Path:
    return CARTELLA / f"{stagione}-{_chiave(stagione)}{'-' + parte if parte else ''}.pkl"


def prepara(stagione: str = config.STAGIONE, verifiche: bool = True) -> Path:
    """Calcola e salva le analisi della stagione; restituisce il file."""
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), stagione)
    for nome in DA_PREPARARE:
        getattr(ctx, nome)
    for camp in ctx.bs["campionato_id"].unique():      # forza delle squadre e fattore campo
        ctx.forze(camp), ctx.hca(camp)
    try:                                               # impatto dei giocatori (Scouting, obiettivi)
        from . import impatto
        impatto.storico(ctx)
    except Exception:  # noqa: BLE001
        pass
    dati = {k: v for k, v in vars(ctx).items() if k not in ("conn", "stagione", "_prossime", "_vigilie", "_verifiche")}
    CARTELLA.mkdir(parents=True, exist_ok=True)
    for vecchio in CARTELLA.glob(f"{stagione}-*.pkl"):
        vecchio.unlink(missing_ok=True)
    f = _file(stagione)
    tmp = f.with_suffix(".tmp")
    with open(tmp, "wb") as out:
        pickle.dump(dati, out, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(f)
    try:                                               # chiavi della vigilia contro le partite giocate
        from . import verifica_chiavi
        if not verifiche:
            raise RuntimeError("non richieste")
        _scrivi(_file(stagione, "verifiche"), verifica_chiavi.prepara_tutte(ctx))
    except Exception:  # noqa: BLE001  (si calcoleranno alla prima apertura)
        pass
    ctx.__dict__.pop("_verifiche", None)
    # memoria: prima delle analisi pesanti si libera tutto quello che non serve a calcolarle
    import gc
    del dati
    tieni = {"conn", "stagione", "ev", "stints", "bs", "bg", "_prior", "_forze", "_hca"}
    for k in [k for k in vars(ctx) if k not in tieni]:
        del ctx.__dict__[k]
    gc.collect()
    for nome in PIGRE:
        try:
            _scrivi(_file(stagione, nome), getattr(ctx, nome))
        except Exception:  # noqa: BLE001  (si calcolerà quando serve)
            pass
        if nome == "leverage_eventi":         # per i crediti basta la cronaca con gli swing
            ctx.__dict__.pop("ev", None)
            gc.collect()
    return f


def _scrivi(f: Path, dati):
    tmp = f.with_suffix(".tmp")
    with open(tmp, "wb") as out:
        pickle.dump(dati, out, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(f)


def _file_storico() -> Path:
    return CARTELLA / f"storico-{_chiave('tutte')}.pkl"


def prepara_storico() -> Path:
    """Archivio dei giocatori di tutte le stagioni (figurine, mercato, report del giocatore)."""
    from . import mercato
    dati = mercato.season_lines(db.connect(config.DB_PATH, readonly=True))
    CARTELLA.mkdir(parents=True, exist_ok=True)
    for vecchio in CARTELLA.glob("storico-*.pkl"):
        vecchio.unlink(missing_ok=True)
    f = _file_storico()
    _scrivi(f, dati)
    return f


def storico():
    """L'archivio delle stagioni preparato all'avvio, o None se va calcolato."""
    try:
        f = _file_storico()
        if f.exists():
            with open(f, "rb") as inp:
                return pickle.load(inp)
    except Exception:  # noqa: BLE001
        pass
    return None


def pigra(ctx: Contesto, nome: str):
    """Un'analisi pesante preparata all'avvio, o None se va calcolata."""
    try:
        f = _file(ctx.stagione, nome)
        if f.exists():
            with open(f, "rb") as inp:
                return pickle.load(inp)
    except Exception:  # noqa: BLE001
        pass
    return None


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
    ctx.__dict__["_preparato"] = True
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
    t = time.time()
    try:
        prepara_storico()
        print(f"Archivio delle stagioni pronto in {time.time() - t:.1f} s")
    except Exception as e:  # noqa: BLE001
        print(f"Archivio delle stagioni non preparato: {e}")
