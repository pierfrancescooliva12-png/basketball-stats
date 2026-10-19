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
    return {"riga": prof.loc[sid].to_dict(), "sintesi": chi + ".", "in_difesa": difesa, "in_attacco": attacco, "ritmo": ritmo,
            "da_ricordare": [a for a in (azione(x) for x in difesa[:2] + attacco[:1]) if a],
            "attenzione": "Inizio stagione: valori su poche partite, da confermare." if partite < 6 else ""}


VOCI_SEMAFORO = [("Attacco", "Rating offensivo (ORtg)", "punti ogni 100 possessi"),
                 ("Difesa", "Rating difensivo (DRtg)", "punti subiti ogni 100 possessi"),
                 ("Tiro", "eFG% in attacco", "% al tiro, triple pesate"),
                 ("Tiro da 3", "% da 3", "percentuale da 3"),
                 ("Palle perse", "Palle perse % in attacco", "a partita"),
                 ("Rimbalzi in attacco", "Rimbalzi offensivi %", "a partita"),
                 ("Rimbalzi in difesa", "Rimbalzi difensivi %", "a partita"),
                 ("Ritmo", "Ritmo (possessi/40')", "possessi per 40'")]

# Valore mostrato da allenatore (a partita) al posto della percentuale; la posizione in
# campionato resta quella della voce avanzata, che tiene conto del numero di possessi.
A_PARTITA = {"Palle perse % in attacco": lambda f: f.get("perse_pg"),
             "Rimbalzi offensivi %": lambda f: f.get("rimb_off_pg"),
             "Rimbalzi difensivi %": lambda f: f.get("rimb_dif_pg"),
             "eFG% in attacco": lambda f: 100 * (f["t2m_pg"] + f["t3m_pg"]) / (f["t2a_pg"] + f["t3a_pg"])
             if f.get("t2a_pg") else None}


def semaforo(profilo, squadra=None) -> list[dict]:
    """Otto voci chiave con la posizione in campionato e il giudizio: punto di forza (primo
    terzo), nella media, punto debole (ultimo terzo); per il ritmo veloce / lento. Con squadra
    (riga del profilo) per palle perse e rimbalzi c'è anche il numero a partita."""
    pr = profilo.set_index("Metrica")
    out = []
    for etichetta, metrica, spiega in VOCI_SEMAFORO:
        if metrica not in pr.index:
            continue
        x = pr.loc[metrica]
        try:
            pos, n = (int(v) for v in str(x["Posizione"]).split("/"))
        except ValueError:
            continue
        if metrica.startswith("Ritmo"):
            giudizio = "veloce" if pos <= n / 3 else ("lento" if pos > 2 * n / 3 else "nella media")
            tipo = "neutro"
        elif pos <= n / 3:
            giudizio, tipo = "punto di forza", "forza"
        elif pos > 2 * n / 3:
            giudizio, tipo = "punto debole", "debole"
        else:
            giudizio, tipo = "nella media", "media"
        valore = x["Valore"]
        if squadra is not None and metrica in A_PARTITA and metrica != "eFG% in attacco":
            try:
                v = A_PARTITA[metrica](squadra)
                if v is not None and v == v:
                    spiega = f"% · {v:.1f} a partita".replace(".", ",")
            except (KeyError, ZeroDivisionError, TypeError):
                pass
        out.append({"etichetta": etichetta, "valore": valore, "posizione": pos, "squadre": n,
                    "giudizio": giudizio, "tipo": tipo, "spiega": spiega})
    return out
