"""Invio settimanale del report PDF sulla prossima avversaria agli abbonati.

Configurazione tramite variabili d'ambiente (in GitHub: Settings > Secrets and variables >
Actions):
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, MITTENTE
    ABBONATI: JSON, es. [{"email": "staff@club.it", "squadra": "Forlì", "club": "forli"}]
    ARCHIVIO_URL (facoltativo): indirizzo dell'archivio del club (lo stesso di [database] url
    nei secrets della dashboard); con "club" nell'abbonato, il PDF include i giochi
    dell'avversaria disegnati sulla lavagna.
Se SMTP_HOST o ABBONATI mancano, non viene inviato nulla.

    python -m basket.invio_email            # invia
    python -m basket.invio_email --prova    # genera i PDF senza inviare
    python -m basket.invio_email --forza    # invia anche i report già inviati

Ogni report parte una sola volta per abbonato e partita: gli invii fatti sono registrati in
config.INVII_PATH come impronte (hash di email e partita), senza indirizzi in chiaro.
"""

import argparse
import hashlib
import json
import logging
import os
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

from . import config, scouting
from .contesto import open_readonly
from .report_extra import build_post_partita
from .report_pdf import build_pdf, slug

log = logging.getLogger("basket.email")


def giochi_avversaria(sub: dict, avv_id: int) -> list[dict]:
    """Giochi dell'avversaria disegnati dallo staff, se l'archivio del club è raggiungibile."""
    url = os.environ.get("ARCHIVIO_URL", "").strip()
    if not url or not sub.get("club"):
        return []
    try:
        from .note import Archivio
        return Archivio(url).plays(sub["club"], avv_id)
    except Exception as e:                       # l'email parte comunque, senza i giochi
        log.warning("Giochi non disponibili per %s: %s", sub.get("club"), e)
        return []


def situazioni_avversaria(sub: dict, ctx, avv_id: int) -> list[list[str]]:
    """Situazioni del loro attacco segnalate dallo staff sul video, se l'archivio è raggiungibile."""
    url = os.environ.get("ARCHIVIO_URL", "").strip()
    if not url or not sub.get("club"):
        return []
    try:
        from . import situazioni as SI
        from .note import Archivio
        sit = SI.situazioni(SI.memorie_club(Archivio(url), sub["club"]), ctx.ev, avv_id)
        return SI.righe_report(sit, "noi") if not sit.empty else []
    except Exception as e:                       # l'email parte comunque, senza le situazioni
        log.warning("Situazioni non disponibili per %s: %s", sub.get("club"), e)
        return []


def abbonati() -> list[dict]:
    raw = os.environ.get("ABBONATI", "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.error("ABBONATI non è un JSON valido")
        return []
    return [d for d in data if d.get("email") and d.get("squadra")]


def impronta(email: str, g: dict) -> str:
    """Chiave di un invio: abbonato e partita, senza salvare l'indirizzo."""
    base = f"{email.strip().lower()}|{g['data']}|{g['casa_id']}|{g['ospite_id']}"
    return hashlib.sha256(base.encode()).hexdigest()[:20]


def invii_fatti() -> dict:
    try:
        return json.loads(config.INVII_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def registra_invii(chiavi: list[str]):
    fatti = invii_fatti()
    oggi = date.today().isoformat()
    fatti.update({k: oggi for k in chiavi})
    # si tengono solo gli ultimi 400 invii: bastano per riconoscere i doppioni della stagione
    tenuti = dict(sorted(fatti.items(), key=lambda kv: kv[1])[-400:])
    config.INVII_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.INVII_PATH.write_text(json.dumps(tenuti, indent=0, sort_keys=True) + "\n")


def prepare(ctx, sub: dict) -> tuple[str, str, list[tuple[bytes, str]], str] | None:
    """(oggetto, testo, allegati, impronta) per l'abbonato: report sulla prossima avversaria e,
    se la squadra ha già giocato, report post-partita sull'ultima partita."""
    teams = scouting.find_team(ctx.conn, sub["squadra"])
    if len(teams) != 1:
        log.warning("Squadra '%s' non trovata o ambigua: %s", sub["squadra"], teams)
        return None
    mia_id, mia = teams[0]
    g = ctx.next_game(mia_id)
    if not g:
        log.info("%s: nessuna prossima partita in calendario", mia)
        return None
    avv_id = g["ospite_id"] if g["casa_id"] == mia_id else g["casa_id"]
    avv = ctx.nomi_squadre.get(avv_id, str(avv_id))
    if avv_id not in set(ctx.bs["squadra_id"]):
        log.info("%s: l'avversaria %s non ha ancora partite giocate", mia, avv)
        return None
    allegati = [(build_pdf(ctx, avv_id, mia_id, giochi_avversaria(sub, avv_id),
                          situazioni=situazioni_avversaria(sub, ctx, avv_id)),
                 f"scouting_{slug(avv)}.pdf")]
    try:
        allegati.append((build_post_partita(ctx, mia_id), f"post_partita_{slug(mia)}.pdf"))
    except ValueError:
        pass
    dove = "in casa" if g["casa_id"] == mia_id else "in trasferta"
    oggetto = f"Scouting {avv} · {g['giornata']}ª giornata ({g['data']})"
    testo = (f"Buongiorno,\n\nin allegato il report di scouting su {avv}, prossima avversaria di "
             f"{mia} ({dove}, {g['giornata']}ª giornata, {g['data']} {g['ora'] or ''}).\n\n"
             + ("Trovate anche il report post-partita sull'ultima partita giocata.\n\n"
                if len(allegati) > 1 else "") +
             f"Dati aggiornati alle partite giocate finora.\n\n"
             f"{config.BRAND} · {config.BRAND_TAGLINE}")
    return oggetto, testo, allegati, impronta(sub["email"], g)


def send(msgs: list[tuple[str, str, str, list[tuple[bytes, str]]]], inviati: list | None = None):
    """Invia i messaggi; in `inviati` gli indici di quelli partiti (anche se poi uno fallisce)."""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user, pwd = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    mittente = os.environ.get("MITTENTE", user)
    with smtplib.SMTP(host, port, timeout=60) as smtp:
        smtp.starttls()
        if user:
            smtp.login(user, pwd)
        for to, oggetto, testo, allegati in msgs:
            m = EmailMessage()
            m["From"], m["To"], m["Subject"] = mittente, to, oggetto
            m["Reply-To"] = os.environ.get("RISPONDI_A", config.CONTATTO)   # le risposte arrivano a info@
            m.set_content(testo)
            for pdf, nome in allegati:
                m.add_attachment(pdf, maintype="application", subtype="pdf", filename=nome)
            smtp.send_message(m)
            if inviati is not None:
                inviati.append(len(inviati))
            log.info("Inviato a %s: %s", to, oggetto)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Invio report PDF agli abbonati")
    ap.add_argument("--prova", action="store_true", help="genera senza inviare")
    ap.add_argument("--forza", action="store_true", help="invia anche i report già inviati")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    subs = abbonati()
    if not subs:
        log.info("Nessun abbonato configurato (variabile ABBONATI): niente da inviare")
        return 0
    ctx = open_readonly()
    fatti = invii_fatti()
    msgs, chiavi = [], []
    for sub in subs:
        p = prepare(ctx, sub)
        if not p:
            continue
        *contenuto, chiave = p
        if chiave in fatti and not args.forza:
            log.info("Report già inviato il %s per questa partita: non lo rimando (%s)",
                     fatti[chiave], contenuto[0])
            continue
        msgs.append((sub["email"], *contenuto))
        chiavi.append(chiave)
    out = config.REPORTS_DIR / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    for *_, allegati in msgs:
        for pdf, nome in allegati:
            (out / nome).write_bytes(pdf)
    if args.prova or not os.environ.get("SMTP_HOST"):
        log.info("Modalità prova o SMTP non configurato: %d report generati in %s", len(msgs), out)
        return 0
    if msgs:
        inviati = []
        try:
            send(msgs, inviati)
        finally:                                 # registrati anche se un invio successivo fallisce
            if inviati:
                registra_invii(chiavi[:len(inviati)])
    else:
        log.info("Nessun report nuovo da inviare")
    return 0


if __name__ == "__main__":
    sys.exit(main())
