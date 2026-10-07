"""Pagine della dashboard e loro organizzazione in aree (navigazione in alto).

Ogni pagina è calcolata solo quando è aperta. Le pagine che lavorano su una squadra o un
giocatore non partono mai vuote: propongono la prossima avversaria della squadra del club
o una scelta rapida.
"""

import pandas as pd
import streamlit as st

from basket import approfondimenti as X
from basket import config

from . import analisi, chiavi_ui, nuove, previsioni_ui, schede
from .stato import App
from .ui import (badge_pos, brand_hero, esc, frase, it, kpis, note_html, num, pills, section,
                 short, titolo_pagina)

APP: App | None = None
PAGINE: dict = {}


def data_it(d) -> str:
    try:
        return pd.Timestamp(str(d)[:10]).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(d)[:10]


# ------------------------------------------------------------------ scelte rapide

def scegli_squadra(a: App, motivo: str):
    """Griglia di pulsanti per scegliere la squadra (al posto di una pagina vuota)."""
    note_html(motivo)
    teams = a.profile.sort_values("squadra")
    cols = st.columns(4)
    for i, r in enumerate(teams.itertuples()):
        cols[i % 4].button(short(r.squadra), key=f"pick_{r.squadra_id}", width="stretch",
                           help=r.squadra, on_click=imposta, kwargs={"f_sq": r.squadra_id})


def scegli_giocatore(a: App):
    pool = a.players if a.sq is None else a.players[a.players["squadra_id"] == a.sq]
    pool = pool.sort_values("minuti", ascending=False)
    opts = {(r.giocatore_id, r.squadra_id): f"{r.giocatore} · {r.squadra}"
            for r in pool.itertuples()}
    note_html("Scegli un giocatore: puoi scrivere parte del nome.")
    def scelto():
        k = st.session_state.get("pick_g")
        if k is not None:
            st.session_state["f_sq"], st.session_state["f_g"] = k[1], k
            st.session_state["pick_g"] = None
    st.selectbox("Giocatore", [None] + list(opts), key="pick_g", on_change=scelto,
                 format_func=lambda k: "Cerca…" if k is None else opts[k],
                 label_visibility="collapsed")


def prossima_avversaria(a: App) -> int | None:
    mia = a.utente.get("squadra_id")
    if mia is None:
        return None
    ng = a.ctx.next_game(mia)
    if not ng:
        return None
    avv = ng["ospite_id"] if ng["casa_id"] == mia else ng["casa_id"]
    return avv if avv in set(a.profile["squadra_id"]) else None


def imposta(**stato):
    """Callback dei pulsanti: imposta i filtri prima che la pagina venga ridisegnata."""
    for k, v in stato.items():
        st.session_state[k] = v


def pulsante(col, etichetta: str, pagina: str, primary: bool = False, **stato):
    """Pulsante che imposta i filtri e apre un'altra pagina."""
    if col.button(etichetta, type="primary" if primary else "secondary", width="stretch",
                  on_click=imposta, kwargs=stato, key=f"vai_{pagina}_{etichetta}"):
        st.switch_page(PAGINE[pagina])


# ------------------------------------------------------------------ Home

def home():
    a = APP
    mia = a.utente.get("squadra_id")
    if mia not in set(a.profile["squadra_id"]):
        mia = None
    brand_hero("La settimana dello staff",
               "Prossima avversaria, ultima partita, avvisi e report pronti da scaricare.")
    if a.utente.get("demo"):
        teams = a.profile.sort_values("squadra")
        nomi = dict(zip(teams["squadra_id"], teams["squadra"]))
        opts = [None] + list(nomi)
        # la scelta resta valida in tutte le pagine (lo stato dei widget non visibili
        # viene cancellato, quindi la si copia in una chiave propria)
        if st.session_state.get("mia_demo") not in opts:
            st.session_state["mia_demo"] = None
        st.session_state["w_mia"] = st.session_state.get("mia_demo")
        st.selectbox("La tua squadra (modalità demo: con gli accessi per club è impostata "
                     "automaticamente)", opts, key="w_mia",
                     on_change=lambda: st.session_state.update(
                         mia_demo=st.session_state["w_mia"]),
                     format_func=lambda s: "Scegli…" if s is None else nomi[s])
    if mia is None:
        note_html("Scegli la tua squadra per vedere la prossima avversaria, l'ultima partita e "
                  "gli avvisi della settimana.")
        _home_campionato(a)
        return

    pr = a.profile.set_index("squadra_id")
    me = pr.loc[mia]
    cl = schede.classifica(a)
    pos = cl.set_index("squadra_id")["pos"].get(mia)
    forma = (a.bs_c[a.bs_c["squadra_id"] == mia].sort_values(["data", "partita_id"])["vinta"]
             .tail(5).map({True: "V", False: "P", 1: "V", 0: "P"}).tolist())
    ng = a.ctx.next_game(mia)
    avv = prossima_avversaria(a)
    from basket import report_extra as R
    ultima = R.ultima_partita(a.ctx, mia)

    cards = []
    # prossima partita
    if ng:
        in_casa = ng["casa_id"] == mia
        nome_avv = ng["ospite"] if in_casa else ng["casa"]
        pv = ng.get("previsione")
        prob = (pv["prob_casa"] if in_casa else 1 - pv["prob_casa"]) if pv else None
        fis = analisi.fisico_prossima(a, ng)
        righe = [("Probabilità di vittoria",
                  num(100 * prob, 0, suffix="%") if prob is not None else "–"),
                 ("Punteggio atteso", f"{pv['punti_casa']:.0f}-{pv['punti_ospite']:.0f}"
                  if pv else "–")]
        if fis.get(mia, {}).get("giorni_riposo") is not None:
            righe.append(("Riposo", f"{fis[mia]['giorni_riposo']} giorni"))
        if not in_casa and fis.get(mia, {}).get("km"):
            righe.append(("Trasferta", f"{num(fis[mia]['km'], 0)} km"))
        chiave = ""
        if pv:
            from basket import previsioni as F
            try:
                sp = F.spiega(a.ctx.forze(ng["campionato_id"]), ng["casa_id"], ng["ospite_id"],
                              a.ctx.hca(ng["campionato_id"]))
                top = sp.iloc[0]
                v = top["probabilita"] if in_casa else -top["probabilita"]
                chiave = (f"<br>Fattore che pesa di più: <b>{esc(top['fattore'].lower())}</b> "
                          f"({num(v, 0, signed=True)}% per voi)")
            except KeyError:
                pass
        cards.append(_card("Prossima partita", f"vs {esc(nome_avv)}",
                           f"{ng['giornata']}ª giornata · {data_it(ng['data'])} "
                           f"{esc(ng['ora'] or '')} · {'in casa' if in_casa else 'in trasferta'}"
                           + chiave, righe))
    else:
        cards.append(_card("Prossima partita", "Calendario concluso", "", []))
    # ultima partita
    if ultima:
        try:
            r = R.riepilogo_partita(a.ctx, mia, ultima, a.archivio.goals(a.club))
            riga = r["riga"]
            cards.append(_card("Ultima partita",
                               f"{'V' if r['vinta'] else 'P'} {int(riga['punti'])}-"
                               f"{int(riga['punti_subiti'])} vs {esc(r['avversario'])}",
                               esc(it(" ".join(r["frasi"][:2]))), []))
        except ValueError:
            pass
    # la mia squadra
    righe = [("Record", f"{int(me['vinte'])}-{int(me['perse_partite'])}"),
             ("Classifica", f"{int(pos)}°" if pd.notna(pos) else "–"),
             ("Net rating", num(me["net_rtg"], 1, signed=True)),
             ("Forma", " ".join(forma) or "–")]
    cards.append(_card("La tua squadra", esc(me["squadra"]),
                       "Net rating " + badge_pos(X.posizione(pr["net_rtg"], mia)), righe))
    st.markdown(f'<div class="cards tre">{"".join(cards)}</div>', unsafe_allow_html=True)

    c = st.columns(4)
    if avv is not None:
        pulsante(c[0], "Scouting dell'avversaria", "scouting", primary=True, f_sq=avv)
        pulsante(c[1], "Anteprima della partita", "anteprima", f_sq=mia)
        with c[2]:
            st.download_button("⬇ PDF avversaria", nuove._pdf(a.ctx, a.mtime, a.stagione, avv, mia),
                               file_name=f"scouting_{analisi.slug(pr.loc[avv, 'squadra'])}.pdf",
                               mime="application/pdf", width="stretch")
    if ultima:
        with c[3]:
            st.download_button("⬇ PDF post-partita",
                               analisi.pdf_post_partita(a, mia, ultima),
                               file_name=f"post_partita_{analisi.slug(me['squadra'])}.pdf",
                               mime="application/pdf", width="stretch")

    if avv is not None:
        frase(f"La prossima avversaria in una frase · {short(pr.loc[avv, 'squadra'])}",
              X.frase_squadra(a.profile, avv))
    al = a.ctx.alerts
    if al is not None and not al.empty:
        mine = al[al["squadra_id"].isin([mia, avv])]
        if not mine.empty:
            section("Avvisi della settimana", "tua squadra e prossima avversaria")
            pills([f"{r.squadra} · {r.giocatore + ': ' if isinstance(r.giocatore, str) else ''}"
                   f"{r.testo}" for r in mine.head(8).itertuples()], "pos", "")
    pulsante(st.columns(4)[0], "Vai a La mia squadra →", "mia")


def _card(h: str, t: str, m: str, righe: list[tuple[str, str]]) -> str:
    row = "".join(f"<div><small>{esc(k)}</small><span class='big' style='font-size:1.5rem'>"
                  f"{esc(it(v))}</span></div>" for k, v in righe)
    return (f'<div class="card"><div class="h">{esc(h)}</div><div class="t">{t}</div>'
            f'<div class="m">{m}</div>' + (f'<div class="row">{row}</div>' if righe else "")
            + "</div>")


def _home_campionato(a: App):
    section("Il campionato in breve")
    cl = schede.classifica(a)
    top = cl.head(4)
    cards = []
    for r in top.itertuples():
        cards.append(_card(f"{r.pos}° posto", esc(r.squadra), "",
                           [("Record", f"{int(r.vinte)}-{int(r.perse_partite)}"),
                            ("Net rating", num(r.net_rtg, 1, signed=True))]))
    st.markdown(f'<div class="cards">{"".join(cards)}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ pagine delle aree

def p_scouting():
    a = APP
    if a.sq is None:
        titolo_pagina("Scouting", "report completo su una squadra")
        scegli_squadra(a, "Scegli la squadra da analizzare.")
        return
    schede.render_scouting(a)
    nuove.scouting_extra(a)


def p_anteprima():
    titolo_pagina("Anteprima", "probabilità, perché, scenari e chiavi della partita")
    nuove.render_anteprima(APP)


def p_proiezione():
    titolo_pagina("Proiezione della classifica", "dove può arrivare ogni squadra")
    previsioni_ui.render_proiezione(APP)


def p_affidabilita():
    titolo_pagina("Affidabilità delle previsioni")
    previsioni_ui.render_affidabilita(APP)


def p_squadre():
    titolo_pagina("Squadre", "tutte le squadre del campionato a confronto")
    schede.render_squadre(APP)


def p_giocatori():
    titolo_pagina("Giocatori", "medie, avanzate, ruolo, andamento")
    schede.render_giocatori(APP)


def p_giocatore():
    a = APP
    if a.gsel is None:
        titolo_pagina("Scheda giocatore")
        scegli_giocatore(a)
        return
    schede.render_giocatore(a)
    nuove.giocatore_extra(a)


def p_mercato():
    titolo_pagina("Mercato", "fabbisogni, ricerca, dalla B all'A2, giocatori simili")
    nuove.render_mercato(APP)


def p_mia():
    a = APP
    nuove.render_mia_squadra(a)
    analisi.ultima_partita(a)


def p_avvisi():
    titolo_pagina("Avvisi", "cosa è cambiato dopo l'ultima giornata")
    nuove.render_avvisi(APP)


def p_panoramica():
    titolo_pagina("Panoramica", "il campionato in numeri")
    schede.render_panoramica(APP)


def p_classifica():
    titolo_pagina("Classifica", "con forma, vittorie attese e forza del calendario")
    schede.render_classifica(APP)


def p_partite():
    titolo_pagina("Partite", "box score, statistiche avanzate, andamento")
    a = APP
    nuove.partita_extra(a, schede.render_partite(a))


def mappa() -> dict:
    def P(fn, titolo, url, chiave, default=False, icona=None):
        pg = st.Page(fn, title=titolo, url_path=url, default=default, icon=icona)
        PAGINE[chiave] = pg
        return pg
    return {
        "": [P(home, "Home", "home", "home", default=True, icona=":material/home:")],
        "Avversaria": [P(p_scouting, "Scouting", "scouting", "scouting"),
                       P(p_squadre, "Squadre", "squadre", "squadre")],
        "Previsioni": [P(p_anteprima, "Anteprima e scenari", "anteprima", "anteprima"),
                       P(p_proiezione, "Proiezione della classifica", "proiezione",
                         "proiezione"),
                       P(p_affidabilita, "Affidabilità delle previsioni", "affidabilita",
                         "affidabilita")],
        "Giocatori": [P(p_giocatori, "Elenco giocatori", "giocatori", "giocatori"),
                      P(p_giocatore, "Scheda giocatore", "giocatore", "giocatore"),
                      P(p_mercato, "Mercato", "mercato", "mercato")],
        "La mia squadra": [P(p_mia, "La mia squadra", "mia-squadra", "mia"),
                           P(p_avvisi, "Avvisi", "avvisi", "avvisi")],
        "Campionato": [P(p_panoramica, "Panoramica", "panoramica", "panoramica"),
                       P(p_classifica, "Classifica", "classifica", "classifica"),
                       P(p_partite, "Partite", "partite", "partite")],
    }
