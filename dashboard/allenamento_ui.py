"""Programmi di allenamento (La mia squadra): dai numeri alla seduta stampata.

Lo staff parte dai suggerimenti (priorità della squadra, quintetti, carichi), sceglie giorni,
durata e aree, ottiene la bozza delle sedute e la modifica riga per riga; poi decide cosa
stampare nel PDF e salva il programma nell'archivio del club per riusarlo.
"""

import copy
import hashlib
import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from basket import allenamento as A
from basket import esercizi as E
from basket.report_allenamento import build_programma, nome_file

from .stato import App
from .ui import esc, note_html, section

CHIAVE = "allen_programma"
FASE_DA_NOME = {v: k for k, v in E.FASI.items()}
INCLUDI = {"obiettivi": "Obiettivi e priorità della settimana", "sedute": "Le sedute (una pagina ciascuna)",
           "esercizi": "Descrizione e punti chiave degli esercizi", "quintetti": "Quintetti e coppie su cui lavorare",
           "individuali": "Schede individuali da consegnare", "avversaria": "Preparazione della prossima partita",
           "carichi": "Gestione dei carichi (minuti recenti)", "giochi": "Giochi della lavagna",
           "presenze": "Foglio presenze e fatica (RPE)"}


def _inizio() -> date:
    """Oggi; nel fine settimana il lunedì dopo."""
    oggi = date.today()
    return oggi + timedelta(days=7 - oggi.weekday()) if oggi.weekday() >= 5 else oggi


def _versione() -> int:
    return st.session_state.get(f"{CHIAVE}_v", 0)


def _nuova_versione():
    st.session_state[f"{CHIAVE}_v"] = _versione() + 1


def _pdf(col, chiave: str, prog: dict, crea, primario: bool = False):
    """PDF in due tocchi: «Prepara il PDF» lo crea, «Scarica il PDF» lo scarica subito. Sui telefoni
    (Safari su iPhone) uno scaricamento che parte dopo l'attesa del server viene bloccato; così il
    tocco su «Scarica» trova il file già pronto. Se il programma cambia, il PDF si prepara di nuovo."""
    firma = hashlib.md5(json.dumps(prog, sort_keys=True, default=str).encode()).hexdigest()
    pronto = st.session_state.get(chiave)
    tipo = "primary" if primario else "secondary"
    if pronto and pronto[0] == firma:
        col.download_button("⬇ Scarica il PDF", pronto[1], file_name=nome_file(prog), mime="application/pdf",
                            type=tipo, on_click="ignore", use_container_width=True, key=f"{chiave}_dl")
    elif col.button("Prepara il PDF", type=tipo, use_container_width=True, key=f"{chiave}_prep"):
        with st.spinner("Preparo il PDF…"):
            st.session_state[chiave] = (firma, crea())
        st.rerun()


def _suggerimenti(a: App, sid: int):
    section("Cosa suggeriscono i numeri", "da dove partire per la settimana", key=None)
    pri = A.priorita_squadra(a.ctx, sid)
    q = A.quintetti(a.ctx, sid)
    ca = A.carichi(a.ctx, sid)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Priorità della squadra**")
        if pri:
            for p in pri:
                st.markdown(f"- **{esc(p['voce'])}** ({p['lato'].lower()}): {esc(p['ora'])} → {esc(p['obiettivo'])}, "
                            f"{esc(p['posizione'])}")
        else:
            st.caption("Nessuna voce dei Four Factors sotto la media.")
    with c2:
        st.markdown("**Quintetti**")
        if q.get("provare"):
            st.markdown(f"- Da provare: **{esc(q['provare']['giocatori'])}**")
        for x in q.get("consolidare", [])[:2]:
            st.markdown(f"- Da consolidare: {esc(x['giocatori'])} ({x['net']:+.0f} in {x['minuti']:.0f}')".replace(".", ","))
        for x in q.get("correggere", [])[:1]:
            st.markdown(f"- Da correggere: {esc(x['giocatori'])} ({x['net']:+.0f} in {x['minuti']:.0f}')".replace(".", ","))
        if not any(q.get(k) for k in ("provare", "consolidare", "correggere")):
            st.caption("Servono più partite con i quintetti verificati.")
    with c3:
        st.markdown("**Carichi**")
        if ca:
            for c in ca[:4]:
                st.markdown(f"- **{esc(c['nome'])}**: {c['recenti']:.0f}' di media nelle ultime partite "
                            f"(stagione {c['stagione']:.0f}')".replace(".", ","))
        else:
            st.caption("Nessun giocatore con minuti molto sopra la sua media nelle ultime partite.")
    return pri


def _crea(a: App, sid: int, pri: list[dict]):
    section("Il programma", "giorni, durata e aree: la bozza delle sedute la prepara la piattaforma", key=None)
    pl = a.ctx.players[a.ctx.players["squadra_id"] == sid].sort_values("minuti", ascending=False)
    nomi = dict(zip(pl["giocatore_id"], pl["giocatore"]))
    salvati = a.archivio.plays(a.club, sid)
    with st.form("allen_crea", border=False):
        c1, c2, c3 = st.columns([2, 1, 1])
        nome = c1.text_input("Nome del programma", value=f"Settimana dal {_inizio().strftime('%d/%m')}")
        tipo = c2.radio("Per", ["Squadra", "Individuale"], horizontal=True)
        dal = c3.date_input("Dal", value=_inizio(), format="DD/MM/YYYY")
        giocatori = st.multiselect("Giocatori (programma individuale o di reparto)", list(nomi),
                                   placeholder="Scegli i giocatori",
                                   format_func=lambda g: nomi.get(g, g))
        c1, c2, c3 = st.columns([2, 1, 1])
        giorni = c1.multiselect("Giorni di allenamento", list(range(7)), default=[0, 1, 3, 4],
                                format_func=lambda i: A.GIORNI[i])
        durata = c2.select_slider("Minuti per seduta", options=list(range(30, 151, 15)), value=90)
        inizio = c3.text_input("Ora di inizio", value="18:00")
        aree_pri = []
        for p in pri:
            aree_pri += [x for x in p["aree"] if x not in aree_pri]
        aree = st.multiselect("Aree di lavoro (in ordine di importanza)", list(E.AREE), default=aree_pri,
                              format_func=lambda k: E.AREE[k],
                              help="Proposte dalle priorità della squadra; per un programma individuale, se lasci "
                                   "vuoto, si usano le aree di miglioramento dei giocatori scelti.")
        giochi = st.multiselect("Giochi della lavagna da provare", [g["id"] for g in salvati],
                                format_func=lambda i: next((g.get("nome") or "Senza nome" for g in salvati
                                                            if g["id"] == i), i)) if salvati else []
        ok = st.form_submit_button("Prepara la bozza delle sedute", type="primary")
    if ok:
        if not giorni:
            st.warning("Scegli almeno un giorno di allenamento.")
            return
        individuale = tipo == "Individuale"
        if individuale and not giocatori:
            st.warning("Per un programma individuale scegli almeno un giocatore.")
            return
        st.session_state[CHIAVE] = A.nuovo_programma(
            a.ctx, sid, nome, dal, giorni, durata, "individuale" if individuale else "squadra",
            giocatori or None, aree or None, inizio, giochi)
        _nuova_versione()


def _seduta(prog: dict, i: int, s: dict):
    titolo = (f"Seduta {i + 1} · {A.giorno_it(s['giorno'])} · {s['durata']}' · intensità {s['intensita']}"
              + (f" · {s['etichetta']}" if s.get("etichetta") else ""))
    with st.expander(titolo, expanded=i == 0):
        c1, c2, c3 = st.columns([1, 1, 2])
        intensita = c1.selectbox("Intensità", list(E.INTENSITA), index=list(E.INTENSITA).index(s["intensita"]),
                                 key=f"allen_int_{i}_{_versione()}")
        s["inizio"] = c2.text_input("Inizio", value=s.get("inizio", ""), key=f"allen_ini_{i}_{_versione()}")
        s["obiettivo"] = c3.text_input("Obiettivo della seduta", value=s.get("obiettivo", ""),
                                       key=f"allen_obi_{i}_{_versione()}")
        df = pd.DataFrame([{"Fase": E.FASI.get(b["fase"], b["fase"]), "Esercizio": b["nome"],
                            "Minuti": int(b.get("minuti") or 0), "Gruppi": b.get("gruppi", ""),
                            "Note": b.get("note", "")} for b in s["blocchi"]])
        nomi = [e["nome"] for e in E.ESERCIZI]
        ed = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"allen_ed_{i}_{_versione()}",
            column_config={
                "Fase": st.column_config.SelectboxColumn("Fase", options=list(E.FASI.values()), required=True),
                "Esercizio": st.column_config.SelectboxColumn("Esercizio", options=nomi, required=True,
                                                              help="Dalla libreria; i dettagli nella scheda Libreria"),
                "Minuti": st.column_config.NumberColumn("Minuti", min_value=1, max_value=90, step=1, required=True),
                "Gruppi": st.column_config.TextColumn("Gruppi", help="Es. esterni / lunghi, 2 canestri, quintetti"),
                "Note": st.column_config.TextColumn("Note")})
        blocchi = []
        for r in ed.to_dict("records"):
            if not r.get("Esercizio"):
                continue
            e = E.PER_NOME.get(r["Esercizio"], {})
            blocchi.append({"fase": FASE_DA_NOME.get(r.get("Fase"), e.get("fase", "tecnica")),
                            "esercizio": e.get("id", ""), "nome": r["Esercizio"],
                            "minuti": int(r.get("Minuti") or e.get("durata", 10)),
                            "gruppi": r.get("Gruppi") or "", "note": r.get("Note") or ""})
        s["blocchi"] = blocchi
        tot = sum(b["minuti"] for b in blocchi)
        orari = A.orari(blocchi, s.get("inizio", ""))
        if orari:
            st.caption(f"Totale {tot}' su {s['durata']}' · fine alle {orari[-1].split('–')[-1]}"
                       if ":" in orari[-1] else f"Totale {tot}' su {s['durata']}'")
        if tot != s["durata"]:
            st.warning(f"Le righe sommano {tot} minuti: la seduta ne prevede {s['durata']}.")
        if intensita != s["intensita"] or st.button("Proponi altri esercizi", key=f"allen_rig_{i}_{_versione()}"):
            s["intensita"] = intensita
            s["obiettivo"] = A.OBIETTIVO_INTENSITA[intensita]
            quintetto = next((b["note"].replace("Quintetto: ", "") for b in blocchi if b["note"].startswith("Quintetto:")), "")
            s["blocchi"] = A.bozza_seduta(s["durata"], intensita, prog.get("aree") or ["tiro"],
                                          prog.get("tipo") == "individuale", {b["esercizio"] for b in blocchi},
                                          quintetto, bool(prog.get("giochi")))
            _nuova_versione()
            st.rerun()


def _programma(a: App, sid: int):
    prog = st.session_state.get(CHIAVE)
    if not prog:
        return
    section("Le sedute", "modifica esercizi, minuti, gruppi e note: le righe si aggiungono in fondo alla tabella",
            key=None)
    for i, s in enumerate(prog["sedute"]):
        _seduta(prog, i, s)

    section("Cosa stampare", "scegli le parti del PDF", key=None)
    cols = st.columns(3)
    for j, (k, lab) in enumerate(INCLUDI.items()):
        prog["includi"][k] = cols[j % 3].checkbox(lab, value=bool(prog["includi"].get(k)),
                                                  key=f"allen_inc_{k}_{_versione()}")
    prog["note"] = st.text_area("Note dello staff per la settimana", value=prog.get("note", ""),
                                key=f"allen_note_{_versione()}")
    giochi = a.archivio.plays(a.club, sid)
    c1, c2, c3, c4 = st.columns(4)
    _pdf(c1, "allen_pdf", prog, lambda: build_programma(a.ctx, sid, prog, giochi), primario=True)
    if c2.button("Salva nell'archivio", use_container_width=True):
        a.archivio.save_program(a.club, prog, a.autore)
        st.success("Programma salvato: lo trovi in «Programmi salvati».")
    if c3.button("Duplica per la settimana dopo", use_container_width=True):
        nuovo = copy.deepcopy(prog)
        nuovo["id"] = A.uuid.uuid4().hex[:12]
        nuovo["dal"] = (date.fromisoformat(prog["dal"]) + timedelta(days=7)).isoformat()
        nuovo["nome"] = f"{prog['nome']} (copia)"
        for s in nuovo["sedute"]:
            s["giorno"] = (date.fromisoformat(s["giorno"]) + timedelta(days=7)).isoformat()
        st.session_state[CHIAVE] = nuovo
        _nuova_versione()
        st.rerun()
    if c4.button("Chiudi il programma", use_container_width=True):
        st.session_state.pop(CHIAVE, None)
        st.rerun()
    if not a.archivio.permanente:
        note_html("Archivio di prova: i programmi restano finché l'app non viene riavviata.")


def _salvati(a: App, sid: int):
    programmi = [p for p in a.archivio.programs(a.club) if p.get("squadra_id") == sid]
    if not programmi:
        st.info("Nessun programma salvato. Preparane uno e premi «Salva nell'archivio».")
        return
    scelta = st.selectbox("Programma", range(len(programmi)),
                          format_func=lambda i: f"{programmi[i]['nome']} · dal {A.giorno_it(programmi[i]['dal'])} · "
                                                f"{len(programmi[i]['sedute'])} sedute")
    p = programmi[scelta]
    c1, c2, c3 = st.columns(3)
    if c1.button("Apri e modifica", type="primary", use_container_width=True):
        st.session_state[CHIAVE] = copy.deepcopy(p)
        _nuova_versione()
        st.rerun()
    _pdf(c2, "allen_pdf_salvato", p, lambda: build_programma(a.ctx, sid, p, a.archivio.plays(a.club, sid)))
    if c3.button("Elimina", use_container_width=True):
        a.archivio.delete_program(a.club, p["id"])
        st.rerun()


def _quanti(n: int) -> str:
    return "anche da soli" if n == 1 else f"da {n} giocatori"


def _libreria():
    c1, c2 = st.columns(2)
    fase = c1.selectbox("Fase", ["Tutte"] + list(E.FASI), format_func=lambda k: E.FASI.get(k, k))
    area = c2.selectbox("Area", ["Tutte"] + list(E.AREE), format_func=lambda k: E.AREE.get(k, k))
    for e in E.ESERCIZI:
        if fase != "Tutte" and e["fase"] != fase or area != "Tutte" and area not in e["aree"]:
            continue
        aree = ", ".join(E.AREE[x] for x in e["aree"])
        misura = f"<br><span style='opacity:.75'>Misura: {esc(e['misura'])}</span>" if e.get("misura") else ""
        st.markdown(f"<div class='card' style='margin-bottom:8px'><b>{esc(e['nome'])}</b> "
                    f"<span style='opacity:.7'>· {esc(E.FASI[e['fase']])} · {e['durata']}' · intensità "
                    f"{e['intensita']} · {_quanti(e['giocatori'])}</span><br>{esc(e['descrizione'])}<br>"
                    f"<span style='opacity:.75'>Punti chiave: {esc(' · '.join(e['punti']))}</span>{misura}"
                    f"<br><span style='opacity:.6;font-size:.85rem'>{esc(aree)}</span></div>",
                    unsafe_allow_html=True)


def render(a: App):
    sid = a.mia_squadra
    if sid is None:
        st.info("Scegli la tua squadra nella Home per preparare i programmi di allenamento.")
        return
    note_html("Dai numeri alla seduta: la piattaforma propone le aree su cui lavorare, gli esercizi e i quintetti; "
              "lo staff sceglie, modifica e stampa. L'intensità segue la distanza dalla partita: carico tre o più "
              "giorni prima, sviluppo due giorni prima, rifinitura il giorno prima.")
    t1, t2, t3 = st.tabs(["Prepara il programma", "Programmi salvati", "Libreria esercizi"])
    with t1:
        pri = _suggerimenti(a, sid)
        _crea(a, sid, pri)
        _programma(a, sid)
    with t2:
        _salvati(a, sid)
    with t3:
        _libreria()
