"""Archivio schemi di movimento: transizione (early offense), giochi per i tiratori e
giochi in post. Stesso formato di ``schemi.py``: ogni schema è una sequenza di fasi e le
posizioni di ogni fase si ricavano dai movimenti della fase precedente.
Coordinate: x 0-150, y 0-140 (y=0 linea di fondo), canestro in (75, 15.75).
"""

from .schemi import POS, schema  # noqa: F401  (POS disponibile per chi estende l'archivio)

# angoli "veri" da 3 (oltre la linea dritta a x=9 / x=141)
_ANG_S = (7, 16)
_ANG_D = (143, 16)

SCHEMI = [
    # ------------------------------------------------------------------ TRANSIZIONE
    schema("Secondary break · trailer pass e consegnato (DHO)", "Transizione",
           "Dopo un rimbalzo o un canestro subito, quando la difesa è rientrata ma non è "
           "ancora schierata: il passaggio al trailer ribalta il lato e il consegnato fa "
           "partire il tiratore in velocità, con il 5 già sigillato sotto.",
           {1: (80, 128), 2: (128, 122), 3: (22, 122), 4: (40, 136), 5: (62, 136)}, 1, [
               ("1 spinge in palleggio verso l'ala destra; 2 e 3 corrono larghi fino agli "
                "angoli, 5 corre dritto al ferro (rim run) e 4 segue da trailer.",
                [("palleggio", 1, [(108, 104), (124, 84)]),
                 ("taglio", 2, [(140, 70), (143, 18)]),
                 ("taglio", 3, [(12, 70), (7, 18)]),
                 ("taglio", 5, [(64, 90), (68, 32)]),
                 ("taglio", 4, [(52, 114)])]),
               ("Trailer pass: 1 serve 4 che arriva in punta; 5 sigilla il suo uomo sul "
                "blocco sinistro, cioè sul lato dove andrà la palla.",
                [("taglio", 4, [(76, 98)]), ("taglio", 5, [(56, 30)]),
                 ("passaggio", 1, 4)]),
               ("4 palleggia verso sinistra e consegna a 3, che risale dall'angolo: se il "
                "difensore di 3 passa dietro, 3 tira; se insegue, attacca.",
                [("palleggio", 4, [(60, 96), (46, 90)]),
                 ("taglio", 3, [(12, 48), (32, 78)]), ("passaggio", 4, 3)]),
               ("3 attacca il centro usando 4 come blocco; 4 si apre (pop). 3 legge: palla a 5 "
                "sigillato se il suo difensore è dietro, scarico a 2 se aiuta l'angolo.",
                [("palleggio", 3, [(46, 72), (62, 62)]), ("taglio", 4, [(40, 104)]),
                 ("passaggio", 3, 5)]),
           ]),
    schema("Drag + ghost in transizione", "Transizione",
           "In semi-transizione contro una difesa che si accoppia in ritardo: il trailer "
           "porta un blocco 'drag' sulla palla e il tiratore finge un secondo blocco (ghost) "
           "e si riapre da 3, punendo chi raddoppia o cambia.",
           {1: (50, 130), 2: (104, 126), 3: (128, 120), 4: (20, 120), 5: (92, 138)}, 1, [
               ("1 porta palla nello slot sinistro; 3 e 4 riempiono gli angoli. 5 arriva da "
                "trailer e si piazza per il drag, 2 si avvicina come se volesse bloccare.",
                [("palleggio", 1, [(36, 110)]), ("taglio", 3, [(140, 70), (143, 18)]),
                 ("taglio", 4, [(12, 70), (7, 18)]), ("taglio", 2, [(84, 110), (70, 94)]),
                 ("blocco", 5, [(66, 122), (50, 106)])]),
               ("Drag: 1 rientra verso il centro passando stretto sul blocco di 5. 2 non "
                "blocca (ghost): appena il suo difensore si stacca verso la palla, scappa sul "
                "lato debole oltre l'arco.",
                [("palleggio", 1, [(48, 117), (66, 106), (84, 90)]),
                 ("taglio", 2, [(48, 90), (26, 84)])]),
               ("5 rolla al ferro. Se i due difensori seguono la palla, 1 serve 2 libero da 3; "
                "se il difensore di 2 resta, il roll di 5 è contro un solo aiuto.",
                [("taglio", 5, [(62, 70), (70, 34)]), ("passaggio", 1, 2)]),
           ]),
    schema("Early offense · pin-down per il tiratore in ala", "Transizione",
           "Per far tirare subito il miglior tiratore in transizione: corre la corsia fino "
           "al blocco e il trailer gli porta un blocco verso il basso mentre la difesa "
           "pensa ancora a fermare la palla.",
           {1: (75, 130), 2: (24, 122), 3: (128, 122), 4: (56, 138), 5: (96, 136)}, 1, [
               ("1 spinge nello slot destro; 2 corre la corsia fino al blocco sinistro, 3 va "
                "nell'angolo destro, 5 corre al ferro sul lato destro, 4 arriva da trailer.",
                [("palleggio", 1, [(90, 104)]), ("taglio", 2, [(20, 80), (44, 30)]),
                 ("taglio", 3, [(140, 70), (143, 18)]), ("taglio", 5, [(100, 80), (100, 32)]),
                 ("taglio", 4, [(52, 108), (54, 80)])]),
               ("4 scende a bloccare (pin-down) il difensore di 2, che esce stretto sul "
                "bloccante verso l'ala: 1 lo serve per il tiro. Se il difensore taglia sopra, "
                "2 esce a ricciolo (curl) verso il centro.",
                [("blocco", 4, [(40, 48)]), ("taglio", 2, [(36, 40), (30, 60), (26, 78)]),
                 ("passaggio", 1, 2)]),
               ("Se la difesa cambia sul blocco, 4 sigilla il piccolo sotto e 2 gli dà palla in "
                "post basso: mismatch immediato.",
                [("taglio", 4, [(50, 32)]), ("passaggio", 2, 4)]),
           ]),
    schema("Uscita veloce · rim run del 5 e sigillo", "Transizione",
           "Dopo il rimbalzo difensivo, quando il centro avversario è rimasto indietro: il 5 "
           "corre dritto al ferro, si gira e sigilla prima che la difesa si sistemi.",
           {1: (110, 130), 2: (30, 120), 3: (128, 118), 4: (52, 136), 5: (76, 138)}, 1, [
               ("1 riceve l'outlet e anticipa subito la palla a 3 in ala destra; 5 corre "
                "lungo la linea centrale verso il ferro, 2 riempie l'angolo sinistro.",
                [("taglio", 3, [(132, 80)]), ("taglio", 5, [(80, 90), (84, 44)]),
                 ("taglio", 2, [(14, 70), (7, 18)]), ("taglio", 4, [(60, 118)]),
                 ("passaggio", 1, 3)]),
               ("5 si gira e sigilla il suo uomo sul lato alto, sul blocco destro; 3 migliora "
                "l'angolo con un palleggio e lo serve. 4 arriva in punta.",
                [("taglio", 5, [(100, 30)]), ("palleggio", 3, [(134, 66)]),
                 ("taglio", 4, [(75, 102)]), ("taglio", 1, [(112, 112)]),
                 ("passaggio", 3, 5)]),
               ("Se arriva l'aiuto dal difensore di 4, 4 taglia in area (dive) e 5 lo serve; "
                "se aiuta l'angolo, scarico a 2.",
                [("taglio", 4, [(70, 62), (66, 36)]), ("passaggio", 5, 4)]),
           ]),

    # --------------------------------------------------------------------- TIRATORI
    schema("Zipper (Zip) · uscita in punta e pick and roll", "Tiratori",
           "Per mettere palla al tiratore in punta contro chi nega la ricezione: sale dal "
           "blocco sul taglio 'zipper' e riceve già in ritmo, poi gioca il pick and roll.",
           {1: (75, 104), 2: (46, 26), 3: (128, 78), 4: (58, 42), 5: (104, 30)}, 1, [
               ("1 entra in palleggio verso l'ala destra e porta 3 nell'angolo; 2 aspetta sul "
                "blocco sinistro.",
                [("palleggio", 1, [(100, 98), (124, 82)]), ("taglio", 3, [(140, 50), _ANG_D])]),
               ("4 blocca sulla linea dell'area; 2 sale lungo la linea (zipper) passando "
                "stretto sul bloccante e riceve in punta: tiro se il difensore resta dietro.",
                [("blocco", 4, [(56, 50)]), ("taglio", 2, [(44, 50), (50, 74), (66, 96)]),
                 ("passaggio", 1, 2)]),
               ("Se il difensore insegue stretto, 5 sale a portare il blocco sulla palla e 4 "
                "si apre in ala sinistra.",
                [("blocco", 5, [(96, 60), (80, 88)]), ("taglio", 4, [(32, 62), (24, 80)])]),
               ("2 attacca sul blocco verso destra; 5 rolla al ferro. 2 legge: tiro dal "
                "palleggio, roll di 5 o scarico a 3 in angolo.",
                [("palleggio", 2, [(78, 100), (96, 88)]), ("taglio", 5, [(84, 60), (84, 34)]),
                 ("passaggio", 2, 5)]),
           ]),
    schema("Stagger away · blocchi in serie sul lato debole", "Tiratori",
           "Per liberare il tiratore lontano dalla palla con due blocchi uno dopo l'altro: "
           "il difensore che insegue deve passare due ostacoli e il secondo bloccante resta "
           "pronto per il mismatch.",
           {1: (58, 100), 2: (50, 26), 3: (22, 78), 4: (100, 26), 5: (96, 60)}, 1, [
               ("4 e 5 si allineano a destra (blocchi in serie); 2 attraversa lungo la linea "
                "di fondo e sale passando stretto prima su 4, poi su 5.",
                [("blocco", 4, [(90, 34)]), ("blocco", 5, [(104, 52)]),
                 ("taglio", 2, [(66, 20), (90, 22), (108, 40), (122, 60), (130, 80)])]),
               ("1 si sposta in punta per migliorare l'angolo e serve 2 in ala destra per il "
                "tiro. Se il difensore taglia dentro, 2 si allarga (fade) verso l'angolo.",
                [("palleggio", 1, [(76, 104)]), ("passaggio", 1, 2)]),
               ("Dopo la ricezione 4 sigilla in post basso il difensore rimasto sul blocco e "
                "5 si apre al gomito: 2 sceglie tra tiro, post basso e ribaltamento.",
                [("taglio", 4, [(104, 30)]), ("taglio", 5, [(90, 66)]),
                 ("passaggio", 2, 4)]),
           ]),
    schema("Pin-down e flare · blocca il bloccante", "Tiratori",
           "Contro una difesa che aiuta sui blocchi: il tiratore prima blocca (pin-down) per "
           "un compagno, poi riceve lui un flare (screen the screener) mentre il suo "
           "difensore è impegnato ad aiutare.",
           {1: (128, 78), 2: (56, 62), 3: (48, 26), 4: (92, 66), 5: (102, 30)}, 1, [
               ("2 scende a bloccare (pin-down) per 3, che esce stretto e sale in punta; 1 "
                "dall'ala destra serve 3.",
                [("blocco", 2, [(46, 46)]),
                 ("taglio", 3, [(36, 36), (36, 56), (58, 88), (74, 98)]),
                 ("passaggio", 1, 3)]),
               ("Il difensore di 2 ha aiutato sul pin-down: 4 gli porta subito un flare e 2 "
                "si allontana dalla palla verso l'ala sinistra. 3 lo serve per il tiro.",
                [("blocco", 4, [(56, 54)]), ("taglio", 2, [(36, 58), (24, 80)]),
                 ("passaggio", 3, 2)]),
               ("Se i difensori cambiano sul flare, 4 si gira e taglia al ferro (slip): 2 "
                "lo serve sopra il piccolo.",
                [("taglio", 4, [(68, 32)]), ("passaggio", 2, 4)]),
           ]),
    schema("Pinch post · passaggio al gomito e consegnato", "Tiratori",
           "Per dare la palla in movimento al tiratore che viene negato in ala: il lungo "
           "riceve al gomito e gli consegna, chiudendo il difensore con il proprio corpo.",
           {1: (54, 100), 2: (128, 78), 3: (22, 78), 4: _ANG_S, 5: (102, 36)}, 2, [
               ("5 sale dal post basso al gomito destro (pinch post) e riceve da 2.",
                [("taglio", 5, [(96, 62)]), ("passaggio", 2, 5)]),
               ("2 finta il taglio backdoor e torna verso 5 per il consegnato: se il "
                "difensore anticipa troppo, 5 lo serve dietro sul taglio.",
                [("taglio", 2, [(120, 60), (108, 72)]), ("passaggio", 5, 2)]),
               ("2 gira sul corpo di 5 e attacca: tiro da 3 se il difensore resta dietro al "
                "consegnato. 5 rolla al ferro dopo il contatto.",
                [("palleggio", 2, [(96, 84), (84, 92)]), ("taglio", 5, [(90, 40)]),
                 ("passaggio", 2, 5)]),
           ]),
    schema("Chin · taglio dalla punta e flare", "Tiratori",
           "Dalla 1-4 alta: il playmaker taglia sul blocco cieco del gomito e lo stesso "
           "bloccante poi porta un flare al tiratore, sfruttando il difensore che si gira "
           "verso il taglio.",
           {1: (75, 102), 2: (22, 80), 3: (128, 78), 4: (54, 62), 5: (96, 62)}, 1, [
               ("1 passa a 3 in ala destra.", [("passaggio", 1, 3)]),
               ("4 sale e blocca alle spalle il difensore di 1 (chin), che taglia verso il "
                "ferro sul lato debole; 5 si apre in punta e 2 sale verso lo slot. 3 guarda "
                "il taglio, poi ribalta a 5.",
                [("blocco", 4, [(62, 78)]), ("taglio", 1, [(72, 82), (62, 52), (48, 28)]),
                 ("taglio", 5, [(84, 96)]), ("taglio", 2, [(30, 92), (46, 100)]),
                 ("passaggio", 3, 5)]),
               ("4 porta il flare al difensore di 2, che si allarga in ala sinistra; 1 si "
                "apre in angolo per togliere l'aiuto dal lato debole.",
                [("blocco", 4, [(56, 100)]), ("taglio", 2, [(34, 96), (24, 82)]),
                 ("taglio", 1, [(30, 22), _ANG_S])]),
               ("5 serve 2 per il tiro dopo il flare. Se i difensori cambiano, 4 si gira e "
                "taglia al ferro (slip) contro il piccolo.",
                [("taglio", 4, [(66, 52)]), ("passaggio", 5, 2)]),
           ]),

    # ---------------------------------------------------------------- GIOCO IN POST
    schema("Post basso · split cut dopo il passaggio in post", "Gioco in post",
           "Quando il lungo ha un vantaggio in post basso e la difesa raddoppia: dopo "
           "l'entrata i due esterni si incrociano (split), così chi aiuta lascia un tiro o "
           "un taglio.",
           {1: (76, 102), 2: (128, 78), 3: (22, 80), 4: (54, 62), 5: (100, 26)}, 2, [
               ("5 sigilla il suo uomo in post basso destro e riceve da 2 (passaggio dall'ala).",
                [("taglio", 5, [(106, 36)]), ("passaggio", 2, 5)]),
               ("Split: 2 va a bloccare per 1 verso la punta; 1 passa stretto sul blocco e "
                "scende in ala destra.",
                [("blocco", 2, [(102, 90)]), ("taglio", 1, [(94, 104), (114, 92), (132, 66)])]),
               ("2 dopo il blocco taglia in area verso il centro. 5 legge: se il difensore "
                "di 1 raddoppia scarica in ala, se aiuta quello di 2 lo serve sul taglio, "
                "altrimenti gioca 1 contro 1.",
                [("taglio", 2, [(90, 72), (82, 52)]), ("passaggio", 5, 1)]),
           ]),
    schema("High-low da Horns", "Gioco in post",
           "Contro un lungo che difende davanti o dietro il post: dal Horns la palla va al "
           "gomito e l'altro lungo si tuffa in area e sigilla, con gli angoli occupati per "
           "punire l'aiuto.",
           {1: (75, 104), 2: _ANG_D, 3: _ANG_S, 4: (54, 62), 5: (96, 62)}, 1, [
               ("4 si apre leggermente dal gomito sinistro e riceve da 1.",
                [("taglio", 4, [(52, 72)]), ("passaggio", 1, 4)]),
               ("1 si allontana in ala destra; 5 scende dal gomito opposto attraverso l'area e "
                "sigilla il suo uomo sul lato alto: 4 lo serve sopra (high-low).",
                [("taglio", 1, [(104, 100), (126, 80)]),
                 ("taglio", 5, [(86, 44), (64, 30)]), ("passaggio", 4, 5)]),
               ("5 gioca vicino al ferro; se il difensore di 3 aiuta dall'angolo, scarico a "
                "3 per il tiro da 3.",
                [("passaggio", 5, 3)]),
           ]),
    schema("Lob per il lungo · blocco orizzontale e verticale", "Gioco in post",
           "Contro un difensore che anticipa il lungo sul lato alto: un blocco orizzontale "
           "lo porta al gomito, poi un blocco cieco verticale lo libera per l'alley-oop.",
           {1: (76, 102), 2: (22, 80), 3: (128, 78), 4: (100, 26), 5: (48, 28)}, 1, [
               ("1 entra in palleggio nello slot destro, 3 si allarga in ala.",
                [("palleggio", 1, [(100, 96)]), ("taglio", 3, [(134, 66)])]),
               ("Blocco orizzontale: 4 attraversa l'area e blocca per 5, che passa sotto e sale "
                "al gomito destro. Il suo difensore insegue alto per negare la ricezione.",
                [("blocco", 4, [(64, 32)]),
                 ("taglio", 5, [(58, 20), (78, 22), (90, 40), (96, 58)])]),
               ("Blocco verticale: 4 sale alle spalle del difensore di 5, che taglia al ferro "
                "sul blocco cieco: 1 lo serve con il lob.",
                [("blocco", 4, [(90, 44)]), ("taglio", 5, [(82, 48), (72, 26)]),
                 ("passaggio", 1, 5)]),
           ]),
]
