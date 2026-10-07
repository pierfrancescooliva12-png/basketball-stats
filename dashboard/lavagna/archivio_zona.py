"""Archivio schemi: attacco alla difesa a zona (2-3, 1-3-1, 3-2, match-up, rimessa).

Solo attacco: la zona è descritta nelle note. Coordinate come in `schemi.py`.
"""

from .schemi import POS, schema

CAT = "Contro la zona"

SCHEMI = [
    # ---- zona 2-3 ----
    schema("Zona 2-3 · high-low dal gomito (21)", CAT,
           "Contro una 2-3 che protegge bene l'area: palla al gomito per costringere il centro "
           "della zona a salire, poi passaggio alto-basso al lungo che sigilla alle sue spalle.",
           {1: "top", 2: "ala_d", 3: "ala_s", 4: "post_s", 5: "blo_d"}, 1, [
               ("5 sale dal blocco al gomito destro nello spazio tra le due guardie della zona e "
                "riceve da 1. 4 resta basso sul lato opposto.",
                [("taglio", 5, [(110, 42), (96, 60)]), ("passaggio", 1, 5)]),
               ("5 si gira fronte a canestro: se il centro della zona esce su di lui, 4 lo "
                "sigilla e scende al blocco opposto. 3 scivola nell'angolo sinistro.",
                [("taglio", 4, [(66, 24)]), ("taglio", 3, [(14, 50), (8, 24)]),
                 ("passaggio", 5, 4)]),
               ("Se l'ala bassa sinistra della zona collassa su 4, 4 scarica a 3 nell'angolo "
                "per il tiro da 3; altrimenti finisce al ferro.",
                [("passaggio", 4, 3)]),
           ]),
    schema("Zona 2-3 · skip pass e taglio dal fondo (baseline runner)", CAT,
           "Allineamento 1-3-1 contro la 2-3: il tiratore corre lungo il fondo dietro la zona "
           "mentre la palla viene ribaltata con uno skip pass, e arriva nell'angolo prima "
           "dell'ala bassa.",
           {1: "top", 2: "ala_s", 3: (8, 22), 4: "ala_d", 5: "ft"}, 1, [
               ("1 passa a 2 in ala sinistra: la zona si sposta a sinistra e l'ala bassa esce "
                "su 3 nell'angolo. 5 occupa la lunetta, fra le guardie e il centro.",
                [("passaggio", 1, 2)]),
               ("2 salta la guardia con lo skip pass a 4 in ala destra; 3 corre lungo il fondo "
                "sotto il canestro fino all'angolo destro.",
                [("taglio", 3, [(36, 6), (114, 6), (142, 20)]), ("passaggio", 2, 4)]),
               ("L'ala bassa destra deve scegliere tra 3 in angolo e 5 che si tuffa alle sue "
                "spalle: 4 legge e serve l'uomo libero, di solito 3 per il tiro.",
                [("taglio", 5, [(92, 30)]), ("passaggio", 4, 3)]),
           ]),
    schema("Zona 2-3 · blocco dentro la zona (screen the zone)", CAT,
           "Contro una 2-3 che chiude bene gli angoli: il lungo blocca dall'interno l'ala "
           "bassa della zona dopo il ribaltamento, così nessuno può uscire sul tiratore in angolo.",
           {1: "top", 2: "ala_s", 3: (142, 18), 4: "ala_d", 5: "post_s"}, 1, [
               ("1 passa a 2 in ala sinistra: la zona si sposta, l'ala bassa destra si stringe "
                "verso il centro dell'area.",
                [("passaggio", 1, 2)]),
               ("2 ribalta a 1 in punta. 5 attraversa l'area e blocca dall'interno l'ala bassa "
                "destra della zona (pin screen), tagliandole la strada verso l'angolo.",
                [("taglio", 5, [(84, 34), (112, 30)]), ("passaggio", 2, 1)]),
               ("1 passa a 4 in ala destra: la guardia della zona esce su 4 e l'ala bassa è "
                "chiusa dal blocco di 5.",
                [("passaggio", 1, 4)]),
               ("4 serve 3 nell'angolo per il tiro. Se la zona cambia e il centro esce su 3, 5 "
                "si gira e taglia al ferro.",
                [("taglio", 5, [(92, 22)]), ("passaggio", 4, 3)]),
           ]),
    schema("Zona 2-3 · flare sul lato debole (flare contro la zona)", CAT,
           "Quando la guardia della zona sul lato debole si stringe verso la palla: un blocco "
           "cieco alle sue spalle libera il tiratore per lo skip pass in ala.",
           {1: "slot_d", 2: "top", 3: "ala_d", 4: "gom_s", 5: "blo_d"}, 1, [
               ("1 passa a 3 in ala destra: la guardia sinistra della zona scala in lunetta "
                "per coprire il gomito e la punta.",
                [("passaggio", 1, 3)]),
               ("4 sale e blocca alle spalle della guardia sinistra (flare screen); 2 si apre "
                "sopra il blocco verso l'ala sinistra.",
                [("blocco", 4, [(60, 90)]), ("taglio", 2, [(62, 100), (22, 74)])]),
               ("3 trova 2 con lo skip pass sopra la zona per il tiro. 4 dopo il blocco si "
                "infila in lunetta (short roll) se la guardia lo insegue.",
                [("taglio", 4, [(68, 56)]), ("passaggio", 3, 2)]),
           ]),

    # ---- zona 1-3-1 ----
    schema("Zona 1-3-1 · attacco degli angoli (baseline runner)", CAT,
           "Contro la 1-3-1, che ha un solo difensore sul fondo per due angoli: doppia punta "
           "per spezzare il vertice, poi il runner arriva nell'angolo lato palla.",
           {1: "slot_s", 2: "slot_d", 3: (8, 20), 4: (128, 74), 5: "ft"}, 1, [
               ("Due guardie contro il vertice della zona: 1 passa a 2, il vertice deve "
                "scivolare e l'ala della zona resta in mezzo tra 2 e 4.",
                [("passaggio", 1, 2)]),
               ("2 serve 4 in ala: il difensore di fondo corre verso l'angolo destro. 3 parte "
                "dall'angolo sinistro e corre lungo il fondo; 5 scende in post basso.",
                [("taglio", 3, [(36, 6), (114, 6), (142, 18)]), ("taglio", 5, [(98, 32)]),
                 ("passaggio", 2, 4)]),
               ("4 serve 3 nell'angolo: il difensore di fondo deve uscire su di lui e lascia "
                "solo il centro della zona a difendere l'area.",
                [("passaggio", 4, 3)]),
               ("Se il difensore di fondo esce forte, 5 lo sigilla sulla linea di passaggio e "
                "riceve da 3 al ferro; altrimenti 3 tira.",
                [("taglio", 5, [(88, 24)]), ("passaggio", 3, 5)]),
           ]),

    # ---- zona 3-2 ----
    schema("Zona 3-2 · 1-4 alto, attacco del gap e della lunetta", CAT,
           "Contro la 3-2 (o 1-2-2) la lunetta è vuota tra la linea dei tre e quella dei due: "
           "penetrazione nel gap, palla in lunetta e passaggio alto-basso o scarico in angolo.",
           {1: (75, 104), 2: (130, 70), 3: (20, 70), 4: "gom_s", 5: "gom_d"}, 1, [
               ("1 palleggia nel gap tra il vertice e l'ala destra della zona, attirando due "
                "difensori. 5 scende al blocco, 4 si sposta in lunetta.",
                [("palleggio", 1, [(92, 90)]), ("taglio", 5, [(108, 44), (100, 30)]),
                 ("taglio", 4, [(75, 62)])]),
               ("1 passa a 4 in lunetta, alle spalle della linea dei tre. 3 scende "
                "nell'angolo sinistro, fuori dalla vista dei due difensori bassi.",
                [("taglio", 3, [(14, 46), (8, 26)]), ("passaggio", 1, 4)]),
               ("4 si gira fronte a canestro: i due difensori bassi sono contro tre. Se uno "
                "sale su 4, 5 sigilla e riceve al ferro; se l'altro aiuta, scarico a 3.",
                [("taglio", 5, [(88, 24)]), ("passaggio", 4, 5)]),
           ]),

    # ---- zona match-up ----
    schema("Zona match-up · pick and roll e skip pass", CAT,
           "Contro la match-up, che difende sull'uomo ma con regole di zona: il blocco sulla "
           "palla obbliga a scegliere (cambio o aiuto) e lo skip pass punisce il lato debole "
           "che ha scalato sul roll.",
           {1: (70, 108), 2: (130, 74), 3: (20, 74), 4: (8, 22), 5: "post_d"}, 1, [
               ("5 sale a bloccare sul fianco destro del difensore di 1; 2 scende nell'angolo "
                "destro per svuotare l'ala e dare spazio alla penetrazione.",
                [("blocco", 5, [(82, 100)]), ("taglio", 2, [(142, 22)])]),
               ("1 attacca a destra sul blocco, 5 rolla forte al ferro. Il difensore basso "
                "del lato debole deve scalare sul roll.",
                [("palleggio", 1, [(78, 112), (98, 104), (110, 86)]),
                 ("taglio", 5, [(80, 60), (78, 30)])]),
               ("1 salta la zona con lo skip pass a 3 in ala sinistra: chi difende su 3 deve "
                "uscire dal centro dell'area.",
                [("passaggio", 1, 3)]),
               ("Sulla chiusura, 3 fa l'extra pass a 4 nell'angolo sinistro, rimasto solo dopo "
                "la rotazione sul roll di 5.",
                [("passaggio", 3, 4)]),
           ]),

    # ---- rimessa ----
    schema("Rimessa dal fondo contro la zona · runner e blocco", CAT,
           "Rimessa dal fondo contro la 2-3: il rimessatore è il tiratore. Dopo la rimessa "
           "corre dietro la zona verso l'angolo opposto, dove un blocco interno ferma l'ala "
           "bassa.",
           {1: "top", 2: "ft", 3: (100, 1), 4: (46, 28), 5: (104, 28)}, 3, [
               ("2 esce dalla lunetta verso l'angolo destro e riceve la rimessa da 3: l'ala "
                "bassa destra della zona esce su di lui.",
                [("taglio", 2, [(120, 44), (142, 22)]), ("passaggio", 3, 2)]),
               ("2 passa a 1 che scivola in ala sinistra alta. 3 entra in campo e corre lungo "
                "il fondo verso l'angolo sinistro; 4 blocca l'ala bassa sinistra dal lato "
                "dell'angolo.",
                [("taglio", 1, [(52, 94)]), ("taglio", 3, [(90, 6), (44, 6), (8, 20)]),
                 ("blocco", 4, [(44, 22)]), ("passaggio", 2, 1)]),
               ("1 serve 3 nell'angolo per il tiro. Se il centro della zona esce, 5 taglia "
                "al ferro dal lato opposto.",
                [("taglio", 5, [(86, 22)]), ("passaggio", 1, 3)]),
           ]),
]
