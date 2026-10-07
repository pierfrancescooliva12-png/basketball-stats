"""Schede e sezioni aggiunte per lo scouting professionale: cronaca (finali, assist,
quintetti, on/off, origine dei punti), anteprima, mercato, avvisi, la mia squadra."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import avvisi as AV
from basket import config, mercato
from basket import previsioni as F
from basket.glossario import G
from basket.report_pdf import build_pdf, slug

from . import analisi
from .stato import App, partite_df, storico
from .ui import (ARANCIO, BLU, GRIGIO, SUPERFICIE, TESTO, esc, hero, it, kpis, note_html, pills,
                 plot, section, short, show)


def _f(v, d=1, signed=False, suffix=""):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    return ((f"{v:+.{d}f}" if signed else f"{v:.{d}f}") + suffix).replace(".", ",")


def _team(df: pd.DataFrame, sid) -> pd.DataFrame:
    if df is None or df.empty or "squadra_id" not in df:
        return pd.DataFrame()
    return df[df["squadra_id"] == sid]


@st.cache_data(show_spinner="Preparo il PDF…")
def _pdf(_ctx, mtime: float, stagione: str, sid: int, mia: int | None = None,
         giochi_json: str = "[]") -> bytes:
    import json
    return build_pdf(_ctx, sid, mia, json.loads(giochi_json))


def _coverage(a: App):
    cov = a.ctx.copertura
    row = cov[cov["campionato_id"] == a.camp]
    if row.empty or not row["con_cronaca"].iloc[0]:
        note_html("Cronaca non ancora disponibile per questo campionato: le sezioni basate sul "
                  "play-by-play compariranno dopo il prossimo aggiornamento.")
        return False
    r = row.iloc[0]
    note_html(f"Cronaca disponibile per {int(r['con_cronaca'])} partite su {int(r['partite'])}; "
              f"quintetti verificati in {int(r['quintetti_ok'] or 0)}.", "quintetti")
    return True


def _notes_box(a: App, tipo: str, riferimento, titolo: str):
    section(titolo, "visibili solo al tuo club")
    if a.utente.get("demo"):
        note_html("Modalità demo: le note sono condivise e su Streamlit Cloud si perdono al "
                  "riavvio. Con gli accessi per club e un database restano private e permanenti.")
    with st.form(f"nota_{tipo}_{riferimento}", clear_on_submit=True):
        testo = st.text_area("Nuova nota", height=80, label_visibility="collapsed",
                             placeholder="Es. difende forte sul pick and roll centrale…")
        if st.form_submit_button("Salva nota") and testo.strip():
            a.archivio.add_note(a.club, tipo, riferimento, testo, a.autore)
    notes = a.archivio.notes(a.club, tipo, riferimento)
    for r in notes.itertuples():
        c1, c2 = st.columns([12, 1])
        c1.markdown(f'<div class="pill">{esc(r.testo)}<br><span class="note">{esc(r.autore)} · '
                    f'{esc(r.creata_il[:10])}</span></div>', unsafe_allow_html=True)
        if c2.button("✕", key=f"del_{r.id}", help="Elimina nota"):
            a.archivio.delete_note(a.club, r.id)
            st.rerun()


# ------------------------------------------------------------------ scouting: cronaca

def scouting_extra(a: App):
    sq = a.sq
    if sq is None:
        return
    ctx = a.ctx
    pf = a.profile[a.profile["squadra_id"] == sq].iloc[0]
    if not _coverage(a):
        _notes_box(a, "squadra", sq, "Note dello staff")
        return

    section("Finali punto a punto", "ultimi 5' con scarto ≤ 5")
    ct = _team(ctx.clutch_teams, sq)
    cp = _team(ctx.clutch_players, sq)
    if ct.empty:
        note_html("Nessun finale punto a punto finora.")
    else:
        c = ct.iloc[0]
        kpis([("Partite con finale punto a punto", str(int(c["partite_clutch"])), "nella stagione"),
              ("Record nei finali", c["record_clutch"], "vinte-perse"),
              ("Punti nei finali", f"{int(c['punti_fatti'])}-{int(c['punti_subiti'])}",
               f"differenza {int(c['diff_clutch']):+d}")])
        if not cp.empty:
            show(cp.head(8).assign(Tiri=lambda d: d["fgm"].astype(int).astype(str) + "/" +
                                   d["fga"].astype(int).astype(str),
                                   TL=lambda d: d["ftm"].astype(int).astype(str) + "/" +
                                   d["fta"].astype(int).astype(str))[
                ["giocatore", "punti", "Tiri", "fg_pct", "TL", "perse", "assist", "quota_tiri"]]
                .rename(columns={"giocatore": "Giocatore", "punti": "Punti", "fg_pct": "% campo",
                                 "perse": "Perse", "assist": "Ass", "quota_tiri": "Quota tiri"}),
                progress={"Quota tiri": (0, 100)})

    analisi.sezione_rotazioni(a, sq, ctx.nomi_giocatori)

    section("Quintetti più usati", "dai quintetti verificati")
    lu = _team(ctx.lineups, sq).head(8)
    if lu.empty:
        note_html("Quintetti non ancora disponibili (servono partite con quintetti verificati).",
                  "quintetti")
    else:
        show(lu[["giocatori", "minuti", "partite", "plus_minus", "ortg", "drtg", "net_rtg"]]
             .rename(columns={"giocatori": "Quintetto", "minuti": "Min", "partite": "PG",
                              "plus_minus": "+/-", "ortg": "ORtg", "drtg": "DRtg",
                              "net_rtg": "Net Rtg"}), colori={"Net Rtg": True})
    analisi.sezione_taglie(a, sq)

    section("+/- e On-Off", "impatto con il giocatore in campo")
    oo = a.players[(a.players["squadra_id"] == sq)]
    if "on_off" in oo and oo["on_off"].notna().any():
        show(oo.sort_values("minuti_campo", ascending=False)[
            ["giocatore", "minuti_campo", "plus_minus", "plus_minus_40", "net_on", "net_off",
             "on_off"]].rename(columns={"giocatore": "Giocatore", "minuti_campo": "Min in campo",
                                        "plus_minus": "+/-", "plus_minus_40": "+/- per 40",
                                        "net_on": "Net on", "net_off": "Net off",
                                        "on_off": "On-Off"}), colori={"On-Off": True})
    else:
        note_html("Non ancora disponibile.", "on_off")

    section("Chi serve chi", "assist → canestro")
    an = _team(ctx.assists, sq).head(10)
    if an.empty:
        note_html("Nessun assist abbinato.")
    else:
        lab = [f"{x.da.split()[-1]} → {x.a.split()[-1]}" for x in an.itertuples()]
        fig = go.Figure(go.Bar(y=lab[::-1], x=an["canestri"][::-1], orientation="h",
                               marker=dict(color=BLU, cornerradius=4),
                               text=an["punti"][::-1].map(lambda p: f"{p} pt"),
                               textposition="outside", textfont=dict(color=TESTO),
                               customdata=an[["da", "a"]].values[::-1],
                               hovertemplate="%{customdata[0]} → %{customdata[1]}<br>"
                                             "%{x} canestri<extra></extra>"))
        fig.update_xaxes(showgrid=False, showticklabels=False)
        fig.update_yaxes(showgrid=False)
        plot(fig, 340, bargap=0.35)
    analisi.sezione_origini(a, sq)
    analisi.sezione_momenti(a, sq)
    kpis([
        ("Break", f"{_f(pf.get('break_fatti_pg'), 2)} / {_f(pf.get('break_subiti_pg'), 2)}",
         "8-0 piazzati / subiti a partita"),
        ("Break massimo", f"{_f(pf.get('max_fatto'), 0)}-0", f"subito {_f(pf.get('max_subito'), 0)}-0"),
        ("Bonus falli", _f(pf.get("quota_periodi_bonus"), 0, suffix="%"),
         f"5° fallo in media al {_f(pf.get('minuto_medio_bonus'))}'"),
        ("Timeout", _f(pf.get("diff_dopo"), signed=True),
         f"punti nei 2' dopo (prima {_f(pf.get('diff_prima'), signed=True)})"),
    ])

    c1, c2 = st.columns(2)
    with c1:
        section("Profilo di tiro", "per giocatore")
        sh = _team(ctx.shots, sq)
        if not sh.empty:
            zone = sh["tiri2_zona"].sum() > 0
            cols = ["giocatore", "tiri", "tre_t", "tre_pct", "schiacciate_r"]
            ren = {"giocatore": "Giocatore", "tiri": "Tiri", "tre_t": "Da 3", "tre_pct": "3P%",
                   "schiacciate_r": "Schiacciate", "area_t": "In area", "area_pct": "Area %",
                   "media_t": "Media dist.", "media_pct": "Media %", "quota_area": "% da 2 in area"}
            if zone:
                cols[2:2] = ["area_t", "area_pct", "media_t", "media_pct"]
            show(sh.sort_values("tiri", ascending=False).head(10)[cols].rename(columns=ren))
            if not zone:
                note_html("In questa stagione la cronaca non distingue i tiri da 2 in area da quelli "
                          "dalla media distanza: è mostrata solo la parte affidabile.")
    with c2:
        section("Problemi di falli", "2+ falli nel 1° quarto o 3+ all'intervallo")
        fo = _team(ctx.fouls, sq)
        fo = fo[fo["partite_problemi"] > 0] if not fo.empty else fo
        if fo.empty:
            note_html("Nessun giocatore con problemi di falli ricorrenti.")
        else:
            show(fo.sort_values("partite_problemi", ascending=False)[
                ["giocatore", "partite_problemi", "uscite_5_falli", "falli"]].rename(
                columns={"giocatore": "Giocatore", "partite_problemi": "Partite con problemi",
                         "uscite_5_falli": "Uscito per 5 falli", "falli": "Falli totali"}))

    analisi.sezione_fisico(a, sq)
    _notes_box(a, "squadra", sq, "Note dello staff")


# ------------------------------------------------------------------ giocatore: extra

def scheda_giocatore(a: App):
    """Anagrafica, presenze, impatto, finali e report PDF: subito sotto i numeri principali."""
    if a.gsel is None:
        return
    gid, gsq = a.gsel
    me = a.players[(a.players["giocatore_id"] == gid) & (a.players["squadra_id"] == gsq)].iloc[0]
    hist = storico(a.mtime)
    mine = hist[hist["giocatore_id"] == gid] if not hist.empty else hist
    cur = mine[mine["stagione"] == a.stagione].head(1)
    bio = cur.iloc[0] if not cur.empty else None
    items = []
    if bio is not None:
        items += [("Età", _f(bio.get("eta"), 0), esc(bio.get("nazionalita") or "–")),
                  ("Altezza", f"{int(bio['altezza_cm'])} cm" if pd.notna(bio.get("altezza_cm"))
                   else "–", f"{int(bio['peso_kg'])} kg" if pd.notna(bio.get("peso_kg")) else ""),
                  ("Ruolo stimato", bio.get("ruolo") or "–", "da altezza e statistiche")]
    pres = analisi.presenze_giocatore(a, gid, gsq)
    if pres:
        items.append(pres)
    if "plus_minus" in me and pd.notna(me.get("plus_minus")):
        items += [("+/-", _f(me["plus_minus"], 0, signed=True),
                   f"{_f(me['plus_minus_40'], signed=True)} per 40'"),
                  ("On-Off", _f(me["on_off"], signed=True),
                   f"Net on {_f(me['net_on'], signed=True)}")]
    cp = a.ctx.clutch_players
    if cp is not None and not cp.empty:
        c = cp[(cp["giocatore_id"] == gid) & (cp["squadra_id"] == gsq)]
        if not c.empty:
            c = c.iloc[0]
            items.append(("Clutch", f"{int(c['punti'])} pt",
                          f"{int(c['fgm'])}/{int(c['fga'])} al tiro · quota {_f(c['quota_tiri'], 0)}%"))
    if items:
        section("Scheda", "anagrafica, presenze, impatto, finali")
        kpis(items)
    st.download_button("⬇ Report individuale per il giocatore (PDF)",
                       analisi.pdf_giocatore(a, gid, gsq, hist),
                       file_name=f"giocatore_{analisi.slug(me['giocatore'])}.pdf",
                       mime="application/pdf",
                       help="Profilo, ultime partite, carriera e spazio per gli obiettivi di "
                            "crescita concordati con lo staff.")


def giocatore_extra(a: App):
    if a.gsel is None:
        return
    gid, gsq = a.gsel
    me = a.players[(a.players["giocatore_id"] == gid) & (a.players["squadra_id"] == gsq)].iloc[0]
    hist = storico(a.mtime)
    mine = hist[hist["giocatore_id"] == gid] if not hist.empty else hist

    from . import tiri_ui
    tiri_ui.render_giocatore(a, gid, gsq)

    if len(mine) > 1:
        section("Carriera in archivio", "stagioni presenti nel database")
        show(mine.sort_values("stagione", ascending=False)[
            ["stagione_label", "squadra", "categoria", "partite", "minuti_pg", "punti_pg",
             "rimb_tot_pg", "assist_pg", "ts_pct", "usg_pct", "game_score_p40"]].rename(columns={
                 "stagione_label": "Stagione", "squadra": "Squadra", "categoria": "Cat.",
                 "partite": "PG", "minuti_pg": "Min", "punti_pg": "Punti", "rimb_tot_pg": "RT",
                 "assist_pg": "Ass", "ts_pct": "TS%", "usg_pct": "USG%",
                 "game_score_p40": "Game Score"}))

    if not hist.empty:
        section("Giocatori simili", "tutte le stagioni e categorie in archivio")
        sim = mercato.similar(hist, gid, a.stagione, n=8)
        if not sim.empty:
            show(sim[["giocatore", "squadra", "categoria", "stagione_label", "eta", "ruolo",
                      "somiglianza", "minuti_pg", "punti_pg", "ts_pct", "usg_pct"]].rename(
                columns={"giocatore": "Giocatore", "squadra": "Squadra", "categoria": "Cat.",
                         "stagione_label": "Stagione", "eta": "Età", "ruolo": "Ruolo",
                         "somiglianza": "Somiglianza", "minuti_pg": "Min", "punti_pg": "Punti",
                         "ts_pct": "TS%", "usg_pct": "USG%"}),
                progress={"Somiglianza": (0, 100)})

    c1, c2 = st.columns([3, 1])
    lista = c1.text_input("Aggiungi a una lista di osservati", "Mercato", key="lista_g")
    if c2.button("☆ Aggiungi", width="stretch"):
        a.archivio.watch(a.club, lista or "Mercato", gid, me["giocatore"], a.autore)
        st.toast(f"{me['giocatore']} aggiunto a «{lista}»")
    _notes_box(a, "giocatore", gid, "Note sul giocatore")


# ------------------------------------------------------------------ partite: extra

def partita_extra(a: App, pid: str | None):
    if not pid:
        return
    ev = a.ctx.ev
    pg = partite_df(a.mtime, a.stagione)
    row = pg[pg["partita_id"] == pid]
    if config.LINK_LNP_PASS and not row.empty and isinstance(row.iloc[0].get("stream_url"), str) \
            and row.iloc[0]["stream_url"]:
        st.link_button("▶ Guarda la partita su LNP Pass", row.iloc[0]["stream_url"])
    if ev is None or ev.empty or pid not in set(ev["partita_id"]):
        return
    e = ev[ev["partita_id"] == pid].groupby("secondi", as_index=False).last()
    section("Andamento della partita", "vantaggio della squadra di casa, minuto per minuto")
    margin = e["punti_casa"] - e["punti_ospite"]
    x = e["secondi"] / 60
    fig = go.Figure()
    fig.add_scatter(x=x, y=margin.where(margin >= 0, 0), mode="lines", line=dict(width=0,
                    shape="hv"), fill="tozeroy", fillcolor="rgba(57,135,229,0.35)",
                    hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=margin.where(margin <= 0, 0), mode="lines", line=dict(width=0,
                    shape="hv"), fill="tozeroy", fillcolor="rgba(217,89,38,0.35)",
                    hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=margin, mode="lines", line=dict(color=TESTO, width=1.5, shape="hv"),
                    customdata=e[["punti_casa", "punti_ospite"]].values, showlegend=False,
                    hovertemplate="%{x:.1f}' · %{customdata[0]}-%{customdata[1]}<extra></extra>")
    for q in range(1, int(e["periodo"].max())):
        fig.add_vline(x=10 * q if q <= 4 else 40 + 5 * (q - 4), line=dict(color=GRIGIO,
                      dash="dot", width=1))
    fig.add_hline(y=0, line=dict(color=GRIGIO, width=1))
    fig.update_xaxes(title="minuto", showgrid=False)
    fig.update_yaxes(title="vantaggio casa")
    plot(fig, 320)

    from . import tiri_ui
    tiri_ui.render_partita(a, pid)


# ------------------------------------------------------------------ anteprima

def render_anteprima(a: App):
    ctx = a.ctx
    teams = a.profile.sort_values("squadra")
    nomi = dict(zip(teams["squadra_id"], teams["squadra"]))
    ids = list(nomi)
    default_a, default_b = (ids[0], ids[1]) if len(ids) > 1 else (ids[0], ids[0])
    rif = a.sq if a.sq is not None else a.mia_squadra
    ng = ctx.next_game(rif) if rif is not None else None
    if ng and ng["casa_id"] in nomi and ng["ospite_id"] in nomi:
        default_a, default_b = ng["casa_id"], ng["ospite_id"]
    c1, c2 = st.columns(2)
    casa = c1.selectbox("Casa", ids, index=ids.index(default_a), format_func=nomi.get,
                        key=f"ant_casa_{a.sq}")
    ospite = c2.selectbox("Ospite", ids, index=ids.index(default_b), format_func=nomi.get,
                          key=f"ant_osp_{a.sq}")
    if casa == ospite:
        st.info("Scegli due squadre diverse.")
        return
    forze = ctx.forze(a.camp)
    pv = F.predict(
        forze, casa, ospite, ctx.hca(a.camp))
    meta = ""
    if ng and {ng["casa_id"], ng["ospite_id"]} == {casa, ospite}:
        meta = f"{ng['giornata']}ª giornata · {esc(it(ng['data']))} {esc(ng['ora'] or '')}"
    hero("Anteprima", f"{nomi[casa]} – {nomi[ospite]}", meta, small=True)
    if config.LINK_LNP_PASS and ng and {ng["casa_id"], ng["ospite_id"]} == {casa, ospite} \
            and ng.get("stream_url"):
        st.link_button("▶ Diretta su LNP Pass", ng["stream_url"])
    fis = analisi.fisico_prossima(a, ng) if ng and {ng["casa_id"], ng["ospite_id"]} == \
        {casa, ospite} else {}
    from . import previsioni_ui as PU
    kpis([("Probabilità di vittoria", f"{100 * pv['prob_casa']:.0f}% – {100 * (1 - pv['prob_casa']):.0f}%",
           f"casa – ospite · {PU.forbice(pv['prob_casa'])}"),
          ("Punteggio atteso", f"{pv['punti_casa']:.0f}-{pv['punti_ospite']:.0f}",
           f"margine {pv['margine']:+.1f}"),
          ("Possessi attesi", f"{pv['possessi']:.0f}", "ritmo medio delle due squadre"),
          ("Vantaggio campo", f"{ctx.hca(a.camp):+.1f}", "punti, dal campionato")]
         + ([("Riposo", f"{_f(fis[casa]['giorni_riposo'], 0)} – {_f(fis[ospite]['giorni_riposo'], 0)}",
              "giorni dalla partita precedente"),
             ("Trasferta ospite", f"{_f(fis[ospite]['km'], 0)} km", "stima su strada")]
            if fis and fis.get(casa, {}).get("giorni_riposo") is not None else []))

    PU.avviso()
    PU.perche(a, forze, casa, ospite, ctx.hca(a.camp), nomi)
    from . import chiavi_ui
    chiavi_ui.anteprima(a, casa, ospite, nomi)
    PU.scenari(a, forze, casa, ospite, ctx.hca(a.camp), nomi)

    pa = a.profile.set_index("squadra_id")
    A_, B_ = pa.loc[casa], pa.loc[ospite]
    metriche = [("Record", "record"), ("Net rating", "net_rtg"), ("ORtg", "ortg"),
                ("DRtg", "drtg"), ("Ritmo", "pace"), ("eFG%", "efg_pct"),
                ("Palle perse %", "tov_pct"), ("Rimb. offensivi %", "orb_pct"),
                ("Rimb. difensivi %", "drb_pct"), ("% punti da 3", "quota_punti_3"),
                ("% punti panchina", "quota_punti_panchina"), ("Punto a punto", "record_pp")]
    meglio_basso = {"drtg", "tov_pct"}
    rows = []
    for lab, col in metriche:
        if col == "record":
            va, vb = f"{int(A_['vinte'])}-{int(A_['perse_partite'])}", \
                f"{int(B_['vinte'])}-{int(B_['perse_partite'])}"
            rows.append((lab, va, vb, ""))
            continue
        va, vb = A_.get(col), B_.get(col)
        if isinstance(va, str):
            rows.append((lab, va, vb, ""))
            continue
        vantaggio = ""
        if pd.notna(va) and pd.notna(vb) and col not in ("pace", "quota_punti_3",
                                                           "quota_punti_panchina"):
            better_a = va < vb if col in meglio_basso else va > vb
            vantaggio = short(nomi[casa]) if better_a else short(nomi[ospite])
        rows.append((lab, _f(va), _f(vb), vantaggio))
    section("Confronto", "chi è meglio, voce per voce")
    show(pd.DataFrame(rows, columns=["Voce", short(nomi[casa]), short(nomi[ospite]), "Vantaggio"]),
         voci=[])

    section("Four Factors incrociati", "attacco di una contro difesa dell'altra")
    ff = [("eFG%", "efg_pct", "opp_efg_pct"), ("Palle perse %", "tov_pct", "opp_tov_pct"),
          ("Rimb. offensivi %", "orb_pct", None), ("FT rate", "ft_rate", "opp_ft_rate")]
    rows = []
    for lab, att, dif in ff:
        dif_b = (100 - B_["drb_pct"]) if att == "orb_pct" else B_.get(dif)
        dif_a = (100 - A_["drb_pct"]) if att == "orb_pct" else A_.get(dif)
        rows.append((lab, _f(A_.get(att), 2 if "FT" in lab else 1),
                     _f(dif_b, 2 if "FT" in lab else 1), _f(B_.get(att), 2 if "FT" in lab else 1),
                     _f(dif_a, 2 if "FT" in lab else 1)))
    show(pd.DataFrame(rows, columns=["Fattore", f"Attacco {short(nomi[casa])}",
                                     f"Difesa {short(nomi[ospite])} (concede)",
                                     f"Attacco {short(nomi[ospite])}",
                                     f"Difesa {short(nomi[casa])} (concede)"]),
         voci=[G["four_factors"]])

    c1, c2 = st.columns(2)
    for col, sid in ((c1, casa), (c2, ospite)):
        with col:
            section(f"Chiave · {short(nomi[sid])}", "primi 5 per minuti")
            p = a.players[a.players["squadra_id"] == sid].sort_values("minuti", ascending=False)
            show(p.head(5)[["giocatore", "minuti_pg", "punti_pg", "ts_pct", "usg_pct",
                            "game_score_pg"]].rename(columns={
                                "giocatore": "Giocatore", "minuti_pg": "Min", "punti_pg": "Pt",
                                "ts_pct": "TS%", "usg_pct": "USG%", "game_score_pg": "GmSc"}))

    h2h = F.head_to_head(
        ctx.conn, casa, ospite)
    section("Precedenti", "partite in archivio tra le due squadre")
    if h2h.empty:
        note_html("Nessun precedente in archivio.")
    else:
        show(h2h.drop(columns="vincente").rename(columns={
            "stagione": "Stagione", "giornata": "G.", "data": "Data", "casa": "Casa",
            "punti_casa": "PC", "punti_ospite": "PO", "ospite": "Ospite"}))


@st.cache_data(show_spinner="Simulo il resto della stagione…")
def _simulation(_ctx, mtime: float, stagione: str, camp: str) -> pd.DataFrame:
    return _ctx.simulation(camp, n=5000)


# ------------------------------------------------------------------ mercato

def render_mercato(a: App):
    hist = storico(a.mtime)
    if hist.empty:
        st.info("Archivio non disponibile.")
        return
    fabbisogni(a, hist)
    stag = [s for s in config.STAGIONI if s in set(hist["stagione"])]
    c1, c2, c3, c4 = st.columns(4)
    stagione = c1.selectbox("Stagione", stag, format_func=config.STAGIONI.get, key="m_st",
                            index=_indice_stagione(a, stag),
                            help="A inizio campionato si parte dalla stagione precedente, "
                                 "che ha più partite.")
    cat = c2.multiselect("Categoria", ["A2", "B Nazionale"], default=["A2", "B Nazionale"])
    ruoli = c3.multiselect("Ruolo stimato", ["Play / guardia", "Esterno / ala", "Lungo"],
                           default=["Play / guardia", "Esterno / ala", "Lungo"])
    eta_max = c4.number_input("Età massima", 16, 45, 45)
    c1, c2, c3, c4 = st.columns(4)
    solo_ita = c1.checkbox("Solo nazionalità ITA")
    min_min = c2.slider("Minuti di media ≥", 0, 35, 12)
    min_pg = c1.number_input("Partite giocate ≥", 0, 40, 3, key="m_pg",
                             help="Con poche partite i numeri sono poco affidabili.")
    usg = c3.slider("Usage ≥", 0, 35, 0)
    ts = c4.slider("TS% ≥", 0, 75, 0)
    d = hist[(hist["stagione"] == stagione) & hist["categoria"].isin(cat) &
             hist["ruolo"].isin(ruoli) & (hist["minuti_pg"] >= min_min) &
             (hist["partite"] >= min_pg) &
             (hist["usg_pct"].fillna(0) >= usg) & (hist["ts_pct"].fillna(0) >= ts)]
    if eta_max < 45:
        d = d[d["eta"].notna() & (d["eta"] <= eta_max)]
    if solo_ita:
        d = d[d["italiano"].fillna(False)]
    if hist["eta"].isna().all():
        note_html("Anagrafica (età, altezza, nazionalità) in arrivo con il prossimo "
                  "aggiornamento: per ora i filtri anagrafici sono vuoti.", "eta")
    section("Ricerca", f"{len(d)} giocatori")
    cols = {"giocatore": "Giocatore", "squadra": "Squadra", "categoria": "Cat.", "eta": "Età",
            "nazionalita": "Naz.", "altezza_cm": "Alt.", "ruolo": "Ruolo", "partite": "PG",
            "minuti_pg": "Min", "punti_pg": "Punti", "rimb_tot_pg": "RT", "assist_pg": "Ass",
            "ts_pct": "TS%", "usg_pct": "USG%", "ast_pct": "AST%", "trb_pct": "REB%",
            "game_score_p40": "Game Score", "presenze_pct": "Presenze %"}
    cols = {k: v for k, v in cols.items() if k in d.columns}
    d = d.assign(dati=(d["partite"] < 3).map({True: "⚠ pochi dati", False: ""}))
    cols = {"giocatore": "Giocatore", "dati": "Dati", **cols}
    show(d.sort_values("game_score_p40", ascending=False)[list(cols)].rename(columns=cols),
         height=520, progress={"USG%": (0, 40), "TS%": (0, 80)},
         colori={"Game Score": True, "Punti": True})

    analisi.dalla_b_alla_a2(a, hist, stagione)

    section("Talenti di B Nazionale", "giovani con minuti e rendimento da A2")
    tal = mercato.prospects(hist, stagione, eta_max=min(eta_max, 25))
    if tal.empty:
        note_html("Nessun giocatore con i criteri (età ≤ 25, 15' di media).")
    else:
        show(tal.head(15)[["giocatore", "squadra", "eta", "ruolo", "minuti_pg", "punti_pg",
                           "ts_pct", "usg_pct", "game_score_p40", "indice"]].rename(columns={
                               **cols, "indice": "Indice"}), progress={"Indice": (0, 100)})

    prev = [s for s in stag if s < stagione]
    if prev:
        section("Chi è cresciuto", f"da {config.STAGIONI[prev[0]]} a {config.STAGIONI[stagione]}")
        pr = mercato.progression(hist, prev[0], stagione)
        pr = pr[pr["minuti_pg"] >= 10].sort_values("delta_game_score_p40", ascending=False)
        show(pr.head(15)[["giocatore", "squadra", "categoria", "squadra_prima", "categoria_prima",
                          "minuti_pg_prima", "minuti_pg", "game_score_p40_prima",
                          "game_score_p40", "delta_game_score_p40"]].rename(columns={
                              "giocatore": "Giocatore", "squadra": "Squadra ora",
                              "categoria": "Cat. ora", "squadra_prima": "Squadra prima",
                              "categoria_prima": "Cat. prima", "minuti_pg_prima": "Min prima",
                              "minuti_pg": "Min ora", "game_score_p40_prima": "Game Score prima",
                              "game_score_p40": "Game Score ora",
                              "delta_game_score_p40": "Δ Game Score"}))

    section("Giocatori simili", "scegli un giocatore dalla ricerca")
    opts = d.sort_values("giocatore")
    labels = {(r.giocatore_id, r.squadra): f"{r.giocatore} ({r.squadra})" for r in opts.itertuples()}
    if labels:
        scelta = st.selectbox("Giocatore", list(labels), format_func=labels.get, key="m_sim")
        sim = mercato.similar(hist, scelta[0], stagione, n=10)
        if not sim.empty:
            show(sim[["giocatore", "squadra", "categoria", "stagione_label", "eta", "ruolo",
                      "somiglianza", "minuti_pg", "punti_pg", "ts_pct", "usg_pct"]].rename(
                columns={**cols, "stagione_label": "Stagione", "somiglianza": "Somiglianza"}),
                progress={"Somiglianza": (0, 100)})
        c1, c2 = st.columns([3, 1])
        lista = c1.text_input("Lista", "Mercato", key="m_lista")
        if c2.button("☆ Aggiungi agli osservati", width="stretch"):
            nome = opts[opts["giocatore_id"] == scelta[0]]["giocatore"].iloc[0]
            a.archivio.watch(a.club, lista or "Mercato", scelta[0], nome, a.autore)
            st.toast(f"{nome} aggiunto a «{lista}»")

    section("Osservati del club", "liste condivise dallo staff")
    wl = a.archivio.watchlist(a.club)
    if wl.empty:
        note_html("Nessun giocatore osservato. Aggiungili da qui o dalla scheda Giocatore.")
    else:
        cur = hist[hist["stagione"] == hist["stagione"].max()]
        wl = wl.merge(cur[["giocatore_id", "squadra", "categoria", "minuti_pg", "punti_pg",
                           "ts_pct", "game_score_p40"]], on="giocatore_id", how="left")
        for lista, g in wl.groupby("lista"):
            st.markdown(f"**{esc(lista)}**")
            show(g[["giocatore", "squadra", "categoria", "minuti_pg", "punti_pg", "ts_pct",
                    "game_score_p40", "aggiunto_da"]].rename(columns={
                        **cols, "aggiunto_da": "Aggiunto da"}))
            rimuovi = st.selectbox("Rimuovi", [None] + g["giocatore_id"].tolist(),
                                   format_func=lambda x: "—" if x is None else
                                   g.set_index("giocatore_id").loc[x, "giocatore"],
                                   key=f"rm_{lista}")
            if rimuovi:
                a.archivio.unwatch(a.club, lista, rimuovi)
                st.rerun()


def _indice_stagione(a: App, stagioni: list[str]) -> int:
    """Stagione proposta per il mercato: quella in corso, o la precedente se il campionato
    è appena iniziato (meno di 5 giornate)."""
    if not stagioni:
        return 0
    i = stagioni.index(a.stagione) if a.stagione in stagioni else 0
    giornate = int(a.bs_c["giornata"].max()) if not a.bs_c.empty else 0
    if giornate < 5 and i + 1 < len(stagioni):
        return i + 1
    return i


# ------------------------------------------------------------------ avvisi

ICONE = {"assenza": "🚑", "quintetto": "🔁", "minuti": "⏱", "forma": "📈", "massimo": "🔥",
         "serie": "📊"}
TITOLI = {"assenza": "Assenze", "quintetto": "Cambi di quintetto", "minuti": "Minutaggio",
          "forma": "Forma", "massimo": "Massimi stagionali", "serie": "Serie"}


def render_avvisi(a: App):
    al = a.ctx.alerts
    al = al[al["campionato_id"] == a.camp] if not al.empty else al
    if a.sq is not None and not al.empty:
        al = al[al["squadra_id"] == a.sq]
    if al.empty:
        st.info("Nessun avviso per i filtri selezionati.")
        return
    note_html("Generati dopo ogni giornata confrontando l'ultima partita con le precedenti.")
    for tipo in ["assenza", "quintetto", "minuti", "forma", "massimo", "serie"]:
        g = al[al["tipo"] == tipo]
        if g.empty:
            continue
        section(f"{ICONE[tipo]} {TITOLI[tipo]}", f"{len(g)}")
        pills([f"{r.squadra} · {r.giocatore + ': ' if isinstance(r.giocatore, str) else ''}"
               f"{r.testo}" for r in g.itertuples()], "neg" if tipo == "assenza" else "pos", "")


# ------------------------------------------------------------------ la mia squadra

METRICHE_OBIETTIVI = {"efg_pct": "eFG% in attacco", "tov_pct": "Palle perse %",
                      "orb_pct": "Rimbalzi offensivi %", "ft_rate": "FT rate",
                      "opp_efg_pct": "eFG% concessa", "opp_tov_pct": "Palle perse forzate %",
                      "drb_pct": "Rimbalzi difensivi %", "opp_ft_rate": "FT rate concesso"}


def render_mia_squadra(a: App):
    sid = a.mia_squadra
    if sid is None:
        st.info("Scegli la tua squadra nella Home, oppure una squadra nel filtro in alto "
                "(con gli accessi per club è impostata automaticamente).")
        return
    pr = a.profile.set_index("squadra_id")
    me = pr.loc[sid]
    n = len(pr)
    rank = lambda c, asc=False: int(pr[c].rank(ascending=asc, method="min")[sid]) \
        if pd.notna(me.get(c)) else 0
    hero("La mia squadra", me["squadra"], f"Record {int(me['vinte'])}-{int(me['perse_partite'])}",
         small=True)
    kpis([("Net rating", _f(me["net_rtg"], signed=True), f"{rank('net_rtg')}° su {n}"),
          ("Rating offensivo", _f(me["ortg"]), f"{rank('ortg')}° su {n}"),
          ("Rating difensivo", _f(me["drtg"]), f"{rank('drtg', True)}° su {n}"),
          ("Ritmo", _f(me["pace"]), f"{rank('pace')}° su {n}"),
          ("Punto a punto", me["record_pp"], "margine ≤ 5"),
          ("Fortuna", _f(me["fortuna"], signed=True), "vittorie reali − attese")])

    from . import miglioramento_ui
    miglioramento_ui.render(a, sid)

    section("Obiettivi Four Factors", "impostati dallo staff, salvati per il club",
            key="four_factors")
    goals = {**AV.OBIETTIVI_DEFAULT, **a.archivio.goals(a.club)}
    with st.expander("Modifica obiettivi"):
        with st.form("obiettivi"):
            cols = st.columns(4)
            nuovi = {}
            for i, (k, lab) in enumerate(METRICHE_OBIETTIVI.items()):
                nuovi[k] = cols[i % 4].number_input(lab, value=float(goals[k]),
                                                     step=0.01 if "ft" in k else 0.5,
                                                     format="%.2f" if "ft" in k else "%.1f")
            if st.form_submit_button("Salva obiettivi"):
                a.archivio.set_goals(a.club, nuovi)
                st.rerun()
    form = AV.rolling_form(a.bs_c, sid)
    rows = []
    for k, lab in METRICHE_OBIETTIVI.items():
        val = me.get(k)
        ult = form[k].tail(5).mean() if not form.empty and k in form else None
        alto = AV.OBIETTIVO_MEGLIO_ALTO[k]
        ok = pd.notna(val) and (val >= goals[k] if alto else val <= goals[k])
        d = 2 if "ft" in k else 1
        rows.append((lab, _f(goals[k], d), _f(val, d), _f(ult, d), "✅" if ok else "❌"))
    show(pd.DataFrame(rows, columns=["Voce", "Obiettivo", "Stagione", "Ultime 5", "Raggiunto"]),
         voci=[])

    if not form.empty:
        section("Andamento", "ORtg e DRtg partita per partita, media mobile su 5")
        x = [f"G{g}" for g in form["giornata"]]
        fig = go.Figure()
        fig.add_scatter(x=x, y=form["ortg_mm"], name="ORtg", mode="lines+markers",
                        line=dict(color=BLU, width=2),
                        marker=dict(size=8, line=dict(color=SUPERFICIE, width=2)))
        fig.add_scatter(x=x, y=form["drtg_mm"], name="DRtg", mode="lines+markers",
                        line=dict(color=ARANCIO, width=2),
                        marker=dict(size=8, line=dict(color=SUPERFICIE, width=2)))
        plot(fig, 340)

    section("Contro le forti e contro le deboli", "avversarie divise per Net rating")
    sp = AV.split_by_opponent(a.bs_c, sid)
    show(sp[["avversari", "partite", "vinte", "perse_partite", "punti_pg", "punti_subiti_pg",
             "ortg", "drtg", "net_rtg"]].rename(columns={
                 "avversari": "Avversarie", "partite": "PG", "vinte": "V", "perse_partite": "P",
                 "punti_pg": "Punti", "punti_subiti_pg": "Subiti", "ortg": "ORtg", "drtg": "DRtg",
                 "net_rtg": "Net Rtg"}))
    ng = a.ctx.next_game(sid)
    if ng:
        avv = ng["ospite"] if ng["casa_id"] == sid else ng["casa"]
        note_html(f"Prossima partita: {ng['giornata']}ª giornata, "
                  f"{pd.Timestamp(ng['data']).strftime('%d/%m/%Y')} contro {avv}. Lo scouting "
                  "dell'avversaria e l'anteprima sono nella Home e nell'area Avversaria.")


# ------------------------------------------------------------------ fabbisogni della squadra

PRIORITA_CLASSE = {"Alta": "neg", "Media": "pos", "Bassa": ""}


def fabbisogni(a: App, hist: pd.DataFrame):
    sid = a.sq if a.sq is not None else a.mia_squadra
    if sid is None:
        note_html("Seleziona una squadra in alto per vedere i suoi fabbisogni e i giocatori "
                  "che potrebbero servirle.", "fabbisogni")
        return
    nome = a.profile.set_index("squadra_id").loc[sid, "squadra"]
    section("Fabbisogni", f"{nome} · tipi di giocatore utili e candidati")

    stag_disp = [s for s in config.STAGIONI if s in set(hist["stagione"])]
    c1, c2, c3, c4 = st.columns(4)
    val = c1.selectbox("Valuta i candidati su", stag_disp, format_func=config.STAGIONI.get,
                       key=f"fb_st_{sid}", index=_indice_stagione(a, stag_disp),
                       help="A inizio campionato la stagione precedente offre più partite.")
    cat = c2.multiselect("Categoria dei candidati", ["A2", "B Nazionale"],
                         default=["A2", "B Nazionale"], key=f"fb_cat_{sid}")
    eta = c3.number_input("Età massima", 16, 45, 45, key=f"fb_eta_{sid}")
    ita = c4.checkbox("Solo nazionalità ITA", key=f"fb_ita_{sid}")

    # la squadra si valuta sempre sulla stagione selezionata in alto; i candidati sulla scelta
    lines = hist.copy()
    if val != a.stagione:
        # squadra attuale dei candidati (se presenti nella stagione in corso)
        ora = hist[hist["stagione"] == a.stagione].sort_values("minuti").groupby(
            "giocatore_id").tail(1).set_index("giocatore_id")["squadra"]
        lines = lines.assign(squadra_ora=lines["giocatore_id"].map(ora))
        # esclude chi oggi gioca già nella squadra
        mine = set(hist[(hist["stagione"] == a.stagione) & (hist["squadra_id"] == sid)]
                   ["giocatore_id"])
        lines.loc[lines["giocatore_id"].isin(mine), "squadra_id"] = sid
    sugg = mercato.suggestions(lines, a.profile, sid, val, categorie=tuple(cat),
                               eta_max=None if eta >= 45 else eta, solo_ita=ita)
    if not sugg:
        note_html("Dati insufficienti per stimare i fabbisogni.")
        return
    if all(s["gravita"] < mercato.SOGLIA_BISOGNO for s in sugg):
        note_html("Nessuna carenza marcata: la squadra è nella metà alta del campionato in tutte "
                  "le aree. Sotto, le due aree meno forti.")

    for i, s in enumerate(sugg):
        st.markdown(
            f'<div class="pill {PRIORITA_CLASSE[s["priorita"]]}" style="margin-top:14px">'
            f'<span class="fb-t">{esc(s["nome"])}</span> · priorità '
            f'{esc(s["priorita"].lower())}<br>'
            f'<span class="note">{esc(s["descrizione"])}</span></div>', unsafe_allow_html=True)
        pills(["Perché: " + m for m in s["motivi"]], "", "")
        b = s["migliore_in_rosa"]
        if b is None:
            note_html("In rosa nessun giocatore corrisponde a questo profilo (con almeno 10' di "
                      "media e il volume minimo).", "adattamento")
        else:
            note_html(f"In rosa il più vicino al profilo è {b['giocatore']} "
                      f"(adattamento {b['adattamento']:.0f}): i candidati sotto fanno meglio.",
                      "adattamento")
        c = s["candidati"]
        if c.empty:
            note_html("Nessun candidato con i filtri scelti.")
            continue
        sq_col = "squadra_ora" if "squadra_ora" in c.columns else "squadra"
        c = c.assign(squadra_vista=c[sq_col].fillna("senza squadra in A2/B " +
                                                    config.STAGIONI.get(a.stagione, "")))
        cols = {"giocatore": "Giocatore", "squadra_vista": "Squadra",
                "adattamento": "Adattamento"}
        cols.update({m: "FTA/FGA" if m == "ft_rate" else mercato.ETICHETTE.get(m, m)
                     for m in s["mostra"]})
        cols.update({"minuti_pg": "Min", "partite": "PG", "categoria": "Cat.", "eta": "Età",
                     "nazionalita": "Naz.", "ruolo": "Ruolo"})
        show(c[list(cols)].rename(columns=cols), progress={"Adattamento": (0, 100)})
        opts = {r.giocatore_id: f"{r.giocatore} ({r.squadra_vista})" for r in c.itertuples()}
        k1, k2 = st.columns([3, 1])
        scelto = k1.selectbox("Aggiungi agli osservati", list(opts), format_func=opts.get,
                              key=f"fb_add_{sid}_{i}", label_visibility="collapsed")
        if k2.button("☆ Osserva", key=f"fb_btn_{sid}_{i}", width="stretch"):
            nome_g = c.set_index("giocatore_id").loc[scelto, "giocatore"]
            a.archivio.watch(a.club, f"Fabbisogno: {s['nome']}", scelto, nome_g, a.autore)
            st.toast(f"{nome_g} aggiunto agli osservati ({s['nome']})")
    st.markdown("<br>", unsafe_allow_html=True)
