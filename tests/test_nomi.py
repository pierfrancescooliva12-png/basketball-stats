from basket.nomi import nome_breve


def test_nome_breve():
    attesi = {
        "LTC Group Sangiorgese Basket": "Sangiorgese",
        "Tecnoswitch Ruvo di Puglia": "Ruvo di Puglia",
        "Infodrive Capo d'Orlando": "Capo d'Orlando",
        "Allianz Pazienza Cestistica San Severo": "San Severo",
        "Rucker San Vendemiano": "San Vendemiano",
        "Myenergy Reggio Calabria": "Reggio Calabria",
        "Siaz Basket Piazza Armerina": "Piazza Armerina",
        "Skills4u Napoli Est": "Napoli Est",
        "TAV Treviglio Brianza Basket": "Treviglio",
        "Virtus Roma GVM": "Virtus Roma",
        "Elachem Vigevano 1955": "Vigevano",
        "Fiorenzuola Bees": "Fiorenzuola",
        "SAE Scientifica-Soevis Legnano Knights": "Legnano",
    }
    for nome, breve in attesi.items():
        assert nome_breve(nome) == breve, nome
