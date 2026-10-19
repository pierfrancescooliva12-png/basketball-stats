"""Sintesi del report di scouting scritta con l'intelligenza artificiale (Claude).

Il modello riceve solo i dati già calcolati da ASSIST (profilo, giocatori, consigli) e li
riscrive in una pagina da spogliatoio: sintesi, cose da ricordare, come attaccare e difendere,
giocatori da fermare. Ogni numero del testo viene confrontato con i dati: una frase con un
numero che non c'è viene scartata. Senza chiave (ANTHROPIC_API_KEY) o se la chiamata non
riesce, la stessa pagina si costruisce dai consigli automatici.

Le note dello staff non vengono mai inviate.
"""

import hashlib
import json
import os
import re

import pandas as pd

from . import config

MODELLO = "claude-opus-5-5"
VERSIONE = 1                      # cambia quando cambiano istruzioni o schema (invalida la cache)
CACHE_DIR = config.ROOT / ".cache" / "assistente"

ISTRUZIONI = """Sei l'assistente allenatore di uno staff di basket italiano (Serie A2 e Serie B \
Nazionale). Prepari la prima pagina del report di scouting sulla prossima avversaria: la legge \
l'allenatore in due minuti e la si appende nello spogliatoio.

Ricevi i FATTI in JSON: profilo della squadra con posizione in campionato, giocatori, consigli \
già calcolati, eventualmente la propria squadra e la probabilità di vittoria.

Regole:
- Usa solo i fatti ricevuti. Ogni numero che scrivi deve comparire nei fatti, arrotondato al più \
a un decimale (virgola decimale italiana). Non inventare numeri, nomi o tendenze.
- Ogni indicazione è concreta e azionabile ("tagliafuori su ogni tiro", "chiudere sui tiratori") \
e porta tra parentesi il dato che la giustifica, per esempio "(35,2% di rimbalzi offensivi, 3° su \
20)".
- Linguaggio da allenatore, frasi brevi, niente sigle se non necessarie (eFG%, ORtg vanno \
spiegati con parole semplici: "efficienza al tiro", "punti segnati ogni 100 possessi").
- Scegli le 3-4 cose che contano di più, non elencare tutto.
- I giocatori da fermare sono al massimo 3, scelti tra quelli nei fatti.
- Se la propria squadra è indicata, parla allo staff della propria squadra ("voi") e usa i \
confronti dei consigli (Occasione, Sfida chiave).
- Se i dati si basano su poche partite, dillo nel campo "attenzione"; altrimenti lascia vuoto."""

SCHEMA = {
    "type": "object",
    "properties": {
        "sintesi": {"type": "string", "description": "2-3 frasi, al massimo 60 parole: chi sono e come si battono"},
        "identita": {"type": "array", "items": {"type": "string"},
                     "description": "3 etichette brevi (2-3 parole) sul loro stile"},
        "da_ricordare": {"type": "array", "items": {"type": "string"},
                         "description": "le 3 cose più importanti, al massimo 14 parole ciascuna"},
        "in_difesa": {"type": "array", "items": {"type": "string"},
                      "description": "2-4 indicazioni per difendere contro il loro attacco"},
        "in_attacco": {"type": "array", "items": {"type": "string"},
                       "description": "2-4 indicazioni per attaccare la loro difesa"},
        "giocatori": {"type": "array", "items": {
            "type": "object",
            "properties": {"nome": {"type": "string"}, "chi_e": {"type": "string"},
                           "come_fermarlo": {"type": "string"}},
            "required": ["nome", "chi_e", "come_fermarlo"], "additionalProperties": False}},
        "attenzione": {"type": "string"},
    },
    "required": ["sintesi", "identita", "da_ricordare", "in_difesa", "in_attacco", "giocatori",
                 "attenzione"],
    "additionalProperties": False,
}


def _n(v, d=1):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return round(float(v), d)


def fatti(ctx, sid: int, mia: int | None = None) -> dict:
    """I dati che il modello può usare, già calcolati da ASSIST."""
    from . import approfondimenti as X
    from . import piano_partita as PP
    from . import scouting
    r = scouting.build_report(ctx.conn, sid, ctx.stagione)
    prof = ctx.profile.set_index("squadra_id")
    pf = prof.loc[sid]
    camp = pf["campionato_id"]
    lega = ctx.profile[ctx.profile["campionato_id"] == camp]
    if mia is not None and (mia == sid or mia not in set(lega["squadra_id"])):
        mia = None
    out = {"squadra": r.squadra, "campionato": r.campionato, "record": r.record,
           "posizione_in_classifica": r.posizione, "partite_giocate": int(pf["partite"]),
           "squadre_nel_campionato": int(len(lega)),
           "in_una_frase": X.frase_squadra(lega, sid),
           "profilo": [{"voce": x.Metrica, "valore": _n(x.Valore, 2 if "Liberi" in x.Metrica else 1),
                        "media_campionato": _n(x._3, 2 if "Liberi" in x.Metrica else 1),
                        "posizione": x.Posizione} for x in r.profilo.itertuples()],
           "punti_di_forza": r.punti_forza, "punti_deboli": r.punti_deboli,
           "quarti": [{"periodo": x.Periodo, "fatti": _n(x.Fatti), "subiti": _n(x.Subiti)}
                      for x in r.periodi.itertuples()]}
    pl = ctx.players[ctx.players["squadra_id"] == sid].sort_values("minuti", ascending=False).head(8)
    out["giocatori"] = [{
        "nome": p.giocatore, "partite": int(p.partite), "minuti": _n(p.minuti_pg),
        "punti": _n(p.punti_pg), "rimbalzi": _n(p.rimb_tot_pg), "assist": _n(p.assist_pg),
        "perse": _n(p.perse_pg), "triple_segnate": _n(p.t3m_pg), "triple_tentate": _n(p.t3a_pg),
        "pct_da_3": _n(p.t3_pct, 0), "pct_liberi": _n(p.tl_pct, 0),
        "efficienza_tiro_ts": _n(p.ts_pct), "quota_possessi_usg": _n(p.usg_pct),
        "on_off": _n(getattr(p, "on_off", None))} for p in pl.itertuples()]
    out["consigli"] = PP.consigli(ctx, sid, mia, None)
    if mia is not None:
        out["propria_squadra"] = ctx.nomi_squadre.get(mia, str(mia))
        ng = ctx.next_game(mia)
        if ng and {ng["casa_id"], ng["ospite_id"]} == {mia, sid}:
            out["prossima_partita"] = {"data": ng["data"], "in_casa": ng["casa_id"] == mia}
            try:
                from . import previsioni as F
                pv = F.predict(ctx.forze(camp), ng["casa_id"], ng["ospite_id"], ctx.hca(camp))
                p_mia = pv["prob_casa"] if ng["casa_id"] == mia else 1 - pv["prob_casa"]
                out["prossima_partita"]["probabilita_vittoria_propria_squadra"] = _n(100 * p_mia, 0)
            except Exception:
                pass
    return out


# ------------------------------------------------------------------ controllo dei numeri

_NUM = re.compile(r"(?<![\w])(\d+(?:[.,]\d+)?)")


def _numeri(testo: str) -> set[str]:
    return {m.replace(",", ".").rstrip("0").rstrip(".") if "." in m.replace(",", ".") else m
            for m in _NUM.findall(str(testo))}


def numeri_ammessi(f: dict) -> set[str]:
    """Tutti i numeri presenti nei fatti, anche arrotondati, più i piccoli interi (1-10)."""
    ok = {str(i) for i in range(0, 11)}
    testo = json.dumps(f, ensure_ascii=False)
    for m in _NUM.findall(testo):
        x = float(m.replace(",", "."))
        for d in (0, 1):
            v = round(x, d)
            ok.add(str(int(v)) if float(v).is_integer() else f"{v:.{d}f}".rstrip("0").rstrip("."))
        ok |= _numeri(m)
    return ok


def verifica(testo: str, ammessi: set[str]) -> bool:
    """True se ogni numero del testo compare nei fatti."""
    return _numeri(testo) <= ammessi


def _pulisci(s: dict, f: dict) -> dict:
    """Scarta le frasi con numeri che non compaiono nei fatti e i giocatori che non ci sono."""
    ok = numeri_ammessi(f)
    nomi = {g["nome"] for g in f.get("giocatori", [])}
    out = dict(s)
    for k in ("identita", "da_ricordare", "in_difesa", "in_attacco"):
        out[k] = [x for x in s.get(k, []) if isinstance(x, str) and verifica(x, ok)]
    out["giocatori"] = [g for g in s.get("giocatori", [])
                        if g.get("nome") in nomi and verifica(g.get("chi_e", "") + " " +
                                                               g.get("come_fermarlo", ""), ok)][:3]
    for k in ("sintesi", "attenzione"):
        if not verifica(s.get(k, ""), ok):
            out[k] = ""
    return out


# ------------------------------------------------------------------ senza AI

_TAG = re.compile(r"<[^>]+>")


def automatica(f: dict) -> dict:
    """La stessa pagina costruita dai consigli automatici, senza modello."""
    c = f.get("consigli", {})

    def gruppo(prefisso):
        for k, v in c.items():
            if k.startswith(prefisso):
                return [_TAG.sub("", x) for x in v]
        return []
    difesa, attacco = gruppo("In difesa")[:4], gruppo("In attacco")[:4]
    frasi = f.get("in_una_frase") or []
    sintesi = (f"{f['squadra']} ({f['record']}, {f['posizione_in_classifica']}° posto) "
               + (", ".join(frasi[:-1]) + " e " + frasi[-1] if len(frasi) > 1 else
                  (frasi[0] if frasi else "")) + ".") if f.get("record") else ""
    giocatori = sorted(f.get("giocatori", []), key=lambda g: -(g.get("punti") or 0))[:3]
    return {"sintesi": sintesi, "identita": [],
            "da_ricordare": [a for a in (_azione(x) for x in difesa[:2] + attacco[:1]) if a],
            "in_difesa": difesa, "in_attacco": attacco,
            "giocatori": [{"nome": g["nome"], "chi_e": f"{_it(g['punti'])} punti e {_it(g['minuti'])} "
                                                       f"minuti a partita",
                           "come_fermarlo": (f"{_it(g['triple_segnate'])}/{_it(g['triple_tentate'])} da 3 "
                                             f"a partita ({_it(g['pct_da_3'])}%)")
                           if (g.get("triple_tentate") or 0) >= 2 else
                           f"{_it(g['rimbalzi'])} rimbalzi e {_it(g['assist'])} assist a partita"}
                          for g in giocatori],
            "attenzione": "Inizio stagione: valori su poche partite." if f.get("partite_giocate", 99) < 6
            else "", "fonte": "automatica"}


def _azione(consiglio: str) -> str:
    """Dal consiglio "Situazione (dato): cosa fare. Pericolosi: ..." tiene il cosa fare."""
    x = re.sub(r"^\w[\w ]*· ", "", consiglio).split(". Pericolosi")[0]
    m = re.search(r"\):\s*(.+)$", x)
    x = (m.group(1) if m else x).strip().rstrip(".")
    return x[:1].upper() + x[1:]


def _it(v) -> str:
    if v is None:
        return "–"
    return (str(int(v)) if float(v).is_integer() else f"{v:.1f}").replace(".", ",")


# ------------------------------------------------------------------ con AI

def disponibile() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _chiave_cache(f: dict) -> str:
    dati = json.dumps({"m": MODELLO, "v": VERSIONE, "f": f}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(dati.encode()).hexdigest()[:24]


def scrivi(f: dict, client=None) -> dict:
    """Sintesi scritta dal modello, controllata sui fatti; se non è possibile, quella automatica."""
    if client is None and not disponibile():
        return automatica(f)
    path = CACHE_DIR / f"{_chiave_cache(f)}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        pass
    try:
        if client is None:
            import anthropic
            client = anthropic.Anthropic(timeout=120.0)
        r = client.beta.messages.create(
            model=MODELLO, max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=ISTRUZIONI,
            messages=[{"role": "user", "content": "FATTI:\n" + json.dumps(f, ensure_ascii=False, default=str)}])
        if r.stop_reason != "end_turn":
            return automatica(f)
        testo = next(b.text for b in r.content if b.type == "text")
        s = _pulisci(json.loads(testo), f)
    except Exception:
        return automatica(f)
    base = automatica(f)
    for k in ("sintesi", "in_difesa", "in_attacco", "da_ricordare", "giocatori"):
        if not s.get(k):                 # tutto scartato dal controllo: si usa quella automatica
            s[k] = base[k]
    s["fonte"] = "ai"
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(s, ensure_ascii=False))
    except OSError:
        pass
    return s
