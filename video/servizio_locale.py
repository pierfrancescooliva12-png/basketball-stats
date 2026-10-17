"""Stesso servizio di servizio_modal, ma sul computer (processore): per lo sviluppo e le prove.
Si attiva con ASSIST_VIDEO_LOCALE=1 e il modello in ASSIST_YOLOX (percorso del file .onnx)."""

import os
import pickle
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_esecutore = ThreadPoolExecutor(max_workers=1)
_lavori: dict = {}
CAMPI = Path(os.environ.get("ASSIST_VIDEO_CAMPI", Path.home() / ".assist_video" / "campi"))


class _Chiamata:
    def __init__(self, futuro):
        self.f = futuro

    def get(self, timeout=None):
        from concurrent.futures import TimeoutError as Scaduto
        try:
            return self.f.result(timeout=timeout)
        except Scaduto:
            raise TimeoutError


def _riferimenti(club):
    out = []
    for f in (CAMPI / club).glob("*.pkl"):
        out.append(pickle.loads(f.read_bytes()))
    return out


def _rileva(lavoro, club, video, estensione=".mp4", inizio=0.0, durata=20.0):
    from video import analisi as A
    p = tempfile.mktemp(suffix=estensione)
    Path(p).write_bytes(video)
    stato = A.rileva(p, os.environ["ASSIST_YOLOX"], _riferimenti(club), inizio, durata)
    out = {"ancora": A.ridotta(stato["ancora"], 1600), "dim": stato["dim"], "auto": None, "fotogrammi": stato["n"]}
    if stato["auto"]:
        controllo, momenti = A.calibra(stato)
        out.update(auto={"nome": stato["auto"]["nome"], "lato": stato["lato"]}, controllo=controllo, momenti=momenti)
    _lavori[lavoro] = stato
    return out


def _calibra(lavoro, club, punti, palazzetto=""):
    from video import analisi as A
    stato = _lavori[lavoro]
    controllo, momenti = A.calibra(stato, punti)
    if palazzetto:
        (CAMPI / club).mkdir(parents=True, exist_ok=True)
        nome = "".join(c for c in palazzetto if c.isalnum()) or "campo"
        (CAMPI / club / f"{nome}_{stato['lato']}.pkl").write_bytes(pickle.dumps(A.riferimento(stato, palazzetto)))
    return {"controllo": controllo, "momenti": momenti, "lato": stato["lato"]}


def _costruisci(lavoro, marcature, nome, clip, tipo):
    from video import analisi as A
    return A.costruisci(_lavori[lavoro], marcature, nome, clip, tipo)


class _Funzione:
    def __init__(self, f):
        self.f = f

    def spawn(self, *a, **k):
        return _Chiamata(_esecutore.submit(self.f, *a, **k))

    def remote(self, *a, **k):
        return self.f(*a, **k)


_FUNZIONI = {"rileva": _rileva, "calibra": _calibra, "costruisci": _costruisci}


def pubblica():
    return False


def funzione(nome):
    return _Funzione(_FUNZIONI[nome])
