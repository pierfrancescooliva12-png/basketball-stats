"""Glossario delle statistiche: cosa misurano, come si calcolano, come leggerle.

I valori di riferimento sono indicativi per Serie A2 / B Nazionale.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Voce:
    titolo: str
    cosa: str       # che concetto esprime
    calcolo: str    # come si calcola
    lettura: str    # come interpretarla, valori tipici


G = {
    "possessi": Voce(
        "Possessi",
        "Quante volte una squadra ha avuto la palla. È la base per confrontare squadre che "
        "giocano a ritmi diversi.",
        "Tiri dal campo tentati − rimbalzi offensivi + palle perse + 0,44 × tiri liberi tentati. "
        "Si fa la media tra le due squadre, perché in una partita i possessi sono quasi uguali.",
        "In A2 di solito 65–75 possessi a partita per squadra."),
    "pace": Voce(
        "Ritmo (pace)",
        "La velocità di gioco: quanti possessi una squadra gioca in 40 minuti.",
        "Possessi × 40 / minuti giocati (per squadra).",
        "Sopra 73 = squadra che corre; sotto 67 = squadra che gioca a metà campo. Il ritmo da "
        "solo non è né buono né cattivo: conta il rendimento per possesso."),
    "ortg": Voce(
        "Rating offensivo (ORtg)",
        "L'efficienza in attacco: quanti punti segna una squadra (o un giocatore in campo) ogni "
        "100 possessi, indipendentemente dal ritmo.",
        "100 × punti segnati / possessi.",
        "Media campionato circa 105–108. Sopra 112 attacco d'élite, sotto 100 attacco in difficoltà."),
    "drtg": Voce(
        "Rating difensivo (DRtg)",
        "L'efficienza in difesa: quanti punti concede la squadra ogni 100 possessi avversari.",
        "100 × punti subiti / possessi.",
        "Più è basso, meglio è. Sotto 100 difesa d'élite, sopra 112 difesa debole."),
    "net_rtg": Voce(
        "Net rating",
        "Il dominio complessivo: di quanti punti la squadra supera gli avversari ogni 100 "
        "possessi. È il miglior indicatore singolo della forza reale.",
        "ORtg − DRtg.",
        "+10 o più = squadra di vertice; intorno a 0 = media; −10 o meno = squadra da salvezza. "
        "Spesso predice i risultati futuri meglio della classifica."),
    "efg": Voce(
        "eFG% (percentuale effettiva)",
        "La precisione al tiro tenendo conto che il tiro da 3 vale di più.",
        "(Canestri dal campo + 0,5 × canestri da 3) / tiri dal campo tentati.",
        "Media circa 50%. Sopra 54% tiro eccellente, sotto 46% tiro in difficoltà."),
    "ts": Voce(
        "TS% (true shooting)",
        "L'efficienza realizzativa completa: comprende tiri da 2, da 3 e tiri liberi.",
        "Punti / (2 × (tiri dal campo tentati + 0,44 × liberi tentati)).",
        "Media circa 54–56%. Sopra 60% realizzatore molto efficiente, sotto 50% poco efficiente. "
        "Con pochi tiri può superare il 100%: va letto insieme al volume."),
    "tov": Voce(
        "Palle perse % (TOV%)",
        "Quanti possessi finiscono con una palla persa, cioè senza nemmeno un tiro.",
        "Palle perse / (tiri dal campo tentati + 0,44 × liberi tentati + palle perse).",
        "Più è basso, meglio è. Media circa 14%. Sotto 11% squadra molto ordinata, sopra 17% "
        "squadra che spreca."),
    "orb": Voce(
        "Rimbalzi offensivi % (OREB%)",
        "La capacità di conquistare seconde occasioni: quota dei propri errori recuperati.",
        "Rimbalzi offensivi / (rimbalzi offensivi + rimbalzi difensivi avversari).",
        "Media circa 30%. Sopra 35% squadra forte a rimbalzo d'attacco."),
    "drb": Voce(
        "Rimbalzi difensivi % (DREB%)",
        "La capacità di chiudere il possesso difensivo con il rimbalzo.",
        "Rimbalzi difensivi / (rimbalzi difensivi + rimbalzi offensivi avversari).",
        "Media circa 70%. Sotto 66% la squadra concede troppe seconde occasioni."),
    "ft_rate": Voce(
        "FT rate (liberi / tiri)",
        "Quanto una squadra va in lunetta rispetto a quanto tira: misura l'aggressività verso "
        "il canestro.",
        "Tiri liberi segnati / tiri dal campo tentati (per i giocatori: liberi tentati / tiri "
        "dal campo tentati).",
        "Squadre: media circa 0,22. Giocatori: sopra 0,40 è uno che attacca il ferro e si "
        "procura falli."),
    "four_factors": Voce(
        "Four Factors",
        "I quattro fattori che spiegano gran parte delle vittorie (Dean Oliver): tirare bene, "
        "non perdere palla, prendere rimbalzi offensivi, andare in lunetta. Ognuno ha il "
        "corrispettivo in difesa.",
        "eFG%, TOV%, OREB% e FT rate, in attacco e concessi agli avversari.",
        "Il più importante è l'eFG% (circa 40% del peso), poi le palle perse (25%), i rimbalzi "
        "(20%) e i liberi (15%). Confronta le barre con la media per vedere dove la squadra "
        "guadagna o perde."),
    "usg": Voce(
        "Usage % (USG%)",
        "Il peso offensivo di un giocatore: quota dei possessi di squadra che conclude lui (con "
        "un tiro, dei liberi o una palla persa) quando è in campo.",
        "100 × (tiri tentati + 0,44 × liberi tentati + perse) × (minuti squadra / 5) / "
        "(minuti giocatore × stesso totale di squadra).",
        "La media è 20% (5 giocatori in campo). Sopra 28% è la prima opzione offensiva; sotto "
        "15% è un giocatore di ruolo. Va letto insieme al TS%."),
    "ast_ratio": Voce(
        "Assist ratio",
        "Quanti possessi conclusi dal giocatore (o dalla squadra) diventano un assist.",
        "100 × assist / (tiri tentati + 0,44 × liberi tentati + assist + perse).",
        "Per un playmaker 25–35; per un lungo realizzatore 5–10."),
    "ast_pct": Voce(
        "Assist % (AST%)",
        "Quota dei canestri dei compagni nati da un suo assist mentre è in campo.",
        "Assist / (canestri di squadra con lui in campo − suoi canestri). I canestri con lui in "
        "campo sono stimati con la quota di minuti.",
        "Sopra 30% è un vero regista; 15–20% buon passatore; sotto 10% gioca poco per i compagni."),
    "reb_ind": Voce(
        "Rimbalzi % individuali (OREB%, DREB%, REB%)",
        "Quanti dei rimbalzi disponibili mentre è in campo cattura il giocatore. Più giusto del "
        "numero di rimbalzi, che dipende dai minuti e dal ritmo.",
        "Rimbalzi del giocatore / rimbalzi disponibili con lui in campo (stimati con la quota "
        "di minuti).",
        "REB% sopra 15% è un ottimo rimbalzista; DREB% sopra 20% è un lungo dominante."),
    "stl_blk": Voce(
        "Recuperi % e stoppate % (STL%, BLK%)",
        "L'impatto difensivo diretto: quanti possessi avversari chiude con un recupero e quanti "
        "tiri da 2 avversari stoppa mentre è in campo.",
        "STL% = recuperi / possessi avversari con lui in campo; BLK% = stoppate / tiri da 2 "
        "avversari con lui in campo.",
        "STL% sopra 2,5% mani molto attive; BLK% sopra 4% protettore del ferro."),
    "tov_ind": Voce(
        "Palle perse % individuale",
        "Quanti dei possessi che usa il giocatore finiscono con una palla persa.",
        "Perse / (tiri tentati + 0,44 × liberi tentati + perse).",
        "Sotto 10% molto sicuro; sopra 18% troppe perse. Per i registi è normale qualche punto in più."),
    "game_score": Voce(
        "Game Score",
        "Un voto sintetico della partita di un giocatore (John Hollinger): somma ciò che fa di "
        "buono e sottrae errori, perse e falli. Rispetto alla valutazione della Lega penalizza "
        "di più i tiri sbagliati.",
        "Punti + 0,4 × canestri − 0,7 × tiri tentati − 0,4 × liberi sbagliati + 0,7 × rimb. "
        "offensivi + 0,3 × rimb. difensivi + recuperi + 0,7 × assist + 0,7 × stoppate − 0,4 × "
        "falli − perse.",
        "10 = partita nella media; 20 = ottima partita; 30+ = partita eccezionale."),
    "valutazione": Voce(
        "Valutazione (Lega)",
        "L'indice ufficiale della Lega: somma di tutte le voci positive meno quelle negative.",
        "Punti + rimbalzi + assist + recuperi + stoppate + falli subiti − tiri sbagliati − perse "
        "− falli commessi − stoppate subite.",
        "Premia il volume più dell'efficienza: un giocatore che tira molto con basse percentuali "
        "può avere una buona valutazione. Leggila insieme al TS%."),
    "per40": Voce(
        "Per 40 minuti",
        "Le statistiche riportate a una partita intera giocata, per confrontare titolari e "
        "panchinari a parità di minuti.",
        "Statistica × 40 / minuti giocati.",
        "Utile per scoprire panchinari molto produttivi. Con pochi minuti (sotto 10 di media) i "
        "valori sono instabili."),
    "pyth": Voce(
        "Vittorie attese (pitagorica)",
        "Quante partite la squadra 'meriterebbe' di aver vinto in base a punti fatti e subiti.",
        "Punti fatti¹⁴ / (punti fatti¹⁴ + punti subiti¹⁴) × partite giocate.",
        "Predice i risultati futuri meglio del record attuale, perché le vittorie di misura "
        "dipendono molto dal caso."),
    "fortuna": Voce(
        "Fortuna",
        "La differenza tra le vittorie reali e quelle attese.",
        "Vittorie reali − vittorie attese.",
        "Positivo = la squadra ha vinto più di quanto dicano i punti (di solito vincendo tante "
        "partite punto a punto): è probabile che rallenti. Negativo = probabile miglioramento."),
    "punto_a_punto": Voce(
        "Partite punto a punto",
        "Il rendimento nelle partite equilibrate, decise negli ultimi possessi.",
        "Record nelle partite finite con 5 punti di scarto o meno.",
        "Un record molto positivo o molto negativo con poche partite è spesso fortuna; con "
        "tante partite può indicare lucidità nei finali e un buon realizzatore nei momenti caldi."),
    "sos": Voce(
        "Forza del calendario",
        "Quanto sono stati forti gli avversari affrontati finora.",
        "Media del Net rating degli avversari incontrati.",
        "Positivo = calendario difficile (il record può migliorare); negativo = calendario "
        "facile (il record può peggiorare)."),
    "panchina": Voce(
        "% punti della panchina",
        "Il contributo dei giocatori non in quintetto.",
        "Punti segnati da chi non è partito in quintetto / punti totali.",
        "Sopra 40% squadra profonda; sotto 25% squadra che dipende dai titolari (attenzione a "
        "falli e stanchezza)."),
    "top2": Voce(
        "% punti dei primi 2 realizzatori",
        "Quanto l'attacco dipende dalle sue due stelle.",
        "Punti dei 2 migliori realizzatori della squadra / punti totali.",
        "Sopra 45% attacco molto concentrato: limitare quei due giocatori è la chiave "
        "difensiva. Sotto 35% attacco distribuito."),
    "assistiti": Voce(
        "% canestri assistiti",
        "Quanto gioco di squadra c'è nei canestri: quanti nascono da un passaggio.",
        "Assist / canestri dal campo segnati.",
        "Sopra 60% attacco basato sulla circolazione; sotto 45% attacco basato sull'uno contro uno."),
    "distribuzione": Voce(
        "Distribuzione dei punti",
        "Da dove arrivano i punti della squadra: tiri da 2, da 3 o liberi.",
        "2 × canestri da 2, 3 × canestri da 3 e liberi segnati, ciascuno diviso per i punti totali.",
        "Una quota da 3 sopra il 40% indica una squadra che vive di tiro da fuori, più "
        "esposta alle serate storte."),
    "quarti": Voce(
        "Differenza per quarto",
        "In quale fase della partita la squadra guadagna o perde terreno.",
        "Media dei punti fatti − subiti in ogni quarto (supplementari esclusi).",
        "Q1 positivo = parte forte (quintetto, preparazione); Q4 positivo = chiude bene "
        "(esperienza, panchina, condizione). Q3 negativo spesso indica problemi di rientro "
        "dall'intervallo."),
    "percentili": Voce(
        "Percentili",
        "La posizione del giocatore rispetto agli altri del campionato, voce per voce.",
        "Percentuale di giocatori (con almeno 10' di media) con un valore peggiore. Per le palle "
        "perse il calcolo è invertito: un percentile alto significa poche perse.",
        "90 = meglio del 90% dei giocatori. Il profilo mostra subito i punti forti (barre blu, "
        "sopra 50) e deboli (barre arancio)."),
    "variabilita": Voce(
        "Variabilità dei punti",
        "La costanza realizzativa del giocatore da una partita all'altra.",
        "Deviazione standard dei punti / media punti (coefficiente di variazione).",
        "Sotto 0,30 molto costante; sopra 0,60 alterna grandi partite a partite spente."),
    "t3a_rate": Voce(
        "% tiri da 3",
        "Quanto il giocatore vive del tiro da fuori.",
        "Tiri da 3 tentati / tiri dal campo tentati.",
        "Sopra 60% è un tiratore puro; sotto 15% gioca quasi solo vicino a canestro."),
    "oer": Voce(
        "OER (sito della Lega)",
        "Indice di efficienza offensiva pubblicato dalla Lega nel box score.",
        "Punti per possesso usato, secondo la formula del sito.",
        "Intorno a 1 nella media; sopra 1,2 molto efficiente."),
    "incompleto": Voce(
        "Box score incompleto",
        "Alcuni box score ufficiali hanno tiri tentati, rimbalzi o palle perse registrati solo "
        "in parte (i punti invece sono corretti).",
        "Una partita è segnalata quando il ritmo stimato è sotto 58 possessi per 40', valore "
        "impossibile in una partita reale.",
        "Queste partite contano per risultati, classifica, punti e totali, ma sono escluse da "
        "percentuali e metriche avanzate per non falsarle."),
    "mappa": Voce(
        "Mappa attacco / difesa",
        "Dove si colloca ogni squadra per efficienza offensiva e difensiva.",
        "Asse orizzontale: ORtg (più a destra = attacco migliore). Asse verticale: DRtg, "
        "invertito (più in alto = difesa migliore). Le linee tratteggiate sono le medie.",
        "In alto a destra le squadre complete; in basso a sinistra quelle in difficoltà su "
        "entrambi i lati."),
    "leader": Voce(
        "Leader",
        "Le classifiche individuali del campionato.",
        "Sono considerati solo i giocatori con almeno metà delle partite della squadra e 10' di "
        "media (per il TS% anche almeno 6 tiri a partita), per evitare valori gonfiati da pochi "
        "minuti.",
        "Tocca il ? di ogni statistica per la spiegazione."),
    "plus_minus": Voce(
        "+/- (plus/minus)",
        "La differenza punti della squadra mentre il giocatore è in campo.",
        "Punti fatti − punti subiti dalla squadra nei minuti del giocatore, dai quintetti "
        "ricostruiti dalla cronaca (solo partite con quintetti verificati).",
        "Dipende molto dai compagni e dagli avversari: va letto insieme all'On-Off e con un "
        "buon numero di minuti. Su poche partite è rumoroso."),
    "on_off": Voce(
        "On-Off",
        "Quanto cambia il rendimento della squadra con il giocatore in campo rispetto a quando "
        "è in panchina.",
        "Net rating con il giocatore in campo − Net rating con il giocatore fuori.",
        "+10 o più = la squadra è molto migliore quando gioca lui; negativo = la squadra rende "
        "di più senza di lui. Con pochi minuti fuori dal campo il dato è instabile."),
    "quintetti": Voce(
        "Quintetti",
        "Le combinazioni di 5 giocatori usate dall'allenatore e il loro rendimento.",
        "La cronaca registra solo chi entra: chi esce è dedotto (non può più comparire in azioni "
        "fino al rientro). Ogni partita è verificata confrontando i minuti ricostruiti con "
        "quelli ufficiali (scarto massimo 3'); le altre partite sono escluse.",
        "Il quintetto con più minuti è quello di cui l'allenatore si fida; un quintetto con "
        "Net rating molto negativo è un'opportunità per l'avversario."),
    "clutch": Voce(
        "Finali punto a punto (clutch)",
        "Chi decide le partite equilibrate e come.",
        "Azioni negli ultimi 5 minuti del 4° quarto e nei supplementari, con scarto di 5 punti o "
        "meno al momento dell'azione.",
        "La 'quota tiri' dice a chi va la palla nei momenti decisivi: è il giocatore da "
        "togliere dalla partita nel finale."),
    "assist_rete": Voce(
        "Chi serve chi",
        "Le combinazioni passaggio-tiro più frequenti della squadra.",
        "Ogni assist della cronaca è abbinato al canestro registrato nello stesso istante.",
        "Una coppia dominante (es. play → centro) indica un'azione ricorrente da preparare in "
        "difesa: togliere quella linea di passaggio."),
    "spiegazione": Voce(
        "Perché questa previsione",
        "Quanto pesa ogni fattore sulla probabilità di vittoria.",
        "Il margine atteso è la somma di più parti: vantaggio del campo, differenza di "
        "attacco, differenza di difesa e quanto conta ancora la stagione precedente. Il peso "
        "di un fattore è quanto cambierebbe la probabilità togliendo solo quel fattore.",
        "Barre blu a favore della squadra di casa, arancio a favore dell'ospite. A inizio "
        "stagione la stagione precedente pesa di più, poi lascia spazio ai numeri di quest'anno."),
    "scenari": Voce(
        "Scenari: e se…",
        "Come cambia la previsione con condizioni diverse: assenze, campo neutro, forma della "
        "squadra secondo lo staff.",
        "Un'assenza toglie alla squadra l'impatto stimato del giocatore moltiplicato per la "
        "quota di minuti che gioca di solito. La correzione dello staff sposta la forza della "
        "squadra in punti per 100 possessi.",
        "Serve a ragionare, non a prevedere con certezza: l'impatto di un singolo giocatore è "
        "una stima con margine di errore, soprattutto con pochi minuti in archivio."),
    "impatto": Voce(
        "Impatto del giocatore",
        "Di quanto cambia l'efficienza della squadra quando il giocatore è in campo rispetto a "
        "chi lo sostituisce.",
        "On-Off dalla cronaca (Net rating con il giocatore in campo meno quello con il "
        "giocatore fuori), ristretto verso 0 in proporzione ai minuti giocati e limitato a ±8. "
        "Senza cronaca si usa il Game Score per 40 minuti rispetto alla mediana del campionato.",
        "Un valore di +5 vuol dire circa 5 punti in più ogni 100 possessi con lui in campo."),
    "forza": Voce(
        "Forza stimata",
        "Quanto una squadra è migliore o peggiore di una squadra media, in punti ogni 100 "
        "possessi.",
        "Media bayesiana tra un terzo del Net rating della stagione precedente e il Net rating "
        "di quest'anno: più partite si giocano, più conta quest'anno. La forbice indica "
        "l'incertezza (intervallo al 90%).",
        "+8 è una squadra di vertice, 0 una squadra media, −8 una squadra in difficoltà."),
    "validazione": Voce(
        "Validazione retrospettiva",
        "Quanto sarebbero state giuste le previsioni del modello sulle partite già giocate.",
        "Per ogni partita in archivio si rifà la previsione usando solo i dati disponibili "
        "prima di quella partita, poi la si confronta con il risultato. Il Brier score misura "
        "la qualità delle probabilità (0 = perfetto, 0,25 = come tirare una moneta).",
        "Il confronto con riferimenti semplici (vince sempre la squadra di casa, vince chi ha "
        "il record migliore) mostra quanto il modello aggiunge."),
    "calibrazione": Voce(
        "Calibrazione",
        "Se le probabilità sono oneste: quando il modello dice 70%, la favorita deve vincere "
        "circa 7 volte su 10.",
        "Le partite sono divise per fasce di probabilità della favorita; per ogni fascia si "
        "confronta la probabilità media prevista con la percentuale di vittorie reali.",
        "Punti vicini alla diagonale tratteggiata indicano un modello ben calibrato."),
    "registro": Voce(
        "Registro delle previsioni",
        "Le previsioni fatte davvero prima delle partite, conservate e verificate dopo.",
        "Ogni lunedì, dopo l'aggiornamento dei dati, si salvano le previsioni delle partite non "
        "ancora giocate. Dopo la partita la previsione non cambia più.",
        "È la prova più trasparente: nessuna previsione può essere corretta a posteriori."),
    "modello": Voce(
        "Il modello",
        "Come vengono calcolate le previsioni.",
        "Forza bayesiana delle squadre, ritmo, vantaggio del campo e variabilità della partita; "
        "simulazione Monte Carlo per la classifica.",
        "Modello statistico trasparente, tarato e validato sui dati delle stagioni precedenti."),
    "rotazioni": Voce(
        "Rotazioni",
        "Come l'allenatore distribuisce i minuti: chi parte titolare, quando entrano i cambi, "
        "chi è in campo nei finali.",
        "Dalla cronaca si ricostruisce chi è in campo secondo per secondo (solo partite con "
        "quintetti verificati sui minuti ufficiali). Per ogni minuto di gioco si conta in quale "
        "percentuale di partite ogni giocatore era in campo.",
        "Una riga accesa da inizio a fine quarto indica un titolare con minuti stabili; "
        "macchie a metà quarto indicano i cambi abituali. Utile per prevedere quando entrerà "
        "un giocatore e preparare i quintetti di risposta."),
    "taglia": Voce(
        "Quintetti alti e bassi",
        "Come rende una squadra a seconda dell'altezza dei cinque in campo.",
        "Per ogni quintetto si calcola l'altezza media (anagrafica ufficiale). Le soglie tra "
        "piccolo, medio e grande sono i terzili del campionato, pesati per minuti. Poi si "
        "calcolano punti fatti e subiti ogni 100 possessi con ciascuna taglia.",
        "Se una squadra soffre quando gioca piccola, conviene forzarla a quei quintetti (per "
        "esempio con falli sui lunghi). Sotto i 10 minuti giocati il dato non è mostrato."),
    "momenti": Voce(
        "Momenti della partita",
        "Quanto vince o perde una squadra nei momenti che spesso decidono le partite.",
        "Dalla cronaca: punti fatti meno subiti, a partita, nei primi 3 minuti, negli ultimi 2 "
        "minuti di ogni quarto, nei primi 3 minuti del terzo quarto e negli ultimi 5 minuti.",
        "Un valore negativo nei primi minuti del terzo quarto indica rientri dallo spogliatoio "
        "difficili; uno positivo negli ultimi 2 minuti dei quarti indica buona gestione dei "
        "possessi finali. Il badge indica la posizione nel campionato."),
    "post_partita": Voce(
        "Report post-partita",
        "La partita confrontata con la media della squadra e con gli obiettivi dello staff.",
        "Four Factors della partita contro la media stagionale e gli obiettivi impostati in "
        "La mia squadra; Game Score di ogni giocatore contro la sua media stagionale.",
        "La voce che ha pesato di più è quella che si discosta di più dalla media, nel verso "
        "che spiega il risultato. Differenze di Game Score oltre ±5 sono partite molto sopra "
        "o sotto il rendimento abituale."),
    "traduzione": Voce(
        "Dalla B all'A2",
        "Stima di come cambiano le statistiche di un giocatore passando dalla B Nazionale "
        "all'A2.",
        "Si confrontano le statistiche per 40 minuti dei giocatori che hanno giocato in entrambe "
        "le categorie (nella stessa stagione o in due consecutive): per punti, rimbalzi, assist "
        "e Game Score il rapporto mediano, per TS% e usage la differenza mediana.",
        "È una stima media: un giocatore può fare meglio o peggio. Più giocatori ci sono nel "
        "confronto, più la stima è affidabile."),
    "presenze": Voce(
        "Presenze",
        "Quanto spesso un giocatore è stato disponibile.",
        "Partite della squadra dalla prima all'ultima volta in cui il giocatore è a referto, "
        "meno quelle in cui non era a referto (infortunio, squalifica, scelta tecnica, "
        "trasferimento).",
        "Sotto l'85% conviene approfondire il motivo delle assenze prima di un ingaggio."),
    "riposo": Voce(
        "Riposo e trasferte",
        "Come rende una squadra con poco riposo o dopo trasferte lunghe.",
        "Giorni dalla partita precedente (qualsiasi competizione presente nei dati) e distanza "
        "tra la città della squadra e quella del palazzetto, stimata su strada (linea d'aria "
        "+ 25%).",
        "Con poche partite per categoria i numeri vanno letti come indicazioni, non certezze."),
    "origini": Voce(
        "Origine dei punti",
        "Da quali situazioni nascono i punti: dopo una palla persa avversaria, da un rimbalzo "
        "offensivo (seconda occasione), in contropiede.",
        "Stima dalla cronaca: ogni canestro è attribuito all'ultimo evento che ha dato il "
        "possesso alla squadra; contropiede = segnato entro 8 secondi da un rimbalzo "
        "difensivo o un recupero.",
        "Molti punti da palle perse o in contropiede = squadra che vive di transizione: "
        "proteggere la palla e rientrare in difesa. Molte seconde occasioni = chiudere l'area."),
    "break": Voce(
        "Break (parziali)",
        "La capacità di piazzare (o subire) parziali che girano la partita.",
        "Sequenze di almeno 8 punti consecutivi di una squadra senza risposta dell'avversario.",
        "Una squadra che subisce molti break ha cali di concentrazione: il timeout giusto al "
        "momento giusto conta."),
    "bonus": Voce(
        "Bonus falli",
        "Quanto spesso e quanto presto la squadra arriva al 5° fallo di squadra nel periodo, "
        "mandando l'avversario ai liberi a ogni fallo.",
        "Percentuale di periodi in cui la squadra commette almeno 5 falli e minuto medio del "
        "5° fallo.",
        "Una squadra che va presto in bonus va attaccata in penetrazione per prendere liberi."),
    "timeout_eff": Voce(
        "Effetto dei timeout",
        "Se i timeout dell'allenatore cambiano l'inerzia della partita.",
        "Differenza punti della squadra nei 2 minuti dopo ogni proprio timeout (e, per "
        "confronto, nei 2 minuti prima).",
        "Prima molto negativa e dopo positiva = timeout efficaci per fermare i parziali."),
    "prob_vittoria": Voce(
        "Probabilità di vittoria",
        "Una stima della probabilità di vincere la partita, dai dati della stagione.",
        "Margine atteso = (forza casa − forza ospite) × possessi / 100 + vantaggio del campo; "
        "probabilità = distribuzione normale con deviazione di 11 punti. La forza è il Net "
        "rating corretto per il numero di partite e, a inizio stagione, per la stagione "
        "precedente.",
        "È un riferimento statistico, non tiene conto di infortuni o mercato: 60% vuol dire "
        "che su 10 partite simili se ne vincono circa 6."),
    "simulazione": Voce(
        "Proiezione della classifica",
        "Come potrebbe finire la stagione regolare.",
        "Il resto del calendario viene giocato 5.000 volte al computer con le probabilità di "
        "ogni partita (e l'incertezza sulla forza delle squadre).",
        "Le zone (primo posto, prime 4, prime 8, ultimi 3) sono indicative: vanno allineate "
        "alla formula ufficiale del campionato in basket/config.py."),
    "somiglianza": Voce(
        "Giocatori simili",
        "Giocatori con un profilo statistico vicino, anche in altre stagioni o nell'altra "
        "categoria: utile per trovare un sostituto.",
        "Distanza su 13 caratteristiche standardizzate (punti, rimbalzi, assist, perse, "
        "recuperi e stoppate per 40', quota da 3, liberi, TS%, usage, AST%, REB%).",
        "Somiglianza sopra 70 = profilo molto vicino; sotto 40 = solo in parte simile. Non "
        "considera difesa e intangibili: è un punto di partenza per il video."),
    "ruolo": Voce(
        "Ruolo stimato",
        "Il sito non pubblica i ruoli: sono stimati da altezza e statistiche.",
        "Lungo: altezza ≥ 203 cm o REB% ≥ 14; Play / guardia: AST% ≥ 22 o altezza ≤ 186 cm; "
        "gli altri Esterno / ala.",
        "Indicativo: per i giocatori senza altezza conta solo lo stile statistico."),
    "talenti": Voce(
        "Talenti di B Nazionale",
        "Giovani di B Nazionale con minuti importanti e alto rendimento: candidati per l'A2.",
        "Indice = 50% percentile Game Score per 40' + 25% percentile TS% + 25% percentile "
        "usage, tra i giocatori di B con almeno 15' di media e l'età indicata.",
        "Un punto di partenza per lo scouting video, da integrare con il livello della squadra."),
    "eta": Voce(
        "Età, nazionalità, altezza",
        "Anagrafica dalla pagina del giocatore sul sito della Lega.",
        "Età calcolata alla data di oggi; 'italiano' = nazionalità ITA.",
        "La nazionalità non coincide sempre con lo status di formazione italiana previsto dai "
        "regolamenti: va verificato sul tesseramento."),
    "fabbisogni": Voce(
        "Fabbisogni della squadra",
        "Le carenze della squadra rispetto al campionato, tradotte nel tipo di giocatore che "
        "servirebbe (tiratore, playmaker, rimbalzista, protettore del ferro, difensore "
        "perimetrale, attaccante del ferro, realizzatore).",
        "Per ogni tipo si guarda la posizione della squadra nelle metriche collegate (es. per il "
        "tiratore: eFG% e % da 3). Priorità alta = la squadra è nell'ultimo quarto del "
        "campionato, media = sotto la metà.",
        "È un punto di partenza statistico: va incrociato con infortuni, budget, regolamento "
        "sugli stranieri e idee dell'allenatore."),
    "adattamento": Voce(
        "Adattamento al profilo",
        "Quanto un giocatore corrisponde al tipo cercato.",
        "Media pesata dei percentili del giocatore nelle metriche del profilo, calcolati "
        "all'interno della sua categoria (A2 o B Nazionale). Le percentuali sono stimate in modo "
        "prudente: con pochi tentativi vengono avvicinate alla media del campionato. Servono "
        "almeno 10' di media e un volume minimo (es. 4 tiri da 3 per 40' per il tiratore).",
        "90+ = profilo quasi perfetto; 70-90 = buona corrispondenza. I candidati mostrati "
        "superano il migliore già in rosa per quel profilo. Un giocatore di B con lo stesso "
        "punteggio di uno di A2 ha numeri ottenuti contro avversari meno forti."),
}

# Etichette di colonna delle tabelle -> voce del glossario
COLONNE = {
    "Pace": "pace", "Possessi": "possessi", "ORtg": "ortg", "DRtg": "drtg",
    "Net Rtg": "net_rtg", "eFG%": "efg", "eFG% avv.": "efg", "TS%": "ts", "TOV%": "tov",
    "TOV% avv.": "tov", "OREB%": "orb", "DREB%": "drb", "FT rate": "ft_rate",
    "FT rate avv.": "ft_rate", "AST ratio": "ast_ratio", "USG%": "usg", "AST%": "ast_pct",
    "REB%": "reb_ind", "STL%": "stl_blk", "BLK%": "stl_blk", "FTA/FGA": "ft_rate",
    "% tiri da 3": "t3a_rate", "Variabilità punti": "variabilita", "Game Score": "game_score",
    "GmSc": "game_score", "Val": "valutazione", "Val/40": "per40", "Punti/40": "per40",
    "V% attesa": "pyth", "V attese": "pyth", "Fortuna": "fortuna",
    "Punto a punto": "punto_a_punto", "Forza calendario": "sos", "Calendario": "sos",
    "% punti panchina": "panchina", "% minuti panchina": "panchina",
    "% punti top 2": "top2", "% canestri assistiti": "assistiti", "% punti da 3": "distribuzione",
    "Box score completo": "incompleto", "+/-": "plus_minus", "+/- per 40": "plus_minus",
    "On-Off": "on_off", "Net on": "on_off", "Net off": "on_off", "Quota tiri": "clutch",
    "Somiglianza": "somiglianza", "Ruolo": "ruolo", "Indice": "talenti", "Età": "eta",
    "Prob. vittoria": "prob_vittoria", "Punti da perse": "origini",
    "Seconde occasioni": "origini", "Contropiede": "origini", "Break fatti": "break",
    "Break subiti": "break", "Quintetto": "quintetti", "Adattamento": "adattamento",
    "Impatto (per 100 possessi)": "impatto", "Prevista %": "calibrazione",
    "Reale %": "calibrazione", "Brier": "validazione", "% da titolare": "rotazioni", "Entra al minuto": "rotazioni",
    "% in campo negli ultimi 5'": "rotazioni", "Presenze %": "presenze",
    "Tiro (TS%)": "ts", "Possessi usati (USG%)": "usg", "Assist % (AST%)": "ast_pct",
    "Rimbalzi % (REB%)": "reb_ind", "Attacco (ORtg)": "ortg", "Difesa (DRtg)": "drtg",
    "Net rating": "net_rtg", "Tiro (eFG%)": "efg", "Palle perse %": "tov",
    "Rimb. offensivi %": "orb", "Ritmo": "pace", "Valutazione": "valutazione",
    "Punti/40 attesi in A2": "traduzione", "Game Score/40 atteso in A2": "traduzione",
}


def voci_per_colonne(colonne) -> list[Voce]:
    """Voci del glossario (senza duplicati) per le colonne di una tabella."""
    viste, out = set(), []
    for c in colonne:
        k = COLONNE.get(c)
        if k and k not in viste:
            viste.add(k)
            out.append(G[k])
    return out
