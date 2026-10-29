"""Guida della piattaforma: la pagina con le istruzioni delle parti meno intuitive e la demo guidata.

La demo guidata parte da sola la prima volta che un utente dello staff apre una pagina: illumina una
parte alla volta e spiega sotto come si usa. Si può rivedere quando si vuole con "? Guida della pagina"
(in basso a destra) o dalla pagina Guida. Delle pagine già viste si salva solo il nome, per utente.
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from .stato import App
from .ui import esc, note_html, section, titolo_pagina

_guida = components.declare_component("guida_assist", path=str(Path(__file__).resolve().parent / "guida"))

# Passi della demo per pagina. Ogni passo: dove (bersagli in ordine di preferenza), titolo, testo.
# Bersagli: "nav", "filtri", "esperto", "pagina", "tip", "sez:<titolo sezione>", "btn:<testo pulsante>",
# "tab:<scheda>", "exp:<riquadro apribile>", "sel:<etichetta del campo>", "frame:<componente>[><testo dentro>]".
# I passi di cui la pagina non mostra la parte (dati assenti, squadra non scelta) si saltano.
TOUR: dict[str, list[tuple[list[str], str, str]]] = {
    "home": [
        (["nav"], "Le aree della piattaforma",
         "In alto ci sono le aree: Avversaria, Previsioni, Giocatori, La mia squadra, Campionato. Tocca un'area per "
         "vederne le pagine. In «Guida» trovi le istruzioni delle parti più complesse."),
        (["filtri"], "Stagione, campionato, squadra, giocatore",
         "Questi filtri valgono per tutte le pagine. L'indirizzo della pagina li conserva: se lo mandi a un collega, "
         "vede esattamente quello che vedi tu."),
        (["esperto"], "Essenziale o Esperto",
         "Spento: solo le voci essenziali, con i nomi per esteso. Acceso: tutte le colonne e le metriche avanzate."),
        (["btn:Scouting dell'avversaria", "btn:Anteprima della partita"], "La settimana in un tocco",
         "La prossima avversaria è già pronta: scouting, anteprima della partita e report da portare in riunione."),
        (["btn:Prepara il PDF avversaria"], "Report da stampare",
         "Il report si prepara con un tocco e poi si scarica. Lo stesso PDF arriva anche per email prima di ogni partita."),
        (["tip"], "Il pulsante «?»",
         "Accanto alle statistiche complesse c'è un «?»: spiega cosa misura il numero, come si calcola e come leggerlo."),
    ],
    "scouting": [
        (["sel:Avversaria", "sel:Squadra"], "Quale squadra",
         "La pagina si apre sulla vostra prossima avversaria. Da qui puoi sceglierne un'altra."),
        (["sez:Chiavi per vincere"], "Su cosa lavorare in settimana",
         "Le leve dei Four Factors: l'obiettivo da tenere e quanto vale, in probabilità di vittoria, raggiungerlo."),
        (["sez:Giocatori chiave di"], "I giocatori che spostano la partita",
         "Chi decide le partite dell'avversaria e quanto cambia il pronostico con le sue cifre sopra o sotto la media."),
        (["sez:Quintetti più usati", "sez:+/- e On-Off"], "Quintetti e On-Off",
         "Ricostruiti dalla cronaca di ogni partita: quanto rende ogni quintetto e cosa cambia con un giocatore in "
         "campo o fuori."),
        (["sez:Giochi dell'avversaria"], "I loro giochi sulla lavagna",
         "Apri la lavagna e disegna i giochi dell'avversaria: finiscono nel PDF di scouting, fase per fase."),
        (["btn:Prepara il report PDF"], "Il report per la riunione tecnica",
         "PDF pronto da stampare, oppure Word da completare con le note dello staff."),
        (["sez:Note dello staff"], "Note dello staff",
         "Appunti del vostro staff su questa squadra: li vede solo il vostro club."),
    ],
    "lavagna_avv": [
        (["sel:Avversaria", "sel:Squadra"], "Quale squadra", "Scegli l'avversaria di cui disegnare i giochi."),
        (["frame:lavagna_assist>Nuovo", "frame:lavagna_assist"], "Un nuovo gioco",
         "«Nuovo», poi trascina il dito dal giocatore lungo il percorso. «+ Fase successiva» per la fase dopo, "
         "«Salva gioco» alla fine: il gioco entra nel PDF di scouting."),
    ],
    "anteprima": [
        (["sel:Casa"], "Quale partita", "Si apre sulla vostra prossima partita: puoi scegliere qualsiasi incrocio."),
        (["sez:Perché questa previsione"], "Probabilità, non certezze",
         "La probabilità di vittoria con la forbice e i fattori che la spiegano: campo, attacco, difesa, stagione "
         "precedente."),
        (["sez:Scenari"], "E se…",
         "Togli i giocatori assenti, indica la forma della squadra secondo lo staff o il campo neutro: la previsione "
         "si ricalcola subito."),
        (["sez:Four Factors incrociati"], "Il confronto che conta",
         "L'attacco di una squadra contro la difesa dell'altra, voce per voce."),
        (["sez:Chiave"], "La chiave della partita",
         "Per ogni squadra la leva che sposta di più la probabilità, con l'obiettivo da raggiungere."),
    ],
    "proiezione": [
        (["pagina"], "Dove può arrivare ogni squadra",
         "Il resto della stagione simulato 5.000 volte con la forza stimata di ogni squadra: vittorie attese, "
         "posizione media e probabilità di finire in ogni zona della classifica."),
        (["sez:Forza stimata delle squadre"], "La forza di ogni squadra",
         "Punti per 100 possessi rispetto a una squadra media, con la forbice: è il valore usato nelle simulazioni."),
    ],
    "mercato": [
        (["sez:Ricerca"], "Cerca con i filtri",
         "Categoria, ruolo stimato, età, minuti, efficienza: l'elenco cambia mentre scegli i filtri."),
        (["sez:Confronto giocatori"], "Due giocatori a confronto",
         "Verdetto in parole, profilo in percentili per ruolo e numeri alla pari tra A2 e B Nazionale. Il PDF è una "
         "pagina per il direttore sportivo."),
        (["sez:Dalla B all'A2"], "Salire di categoria",
         "Le statistiche che un giocatore di B Nazionale avrebbe, secondo i numeri, giocando in A2."),
        (["sez:Giocatori simili"], "Giocatori simili",
         "Parti da un giocatore che conosci: ASSIST trova chi ha un profilo statistico vicino."),
        (["sez:Osservati del club", "btn:Aggiungi agli osservati"], "Le vostre liste",
         "Con «☆ Aggiungi agli osservati» costruisci liste condivise con il vostro staff."),
    ],
    "mia": [
        (["sez:Aree da migliorare"], "Dove migliorare",
         "Su cosa concentrarsi, in parole: le priorità di lavoro e quante vittorie in più vale raggiungere l'obiettivo."),
        (["sez:Punti regalati"], "Punti regalati",
         "Palle perse, seconde occasioni, contropiede, liberi sbagliati, falli: quanto vi costano a partita."),
        (["exp:Modifica obiettivi", "sez:Obiettivi Four Factors"], "I vostri obiettivi",
         "Lo staff imposta gli obiettivi sui Four Factors: ogni partita si misura contro di essi."),
        (["sez:Report post-partita"], "Dopo la partita",
         "Scegli la partita: il report post-partita, anche in PDF."),
        (["btn:Prepara il PDF completo"], "Tutta la squadra in un PDF", "Tutte le voci della pagina, più i giochi della lavagna."),
    ],
    "sviluppo": [
        (["sez:Priorità di lavoro"], "Su cosa lavorare con ogni giocatore",
         "Per ogni giocatore cosa fa bene, cosa fa male e dove il miglioramento vale di più."),
        (["sez:Le prestazioni che spostano"], "Le prestazioni che contano",
         "Le cifre individuali che, per questa squadra, hanno spostato di più il risultato."),
        (["btn:Prepara il report sviluppo"], "Report da consegnare",
         "Un PDF per tutta la rosa, oppure uno per ogni giocatore."),
    ],
    "allenamento": [
        (["tab:Prepara il programma"], "Dai numeri alla seduta",
         "La piattaforma propone aree di lavoro, esercizi e quintetti. Tu decidi e modifichi ogni campo."),
        (["sez:Cosa suggeriscono i numeri"], "Cosa suggeriscono i numeri",
         "Le aree su cui lavorare questa settimana, calcolate dalle partite della squadra."),
        (["sel:Come partire"], "Da dove partire", "Da una bozza proposta da ASSIST, da un modello o da zero."),
        (["sel:Giorni di allenamento"], "La settimana",
         "Giorni e durata delle sedute. L'intensità segue la distanza dalla partita: carico tre o più giorni prima, "
         "sviluppo due giorni prima, rifinitura il giorno prima."),
        (["tab:Programmi salvati"], "Programmi salvati", "I programmi del club, da riaprire, modificare e stampare."),
        (["tab:Libreria esercizi"], "Libreria esercizi", "Gli esercizi pronti e quelli creati dal vostro staff."),
    ],
    "live": [
        (["sel:Partita"], "In diretta o rivista",
         "Durante la partita i dati arrivano dalla cronaca della lega ogni 30 secondi. Senza partita in corso puoi "
         "rivedere una partita giocata, fermandola al minuto che vuoi."),
        (["sez:Suggerimenti per lo staff"], "Suggerimenti per la panchina",
         "Ordinati per urgenza: timeout sui parziali, giocatori carichi di falli, bonus, chi è caldo."),
        (["sez:Prossime partite"], "Quando si gioca",
         "La pagina conosce il calendario e si apre da sola 20 minuti prima della palla a due."),
    ],
    "lavagna": [
        (["frame:lavagna_assist>Nuovo", "frame:lavagna_assist"], "Disegnare un gioco",
         "«Nuovo», poi scegli lo strumento e trascina il dito dal giocatore lungo il percorso. «+ Fase successiva» "
         "per la fase dopo, «Salva gioco» alla fine."),
        (["frame:lavagna_assist>Difesa", "frame:lavagna_assist"], "La difesa",
         "Scegli una difesa (a uomo, zone, box-and-one o manuale): le X si piazzano da sole a ogni fase. Nella difesa "
         "a uomo scegli anche come difendere il pick and roll."),
        (["frame:lavagna_assist>Vista 3D", "frame:lavagna_assist"], "Vista 3D",
         "Rivedi il gioco animato da quattro telecamere: dall'alto, tribuna, dietro il canestro, occhi del portatore."),
        (["frame:lavagna_assist>Schemi pronti", "frame:lavagna_assist"], "Schemi pronti",
         "63 schemi in 12 categorie da caricare e adattare."),
        (["btn:Archivio degli schemi"], "Tutto in PDF", "L'archivio degli schemi pronti, da stampare."),
    ],
    "video": [
        (["sel:Partita del video"], "La partita del video",
         "Scegli la partita: la sua cronaca si collega al video e le segnalazioni si salvano con lei."),
        (["frame:telestrator_assist>Scegli il video", "frame:telestrator_assist"], "Apri il video",
         "Il video resta sul dispositivo: non viene caricato. Poi «Sincronizza con il cronometro», i tasti «Segnala» "
         "e l'elenco delle azioni: tutti i passi sono nella pagina Guida."),
    ],
    "partite": [
        (["sel:Partita"], "Quale partita", "Box score, statistiche avanzate e andamento di ogni partita giocata."),
        (["sez:Andamento della partita"], "Andamento", "Il punteggio minuto per minuto, con i break."),
        (["sez:Probabilità di vittoria e momenti decisivi"], "I momenti decisivi",
         "Come è cambiata la probabilità di vittoria durante la partita e quali azioni l'hanno spostata di più."),
        (["sez:Mappa di tiro della partita"], "Da dove si è tirato", "La mappa di tiro a zone della partita."),
    ],
}

NOMI = {"home": "Home", "scouting": "Scouting", "lavagna_avv": "Lavagna dell'avversaria", "anteprima": "Anteprima",
        "proiezione": "Proiezione della classifica", "mercato": "Mercato", "mia": "La mia squadra",
        "sviluppo": "Sviluppo dei giocatori", "allenamento": "Programmi di allenamento", "live": "Live",
        "lavagna": "Lavagna dei giochi", "video": "Lavagna sul video", "partite": "Partite"}


def da_mostrare(utente: dict, viste: set, chiave: str) -> bool:
    """La demo parte da sola per gli utenti dello staff dei club, alla prima apertura di ogni pagina."""
    staff = bool(utente.get("club")) and not utente.get("demo") and utente.get("ruolo") != "admin"
    return staff and chiave in TOUR and chiave not in viste


def _viste(a: App) -> set:
    k = "guida_viste"
    if k not in st.session_state:
        try:
            st.session_state[k] = set(a.archivio.guida_viste(a.autore))
        except Exception:  # noqa: BLE001  (archivio non raggiungibile: la demo si vede, niente di grave)
            st.session_state[k] = set()
    return st.session_state[k]


def tour(a: App, chiave: str):
    """Demo guidata della pagina (in automatico solo la prima volta) e pulsante per rivederla."""
    if chiave not in TOUR:
        return
    viste = _viste(a)
    passi = [{"b": b, "t": t, "x": x} for b, t, x in TOUR[chiave]]
    valore = _guida(chiave=chiave, nome=NOMI.get(chiave, "Guida"), passi=passi,
                    auto=da_mostrare(a.utente, viste, chiave), key=f"guida_{chiave}", default=None)
    if isinstance(valore, dict) and valore.get("visto") == chiave and chiave not in viste:
        viste.add(chiave)
        try:
            a.archivio.segna_guida(a.autore, chiave)
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------------ pagina Guida
# Istruzioni delle parti meno intuitive, area per area: a cosa serve e come si usa, passo per passo.
GUIDA: list[tuple[str, str, list[str]]] = [
    ("Primi passi",
     "Come è fatta la piattaforma e gli strumenti che valgono ovunque.",
     ["In alto ci sono le aree (Avversaria, Previsioni, Giocatori, La mia squadra, Campionato): tocca un'area per "
      "vederne le pagine.",
      "Stagione, campionato, squadra e giocatore valgono per tutte le pagine. L'indirizzo della pagina li conserva: "
      "mandalo a un collega e vedrà la stessa cosa.",
      "«Esperto» spento mostra solo le voci essenziali con i nomi per esteso; acceso, tutte le colonne e le metriche "
      "avanzate.",
      "Il «?» accanto a una statistica spiega cosa misura, come si calcola e come leggerla. «? Cosa significano le "
      "colonne» fa lo stesso per una tabella intera.",
      "I report PDF si preparano con un tocco e poi si scaricano; lo scouting della prossima avversaria arriva anche "
      "per email prima di ogni partita.",
      "«? Guida della pagina», in basso a destra, ripete la demo guidata della pagina che stai guardando."]),
    ("Scouting dell'avversaria",
     "Il report completo sulla squadra da affrontare, pronto per la riunione tecnica.",
     ["La pagina si apre sulla vostra prossima avversaria; il campo «Avversaria» in alto permette di sceglierne "
      "un'altra.",
      "«Chiavi per vincere»: le leve dei Four Factors con l'obiettivo da tenere e quanto vale in probabilità di "
      "vittoria. Sono le stesse del PDF.",
      "«Quintetti più usati», «+/- e On-Off», «Finali punto a punto» e «Chi serve chi» sono ricostruiti dalla cronaca "
      "di ogni partita: le partite con dati incompleti sono escluse.",
      "«Giochi dell'avversaria»: apri la lavagna, disegna i loro giochi e salvali. Finiscono nel PDF di scouting.",
      "«Prepara il report PDF» per la stampa; «Prepara il report in Word» per completarlo con le note dello staff.",
      "«Note dello staff»: appunti privati del vostro club, visibili solo al vostro staff."]),
    ("Anteprima e scenari",
     "La probabilità di vittoria della partita e come cambia con le assenze.",
     ["La probabilità è sempre con la forbice: è una stima, non una certezza.",
      "«Perché questa previsione» mostra quanto pesano campo, attacco, difesa e stagione precedente.",
      "«Scenari: e se…»: scegli gli assenti di ciascuna squadra, la forma secondo lo staff o il campo neutro. La "
      "probabilità si ricalcola subito, senza toccare i dati della piattaforma.",
      "«Four Factors incrociati» mette l'attacco di una squadra contro la difesa dell'altra.",
      "«Proiezione della classifica» (in Previsioni) simula 5.000 volte le partite ancora da giocare: vittorie "
      "attese, posizione media e probabilità di finire in ogni zona della classifica."]),
    ("Mercato",
     "Per il direttore sportivo: cercare, confrontare, tenere d'occhio.",
     ["«Ricerca»: categoria, ruolo stimato, età, partite, minuti, usage ed efficienza. L'elenco cambia mentre scegli.",
      "«Confronto giocatori»: scegli due giocatori. Verdetto in parole, profilo in percentili per ruolo e numeri alla "
      "pari tra A2 e B Nazionale; «Confronto in PDF» è una pagina sola per il direttore sportivo.",
      "«Dalla B all'A2»: le statistiche che un giocatore di B Nazionale avrebbe, secondo i numeri, in A2.",
      "«Giocatori simili»: parti da un giocatore che conosci e trovi chi ha un profilo vicino.",
      "«☆ Aggiungi agli osservati» mette il giocatore in una lista del club, condivisa con lo staff."]),
    ("La mia squadra e Sviluppo dei giocatori",
     "Le priorità di lavoro della vostra squadra e dei singoli.",
     ["«Aree da migliorare»: su cosa concentrarsi, con le vittorie in più che vale raggiungere l'obiettivo.",
      "«Modifica obiettivi»: lo staff imposta gli obiettivi sui Four Factors; ogni partita si misura contro di essi.",
      "«Report post-partita»: scegli la partita e scarica il PDF.",
      "In «Sviluppo dei giocatori» ogni giocatore ha cosa fa bene, cosa fa male e dove migliorare vale di più, con un "
      "PDF da consegnargli."]),
    ("Programmi di allenamento",
     "Dai numeri alla seduta, pronta da stampare.",
     ["«Prepara il programma»: in «Cosa suggeriscono i numeri» ASSIST propone aree di lavoro, esercizi e quintetti.",
      "«Come partire»: da una bozza proposta, da un modello o da zero.",
      "Scegli giorni, minuti per seduta, ora di inizio e aree di lavoro in ordine di importanza. L'intensità segue la "
      "distanza dalla partita: carico tre o più giorni prima, sviluppo due giorni prima, rifinitura il giorno prima.",
      "Ogni campo si modifica; poi «Cosa stampare» sceglie le parti da stampare.",
      "«Programmi salvati» e «Libreria esercizi» (anche quelli creati dal vostro staff) sono nelle altre schede."]),
    ("Live",
     "La partita in diretta, per la panchina.",
     ["«In diretta»: i dati arrivano dalla cronaca della lega ogni 30 secondi. Punteggio, probabilità di vittoria, "
      "parziali, falli e bonus, timeout rimasti.",
      "«Suggerimenti per lo staff» sono ordinati per urgenza: timeout sui parziali, giocatori carichi di falli, bonus, "
      "chi è caldo, gestione dei finali.",
      "Se la lega non ha ancora pubblicato la cronaca lo dice la pagina: i dati compaiono appena arrivano.",
      "«Rivedi una partita giocata»: scegli la partita e sposta il minuto, come se fosse in diretta."]),
    ("Lavagna dei giochi",
     "I vostri giochi, fase per fase, anche in 3D e nel PDF.",
     ["«Nuovo», poi scegli lo strumento (taglio, passaggio, palleggio, blocco) e trascina il dito dal giocatore lungo "
      "il percorso.",
      "«+ Fase successiva» per la fase dopo; le note di ogni fase finiscono nel PDF. «Salva gioco» alla fine.",
      "«Difesa»: a uomo, zone (2-3, 3-2, 1-3-1, 1-2-2), box-and-one o manuale. Le X si piazzano da sole e seguono la "
      "palla; nella difesa a uomo scegli anche come difendere il pick and roll.",
      "«Vista 3D»: il gioco animato da quattro telecamere, con la velocità regolabile.",
      "«Schemi pronti»: 63 schemi in 12 categorie, da caricare e modificare. «Video» collega una clip dal dispositivo "
      "alle fasi del gioco.",
      "La stessa lavagna è in Avversaria › Lavagna dell'avversaria, per i loro giochi."]),
    ("Lavagna sul video",
     "La cronaca e le vostre segnalazioni sul video della partita, che resta sul dispositivo.",
     ["Scegli la partita in «Partita del video», poi apri il file del video (su computer puoi trascinarlo).",
      "«Sincronizza con il cronometro»: ASSIST trova da solo la grafica con il tempo e la legge, una volta per video "
      "(uno o due minuti). Poi tocca un'azione dell'elenco: il video mostra l'azione intera, da quando la squadra ha "
      "preso palla.",
      "Video senza grafica: porta il video alla palla a due e tocca «Palla a due qui». I minuti sono stimati: se "
      "un'azione non coincide, porta il video al momento giusto e tocca «📍 L'azione è qui».",
      "Mentre guardi, tocca un tasto «Segnala» (pick and roll centrale o laterale, hand-off, post basso…) nel momento "
      "della situazione; su computer i tasti 1–9. «＋ Nuova» crea un tasto con il nome che volete, per esempio lo "
      "schema «Horns 45»; «Modifica» toglie quelli che non usate.",
      "«Mostra» filtra l'elenco: una segnalazione, i canestri, le palle perse… con squadra, giocatore e quarto. «▶ In "
      "sequenza» rivede tutto l'elenco filtrato, una clip dopo l'altra.",
      "Con la partita si salvano solo le segnalazioni e la sincronizzazione, mai il video: riaprendo lo stesso file è "
      "tutto pronto.",
      "Ferma il video e disegna sul fotogramma (tagli, passaggi, blocchi, riflettore). In «Crea un gioco» tocchi "
      "campo e giocatori e il gioco si apre nella lavagna."]),
    ("Partite",
     "Ogni partita giocata, oltre il box score.",
     ["«Andamento della partita»: il punteggio minuto per minuto, con i break.",
      "«Probabilità di vittoria e momenti decisivi»: come è cambiata la probabilità e quali azioni l'hanno spostata.",
      "«Mappa di tiro della partita» e, attivandola, la cronologia dei tiri con quarto, cronometro e punteggio."]),
]


def pagina(a: App):
    titolo_pagina("Guida", "come si usano le parti più complesse della piattaforma")
    note_html("Qui trovi le istruzioni delle parti meno intuitive, area per area. In ogni pagina, «? Guida della "
              "pagina» in basso a destra illumina una parte alla volta e spiega come si usa.")
    if st.button("Rivedi la demo guidata in tutte le pagine", key="guida_azzera",
                 help="La demo ripartirà da sola la prossima volta che apri ciascuna pagina"):
        try:
            a.archivio.azzera_guida(a.autore)
        except Exception:  # noqa: BLE001
            pass
        st.session_state["guida_viste"] = set()
        if da_mostrare(a.utente, set(), "home"):
            st.success("Fatto: la demo ripartirà aprendo ogni pagina.")
        else:
            st.info("La demo parte da sola solo con gli accessi dello staff dei club: qui usa «? Guida della pagina» "
                    "in basso a destra.")
    for titolo, desc, passi in GUIDA:
        section(titolo, desc)
        st.markdown('<ol class="guida">' + "".join(f"<li>{esc(p)}</li>" for p in passi) + "</ol>",
                    unsafe_allow_html=True)
