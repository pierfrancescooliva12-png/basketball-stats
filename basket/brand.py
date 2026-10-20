"""Brand del club: logo e colori della squadra sulla piattaforma (fascia in alto, testate,
pulsanti, sfondo) e sulla schermata di accesso del club.

Il logo è quello del sito della Lega (static.legapallacanestro.com/.../team_logo/<id>.png,
lo stesso id squadra del database): si scarica quando serve e resta nella cache locale,
mai nel repository. I colori si ricavano dal logo; si possono correggere nei Secrets:

    [brand.9583]                  # id della squadra
    primario = "#0b2a5b"          # fascia in alto e testate (scuro: il testo è bianco)
    secondario = "#4fb3e8"        # accento: striscia, pulsanti, titoletti
    logo_url = "https://..."      # facoltativo: un altro indirizzo per il logo
"""

import base64
import colorsys
import io
import re
import unicodedata
from dataclasses import dataclass

from . import config
from .scheda_giocatori import _scarica

# "loghi2": i vecchi file "nessun logo" (si cercavano solo i PNG) non valgono più
CACHE_LOGHI = config.ROOT / ".cache" / "loghi2"
# il logo è quasi sempre PNG, ma alcune squadre l'hanno caricato in un altro formato
CANDIDATI = tuple(f"https://static.legapallacanestro.com/sites/default/files/{cartella}team_logo/{{id}}.{ext}"
                  for ext in ("png", "jpg", "jpeg", "webp", "gif")
                  for cartella in ("", "styles/255_x/public/"))
NAVY, ARANCIO, SFONDO = "#0b1220", "#ff7a1a", "#f4f6fa"


def slug(nome: str) -> str:
    """"Luiss Roma" -> "luiss-roma" (per il link di accesso del club)."""
    ascii_ = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


# ------------------------------------------------------------------ logo

_FALLITI: dict[int, float] = {}


def logo(squadra_id: int, url: str | None = None, timeout: float = 8.0) -> bytes | None:
    """Logo della squadra (in cache locale); None se non c'è o il sito non risponde. Se il
    sito non risponde si riprova dopo qualche minuto; se il logo non c'è, dopo qualche giorno."""
    import time
    from .scheda_giocatori import RIPROVA_RETE, vuota_scaduta
    import hashlib
    # con un indirizzo alternativo (dall'Amministrazione) il file in cache è un altro
    extra = "_" + hashlib.md5(url.encode()).hexdigest()[:8] if url else ""
    path = CACHE_LOGHI / f"{int(squadra_id)}{extra}.png"
    if path.exists() and not vuota_scaduta(path):
        return path.read_bytes() or None
    if time.time() - _FALLITI.get(int(squadra_id), 0) < RIPROVA_RETE:
        return None
    dati, rete_ok = b"", False
    for u in ([url] if url else []) + [c.format(id=int(squadra_id)) for c in CANDIDATI]:
        try:
            dati = _scarica(u, timeout)
            rete_ok = True
        except Exception:
            continue
        if dati:
            break
    if not rete_ok:
        _FALLITI[int(squadra_id)] = time.time()     # errore di rete: si riprova tra qualche minuto
        return None
    _FALLITI.pop(int(squadra_id), None)
    try:
        CACHE_LOGHI.mkdir(parents=True, exist_ok=True)
        path.write_bytes(dati)            # anche vuoto: "nessun logo", non si richiede ancora
    except OSError:
        pass
    return dati or None


def miniatura(dati: bytes | None, lato: int = 44) -> str | None:
    """Logo rimpicciolito (PNG con trasparenza) per le tabelle: pochi kB invece del file intero."""
    if not dati:
        return None
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(dati)).convert("RGBA")
        im.thumbnail((lato, lato))
        out = io.BytesIO()
        im.save(out, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode()
    except Exception:
        return None


def data_uri(dati: bytes | None) -> str | None:
    if not dati:
        return None
    tipo = ("image/png" if dati[:8] == b"\x89PNG\r\n\x1a\n" else "image/gif" if dati[:4] == b"GIF8"
            else "image/webp" if dati[:4] == b"RIFF" else "image/jpeg")
    return f"data:{tipo};base64,{base64.b64encode(dati).decode()}"


# ------------------------------------------------------------------ colori

def _hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(round(c)))) for c in rgb[:3]))


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminanza(h: str) -> float:
    """Luminanza relativa WCAG (0 nero, 1 bianco)."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrasto(a: str, b: str) -> float:
    la, lb = sorted((luminanza(a), luminanza(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _scurisci(h: str, verso: str = "#ffffff", minimo: float = 4.5) -> str:
    """Scurisce il colore finché il testo nel colore verso si legge (contrasto >= minimo)."""
    r, g, b = _rgb(h)
    for _ in range(40):
        if contrasto(_hex((r, g, b)), verso) >= minimo:
            break
        r, g, b = r * 0.9, g * 0.9, b * 0.9
    return _hex((r, g, b))


def mescola(a: str, b: str, quota_a: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(quota_a * x + (1 - quota_a) * y for x, y in zip(ra, rb)))


def colori_da_logo(dati: bytes | None) -> tuple[str, str] | None:
    """(primario, secondario) dai colori più presenti nel logo, esclusi bianco, trasparenze e
    grigi; None se il logo non ha colori utilizzabili."""
    if not dati:
        return None
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(dati)).convert("RGBA")
    except Exception:
        return None
    im.thumbnail((96, 96))
    raw = im.tobytes()                    # RGBA: vale per tutte le versioni di Pillow
    pixel = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 4) if raw[i + 3] >= 160]
    utili = []
    for r, g, b in pixel:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l > 0.92 or (s < 0.18 and l > 0.25):     # bianco e grigi chiari: sfondo del logo
            continue
        utili.append((r, g, b))
    if len(utili) < 30:
        return None
    tav = Image.new("RGB", (len(utili), 1))
    tav.putdata(utili)
    q = tav.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    conti = sorted(q.getcolors(), reverse=True)
    colori = [_hex(pal[3 * i:3 * i + 3]) for _, i in conti]
    primario = colori[0]
    secondario = next((c for c in colori[1:]
                       if sum(abs(x - y) for x, y in zip(_rgb(c), _rgb(primario))) > 120), None)
    if secondario is None:          # logo di un solo colore: accento più chiaro dello stesso tono
        secondario = mescola(primario, "#ffffff", 0.55)
    # il più scuro fa da fondo (testo bianco sopra), l'altro da accento
    if luminanza(secondario) < luminanza(primario):
        primario, secondario = secondario, primario
    return primario, secondario


# ------------------------------------------------------------------ tema

@dataclass
class Tema:
    squadra_id: int
    nome: str
    fondo: str            # fascia in alto e testate (testo bianco)
    fondo_2: str          # parte destra della testata
    accento: str          # striscia, pulsanti, titoletti
    testo_accento: str    # testo sui pulsanti (bianco o scuro, quello che si legge)
    sfondo: str           # sfondo della pagina, appena colorato
    logo: str | None      # data URI del logo
    da_logo: bool         # colori ricavati dal logo (non confermati)


def tema(squadra_id: int, nome: str, sovrascrivi: dict | None = None, scarica: bool = True) -> Tema:
    sv = dict(sovrascrivi or {})
    dati = logo(squadra_id, sv.get("logo_url")) if scarica else None
    auto = colori_da_logo(dati)
    primario = sv.get("primario") or (auto[0] if auto else NAVY)
    secondario = sv.get("secondario") or (auto[1] if auto else ARANCIO)
    fondo = _scurisci(primario, "#ffffff", 7.0)
    # accento: un colore vero (un grigio non fa da accento: resta l'arancio) che stacchi dal fondo
    accento = secondario
    if colorsys.rgb_to_hls(*(c / 255 for c in _rgb(accento)))[2] < 0.2:
        accento = ARANCIO
    if contrasto(accento, fondo) < 2.2:
        accento = mescola(accento, "#ffffff", 0.6)
    testo_accento = "#ffffff" if contrasto(accento, "#ffffff") >= 2.5 else fondo
    return Tema(squadra_id=int(squadra_id), nome=nome, fondo=fondo,
                fondo_2=mescola(fondo, "#ffffff", 0.82), accento=accento,
                testo_accento=testo_accento,
                sfondo=mescola(primario, SFONDO, 0.07), logo=data_uri(dati),
                da_logo=bool(auto) and not (sv.get("primario") or sv.get("secondario")))


def css(t: Tema) -> str:
    """Foglio di stile che ridipinge la piattaforma con i colori del club."""
    a = _rgb(t.accento)
    logo_css = ""
    if t.logo:
        logo_css = (f'header[data-testid="stHeader"]::after {{content: ""; position: absolute; right: 150px; '
                    f'top: 50%; transform: translateY(-50%); height: 40px; width: 150px; '
                    f'background: url("{t.logo}") right center / contain no-repeat; pointer-events: none;}}')
    return f"""
<style>
:root {{--navy: {t.fondo}; --navy-2: {t.fondo_2}; --accent: {t.accento};
  --accent-soft: rgba({a[0]},{a[1]},{a[2]},.12); --bg: {t.sfondo};}}
[data-testid="stAppViewContainer"] {{background:
  linear-gradient(180deg, {mescola(t.fondo, t.sfondo, 0.10)} 0, {t.sfondo} 340px) !important;}}
header[data-testid="stHeader"] {{border-bottom-color: {t.accento} !important;}}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  background: {t.accento} !important; border-color: {t.accento} !important;
  box-shadow: 0 6px 18px rgba({a[0]},{a[1]},{a[2]},.28) !important; color: {t.testo_accento} !important;}}
[data-testid="stBaseButton-primary"] *, [data-testid="stBaseButton-primaryFormSubmit"] * {{
  color: {t.testo_accento} !important;}}
[data-testid="stBaseButton-primaryFormSubmit"] {{color: {t.testo_accento} !important;}}
.club-logo {{height: 84px; width: auto; max-width: 180px; object-fit: contain;
  filter: drop-shadow(0 4px 14px rgba(0,0,0,.35));}}
{logo_css}
</style>"""
