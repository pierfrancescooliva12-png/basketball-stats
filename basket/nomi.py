"""Nome breve di una squadra, uguale in piattaforma, report ed email.

Dal nome ufficiale si tolgono sponsor e parole generiche e resta la città o il nome del club:
"LTC Group Sangiorgese Basket" → "Sangiorgese", "Tecnoswitch Ruvo di Puglia" → "Ruvo di Puglia".
Prendere solo l'ultima parola darebbe "Basket".
"""

GENERICI = {"basket", "pallacanestro", "basketball", "knights", "bees", "sharks", "academy",
            "brianza"}
# nomi ufficiali in cui la regola non basta
FISSI = {"Virtus Roma GVM": "Virtus Roma"}
# la città è di due parole: "San Severo", "Reggio Calabria", "Piazza Armerina", "Napoli Est"
PRIMA = {"san", "santa", "sant'", "santo", "reggio", "piazza", "porto", "castel", "borgo"}
DOPO = {"est", "ovest", "nord", "sud"}


def nome_breve(nome) -> str:
    nome = str(nome)
    if nome in FISSI:
        return FISSI[nome]
    parole = [p for p in nome.split() if not p.isdigit() and p.lower() not in GENERICI]
    if not parole:
        return nome
    if len(parole) >= 3 and parole[-2].islower():
        return " ".join(parole[-3:])
    if len(parole) >= 2 and (parole[-1][0].islower() or parole[-2].lower() in PRIMA
                             or parole[-1].lower() in DOPO):
        return " ".join(parole[-2:])
    return parole[-1]
