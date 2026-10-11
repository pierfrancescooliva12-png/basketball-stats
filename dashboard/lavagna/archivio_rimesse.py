"""Archivio di rimesse e situazioni di fine partita (dopo timeout) per la lavagna.

Stesso formato di `schemi.py`: ogni schema è una sequenza di fasi e le posizioni di ogni
fase si ricavano dai movimenti della precedente. Gli avversari non sono disegnati: la
difesa è descritta nelle note. Coordinate: x 0-150, y 0-140, canestro in (75, 15.75).
Regola FIBA ultimi 2 minuti: dopo il timeout la rimessa può essere spostata sulla linea di
rimessa in zona d'attacco, a 8,3 m dal fondo (qui x=150 o x=0, y=83).
"""

from .schemi import POS, schema  # noqa: F401  (POS disponibile per eventuali varianti)

FP = "Fine partita"
BLOB = "Rimesse dal fondo"
SLOB = "Rimesse laterali"

SCHEMI = [
    # ------------------------------------------------------------------ fine partita
    schema("Sotto di 3 · rimessa in attacco, flare dalla punta", FP,
           "Sotto di 3, 5-7 secondi, timeout e rimessa dalla linea in zona d'attacco: "
           "ricezione sicura del lungo in punta e flare per il tiratore che riceve lo "
           "skip da 3 in ala opposta.",
           {1: (150, 83), 2: (96, 40), 3: (6, 18), 4: (60, 60), 5: (104, 62)}, 1, [
               ("2 finge di venire verso la palla e trascina il difensore che lo anticipa; 5 "
                "sale in punta dove la difesa (attenta a negare il tiro da 3) lo lascia "
                "ricevere. 4 si porta al centro per bloccare.",
                [("taglio", 2, [(116, 66)]), ("taglio", 5, [(100, 80), (96, 100)]),
                 ("taglio", 4, [(74, 84)]), ("passaggio", 1, 5)]),
               ("Appena 5 riceve, 4 blocca in flare il difensore di 2, che ha ancora la testa "
                "sul lato palla: 2 si allontana verso l'ala sinistra, fuori dall'arco.",
                [("blocco", 4, [(74, 86)]), ("taglio", 2, [(90, 74), (40, 86)])]),
               ("5 serve lo skip a 2 per il tiro da 3 in ritmo. Se la difesa cambia sul flare, "
                "4 scivola al ferro (slip) contro il piccolo; 3 nell'angolo è la terza "
                "opzione da 3 se il suo difensore aiuta.",
                [("passaggio", 5, 2), ("taglio", 4, [(80, 60), (80, 32)])]),
           ]),
    schema("Sotto di 2 · rimessa in attacco, lob al ferro", FP,
           "Sotto di 2, 3-5 secondi, rimessa dalla linea in zona d'attacco: il blocco per "
           "il tiratore attira la difesa (che teme la tripla della vittoria) e libera un "
           "back screen per il lob del pareggio.",
           {1: (150, 83), 2: (100, 26), 3: (6, 18), 4: (75, 96), 5: (96, 62)}, 1, [
               ("5 scende a bloccare per 2, che sale forte verso la palla in ala: la difesa "
                "deve rispettare il suo tiro da 3 per la vittoria e anticipa.",
                [("blocco", 5, [(100, 42)]), ("taglio", 2, [(112, 36), (128, 78)])]),
               ("5 risale subito e blocca alla cieca il difensore di 4, girato verso 2: 4 "
                "taglia al ferro alle sue spalle. 3 resta nell'angolo per tenere lontano "
                "l'aiuto dal lato debole.",
                [("blocco", 5, [(84, 82)]), ("taglio", 4, [(72, 70), (76, 28)])]),
               ("1 alza il lob a 4 sul lato debole del ferro. Se il lungo cambia e copre il "
                "lob, 5 dopo il blocco si apre verso la palla e 2 resta libero in ala.",
                [("passaggio", 1, 4), ("taglio", 5, [(100, 100)])]),
           ]),
    schema("Ultimo tiro, 5 secondi · rimessa laterale e pick and roll", FP,
           "Pari o sotto di 1, 4-5 secondi, rimessa dalla linea in zona d'attacco a "
           "sinistra: la palla al miglior giocatore e pick and roll immediato con tre "
           "letture (arresto, roll, scarico in angolo).",
           {3: (0, 83), 1: (62, 30), 5: (48, 48), 4: (100, 62), 2: (144, 14)}, 3, [
               ("5 blocca verso il basso per 1, che esce forte verso la palla e riceve in ala "
                "sinistra; 4 sale in punta come seconda ricezione. Il cronometro parte al "
                "tocco di 1.",
                [("blocco", 5, [(46, 44)]), ("taglio", 1, [(38, 38), (26, 80)]),
                 ("taglio", 4, [(84, 96)]), ("passaggio", 3, 1)]),
               ("5 sale subito a bloccare sul lato alto del difensore: 1 attacca verso il "
                "centro. 4 si sposta in ala destra per svuotare la lunetta, 3 entra e si apre "
                "nell'angolo sinistro.",
                [("blocco", 5, [(38, 88)]),
                 ("palleggio", 1, [(30, 98), (56, 96), (68, 78)]),
                 ("taglio", 4, [(118, 86)]), ("taglio", 3, [(6, 50), (6, 18)])]),
               ("5 rolla al ferro. 1 legge a 2 secondi dalla fine: arresto e tiro se il lungo "
                "resta basso, palla a 5 se il piccolo aiuta tardi, scarico a 2 o 3 se "
                "l'angolo chiude la penetrazione.",
                [("taglio", 5, [(56, 60), (68, 30)]), ("passaggio", 1, 5)]),
           ]),
    schema("Rimessa dal fondo, 1,5 secondi · uscita in ala per il tiro", FP,
           "Pari o sotto di 2-3, 1-2 secondi, rimessa dal fondo: tutto il movimento avviene "
           "prima del tocco (il cronometro parte alla ricezione), il tiratore riceve fermo "
           "fuori dall'arco e tira subito.",
           {1: (104, 1), 2: (100, 40), 3: (140, 56), 4: (56, 60), 5: (96, 58)}, 1, [
               ("4 taglia dal gomito al ferro come esca per il lob e porta con sé l'aiuto; 3 "
                "scende nell'angolo destro. 5 blocca alle spalle del difensore di 2, che si "
                "allontana verso l'ala destra fuori dall'arco.",
                [("taglio", 4, [(66, 40), (70, 26)]), ("taglio", 3, [(144, 16)]),
                 ("blocco", 5, [(108, 50)]),
                 ("taglio", 2, [(118, 44), (128, 68)])]),
               ("1 rimette a 2 per la ricezione e tiro immediato: 1,5 secondi bastano solo "
                "per un tiro piedi a terra. Se il difensore passa sopra il blocco, 5 si gira e "
                "sigilla verso il ferro; 3 è l'opzione nell'angolo.",
                [("passaggio", 1, 2), ("taglio", 5, [(92, 30)])]),
           ]),
    schema("Ultimo tiro contro i cambi · finto blocco e slip", FP,
           "Pari, 6-8 secondi, contro una difesa che cambia su tutti i blocchi: rimessa "
           "dalla linea in zona d'attacco, finto blocco sulla palla e taglio del lungo "
           "prima del contatto (slip), con il lato debole occupato.",
           {1: (96, 50), 2: (6, 16), 3: (150, 83), 4: (54, 62), 5: (84, 72)}, 3, [
               ("1 esce dall'area verso la palla e riceve in ala alta; 4 sale nello slot "
                "sinistro. Contro chi cambia tutto la ricezione sicura c'è sempre: il lavoro "
                "vero inizia dopo.",
                [("taglio", 1, [(118, 74), (122, 98)]), ("taglio", 4, [(54, 96)]),
                 ("passaggio", 3, 1)]),
               ("5 sale come per il pick and roll; i due difensori si preparano al cambio e 5 "
                "scivola al ferro prima del contatto (slip). 4 finge un secondo blocco "
                "(ghost) e si apre; 3 entra nell'angolo destro.",
                [("taglio", 5, [(106, 90), (88, 30)]), ("taglio", 4, [(28, 84)]),
                 ("taglio", 3, [(144, 50), (144, 18)])]),
               ("1 serve 5 al ferro, dove il cambio ha lasciato il vuoto. Se un difensore del "
                "lato debole aiuta, 5 scarica a 2 o 3 negli angoli; con 3 secondi 1 può anche "
                "attaccare in isolamento il lungo rimasto su di lui.",
                [("passaggio", 1, 5)]),
           ]),

    # ------------------------------------------------------------------ rimesse dal fondo
    schema("BLOB box · blocco per il bloccante, tiro in punta", BLOB,
           "Rimessa dal fondo a box, ideale sotto di 3 o per un canestro facile con "
           "cronometro pieno: il tiratore blocca il lungo e poi riceve il blocco per il "
           "bloccante (screen the screener) per la tripla.",
           {1: (96, 1), 2: (58, 26), 3: (92, 26), 4: (58, 56), 5: (92, 56)}, 1, [
               ("2 blocca in diagonale per 5, che taglia al ferro dal gomito; 3 si apre "
                "nell'angolo destro come sicurezza. Il difensore di 2 aiuta sul taglio di 5.",
                [("blocco", 2, [(80, 48)]), ("taglio", 5, [(88, 40), (78, 22)]),
                 ("taglio", 3, [(120, 22), (144, 16)])]),
               ("4 scende a bloccare per 2 (blocco per il bloccante): 2 sale verso lo slot "
                "destro e 1 lo serve per il tiro, mentre il suo difensore è ancora sotto.",
                [("blocco", 4, [(74, 64)]), ("taglio", 2, [(86, 70), (104, 92)]),
                 ("passaggio", 1, 2)]),
               ("1 entra e si apre nell'angolo sinistro, 4 si apre (pop) in ala sinistra: se "
                "il tiro non c'è, 2 ha il campo aperto per attaccare o ribaltare.",
                [("taglio", 1, [(70, 4), (8, 8)]), ("taglio", 4, [(30, 80)])]),
           ]),
    schema("BLOB stack · fila verticale in area", BLOB,
           "Rimessa dal fondo con quattro giocatori in fila al centro dell'area, buona in "
           "ogni momento e sotto di 3: le uscite in direzioni diverse impediscono alla "
           "difesa di anticipare tutti.",
           {1: (98, 1), 5: (75, 30), 4: (75, 44), 2: (75, 58), 3: (75, 72)}, 1, [
               ("Al segnale la fila esplode: 3 scatta in punta (sicurezza), 5 si sposta sul "
                "blocco sinistro, 4 blocca il difensore di 2, che esce verso l'angolo destro "
                "lato palla.",
                [("taglio", 3, [(75, 104)]), ("taglio", 5, [(54, 24)]),
                 ("blocco", 4, [(86, 46)]),
                 ("taglio", 2, [(96, 60), (128, 44), (144, 22)])]),
               ("4 si gira e taglia al ferro (screen and dive). 1 legge il difensore di 4: se "
                "resta con lui, palla a 2 per la tripla dall'angolo; se cambia su 2, 4 è "
                "libero sotto canestro.",
                [("taglio", 4, [(80, 26)]), ("passaggio", 1, 2)]),
           ]),
    schema("BLOB diamante · cieco e lob dalla punta", BLOB,
           "Rimessa dal fondo a diamante, per un canestro facile in un finale punto a "
           "punto o sotto di 2: si svuota il centro e il giocatore in cima taglia sul "
           "blocco alle spalle per il lob.",
           {1: (100, 1), 3: (75, 30), 2: (54, 46), 5: (96, 48), 4: (75, 70)}, 1, [
               ("3, in fondo al diamante, scatta nell'angolo destro (esca e ricezione "
                "sicura); 2 si apre in ala sinistra e porta via il suo difensore: il centro "
                "dell'area resta vuoto.",
                [("taglio", 3, [(112, 20), (144, 16)]), ("taglio", 2, [(22, 78)])]),
               ("5 risale e blocca alla cieca il difensore di 4, che guarda la palla: 4 "
                "taglia al ferro passando vicino al blocco.",
                [("blocco", 5, [(84, 64)]), ("taglio", 4, [(72, 54), (74, 26)])]),
               ("1 alza il lob a 4. Se la difesa cambia, 5 si apre in punta (seconda "
                "ricezione) e il piccolo rimasto su 4 lo lascia in vantaggio sotto.",
                [("passaggio", 1, 4), ("taglio", 5, [(80, 98)])]),
           ]),
    schema("BLOB per il lungo · blocco cieco di chi rimette", BLOB,
           "Rimessa dal fondo per il lungo, utile per un canestro da 2 a pochi secondi o "
           "con il bonus: la palla va nell'angolo e chi ha rimesso entra a bloccare alla "
           "cieca il difensore del lungo.",
           {1: (98, 1), 2: (118, 58), 3: (40, 70), 4: (56, 30), 5: (102, 46)}, 1, [
               ("2 sale e poi scatta nell'angolo destro: riceve la rimessa. 4 si stacca dal "
                "ferro sul lato debole per allontanare l'aiuto.",
                [("taglio", 2, [(130, 60), (142, 22)]), ("taglio", 4, [(38, 44)]),
                 ("passaggio", 1, 2)]),
               ("1 entra subito e blocca alle spalle del difensore di 5, girato a guardare la "
                "palla nell'angolo: 5 taglia al ferro e 2 lo serve sotto canestro.",
                [("blocco", 1, [(96, 32)]), ("taglio", 5, [(88, 40), (78, 20)]),
                 ("passaggio", 2, 5)]),
           ]),

    # ------------------------------------------------------------------ rimesse laterali
    schema("SLOB box · cross e blocco per il bloccante", SLOB,
           "Rimessa laterale con quattro giocatori a box in area, in ogni fase della "
           "partita (anche sotto di 3): blocco orizzontale sul fondo e poi blocco per il "
           "bloccante, che sale in punta per il tiro.",
           {1: (150, 70), 2: (54, 30), 3: (96, 30), 4: (54, 58), 5: (96, 58)}, 1, [
               ("3 blocca in orizzontale (cross) per 2, che passa sopra il blocco verso il blocco "
                "lato palla: prima opzione, passaggio vicino al ferro.",
                [("blocco", 3, [(64, 24)]), ("taglio", 2, [(62, 40), (104, 34)])]),
               ("5 scende a bloccare per 3 (blocco per il bloccante): 3 sale in punta e 1 lo "
                "serve per il tiro, con il difensore di 3 rimasto in aiuto sul taglio di 2.",
                [("blocco", 5, [(74, 44)]), ("taglio", 3, [(64, 46), (70, 72), (84, 96)]),
                 ("passaggio", 1, 3)]),
           ]),
    schema("SLOB zipper doppio · ricezione e ribaltamento", SLOB,
           "Rimessa laterale in situazione normale o dopo timeout con 10-15 secondi: due "
           "tagli zipper simultanei verso gli slot, la difesa deve scegliere e il "
           "ribaltamento trova il lato debole scoperto.",
           {1: (150, 78), 2: (102, 28), 3: (48, 28), 4: (54, 60), 5: (96, 60)}, 1, [
               ("5 e 4 bloccano verso il basso; 2 e 3 salgono dritti lungo il bordo dell'area "
                "(zipper) verso i due slot.",
                [("blocco", 5, [(96, 52)]), ("taglio", 2, [(106, 50), (104, 84)]),
                 ("blocco", 4, [(54, 52)]), ("taglio", 3, [(44, 50), (46, 84)])]),
               ("1 rimette a 2 nello slot destro, il lato dove la difesa è più tirata.",
                [("passaggio", 1, 2)]),
               ("2 ribalta subito a 3: il suo difensore aveva aiutato sullo zipper e arriva "
                "in ritardo. 1 entra nell'angolo destro, 4 sale a bloccare per 3.",
                [("passaggio", 2, 3), ("taglio", 1, [(144, 50), (144, 18)]),
                 ("blocco", 4, [(60, 74)])]),
           ]),
    schema("SLOB lob · blocco cieco al gomito", SLOB,
           "Rimessa laterale contro una difesa che anticipa tutto (per esempio quando "
           "si è sopra di poco e serve un canestro facile): esca verso la palla e blocco "
           "alle spalle per il lob.",
           {1: (150, 72), 2: (128, 40), 3: (82, 98), 4: (54, 60), 5: (96, 62)}, 1, [
               ("2 sale verso la palla (esca e ricezione sicura); 4 si apre in ala sinistra e "
                "porta il suo difensore lontano dall'area: niente aiuto sul lato debole.",
                [("taglio", 2, [(132, 92)]), ("taglio", 4, [(24, 74)])]),
               ("5 sale e blocca alla cieca il difensore di 3, che anticipava la linea di "
                "passaggio in punta: 3 taglia al ferro passando vicino al blocco.",
                [("blocco", 5, [(86, 80)]), ("taglio", 3, [(76, 70), (78, 30)])]),
               ("1 alza il lob a 3. Se il lungo cambia e copre il ferro, 5 si apre verso la "
                "palla (slip) e 2 resta disponibile per ripartire.",
                [("passaggio", 1, 3), ("taglio", 5, [(104, 96)])]),
           ]),
]
