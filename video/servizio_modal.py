"""Servizio di analisi delle clip su Modal (GPU T4, si paga solo il tempo di elaborazione).

Tre funzioni, una per passaggio (vedi video/analisi.py); lo stato di ogni lavoro e i
palazzetti già calibrati stanno in un volume privato di Modal, mai nel repository.
Il sito lo pubblica da solo alla prima analisi (pubblica()), con il token nei Secrets.
"""

import modal

NOME = "assist-video"
VERSIONE = "1"                    # cambiarla quando cambia l'analisi: il sito ripubblica
MODELLO = "/modelli/yolox_m.onnx"

immagine = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04", add_python="3.11")
    .apt_install("ffmpeg", "curl", "libgl1", "libglib2.0-0")
    .pip_install("numpy<2.3", "scipy", "opencv-python-headless>=4.9", "onnxruntime-gpu>=1.19")
    .run_commands("mkdir -p /modelli && curl -sL -o /modelli/yolox_m.onnx "
                  "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_m.onnx")
    .add_local_python_source("video")
)
app = modal.App(NOME, image=immagine)
volume = modal.Volume.from_name("assist-video-dati", create_if_missing=True)
DATI = "/dati"


def _salva(nome, oggetto):
    import os, pickle
    os.makedirs(os.path.dirname(f"{DATI}/{nome}"), exist_ok=True)
    with open(f"{DATI}/{nome}", "wb") as f:
        pickle.dump(oggetto, f)
    volume.commit()


def _pulisci(ore=48):
    """I lavori (fotogrammi e rilevamenti di una clip) non restano: dopo due giorni si cancellano."""
    import glob, os, time
    for f in glob.glob(f"{DATI}/lavori/*.pkl"):
        if time.time() - os.path.getmtime(f) > ore * 3600:
            os.remove(f)


def _carica(nome):
    import pickle
    volume.reload()
    with open(f"{DATI}/{nome}", "rb") as f:
        return pickle.load(f)


def _riferimenti(club):
    import glob, pickle
    volume.reload()
    out = []
    for f in glob.glob(f"{DATI}/campi/{club}/*.pkl"):
        with open(f, "rb") as fh:
            out.append(pickle.load(fh))
    return out


@app.function(gpu="T4", timeout=900, volumes={DATI: volume}, scaledown_window=60)
def rileva(lavoro: str, club: str, video: bytes, estensione: str = ".mp4", inizio: float = 0.0, durata: float = 20.0):
    """Passaggio 1. Restituisce il fotogramma per i tocchi e, se il palazzetto è noto,
    direttamente i momenti chiave."""
    import os, tempfile
    from video import analisi as A
    p = tempfile.mktemp(suffix=estensione)
    with open(p, "wb") as f:
        f.write(video)
    stato = A.rileva(p, MODELLO, _riferimenti(club), inizio, durata)
    os.remove(p)                                      # la clip non resta nel servizio
    _pulisci()
    out = {"ancora": A.ridotta(stato["ancora"], 1600), "dim": stato["dim"], "auto": None, "fotogrammi": stato["n"]}
    if stato["auto"]:
        controllo, momenti = A.calibra(stato)
        out.update(auto={"nome": stato["auto"]["nome"], "lato": stato["lato"]}, controllo=controllo, momenti=momenti)
    _salva(f"lavori/{lavoro}.pkl", stato)
    return out


@app.function(cpu=2, memory=4096, timeout=300, volumes={DATI: volume})
def calibra(lavoro: str, club: str, punti: list, palazzetto: str = ""):
    """Passaggio 2 (solo la prima volta in un palazzetto): i 4 tocchi sull'area."""
    from video import analisi as A
    stato = _carica(f"lavori/{lavoro}.pkl")
    controllo, momenti = A.calibra(stato, punti)
    _salva(f"lavori/{lavoro}.pkl", stato)
    if palazzetto:
        nome = "".join(c for c in palazzetto if c.isalnum()) or "campo"
        _salva(f"campi/{club}/{nome}_{stato['lato']}.pkl", A.riferimento(stato, palazzetto))
    return {"controllo": controllo, "momenti": momenti, "lato": stato["lato"]}


@app.function(cpu=2, memory=4096, timeout=300, volumes={DATI: volume})
def costruisci(lavoro: str, marcature: dict, nome: str, clip: str, tipo: str):
    """Passaggio 3: la bozza del gioco per la lavagna."""
    from video import analisi as A
    import os
    stato = _carica(f"lavori/{lavoro}.pkl")
    out = A.costruisci(stato, marcature, nome, clip, tipo)
    os.remove(f"{DATI}/lavori/{lavoro}.pkl"); volume.commit()   # finito il gioco, il lavoro si cancella
    return out


@app.function(volumes={DATI: volume})
def versione():
    return VERSIONE


def pubblica():
    """Pubblica (o aggiorna) il servizio dal sito. Torna True se l'ha ripubblicato."""
    try:
        if modal.Function.from_name(NOME, "versione").remote() == VERSIONE:
            return False
    except Exception:
        pass
    app.deploy(name=NOME)
    return True


def funzione(nome):
    return modal.Function.from_name(NOME, nome)
