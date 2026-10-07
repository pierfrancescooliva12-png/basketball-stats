"""Mappa di tiro a zone e cronologia dei tiri, dalla cronaca LNP.

La cronaca non ha le coordinate del tiro, ma distingue la zona: area (vicino al canestro),
fuori area (media distanza), tiro da 3, schiacciata. Per ogni tiro ricaviamo quarto,
cronometro come sul tabellone (tempo che manca alla fine del quarto), punteggio e assist,
così lo staff ritrova l'azione nel video.

Sincronizzazione con il video: la cronaca conta il tempo di gioco, il video il tempo reale
(con timeout, liberi, intervalli). Se lo staff indica il minuto del video in cui inizia
ogni quarto, il minuto di ogni tiro si stima per interpolazione dentro il quarto.
"""

import numpy as np
import pandas as pd

ZONE = {"area": "Area", "media": "Media distanza", "tre": "Da 3", "schiacciata": "Schiacciate"}
DURATA_QUARTO, DURATA_SUPPL = 600, 300
SECONDI_REALI_PER_SECONDO = 2.3      # rapporto medio tempo reale / tempo di gioco (stima)


def inizio_periodo(p: int) -> int:
    return (p - 1) * DURATA_QUARTO if p <= 4 else 4 * DURATA_QUARTO + (p - 5) * DURATA_SUPPL


def durata_periodo(p: int) -> int:
    return DURATA_QUARTO if p <= 4 else DURATA_SUPPL


def nome_periodo(p: int) -> str:
    return f"{p}° quarto" if p <= 4 else f"{p - 4}° supplementare"


def cronometro(p: int, secondi: float) -> str:
    """Tempo che manca alla fine del periodo, come sul tabellone (mm:ss)."""
    dentro = min(max(secondi - inizio_periodo(p), 0), durata_periodo(p))
    resto = int(round(durata_periodo(p) - dentro))
    return f"{resto // 60:02d}:{resto % 60:02d}"


def tiri(ev: pd.DataFrame) -> pd.DataFrame:
    """Una riga per tiro dal campo, con zona, esito, momento, punteggio e assist."""
    if ev is None or ev.empty:
        return pd.DataFrame()
    ev = ev.sort_values(["partita_id", "n"])
    m = ev["tipo"].str.match(r"tiro[23]_(fatto|sbagliato)$", na=False)
    s = ev[m].copy()
    s["fatto"] = s["tipo"].str.endswith("fatto")
    s["valore"] = np.where(s["tipo"].str.startswith("tiro3"), 3, 2)
    s["zona_mappa"] = s["zona"].map({"area": "area", "fuori_area": "media", "tre": "tre",
                                    "schiacciata": "schiacciata"})
    s.loc[s["zona_mappa"].isna() & (s["valore"] == 3), "zona_mappa"] = "tre"
    # assist: evento "assist" della stessa squadra subito dopo un tiro segnato
    succ = ev[["partita_id", "n", "tipo", "giocatore_id", "squadra_id"]].copy()
    succ["n"] = succ["n"] - 1
    succ = succ[succ["tipo"] == "assist"].rename(columns={"giocatore_id": "assist_id",
                                                          "squadra_id": "sq_assist"})
    s = s.merge(succ[["partita_id", "n", "assist_id", "sq_assist"]], on=["partita_id", "n"],
                how="left")
    s.loc[(s["sq_assist"] != s["squadra_id"]) | ~s["fatto"], "assist_id"] = None
    s["tempo"] = [cronometro(int(p), x) for p, x in zip(s["periodo"], s["secondi"])]
    s["punteggio"] = s["punti_casa"].astype(int).astype(str) + "-" + \
        s["punti_ospite"].astype(int).astype(str)
    return s.drop(columns=["sq_assist"]).reset_index(drop=True)


def riepilogo(t: pd.DataFrame) -> pd.DataFrame:
    """Per zona: tentativi, segnati, percentuale, quota sul totale."""
    righe = []
    tot = len(t)
    gruppi = {**{z: [z] for z in ZONE}, "area_tot": ["area", "schiacciata"]}
    for z, zone in gruppi.items():
        nome = ZONE.get(z, "Area")
        g = t[t["zona_mappa"].isin(zone)]
        righe.append({"zona": z, "nome": nome, "tentati": len(g), "segnati": int(g["fatto"].sum()),
                      "pct": 100 * g["fatto"].mean() if len(g) else np.nan,
                      "quota": 100 * len(g) / tot if tot else np.nan})
    return pd.DataFrame(righe)


def confronto(t: pd.DataFrame, lega: pd.DataFrame, partite: int | None = None) -> pd.DataFrame:
    """Riepilogo del giocatore o della squadra con la percentuale e la quota del campionato."""
    r = riepilogo(t)
    rl = riepilogo(lega).set_index("zona")
    r["pct_lega"] = r["zona"].map(rl["pct"])
    r["quota_lega"] = r["zona"].map(rl["quota"])
    r["diff"] = r["pct"] - r["pct_lega"]
    if partite:
        r["tentati_pg"] = r["tentati"] / partite
    return r


# ------------------------------------------------------------------ disegno

def _colore(diff: float, tentati: int, minimo: int) -> str:
    """Blu sopra la media del campionato, arancio sotto; grigio con pochi tiri."""
    if tentati < minimo or pd.isna(diff):
        return "rgba(140,150,170,0.25)"
    k = min(abs(diff) / 12.0, 1.0)
    a = 0.18 + 0.55 * k
    return f"rgba(57,135,229,{a:.2f})" if diff >= 0 else f"rgba(217,89,38,{a:.2f})"


def svg_mappa(r: pd.DataFrame, minimo: int = 8, titolo: str = "") -> str:
    """Metà campo con le tre zone colorate e le etichette (percentuale e tentativi)."""
    z = r.set_index("zona")
    area, m, t3 = z.loc["area_tot"], z.loc["media"], z.loc["tre"]   # area con le schiacciate

    def etichetta(x, y, d, nome):
        pct = "–" if pd.isna(d["pct"]) else f"{d['pct']:.0f}%".replace(".", ",")
        diff = "" if pd.isna(d.get("diff")) or d["tentati"] < minimo else \
            f"{d['diff']:+.0f} vs media".replace(".", ",")
        return (f'<text x="{x}" y="{y}" text-anchor="middle" class="zp">{pct}</text>'
                f'<text x="{x}" y="{y + 9}" text-anchor="middle" class="zs">{nome} · '
                f'{int(d["segnati"])}/{int(d["tentati"])}</text>'
                + (f'<text x="{x}" y="{y + 16}" text-anchor="middle" class="zs">{diff}</text>'
                   if diff else ""))

    c_tre = _colore(t3["diff"], int(t3["tentati"]), minimo)
    c_med = _colore(m["diff"], int(m["tentati"]), minimo)
    c_area = _colore(area["diff"], int(area["tentati"]), minimo)
    righe = "#c9d1e0"
    return f"""
<svg viewBox="-4 -4 158 148" role="img" aria-label="Mappa di tiro {titolo}" style="width:100%;max-width:520px;display:block;margin:auto">
<style>.zp{{font:700 9px 'Barlow Condensed',Arial Narrow,sans-serif;fill:#f4f6fb}}
.zs{{font:500 4.6px 'Inter',Arial,sans-serif;fill:#dfe5ef}}</style>
<rect x="0" y="0" width="150" height="140" fill="{c_tre}" stroke="{righe}" stroke-width="0.6"/>
<path d="M9 0 V29.9 A67.5 67.5 0 0 0 141 29.9 V0 Z" fill="#131c2e"/>
<path d="M9 0 V29.9 A67.5 67.5 0 0 0 141 29.9 V0 Z" fill="{c_med}" stroke="{righe}" stroke-width="0.6"/>
<rect x="50.5" y="0" width="49" height="58" fill="#131c2e"/>
<rect x="50.5" y="0" width="49" height="58" fill="{c_area}" stroke="{righe}" stroke-width="0.6"/>
<path d="M57 58 A18 18 0 0 0 93 58" fill="none" stroke="{righe}" stroke-width="0.5"/>
<line x1="66" y1="12" x2="84" y2="12" stroke="{righe}" stroke-width="1"/>
<circle cx="75" cy="15.75" r="2.25" fill="none" stroke="{righe}" stroke-width="0.7"/>
<path d="M57 140 A18 18 0 0 1 93 140" fill="none" stroke="{righe}" stroke-width="0.5"/>
{etichetta(75, 32, area, "Area")}
{etichetta(33, 34, m, "Media")}
{etichetta(75, 112, t3, "Da 3")}
</svg>"""


# ------------------------------------------------------------------ video

def stima_video(periodo: int, secondi: float, inizi: dict) -> float | None:
    """Minuto del video (in secondi) di un'azione, dagli inizi dei quarti indicati dallo
    staff ({periodo: secondi nel video}). Dentro il quarto il tempo reale scorre più del
    tempo di gioco: si usa il rapporto misurato tra due inizi consecutivi quando c'è,
    altrimenti un rapporto medio."""
    p = int(periodo)
    if p not in inizi or inizi[p] is None:
        return None
    dentro = min(max(secondi - inizio_periodo(p), 0), durata_periodo(p))
    succ = inizi.get(p + 1)
    if succ is not None and succ > inizi[p]:
        pausa = 900 if p == 2 else 120            # intervallo lungo dopo il 2° quarto
        k = max(1.2, min(3.5, (succ - inizi[p] - pausa) / durata_periodo(p)))
    else:
        k = SECONDI_REALI_PER_SECONDO
    return inizi[p] + dentro * k


def hms(secondi: float | None) -> str:
    if secondi is None or pd.isna(secondi):
        return "–"
    s = int(round(secondi))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def leggi_hms(testo: str) -> int | None:
    """'1:02:30', '62:30' o '3750' -> secondi."""
    testo = (testo or "").strip()
    if not testo:
        return None
    try:
        parti = [int(x) for x in testo.replace(".", ":").split(":")]
    except ValueError:
        return None
    s = 0
    for p in parti:
        s = s * 60 + p
    return s
