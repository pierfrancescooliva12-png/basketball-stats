"""Scouting da template Excel, per i campionati di cui la piattaforma non ha i dati (B Interregionale).

Lo staff scarica il template, lo compila con le medie a partita della squadra avversaria (e, se le ha, dei
suoi avversari e del campionato) e dei suoi giocatori, e lo carica. Qui il file si legge, si controlla e si
analizza: indici di squadra (tiro effettivo, palle perse per possesso, rimbalzi, liberi, ritmo) confrontati
con un riferimento, punti di forza e punti deboli della squadra e di ogni giocatore, giocatori chiave.

Riferimento, in ordine: le medie del campionato scritte nel template; la media delle squadre già caricate
dal club (da 4 in su); la media della Serie B Nazionale (categoria superiore), calcolata dai dati della
piattaforma.
"""

import io
import re
import unicodedata

import pandas as pd

# ------------------------------------------------------------------ voci del template
# chiave interna, etichetta nel template
VOCI = [("partite", "Partite giocate"), ("punti", "Punti"), ("t2m", "Tiri da 2 segnati"),
        ("t2a", "Tiri da 2 tentati"), ("t3m", "Tiri da 3 segnati"), ("t3a", "Tiri da 3 tentati"),
        ("tlm", "Tiri liberi segnati"), ("tla", "Tiri liberi tentati"), ("ro", "Rimbalzi offensivi"),
        ("rd", "Rimbalzi difensivi"), ("ast", "Assist"), ("to", "Palle perse"), ("st", "Palle recuperate"),
        ("blk", "Stoppate"), ("pf", "Falli commessi")]
COLONNE_G = [("numero", "N°"), ("nome", "Giocatore"), ("ruolo", "Ruolo"), ("partite", "Partite"),
             ("minuti", "Minuti"), ("punti", "Punti"), ("t2m", "T2 segnati"), ("t2a", "T2 tentati"),
             ("t3m", "T3 segnati"), ("t3a", "T3 tentati"), ("tlm", "TL segnati"), ("tla", "TL tentati"),
             ("ro", "Rimb. off."), ("rd", "Rimb. dif."), ("ast", "Assist"), ("to", "Perse"),
             ("st", "Recuperi"), ("blk", "Stoppate"), ("pf", "Falli")]
INTESTAZIONE = [("squadra", "Squadra"), ("campionato", "Campionato"), ("girone", "Girone"), ("aggiornato", "Aggiornato al")]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _num(v):
    """Numero da una cella: accetta 12,5 e 12.5; vuoto o testo non numerico = None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("%", "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# ------------------------------------------------------------------ template
def template() -> bytes:
    """Il file Excel da compilare: istruzioni, squadra, giocatori."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ink, arancio, carta, bordo = "141413", "E8631C", "F3F1EA", "E3E0D4"
    tit = Font(name="Calibri", size=16, bold=True, color=ink)
    th = Font(name="Calibri", bold=True, color="FAF9F5")
    fill_th = PatternFill("solid", fgColor=ink)
    fill_in = PatternFill("solid", fgColor="FFFEFB")
    fill_lab = PatternFill("solid", fgColor=carta)
    linea = Side(style="thin", color=bordo)
    box = Border(left=linea, right=linea, top=linea, bottom=linea)

    ws = wb.active
    ws.title = "Istruzioni"
    righe = [
        ("ASSIST · Scouting da Excel (B Interregionale)", tit),
        ("", None),
        ("1. Nel foglio «Squadra» scrivi il nome della squadra e le sue medie a partita (colonna B).", None),
        ("2. Se le hai, scrivi anche le medie concesse agli avversari (colonna C): servono per l'analisi della difesa.", None),
        ("3. Se le hai, scrivi le medie del campionato (colonna D): diventano il riferimento del confronto.", None),
        ("4. Nel foglio «Giocatori» una riga per giocatore, con le medie a partita (minuti compresi).", None),
        ("5. Si possono usare i decimali con la virgola o con il punto. Le celle vuote non vengono considerate.", None),
        ("6. Salva il file e caricalo nella pagina Scouting avversarie di ASSIST.", None),
        ("", None),
        ("Senza le medie del campionato il riferimento è la media delle squadre già caricate dal club (da 4 in su),", None),
        ("altrimenti la media della Serie B Nazionale, la categoria superiore: in quel caso il confronto va letto con cautela.", None),
        ("Il file resta privato del club: non viene pubblicato da nessuna parte.", None),
    ]
    for i, (t, f) in enumerate(righe, start=1):
        c = ws.cell(row=i, column=1, value=t)
        if f:
            c.font = f
    ws.column_dimensions["A"].width = 120

    ws = wb.create_sheet("Squadra")
    ws["A1"] = "Scouting squadra · medie a partita"
    ws["A1"].font = tit
    for i, (_, lab) in enumerate(INTESTAZIONE, start=3):
        ws.cell(row=i, column=1, value=lab).fill = fill_lab
        c = ws.cell(row=i, column=2)
        c.fill, c.border = fill_in, box
    r0 = 3 + len(INTESTAZIONE) + 1
    for j, h in enumerate(["Voce", "Squadra", "Avversari (concessi)", "Media del campionato"], start=1):
        c = ws.cell(row=r0, column=j, value=h)
        c.font, c.fill, c.alignment = th, fill_th, Alignment(horizontal="center")
    for i, (_, lab) in enumerate(VOCI, start=r0 + 1):
        ws.cell(row=i, column=1, value=lab).fill = fill_lab
        for j in (2, 3, 4):
            c = ws.cell(row=i, column=j)
            c.fill, c.border, c.number_format = fill_in, box, "0.0"
    ws.column_dimensions["A"].width = 26
    for col in "BCD":
        ws.column_dimensions[col].width = 22

    ws = wb.create_sheet("Giocatori")
    for j, (_, h) in enumerate(COLONNE_G, start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font, c.fill, c.alignment = th, fill_th, Alignment(horizontal="center")
        ws.column_dimensions[c.column_letter].width = 24 if h == "Giocatore" else 11
    for i in range(2, 22):
        for j in range(1, len(COLONNE_G) + 1):
            c = ws.cell(row=i, column=j)
            c.fill, c.border = fill_in, box
            if j > 3:
                c.number_format = "0.0"
    ruoli = DataValidation(type="list", formula1='"Play,Guardia,Ala piccola,Ala grande,Centro"', allow_blank=True)
    ws.add_data_validation(ruoli)
    ruoli.add("C2:C21")
    ws.freeze_panes = "C2"
    ws["A1"].fill = PatternFill("solid", fgColor=arancio)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ lettura
class ErroreTemplate(ValueError):
    pass


def leggi(file) -> dict:
    """Dati dal template compilato: {intestazione, squadra, avversari, media, giocatori}. ErroreTemplate se il
    file non è il template o mancano i dati essenziali."""
    try:
        fogli = pd.read_excel(file, sheet_name=None, header=None, engine="openpyxl")
    except Exception as e:  # noqa: BLE001
        raise ErroreTemplate("il file non si apre come Excel (.xlsx)") from e
    nomi = {_norm(k): k for k in fogli}
    if "squadra" not in nomi:
        raise ErroreTemplate("manca il foglio «Squadra»: usa il template di ASSIST")
    sq = fogli[nomi["squadra"]]
    etichette = {_norm(lab): k for k, lab in VOCI}
    intest = {_norm(lab): k for k, lab in INTESTAZIONE}
    out = {"intestazione": {}, "squadra": {}, "avversari": {}, "media": {}, "giocatori": []}
    for _, r in sq.iterrows():
        lab = _norm(r.iloc[0])
        if lab in intest and len(r) > 1 and pd.notna(r.iloc[1]):
            v = r.iloc[1]
            out["intestazione"][intest[lab]] = v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else str(v).strip()
        elif lab in etichette:
            k = etichette[lab]
            for col, dove in ((1, "squadra"), (2, "avversari"), (3, "media")):
                v = _num(r.iloc[col]) if len(r) > col else None
                if v is not None:
                    out[dove][k] = v
    s = out["squadra"]
    mancano = [lab for k, lab in VOCI if k in ("punti", "t2a", "t3a", "tla", "to") and k not in s]
    if mancano:
        raise ErroreTemplate("nel foglio «Squadra» mancano: " + ", ".join(mancano))
    if "giocatori" in nomi:
        g = fogli[nomi["giocatori"]]
        if len(g):
            colonne = {_norm(lab): k for k, lab in COLONNE_G}
            testata = [colonne.get(_norm(x)) for x in g.iloc[0]]
            if "nome" not in testata:
                raise ErroreTemplate("nel foglio «Giocatori» manca la colonna «Giocatore»")
            for _, r in g.iloc[1:].iterrows():
                d = {}
                for k, v in zip(testata, r):
                    if k is None:
                        continue
                    d[k] = (str(v).strip() if pd.notna(v) else "") if k in ("nome", "ruolo", "numero") else _num(v)
                if d.get("nome"):
                    if d.get("numero", "").endswith(".0"):
                        d["numero"] = d["numero"][:-2]
                    out["giocatori"].append(d)
    return out


# ------------------------------------------------------------------ indici
def indici(t: dict, contro: dict | None = None) -> dict:
    """Indici di squadra da medie a partita (contro: le medie dell'altra squadra, per rimbalzi e possessi)."""
    g = lambda k: t.get(k) or 0.0  # noqa: E731
    fga = g("t2a") + g("t3a")
    fgm = g("t2m") + g("t3m")
    poss = fga - g("ro") + g("to") + 0.44 * g("tla")
    out = {"possessi": poss, "punti": g("punti")}
    if fga:
        out["efg"] = 100 * (fgm + 0.5 * g("t3m")) / fga if t.get("t2m") is not None else None
        out["ts"] = 100 * g("punti") / (2 * (fga + 0.44 * g("tla"))) if fga + g("tla") else None
        out["tre_quota"] = 100 * g("t3a") / fga
        out["liberi_quota"] = 100 * g("tla") / fga
    if t.get("t2a"):
        out["p2"] = 100 * g("t2m") / g("t2a") if t.get("t2m") is not None else None
    if t.get("t3a"):
        out["p3"] = 100 * g("t3m") / g("t3a") if t.get("t3m") is not None else None
    if t.get("tla"):
        out["pl"] = 100 * g("tlm") / g("tla") if t.get("tlm") is not None else None
    if poss:
        out["perse"] = 100 * g("to") / poss
        out["ortg"] = 100 * g("punti") / poss
    if fgm and t.get("ast") is not None:
        out["assist"] = 100 * g("ast") / fgm
    if contro and t.get("ro") is not None and contro.get("rd") is not None and (g("ro") + contro["rd"]):
        out["rimb_off"] = 100 * g("ro") / (g("ro") + contro["rd"])
    if contro and t.get("rd") is not None and contro.get("ro") is not None and (g("rd") + contro["ro"]):
        out["rimb_dif"] = 100 * g("rd") / (g("rd") + contro["ro"])
    out = {k: v for k, v in out.items() if v is not None}
    return out


# voce: (etichetta, meglio_alto, soglia in punti, attacco o difesa)
GIUDIZI = {
    "efg": ("Tiro effettivo (triple pesate)", True, 2.5, "attacco"),
    "p2": ("Tiro da 2", True, 3.0, "attacco"),
    "p3": ("Tiro da 3", True, 2.5, "attacco"),
    "pl": ("Tiri liberi", True, 5.0, "attacco"),
    "perse": ("Palle perse per possesso", False, 2.0, "attacco"),
    "rimb_off": ("Rimbalzi offensivi", True, 3.0, "attacco"),
    "liberi_quota": ("Tiri liberi conquistati (su 100 tiri)", True, 5.0, "attacco"),
    "assist": ("Canestri assistiti", True, 6.0, "attacco"),
    "ortg": ("Punti per 100 possessi", True, 4.0, "attacco"),
    "d_efg": ("Tiro effettivo concesso", False, 2.5, "difesa"),
    "d_perse": ("Palle perse forzate per possesso", True, 2.0, "difesa"),
    "rimb_dif": ("Rimbalzi difensivi", True, 3.0, "difesa"),
    "d_liberi_quota": ("Tiri liberi concessi (su 100 tiri)", False, 5.0, "difesa"),
    "d_ortg": ("Punti concessi per 100 possessi", False, 4.0, "difesa"),
}


def indici_completi(d: dict) -> dict:
    """Indici di attacco e, se ci sono le medie concesse, di difesa (con il prefisso d_)."""
    s, a = d.get("squadra") or {}, d.get("avversari") or {}
    out = indici(s, a if a else None)
    if a:
        ia = indici(a, s)
        for k in ("efg", "perse", "liberi_quota", "ortg", "tre_quota"):
            if k in ia:
                out["d_" + k] = ia[k]
        out["ritmo"] = (out.get("possessi", 0) + ia.get("possessi", 0)) / 2
    else:
        out["ritmo"] = out.get("possessi")
    return out


def riferimento(d: dict, altre: list[dict], lnp: dict | None) -> tuple[dict, str]:
    """Indici di riferimento e da dove vengono."""
    media = d.get("media") or {}
    if {"punti", "t2a", "t3a", "tla", "to"} <= set(media):
        return indici(media, media), "medie del campionato scritte nel template"
    if len(altre) >= 4:
        tabella = pd.DataFrame([indici_completi(x) for x in altre])
        return tabella.mean(numeric_only=True).dropna().to_dict(), f"media delle {len(altre)} squadre caricate dal club"
    return (lnp or {}), "media della Serie B Nazionale (categoria superiore: confronto da leggere con cautela)"


def giudizio_squadra(ind: dict, rif: dict) -> tuple[list[str], list[str], pd.DataFrame]:
    forza, debolezza, righe = [], [], []
    for k, (lab, alto, soglia, lato) in GIUDIZI.items():
        if k not in ind or k not in rif:
            continue
        diff = ind[k] - rif[k]
        buono = diff > soglia if alto else diff < -soglia
        cattivo = diff < -soglia if alto else diff > soglia
        testo = f"{lab}: {ind[k]:.1f} (riferimento {rif[k]:.1f})".replace(".", ",")
        if buono:
            forza.append(testo)
        elif cattivo:
            debolezza.append(testo)
        righe.append({"Lato": lato.capitalize(), "Voce": lab, "Valore": round(ind[k], 1), "Riferimento": round(rif[k], 1),
                      "Differenza": round(diff, 1), "Giudizio": "punto di forza" if buono else "punto debole" if cattivo else "nella media"})
    return forza, debolezza, pd.DataFrame(righe)


def stile(ind: dict, rif: dict) -> list[str]:
    """Come gioca: ritmo e scelta di tiro rispetto al riferimento (né forza né debolezza)."""
    out = []
    if "ritmo" in ind and rif.get("ritmo"):
        d = ind["ritmo"] - rif["ritmo"]
        if abs(d) >= 2.5:
            out.append(f"Ritmo {'alto' if d > 0 else 'basso'}: {ind['ritmo']:.0f} possessi a partita (riferimento {rif['ritmo']:.0f})")
    if "tre_quota" in ind and rif.get("tre_quota"):
        d = ind["tre_quota"] - rif["tre_quota"]
        if abs(d) >= 5:
            out.append(f"{'Tira molto' if d > 0 else 'Tira poco'} da 3: {ind['tre_quota']:.0f} tiri su 100 (riferimento {rif['tre_quota']:.0f})")
    return [x.replace(".", ",") for x in out]


# ------------------------------------------------------------------ giocatori
def giocatori(d: dict) -> pd.DataFrame:
    """Una riga per giocatore: indici, uso dei possessi, punti di forza e punti deboli in parole."""
    s = d.get("squadra") or {}
    uso_sq = (s.get("t2a", 0) + s.get("t3a", 0)) + 0.44 * s.get("tla", 0) + s.get("to", 0)
    righe = []
    for p in d.get("giocatori") or []:
        g = lambda k: p.get(k) or 0.0  # noqa: E731
        mi = g("minuti")
        fga = g("t2a") + g("t3a")
        per40 = (lambda v: 40 * v / mi) if mi else (lambda v: None)
        ts = 100 * g("punti") / (2 * (fga + 0.44 * g("tla"))) if fga + g("tla") else None
        uso = 100 * (fga + 0.44 * g("tla") + g("to")) * 40 / (mi * uso_sq) if mi and uso_sq else None
        p3 = 100 * g("t3m") / g("t3a") if g("t3a") else None
        p2 = 100 * g("t2m") / g("t2a") if g("t2a") else None
        pl = 100 * g("tlm") / g("tla") if g("tla") else None
        forza, debole = [], []
        if mi >= 8:
            if p3 is not None and g("t3a") >= 2 and p3 >= 37:
                forza.append(f"tiratore da 3 ({p3:.0f}% su {g('t3a'):.1f} a partita)")
            if p3 is not None and g("t3a") >= 2 and p3 <= 28:
                debole.append(f"tiro da 3 poco preciso ({p3:.0f}% su {g('t3a'):.1f})")
            if ts is not None and uso and uso >= 18 and ts >= 58:
                forza.append(f"molto efficiente con tanti tiri ({ts:.0f}% di tiro reale)")
            if ts is not None and uso and uso >= 18 and ts <= 46:
                debole.append(f"poco efficiente con tanti tiri ({ts:.0f}% di tiro reale)")
            if p2 is not None and g("t2a") >= 4 and p2 >= 55:
                forza.append(f"solido vicino al canestro ({p2:.0f}% da 2)")
            if p2 is not None and g("t2a") >= 4 and p2 <= 40:
                debole.append(f"fatica da 2 ({p2:.0f}%)")
            if g("tla") >= 3 and fga and g("tla") / fga >= 0.45:
                forza.append(f"conquista molti liberi ({g('tla'):.1f} a partita)")
            if pl is not None and g("tla") >= 2 and pl < 62:
                debole.append(f"tiro libero debole ({pl:.0f}%)")
            rimb = per40(g("ro") + g("rd"))
            if rimb is not None and rimb >= 11:
                forza.append(f"rimbalzista ({rimb:.1f} ogni 40 minuti)")
            if per40(g("ro")) is not None and per40(g("ro")) >= 4:
                forza.append("forte a rimbalzo offensivo")
            ast, to = per40(g("ast")), per40(g("to"))
            if ast is not None and ast >= 6 and g("ast") >= 2 * max(g("to"), 0.1):
                forza.append(f"passatore affidabile ({g('ast'):.1f} assist, {g('to'):.1f} perse)")
            if to is not None and (to >= 4.5 or (g("ast") >= 2 and g("ast") < g("to"))):
                debole.append(f"perde molti palloni ({g('to'):.1f} a partita)")
            if per40(g("st")) is not None and per40(g("st")) >= 2.5:
                forza.append("mani rapide in difesa (recuperi)")
            if per40(g("blk")) is not None and per40(g("blk")) >= 2:
                forza.append("protegge il ferro (stoppate)")
            if per40(g("pf")) is not None and per40(g("pf")) >= 5.5:
                debole.append(f"spesso carico di falli ({g('pf'):.1f} a partita)")
        righe.append({"numero": p.get("numero", ""), "nome": p.get("nome", ""), "ruolo": p.get("ruolo", ""),
                      "partite": p.get("partite"), "minuti": p.get("minuti"), "punti": p.get("punti"),
                      "ts": ts, "p3": p3, "t3a": p.get("t3a"), "pl": pl, "rimbalzi": (p.get("ro") or 0) + (p.get("rd") or 0),
                      "assist": p.get("ast"), "perse": p.get("to"), "uso": uso,
                      "forza": _virgola("; ".join(forza)), "debolezze": _virgola("; ".join(debole))})
    df = pd.DataFrame(righe)
    if df.empty:
        return df
    return df.sort_values(["punti", "minuti"], ascending=False, na_position="last").reset_index(drop=True)


def _virgola(t: str) -> str:
    return re.sub(r"(\d)\.(\d)", r"\1,\2", t)


def chiave(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Giocatori chiave: i migliori realizzatori tra chi gioca almeno 15 minuti (a parità, il più usato nei possessi)."""
    if df.empty:
        return df
    base = df[df["minuti"].fillna(0) >= 15]
    return (base if len(base) else df).sort_values(["punti", "uso"], ascending=False, na_position="last").head(n)


# ------------------------------------------------------------------ riferimento dalla B Nazionale
def riferimento_lnp(conn, stagione: str, campionati=("ita3_a", "ita3_b")) -> dict:
    """Indici medi di squadra della B Nazionale nella stagione (dai box score della piattaforma)."""
    q = ",".join("?" * len(campionati))
    b = pd.read_sql_query(f"""SELECT b.* FROM box_squadra b JOIN partite p USING (partita_id)
                              WHERE p.stagione = ? AND p.campionato_id IN ({q})""", conn, params=(stagione, *campionati))
    if b.empty:
        return {}
    m = b[["punti", "t2m", "t2a", "t3m", "t3a", "tlm", "tla", "rimb_off", "rimb_dif", "assist", "perse"]].mean()
    t = {"punti": m["punti"], "t2m": m["t2m"], "t2a": m["t2a"], "t3m": m["t3m"], "t3a": m["t3a"], "tlm": m["tlm"],
         "tla": m["tla"], "ro": m["rimb_off"], "rd": m["rimb_dif"], "ast": m["assist"], "to": m["perse"]}
    out = indici(t, t)
    out["ritmo"] = out.get("possessi")
    for k in ("efg", "perse", "liberi_quota", "ortg"):
        if k in out:
            out["d_" + k] = out[k]
    return out


# ------------------------------------------------------------------ PDF per la riunione tecnica
def pdf(nome: str, club: str, d: dict, ind: dict, rif: dict, fonte: str, gioc: pd.DataFrame, note: str = "") -> bytes:
    from datetime import date

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    from . import config
    from .report_pdf import _esc, _fonts, _styles, _table
    _fonts()
    S = _styles()
    buf = io.BytesIO()
    W = A4[0] - 24 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=14 * mm, title=f"Scouting {nome}", author=config.BRAND)
    it = d.get("intestazione") or {}
    meta = " · ".join(x for x in [it.get("campionato"), it.get("girone") and f"girone {it['girone']}",
                                  it.get("aggiornato") and f"dati al {it['aggiornato']}"] if x)
    el = [Paragraph(f"Scouting · {_esc(nome)}", S["h1"] if "h1" in S else S["h2"]),
          Paragraph(_esc(f"{club} · {meta} · report del {date.today().strftime('%d/%m/%Y')}"), S["body"]),
          Spacer(1, 6)]
    forza, debole, tab = giudizio_squadra(ind, rif)
    el.append(Paragraph("Punti di forza", S["h2"]))
    el += [Paragraph("• " + _esc(x), S["body"]) for x in forza] or [Paragraph("Nessuno marcato.", S["body"])]
    el.append(Paragraph("Punti deboli", S["h2"]))
    el += [Paragraph("• " + _esc(x), S["body"]) for x in debole] or [Paragraph("Nessuno marcato.", S["body"])]
    for x in stile(ind, rif):
        el.append(Paragraph("• " + _esc(x), S["body"]))
    if not tab.empty:
        el += [Paragraph("Indici di squadra", S["h2"]),
               Paragraph(_esc(f"Riferimento: {fonte}."), S["body"]),
               _table([["", "Voce", "Valore", "Riferimento", "Giudizio"]] +
                      [[r.Lato, r.Voce, f"{r.Valore:.1f}".replace(".", ","), f"{r.Riferimento:.1f}".replace(".", ","),
                        r.Giudizio] for r in tab.itertuples()],
                      [20 * mm, W - 20 * mm - 3 * 28 * mm, 28 * mm, 28 * mm, 28 * mm], align_left=(0, 1, 4))]
    if not gioc.empty:
        el.append(Paragraph("Giocatori", S["h2"]))
        for r in gioc.itertuples():
            testa = f"<b>{_esc(r.numero)} {_esc(r.nome)}</b>" + (f" · {_esc(r.ruolo)}" if r.ruolo else "")
            num = f"{(r.minuti or 0):.0f} minuti, {(r.punti or 0):.1f} punti".replace(".", ",")
            el.append(Paragraph(f"{testa} · {num}", S["body"]))
            if r.forza:
                el.append(Paragraph("Punti di forza: " + _esc(r.forza), S["body"]))
            if r.debolezze:
                el.append(Paragraph("Punti deboli: " + _esc(r.debolezze), S["body"]))
    if note:
        el += [Paragraph("Note dello staff", S["h2"]), Paragraph(_esc(note).replace("\n", "<br/>"), S["body"])]
    doc.build(el)
    return buf.getvalue()
