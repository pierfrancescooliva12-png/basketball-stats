"""Mercato: confronto tra due giocatori con metriche avanzate."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import config
from basket import confronto as CF

from .stato import App
from .ui import ARANCIO, BLU, GRIGIO, TESTO, TESTO_2, esc, it, note_html, num, plot, section, show


def _scelta(col, hist: pd.DataFrame, chiave: str, stagioni: list[str], i_default: int,
            i_stagione: int):
    st_ = col.selectbox("Stagione", stagioni, format_func=config.STAGIONI.get,
                        key=f"cf_st_{chiave}", index=i_stagione)
    d = hist[(hist["stagione"] == st_) & (hist["minuti_pg"] >= 8) & (hist["partite"] >= 2)]
    d = d.sort_values("minuti", ascending=False).drop_duplicates("giocatore_id")
    # prima chi ha minuti sufficienti per un profilo affidabile, poi per Game Score
    d = d.assign(_ok=d["minuti"] >= CF.MINUTI_AFFIDABILI).sort_values(
        ["_ok", "game_score_p40"], ascending=False)
    opz = list(d["giocatore_id"])
    if not opz:
        col.info("Nessun giocatore con almeno 8' di media.")
        return None
    etich = {r.giocatore_id: f"{r.giocatore} · {r.squadra} ({r.categoria}, {r.ruolo.lower()})"
             for r in d.itertuples()}
    gid = col.selectbox("Giocatore", opz, format_func=etich.get, key=f"cf_g_{chiave}",
                        index=min(i_default, len(opz) - 1),
                        help="Scrivi per cercare. Ordinati per Game Score per 40'.")
    return gid, st_


def _nome(s: dict) -> str:
    return CF._cognome(s["riga"]["giocatore"])


def render(a: App, hist: pd.DataFrame):
    section("Confronto giocatori", "metriche avanzate per ruolo, alla pari tra A2 e B Nazionale",
            key="confronto")
    from .nuove import _indice_stagione
    stagioni = [s for s in config.STAGIONI if s in set(hist["stagione"])]
    i_st = _indice_stagione(a, stagioni)
    c1, c2 = st.columns(2)
    sa_ = _scelta(c1, hist, "a", stagioni, 0, i_st)
    sb_ = _scelta(c2, hist, "b", stagioni, 1, i_st)
    if not sa_ or not sb_:
        return
    if sa_ == sb_:
        note_html("Scegli due giocatori diversi (o lo stesso giocatore in due stagioni).")
        return
    oo = a.ctx.players[["giocatore_id", "on_off"]].dropna() if "on_off" in a.ctx.players \
        else pd.DataFrame()
    oo.attrs["stagione"] = a.stagione
    sa, sb = CF.confronta(hist, sa_, sb_, oo)
    if sa is None or sb is None:
        note_html("Dati non disponibili per uno dei due giocatori.")
        return
    na, nb = _nome(sa), _nome(sb)
    if na == nb:
        na, nb = (f"{na} {config.STAGIONI[sa_[1]]}", f"{nb} {config.STAGIONI[sb_[1]]}")

    voci = "".join(f"<li>{esc(it(v))}</li>" for v in CF.verdetto(sa, sb))
    st.markdown(f'<div class="frase"><b>In sintesi</b><ul style="margin:6px 0 0 18px;padding:0">'
                f'{voci}</ul></div>', unsafe_allow_html=True)
    avvisi = []
    for s, n in ((sa, na), (sb, nb)):
        if s["convertito"]:
            avvisi.append(f"i numeri di {n} (B Nazionale) sono riportati alla scala dell'A2 con i "
                          "fattori stimati sui giocatori passati tra le due categorie")
        if s["pochi_dati"]:
            avvisi.append(f"{n} ha giocato solo {num(s['riga']['minuti'], 0)} minuti in questa "
                          "stagione: profilo indicativo, confrontalo anche sulla stagione "
                          "precedente")
    if sa["ruolo"] != sb["ruolo"]:
        avvisi.append(f"ruoli diversi ({sa['ruolo'].lower()} e {sb['ruolo'].lower()}): ognuno è "
                      "misurato rispetto ai giocatori del proprio ruolo")
    if avvisi:
        note_html("⚠ " + avvisi[0][0].upper() + "; ".join(avvisi)[1:] + ".")

    # ---- profilo a sei dimensioni
    dims = list(CF.DIMENSIONI)
    fig = go.Figure()
    for s, n, colore in ((sa, na, BLU), (sb, nb, ARANCIO)):
        v = [s["dimensioni"].get(d) if pd.notna(s["dimensioni"].get(d)) else 0 for d in dims]
        fig.add_trace(go.Scatterpolar(
            r=v + v[:1], theta=dims + dims[:1], name=n, fill="toself", opacity=0.55,
            line=dict(color=colore, width=2),
            hovertemplate="%{theta}: %{r:.0f}° percentile<extra>" + n + "</extra>"))
    fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75],
                                                 gridcolor=GRIGIO, tickfont=dict(color=TESTO_2)),
                                 angularaxis=dict(gridcolor=GRIGIO, tickfont=dict(color=TESTO))),
                      legend=dict(orientation="h", y=-0.12, font=dict(color=TESTO)),
                      margin=dict(l=40, r=40, t=30, b=30))
    c1, c2 = st.columns([3, 2])
    with c1:
        plot(fig, 420)
    with c2:
        rows = []
        for d in dims:
            va, vb = sa["dimensioni"].get(d), sb["dimensioni"].get(d)
            rows.append({"Dimensione": d, na: num(va, 0), nb: num(vb, 0),
                         "Differenza": num(va - vb, 0, signed=True)
                         if pd.notna(va) and pd.notna(vb) else "–"})
        show(pd.DataFrame(rows), voci=[])
        note_html(f"Percentili (0-100) tra i giocatori dello stesso ruolo di "
                  f"{'A2' if sa['scala'] == 'A2' and sb['scala'] == 'A2' else 'categoria'} "
                  f"con almeno 10' di media ({sa['pool']} per {na}, {sb['pool']} per {nb}). "
                  "50 = nella media del ruolo.")

    # ---- costo del possesso
    section("Cosa produce ogni possesso", "per 100 possessi che il giocatore usa (tiri, liberi, "
            "palle perse)", key="possesso_giocatore")
    pa, pb = sa["possesso"], sb["possesso"]
    mediane = {f"Mediana {sa['ruolo'].lower()}": sa["possesso_ruolo"]}
    if sb["ruolo"] != sa["ruolo"]:
        mediane[f"Mediana {sb['ruolo'].lower()}"] = sb["possesso_ruolo"]
    righe = [("Possessi usati ogni 40'", "usati_p40", 1),
             ("Punti prodotti", "punti_100", 0),
             ("Palle perse", "perse_100", 0),
             ("Tiri sbagliati", "sbagliati_100", 0)]
    show(pd.DataFrame([{"Voce": lab, na: num(pa[k], d), nb: num(pb[k], d),
                        **{c: num(m.get(k), d) for c, m in mediane.items()}}
                       for lab, k, d in righe]), voci=[])
    note_html("Più possessi usati = più responsabilità in attacco. A parità di volume conta quanti "
              "punti ne escono: sopra 105 è un attacco efficiente, sotto 90 costa possessi alla "
              "squadra.")

    # ---- numeri
    section("I numeri", "per 40 minuti" + (" · scala A2" if sa["convertito"] or sb["convertito"]
                                            else ""))
    voci_n = [("Squadra", "squadra", None), ("Stagione", "stagione_label", None),
              ("Ruolo stimato", "ruolo", None), ("Età", "eta", 0), ("Altezza", "altezza_cm", 0),
              ("Partite", "partite", 0), ("Minuti a partita", "minuti_pg", 1),
              ("Punti / 40'", "punti_p40", 1), ("TS%", "ts_pct", 1), ("Usage %", "usg_pct", 1),
              ("Assist / 40'", "assist_p40", 1), ("AST%", "ast_pct", 1),
              ("Palle perse %", "tov_pct", 1), ("Rimbalzi / 40'", "rimb_tot_p40", 1),
              ("REB%", "trb_pct", 1), ("Tiri da 3 / 40'", "t3a_p40", 1),
              ("% da 3 (prudente)", "t3_pct", 1), ("% ai liberi (prudente)", "tl_pct", 1),
              ("Recuperi / 40'", "recuperate_p40", 1), ("Stoppate / 40'", "stoppate_p40", 1),
              ("Falli / 40'", "falli_commessi_p40", 1), ("Game Score / 40'", "game_score_p40", 1),
              ("On-Off", "on_off", 1), ("Presenze %", "presenze_pct", 0)]
    rows = []
    for lab, col, d in voci_n:
        va, vb = sa["riga"].get(col), sb["riga"].get(col)
        if (va is None or (not isinstance(va, str) and pd.isna(va))) and \
                (vb is None or (not isinstance(vb, str) and pd.isna(vb))):
            continue
        f = (lambda v: "–" if v is None or (not isinstance(v, str) and pd.isna(v)) else
             (str(v) if d is None else num(v, d, signed=col == "on_off")))
        rows.append({"Voce": lab, na: f(va), nb: f(vb)})
    show(pd.DataFrame(rows), voci=[])
    note_html("Percentuali di tiro prudenti: ai tiri del giocatore si aggiungono alcuni tentativi "
              "alla media della categoria, così chi ha tirato poco non sembra un 100%. On-Off solo "
              "per la stagione in corso, dalle partite con quintetti verificati.")

    # ---- affidabilità
    conn = a.ctx.conn
    aa = CF.in_scala(CF.affidabilita(conn, *sa_), sa)
    ab = CF.in_scala(CF.affidabilita(conn, *sb_), sb)
    section("Affidabilità", "costanza partita per partita, avversarie forti e deboli, forma",
            key="affidabilita_giocatore")
    if aa.get("partite") and ab.get("partite"):
        frasi = CF.frasi_affidabilita(aa, ab, na, nb)
        if frasi:
            note_html(" ".join(frasi))
        voci_a = [("Partite (almeno 5')", "partite", 0, ""),
                  ("Game Score per 40'", "gs_p40", 1, ""),
                  ("Partite storte (sotto metà della sua media)", "partite_storte", 0, "%"),
                  ("Contro la metà alta del campionato (GS/40)", "forti_p40", 1, ""),
                  ("Contro la metà bassa (GS/40)", "deboli_p40", 1, ""),
                  ("Ultime 5 partite (GS/40)", "ultime5_p40", 1, "")]
        show(pd.DataFrame([{"Voce": lab, na: num(aa.get(k), d) + suf if pd.notna(aa.get(k)) else "–",
                            nb: num(ab.get(k), d) + suf if pd.notna(ab.get(k)) else "–"}
                           for lab, k, d, suf in voci_a]), voci=[])
        if sa["convertito"] or sb["convertito"]:
            note_html("Game Score di B Nazionale riportato alla scala dell'A2, come gli altri "
                      "numeri; le partite storte non cambiano.")
    else:
        note_html("Partite insufficienti per misurare la costanza.")

    # ---- per la vostra squadra
    fit = pd.DataFrame()
    mia = a.mia_squadra
    if mia is not None:
        pr = a.profile[a.profile["squadra_id"] == mia]
        if not pr.empty:
            lega = a.profile[a.profile["campionato_id"] == pr["campionato_id"].iloc[0]]
            fit = CF.adattamento(hist, lega, mia, [sa_, sb_])
    if not fit.empty:
        nome_mia = pr["squadra"].iloc[0]
        section(f"Per {nome_mia}", "quanto ognuno copre le carenze della squadra (0-100)",
                key="fabbisogni")
        fr = CF.frase_adattamento(fit, [sa_, sb_], [na, nb])
        if fr:
            note_html(fr)
        show(pd.DataFrame({"Bisogno": fit["bisogno"], "Priorità": fit["priorita"],
                           "Perché": fit["motivo"].map(it),
                           na: [num(v, 0) if pd.notna(v) else "fuori profilo" for v in fit[sa_]],
                           nb: [num(v, 0) if pd.notna(v) else "fuori profilo" for v in fit[sb_]]}),
             voci=[])
        note_html("Adattamento: percentile del giocatore nel profilo richiesto, nella sua categoria "
                  "e stagione. \"Fuori profilo\": non ha il volume minimo per quel tipo di "
                  "giocatore (es. tiri da 3 per il tiratore).")

    # ---- PDF
    from basket.report_confronto import build_confronto
    pdf = build_confronto(sa, sb, aa, ab, fit, [sa_, sb_], [na, nb],
                          pr["squadra"].iloc[0] if not fit.empty else None)
    st.download_button("⬇ Confronto in PDF (una pagina per il direttore sportivo)", pdf,
                       file_name=f"confronto_{CF._cognome(sa['riga']['giocatore']).lower()}_"
                                 f"{CF._cognome(sb['riga']['giocatore']).lower()}.pdf",
                       mime="application/pdf", key="pdf_confronto")
