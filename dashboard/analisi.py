"""Sezioni di approfondimento della dashboard: rotazioni, taglia dei quintetti, momenti
della partita, origine dei punti fatti e concessi, riposo e trasferte, ultima partita,
report PDF post-partita e individuale."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import approfondimenti as X
from basket import luoghi
from basket import report_extra as R
from basket.report_pdf import slug  # noqa: F401  (riesportato per le pagine)

from .stato import App
from .ui import (ARANCIO, BLU, GRIGIO, NEUTRO, SUPERFICIE, TESTO, badge_pos, esc, it, kpis,
                 note_html, num, plot, section, short, show)


# ------------------------------------------------------------------ PDF

@st.cache_data(show_spinner="Preparo il PDF post-partita…")
def _pdf_post(_ctx, mtime: float, stagione: str, sid: int, pid: str, obiettivi: tuple) -> bytes:
    return R.build_post_partita(_ctx, sid, pid, dict(obiettivi))


def pdf_post_partita(a: App, sid: int, pid: str) -> bytes:
    return _pdf_post(a.ctx, a.mtime, a.stagione, sid, pid,
                     tuple(sorted(a.archivio.goals(a.club).items())))


@st.cache_data(show_spinner="Preparo il report del giocatore…")
def _pdf_giocatore(_ctx, _hist, mtime: float, stagione: str, gid: str, sid: int) -> bytes:
    return R.build_giocatore(_ctx, gid, sid, _hist)


def pdf_giocatore(a: App, gid: str, sid: int, hist) -> bytes:
    return _pdf_giocatore(a.ctx, hist, a.mtime, a.stagione, gid, sid)


# ------------------------------------------------------------------ riposo e trasferte

def fisico_prossima(a: App, ng: dict) -> dict:
    """Giorni di riposo e km di trasferta delle due squadre per la prossima partita."""
    cal = a.ctx.calendario_fisico
    out = {}
    if cal is None or cal.empty or not ng:
        return out
    casa_citta = cal[cal["casa"] == 1].groupby("squadra_id")["citta_squadra"].agg(
        lambda s: s.value_counts().index[0] if s.notna().any() else None)
    citta_partita = casa_citta.get(ng["casa_id"])
    for sid in (ng["casa_id"], ng["ospite_id"]):
        ultima = cal[cal["squadra_id"] == sid]["data"].max()
        in_casa = sid == ng["casa_id"]
        out[sid] = X.prossima_trasferta(ultima, ng["data"], citta_partita,
                                        casa_citta.get(sid), in_casa)
    return out


def _rendimento(a: App, sid: int, colonna: str, ordine: list[str], titolo: str, desc: str):
    cal = a.ctx.calendario_fisico
    t = X.rendimento_per(a.bs_c, cal, colonna)
    if t.empty:
        return
    t = t[t["squadra_id"] == sid].copy()
    if t.empty:
        return
    t[colonna] = pd.Categorical(t[colonna], ordine, ordered=True)
    t = t.sort_values(colonna)
    section(titolo, desc)
    show(t[[colonna, "partite", "vinte", "perse_partite", "punti_pg", "punti_subiti_pg",
            "net_rtg"]].rename(columns={colonna: "Situazione", "partite": "PG", "vinte": "V",
                                         "perse_partite": "P", "punti_pg": "Punti fatti",
                                         "punti_subiti_pg": "Punti subiti",
                                         "net_rtg": "Net rating"}), voci=[])


# ------------------------------------------------------------------ scouting: approfondimenti

def sezione_fisico(a: App, sid: int):
    c1, c2 = st.columns(2)
    with c1:
        _rendimento(a, sid, "riposo", ["Ravvicinata (≤ 3 giorni)", "Normale (4-6 giorni)",
                                       "Lunga (7+ giorni)"],
                    "Riposo", "rendimento per giorni dalla partita precedente")
    with c2:
        _rendimento(a, sid, "viaggio", ["Vicina (< 250 km)", "Media (250-500 km)",
                                        "Lunga (> 500 km)"],
                    "Trasferte", "rendimento fuori casa per distanza (stima su strada)")


def sezione_rotazioni(a: App, sid: int, nomi: dict):
    rot = a.ctx.rotazioni
    sq = rot["squadre"]
    if sq.empty or sid not in set(sq["squadra_id"]):
        return
    s = sq.set_index("squadra_id").loc[sid]
    section("Rotazioni", f"dalle {int(s['partite'])} partite con quintetti verificati",
            key="rotazioni")
    base = " · ".join(nomi.get(g, g).split()[-1] for g in str(s["quintetto"]).split(","))
    kpis([("Primo cambio", f"{num(s['minuto_primo_cambio'])}'", "minuto mediano"),
          ("Giocatori in rotazione", num(s["giocatori_rotazione"]), "con almeno 5' a partita"),
          ("Quintetto base", f"{num(s['quota_quintetto_base'], 0)}%", base)])
    g = rot["griglia"]
    g = g[g["squadra_id"] == sid]
    gi = rot["giocatori"]
    gi = gi[(gi["squadra_id"] == sid)].sort_values("secondi", ascending=False)
    gi = gi[gi["minuti_pg"] * gi["partite_giocate"] >= 20]
    if g.empty or gi.empty:
        return
    ordine = list(gi["giocatore_id"])
    z = (g.pivot_table(index="giocatore_id", columns="minuto", values="quota", fill_value=0)
         .reindex(index=ordine, columns=range(40), fill_value=0))
    etich = [nomi.get(x, x) for x in z.index]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=[f"{m + 1}'" for m in z.columns], y=etich, zmin=0, zmax=100,
        colorscale=[[0, SUPERFICIE], [0.5, "#2b5d9e"], [1, BLU]], xgap=1, ygap=2,
        showscale=False,
        hovertemplate="%{y}<br>minuto %{x}: in campo nel %{z:.0f}% delle partite<extra></extra>"))
    for q in (10, 20, 30):
        fig.add_vline(x=q - 0.5, line=dict(color=GRIGIO, width=1))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False, tickvals=[f"{m}'" for m in (1, 5, 10, 15, 20, 25, 30, 35, 40)])
    st.markdown('<div class="note">Più il colore è acceso, più spesso il giocatore è in campo in '
                'quel minuto. Le linee separano i quarti.</div>', unsafe_allow_html=True)
    plot(fig, max(300, 30 * len(etich) + 60))
    t = gi.assign(giocatore=gi["giocatore_id"].map(nomi))
    show(t[["giocatore", "minuti_pg", "quota_titolare", "minuto_ingresso", "quota_finale"]]
         .rename(columns={"giocatore": "Giocatore", "minuti_pg": "Minuti",
                          "quota_titolare": "% da titolare", "minuto_ingresso": "Entra al minuto",
                          "quota_finale": "% in campo negli ultimi 5'"}),
         progress={"% da titolare": (0, 100), "% in campo negli ultimi 5'": (0, 100)}, voci=[])


def sezione_taglie(a: App, sid: int):
    tg = a.ctx.taglie
    if tg is None or tg.empty or sid not in set(tg["squadra_id"]):
        return
    t = tg[tg["squadra_id"] == sid]
    lo, hi = t["soglia_bassa"].iloc[0], t["soglia_alta"].iloc[0]
    section("Quintetti alti e bassi",
            f"piccolo: media sotto {num(lo, 0)} cm · grande: da {num(hi, 0)} cm in su",
            key="taglia")
    c1, c2 = st.columns([3, 2])
    with c1:
        fig = go.Figure(go.Bar(
            x=t["taglia"].astype(str), y=t["net_rtg"],
            marker=dict(color=[BLU if (v or 0) >= 0 else ARANCIO for v in t["net_rtg"]],
                        cornerradius=4),
            text=[num(v, 1, signed=True) if pd.notna(v) else "pochi minuti"
                  for v in t["net_rtg"]], textposition="outside", textfont=dict(color=TESTO),
            customdata=t[["minuti", "quota_minuti"]].values,
            hovertemplate="%{x}: Net %{y:+.1f}<br>%{customdata[0]:.0f}' (%{customdata[1]:.0f}%)"
                          "<extra></extra>"))
        fig.add_hline(y=0, line=dict(color=GRIGIO, width=1))
        fig.update_yaxes(title="Net rating")
        plot(fig, 300, bargap=0.5)
    with c2:
        show(t[["taglia", "quota_minuti", "altezza", "ortg", "drtg", "net_rtg"]]
             .assign(taglia=lambda d: d["taglia"].astype(str))
             .rename(columns={"taglia": "Quintetto", "quota_minuti": "% minuti",
                              "altezza": "Altezza media", "ortg": "ORtg", "drtg": "DRtg",
                              "net_rtg": "Net rating"}), voci=[])


def sezione_momenti(a: App, sid: int):
    m = a.ctx.momenti
    if m is None or m.empty or sid not in set(m["squadra_id"]):
        return
    t = m[m["squadra_id"] == sid]
    section("Momenti della partita", "punti fatti − subiti a partita in momenti chiave",
            key="momenti")
    cards = []
    for r in t.itertuples():
        sub = (f'<span>{esc(it(f"{num(r.fatti_pg)} fatti, {num(r.subiti_pg)} subiti"))}</span>'
               + badge_pos((r.posizione, r.squadre)))
        cards.append((r.etichetta, num(r.diff_pg, 1, signed=True), sub))
    kpis(cards)
    pf = a.profile.set_index("squadra_id")
    if "diff_dopo" in pf.columns and pd.notna(pf.loc[sid].get("diff_dopo")):
        note_html(f"Dopo i propri timeout (2 minuti successivi): differenza "
                  f"{num(pf.loc[sid]['diff_dopo'], 1, signed=True)} punti di media.", "timeout_eff")


def sezione_origini(a: App, sid: int):
    oc = a.ctx.origini_concesse
    pf = a.profile.set_index("squadra_id")
    if oc is None or oc.empty or sid not in set(oc["squadra_id"]) or \
            "punti_da_perse_pg" not in pf.columns:
        return
    o = oc.set_index("squadra_id")
    lega_oc = oc[oc["campionato_id"] == a.camp].set_index("squadra_id")
    voci = [("Da palle perse", "punti_da_perse_pg", "concessi_da_perse_pg"),
            ("Seconde occasioni", "punti_seconda_occasione_pg", "concessi_seconda_occasione_pg"),
            ("Contropiede", "punti_contropiede_pg", "concessi_contropiede_pg")]
    rows = []
    for lab, f, c in voci:
        rows.append({
            "Origine": lab, "Fatti": pf.loc[sid, f], "Media fatti": a.profile[f].mean(),
            "Posizione fatti": badge_txt(X.posizione(a.profile.set_index("squadra_id")[f], sid)),
            "Concessi": o.loc[sid, c], "Media concessi": lega_oc[c].mean(),
            "Posizione concessi": badge_txt(X.posizione(lega_oc[c], sid, piu_alto_meglio=False)),
        })
    section("Origine dei punti fatti e concessi", "a partita, dalla cronaca", key="origini")
    show(pd.DataFrame(rows), voci=[])


def badge_txt(pos) -> str:
    return f"{pos[0]}° su {pos[1]}" if pos else "–"


# ------------------------------------------------------------------ ultima partita (mia squadra)

def ultima_partita(a: App):
    sid = a.mia_squadra
    if sid is None:
        return
    mine = a.bs_c[a.bs_c["squadra_id"] == sid].sort_values(["data", "partita_id"],
                                                           ascending=False)
    if mine.empty:
        return
    section("Report post-partita", "cosa è andato bene e cosa no, rispetto alla stagione",
            key="post_partita")
    labels = {r.partita_id: f"G{r.giornata} · {pd.Timestamp(r.data).strftime('%d/%m')} · "
                            f"{'V' if r.vinta else 'P'} {int(r.punti)}-{int(r.punti_subiti)} "
                            f"vs {r.avversario}" for r in mine.itertuples()}
    pid = st.selectbox("Partita", list(labels), format_func=labels.get, key=f"post_{sid}")
    goals = a.archivio.goals(a.club)
    r = R.riepilogo_partita(a.ctx, sid, pid, goals)
    if r["frasi"]:
        st.markdown('<div class="frase"><b>In sintesi</b>' +
                    "<br>".join(esc(it(f)) for f in r["frasi"]) + "</div>",
                    unsafe_allow_html=True)
    if r["affidabile"]:
        rows = [{"Fattore": f["voce"], "Partita": num(f["partita"], f["decimali"]),
                 "Media stagione": num(f["media"], f["decimali"]),
                 "Obiettivo": num(f["obiettivo"], f["decimali"]),
                 "Esito": "" if f["raggiunto"] is None else ("✅ raggiunto" if f["raggiunto"]
                                                             else "❌ mancato")}
                for f in r["fattori"]]
        show(pd.DataFrame(rows), voci=[])
    g = r["giocatori"]
    show(g[["giocatore", "minuti", "punti", "rimb_tot", "assist", "perse", "game_score",
            "gs_medio", "delta_gs"]].rename(columns={
                "giocatore": "Giocatore", "minuti": "Min", "punti": "Punti",
                "rimb_tot": "Rimbalzi", "assist": "Assist", "perse": "Perse",
                "game_score": "Game Score", "gs_medio": "Media stagione",
                "delta_gs": "Differenza"}), colori={"Differenza": True})
    st.download_button("⬇ Report post-partita (PDF)", pdf_post_partita(a, sid, pid),
                       file_name=f"post_partita_{slug(r['squadra'])}_{pid}.pdf",
                       mime="application/pdf", type="primary")


# ------------------------------------------------------------------ mercato e giocatore

def dalla_b_alla_a2(a: App, hist: pd.DataFrame, stagione: str):
    section("Dalla B all'A2", "come cambierebbero i numeri salendo di categoria",
            key="traduzione")
    fatt = X.fattori_categoria(hist)
    n = int(fatt["coppie"].max()) if not fatt.empty else 0
    if n < X.MIN_COPPIE:
        note_html(f"Servono più giocatori passati tra B Nazionale e A2 per una stima affidabile "
                  f"(ora {n}, ne servono almeno {X.MIN_COPPIE}). La stima migliora con lo storico "
                  "2024/25 e con l'avanzare della stagione.")
        return
    righe = []
    for f in fatt.itertuples():
        if pd.isna(f.valore):
            continue
        righe.append(f"{f.etichetta}: " + (f"× {num(f.valore, 2)}" if f.tipo == "ratio"
                                            else f"{num(f.valore, 1, signed=True)} punti"))
    note_html(f"Stima dai {n} giocatori che hanno giocato in entrambe le categorie (stessa "
              "stagione o stagioni consecutive): " + " · ".join(righe) + ".")
    b = hist[(hist["stagione"] == stagione) & (hist["categoria"] == "B Nazionale")
             & (hist["minuti_pg"] >= 15) & (hist["partite"] >= 3)]
    if b.empty:
        return
    pr = X.proiezione_a2(b, fatt).sort_values("game_score_p40_a2", ascending=False).head(20)
    show(pr[["giocatore", "squadra", "eta", "ruolo", "minuti_pg", "punti_p40", "punti_p40_a2",
             "ts_pct", "ts_pct_a2", "game_score_p40", "game_score_p40_a2"]].rename(columns={
                 "giocatore": "Giocatore", "squadra": "Squadra", "eta": "Età", "ruolo": "Ruolo",
                 "minuti_pg": "Min", "punti_p40": "Punti/40 in B",
                 "punti_p40_a2": "Punti/40 attesi in A2", "ts_pct": "TS% in B",
                 "ts_pct_a2": "TS% attesa in A2", "game_score_p40": "Game Score/40 in B",
                 "game_score_p40_a2": "Game Score/40 atteso in A2"}),
         colori={"Game Score/40 atteso in A2": True})


def presenze_giocatore(a: App, gid: str, sid: int) -> tuple | None:
    pr = a.ctx.presenze
    if pr is None or pr.empty:
        return None
    r = pr[(pr["giocatore_id"] == gid) & (pr["squadra_id"] == sid)]
    if r.empty:
        return None
    r = r.iloc[0]
    sub = f"{int(r['saltate'])} saltate su {int(r['partite_periodo'])}"
    if r["senza_entrare"]:
        sub += f" · {int(r['senza_entrare'])} a referto senza entrare"
    return ("Presenze", f"{num(r['presenze_pct'], 0)}%", sub)
