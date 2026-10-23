"""Lavagna sul video (telestrator): si apre un video dal dispositivo, lo si ferma e si disegna sul
fotogramma, come nelle trasmissioni NBA.

Il video non passa mai dal server: il componente lo apre nel browser (URL locale del file). Disegni,
momenti e azioni marcate vivono solo nella pagina aperta e spariscono quando la si chiude. Alla
piattaforma tornano soltanto, e solo su richiesta esplicita, gli inizi dei quarti nel video e i
giochi creati dalle posizioni toccate sul fotogramma.
"""

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from basket import tiri as T

from .stato import App, partite_df
from .ui import it, note_html

_lavagna_video = components.declare_component(
    "telestrator_assist", path=str(Path(__file__).resolve().parent / "telestrator"))

# azioni della cronaca mostrate nella lista (cambi e falli subiti restano fuori: sono rumore)
TESTI = {"tiro2_fatto": "Canestro da 2", "tiro2_sbagliato": "Tiro da 2 sbagliato",
         "tiro3_fatto": "Tripla segnata", "tiro3_sbagliato": "Tripla sbagliata",
         "tl_fatto": "Libero segnato", "tl_sbagliato": "Libero sbagliato",
         "persa": "Palla persa", "recupero": "Palla recuperata",
         "rimb_off": "Rimbalzo offensivo", "rimb_dif": "Rimbalzo difensivo",
         "assist": "Assist", "fallo": "Fallo", "fallo_tecnico": "Fallo tecnico",
         "stoppata": "Stoppata", "timeout": "Timeout"}


def _partite(a: App, sid: int) -> pd.DataFrame:
    """Partite giocate dalla squadra di cui c'è la cronaca, dalla più recente."""
    pg = partite_df(a.mtime, a.stagione)
    pg = pg[(pg["squadra_casa_id"] == sid) | (pg["squadra_ospite_id"] == sid)]
    con_cronaca = set(a.ctx.ev["partita_id"]) if not a.ctx.ev.empty else set()
    return pg[pg["partita_id"].isin(con_cronaca)].sort_values(["data", "giornata"], ascending=False)


def _etichetta(r) -> str:
    return (f"{r['giornata']}ª · {it(str(r['data'])[:10])} · {r['casa']} – {r['ospite']} "
            f"{r['punti_casa']}-{r['punti_ospite']}")


def eventi(a: App, pid: str) -> list[dict]:
    """Cronaca della partita nel formato del componente: periodo, secondi dall'inizio del periodo,
    tempo sul tabellone, testo, squadra, giocatore e punteggio."""
    ev = a.ctx.ev
    ev = ev[(ev["partita_id"] == pid) & ev["tipo"].isin(TESTI)].sort_values("n")
    nomi_g, nomi_s = a.ctx.nomi_giocatori, a.ctx.nomi_squadre
    out = []
    for r in ev.itertuples():
        p, s = int(r.periodo), float(r.secondi)
        g = r.giocatore_id if isinstance(r.giocatore_id, str) else None
        sq = nomi_s.get(r.squadra_id, "") if pd.notna(r.squadra_id) else ""
        out.append({"p": p, "s": round(s - T.inizio_periodo(p), 1), "cron": T.cronometro(p, s),
                    "tipo": r.tipo, "testo": TESTI[r.tipo], "sq": escape(sq),
                    "g": escape(nomi_g.get(g, "")) if g else "",
                    "pt": f"{int(r.punti_casa)}-{int(r.punti_ospite)}"
                    if pd.notna(r.punti_casa) and pd.notna(r.punti_ospite) else ""})
    return out


def _squadre(a: App, sid: int | None, partita: pd.Series | None) -> list[dict]:
    """Squadre a cui si può intestare il gioco creato: la propria per prima, poi le avversarie
    (quella della partita scelta, oppure tutte quelle del campionato)."""
    nomi = a.ctx.nomi_squadre
    if partita is not None:
        altre = [int(partita["squadra_casa_id"]), int(partita["squadra_ospite_id"])]
    else:
        pr = a.profile
        if "campionato_id" in pr:
            pr = pr[pr["campionato_id"] == a.camp]
        altre = sorted(pr["squadra_id"].astype(int), key=lambda x: nomi.get(x, ""))
    ids = ([sid] if sid else []) + [x for x in altre if x != sid]
    return [{"id": x, "nome": escape(nomi.get(x, str(x))), "mia": x == sid} for x in ids]


def render(a: App):
    note_html("Apri un video della partita o dell'allenamento: fermalo e disegna sul fotogramma (tagli, passaggi, "
              "blocchi, cerchi sotto i giocatori, riflettore, aree, testo). Ogni fermo-immagine disegnato diventa "
              "un momento della sessione. Sotto il video: marca le azioni con un tocco e rivedile in sequenza, "
              "salta alle azioni della cronaca, ingrandisci il fotogramma, trasforma le posizioni dei giocatori "
              "in un gioco della lavagna. Il video non viene caricato su ASSIST: disegni, momenti e azioni "
              "marcate spariscono chiudendo la pagina.")
    sid = a.mia_squadra
    pid, nome, partita = None, "", None
    if sid:
        pg = _partite(a, sid)
        if not pg.empty:
            scelte = [None] + list(pg["partita_id"])
            etichette = {r["partita_id"]: _etichetta(r) for _, r in pg.iterrows()}
            pid = st.selectbox("Partita del video (per la cronaca)", scelte, key="telestrator_partita",
                               format_func=lambda x: "Nessuna: solo disegno e azioni marcate" if x is None
                               else etichette[x])
            if pid:
                partita = pg[pg["partita_id"] == pid].iloc[0]
                nome = etichette[pid]
    valore = _lavagna_video(squadre=_squadre(a, sid, partita), partita_id=pid, partita_nome=escape(nome),
                            eventi=eventi(a, pid) if pid else [],
                            inizi=a.archivio.video_sync(a.club, pid) if pid else {},
                            esito=st.session_state.get("telestrator_esito"), key="telestrator", default=None)
    if isinstance(valore, dict) and valore.get("t") != st.session_state.get("telestrator_ultimo"):
        st.session_state["telestrator_ultimo"] = valore.get("t")
        if valore.get("azione") == "gioco" and isinstance(valore.get("gioco"), dict):
            a.archivio.save_play(a.club, int(valore["riferimento"]), valore["gioco"], a.autore)
            mia = str(valore["riferimento"]) == str(sid)
            st.session_state["telestrator_esito"] = {
                "t": valore["t"], "testo": "Gioco creato ✓ Lo trovi nella " +
                ("Lavagna dei vostri giochi." if mia else "lavagna dell'avversaria, nel suo scouting.")}
            st.rerun()
        elif valore.get("azione") == "sync" and valore.get("partita_id") == pid and pid:
            inizi = {int(k): float(v) for k, v in (valore.get("inizi") or {}).items() if v is not None}
            a.archivio.set_video_sync(a.club, pid, inizi)
            st.rerun()
    st.caption("Consiglio: sul telefono gira lo schermo in orizzontale; su computer usa lo schermo intero e la "
               "tastiera (spazio, frecce, Z, numeri 1–9 per marcare le azioni).")
