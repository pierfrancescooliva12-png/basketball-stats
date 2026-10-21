"""Icona dell'app sulla schermata Home (iPhone e Android): il logo del club su un quadrato
pieno nel colore della squadra, oppure il marchio ASSIST. Più il manifest per Android.

I file si scrivono in static/club/ (Streamlit li serve da /app/static/club/...): si creano
quando servono e non vanno nel repository (i loghi restano solo in cache)."""

import io
import json
from pathlib import Path

from . import brand, config

CARTELLA = config.ROOT / "static" / "club"
LATI = (180, 192, 512)           # 180: iPhone (apple-touch-icon); 192 e 512: Android
VERSIONE = "1"                   # cambiarla rigenera le icone già create


def immagine(logo: bytes | None, fondo: str, lato: int, quota: float = 0.66) -> bytes:
    """PNG quadrato pieno (niente trasparenza: iOS la riempirebbe di nero) con il logo
    centrato. quota 0,66 resta dentro la zona sicura delle icone "maskable" di Android."""
    from PIL import Image
    tela = Image.new("RGB", (lato, lato), fondo)
    if logo:
        try:
            im = Image.open(io.BytesIO(logo)).convert("RGBA")
            box = int(lato * quota)
            im.thumbnail((box, box), Image.LANCZOS)
            tela.paste(im, ((lato - im.width) // 2, (lato - im.height) // 2), im)
        except Exception:
            pass
    out = io.BytesIO()
    tela.save(out, format="PNG", optimize=True)
    return out.getvalue()


def nome_file(chiave: str) -> str:
    return brand.slug(chiave) or "assist"


def prepara(chiave: str, nome: str, logo: bytes | None, fondo: str, cartella: Path = CARTELLA,
            quota: float = 0.66) -> dict:
    """Crea (se non ci sono già) le icone e il manifest; restituisce i percorsi web."""
    import hashlib
    base = nome_file(chiave)
    # l'impronta di logo e colore nel nome: se il club cambia logo o colori l'icona si rifà
    impronta = hashlib.md5((logo or b"") + f"{fondo}{quota}{VERSIONE}".encode()).hexdigest()[:8]
    cartella.mkdir(parents=True, exist_ok=True)
    for lato in LATI:
        f = cartella / f"{base}-{lato}-{impronta}.png"
        if not f.exists():
            f.write_bytes(immagine(logo, fondo, lato, quota))
    web = "/app/static/club/"
    breve = nome if len(nome) <= 12 else config.BRAND
    manifest = {
        "name": f"{config.BRAND} · {nome}" if nome != config.BRAND else config.BRAND,
        "short_name": breve,
        "start_url": f"/?club={base}" if base != "assist" else "/",
        "scope": "/",
        "display": "standalone",
        "background_color": fondo,
        "theme_color": fondo,
        "icons": [{"src": f"{web}{base}-{lato}-{impronta}.png", "sizes": f"{lato}x{lato}", "type": "image/png",
                   "purpose": "any maskable"} for lato in (192, 512)],
    }
    (cartella / f"{base}-{impronta}.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return {"apple": f"{web}{base}-180-{impronta}.png", "manifest": f"{web}{base}-{impronta}.json",
            "titolo": breve, "colore": fondo}


def marchio() -> bytes | None:
    """Il marchio ASSIST (la A con il passaggio) per chi non ha un club."""
    f = config.LOGO_DIR / "assist-mark-512.png"
    return f.read_bytes() if f.exists() else None
