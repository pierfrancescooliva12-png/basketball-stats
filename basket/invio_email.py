"""Invio dei report per email: post-partita appena arrivano i dati della partita, scouting della
prossima avversaria appena lei (e la propria squadra) hanno giocato l'ultima partita.

Destinatari: gli indirizzi che gli utenti lasciano nella piattaforma (archivio, tabella
email_report) e, come prima, quelli della variabile ABBONATI.

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
    python -m basket.invio_email --controlla  # ci sono partite finite di cui mancano i dati?

Ogni report parte una sola volta per destinatario e partita: gli invii fatti sono registrati come
impronte (hash di indirizzo, tipo di report e partita), senza indirizzi in chiaro, nell'archivio
(con ARCHIVIO_URL) o in config.INVII_PATH.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import smtplib
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
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


def impronta(email: str, tipo: str, partita_id: str) -> str:
    """Chiave di un invio: indirizzo, tipo di report e partita, senza salvare l'indirizzo."""
    base = f"{email.strip().lower()}|{tipo}|{partita_id}"
    return hashlib.sha256(base.encode()).hexdigest()[:20]


def valida_email(testo: str) -> str | None:
    """L'indirizzo ripulito, o None se non ha la forma di un'email."""
    e = (testo or "").strip().lower()
    return e if re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", e) and len(e) <= 120 else None


class Registro:
    """Report già inviati. Con l'archivio (ARCHIVIO_URL) stanno nel database, così il controllo
    orario non deve salvare nulla nel repository; senza, nel file data/invii_report.json."""

    def __init__(self, archivio=None):
        self.archivio = archivio
        self.fatti = set(archivio.invii_fatti()) if archivio is not None else set(invii_fatti())

    def __contains__(self, chiave: str) -> bool:
        return chiave in self.fatti

    def segna(self, chiavi: list[str]):
        if not chiavi:
            return
        self.fatti.update(chiavi)
        if self.archivio is not None:
            self.archivio.segna_invii(chiavi)
        else:
            registra_invii(chiavi)


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


def _archivio():
    url = os.environ.get("ARCHIVIO_URL", "").strip()
    if not url:
        return None
    try:
        from .note import Archivio, normalizza_url
        return Archivio(normalizza_url(url))
    except Exception as e:                       # senza archivio restano gli abbonati dei segreti
        log.warning("Archivio non raggiungibile: %s", e)
        return None


def destinatari(archivio=None) -> list[dict]:
    """Chi riceve i report: gli indirizzi lasciati dagli utenti nella piattaforma (con la scelta
    di quali report) e quelli della variabile ABBONATI (entrambi i report)."""
    out = [{**d, "post_partita": True, "scouting": True} for d in abbonati()]
    if archivio is not None:
        try:
            for r in archivio.iscritti_email():
                if r.get("club") and valida_email(r["email"]):
                    out.append({"email": r["email"], "squadra": r["club"], "club": r["club"],
                                "post_partita": r["post_partita"], "scouting": r["scouting"]})
        except Exception as e:
            log.warning("Iscritti non letti dall'archivio: %s", e)
    visti, unici = set(), []
    for d in out:                                # lo stesso indirizzo per la stessa squadra: una volta
        k = (d["email"].strip().lower(), str(d["squadra"]).strip().lower())
        if k not in visti:
            visti.add(k)
            unici.append(d)
    return unici


# ------------------------------------------------------------------ quando un report è pronto

ROMA = ZoneInfo("Europe/Rome")
RECENTE_GIORNI = 3            # una partita non in archivio dopo 3 giorni si considera rinviata


def _calendario(ctx, sid: int) -> list[dict]:
    """Le partite in calendario della squadra, in ordine, con l'ora d'inizio (ora italiana)."""
    rows = ctx.conn.execute(
        "SELECT partita_id, giornata, data, ora, squadra_casa_id, squadra_ospite_id FROM calendario "
        "WHERE stagione = ? AND (squadra_casa_id = ? OR squadra_ospite_id = ?) ORDER BY data, ora",
        (ctx.stagione, sid, sid)).fetchall()
    out = []
    for pid, giornata, data, ora, casa, osp in rows:
        try:
            inizio = datetime.fromisoformat(f"{data} {ora or '23:59'}")
        except ValueError:
            continue
        out.append({"partita_id": pid, "giornata": giornata, "data": data, "ora": ora, "casa_id": casa,
                    "ospite_id": osp, "inizio": inizio})
    return out


def stato_squadra(ctx, sid: int, adesso: datetime | None = None) -> dict:
    """{in_attesa: partita cominciata di cui non ci sono ancora i dati, prossima: prima partita
    non ancora cominciata}. adesso è l'ora italiana (senza fuso)."""
    adesso = adesso or datetime.now(ROMA).replace(tzinfo=None)
    giocate = set(ctx.bs["partita_id"])
    in_attesa = prossima = None
    for g in _calendario(ctx, sid):
        if g["partita_id"] in giocate:
            continue
        if g["inizio"] <= adesso:
            if adesso - g["inizio"] <= timedelta(days=RECENTE_GIORNI):
                in_attesa = g
        elif prossima is None:
            prossima = g
    return {"in_attesa": in_attesa, "prossima": prossima}


def serve_aggiornare(ctx, subs: list[dict], adesso: datetime | None = None) -> bool:
    """C'è una partita delle squadre seguite (o della loro prossima avversaria) cominciata da
    almeno un'ora e tre quarti di cui mancano ancora i dati: vale la pena scaricarli."""
    adesso = adesso or datetime.now(ROMA).replace(tzinfo=None)
    squadre = set()
    for sub in subs:
        teams = scouting.find_team(ctx.conn, sub["squadra"])
        if len(teams) != 1:
            continue
        mia = teams[0][0]
        squadre.add(mia)
        pr = stato_squadra(ctx, mia, adesso)["prossima"]
        if pr:
            squadre.add(pr["ospite_id"] if pr["casa_id"] == mia else pr["casa_id"])
    for sid in squadre:
        g = stato_squadra(ctx, sid, adesso)["in_attesa"]
        if g and adesso - g["inizio"] >= timedelta(minutes=105):
            return True
    return False


def prepare(ctx, sub: dict, adesso: datetime | None = None) -> list[tuple[str, str, list, str]]:
    """I report pronti per il destinatario: [(oggetto, testo, allegati, impronta)].

    - Post-partita: appena i dati dell'ultima partita della squadra sono in archivio.
    - Scouting della prossima avversaria: quando hanno giocato (e ci sono i dati) sia la squadra
      sia l'avversaria, cioè la prossima partita di tutte e due è proprio quella tra loro."""
    teams = scouting.find_team(ctx.conn, sub["squadra"])
    if len(teams) != 1:
        log.warning("Squadra '%s' non trovata o ambigua: %s", sub["squadra"], teams)
        return []
    mia_id, mia = teams[0]
    adesso = adesso or datetime.now(ROMA).replace(tzinfo=None)
    firma = f"{config.BRAND} · {config.BRAND_TAGLINE}"
    cambia = ("Ricevi questa email perché hai lasciato il tuo indirizzo in ASSIST: puoi cambiarlo o "
              "toglierlo dal pulsante «Email» in alto nella piattaforma.")
    out = []
    mie = ctx.bs[ctx.bs["squadra_id"] == mia_id].sort_values(["data", "partita_id"])
    if sub.get("post_partita", True) and not mie.empty:
        u = mie.iloc[-1]
        try:
            recente = adesso - datetime.fromisoformat(str(u["data"])[:10]) <= timedelta(days=RECENTE_GIORNI + 1)
        except ValueError:
            recente = False
        if recente:
            try:
                pdf = build_post_partita(ctx, mia_id, u["partita_id"])
                esito = "vittoria" if bool(u["vinta"]) else "sconfitta"
                out.append((f"Post-partita {mia} · {u['avversario']} ({int(u['punti'])}-{int(u['punti_subiti'])})",
                            f"Buongiorno,\n\nin allegato il report post-partita di {mia} contro {u['avversario']} "
                            f"({esito} {int(u['punti'])}-{int(u['punti_subiti'])}, {int(u['giornata'])}ª giornata).\n\n"
                            f"{cambia}\n\n{firma}",
                            [(pdf, f"post_partita_{slug(mia)}.pdf")], impronta(sub["email"], "post", u["partita_id"])))
            except ValueError:
                pass
    if sub.get("scouting", True):
        st_mia = stato_squadra(ctx, mia_id, adesso)
        g = st_mia["prossima"]
        if g and not st_mia["in_attesa"]:
            avv_id = g["ospite_id"] if g["casa_id"] == mia_id else g["casa_id"]
            st_avv = stato_squadra(ctx, avv_id, adesso)
            avv = ctx.nomi_squadre.get(avv_id, str(avv_id))
            pronta = (not st_avv["in_attesa"] and st_avv["prossima"]
                      and st_avv["prossima"]["partita_id"] == g["partita_id"]
                      and avv_id in set(ctx.bs["squadra_id"]))
            if pronta:
                pdf = build_pdf(ctx, avv_id, mia_id, giochi_avversaria(sub, avv_id),
                                situazioni=situazioni_avversaria(sub, ctx, avv_id))
                dove = "in casa" if g["casa_id"] == mia_id else "in trasferta"
                out.append((f"Scouting {avv} · {g['giornata']}ª giornata ({g['data']})",
                            f"Buongiorno,\n\nin allegato il report di scouting su {avv}, prossima avversaria di "
                            f"{mia} ({dove}, {g['giornata']}ª giornata, {g['data']} {g['ora'] or ''}). "
                            f"È aggiornato all'ultima partita giocata da {avv}.\n\n{cambia}\n\n{firma}",
                            [(pdf, f"scouting_{slug(avv)}.pdf")], impronta(sub["email"], "scouting", g["partita_id"])))
            else:
                log.info("%s: scouting su %s non ancora pronto (si aspetta l'ultima partita)", mia, avv)
    return out


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
    ap = argparse.ArgumentParser(description="Invio dei report post-partita e di scouting")
    ap.add_argument("--prova", action="store_true", help="genera senza inviare")
    ap.add_argument("--forza", action="store_true", help="invia anche i report già inviati")
    ap.add_argument("--controlla", action="store_true",
                    help="dice solo se ci sono partite finite di cui scaricare i dati (per il controllo orario)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    archivio = _archivio()
    subs = destinatari(archivio)
    if args.controlla:
        serve = bool(subs) and serve_aggiornare(open_readonly(), subs)
        log.info("Destinatari: %d · dati da scaricare: %s", len(subs), "sì" if serve else "no")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"aggiorna={'si' if serve else 'no'}\n")
        return 0
    if not subs:
        log.info("Nessun destinatario (né iscritti nella piattaforma né variabile ABBONATI): niente da inviare")
        return 0
    ctx = open_readonly()
    registro = Registro(archivio)
    msgs, chiavi = [], []
    for sub in subs:
        try:
            pronti = prepare(ctx, sub)
        except Exception as e:                   # un destinatario che dà errore non ferma gli altri
            log.warning("Report non preparato per la squadra '%s': %s", sub.get("squadra"), e)
            continue
        for *contenuto, chiave in pronti:
            if chiave in registro and not args.forza:
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
            registro.segna(chiavi[:len(inviati)])
    else:
        log.info("Nessun report nuovo da inviare")
    return 0


if __name__ == "__main__":
    sys.exit(main())
