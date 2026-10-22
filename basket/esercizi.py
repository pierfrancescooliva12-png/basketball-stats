"""Libreria degli esercizi per i programmi di allenamento.

Ogni esercizio ha la fase della seduta in cui si usa, le aree di lavoro che allena, durata e
intensità tipiche, il numero minimo di giocatori, una descrizione breve, i punti chiave da
correggere e, quando c'è, come misurarlo (così lo staff vede i progressi). Le aree sono le
stesse dei numeri della piattaforma: le priorità della squadra (Four Factors) e le aree di
miglioramento dei giocatori portano agli esercizi giusti.
"""

FASI = {
    "riscaldamento": "Riscaldamento",
    "tecnica": "Tecnica individuale",
    "situazioni": "Situazioni (1c1 – 4c4)",
    "collettivo": "Collettivo 5c5",
    "tiro": "Tiro e liberi",
    "defaticamento": "Defaticamento",
}

AREE = {
    "tiro": "Tiro",
    "liberi": "Tiri liberi",
    "attacco_ferro": "Attacco al ferro",
    "palle_perse": "Gestione palla e palle perse",
    "passaggio": "Passaggio e letture",
    "pnr_attacco": "Pick and roll in attacco",
    "rimb_off": "Rimbalzo offensivo",
    "rimb_dif": "Rimbalzo difensivo e tagliafuori",
    "difesa_tiro": "Difesa sul tiro (closeout)",
    "difesa_falli": "Difendere senza falli",
    "difesa_pnr": "Difesa sul pick and roll",
    "pressione": "Pressione e palle recuperate",
    "protezione_ferro": "Protezione del ferro",
    "transizione_off": "Contropiede",
    "transizione_dif": "Transizione difensiva",
    "sinergie": "Sinergie di quintetto",
    "finali": "Finali punto a punto",
    "condizione": "Condizione e ritmo",
}

# priorità della squadra (colonne dei Four Factors) → aree di lavoro
AREE_SQUADRA = {
    "efg_pct": ["tiro", "passaggio"],
    "tov_pct": ["palle_perse", "passaggio"],
    "orb_pct": ["rimb_off"],
    "ft_rate": ["attacco_ferro", "pnr_attacco"],
    "opp_efg_pct": ["difesa_tiro", "difesa_pnr"],
    "opp_tov_pct": ["pressione"],
    "drb_pct": ["rimb_dif"],
    "opp_ft_rate": ["difesa_falli"],
}

# aree di miglioramento dei giocatori (basket.sviluppo) → aree di lavoro
AREE_GIOCATORE = {
    "Tiri liberi": ["liberi"],
    "Tiro da 3": ["tiro"],
    "Punti per tiro (liberi compresi)": ["tiro", "attacco_ferro"],
    "Palle perse": ["palle_perse"],
    "Assist": ["passaggio"],
    "Rimbalzi difensivi": ["rimb_dif"],
    "Rimbalzi offensivi": ["rimb_off"],
    "Recuperi": ["pressione"],
    "Stoppate": ["protezione_ferro"],
    "Falli commessi": ["difesa_falli"],
}

INTENSITA = ("bassa", "media", "alta")


def _e(id_, nome, fase, aree, durata, intensita, giocatori, descrizione, punti, misura=""):
    return {"id": id_, "nome": nome, "fase": fase, "aree": aree, "durata": durata, "intensita": intensita,
            "giocatori": giocatori, "descrizione": descrizione, "punti": punti, "misura": misura}


ESERCIZI = [
    # ------------------------------------------------------------ riscaldamento
    _e("r_attivazione", "Attivazione con palla", "riscaldamento", ["condizione"], 10, "bassa", 1,
       "Andature, mobilità e palleggio in movimento a metà velocità, poi cambi di ritmo.",
       ["Prima mobilità, poi velocità", "Palla sempre viva, testa alta"]),
    _e("r_passaggi", "Passaggi a coppie in movimento", "riscaldamento", ["passaggio"], 8, "bassa", 2,
       "Coppie che risalgono il campo passandosi la palla: petto, battuto, una mano dal palleggio.",
       ["Passaggio al petto del compagno, non dove si trova", "Chiamare il nome prima di ricevere"]),
    _e("r_mikan", "Mikan e appoggi a due mani", "riscaldamento", ["attacco_ferro", "protezione_ferro"], 6, "bassa", 1,
       "Appoggi alternati destra e sinistra sotto canestro senza far toccare terra alla palla, poi varianti.",
       ["Palla sopra la testa, mai sotto il mento", "Ritmo continuo, piedi sempre pronti"],
       "Canestri consecutivi in 60 secondi"),
    # ------------------------------------------------------------ tecnica
    _e("t_tiro_blocchi", "Tiro in uscita dai blocchi", "tecnica", ["tiro"], 12, "media", 2,
       "Uscite ricciolo e a ricciolo largo dai blocchi lontano dalla palla, con passaggio e tiro piazzato.",
       ["Piedi pronti prima della palla", "Mani a bersaglio per il passatore", "Stesso ritmo di tiro"],
       "Canestri su 20 tiri per lato"),
    _e("t_tiro_5", "Tiro da 3 da cinque posizioni", "tecnica", ["tiro"], 10, "media", 1,
       "Cinque tiri per posizione (angoli, ali, centro), a coppie con rimbalzista che passa.",
       ["Equilibrio all'arrivo", "Gomito sotto la palla", "Accompagnare il tiro"],
       "Canestri su 25 tentativi: segnare sul foglio"),
    _e("t_catch_shoot", "Ricezione e tiro dal passaggio", "tecnica", ["tiro", "passaggio"], 10, "media", 3,
       "Passaggio dal post o dalla penetrazione (kick-out) e tiro immediato dall'angolo o dall'ala.",
       ["Spostarsi nella linea di passaggio libera", "Tiro senza palleggio se aperto"],
       "Canestri su 20 ricezioni"),
    _e("t_liberi_coppie", "Tiri liberi a coppie con penalità", "tiro", ["liberi"], 8, "bassa", 2,
       "Serie da due liberi a turno: chi sbaglia il secondo fa una corsa breve, poi torna in lunetta.",
       ["Stessa routine ogni volta", "Respiro prima del tiro", "Piedi allineati"],
       "Liberi segnati su 20"),
    _e("t_liberi_fatica", "Liberi sotto fatica", "tiro", ["liberi", "finali"], 8, "media", 1,
       "Sprint andata e ritorno, poi due liberi subito: simula i liberi dei finali di partita.",
       ["Recuperare il respiro con la routine", "Non accorciare il gesto"],
       "Liberi segnati su 10 serie"),
    _e("t_palleggio_pressione", "Palleggio sotto pressione 1c1 a tutto campo", "tecnica",
       ["palle_perse", "pressione"], 10, "alta", 2,
       "Il portatore deve superare la metà campo entro 8 secondi contro un difensore aggressivo.",
       ["Corpo tra difensore e palla", "Cambi di direzione solo con spazio", "Testa alta per il passaggio"],
       "Palle perse ogni 10 risalite"),
    _e("t_ball_handling", "Due palloni e controllo palla", "tecnica", ["palle_perse"], 8, "bassa", 1,
       "Palleggio con due palloni da fermi e in movimento: alternato, simultaneo, alto-basso.",
       ["Palleggio con i polpastrelli", "Sguardo avanti, non sulla palla"]),
    _e("t_torello", "Passaggi con difensore in mezzo (torello)", "tecnica", ["passaggio", "palle_perse"], 8, "media", 4,
       "Tre o quattro attaccanti fermi si passano la palla contro uno o due difensori nel mezzo.",
       ["Finta prima del passaggio", "Passaggi brevi e tesi", "Leggere le mani del difensore"],
       "Passaggi intercettati in 3 minuti"),
    _e("t_arresto_scelta", "Arresto e scelta: tiro, passaggio o palleggio", "tecnica",
       ["passaggio", "attacco_ferro"], 10, "media", 3,
       "Penetrazione con arresto a due tempi: l'allenatore indica all'ultimo se tirare, scaricare o ripartire.",
       ["Arresto in equilibrio", "Decidere in un tempo", "Perno per proteggere la palla"]),
    _e("t_contatto", "Attacchi al ferro con contatto", "tecnica", ["attacco_ferro"], 10, "media", 2,
       "Penetrazione e conclusione contro il contatto di un compagno con il cuscinetto, poi tiro libero.",
       ["Spalla dentro il contatto", "Due mani alla conclusione", "Cercare il fallo e il canestro"],
       "Canestri con contatto su 15"),
    _e("t_closeout", "Closeout e contest", "tecnica", ["difesa_tiro", "difesa_falli"], 10, "alta", 2,
       "Il difensore parte dal pitturato e chiude sul tiratore con passi corti, mano alta, senza saltare.",
       ["Ultimi passi corti e bassi", "Mano alta sul tiro", "Non regalare la linea di fondo"],
       "Tiri contestati su 10 closeout"),
    _e("t_scivolamenti", "Scivolamenti con mani attive", "tecnica", ["difesa_falli", "pressione"], 8, "media", 1,
       "Scivolamenti a zig-zag a tutto campo davanti al palleggiatore, mani sulle linee di passaggio.",
       ["Muovere i piedi, non le mani", "Petto davanti, braccia fuori dal contatto"]),
    _e("t_verticalita", "Verticalità sul tiro: difendere senza falli", "tecnica",
       ["difesa_falli", "protezione_ferro"], 8, "media", 2,
       "Il difensore salta in verticale con le braccia alte contro l'attacco al ferro, senza scendere sul tiratore.",
       ["Braccia verticali, mai verso la palla", "Saltare dopo l'attaccante", "Restare tra uomo e canestro"],
       "Falli commessi su 10 contrasti"),
    _e("t_tagliafuori", "Tagliafuori 1c1 a coppie", "tecnica", ["rimb_dif"], 8, "alta", 2,
       "Al tiro dell'allenatore il difensore trova l'attaccante, lo tiene fuori con il corpo e prende la palla.",
       ["Prima il contatto, poi la palla", "Base larga e sedere basso", "Prendere la palla con due mani"],
       "Rimbalzi presi su 10 tiri"),
    _e("t_rimb_off", "Rimbalzo offensivo: secondo salto e tap", "tecnica", ["rimb_off"], 8, "alta", 2,
       "Attacco del ferro dopo il tiro: aggirare il tagliafuori, secondo salto rapido, tap o ricezione e appoggio.",
       ["Muoversi al tiro, non dopo", "Aggirare con la spalla", "Secondo salto più rapido del primo"],
       "Rimbalzi offensivi su 10 tiri"),
    _e("t_pnr_letture", "Letture del portatore sul pick and roll", "tecnica", ["pnr_attacco", "passaggio"], 10, "media", 3,
       "Portatore, bloccante e un difensore passivo: l'allenatore mostra la copertura, il portatore legge.",
       ["Usare il blocco spalla a spalla", "Primo palleggio aggressivo", "Passaggio al rollante in anticipo"]),
    # ------------------------------------------------------------ situazioni
    _e("s_pnr_2c2", "2c2 pick and roll a metà campo", "situazioni", ["pnr_attacco", "sinergie"], 12, "alta", 4,
       "Pick and roll centrale e laterale a punteggio: tre canestri per vincere il turno.",
       ["Angolo del blocco giusto", "Il bloccante rolla o si apre in base al difensore", "Comunicare"],
       "Punti per possesso"),
    _e("s_pnr_difesa", "2c2 difesa del pick and roll", "situazioni", ["difesa_pnr", "difesa_falli"], 12, "alta", 4,
       "Pick and roll con la copertura scelta per la settimana (sopra, sotto, cambio, show, contenimento).",
       ["Chiamare il blocco ad alta voce", "Il lungo tiene il rollante e il portatore", "Recupero rapido"],
       "Canestri concessi su 10 possessi"),
    _e("s_consegnato", "3c3 consegnato e taglio", "situazioni", ["sinergie", "passaggio"], 12, "alta", 6,
       "Consegnati e tagli backdoor sul lato debole: si gioca in continuità senza giochi chiamati.",
       ["Tempi tra consegna e taglio", "Spaziature di 4-5 metri", "Leggere l'anticipo del difensore"]),
    _e("s_shell", "Shell drill 4c4: aiuto e recupero", "situazioni", ["difesa_tiro", "difesa_pnr", "difesa_falli"], 12,
       "media", 8,
       "Quattro attaccanti sul perimetro si passano la palla; i difensori cambiano posizione a ogni passaggio.",
       ["Saltare verso la palla a ogni passaggio", "Aiuto a un passo dalla linea", "Closeout con mani alte"],
       "Penetrazioni concesse in 3 minuti"),
    _e("s_rimbalzo_4c4", "4c4 a rimbalzo: tutti a tagliafuori", "situazioni", ["rimb_dif", "rimb_off"], 10, "alta", 8,
       "Tiro dell'allenatore e lotta a rimbalzo: un punto per il rimbalzo, due per il canestro su secondo tiro.",
       ["Ognuno trova il suo uomo", "Gli esterni scendono a rimbalzo", "Uscita veloce dopo il rimbalzo"],
       "Rimbalzi offensivi concessi su 10 tiri"),
    _e("s_3c2", "3c2 e 2c1 continuo", "situazioni", ["transizione_off", "transizione_dif"], 10, "alta", 5,
       "Tre attaccano contro due; chi tira e i due difensori ripartono in 2c1 dall'altra parte.",
       ["Palla al centro, ali larghe", "Il primo difensore ferma la palla", "Decidere entro due passaggi"],
       "Punti per possesso"),
    _e("s_rientro", "Rientro difensivo: 5 contro 4 + 1", "situazioni", ["transizione_dif"], 10, "alta", 10,
       "Dopo il tiro un difensore tocca la linea di fondo: gli altri quattro rientrano e fermano il contropiede.",
       ["Il primo rientra sotto canestro", "Fermare la palla prima di tutto", "Parlare: chi prende chi"],
       "Canestri facili concessi su 10 rientri"),
    _e("s_pressione", "Pressione a tutto campo e uscita", "situazioni", ["pressione", "palle_perse"], 10, "alta", 8,
       "Pressione a uomo dopo canestro: l'attacco deve superare la metà campo con passaggi, non con il palleggio.",
       ["Raddoppio sulla linea laterale", "L'attacco usa il centro e il passaggio lungo", "Rotazioni alle spalle"],
       "Palloni recuperati su 10 rimesse"),
    # ------------------------------------------------------------ collettivo
    _e("c_quintetto", "5c5 a metà campo con il quintetto della settimana", "collettivo", ["sinergie"], 15, "media", 10,
       "Il quintetto su cui lavorare gioca i suoi giochi contro la difesa che userà l'avversaria.",
       ["Spaziature e tempi dei giochi", "Chi chiama i giochi", "Correggere subito, poi rigiocare"]),
    _e("c_tema", "5c5 a tutto campo a tema", "collettivo", ["sinergie", "condizione"], 20, "alta", 10,
       "Partita a tempo con un punteggio a tema: punti extra per l'obiettivo della settimana "
       "(rimbalzo offensivo, palla recuperata, tiro dall'angolo, nessuna palla persa).",
       ["Il tema si dichiara prima", "Fermare il gioco solo per gli errori del tema"],
       "Punti a tema per squadra"),
    _e("c_finali", "Finali di partita a tempo e punteggio", "collettivo", ["finali", "liberi"], 12, "media", 10,
       "Situazioni da ultimi due minuti: sotto di 3 con 30 secondi, sopra di 2 con palla, rimessa con 5 secondi.",
       ["Chi tira e chi rimette", "Gestione dei falli e dei timeout", "Rimesse provate"]),
    _e("c_zona", "Attacco alla zona", "collettivo", ["tiro", "passaggio"], 12, "media", 10,
       "Attacco contro zona 2-3 e 3-2 con ribaltamenti, tagli nel cuore della zona e tiro dall'angolo.",
       ["Attaccare gli spazi tra due difensori", "Palla in mezzo e fuori", "Rimbalzo dal lato debole"]),
    _e("c_rifinitura", "Rifinitura: giochi della lavagna a ritmo partita", "collettivo", ["sinergie"], 20, "bassa", 10,
       "I giochi da provare per la partita, contro una difesa che conosce lo scouting, senza contatto pieno.",
       ["Ogni gioco almeno due volte per lato", "Contro-mosse dell'avversaria", "Rimesse e situazioni speciali"]),
    _e("c_scouting", "Attacco dell'avversaria con le riserve", "collettivo", ["difesa_pnr", "difesa_tiro"], 15, "media", 10,
       "Le riserve giocano i giochi dell'avversaria (dalla lavagna): il quintetto titolare li difende.",
       ["Riconoscere il gioco alla chiamata", "Coperture già decise", "Chi marca chi in transizione"]),
    # ------------------------------------------------------------ defaticamento
    _e("d_defaticamento", "Defaticamento e allungamento", "defaticamento", ["condizione"], 8, "bassa", 1,
       "Corsa lenta, allungamento dei muscoli delle gambe e della schiena, respirazione.",
       ["Allungamento senza molleggiare", "Bere e annotare la fatica (RPE)"]),
]

PER_ID = {e["id"]: e for e in ESERCIZI}
PER_NOME = {e["nome"]: e for e in ESERCIZI}


def per_aree(aree: list[str], fase: str | None = None, intensita_max: str = "alta") -> list[dict]:
    """Esercizi che allenano le aree date (i primi allenano le prime aree), filtrati per fase
    e per intensità massima."""
    lim = INTENSITA.index(intensita_max)
    candidati = [e for e in ESERCIZI if (fase is None or e["fase"] == fase)
                 and INTENSITA.index(e["intensita"]) <= lim]

    def punteggio(e):
        pos = [aree.index(a) for a in e["aree"] if a in aree]
        return (min(pos) if pos else 99, -len(pos))
    return sorted(candidati, key=punteggio)
