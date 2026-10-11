"""Archivio schemi: varianti avanzate del pick and roll e soluzioni contro i cambi.

Giochi di alto livello (Serie A / EuroLeague) scritti con la stessa funzione `schema` degli
schemi base: le posizioni di ogni fase derivano dai movimenti della fase precedente.
"""

from .schemi import POS, schema  # noqa: F401  (POS usato tramite le chiavi stringa)

SCHEMI = [
    # ---- pick and roll: varianti avanzate ----
    schema("Horns twist · blocco e riblocco", "Pick and roll",
           "Dal Horns il lungo blocca, poi rovescia l'angolo e riblocca dal lato opposto: "
           "ottimo contro hedge e ice, perché il difensore che si è già schierato per "
           "spingere da una parte si ritrova il blocco alle spalle.",
           {1: "top", 2: "ang_d", 3: "ang_s", 4: "gom_s", 5: "gom_d"}, 1, [
               ("4 sale e blocca sul lato sinistro del difensore di 1, che attacca a sinistra "
                "per due palleggi: il difensore del 4 esce alto in hedge.",
                [("blocco", 4, [(66, 94)]), ("palleggio", 1, [(64, 106), (48, 98)])]),
               ("Twist: 4 si gira e riblocca dall'altro lato, 1 rientra verso destra sul nuovo "
                "blocco. 5 scende sul lato destro (dunker) per liberare il centro.",
                [("blocco", 4, [(60, 92)]), ("palleggio", 1, [(56, 104), (76, 100), (92, 84)]),
                 ("taglio", 5, [(104, 44), (108, 28)])]),
               ("4 rolla al ferro con il suo difensore in ritardo dopo il doppio cambio di "
                "direzione. 1 legge: arresto e tiro, roll di 4, o 5 se il suo uomo aiuta.",
                [("taglio", 4, [(68, 62), (72, 30)]), ("passaggio", 1, 4)]),
           ]),
    schema("Zoom · pin-down, consegnato e pick and roll", "Pick and roll",
           "L'esterno esce da un blocco verso il basso, riceve il consegnato dal 5 e subito "
           "dopo usa il suo pick and roll: contro il drop tira dal consegnato, contro l'hedge "
           "il 5 è già in movimento verso il ferro.",
           {1: "slot_d", 2: (40, 22), 3: "ang_d", 4: (46, 44), 5: (68, 98)}, 1, [
               ("1 passa a 5 in punta e si allarga in ala destra. 4 blocca verso il basso per 2, "
                "che risale lungo la linea dei 3 punti.",
                [("passaggio", 1, 5), ("taglio", 1, [(128, 76)]), ("blocco", 4, [(42, 38)]),
                 ("taglio", 2, [(30, 32), (34, 60), (44, 80)])]),
               ("5 palleggia incontro a 2 e gli consegna la palla (DHO). 4, dopo il blocco, "
                "scivola nello short corner sinistro.",
                [("palleggio", 5, [(60, 88)]), ("taglio", 2, [(48, 94), (52, 102)]),
                 ("passaggio", 5, 2), ("taglio", 4, [(32, 16)])]),
               ("Zoom: 5 non si allontana, si gira e blocca subito per 2, che attacca verso il "
                "centro prima che la difesa si riorganizzi.",
                [("blocco", 5, [(64, 98)]), ("palleggio", 2, [(58, 110), (76, 106), (90, 88)])]),
               ("5 rolla al ferro. 2 legge il lungo: se resta in drop tira dal palleggio, "
                "se esce serve 5 sul roll o scarica a 3 nell'angolo.",
                [("taglio", 5, [(70, 66), (76, 30)]), ("passaggio", 2, 5)]),
           ]),
    schema("Zipper · pick and roll laterale", "Pick and roll",
           "Taglio zipper dal blocco alla punta della linea dei 3, ricezione in ala e pick "
           "and roll laterale immediato: il blocco arriva prima che la difesa possa mettersi "
           "in ice, e il portatore attacca verso il centro contro drop o hedge.",
           {1: "top", 2: (46, 24), 3: "ang_d", 4: (56, 42), 5: "blo_d"}, 1, [
               ("4 blocca il difensore di 2 sul lato del canestro; 2 risale in zipper fino "
                "all'ala sinistra e riceve da 1.",
                [("blocco", 4, [(50, 38)]), ("taglio", 2, [(40, 36), (26, 72)]),
                 ("passaggio", 1, 2)]),
               ("1 si sposta nello slot destro. 4 sale e blocca sul lato alto per 2, che "
                "attacca verso il centro passando vicino al bloccante.",
                [("taglio", 1, [(104, 96)]), ("blocco", 4, [(32, 84)]),
                 ("palleggio", 2, [(22, 90), (40, 96), (58, 82)])]),
               ("4 rolla verso il ferro; 5 si alza al gomito per tenere occupato il suo uomo. "
                "2 legge: roll di 4, tiro in arresto o 5 sul lato debole.",
                [("taglio", 4, [(46, 54), (62, 28)]), ("taglio", 5, [(100, 58)]),
                 ("passaggio", 2, 4)]),
           ]),
    schema("Hawk · taglio UCLA e pick and roll centrale", "Pick and roll",
           "Il playmaker passa in ala e taglia sul blocco UCLA del 5, che poi sale a bloccare "
           "per l'ala: il pick and roll centrale nasce con il lato debole già vuoto. Utile "
           "contro il drop, che deve scegliere tra tiro dal palleggio e roll.",
           {1: "top", 2: "ala_d", 3: "ala_s", 4: "ang_s", 5: "ft"}, 1, [
               ("1 passa a 2 in ala destra.", [("passaggio", 1, 2)]),
               ("5 blocca alle spalle del difensore di 1 (UCLA): 1 taglia al ferro sul lato "
                "palla e, se non riceve, si svuota nell'angolo destro.",
                [("blocco", 5, [(82, 70)]), ("taglio", 1, [(92, 80), (94, 34), (138, 16)])]),
               ("5 sale e blocca per 2 sul lato alto; 2 attacca dall'ala verso il centro, "
                "passando vicino al bloccante.",
                [("blocco", 5, [(114, 86)]),
                 ("palleggio", 2, [(124, 92), (106, 98), (88, 90)])]),
               ("5 rolla al ferro. 2 legge il lungo in drop: tiro in arresto, servizio sul roll "
                "o scarico a 1 nell'angolo se l'aiuto arriva dal lato forte.",
                [("taglio", 5, [(100, 56), (84, 30)]), ("passaggio", 2, 5)]),
           ]),
    schema("Short roll · 4 contro 3 sul lato debole", "Pick and roll",
           "Contro l'hedge aggressivo o il raddoppio (blitz) sul portatore: la palla esce "
           "subito al 5 sul short roll, che gioca 4 contro 3 leggendo il difensore in "
           "rotazione dal lato debole.",
           {1: "top", 2: "ang_d", 3: "ang_s", 4: "ala_s", 5: (96, 70)}, 1, [
               ("5 sale e blocca sul lato destro del difensore di 1, che attacca a destra "
                "passando vicino al blocco.",
                [("blocco", 5, [(86, 98)]), ("palleggio", 1, [(80, 108), (96, 106), (110, 94)])]),
               ("Raddoppio su 1: 5 fa uno short roll fino alla lunetta e riceve. 4 scende dal "
                "lato debole verso la posizione dunker sinistra.",
                [("taglio", 5, [(82, 68)]), ("taglio", 4, [(30, 52), (52, 26)]),
                 ("passaggio", 1, 5)]),
               ("5 attacca l'area in palleggio e legge il difensore che ruota: se chiude su di "
                "lui, appoggio a 4 al ferro; se ruota su 4, skip a 3 o a 2 negli angoli.",
                [("palleggio", 5, [(78, 50)]), ("taglio", 4, [(64, 22)]),
                 ("passaggio", 5, 4)]),
           ]),
    schema("Horns double · pop del 4 e slip del 5", "Pick and roll",
           "Doppio blocco alto (double high): 1 sceglie il lato, il 5 si sfila al ferro "
           "prima del contatto (slip) e il 4 si apre per il tiro (pop). Efficace contro hedge "
           "e cambio, perché i due difensori dei lunghi non possono coprire roll e pop.",
           {1: (75, 108), 2: "ang_d", 3: "ang_s", 4: "gom_s", 5: "gom_d"}, 1, [
               ("4 e 5 salgono ai due lati del difensore di 1 (double high). 2 e 3 restano "
                "larghi negli angoli.",
                [("blocco", 4, [(64, 98)]), ("blocco", 5, [(86, 98)])]),
               ("1 attacca a destra sul blocco di 5, che si sfila subito verso il ferro (slip). "
                "4 si apre in pop nello slot sinistro.",
                [("palleggio", 1, [(84, 108), (98, 102), (110, 92)]),
                 ("taglio", 5, [(90, 70), (84, 32)]), ("taglio", 4, [(48, 92)])]),
               ("Il difensore di 4 è sceso sullo slip: 1 serve 4 per il tiro. 5 sigilla il suo "
                "uomo al centro dell'area per l'eventuale high-low.",
                [("passaggio", 1, 4), ("taglio", 5, [(68, 30)])]),
           ]),
    schema("Snake · rifiuto del blocco (reject)", "Pick and roll",
           "Contro l'ice o l'hedge che si schiera troppo presto per negare il centro: il "
           "portatore rifiuta il blocco, poi rientra a serpente (snake) verso il centro "
           "lasciando il lungo in drop alle sue spalle.",
           {1: "slot_s", 2: "ang_d", 3: "ala_d", 4: "ang_s", 5: (78, 72)}, 1, [
               ("5 sale e blocca sul lato centrale del difensore di 1. Il difensore si sposta "
                "per negare il centro: 1 rifiuta il blocco e attacca verso l'esterno.",
                [("blocco", 5, [(60, 98)]), ("palleggio", 1, [(40, 86), (38, 66)])]),
               ("Snake: 1 rientra in palleggio verso il centro sotto la lunetta, chiudendo il "
                "difensore alle spalle; 5 rolla verso il lato destro del ferro.",
                [("palleggio", 1, [(48, 54), (66, 54)]), ("taglio", 5, [(80, 74), (90, 34)])]),
               ("Il lungo in drop è preso tra due fuochi: 1 sceglie tra il floater, il passaggio "
                "a 5 dietro di lui o lo scarico a 2 nell'angolo.",
                [("passaggio", 1, 5)]),
           ]),

    # ---- contro i cambi ----
    schema("Slip screen · sfilarsi contro il cambio", "Contro i cambi",
           "Contro chi cambia su ogni blocco: il bloccante non arriva al contatto e taglia "
           "subito al ferro, mentre i due difensori si scambiano l'uomo e restano fermi per "
           "un istante.",
           {1: "top", 2: "ang_d", 3: "ang_s", 4: (56, 70), 5: "blo_d"}, 1, [
               ("4 sale a bloccare sul lato sinistro del difensore di 1. I difensori chiamano "
                "il cambio in anticipo; 1 porta il suo uomo verso il blocco.",
                [("blocco", 4, [(66, 92)]), ("palleggio", 1, [(68, 106)])]),
               ("Prima del contatto 4 si sfila (slip) verso il ferro; 5 libera l'area scendendo "
                "nello short corner. 1 serve 4 in corsa.",
                [("taglio", 4, [(70, 60), (74, 30)]), ("taglio", 5, [(118, 14)]),
                 ("passaggio", 1, 4)]),
           ]),
    schema("Ghost screen e riblocco", "Contro i cambi",
           "Contro il cambio anticipato: il primo bloccante finge (ghost) e si apre per il "
           "tiro; se la difesa non si sbaglia, arriva subito il blocco vero del 5 su una "
           "difesa già in movimento.",
           {1: (75, 104), 2: "ang_d", 3: "ang_s", 4: (52, 68), 5: "blo_d"}, 1, [
               ("4 corre verso il difensore di 1 come per bloccare, poi si apre senza toccarlo "
                "(ghost) nello slot sinistro. Se i due difensori saltano su 1, 4 è libero per il tiro.",
                [("taglio", 4, [(66, 96), (42, 96)])]),
               ("Riblocco: 5 sale dal fondo e blocca sul lato destro; 1 attacca a destra "
                "passando vicino al blocco.",
                [("blocco", 5, [(110, 50), (86, 96)]),
                 ("palleggio", 1, [(84, 106), (98, 102), (112, 90)])]),
               ("5 rolla al ferro contro una difesa che ha già cambiato una volta: 1 serve il "
                "roll o ribalta su 4 nello slot.",
                [("taglio", 5, [(84, 64), (80, 30)]), ("passaggio", 1, 5)]),
           ]),
    schema("Caccia al mismatch · doppio blocco e post", "Contro i cambi",
           "Contro chi cambia tutto: doppio blocco sulla palla con un esterno e il 5 per "
           "forzare il cambio, poi il 5 sigilla il piccolo in post (o 1 isola il lungo che "
           "gli è rimasto addosso).",
           {1: (56, 112), 2: "slot_d", 3: "ang_d", 4: "ang_s", 5: (96, 64)}, 1, [
               ("2 e 5 salgono e si mettono in fila sul lato destro del difensore di 1 "
                "(doppio blocco sulla palla).",
                [("blocco", 2, [(68, 106)]), ("blocco", 5, [(72, 94)])]),
               ("1 attacca a destra su entrambi i blocchi: la difesa cambia e un esterno resta "
                "sul 5. 2 si apre a sinistra, 5 rolla e sigilla il piccolo in post basso.",
                [("palleggio", 1, [(64, 118), (84, 114), (120, 82)]),
                 ("taglio", 2, [(48, 94), (28, 82)]), ("taglio", 5, [(88, 60), (102, 36)])]),
               ("1 entra in post a 5 con il mismatch. Se arriva il raddoppio, 5 scarica a 3 "
                "nell'angolo o ribalta sul lato debole.",
                [("passaggio", 1, 5)]),
           ]),
]
