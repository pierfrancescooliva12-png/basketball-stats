"""Piattaforma per i club di B Interregionale: scouting delle avversarie da template Excel, lavagna dei giochi e
lavagna sul video. Niente statistiche di A2 e B Nazionale: la piattaforma non ha i dati di questo campionato,
che arrivano dallo staff con i template compilati e restano privati del club (nell'archivio, mai nel codice o
sul sito pubblico).
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from basket import config
from basket import scouting_excel as SX
from basket.note import Archivio

from .ui import esc, note_html, pills, section, show, titolo_pagina, topbar

RUOLO = "interregionale"


@dataclass
class AppLibera:
    """Quanto serve alle pagine della lavagna, del video e della guida, senza i dati della Lega."""
    utente: dict
    archivio: Archivio
    tema: object = None
    esperto: bool = False

    @property
    def club(self) -> str:
        return self.utente.get("club") or f"admin:{self.utente.get('username')}"

    @property
    def autore(self) -> str:
        return self.utente.get("username", "")

    @property
    def mia_squadra(self):
        return None


A: AppLibera | None = None


def slug(nome: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "squadra"


# ------------------------------------------------------------------ archivio del club
def avversarie(a: AppLibera) -> list[dict]:
    return a.archivio.video_dati(a.club, "scout:elenco") or []


def salva_avversaria(a: AppLibera, nome: str) -> str:
    el, s = avversarie(a), slug(nome)
    if not any(x["slug"] == s for x in el):
        el.append({"slug": s, "nome": nome.strip()[:60]})
        a.archivio.set_video_dati(a.club, "scout:elenco", sorted(el, key=lambda x: x["nome"].lower()))
    return s


def scouting_di(a: AppLibera, s: str) -> dict | None:
    return a.archivio.video_dati(a.club, f"scout:{s}")


def altre_caricate(a: AppLibera, escluso: str) -> list[dict]:
    out = []
    for x in avversarie(a):
        if x["slug"] != escluso:
            d = scouting_di(a, x["slug"])
            if d and d.get("dati"):
                out.append(d["dati"])
    return out


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _rif_lnp(mtime: float) -> dict:
    from basket import db
    try:
        conn = db.connect(config.DB_PATH, readonly=True)
        stag = conn.execute("SELECT MAX(stagione) FROM partite").fetchone()[0]
        return SX.riferimento_lnp(conn, stag)
    except Exception:  # noqa: BLE001
        return {}


def _data(iso) -> str:
    s = str(iso or "")[:10]
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}" if len(s) == 10 else s


def _f(x, d=1, pct=False):
    if x is None or pd.isna(x):
        return "–"
    return f"{x:.{d}f}".replace(".", ",") + ("%" if pct else "")


# ------------------------------------------------------------------ pagina: scouting delle avversarie
def p_scouting():
    a = A
    titolo_pagina("Scouting avversarie", "carica le statistiche dell'avversaria con il template Excel: punti di forza e "
                  "punti deboli della squadra e dei giocatori")
    c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
    el = avversarie(a)
    nomi = {x["slug"]: x["nome"] for x in el}
    if "_ir_nuova" in st.session_state:          # avversaria appena aggiunta: si apre lei
        st.session_state["ir_avv"] = st.session_state.pop("_ir_nuova")
    scelta = c1.selectbox("Avversaria", [None] + list(nomi), key="ir_avv",
                          format_func=lambda s: "Scegli o aggiungi un'avversaria…" if s is None else nomi[s])
    c2.download_button("⬇ Template Excel da compilare", SX.template(), file_name="ASSIST_template_scouting.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
                       help="Fogli Squadra e Giocatori, con le istruzioni: medie a partita")
    with st.expander("＋ Aggiungi un'avversaria", expanded=not el):
        with st.form("ir_nuova", clear_on_submit=True):
            nome = st.text_input("Nome della squadra", placeholder="es. Stella Azzurra")
            if st.form_submit_button("Aggiungi", type="primary") and nome.strip():
                st.session_state["_ir_nuova"] = salva_avversaria(a, nome)
                st.rerun()
    if scelta is None:
        note_html("Scegli un'avversaria o aggiungila, poi scarica il template, compilalo con le medie a partita della "
                  "squadra e dei giocatori (per esempio dalle statistiche del campionato) e caricalo qui. ASSIST "
                  "calcola gli indici, li confronta con il riferimento e scrive i punti di forza e i punti deboli.")
        return
    nome = nomi[scelta]
    salvato = scouting_di(a, scelta) or {}
    file = st.file_uploader(f"Carica il template compilato di {nome}", type=["xlsx"], key=f"ir_file_{scelta}",
                            help="Il file viene letto e analizzato; si salvano i numeri, privati del club.")
    if file is not None and st.session_state.get(f"ir_letto_{scelta}") != file.file_id:
        try:
            dati = SX.leggi(file)
        except SX.ErroreTemplate as e:
            st.error(f"Il file non va bene: {e}.")
            return
        st.session_state[f"ir_letto_{scelta}"] = file.file_id
        salvato = {**salvato, "dati": dati, "caricato_il": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                   "da": a.autore}
        a.archivio.set_video_dati(a.club, f"scout:{scelta}", salvato)
        st.success(f"Dati di {nome} caricati: {len(dati['giocatori'])} giocatori.")
    d = salvato.get("dati")
    if not d:
        note_html(f"Nessun dato ancora per {nome}: scarica il template, compilalo e caricalo qui sopra.")
        _note_e_lavagna(a, scelta, nome, salvato)
        return
    ind = SX.indici_completi(d)
    import os
    mtime = os.path.getmtime(config.DB_PATH) if config.DB_PATH.exists() else 0.0
    rif, fonte = SX.riferimento(d, altre_caricate(a, scelta), _rif_lnp(mtime))
    forza, debole, tab = SX.giudizio_squadra(ind, rif)
    it = d.get("intestazione") or {}
    meta = " · ".join(x for x in [it.get("campionato"), it.get("girone") and f"girone {it['girone']}",
                                  it.get("aggiornato") and f"dati al {it['aggiornato']}"] if x)
    st.markdown(f'<div class="hero" style="padding:16px 20px"><div class="eyebrow">Scouting · {esc(meta or "B Interregionale")}'
                f'</div><div class="title" style="font-size:2rem">{esc(nome)}</div><div class="meta">caricato il '
                f'{esc(_data(salvato.get("caricato_il")))} · riferimento: {esc(fonte)}</div></div>',
                unsafe_allow_html=True)
    s = d["squadra"]
    from .ui import kpis
    kpis([("Punti a partita", _f(s.get("punti")), "segnati"),
          ("Punti per 100 possessi", _f(ind.get("ortg")), f"rif. {_f(rif.get('ortg'))}"),
          ("Ritmo", _f(ind.get("ritmo"), 0), "possessi a partita"),
          ("Tiro effettivo", _f(ind.get("efg"), 1, True), f"rif. {_f(rif.get('efg'), 1, True)}"),
          ("Palle perse", _f(ind.get("perse"), 1, True), "per possesso"),
          ("Subiti", _f((d.get("avversari") or {}).get("punti")), "a partita")])
    cf, cd = st.columns(2)
    with cf:
        section("Punti di forza")
        pills(forza, "pos", "Nessuno marcato")
    with cd:
        section("Punti deboli")
        pills(debole, "neg", "Nessuno marcato")
    n_part = (d.get("squadra") or {}).get("partite")
    if n_part and n_part < 6:
        note_html(f"Solo {int(n_part)} partite: i numeri cambiano molto da una partita all'altra, considerali indicativi.")
    st_ = SX.stile(ind, rif)
    if st_:
        note_html("Come gioca: " + "; ".join(st_) + ".")
    if not d.get("avversari"):
        note_html("Per l'analisi della difesa (tiro concesso, palle perse forzate, rimbalzi difensivi) compila anche la "
                  "colonna «Avversari (concessi)» del template.")
    if not tab.empty:
        section("Indici di squadra", f"confronto con il riferimento: {fonte}")
        show(tab.drop(columns=["Differenza"]), voci=[])
    gioc = SX.giocatori(d)
    if not gioc.empty:
        section("Giocatori chiave", "i più coinvolti nei possessi e i migliori realizzatori")
        for r in SX.chiave(gioc).itertuples():
            st.markdown(f"**{esc(r.numero)} {esc(r.nome)}** · {_f(r.minuti, 0)} minuti, {_f(r.punti)} punti, uso dei possessi "
                        f"{_f(r.uso, 0, True)}" + (f"  \n✅ {esc(r.forza)}" if r.forza else "") +
                        (f"  \n⚠️ {esc(r.debolezze)}" if r.debolezze else ""))
        section("Tutti i giocatori", "medie a partita; punti di forza e deboli dai numeri")
        out = pd.DataFrame({
            "N°": gioc["numero"], "Giocatore": gioc["nome"], "Ruolo": gioc["ruolo"], "Min": gioc["minuti"].round(1),
            "Punti": gioc["punti"].round(1), "Tiro reale %": gioc["ts"].round(1), "Da 3 %": gioc["p3"].round(1),
            "Liberi %": gioc["pl"].round(1), "Rimbalzi": gioc["rimbalzi"].round(1), "Assist": gioc["assist"].round(1),
            "Perse": gioc["perse"].round(1), "Uso %": gioc["uso"].round(1),
            "Punti di forza": gioc["forza"], "Punti deboli": gioc["debolezze"]})
        show(out, voci=[])
    _note_e_lavagna(a, scelta, nome, salvato, d=d, ind=ind, rif=rif, fonte=fonte, gioc=gioc)


def _note_e_lavagna(a, scelta, nome, salvato, d=None, ind=None, rif=None, fonte="", gioc=None):
    section("Note dello staff", "private del club")
    with st.form(f"ir_note_{scelta}"):
        testo = st.text_area("Note", value=salvato.get("note", ""), height=120, label_visibility="collapsed",
                             placeholder="Cosa avete visto in video, assenze, accorgimenti per la partita…")
        if st.form_submit_button("Salva le note"):
            salvato = {**(scouting_di(a, scelta) or {}), "note": testo}
            a.archivio.set_video_dati(a.club, f"scout:{scelta}", salvato)
            st.success("Note salvate.")
    if d is not None:
        st.download_button("⬇ Report PDF per la riunione tecnica",
                           SX.pdf(nome, a.club, d, ind, rif, fonte, gioc, salvato.get("note", "")),
                           file_name=f"scouting_{scelta}.pdf", mime="application/pdf", type="primary")
    from . import lavagna_ui
    section("Giochi dell'avversaria", "disegnati dallo staff sulla lavagna")
    with st.expander(f"Apri la lavagna per i giochi di {nome}"):
        lavagna_ui.render(a, f"m:{scelta}", "avversaria", f"Giochi di {nome}", nome)


# ------------------------------------------------------------------ altre pagine
def p_lavagna():
    a = A
    titolo_pagina("Lavagna", "i vostri giochi, fase per fase")
    from . import lavagna_ui
    lavagna_ui.render(a, "club", "nostro", f"Giochi di {a.utente.get('club')}", a.utente.get("club") or "")


def p_video():
    a = A
    titolo_pagina("Lavagna sul video", "le vostre segnalazioni sul video della partita, che resta sul dispositivo")
    from . import telestrator_ui
    telestrator_ui.render_libero(a, avversarie(a))


def p_guida():
    from . import guida
    guida.pagina(A, sezioni=guida.GUIDA_IR)


def _con_guida(fn, chiave):
    def pagina():
        fn()
        from . import guida
        guida.tour(A, chiave)
    pagina.__name__ = fn.__name__
    return pagina


def esegui(utente: dict, arch: Archivio):
    """Tutta la piattaforma per un utente di B Interregionale (al posto dei filtri e delle aree della Lega)."""
    global A
    A = AppLibera(utente=utente, archivio=arch)
    nav = st.navigation({"": [
        st.Page(_con_guida(p_scouting, "scouting_ir"), title="Scouting avversarie", url_path="scouting-avversarie",
                default=True, icon=":material/assignment:"),
        st.Page(_con_guida(p_lavagna, "lavagna"), title="Lavagna dei giochi", url_path="lavagna", icon=":material/draw:"),
        st.Page(_con_guida(p_video, "video_ir"), title="Lavagna sul video", url_path="video", icon=":material/videocam:"),
        st.Page(p_guida, title="Guida", url_path="guida", icon=":material/help:")]}, position="top")
    c1, c2 = st.columns([6, 1], vertical_alignment="center")
    with c1:
        topbar(f"B Interregionale · {esc(utente.get('club') or '')} · {esc(utente['username'])}")
    with c2:
        b1, b2 = st.columns(2)
        if utente.get("fonte") == "database" and b1.button("Password", key="cambia_pw", help="Cambia la tua password"):
            from . import accesso_ui
            accesso_ui.cambia_password(utente, arch)
        if b2.button("Esci", key="logout"):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
    nav.run()
