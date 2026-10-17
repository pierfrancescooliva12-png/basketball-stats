"""Dalla clip alla bozza del gioco per la lavagna.

Tre passaggi, con due interventi dello staff in mezzo:
1. rileva(): fotogrammi, giocatori e palla (YOLOX a tasselli), movimento della telecamera
   (ORB sul parquet); se il palazzetto è già calibrato, aggancio automatico del campo (SIFT).
2. calibra(): con i 4 tocchi sugli angoli dell'area (prima volta in un palazzetto) o con
   l'aggancio automatico, posizione sul parquet di ogni persona; momenti chiave con una
   proposta di squadre (colore della maglia) da correggere.
3. costruisci(): dai momenti chiave marcati (attacco / difesa) tracciamento guidato,
   portatore dalla palla, passaggi, fasi, linee e tempi del video, nel formato della lavagna.

Coordinate del campo: decimetri della lavagna (metà campo 150 × 140, fondo a y = 0,
canestro in (75, 15.75)); il lato della telecamera finisce a destra o a sinistra a seconda
del canestro attaccato, come se si guardasse il canestro da metà campo.
"""

import glob
import os
import subprocess
import tempfile

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

FPS = 20
LATO = 1600                      # larghezza di lavoro per il rilevamento
CANESTRO = np.array([75.0, 15.75])
AREA = {"sinistra": [[50.5, 0], [99.5, 0], [50.5, 58], [99.5, 58]],   # fondo lontano, fondo vicino,
        "destra": [[99.5, 0], [50.5, 0], [99.5, 58], [50.5, 58]]}     # lunetta lontano, lunetta vicino


# ------------------------------------------------------------------ fotogrammi

def fotogrammi(video: str, cartella: str, inizio: float = 0.0, durata: float = 20.0) -> list[str]:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(inizio), "-t", str(durata), "-i", video,
                    "-vf", f"fps={FPS}", "-q:v", "2", os.path.join(cartella, "f_%04d.jpg")], check=True)
    return sorted(glob.glob(os.path.join(cartella, "f_*.jpg")))


def fascia(img) -> tuple[int, int]:
    """Righe del video vero (senza le bande nere di una registrazione dello schermo)."""
    r = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean(1)
    righe = np.where(r > 8)[0]
    return (int(righe[0]), int(righe[-1]) + 1) if len(righe) else (0, img.shape[0])


# ------------------------------------------------------------------ rilevamento (YOLOX)

class Rilevatore:
    def __init__(self, modello: str):
        import onnxruntime as ort
        disp = ort.get_available_providers()
        prov = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in disp]
        self.s = ort.InferenceSession(modello, providers=prov)
        self.inp = self.s.get_inputs()[0].name
        g, st = [], []
        for passo in (8, 16, 32):
            n = 640 // passo
            xv, yv = np.meshgrid(np.arange(n), np.arange(n))
            g.append(np.stack((xv, yv), 2).reshape(1, -1, 2)); st.append(np.full((1, n * n, 1), passo))
        self.griglia, self.passi = np.concatenate(g, 1), np.concatenate(st, 1)

    def _tassello(self, img):
        h, w = img.shape[:2]
        pad = np.full((640, 640, 3), 114, np.uint8); pad[:h, :w] = img
        o = self.s.run(None, {self.inp: pad.transpose(2, 0, 1)[None].astype(np.float32)})[0]
        o[..., :2] = (o[..., :2] + self.griglia) * self.passi
        o[..., 2:4] = np.exp(o[..., 2:4]) * self.passi
        o = o[0]; sc = o[:, 4:5] * o[:, 5:]
        out = []
        for c, soglia in ((0, 0.25), (32, 0.15)):                  # persona, palla
            m = sc[:, c] > soglia
            for (cx, cy, bw, bh), p in zip(o[m, :4], sc[m, c]):
                out.append([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2, float(p), c])
        return out

    def rileva(self, img, y0, y1):
        """Persone e palla su tasselli sovrapposti (i giocatori lontani sono piccoli)."""
        banda = img[y0:y1]; sc = LATO / banda.shape[1]
        im = cv2.resize(banda, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        H, W = im.shape[:2]
        xs = list(range(0, max(1, W - 640), 480)) + [max(0, W - 640)]
        ys = list(range(0, max(1, H - 640), 380)) + [max(0, H - 640)]
        dets = []
        for x0 in sorted(set(xs)):
            for yy in sorted(set(ys)):
                for d in self._tassello(im[yy:yy + 640, x0:x0 + 640]):
                    dets.append([d[0] + x0, d[1] + yy, d[2] + x0, d[3] + yy, d[4], d[5]])
        out = []
        for c in (0, 32):
            d = [x for x in dets if x[5] == c]
            if not d: continue
            b = [[x[0], x[1], x[2] - x[0], x[3] - x[1]] for x in d]
            for i in np.array(cv2.dnn.NMSBoxes(b, [x[4] for x in d], 0.1, 0.5)).flatten():
                x = d[int(i)]
                out.append([x[0] / sc, x[1] / sc + y0, x[2] / sc, x[3] / sc + y0, x[4], c])
        return out


def istogramma(hsv, box):
    """Colore della maglia: istogramma HSV della parte alta del busto."""
    x0, y0, x1, y1 = box; h, w = y1 - y0, x1 - x0
    t = hsv[int(y0 + h * .15):int(y0 + h * .5), int(x0 + w * .2):int(x1 - w * .2)]
    H = cv2.calcHist([t], [0, 1, 2], None, [12, 6, 6], [0, 180, 0, 256, 0, 256])
    return cv2.normalize(H, H).flatten().astype(np.float32)


def colore(hsv, box):
    """Descrittore compatto della maglia per dividere le squadre: quota di pixel scuri e chiari e
    tinta dei pixel saturi, sulla parte centrale del busto (senza il parquet tra le braccia)."""
    x0, y0, x1, y1 = box; h, w = y1 - y0, x1 - x0
    t = hsv[int(y0 + h * .18):int(y0 + h * .45), int(x0 + w * .32):int(x1 - w * .32)].reshape(-1, 3).astype(np.float32)
    if len(t) < 6:
        return None
    H, S, V = t[:, 0], t[:, 1], t[:, 2]
    legno = (H >= 8) & (H <= 25) & (S > 70) & (S < 170) & (V > 120)
    saturi = (S > 90) & (V > 60) & ~legno
    tinta = np.histogram(H[saturi], bins=6, range=(0, 180))[0] / len(t)
    return np.concatenate([[2 * np.mean(V < 85), 2 * np.mean((V > 140) & (S < 80))], tinta]).astype(np.float32)


# ------------------------------------------------------------------ telecamera

def _maschera(shape, y0, y1, persone):
    m = np.zeros(shape[:2], np.uint8)
    m[y0 + int((y1 - y0) * 0.3):y1] = 255                           # parquet, non la tribuna
    m[y1 - int((y1 - y0) * 0.17):y1, :int(shape[1] * 0.35)] = 0      # grafica del punteggio
    for x0, yy0, x1, yy1, *_ in persone:
        m[max(0, int(yy0)):int(yy1), max(0, int(x0)):int(x1)] = 0
    return m


def movimento_telecamera(files, rilevamenti, y0, y1):
    """Omografie fotogramma → fotogramma di ancoraggio (quello centrale)."""
    orb = cv2.ORB_create(6000, fastThreshold=10); bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    kp, de = [], []
    for f, det in zip(files, rilevamenti):
        g = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        k, d = orb.detectAndCompute(g, _maschera(g.shape, y0, y1, [x for x in det if x[5] == 0]))
        kp.append(k); de.append(d)
    passi, qualita = [], []
    for i in range(len(files) - 1):
        H, n = np.eye(3), 0
        if de[i] is not None and de[i + 1] is not None:
            m = [a for a, b in (p for p in bf.knnMatch(de[i], de[i + 1], k=2) if len(p) == 2) if a.distance < 0.75 * b.distance]
            if len(m) >= 8:
                A = np.float32([kp[i][x.queryIdx].pt for x in m]); B = np.float32([kp[i + 1][x.trainIdx].pt for x in m])
                Hm, inl = cv2.findHomography(A, B, cv2.RANSAC, 3.0)
                if Hm is not None: H, n = Hm, int(inl.sum())
        passi.append(H); qualita.append(n)
    R = len(files) // 2
    M = [None] * len(files); M[R] = np.eye(3)
    for i in range(R - 1, -1, -1): M[i] = M[i + 1] @ passi[i]
    for i in range(R + 1, len(files)): M[i] = M[i - 1] @ np.linalg.inv(passi[i - 1])
    return R, M, qualita


def aggancia(img_gray, riferimenti, y0, y1):
    """Cerca il campo tra i palazzetti già calibrati. riferimenti: [{nome, lato, img, G}]."""
    sift = cv2.SIFT_create(6000)
    ma = np.zeros_like(img_gray); ma[y0 + int((y1 - y0) * 0.3):y0 + int((y1 - y0) * 0.83)] = 255
    ka, da = sift.detectAndCompute(img_gray, ma)
    meglio = None
    for r in riferimenti:
        b = r["img"]; mb = np.zeros_like(b); by0, by1 = r.get("fascia", (0, b.shape[0]))
        mb[by0 + int((by1 - by0) * 0.3):by0 + int((by1 - by0) * 0.83)] = 255
        kb, db = sift.detectAndCompute(b, mb)
        if da is None or db is None: continue
        m = [x for x, y in (p for p in cv2.BFMatcher().knnMatch(da, db, k=2) if len(p) == 2) if x.distance < 0.7 * y.distance]
        if len(m) < 20: continue
        A = np.float32([ka[x.queryIdx].pt for x in m]); B = np.float32([kb[x.trainIdx].pt for x in m])
        H, inl = cv2.findHomography(A, B, cv2.RANSAC, 4.0)
        if H is None: continue
        n = int(inl.sum())
        if n >= 60 and (meglio is None or n > meglio["coerenti"]):
            G = np.linalg.inv(np.linalg.inv(np.array(r["G"])) @ H)        # campo → pixel di questa clip
            meglio = {"nome": r["nome"], "lato": r["lato"], "G": G, "coerenti": n}
    return meglio


def da_tocchi(punti):
    """4 tocchi sugli angoli dell'area: fondo lontano, fondo vicino, lunetta lontano, lunetta vicino
    (lontano/vicino rispetto alla telecamera). Il lato del canestro si capisce dalla posizione."""
    p = np.float32(punti)
    lato = "sinistra" if p[:2, 0].mean() < p[2:, 0].mean() else "destra"
    return lato, cv2.getPerspectiveTransform(np.float32(AREA[lato]), p)


def righe_campo():
    L = [[(0, 0), (150, 0)], [(50.5, 0), (50.5, 58)], [(99.5, 0), (99.5, 58)], [(50.5, 58), (99.5, 58)],
         [(0, 0), (0, 140)], [(150, 0), (150, 140)], [(0, 140), (150, 140)], [(9, 0), (9, 29.9)], [(141, 0), (141, 29.9)]]
    for cx, cy, r, a0, a1 in ((75, 15.75, 67.5, 0.32, np.pi - 0.32), (75, 58, 18, 0, 2 * np.pi)):
        q = [(cx + r * np.cos(a), cy + r * np.sin(a)) for a in np.linspace(a0, a1, 40)]
        L += list(zip(q[:-1], q[1:]))
    return L


def disegna_campo(img, G, colore=(60, 230, 90)):
    out = img.copy()
    for a, b in righe_campo():
        q = cv2.perspectiveTransform(np.float32([a, b]).reshape(-1, 1, 2), G).reshape(-1, 2)
        if np.all(np.abs(q) < 8000):
            cv2.line(out, tuple(map(int, q[0])), tuple(map(int, q[1])), colore, 4)
    return out


# ------------------------------------------------------------------ persone sul parquet

def unisci_doppi(rr):
    """Due box sulla stessa persona (tasselli diversi): resta il più grande."""
    rr = sorted(rr, key=lambda r: -(r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1]))
    out = []
    for r in rr:
        a = r["box"]
        if any(max(0, min(a[2], q["box"][2]) - max(a[0], q["box"][0])) * max(0, min(a[3], q["box"][3]) - max(a[1], q["box"][1]))
               > 0.6 * (a[2] - a[0]) * (a[3] - a[1]) for q in out):
            continue
        out.append(r)
    return out


def persone_in_campo(stato):
    """Per ogni fotogramma: persone con i piedi sul parquet (coordinate della lavagna)."""
    per = []
    for i, cand in enumerate(stato["candidati"]):
        C = np.linalg.inv(stato["G"]) @ stato["M"][i]
        rr = []
        for c in cand:
            x0, y0, x1, y1 = c["box"]
            q = cv2.perspectiveTransform(np.float32([[[(x0 + x1) / 2, y1]]]), C)[0, 0]
            if -3 < q[0] < 153 and -3 < q[1] < 145:
                rr.append({**c, "x": float(q[0]), "y": float(q[1])})
        per.append(unisci_doppi(rr))
    return per


def bh(a, b):
    return cv2.compareHist(np.float32(a), np.float32(b), cv2.HISTCMP_BHATTACHARYYA)


def proponi_squadre(chiave):
    """Proposta di squadre per i momenti chiave: due gruppi di colore della maglia (chi è lontano
    da entrambi, come gli arbitri, resta senza squadra), poi attacco = il gruppo più lontano dal
    canestro (la difesa sta tra uomo e canestro). chiave: {k: [persone]} → {k: ["A"|"D"|"", ...]}.
    È solo una proposta: lo staff la corregge con un tocco."""
    tutti = [(k, j, r) for k, rr in chiave.items() for j, r in enumerate(rr)]
    if all("c" in r for _, _, r in tutti):                          # descrittore compatto della maglia
        tutti = [x for x in tutti if x[2]["c"] is not None]
        X = np.array([r["c"] for _, _, r in tutti], np.float32)
    else:
        X = np.sqrt(np.maximum(np.array([r["h"] for _, _, r in tutti], np.float32), 0))
    if len(tutti) < 4:
        return {k: [""] * len(rr) for k, rr in chiave.items()}
    _, lab, cen = cv2.kmeans(X, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4), 5,
                             cv2.KMEANS_PP_CENTERS)
    lab = lab.flatten(); gruppi = [0, 1]
    # arbitri e altri: lontani da entrambi i colori
    d = np.linalg.norm(X - cen[lab], axis=1)
    lontani = d > max(0.6, 2.5 * float(np.median(d)))
    lab = np.where(lontani, -1, lab)
    dist = {g: np.mean([np.hypot(r["x"] - CANESTRO[0], r["y"] - CANESTRO[1])
                        for (_, _, r), l in zip(tutti, lab) if l == g] or [0]) for g in gruppi}
    att = max(gruppi, key=dist.get)
    out = {k: [""] * len(rr) for k, rr in chiave.items()}
    for (k, j, _), l in zip(tutti, lab):
        out[k][j] = "A" if l == att else ("D" if l in gruppi else "")
    # al massimo 5 per squadra in ogni momento: restano i più somiglianti al colore della squadra
    vicino = {(k, j): float(x) for (k, j, _), x in zip(tutti, d)}
    for k, v in out.items():
        for chi in ("A", "D"):
            js = sorted([j for j, x in enumerate(v) if x == chi], key=lambda j: vicino.get((k, j), 0))
            for j in js[5:]: v[j] = ""
    return out


# ------------------------------------------------------------------ passaggio 1 e 2

def ridotta(jpg: bytes, larghezza: int) -> bytes:
    """JPEG più leggero da mandare al sito (le coordinate restano quelle originali)."""
    img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
    s = larghezza / img.shape[1]
    if s < 1: img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])[1].tobytes()


def rileva(video: str, modello: str, riferimenti=None, inizio=0.0, durata=20.0, avanzamento=None):
    """Fotogrammi, rilevamenti, telecamera e (se possibile) aggancio al campo."""
    tmp = tempfile.mkdtemp()
    files = fotogrammi(video, tmp, inizio, durata)
    if len(files) < 10:
        raise ValueError("Clip troppo corta o illeggibile.")
    prima = cv2.imread(files[0]); y0, y1 = fascia(prima)
    ril = Rilevatore(modello)
    rilevamenti, candidati = [], []
    for i, f in enumerate(files):
        img = cv2.imread(f); det = ril.rileva(img, y0, y1); rilevamenti.append(det)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        candidati.append([{"box": [float(v) for v in d[:4]], "p": d[4], "h": istogramma(hsv, d[:4]),
                           "c": colore(hsv, d[:4])}
                          for d in det if d[5] == 0 and d[4] >= 0.35 and d[3] - d[1] >= 60 * (y1 - y0) / 1328])
        if avanzamento and i % 20 == 0: avanzamento(i / len(files))
    R, M, qualita = movimento_telecamera(files, rilevamenti, y0, y1)
    ancora = cv2.imread(files[R])
    auto = aggancia(cv2.cvtColor(ancora, cv2.COLOR_BGR2GRAY), riferimenti or [], y0, y1)
    stato = {"inizio": float(inizio), "n": len(files), "fascia": (y0, y1), "R": R, "M": M, "qualita": qualita,
             "dim": (int(prima.shape[1]), int(prima.shape[0])),
             "rilevamenti": rilevamenti, "candidati": candidati, "auto": auto,
             "ancora": cv2.imencode(".jpg", ancora, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes(),
             "chiavi_img": {}}
    stato["momenti"] = list(range(0, len(files) - 1, 30)) + [len(files) - 1]
    for k in stato["momenti"]:
        stato["chiavi_img"][k] = cv2.imencode(".jpg", cv2.imread(files[k]), [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()
    return stato


def calibra(stato, punti=None):
    """Campo dai 4 tocchi (sul fotogramma di ancoraggio) o dall'aggancio automatico.
    Restituisce l'immagine di controllo e i momenti chiave con la proposta di squadre."""
    if punti is not None:
        lato, G = da_tocchi(punti)
    elif stato.get("auto"):
        lato, G = stato["auto"]["lato"], np.array(stato["auto"]["G"])
    else:
        raise ValueError("Servono i 4 tocchi sull'area.")
    stato["G"], stato["lato"] = G, lato
    stato["per"] = persone_in_campo(stato)
    ancora = cv2.imdecode(np.frombuffer(stato["ancora"], np.uint8), cv2.IMREAD_COLOR)
    controllo = ridotta(cv2.imencode(".jpg", disegna_campo(ancora, G))[1].tobytes(), 1280)
    chiave = {k: stato["per"][k] for k in stato["momenti"]}
    proposta = proponi_squadre(chiave)
    momenti = [{"k": k, "t": round(stato["inizio"] + k / FPS, 2), "img": ridotta(stato["chiavi_img"][k], 1280),
                "box": [r["box"] for r in chiave[k]], "proposta": proposta[k]} for k in stato["momenti"]]
    return controllo, momenti


# ------------------------------------------------------------------ passaggio 3

def _semplifica(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; n = np.linalg.norm(b - a) or 1
    d = np.abs((b[0] - a[0]) * (a[1] - p[:, 1]) - (a[0] - p[:, 0]) * (b[1] - a[1])) / n
    i = int(np.argmax(d))
    if d[i] > eps: return np.vstack([_semplifica(p[:i + 1], eps)[:-1], _semplifica(p[i:], eps)])
    return np.array([a, b])


def traccia(stato, marcature):
    """Tracciamento guidato. marcature: {k: {"A": [indici], "D": [indici]}} sui momenti chiave."""
    per, N = stato["per"], stato["n"]
    K = {int(k): v for k, v in marcature.items() if v.get("A") or v.get("D")}
    if not K:
        raise ValueError("Indica attacco e difesa in almeno un momento.")
    k0 = min(K)
    gioc, punti, box = [], {}, {}

    def nuovo(t, r, i):
        gioc.append({"t": t, "pos": np.array([r["x"], r["y"]]), "v": np.zeros(2), "h": np.float32(r["h"]), "ultimo": i})
        punti[len(gioc) - 1] = {i: np.array([r["x"], r["y"]])}; box[len(gioc) - 1] = {i: r["box"]}

    def assegna(i, cand, soglia, solo=None):
        idx = [g for g in range(len(gioc)) if solo is None or gioc[g]["t"] == solo]
        if not idx or not cand: return set()
        cost = np.zeros((len(idx), len(cand)))
        for a, g in enumerate(idx):
            G = gioc[g]; dt = i - G["ultimo"]; pr = G["pos"] + G["v"] * dt
            for b, r in enumerate(cand):
                cost[a, b] = np.hypot(pr[0] - r["x"], pr[1] - r["y"]) / (5 + 2.5 * dt) + 3 * bh(G["h"], r["h"])
        usati = set()
        for a, b in zip(*linear_sum_assignment(cost)):
            if cost[a, b] > soglia: continue
            G = gioc[idx[a]]; r = cand[b]; dt = i - G["ultimo"]; p = np.array([r["x"], r["y"]])
            G["v"] = 0.6 * G["v"] + 0.4 * (p - G["pos"]) / max(1, dt); G["pos"] = p; G["ultimo"] = i
            G["h"] = 0.92 * G["h"] + 0.08 * np.float32(r["h"])
            punti[idx[a]][i] = p; box[idx[a]][i] = r["box"]; usati.add(b)
        return usati

    for i in range(k0, N):
        if i in K:
            for t, chi in (("o", "A"), ("x", "D")):
                cand = [per[i][j] for j in K[i].get(chi, []) if j < len(per[i])]
                usati = assegna(i, cand, 99, solo=t)
                for b, r in enumerate(cand):          # entrati nell'inquadratura
                    if b not in usati and sum(1 for g in gioc if g["t"] == t) < 5: nuovo(t, r, i)
        else:
            assegna(i, per[i], 2.8)
    idx = np.arange(N); P = []
    for g in range(len(gioc)):
        kk = sorted(punti[g]); X = np.array([punti[g][k] for k in kk])
        T = np.stack([np.interp(idx, kk, X[:, 0]), np.interp(idx, kk, X[:, 1])], 1)
        Q = np.array([np.median(T[max(0, i - 3):i + 4], 0) for i in range(N)])
        P.append(np.clip(np.array([Q[max(0, i - 3):i + 4].mean(0) for i in range(N)]), [2, 2], [148, 138]))
    return k0, gioc, P, box, {g: len(punti[g]) for g in range(len(gioc))}


def portatore(stato, att, box, N):
    """Attaccante più vicino alla palla rilevata (nell'immagine), riempito e filtrato."""
    port = [None] * N
    for i in range(N):
        palle = [d for d in stato["rilevamenti"][i] if d[5] == 32]
        if not palle: continue
        x0, y0, x1, y1, *_ = max(palle, key=lambda d: d[4]); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        best, d0 = None, 1e9
        for g in att:
            if i not in box[g]: continue
            bx0, by0, bx1, by1 = box[g][i]
            d = np.hypot(cx - min(max(cx, bx0), bx1), cy - min(max(cy, by0), by1)) / (by1 - by0)
            if d < d0: d0, best = d, g
        if best is not None and d0 < 0.35: port[i] = best
    return port


def costruisci(stato, marcature, nome="Gioco dal video", clip="clip", tipo="avversaria", fine=None):
    N = stato["n"]
    k0, gioc, P, box, visti = traccia(stato, marcature)
    att = [g for g in range(len(gioc)) if gioc[g]["t"] == "o"]
    dif = [g for g in range(len(gioc)) if gioc[g]["t"] == "x"]
    if not att:
        raise ValueError("Nessun attaccante indicato.")
    port = portatore(stato, att, box, N)
    noto = [i for i in range(N) if port[i] is not None]
    ultimo = port[noto[0]] if noto else att[0]
    pieno = []
    for i in range(N):
        if port[i] is not None: ultimo = port[i]
        pieno.append(ultimo)
    liscio = []
    for i in range(N):
        w = pieno[max(0, i - 6):i + 7]; liscio.append(max(set(w), key=w.count))
    ordine = [liscio[k0]] + sorted([g for g in att if g != liscio[k0]], key=lambda g: P[g][k0, 0])
    nomi = {g: f"o{n + 1}" for n, g in enumerate(ordine)}
    if dif:
        C = np.array([[np.hypot(*(P[a][k0] - P[d][k0])) for d in dif] for a in ordine])
        liberi = list(range(1, 6))
        for a, b in zip(*linear_sum_assignment(C)):
            nomi[dif[b]] = f"x{a + 1}"; liberi.remove(a + 1)
        for d in dif:
            if d not in nomi: nomi[d] = f"x{liberi.pop(0)}"
    FINE = min(N - 1, fine if fine is not None else N - 1)
    cambi = [i for i in range(k0 + 1, FINE) if liscio[i] != liscio[i - 1]]
    tagli = [k0]
    for c in cambi + [FINE]:
        while c - tagli[-1] > 36: tagli.append(tagli[-1] + 30)
        if c - tagli[-1] >= 12: tagli.append(c)
    if tagli[-1] != FINE and FINE - tagli[-1] >= 12: tagli.append(FINE)
    r1 = lambda v: round(float(v), 1)
    fasi = []
    for j, k in enumerate(tagli):
        g = [{"id": nomi[q], "tipo": nomi[q][0], "n": int(nomi[q][1]), "x": r1(P[q][k, 0]), "y": r1(P[q][k, 1])}
             for q in range(len(gioc)) if q in nomi]
        linee, h0 = [], liscio[k]
        if j + 1 < len(tagli):
            k2 = tagli[j + 1]; h1 = liscio[k2]
            for q in att:
                tr = P[q][k:k2 + 1]; lung = np.linalg.norm(np.diff(tr, axis=0), axis=1).sum()
                if lung < 10: continue
                tipo_l = "palleggio" if q == h0 else "movimento"
                if q != h0:                      # blocco: arriva vicino al portatore e si ferma
                    vic = np.linalg.norm(P[q][k2] - P[h0][max(k, k2 - 8)])
                    fermo = np.linalg.norm(P[q][k2] - P[q][max(k, k2 - 6)])
                    if vic < 22 and fermo < 6 and lung > 25: tipo_l = "blocco"
                linee.append({"id": f"l{j}{nomi[q]}", "tipo": tipo_l, "da": nomi[q],
                              "punti": [[r1(x), r1(y)] for x, y in _semplifica(tr, 2.0)]})
            if h1 != h0:
                a, b = P[h0][k2], P[h1][k2]
                linee.append({"id": f"p{j}", "tipo": "passaggio", "da": nomi[h0], "a": nomi[h1],
                              "punti": [[r1(a[0]), r1(a[1])], [r1(b[0]), r1(b[1])]]})
        fasi.append({"giocatori": g, "linee": linee, "palla": nomi[h0], "nota": ""})
    gioco = {"id": f"g{abs(hash((clip, nome))) % 10**9}", "nome": nome, "tipo": tipo, "palla": fasi[0]["palla"],
             "difesa": bool(dif), "difesaTipo": "manuale" if dif else "nessuna", "fasi": fasi,
             "video": {"nome": clip, "tempi": [round(stato["inizio"] + k / FPS, 2) for k in tagli]}}
    qualita = {"fotogrammi": N, "palla": len(noto),
               "visti": {nomi[g]: round(100 * visti[g] / max(1, N - k0)) for g in nomi}}
    return gioco, qualita


def riferimento(stato, nome):
    """Il palazzetto calibrato con i tocchi diventa un riferimento per l'aggancio automatico."""
    ancora = cv2.imdecode(np.frombuffer(stato["ancora"], np.uint8), cv2.IMREAD_GRAYSCALE)
    return {"nome": nome, "lato": stato["lato"], "img": ancora, "G": np.array(stato["G"]).tolist(),
            "fascia": tuple(stato["fascia"])}
