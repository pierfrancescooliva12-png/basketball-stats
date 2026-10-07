"""Schemi pronti per la lavagna: situazioni classiche da cui partire e modificare.

Ogni schema è scritto come sequenza di fasi; le posizioni di ogni fase si ricavano dai
movimenti della fase precedente (come fa "+ Fase successiva" sulla lavagna), così gli
schemi restano sempre coerenti. Coordinate della metà campo: x 0-150 (sinistra-destra),
y 0-140 (dalla linea di fondo verso metà campo), canestro in (75, 15.75).
"""

import copy

# posizioni tipiche
POS = {
    "top": (75, 100), "slot_d": (100, 92), "slot_s": (50, 92),
    "ala_d": (128, 76), "ala_s": (22, 76), "ang_d": (140, 16), "ang_s": (10, 16),
    "gom_d": (96, 60), "gom_s": (54, 60), "blo_d": (100, 26), "blo_s": (50, 26),
    "short_d": (118, 14), "short_s": (32, 14), "post_d": (102, 36), "post_s": (48, 36),
    "ferro": (75, 24), "ft": (75, 60),
}


def _p(x):
    return list(POS[x]) if isinstance(x, str) else list(x)


def schema(nome: str, categoria: str, descrizione: str, partenza: dict, palla: int,
           fasi: list[tuple[str, list]]) -> dict:
    """partenza: {numero: posizione}. fasi: [(nota, [linee])], linea =
    ("taglio"|"palleggio"|"blocco", numero, [punti...]) oppure ("passaggio", da, a)."""
    gioc = [{"id": f"o{n}", "tipo": "o", "n": n, "x": _p(p)[0], "y": _p(p)[1]}
            for n, p in sorted(partenza.items())]
    out_fasi = []
    portatore = f"o{palla}"
    for i, (nota, linee) in enumerate(fasi):
        pos = {g["id"]: [g["x"], g["y"]] for g in gioc}
        arrivi = {}
        righe = []
        for k, l in enumerate(linee):
            tipo = l[0]
            if tipo == "passaggio":
                continue
            da = f"o{l[1]}"
            punti = [pos[da]] + [_p(q) for q in l[2]]
            arrivi[da] = punti[-1]
            righe.append({"id": f"s{i}_{k}", "tipo": "movimento" if tipo == "taglio" else tipo,
                          "da": da, "punti": punti})
        nuovo = portatore
        palleggiano = {f"o{l[1]}" for l in linee if l[0] == "palleggio"}
        for k, l in enumerate(linee):
            if l[0] != "passaggio":
                continue
            da, a = f"o{l[1]}", f"o{l[2]}"
            # chi palleggia passa da dove arriva; chi passa e poi taglia, da dove parte
            p0 = arrivi[da] if da in palleggiano else pos[da]
            p1 = arrivi.get(a, pos[a])
            righe.append({"id": f"s{i}_p{k}", "tipo": "passaggio", "da": da, "a": a,
                          "punti": [p0, p1]})
            nuovo = a
        out_fasi.append({"giocatori": copy.deepcopy(gioc), "linee": righe, "palla": portatore,
                         "nota": nota})
        for g in gioc:
            if g["id"] in arrivi:
                g["x"], g["y"] = arrivi[g["id"]]
        portatore = nuovo
    out_fasi.append({"giocatori": copy.deepcopy(gioc), "linee": [], "palla": portatore,
                     "nota": "Posizioni finali: da qui si legge la difesa."})
    sid = "schema_" + "".join(c for c in nome.lower() if c.isalnum())[:40]
    return {"id": sid, "nome": nome, "categoria": categoria, "descrizione": descrizione,
            "tipo": "nostro", "difesa": False, "palla": f"o{palla}", "fasi": out_fasi}


CINQUE_FUORI = {1: "top", 2: "ala_d", 3: "ala_s", 4: "ang_d", 5: "ang_s"}
HORNS = {1: "top", 2: "ang_d", 3: "ang_s", 4: "gom_s", 5: "gom_d"}

SCHEMI = [
    schema("Horns · pick and roll centrale", "Metà campo",
           "Due lunghi ai gomiti, due tiratori negli angoli: spazio per il pick and roll e "
           "per lo scarico a chi si apre.", HORNS, 1, [
               ("5 sale a bloccare per 1, che attacca a destra. 4 resta pronto ad aprirsi.",
                [("blocco", 5, [(88, 78)]), ("palleggio", 1, [(92, 92), (108, 78)])]),
               ("5 rolla verso il canestro, 4 si apre in punta. 1 legge l'aiuto: a 5 sul roll "
                "o fuori a 4.", [("taglio", 5, [(84, 50), (80, 30)]),
                                 ("taglio", 4, [(62, 82), (70, 98)]),
                                 ("passaggio", 1, 5)]),
           ]),
    schema("Horns · flare", "Metà campo",
           "Dal Horns, 1 passa al gomito e riceve un blocco cieco (flare) per il tiro da 3 "
           "in ala.", HORNS, 1, [
               ("4 si apre leggermente e riceve da 1.",
                [("taglio", 4, [(58, 72)]), ("passaggio", 1, 4)]),
               ("5 blocca in flare per 1, che si allontana verso l'ala destra per il tiro.",
                [("blocco", 5, [(90, 92)]), ("taglio", 1, [(104, 96), (124, 82)])]),
               ("4 trova 1 in ala per il tiro; se la difesa cambia, 5 taglia verso il canestro.",
                [("passaggio", 4, 1), ("taglio", 5, [(86, 60), (82, 32)])]),
           ]),
    schema("Spain pick and roll", "Metà campo",
           "Pick and roll centrale con un blocco alle spalle del difensore del lungo: "
           "difficile da difendere senza cambi.", {1: "top", 2: "ala_s", 3: "ang_s", 4: "ang_d",
                                                    5: (82, 72)}, 1, [
               ("5 blocca per 1. 2 sale alle spalle e blocca il difensore di 5.",
                [("blocco", 5, [(84, 86)]), ("blocco", 2, [(68, 72)]),
                 ("palleggio", 1, [(92, 94), (106, 82)])]),
               ("5 rolla al ferro, 2 si apre in punta per il tiro: 1 sceglie tra i due.",
                [("taglio", 5, [(82, 56), (78, 30)]), ("taglio", 2, [(62, 88), (70, 102)]),
                 ("passaggio", 1, 2)]),
           ]),
    schema("Floppy", "Metà campo",
           "Il tiratore parte sotto canestro e sceglie da che lato uscire, tra un blocco "
           "doppio e uno singolo.", {1: "top", 2: "ferro", 3: "ala_s", 4: "blo_s", 5: "blo_d"}, 1,
           [
               ("4 e 5 bloccano ai lati dell'area; 2 legge la difesa ed esce a destra.",
                [("blocco", 4, [(54, 32)]), ("blocco", 5, [(98, 32)]),
                 ("taglio", 2, [(90, 22), (108, 26), (116, 46), (124, 70)])]),
               ("1 serve 2 in ala per il tiro; 5 si gira e cerca il mismatch in post.",
                [("passaggio", 1, 2), ("taglio", 5, [(104, 30)])]),
           ]),
    schema("Elevator (porte dell'ascensore)", "Metà campo",
           "Il tiratore passa tra due lunghi che chiudono la 'porta' alle sue spalle: "
           "tiro da 3 in punta.", {1: "ala_d", 2: "ferro", 3: "ang_s", 4: (62, 82), 5: (88, 82)},
           1, [
               ("2 sale dal canestro verso lo spazio tra 4 e 5.",
                [("taglio", 2, [(75, 60), (75, 92)])]),
               ("4 e 5 si chiudono come le porte di un ascensore; 1 serve 2 in punta per il tiro.",
                [("blocco", 4, [(70, 86)]), ("blocco", 5, [(80, 86)]),
                 ("taglio", 2, [(75, 104)]), ("passaggio", 1, 2)]),
           ]),
    schema("Flex", "Metà campo",
           "Movimento continuo: taglio sul blocco in linea di fondo e blocco per il "
           "bloccante. Si ripete dai due lati.", {1: "top", 2: "ala_d", 3: "ang_s", 4: "blo_s",
                                                  5: "gom_s"}, 1, [
               ("1 ribalta su 2 in ala destra.", [("passaggio", 1, 2)]),
               ("4 blocca in linea di fondo per 3, che taglia verso il ferro (taglio flex). "
                "5 scende a bloccare per 4, che sale in ala sinistra.",
                [("blocco", 4, [(46, 24)]), ("taglio", 3, [(34, 18), (60, 22), (92, 26)]),
                 ("blocco", 5, [(50, 40)]), ("taglio", 4, [(40, 40), (46, 64), (50, 90)]),
                 ("passaggio", 2, 3)]),
           ]),
    schema("Chicago (blocco e consegnato)", "Metà campo",
           "Uscita dal blocco verso un consegnato in palleggio, poi pick and roll: tre "
           "letture in un'azione.", {1: "slot_s", 2: "blo_s", 3: "ang_d", 4: "post_s",
                                     5: "gom_d"}, 1, [
               ("4 blocca verso il basso per 2, che esce verso 1. 1 palleggia incontro.",
                [("blocco", 4, [(50, 40)]), ("taglio", 2, [(42, 46), (40, 74)]),
                 ("palleggio", 1, [(44, 84)])]),
               ("1 consegna a 2 (dribble hand-off) e taglia; 5 sale a bloccare per 2.",
                [("passaggio", 1, 2), ("taglio", 1, [(30, 88), (16, 60), (14, 30)]),
                 ("blocco", 5, [(60, 74)])]),
               ("2 attacca il centro sul blocco di 5, che rolla: 2 legge il roll o lo scarico.",
                [("palleggio", 2, [(56, 82), (76, 74)]), ("taglio", 5, [(70, 48), (74, 28)]),
                 ("passaggio", 2, 5)]),
           ]),
    schema("Hammer", "Metà campo",
           "Penetrazione dal fondo e blocco sul lato debole per il tiratore nell'angolo "
           "opposto: tiro da 3 sullo scarico lungo.", {1: "ala_d", 2: "top", 3: "ala_s",
                                                       4: "post_s", 5: "gom_d"}, 1, [
               ("1 attacca dal fondo; 3 scivola verso l'angolo; 4 si prepara a bloccare.",
                [("palleggio", 1, [(136, 54), (122, 26)]), ("taglio", 3, [(14, 50), (10, 20)]),
                 ("taglio", 4, [(36, 26)])]),
               ("4 blocca il difensore di 3 (hammer); 1 scarica lungo a 3 nell'angolo.",
                [("blocco", 4, [(26, 28)]), ("passaggio", 1, 3)]),
           ]),
    schema("UCLA", "Metà campo",
           "Il playmaker passa in ala e taglia al ferro sfruttando il blocco del lungo in "
           "lunetta.", {1: "top", 2: "ala_d", 3: "ala_s", 4: "ang_s", 5: "ft"}, 1, [
               ("1 passa a 2 in ala destra.", [("passaggio", 1, 2)]),
               ("5 blocca per 1, che taglia al ferro (taglio UCLA). 5 poi sale in punta.",
                [("blocco", 5, [(82, 66)]), ("taglio", 1, [(68, 72), (72, 30)]),
                 ("passaggio", 2, 1)]),
               ("Se 1 non è libero, 5 si apre in punta e riceve per ribaltare il lato.",
                [("taglio", 5, [(75, 98)]), ("taglio", 1, [(104, 20)])]),
           ]),
    schema("Iverson", "Metà campo",
           "Due esterni attraversano la punta sui blocchi dei lunghi ai gomiti e ricevono "
           "in movimento sul lato opposto.", {1: "top", 2: "ala_d", 3: "ang_s", 4: "gom_s",
                                              5: "gom_d"}, 1, [
               ("2 attraversa sopra i blocchi di 5 e di 4 e arriva in ala sinistra.",
                [("blocco", 5, [(94, 66)]), ("blocco", 4, [(56, 66)]),
                 ("taglio", 2, [(100, 76), (75, 74), (40, 78), (24, 82)])]),
               ("1 serve 2 in ala; 4 sale a bloccare per il pick and roll laterale.",
                [("passaggio", 1, 2), ("blocco", 4, [(38, 70)])]),
           ]),
    schema("Rimessa dal fondo · box", "Rimesse",
           "Rimessa dalla linea di fondo con quattro giocatori a box: blocco per il "
           "tiratore e taglio al ferro del lungo.", {1: (88, 1), 2: "blo_s", 3: "blo_d",
                                                     4: "gom_s", 5: "gom_d"}, 1, [
               ("4 scende a bloccare per 2, che esce nell'angolo; 3 blocca in diagonale per 5.",
                [("blocco", 4, [(50, 34)]), ("taglio", 2, [(30, 22), (12, 16)]),
                 ("blocco", 3, [(86, 44)]), ("taglio", 5, [(76, 46), (68, 22)])]),
               ("1 sceglie: 5 al ferro o 2 nell'angolo per il tiro.", [("passaggio", 1, 5)]),
           ]),
    schema("Rimessa laterale · stack", "Rimesse",
           "Rimessa dal lato con tre giocatori in fila: il primo blocca, gli altri escono "
           "in direzioni opposte.", {1: (150, 78), 2: (112, 70), 3: (104, 64), 4: (96, 58),
                                     5: "top"}, 1, [
               ("4 blocca verso il basso; 3 esce verso il canestro e 2 sale verso la palla.",
                [("blocco", 4, [(96, 44)]), ("taglio", 3, [(108, 44), (100, 24)]),
                 ("taglio", 2, [(124, 86)])]),
               ("1 rimette a 2, poi entra; 5 si apre per il ribaltamento.",
                [("passaggio", 1, 2), ("taglio", 1, [(136, 60), (128, 40)]),
                 ("taglio", 5, [(56, 96)])]),
           ]),

    # ---- fine quarto: rimesse e ultimo possesso ----
    schema("Fine quarto · rimessa dal fondo con lob", "Fine quarto",
           "Pochi secondi, rimessa dal fondo: blocco alle spalle per il lob al ferro, poi "
           "blocco per il bloccante che si apre nell'angolo.",
           {1: (88, 1), 2: "blo_s", 3: "gom_d", 4: "gom_s", 5: "blo_d"}, 1, [
               ("2 blocca alle spalle di 4 (back screen): 4 taglia al ferro per il lob. 3 sale "
                "in punta come sicurezza.",
                [("blocco", 2, [(54, 48)]), ("taglio", 4, [(64, 46), (70, 24)]),
                 ("taglio", 3, [(88, 80), (75, 100)])]),
               ("Subito dopo 5 blocca per 2 (blocco per il bloccante), che esce nell'angolo. "
                "1 sceglie: lob a 4, 2 nell'angolo o 3 in punta per ripartire.",
                [("blocco", 5, [(66, 46)]), ("taglio", 2, [(36, 34), (12, 18)]),
                 ("passaggio", 1, 4)]),
           ]),
    schema("Fine quarto · rimessa laterale, blocchi in serie", "Fine quarto",
           "Rimessa laterale per il tiro da 3: un'esca taglia al ferro mentre il tiratore "
           "risale dall'angolo su due blocchi in serie (stagger).",
           {1: (150, 72), 2: "ang_s", 3: "slot_d", 4: (64, 66), 5: (44, 44)}, 1, [
               ("3 taglia verso il canestro come esca. 5 e 4 bloccano in serie per 2, che "
                "risale dall'angolo verso la punta.",
                [("taglio", 3, [(100, 60), (92, 28)]), ("blocco", 5, [(32, 44)]),
                 ("blocco", 4, [(58, 76)]),
                 ("taglio", 2, [(28, 22), (46, 40), (68, 66), (80, 98)])]),
               ("1 rimette a 2 in punta per il tiro. Se 2 è negato, 4 si apre verso la palla "
                "dopo il blocco (slip).",
                [("passaggio", 1, 2), ("taglio", 4, [(84, 72), (108, 82)])]),
           ]),
    schema("Fine quarto · rimessa dal fondo, 1 secondo", "Fine quarto",
           "Per l'ultimo secondo: quattro in fila sulla linea del tiro libero, esca "
           "nell'angolo e tiro in uscita dal doppio blocco.",
           {1: (88, 1), 2: (40, 58), 3: (110, 58), 4: (62, 58), 5: (88, 58)}, 1, [
               ("Al segnale 3 scatta nell'angolo destro (esca); 4 e 5 si stringono in un "
                "doppio blocco.",
                [("taglio", 3, [(130, 34), (140, 16)]), ("blocco", 4, [(68, 64)]),
                 ("blocco", 5, [(82, 64)])]),
               ("2 gira dietro il doppio blocco e riceve in ala per il tiro immediato; 5 si "
                "gira e sigilla verso il ferro come seconda opzione.",
                [("taglio", 2, [(52, 76), (75, 82), (100, 80), (122, 72)]),
                 ("taglio", 5, [(86, 40), (80, 26)]), ("passaggio", 1, 2)]),
           ]),
    schema("Fine quarto · ultimo possesso, blocco a 5 secondi", "Fine quarto",
           "Ultimo tiro del quarto: si consuma il cronometro, un finto blocco porta via "
           "l'aiuto e il pick and roll parte a 5 secondi dalla fine.",
           {1: (75, 112), 2: "ang_s", 3: "ang_d", 4: (40, 94), 5: (110, 94)}, 1, [
               ("1 consuma il cronometro lontano dal canestro. A 8 secondi 4 finge il blocco "
                "(ghost) e si apre in ala sinistra.",
                [("taglio", 4, [(64, 104), (24, 82)])]),
               ("A 5 secondi 5 blocca per 1, che attacca verso destra.",
                [("blocco", 5, [(88, 110)]),
                 ("palleggio", 1, [(82, 100), (100, 94), (112, 78)])]),
               ("5 rolla forte al ferro. 1 legge: tiro in arresto, 5 sul roll o scarico in "
                "angolo. Il tiro deve partire entro 2 secondi.",
                [("taglio", 5, [(94, 70), (82, 30)]), ("passaggio", 1, 5)]),
           ]),

    # ---- giochi avanzati ----
    schema("Ram · pick and roll dopo il blocco per il lungo", "Giochi avanzati",
           "Un blocco verso il basso libera il lungo che arriva in corsa sul pick and roll: "
           "la difesa non ha tempo per organizzarsi, con tre letture.",
           {1: (64, 104), 2: "ang_d", 3: "ang_s", 4: (100, 64), 5: (102, 30)}, 1, [
               ("4 blocca verso il basso per 5 (ram): 5 sale a portare il blocco sulla palla.",
                [("blocco", 4, [(98, 44)]), ("taglio", 5, [(114, 44), (102, 74), (82, 98)])]),
               ("5 blocca per 1, che attacca a destra; 4, dopo il ram, si apre in ala sinistra "
                "(pop).",
                [("blocco", 5, [(74, 108)]),
                 ("palleggio", 1, [(70, 96), (92, 92), (110, 80)]),
                 ("taglio", 4, [(80, 62), (40, 90)])]),
               ("5 rolla al ferro: 1 sceglie tra il roll di 5, il pop di 4 e lo scarico a 2 "
                "nell'angolo.",
                [("taglio", 5, [(86, 70), (80, 30)]), ("passaggio", 1, 5)]),
           ]),
    schema("Double drag in transizione", "Giochi avanzati",
           "In transizione i due lunghi arrivano in corsa e portano due blocchi in fila: "
           "il primo si apre fuori, il secondo rolla al ferro.",
           {1: (36, 118), 2: "ang_d", 3: "ang_s", 4: (70, 134), 5: (96, 136)}, 1, [
               ("1 porta palla a sinistra; 4 e 5 arrivano in corsa e bloccano in fila "
                "(double drag).",
                [("blocco", 4, [(56, 110)]), ("blocco", 5, [(72, 110)])]),
               ("1 attacca a destra su entrambi i blocchi: 4 si apre fuori (pop), 5 rolla al "
                "ferro. 1 legge l'aiuto.",
                [("palleggio", 1, [(50, 98), (76, 96), (106, 84)]),
                 ("taglio", 4, [(42, 122)]), ("taglio", 5, [(84, 80), (80, 30)]),
                 ("passaggio", 1, 5)]),
           ]),
    schema("Pistol (21) · consegnato e pick and roll", "Giochi avanzati",
           "Attacco rapido: passaggio all'ala, consegnato in corsa e pick and roll centrale "
           "prima che la difesa si sistemi.",
           {1: (46, 122), 2: (12, 50), 3: "ang_d", 4: (96, 128), 5: "blo_d"}, 1, [
               ("1 spinge a sinistra e passa a 2, che risale lungo la linea laterale.",
                [("taglio", 2, [(18, 84)]), ("passaggio", 1, 2)]),
               ("1 segue il passaggio e riceve da 2 in consegnato; 2 taglia nell'angolo. "
                "4 arriva per il blocco.",
                [("taglio", 1, [(30, 100)]), ("passaggio", 2, 1),
                 ("taglio", 2, [(14, 50), (10, 18)]), ("blocco", 4, [(44, 102)])]),
               ("1 attacca il centro sul blocco di 4, che rolla. 5 resta sul lato debole per "
                "lo scarico.",
                [("palleggio", 1, [(36, 112), (58, 106), (76, 90)]),
                 ("taglio", 4, [(54, 80), (68, 40)]),
                 ("passaggio", 1, 4)]),
           ]),
    schema("Princeton · taglio backdoor", "Giochi avanzati",
           "Quattro fuori e il lungo in lunetta alta: chi è marcato in anticipo taglia alle "
           "spalle del difensore. Se il backdoor è chiuso, 5 consegna e si riparte.",
           {1: "slot_s", 2: "ala_d", 3: "ala_s", 4: "slot_d", 5: "ferro"}, 1, [
               ("5 sale in lunetta alta e riceve da 1. 2, marcato in anticipo, porta il "
                "difensore verso l'alto.",
                [("taglio", 5, [(75, 64)]), ("passaggio", 1, 5), ("taglio", 2, [(132, 90)])]),
               ("2 taglia backdoor alle spalle del difensore e 5 lo serve con un passaggio "
                "a terra; 4 scende a riempire l'ala.",
                [("taglio", 2, [(116, 60), (84, 24)]), ("passaggio", 5, 2),
                 ("taglio", 4, [(120, 96)])]),
           ]),
    schema("Contro la zona 2-3 · short corner e high-low", "Giochi avanzati",
           "Sovraccarico di un lato contro la zona: palla nello short corner, il centro "
           "della zona deve uscire e il lungo si tuffa alle sue spalle.",
           {1: "top", 2: "ala_d", 3: "ala_s", 4: "blo_s", 5: "blo_d"}, 1, [
               ("1 passa a 2 in ala: l'ala della zona esce. 5 scivola nello short corner, 4 si "
                "alza in lunetta, 3 scende nell'angolo opposto.",
                [("passaggio", 1, 2), ("taglio", 5, [(118, 14)]),
                 ("taglio", 4, [(70, 40), (75, 58)]), ("taglio", 3, [(12, 40), (10, 18)])]),
               ("2 serve 5 nello short corner: il centro della zona esce su di lui e 4 si "
                "tuffa al ferro alle sue spalle (high-low).",
                [("passaggio", 2, 5), ("taglio", 4, [(80, 26)])]),
               ("5 serve 4 sotto canestro; se la zona collassa, scarica lungo a 3 nell'angolo "
                "opposto.", [("passaggio", 5, 4)]),
           ]),
]
