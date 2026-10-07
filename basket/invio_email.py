"""Invio settimanale del report PDF sulla prossima avversaria agli abbonati.

Configurazione tramite variabili d'ambiente (in GitHub: Settings > Secrets and variables >
Actions):
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, MITTENTE
    ABBONATI: JSON, es. [{"email": "staff@club.it", "squadra": "Forlì"}]
Se SMTP_HOST o ABBONATI mancano, non viene inviato nulla.

    python -m basket.invio_email            # invia
    python -m basket.invio_email --prova    # genera i PDF senza inviare
"""

import argparse
import json
import logging
import os
import smtplib
import sys
from email.message import EmailMessage

from . import config, scouting
from .contesto import open_readonly
from .report_extra import build_post_partita
from .report_pdf import build_pdf, slug

log = logging.getLogger("basket.email")


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


def prepare(ctx, sub: dict) -> tuple[str, str, list[tuple[bytes, str]]] | None:
    """(oggetto, testo, allegati) per l'abbonato: report sulla prossima avversaria e, se la
    squadra ha già giocato, report post-partita sull'ultima partita."""
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
    allegati = [(build_pdf(ctx, avv_id), f"scouting_{slug(avv)}.pdf")]
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
             f"Dati aggiornati alle partite giocate finora (fonte legapallacanestro.com).\n\n"
             f"{config.BRAND} · {config.BRAND_TAGLINE}")
    return oggetto, testo, allegati


def send(msgs: list[tuple[str, str, str, list[tuple[bytes, str]]]]):
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
            m.set_content(testo)
            for pdf, nome in allegati:
                m.add_attachment(pdf, maintype="application", subtype="pdf", filename=nome)
            smtp.send_message(m)
            log.info("Inviato a %s: %s", to, oggetto)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Invio report PDF agli abbonati")
    ap.add_argument("--prova", action="store_true", help="genera senza inviare")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    subs = abbonati()
    if not subs:
        log.info("Nessun abbonato configurato (variabile ABBONATI): niente da inviare")
        return 0
    ctx = open_readonly()
    msgs = []
    for sub in subs:
        p = prepare(ctx, sub)
        if p:
            msgs.append((sub["email"], *p))
    out = config.REPORTS_DIR / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    for *_, allegati in msgs:
        for pdf, nome in allegati:
            (out / nome).write_bytes(pdf)
    if args.prova or not os.environ.get("SMTP_HOST"):
        log.info("Modalità prova o SMTP non configurato: %d report generati in %s", len(msgs), out)
        return 0
    send(msgs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
