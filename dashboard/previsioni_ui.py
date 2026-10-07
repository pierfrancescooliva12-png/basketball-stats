"""Area Previsioni: perché di una previsione, scenari "e se", proiezione della classifica,
affidabilità delle previsioni (validazione retrospettiva e registro)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import config
from basket import previsioni as F
from basket import validazione as V
from basket.glossario import G

from .stato import App
from .ui import (ARANCIO, BLU, GRIGIO, TESTO, badge, esc, kpis, note_html, num, plot, section,
                 short, show)

AVVISO = ("Le previsioni sono probabilità, non certezze: il basket ha un'alta componente "
          "casuale e anche una favorita al 70% perde circa 3 partite su 10. Strumento di "
          "analisi per lo staff tecnico, non destinato alle scommesse.")


def avviso():
    st.markdown(f'<div class="note">{badge("Probabilità, non certezze", "warn")} '
                f'{esc(AVVISO)}</div>', unsafe_allow_html=True)


def forbice(p: float) -> str:
    """Intervallo indicativo della probabilità, dall'errore di calibrazione osservato."""
    lo, hi = max(0.01, p - 0.07), min(0.99, p + 0.07)
    return f"tra {num(100 * lo, 0)}% e {num(100 * hi, 0)}%"


def forbice_breve(p: float) -> str:
    lo, hi = max(0.01, p - 0.07), min(0.99, p + 0.07)
    return f"{num(100 * lo, 0)}–{num(100 * hi, 0)}%"


# ------------------------------------------------------------------ perché e scenari

def perche(a: App, forze, casa: int, ospite: int, hca: float, nomi: dict):
    sp = F.spiega(forze, casa, ospite, hca)
    section("Perché questa previsione", "quanto pesa ogni fattore sulla probabilità di "
            f"vittoria di {short(nomi[casa])}", key="spiegazione")
    _grafico_fattori(sp, nomi[casa])


def _grafico_fattori(sp: pd.DataFrame, nome_casa: str):
    sp = sp.iloc[::-1]
    fig = go.Figure(go.Bar(
        y=sp["fattore"], x=sp["probabilita"], orientation="h",
        marker=dict(color=[BLU if v >= 0 else ARANCIO for v in sp["probabilita"]],
                    cornerradius=4),
        text=[f"{v:+.0f}%".replace(".", ",") for v in sp["probabilita"]],
        textposition="outside", textfont=dict(color=TESTO),
        customdata=sp["punti"],
        hovertemplate="%{y}: %{x:+.1f}% di probabilità<br>%{customdata:+.1f} punti di margine"
                      "<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=GRIGIO, width=1))
    lim = max(10.0, float(sp["probabilita"].abs().max()) * 1.3)
    fig.update_xaxes(range=[-lim, lim], ticksuffix="%", title=f"a favore di {short(nome_casa)} →")
    fig.update_yaxes(showgrid=False)
    plot(fig, 70 + 46 * len(sp), bargap=0.35)


def scenari(a: App, forze, casa: int, ospite: int, hca: float, nomi: dict):
    section("Scenari: e se…", "cambia le condizioni e guarda come si sposta la previsione",
            key="scenari")
    pl = a.players
    imp = F.impatto_giocatori(pl)

    def opzioni(sid):
        p = imp[imp["squadra_id"] == sid].sort_values("minuti", ascending=False)
        p = p[p["minuti_pg"] >= 8]
        return {r.giocatore_id: f"{r.giocatore} ({num(r.minuti_pg)}')" for r in p.itertuples()}

    oc, oo = opzioni(casa), opzioni(ospite)
    c1, c2 = st.columns(2)
    ass_c = c1.multiselect(f"Assenti · {short(nomi[casa])}", list(oc), format_func=oc.get,
                           key=f"sc_ac_{casa}_{ospite}", placeholder="Scegli i giocatori…")
    ass_o = c2.multiselect(f"Assenti · {short(nomi[ospite])}", list(oo), format_func=oo.get,
                           key=f"sc_ao_{casa}_{ospite}", placeholder="Scegli i giocatori…")
    corr_c = c1.slider(f"Forma di {short(nomi[casa])} secondo lo staff", -6, 6, 0,
                       key=f"sc_cc_{casa}_{ospite}",
                       help="Correzione in punti per 100 possessi: per esempio +3 se lo staff "
                            "ritiene la squadra in crescita rispetto ai numeri.")
    corr_o = c2.slider(f"Forma di {short(nomi[ospite])} secondo lo staff", -6, 6, 0,
                       key=f"sc_co_{casa}_{ospite}")
    neutro = st.toggle("Campo neutro", key=f"sc_n_{casa}_{ospite}")
    r = F.scenario(forze, pl, casa, ospite, hca, ass_c, ass_o, neutro, corr_c, corr_o)
    b, s = r["base"], r["scenario"]
    d = 100 * (s["prob_casa"] - b["prob_casa"])
    kpis([("Prima", f"{num(100 * b['prob_casa'], 0)}%",
           f"{short(nomi[casa])} · {b['punti_casa']:.0f}-{b['punti_ospite']:.0f}"),
          ("Nello scenario", f"{num(100 * s['prob_casa'], 0)}%",
           f"{short(nomi[casa])} · {s['punti_casa']:.0f}-{s['punti_ospite']:.0f}"),
          ("Variazione", f"{num(d, 0, signed=True)}%", "punti di probabilità"),
          ("Forbice", forbice_breve(s["prob_casa"]), "intervallo indicativo")])
    if ass_c or ass_o:
        dett = imp[imp["giocatore_id"].isin(list(ass_c) + list(ass_o))]
        show(dett[["giocatore", "squadra", "minuti_pg", "impatto", "fonte_impatto"]].rename(
            columns={"giocatore": "Giocatore", "squadra": "Squadra", "minuti_pg": "Minuti",
                     "impatto": "Impatto (per 100 possessi)", "fonte_impatto": "Stima da"}),
            voci=[G["impatto"]])
    if ass_c or ass_o or neutro or corr_c or corr_o:
        _grafico_fattori(r["spiegazione"], nomi[casa])


# ------------------------------------------------------------------ proiezione classifica

@st.cache_data(show_spinner="Simulo il resto della stagione…")
def _simulazione(_ctx, mtime: float, stagione: str, camp: str) -> pd.DataFrame:
    return _ctx.simulation(camp, n=5000)


def render_proiezione(a: App):
    avviso()
    sim = _simulazione(a.ctx, a.mtime, a.stagione, a.camp)
    if sim.empty:
        st.info("Nessuna partita giocata nel campionato selezionato.")
        return
    rimaste = int(sim["partite_rimanenti"].sum() / 2)
    if rimaste == 0:
        note_html("Stagione conclusa: la proiezione coincide con la classifica finale.")
    else:
        note_html(f"5.000 simulazioni delle {rimaste} partite ancora da giocare, con la forza "
                  "stimata di ogni squadra e la sua incertezza.", "simulazione")
    zone = list(config.ZONE_CLASSIFICA.get(a.camp, {}))
    show(sim[["squadra", "vinte_ora", "vinte_finali", "posizione_media"] + zone].rename(
        columns={"squadra": "Squadra", "vinte_ora": "Vinte ora", "vinte_finali": "Vinte attese",
                 "posizione_media": "Posizione media"}),
        progress={z: (0, 100) for z in zone}, voci=[G["simulazione"]])
    fz = a.ctx.forze(a.camp).sort_values("forza", ascending=False)
    section("Forza stimata delle squadre", "punti per 100 possessi rispetto a una squadra "
            "media, con la forbice di incertezza", key="forza")
    fig = go.Figure(go.Scatter(
        x=fz["forza"], y=[short(n) for n in fz["squadra"]], mode="markers",
        marker=dict(size=11, color=BLU),
        error_x=dict(type="data", array=1.64 * fz["incertezza"], color=GRIGIO, thickness=1.5),
        customdata=fz[["squadra", "incertezza"]].values,
        hovertemplate="%{customdata[0]}: %{x:+.1f} (± %{customdata[1]:.1f})<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=GRIGIO, dash="dot", width=1))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    plot(fig, 40 + 26 * len(fz))


# ------------------------------------------------------------------ affidabilità

@st.cache_data(show_spinner=False)
def _validazione(mtime: float) -> pd.DataFrame:
    return V.carica()


def render_affidabilita(a: App):
    st.markdown('<div class="pagina-d">Validazione su 3 stagioni e registro delle previsioni'
                '</div>', unsafe_allow_html=True)
    bt = _validazione(a.mtime)
    if bt.empty:
        st.info("La validazione viene calcolata con l'aggiornamento settimanale dei dati.")
        return
    m = V.metriche(bt)
    section("In sintesi", "previsioni ricalcolate partita per partita con i soli dati "
            "disponibili prima di ogni partita", key="validazione")
    kpis([("Favorita che vince", f"{num(m['accuratezza'], 1)}%",
           f"su {m['partite']} partite"),
          ("Riferimento: sempre la squadra di casa", f"{num(m['rif_sempre_casa'], 1)}%",
           "quanto vince chi gioca in casa"),
          ("Riferimento: record migliore", f"{num(m['rif_record_migliore'], 1)}%",
           "vince chi ha vinto di più finora"),
          ("Errore medio sul margine", f"{num(m['errore_margine'], 1)} punti",
           "scarto tra margine previsto e reale"),
          ("Brier score", num(m["brier"], 3),
           f"più basso è meglio · riferimento {num(m['brier_riferimento'], 3)}")])

    section("Calibrazione", "quando il modello dà una certa probabilità, quante volte la "
            "favorita vince davvero", key="calibrazione")
    cal = V.calibrazione(bt)
    c1, c2 = st.columns([3, 2])
    with c1:
        fig = go.Figure()
        fig.add_scatter(x=[50, 100], y=[50, 100], mode="lines", name="Calibrazione perfetta",
                        line=dict(color=GRIGIO, dash="dot", width=1), hoverinfo="skip")
        fig.add_scatter(x=cal["prevista"], y=cal["reale"], mode="markers+lines",
                        name="ASSIST", line=dict(color=BLU, width=2),
                        marker=dict(size=[8 + 14 * p / cal["partite"].max()
                                          for p in cal["partite"]], color=BLU),
                        customdata=cal[["fascia", "partite"]].values,
                        hovertemplate="Fascia %{customdata[0]} · %{customdata[1]} partite<br>"
                                      "prevista %{x:.0f}% · reale %{y:.0f}%<extra></extra>")
        fig.update_xaxes(range=[48, 100], title="probabilità prevista per la favorita",
                         ticksuffix="%")
        fig.update_yaxes(range=[40, 100], title="vittorie reali della favorita", ticksuffix="%")
        plot(fig, 380)
    with c2:
        show(cal.rename(columns={"fascia": "Fascia", "partite": "Partite",
                                 "prevista": "Prevista %", "reale": "Reale %"}), voci=[])

    c1, c2 = st.columns(2)
    with c1:
        section("Nel corso della stagione")
        g = V.per_gruppo(bt.assign(fase=V.fase_stagione(bt)), "fase")
        show(g.rename(columns={"fase": "Fase", "partite": "Partite",
                               "accuratezza": "Favorita vince %", "brier": "Brier",
                               "errore_margine": "Errore margine"}), voci=[])
        note_html("A inizio stagione le previsioni sono più incerte: il modello parte da un "
                  "terzo della forza della stagione precedente e impara partita dopo partita.")
    with c2:
        section("Per campionato e stagione")
        g = V.per_gruppo(bt.assign(gruppo=bt["campionato_id"].map(config.CAMPIONATI) + " · " +
                                   bt["stagione"].map(config.STAGIONI)), "gruppo")
        show(g.rename(columns={"gruppo": "Campionato", "partite": "Partite",
                               "accuratezza": "Favorita vince %", "brier": "Brier",
                               "errore_margine": "Errore margine"}), voci=[])

    section("Registro delle previsioni", "salvate ogni lunedì prima delle partite e poi "
            "confrontate con il risultato", key="registro")
    reg = V.registro(a.ctx.conn)
    if reg.empty:
        note_html("Il registro parte con il prossimo aggiornamento settimanale.")
    else:
        giocate = reg[reg["punti_casa"].notna()].copy()
        if giocate.empty:
            note_html(f"{len(reg)} previsioni registrate sulle prossime partite: i risultati "
                      "compariranno qui dopo le partite.")
        else:
            giocate["vince_casa"] = giocate["punti_casa"] > giocate["punti_ospite"]
            ok = np.where(giocate["prob_casa"] >= 0.5, giocate["vince_casa"],
                          ~giocate["vince_casa"])
            note_html(f"Previsioni verificate: {len(giocate)}, favorita vincente nel "
                      f"{num(100 * ok.mean(), 1)}% dei casi.")
        prossime = reg[reg["punti_casa"].isna()].sort_values("data_partita").head(20)
        if not prossime.empty:
            show(prossime.assign(
                Partita=prossime["casa"] + " – " + prossime["ospite"],
                Casa=(100 * prossime["prob_casa"]).round(0),
                Data=prossime["data_partita"])[["Data", "Partita", "Casa"]].rename(
                columns={"Casa": "Prob. vittoria casa %"}), voci=[])

    section("Come funziona il modello", key="modello")
    st.markdown(
        '<div class="note" style="font-size:.9rem;line-height:1.55">'
        "La forza di ogni squadra è la sua efficienza (punti fatti meno subiti ogni 100 "
        "possessi), stimata in modo bayesiano: a inizio stagione pesa la stagione precedente, "
        "poi contano sempre di più le partite giocate. Il margine atteso combina la differenza "
        "di forza, il ritmo delle due squadre e il vantaggio del campo stimato dai dati. La "
        "probabilità tiene conto della variabilità tipica di una partita (circa 12 punti). I "
        "parametri sono stati tarati sulle stagioni 2024/25 e 2025/26. Le assenze negli "
        "scenari usano l'impatto stimato di ogni giocatore (On-Off dalla cronaca, ristretto "
        "verso zero con pochi minuti).</div>", unsafe_allow_html=True)
    avviso()
