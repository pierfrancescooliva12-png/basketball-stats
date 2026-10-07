"""Mappa di tiro a zone e cronologia dei tiri (giocatore e singola partita)."""

import pandas as pd
import streamlit as st

from basket import tiri as T

from .stato import App, partite_df
from .ui import esc, it, note_html, num, section, show

SCELTE = {"tutti": "Tutti i tiri", "area_tot": "Area", "media": "Media distanza",
          "tre": "Da 3", "schiacciata": "Schiacciate"}


@st.cache_data(show_spinner="Preparo i tiri della stagione…")
def _tiri(_ctx, mtime: float, stagione: str) -> pd.DataFrame:
    return T.tiri(_ctx.ev)


def tiri_stagione(a: App) -> pd.DataFrame:
    return _tiri(a.ctx, a.mtime, a.stagione)


def _etichetta_partita(r) -> str:
    return f"{it(str(r['data'])[:10])} · {r['giornata']}ª giornata vs {r['avversario']}"


def mappa_e_cronologia(a: App, t: pd.DataFrame, lega: pd.DataFrame, chiave: str,
                       pid: str | None = None, partite: int | None = None):
    """Mappa a zone, scelta della zona e cronologia dei tiri. Con pid (una partita) anche la
    sincronizzazione con il video."""
    if t.empty:
        note_html("Nessun tiro registrato nella cronaca.")
        return
    r = T.confronto(t, lega, partite)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(T.svg_mappa(r, minimo=3 if pid else 8), unsafe_allow_html=True)
        note_html("Blu: percentuale sopra la media del campionato in quella zona. Arancio: sotto. "
                  "Grigio: troppo pochi tiri per giudicare.")
    with c2:
        rz = r.set_index("zona")
        righe = []
        for z in ("area_tot", "media", "tre"):
            x = rz.loc[z]
            righe.append({"Zona": SCELTE[z], "Segnati/tentati": f"{int(x.segnati)}/{int(x.tentati)}",
                          "%": num(x.pct, 0, suffix="%"), "Media campionato": num(x.pct_lega, 0, suffix="%"),
                          "Quota dei tiri": num(x.quota, 0, suffix="%"),
                          "Quota campionato": num(x.quota_lega, 0, suffix="%")})
        show(pd.DataFrame(righe), voci=[])
        zona = st.pills("Mostra la cronologia dei tiri", list(SCELTE), format_func=SCELTE.get,
                        default="tutti", key=f"zona_{chiave}")
    zona = zona or "tutti"
    sel = t if zona == "tutti" else \
        t[t["zona_mappa"].isin(["area", "schiacciata"] if zona == "area_tot" else [zona])]
    inizi = {}
    if pid:
        inizi = _sincronizza(a, pid)
    nomi = a.ctx.nomi_giocatori
    sel = sel.sort_values(["data", "partita_id", "n"]) if "data" in sel else sel
    tab = pd.DataFrame({
        **({"Partita": [f"{it(str(d)[:10])} vs {a.ctx.nomi_squadre.get(o, '')}"
                        for d, o in zip(sel["data"], sel["avversario_id"])]} if not pid else {}),
        "Quarto": [T.nome_periodo(int(p)) for p in sel["periodo"]],
        "Tempo": sel["tempo"],
        "Giocatore": [nomi.get(g, g) for g in sel["giocatore_id"]],
        "Tiro": [f"{'Segnato' if f else 'Sbagliato'} da {v}" for f, v in zip(sel["fatto"], sel["valore"])],
        "Zona": [SCELTE.get("area_tot" if z in ("area", "schiacciata") else z, z) for z in sel["zona_mappa"]],
        "Punteggio": sel["punteggio"],
        "Assist": [nomi.get(x, "") if isinstance(x, str) else "" for x in sel["assist_id"]],
    })
    if pid and inizi:
        tab["Video ≈"] = [T.hms(T.stima_video(int(p), s, inizi))
                          for p, s in zip(sel["periodo"], sel["secondi"])]
    st.markdown(f"**{len(sel)} tiri** · {esc(SCELTE[zona].lower())}. Il tempo è quello del "
                "tabellone (minuti e secondi alla fine del quarto).")
    show(tab, height=min(36 * (len(tab) + 1) + 4, 460), voci=[])


def _sincronizza(a: App, pid: str) -> dict:
    """Inizi dei quarti nel video, salvati per il club, e link alla partita su LNP Pass."""
    pg = partite_df(a.mtime, a.stagione)
    row = pg[pg["partita_id"] == pid]
    url = row.iloc[0].get("stream_url") if not row.empty else None
    inizi = a.archivio.video_sync(a.club, pid)
    with st.expander("Sincronizza con il video della partita" +
                     (" · fatto" if inizi else ""), expanded=False):
        note_html("Apri la partita su LNP Pass e scrivi il minuto del video in cui inizia ogni "
                  "quarto (per esempio 0:12:30). Nella cronologia compare il minuto stimato di ogni "
                  "tiro: si arriva entro pochi secondi, poi si usa il cronometro sul tabellone.")
        if isinstance(url, str) and url:
            st.link_button("▶ Apri la partita su LNP Pass", url)
        with st.form(f"sync_{pid}"):
            cols = st.columns(4)
            valori = {}
            for i, p in enumerate((1, 2, 3, 4)):
                valori[p] = cols[i].text_input(f"Inizio {p}° quarto", value=T.hms(inizi[p])
                                               if p in inizi else "", placeholder="0:12:30",
                                               key=f"sync_{pid}_{p}")
            if st.form_submit_button("Salva"):
                nuovi = {p: T.leggi_hms(v) for p, v in valori.items()}
                a.archivio.set_video_sync(a.club, pid, nuovi)
                st.rerun()
    return inizi


def render_giocatore(a: App, gid: str, sid: int):
    t_all = tiri_stagione(a)
    if t_all.empty:
        return
    t = t_all[(t_all["giocatore_id"] == gid) & (t_all["squadra_id"] == sid)]
    if t.empty:
        return
    camp = t["campionato_id"].iloc[0]
    lega = t_all[t_all["campionato_id"] == camp]
    section("Mappa di tiro", "dove tira e quanto segna, rispetto alla media del campionato; "
            "tocca una zona per la cronologia dei tiri", key="mappa_tiro")
    partite = t.drop_duplicates("partita_id").sort_values("data", ascending=False)
    opz = {None: f"Tutta la stagione ({len(partite)} partite)"}
    opz.update({r.partita_id: _etichetta_partita(
        {"data": r.data, "giornata": r.giornata, "avversario": a.ctx.nomi_squadre.get(r.avversario_id, "")})
        for r in partite.itertuples()})
    pid = st.selectbox("Periodo", list(opz), format_func=opz.get, key=f"mappa_p_{gid}")
    if pid:
        mappa_e_cronologia(a, t[t["partita_id"] == pid], lega, f"g_{gid}_{pid}", pid=pid)
    else:
        mappa_e_cronologia(a, t, lega, f"g_{gid}", partite=len(partite))


def render_partita(a: App, pid: str):
    t_all = tiri_stagione(a)
    t = t_all[t_all["partita_id"] == pid] if not t_all.empty else t_all
    if t.empty:
        return
    lega = t_all[t_all["campionato_id"] == t["campionato_id"].iloc[0]]
    section("Mappa di tiro della partita", "tocca una zona per la cronologia dei tiri e il "
            "momento nel video", key="mappa_tiro")
    nomi_sq = a.ctx.nomi_squadre
    squadre = list(dict.fromkeys(t["squadra_id"]))
    c1, c2 = st.columns(2)
    sq = c1.selectbox("Squadra", squadre, format_func=lambda s: nomi_sq.get(s, s),
                      key=f"mp_sq_{pid}")
    t = t[t["squadra_id"] == sq]
    nomi = a.ctx.nomi_giocatori
    gioc = [None] + list(t.groupby("giocatore_id").size().sort_values(ascending=False).index)
    g = c2.selectbox("Giocatore", gioc, format_func=lambda x: "Tutta la squadra" if x is None
                     else nomi.get(x, x), key=f"mp_g_{pid}_{sq}")
    if g:
        t = t[t["giocatore_id"] == g]
    mappa_e_cronologia(a, t, lega, f"p_{pid}_{sq}_{g}", pid=pid)
