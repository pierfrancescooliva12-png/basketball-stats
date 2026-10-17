"""Pagina Live: la partita della propria squadra in diretta, con suggerimenti per lo staff.

In diretta la cronaca si rilegge dal sito della lega ogni 30 secondi (una sola richiesta condivisa
tra tutti quelli che guardano). Senza partita in corso si può rivedere una partita giocata
fermandola a un minuto qualsiasi, come allenamento o per preparare i finali.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from basket import live
from basket import previsioni as F

from . import leverage_ui
from .stato import App
from .ui import esc, kpis, note_html, num, section, show

AGGIORNA = 30
COLORI = {3: "#ff6b5a", 2: "#ff9d2e", 1: "#9aa6b8"}
ETICHETTA = {3: "ADESSO", 2: "PRESTO", 1: "DA TENERE D'OCCHIO"}


@st.cache_data(ttl=AGGIORNA - 5, show_spinner=False)
def _cronaca(gameid: str, campionato: str, stagione: str) -> dict:
    return live.scarica(gameid, campionato, stagione)


def _attesa(a: App, camp, casa, osp) -> float:
    try:
        return F.predict(a.ctx.forze(camp), casa, osp, a.ctx.hca(camp))["margine"]
    except Exception:
        return 0.0


def _pct(v):
    """Rapporti salvati come frazione (0,2) mostrati come percentuale (20)."""
    return v * 100 if v is not None and v == v and v <= 1.5 else v


def _nomi(a: App) -> dict:
    bg = a.ctx.bg
    return bg.drop_duplicates("giocatore_id").set_index("giocatore_id")["giocatore"].to_dict() if not bg.empty else {}


def pannello(a: App, ev: pd.DataFrame, noi, nomi: dict, casa: str, ospite: str, attesa_casa: float, fonte: str):
    s = live.stato(ev, noi, attesa_casa, nomi)
    if s.get("vuota"):
        st.info("La partita non è ancora iniziata: la cronaca comparirà alla palla a due.")
        return
    loro = s["loro"]; sqn = {s["casa"]: casa, (loro if noi == s["casa"] else noi): ospite}
    nome_noi, nome_loro = sqn[noi], sqn[loro]
    per = s["periodo"]; m, sec = divmod(int(s["resta_periodo"]), 60)
    st.markdown(f'<div class="frase"><b>{esc(nome_noi)} {s["punti"][noi]} – {s["punti"][loro]} {esc(nome_loro)}</b>'
                f'<br>{per}° {"periodo" if per <= 4 else "supplementare"} · {m}:{sec:02d} da giocare · {esc(fonte)}</div>',
                unsafe_allow_html=True)
    f, fl = s["fattori"][noi], s["fattori"][loro]
    kpis([("Probabilità di vittoria", num(100 * s["wp"], 0, suffix="%"), "modello Leverage"),
          ("Parziale ultimi 3'", f"{s['parziale_3'][noi]}-{s['parziale_3'][loro]}",
           f"serie aperta: {max(s['serie'].values())} di {nome_noi if s['serie'][noi] else nome_loro}" if max(s['serie'].values()) else ""),
          ("Falli di squadra", f"{s['falli'][noi]} – {s['falli'][loro]}",
           ("voi in bonus · " if s["bonus"][noi] else "") + ("loro in bonus" if s["bonus"][loro] else "") or "nel periodo"),
          ("Timeout rimasti", f"{s['timeout'][noi]} – {s['timeout'][loro]}", "voi – loro")])
    # suggerimenti
    prof = a.ctx.profile.set_index("squadra_id")
    stag = {"noi": prof.loc[noi].to_dict() if noi in prof.index else {},
            "loro": prof.loc[loro].to_dict() if loro in prof.index else {}}
    sug = live.suggerimenti(s, stag, a.ctx.players[["giocatore_id", "punti_pg"]])
    section("Suggerimenti per lo staff", "dal punteggio, dai falli, dai parziali e dai numeri della stagione",
            key="live_suggerimenti")
    if not sug:
        note_html("Niente da segnalare in questo momento.")
    for x in sug[:8]:
        st.markdown(f'<div class="frase" style="border-left:4px solid {COLORI[x["urgenza"]]}">'
                    f'<b style="color:{COLORI[x["urgenza"]]};letter-spacing:.06em;font-size:.78rem">'
                    f'{ETICHETTA[x["urgenza"]]} · {esc(x["categoria"]).upper()}</b><br>{esc(x["testo"])}</div>',
                    unsafe_allow_html=True)
    # numeri della partita
    section("Four Factors in partita", "contro la media della vostra stagione")
    sn = stag["noi"]
    righe = pd.DataFrame([
        {"Fattore": "Tiro effettivo (eFG%)", nome_noi: f["efg"], nome_loro: fl["efg"],
         "Voi di solito": sn.get("efg_pct"), "Concedete di solito": sn.get("opp_efg_pct")},
        {"Fattore": "Palle perse (% dei possessi)", nome_noi: f["tov"], nome_loro: fl["tov"],
         "Voi di solito": sn.get("tov_pct"), "Concedete di solito": sn.get("opp_tov_pct")},
        {"Fattore": "Rimbalzi offensivi", nome_noi: float(f["rimb_off"]), nome_loro: float(fl["rimb_off"]),
         "Voi di solito": None, "Concedete di solito": None},
        {"Fattore": "Liberi segnati / tiri (FT rate)", nome_noi: f["ft_rate"], nome_loro: fl["ft_rate"],
         "Voi di solito": None, "Concedete di solito": _pct(sn.get("opp_ft_rate"))}])
    show(righe, voci=[])
    g = s["giocatori"].copy()
    g["Squadra"] = g["squadra_id"].map({noi: nome_noi, loro: nome_loro})
    g["Tiri"] = [f"{int(x)}/{int(y)}" for x, y in g[["fatti", "tentati"]].values]
    tab = g.sort_values(["squadra_id", "leverage"], ascending=[True, False])
    show(tab[["nome", "Squadra", "punti", "Tiri", "falli", "leverage"]].rename(columns={
        "nome": "Giocatore", "punti": "Punti", "falli": "Falli", "leverage": "Leverage"}),
        colori={"Leverage": True}, voci=[])
    e = s["eventi"]
    leverage_ui.grafico_probabilita(e, casa, ospite, None, 260)


def render(a: App):
    noi = a.mia_squadra
    if noi is None:
        st.info("Scegli la tua squadra nella Home per seguire la sua partita in diretta.")
        return
    nomi = _nomi(a)
    modo = st.radio("Partita", ["In diretta", "Rivedi una partita giocata"], horizontal=True, key="live_modo")
    if modo == "In diretta":
        oggi = date.today()
        pg = pd.concat([live.partite_di_oggi(a.ctx.conn, a.stagione, (oggi - timedelta(days=d)).isoformat())
                        for d in (0, 1)])
        pg = pg[(pg["squadra_casa_id"] == noi) | (pg["squadra_ospite_id"] == noi)]
        if pg.empty:
            ng = a.ctx.next_game(noi)
            st.info("Oggi la vostra squadra non gioca." + (
                f" Prossima partita: {ng['casa']} – {ng['ospite']}, {pd.Timestamp(ng['data']).strftime('%d/%m')}"
                f"{' alle ' + ng['ora'] if ng.get('ora') else ''}." if ng else "")
                + " Intanto puoi rivedere una partita giocata.")
            return
        r = pg.iloc[0]

        @st.fragment(run_every=AGGIORNA)
        def diretta():
            try:
                cr = _cronaca(r.gameid, r.campionato_id, r.stagione)
            except Exception as e:                                  # noqa: BLE001 (sito non raggiungibile)
                st.warning(f"Cronaca non disponibile in questo momento ({type(e).__name__}): riprovo tra {AGGIORNA} secondi.")
                return
            ev = live.da_cronaca(cr, r.squadra_casa_id, r.squadra_ospite_id, r.partita_id)
            nomi_l = {**nomi, **cr.get("nomi", {})}
            pannello(a, ev, noi, nomi_l, r.casa, r.ospite, _attesa(a, r.campionato_id, r.squadra_casa_id, r.squadra_ospite_id),
                     f"aggiornato ogni {AGGIORNA} secondi")
        diretta()
        return
    # rivedere una partita giocata
    ev_all = a.ctx.ev
    mie = ev_all[(ev_all["squadra_casa_id"] == noi) | (ev_all["squadra_ospite_id"] == noi)]
    if mie.empty:
        st.info("Nessuna partita con la cronaca per la vostra squadra in questa stagione.")
        return
    part = mie.drop_duplicates("partita_id").sort_values("data", ascending=False)
    sqn = a.ctx.nomi_squadre
    labels = {p.partita_id: f"G{p.giornata} · {sqn.get(p.squadra_casa_id)} – {sqn.get(p.squadra_ospite_id)}"
              for p in part.itertuples()}
    pid = st.selectbox("Partita", list(labels), format_func=labels.get, key="live_rivedi")
    e = mie[mie["partita_id"] == pid]
    casa, osp = e["squadra_casa_id"].iloc[0], e["squadra_ospite_id"].iloc[0]
    durata = int(e["secondi"].max())
    t = st.slider("Minuto della partita", 0.0, durata / 60, min(36.0, durata / 60), 0.25, key=f"live_t_{pid}",
                  format="%.2f'")
    cols = ["n", "periodo", "secondi", "squadra_id", "giocatore_id", "tipo", "zona", "di_squadra",
            "punti_casa", "punti_ospite"]
    ev = live.normalizza(e[cols], casa, osp, pid)
    pannello(a, live.fino_a(ev, t * 60), noi, nomi, sqn.get(casa), sqn.get(osp),
             _attesa(a, e["campionato_id"].iloc[0], casa, osp), "partita rivista come se fosse in diretta")
