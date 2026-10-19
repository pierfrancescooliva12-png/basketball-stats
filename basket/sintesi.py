"""Visione di squadra per la prima pagina del report prepartita: chi sono, come difendere e
attaccare, ritmo e momenti, tre cose da ricordare. Tutto dai consigli già calcolati da ASSIST
(piano_partita.consigli), senza servizi esterni."""

import re

_TAG = re.compile(r"<[^>]+>")


def _gruppo(consigli: dict, prefisso: str) -> list[str]:
    for k, v in consigli.items():
        if k.startswith(prefisso):
            return [_TAG.sub("", x) for x in v]
    return []


def azione(consiglio: str) -> str:
    """Dal consiglio "Situazione (dato): cosa fare. Pericolosi: ..." tiene il cosa fare."""
    x = re.sub(r"^\w[\w ]*· ", "", consiglio).split(". Pericolosi")[0]
    m = re.search(r"\):\s*(.+)$", x)
    x = (m.group(1) if m else x).strip().rstrip(".")
    return x[:1].upper() + x[1:]


def squadra(ctx, sid: int, mia: int | None = None, report=None) -> dict:
    """{sintesi, in_difesa, in_attacco, ritmo, da_ricordare, attenzione}."""
    from . import approfondimenti as X
    from . import piano_partita as PP
    from . import scouting
    r = report or scouting.build_report(ctx.conn, sid, ctx.stagione)
    prof = ctx.profile.set_index("squadra_id")
    camp = prof.loc[sid, "campionato_id"]
    lega = ctx.profile[ctx.profile["campionato_id"] == camp]
    if mia is not None and (mia == sid or mia not in set(lega["squadra_id"])):
        mia = None
    c = PP.consigli(ctx, sid, mia, None)
    difesa, attacco = _gruppo(c, "In difesa")[:4], _gruppo(c, "In attacco")[:4]
    ritmo = (_gruppo(c, "Ritmo")[:3] + _gruppo(c, "Finali")[:2])[:4]
    frasi = X.frase_squadra(lega, sid)
    chi = f"{r.squadra} ({r.record}, {r.posizione}° posto)"
    if frasi:
        chi += " " + (", ".join(frasi[:-1]) + " e " + frasi[-1] if len(frasi) > 1 else frasi[0])
    partite = int(prof.loc[sid, "partite"])
    return {"sintesi": chi + ".", "in_difesa": difesa, "in_attacco": attacco, "ritmo": ritmo,
            "da_ricordare": [a for a in (azione(x) for x in difesa[:2] + attacco[:1]) if a],
            "attenzione": "Inizio stagione: valori su poche partite, da confermare." if partite < 6 else ""}
