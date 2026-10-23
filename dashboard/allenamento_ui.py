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


PARTENZE = {"dati": "Bozza dai numeri (esercizi scelti per le priorità)",
            "modello": "Modello predefinito", "vuoto": "Da zero: sedute vuote da riempire"}


def _crea(a: App, sid: int, pri: list[dict], club_es: list[dict]):
    section("Il programma", "parti dai numeri, da un modello o da zero: poi ogni campo si modifica", key=None)
    pl = a.ctx.players[a.ctx.players["squadra_id"] == sid].sort_values("minuti", ascending=False)
    nomi = dict(zip(pl["giocatore_id"], pl["giocatore"]))
    salvati = a.archivio.plays(a.club, sid)
    with st.form("allen_crea", border=False):
        c1, c2, c3 = st.columns([2, 1, 1])
        nome = c1.text_input("Nome del programma", value=f"Settimana dal {_inizio().strftime('%d/%m')}")
        tipo = c2.radio("Per", ["Squadra", "Individuale"], horizontal=True)
        dal = c3.date_input("Dal", value=_inizio(), format="DD/MM/YYYY")
        c1, c2 = st.columns([2, 1])
        partenza = c1.radio("Come partire", list(PARTENZE), format_func=PARTENZE.get, horizontal=True)
        modello = c2.selectbox("Modello (se scegli «Modello predefinito»)", list(A.MODELLI))
        giocatori = st.multiselect("Giocatori (programma individuale o di reparto)", list(nomi),
                                   placeholder="Scegli i giocatori",
                                   format_func=lambda g: nomi.get(g, g))
        c1, c2, c3 = st.columns([2, 1, 1])
        giorni = c1.multiselect("Giorni di allenamento", list(range(7)), default=[0, 1, 3, 4],
                                format_func=lambda i: A.GIORNI[i])
        durata = c2.number_input("Minuti per seduta", min_value=15, max_value=240, value=90, step=5)
        inizio = c3.text_input("Ora di inizio", value="18:00")
        aree_pri = []
        for p in pri:
            aree_pri += [x for x in p["aree"] if x not in aree_pri]
        aree = st.multiselect("Aree di lavoro (in ordine di importanza)", list(E.AREE), default=aree_pri,
                              format_func=lambda k: E.AREE[k], placeholder="Scegli le aree",
                              help="Proposte dalle priorità della squadra; servono alla bozza dai numeri. Per un "
                                   "programma individuale, se lasci vuoto, si usano le aree dei giocatori scelti.")
        giochi = st.multiselect("Giochi della lavagna da provare", [g["id"] for g in salvati],
                                placeholder="Scegli i giochi",
                                format_func=lambda i: next((g.get("nome") or "Senza nome" for g in salvati
                                                            if g["id"] == i), i)) if salvati else []
        ok = st.form_submit_button("Crea il programma", type="primary")
    if ok:
        if not giorni:
            st.warning("Scegli almeno un giorno di allenamento (le altre sedute si aggiungono dopo).")
            return
        individuale = tipo == "Individuale"
        if individuale and not giocatori:
            st.warning("Per un programma individuale scegli almeno un giocatore.")
            return
        st.session_state[CHIAVE] = A.nuovo_programma(
            a.ctx, sid, nome, dal, giorni, int(durata), "individuale" if individuale else "squadra",
            giocatori or None, aree or None, inizio, giochi,
            partenza=modello if partenza == "modello" else partenza, extra=club_es)
        _nuova_versione()


def _fase_txt(fase: str) -> str:
    return E.FASI.get(fase, fase or "")


def _seduta(prog: dict, i: int, s: dict, club_es: list[dict]):
    v = _versione()
    cat = E.catalogo(club_es)
    per_nome = {e["nome"]: e for e in cat.values()}
    titolo = " · ".join(x for x in (f"Seduta {i + 1}", A.giorno_it(s["giorno"]), f"{s.get('durata', 0)}'",
                                     f"intensità {s.get('intensita', '')}", s.get("etichetta", ""), s.get("luogo", ""))
                        if x)
    with st.expander(titolo, expanded=i == 0):
        c = st.columns([1.3, 1, 1, 0.8, 0.8, 1.4])
        try:
            giorno = date.fromisoformat(s["giorno"])
        except (TypeError, ValueError):
            giorno = date.today()
        s["giorno"] = c[0].date_input("Data", value=giorno, format="DD/MM/YYYY", key=f"allen_g_{i}_{v}").isoformat()
        s["etichetta"] = c[1].text_input("Etichetta", value=s.get("etichetta", ""), placeholder="es. MD-2",
                                         key=f"allen_et_{i}_{v}")
        s["intensita"] = c[2].selectbox("Intensità", list(E.INTENSITA),
                                        index=list(E.INTENSITA).index(s.get("intensita", "media")),
                                        key=f"allen_int_{i}_{v}")
        s["durata"] = int(c[3].number_input("Minuti", min_value=10, max_value=300, value=int(s.get("durata") or 90),
                                            step=5, key=f"allen_dur_{i}_{v}"))
        s["inizio"] = c[4].text_input("Inizio", value=s.get("inizio", ""), placeholder="18:00", key=f"allen_ini_{i}_{v}")
        s["luogo"] = c[5].text_input("Luogo", value=s.get("luogo", ""), placeholder="Palestra, campo",
                                     key=f"allen_luo_{i}_{v}")
        s["obiettivo"] = st.text_input("Obiettivo della seduta", value=s.get("obiettivo", ""),
                                       placeholder="Cosa deve lasciare questa seduta", key=f"allen_obi_{i}_{v}")
        df = pd.DataFrame([{"Fase": _fase_txt(b.get("fase")), "Esercizio": b.get("nome", ""),
                            "Minuti": int(b.get("minuti") or 0), "Gruppi": b.get("gruppi", ""),
                            "Dettagli": b.get("dettagli", ""), "Note": b.get("note", "")} for b in s["blocchi"]],
                          columns=["Fase", "Esercizio", "Minuti", "Gruppi", "Dettagli", "Note"])
        ed = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"allen_ed_{i}_{v}",
            column_config={
                "Fase": st.column_config.TextColumn("Fase", help="Una fase standard (Riscaldamento, Tecnica "
                                                    "individuale, …) o una vostra: scrivetela come volete"),
                "Esercizio": st.column_config.TextColumn("Esercizio", help="Dalla libreria o scritto da voi"),
                "Minuti": st.column_config.NumberColumn("Minuti", min_value=0, max_value=180, step=1),
                "Gruppi": st.column_config.TextColumn("Gruppi", help="Es. esterni / lunghi, 2 canestri, quintetti"),
                "Dettagli": st.column_config.TextColumn("Dettagli", help="Descrizione e punti chiave vostri: nel PDF "
                                                        "prendono il posto di quelli della libreria"),
                "Note": st.column_config.TextColumn("Note")})
        blocchi = []
        for r in ed.to_dict("records"):
            nome = str(r.get("Esercizio") or "").strip()
            fase_t = str(r.get("Fase") or "").strip()
            if not nome and not fase_t:
                continue
            e = per_nome.get(nome, {})
            minuti = r.get("Minuti")
            blocchi.append({"fase": FASE_DA_NOME.get(fase_t, fase_t or e.get("fase", "")), "esercizio": e.get("id", ""),
                            "nome": nome or fase_t, "minuti": int(minuti) if minuti == minuti and minuti is not None else 0,
                            "gruppi": r.get("Gruppi") or "", "dettagli": r.get("Dettagli") or "", "note": r.get("Note") or ""})
        s["blocchi"] = blocchi
        tot = sum(b["minuti"] for b in blocchi)
        orari = A.orari(blocchi, s.get("inizio", ""))
        if orari:
            st.caption(f"Totale {tot}' su {s['durata']}'" + (f" · fine alle {orari[-1].split('–')[-1]}"
                                                            if ":" in orari[-1] else ""))
            if tot != s["durata"]:
                st.warning(f"Le righe sommano {tot} minuti: la seduta ne prevede {s['durata']}.")
        else:
            st.caption("Seduta vuota: scrivi le righe nella tabella o aggiungile dalla libreria qui sotto.")

        # aggiungere una riga dalla libreria (esercizi del club per primi)
        fasi_prog = [x for x in dict.fromkeys(_fase_txt(b.get("fase")) for se in prog["sedute"] for b in se["blocchi"])
                     if x and x not in E.FASI.values()]
        c = st.columns([1.2, 2, 0.7, 1])
        fase_scelta = c[0].selectbox("Fase", ["Quella dell'esercizio"] + list(E.FASI.values()) + fasi_prog,
                                     key=f"allen_af_{i}_{v}")
        opzioni = [e["id"] for e in club_es] + [e["id"] for e in E.ESERCIZI]
        es_id = c[1].selectbox("Esercizio dalla libreria", opzioni, key=f"allen_ae_{i}_{v}",
                               format_func=lambda k: (("★ " if cat[k].get("club") else "") + cat[k]["nome"] + " · "
                                                      + _fase_txt(cat[k].get("fase"))))
        minuti_n = c[2].number_input("Minuti", min_value=1, max_value=180, value=int(cat[es_id].get("durata", 10)),
                                     key=f"allen_am_{i}_{v}_{es_id}")
        c[3].markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if c[3].button("+ Aggiungi riga", key=f"allen_add_{i}_{v}", use_container_width=True):
            e = cat[es_id]
            s["blocchi"].append({"fase": e.get("fase", "") if fase_scelta == "Quella dell'esercizio"
                                 else FASE_DA_NOME.get(fase_scelta, fase_scelta),
                                 "esercizio": e["id"], "nome": e["nome"], "minuti": int(minuti_n), "gruppi": "",
                                 "dettagli": "", "note": ""})
            _nuova_versione()
            st.rerun()

        # azioni sulla seduta
        c = st.columns([1.4, 1, 1, 0.8, 0.8, 0.9])
        modello = c[0].selectbox("Modello", list(A.MODELLI), key=f"allen_mod_{i}_{v}", label_visibility="collapsed")
        azione = None
        if c[1].button("Applica il modello", key=f"allen_am2_{i}_{v}", use_container_width=True):
            s["intensita"], s["blocchi"] = A.da_modello(modello, s["durata"])
            s["obiettivo"] = s.get("obiettivo") or A.OBIETTIVO_INTENSITA[s["intensita"]]
            azione = True
        if c[2].button("Proponi dai numeri", key=f"allen_rig_{i}_{v}", use_container_width=True):
            quintetto = next((b["note"].replace("Quintetto: ", "") for b in blocchi
                              if str(b.get("note", "")).startswith("Quintetto:")), "")
            s["blocchi"] = A.bozza_seduta(s["durata"], s["intensita"], prog.get("aree") or ["tiro"],
                                          prog.get("tipo") == "individuale", {b["esercizio"] for b in blocchi},
                                          quintetto, bool(prog.get("giochi")), club_es)
            azione = True
        if c[3].button("Svuota", key=f"allen_svu_{i}_{v}", use_container_width=True):
            s["blocchi"] = []
            azione = True
        if c[4].button("Duplica", key=f"allen_dup_{i}_{v}", use_container_width=True):
            copia = copy.deepcopy(s)
            copia["giorno"] = (date.fromisoformat(s["giorno"]) + timedelta(days=1)).isoformat()
            prog["sedute"].insert(i + 1, copia)
            azione = True
        if c[5].button("Elimina", key=f"allen_del_{i}_{v}", use_container_width=True):
            prog["sedute"].pop(i)
            azione = True
        if azione:
            _nuova_versione()
            st.rerun()


def _dati_programma(a: App, prog: dict):
    v = _versione()
    with st.expander("Dati del programma: nome, date, partita di riferimento, aree", expanded=False):
        c1, c2 = st.columns([2, 1])
        prog["nome"] = c1.text_input("Nome", value=prog.get("nome", ""), key=f"allen_pn_{v}")
        try:
            dal = date.fromisoformat(prog.get("dal", ""))
        except ValueError:
            dal = date.today()
        prog["dal"] = c2.date_input("Dal", value=dal, format="DD/MM/YYYY", key=f"allen_pd_{v}").isoformat()
        p = prog.get("partita") or {}
        c1, c2, c3 = st.columns([1, 2, 1])
        con = c1.checkbox("Partita di riferimento", value=bool(p), key=f"allen_pp_{v}")
        if con:
            try:
                gd = date.fromisoformat(p.get("data", ""))
            except ValueError:
                gd = dal + timedelta(days=6)
            gd = c3.date_input("Data della partita", value=gd, format="DD/MM/YYYY", key=f"allen_pg_{v}")
            mia = a.ctx.nomi_squadre.get(prog["squadra_id"], "")
            avv_attuale = p.get("ospite") if p.get("casa") == mia else p.get("casa")
            avv = c2.text_input("Avversaria", value=avv_attuale or "", key=f"allen_pa_{v}")
            casa = st.radio("Si gioca", ["in casa", "in trasferta"], horizontal=True,
                            index=0 if p.get("casa", mia) == mia else 1, key=f"allen_pc_{v}")
            prog["partita"] = {"data": gd.isoformat(), "casa": mia if casa == "in casa" else avv,
                               "ospite": avv if casa == "in casa" else mia}
            if st.button("Ricalcola le etichette delle sedute (MD-1, MD-2…)", key=f"allen_md_{v}"):
                for s in prog["sedute"]:
                    s["etichetta"], _ = A.microciclo(date.fromisoformat(s["giorno"]), gd)
                _nuova_versione()
                st.rerun()
        else:
            prog["partita"] = None
        prog["aree"] = st.multiselect("Aree di lavoro", list(E.AREE), default=[x for x in prog.get("aree", []) if x in E.AREE],
                                      format_func=lambda k: E.AREE[k], key=f"allen_par_{v}",
                                      help="Usate da «Proponi dai numeri» e stampate negli obiettivi")


def _programma(a: App, sid: int, club_es: list[dict]):
    prog = st.session_state.get(CHIAVE)
    if not prog:
        return
    prog["esercizi_club"] = club_es           # i dettagli degli esercizi del club finiscono nel PDF
    _dati_programma(a, prog)
    section("Le sedute", "ogni campo si modifica; nella tabella le righe si aggiungono in fondo e si eliminano "
            "selezionandole", key=None)
    for i, s in enumerate(prog["sedute"]):
        _seduta(prog, i, s, club_es)
    c = st.columns([1.2, 2, 1])
    ultimo = max((date.fromisoformat(s["giorno"]) for s in prog["sedute"]), default=date.fromisoformat(prog["dal"]))
    giorno = c[0].date_input("Nuova seduta il", value=ultimo + timedelta(days=1), format="DD/MM/YYYY",
                             key=f"allen_ng_{_versione()}")
    come = c[1].selectbox("Parti da", ["Seduta vuota"] + [f"Modello: {m}" for m in A.MODELLI] + ["Bozza dai numeri"],
                          key=f"allen_nc_{_versione()}")
    c[2].markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if c[2].button("+ Aggiungi seduta", key=f"allen_ns_{_versione()}", use_container_width=True):
        durata = prog["sedute"][-1]["durata"] if prog["sedute"] else 90
        inizio = prog["sedute"][-1].get("inizio", "18:00") if prog["sedute"] else "18:00"
        nuova = A.seduta_vuota(giorno, durata, inizio)
        if come.startswith("Modello: "):
            nuova["intensita"], nuova["blocchi"] = A.da_modello(come.replace("Modello: ", ""), durata)
            nuova["obiettivo"] = A.OBIETTIVO_INTENSITA[nuova["intensita"]]
        elif come == "Bozza dai numeri":
            nuova["blocchi"] = A.bozza_seduta(durata, "media", prog.get("aree") or ["tiro"],
                                              prog.get("tipo") == "individuale", extra=club_es)
            nuova["obiettivo"] = A.OBIETTIVO_INTENSITA["media"]
        if prog.get("partita"):
            nuova["etichetta"], _ = A.microciclo(giorno, date.fromisoformat(prog["partita"]["data"]))
        prog["sedute"].append(nuova)
        prog["sedute"].sort(key=lambda x: x["giorno"])
        _nuova_versione()
        st.rerun()

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
        if nuovo.get("partita"):
            nuovo["partita"] = None           # la partita della settimana dopo è un'altra
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


def _scheda_esercizio(e: dict) -> str:
    aree = ", ".join(E.AREE.get(x, x) for x in e.get("aree", []))
    misura = f"<br><span style='opacity:.75'>Misura: {esc(e['misura'])}</span>" if e.get("misura") else ""
    punti = (f"<br><span style='opacity:.75'>Punti chiave: {esc(' · '.join(e['punti']))}</span>"
             if e.get("punti") else "")
    return (f"<div class='card' style='margin-bottom:8px'><b>{'★ ' if e.get('club') else ''}{esc(e['nome'])}</b> "
            f"<span style='opacity:.7'>· {esc(_fase_txt(e.get('fase')))} · {e.get('durata', '')}' · intensità "
            f"{e.get('intensita', '')} · {_quanti(int(e.get('giocatori') or 1))}</span><br>{esc(e.get('descrizione', ''))}"
            f"{punti}{misura}<br><span style='opacity:.6;font-size:.85rem'>{esc(aree)}</span></div>")


def _esercizi_club(a: App, club_es: list[dict]):
    section("Gli esercizi del club", "create i vostri: finiscono nella libreria, nelle bozze delle sedute e nel PDF",
            key=None)
    per_id = {e["id"]: e for e in club_es}
    scelta = st.selectbox("Esercizio", ["nuovo"] + list(per_id), key="allen_ec_scelta",
                          format_func=lambda k: "+ Nuovo esercizio" if k == "nuovo" else per_id[k]["nome"])
    e = per_id.get(scelta, {})
    fasi = list(E.FASI.values())
    fase_e = _fase_txt(e.get("fase", "tecnica"))
    with st.form(f"allen_ec_{scelta}", border=True):
        c1, c2 = st.columns([2, 1])
        nome = c1.text_input("Nome", value=e.get("nome", ""))
        fase = c2.selectbox("Fase", fasi + ["Altra fase…"], index=fasi.index(fase_e) if fase_e in fasi else len(fasi))
        fase_libera = c2.text_input("Altra fase (se l'hai scelta)", value="" if fase_e in fasi else fase_e)
        aree = st.multiselect("Aree di lavoro", list(E.AREE), default=[x for x in e.get("aree", []) if x in E.AREE],
                              format_func=lambda k: E.AREE[k], placeholder="Scegli le aree")
        c1, c2, c3 = st.columns(3)
        durata = c1.number_input("Minuti tipici", min_value=1, max_value=120, value=int(e.get("durata", 10)))
        intensita = c2.selectbox("Intensità", list(E.INTENSITA),
                                 index=list(E.INTENSITA).index(e.get("intensita", "media")))
        giocatori = c3.number_input("Giocatori minimi", min_value=1, max_value=20, value=int(e.get("giocatori", 1)))
        descrizione = st.text_area("Descrizione", value=e.get("descrizione", ""))
        punti = st.text_area("Punti chiave (uno per riga)", value="\n".join(e.get("punti", [])))
        misura = st.text_input("Come misurarlo (facoltativo)", value=e.get("misura", ""),
                               placeholder="es. canestri su 20 tiri")
        c1, c2 = st.columns(2)
        salva = c1.form_submit_button("Salva l'esercizio", type="primary")
        elimina = c2.form_submit_button("Elimina", disabled=not e)
    if salva:
        if not nome.strip():
            st.warning("Dai un nome all'esercizio.")
            return
        fase_k = FASE_DA_NOME.get(fase, fase) if fase != "Altra fase…" else (fase_libera.strip() or "Altro")
        a.archivio.save_exercise(a.club, E.nuovo_esercizio(nome, fase_k, aree, durata, intensita, giocatori,
                                                           descrizione, punti.splitlines(), misura,
                                                           id_=e.get("id")), a.autore)
        st.success("Esercizio salvato.")
        st.rerun()
    if elimina and e:
        a.archivio.delete_exercise(a.club, e["id"])
        st.rerun()


def _libreria(a: App, club_es: list[dict]):
    _esercizi_club(a, club_es)
    section("La libreria", "★ gli esercizi del club", key=None)
    fasi_extra = [x for x in dict.fromkeys(e.get("fase") for e in club_es) if x and x not in E.FASI]
    c1, c2 = st.columns(2)
    fase = c1.selectbox("Fase", ["Tutte"] + list(E.FASI) + fasi_extra, format_func=lambda k: E.FASI.get(k, k))
    area = c2.selectbox("Area", ["Tutte"] + list(E.AREE), format_func=lambda k: E.AREE.get(k, k))
    for e in club_es + E.ESERCIZI:
        if fase != "Tutte" and e.get("fase") != fase or area != "Tutte" and area not in e.get("aree", []):
            continue
        st.markdown(_scheda_esercizio(e), unsafe_allow_html=True)


def render(a: App):
    sid = a.mia_squadra
    if sid is None:
        st.info("Scegli la tua squadra nella Home per preparare i programmi di allenamento.")
        return
    note_html("Dai numeri alla seduta: la piattaforma propone le aree su cui lavorare, gli esercizi e i quintetti; "
              "lo staff può partire da una bozza, da un modello o da zero e modificare ogni campo, poi stampa. L'intensità segue la distanza dalla partita: carico tre o più "
              "giorni prima, sviluppo due giorni prima, rifinitura il giorno prima.")
    club_es = a.archivio.exercises(a.club)
    t1, t2, t3 = st.tabs(["Prepara il programma", "Programmi salvati", "Libreria esercizi"])
    with t1:
        pri = _suggerimenti(a, sid)
        _crea(a, sid, pri, club_es)
        _programma(a, sid, club_es)
    with t2:
        _salvati(a, sid)
    with t3:
        _libreria(a, club_es)
