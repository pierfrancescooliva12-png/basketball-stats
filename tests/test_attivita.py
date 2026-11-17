from basket.note import Archivio
from dashboard.admin_ui import ora_italiana


def test_registro_attivita(tmp_path):
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    a.add_user("pistoiastaff", "x", "Lumos Pistoia Basket", "staff", "admin")
    a.touch_login("pistoiastaff")
    a.touch_login("pistoiastaff")
    for p in ("Home", "Scouting", "Scouting", "Lavagna"):
        a.registra_pagina("pistoiastaff", p)
    st = a.statistiche_accessi()
    assert st["pistoiastaff"]["accessi"] == 2 and st["pistoiastaff"]["primo"]
    pg = a.pagine_aperte()
    assert pg.iloc[0].to_dict()["pagina"] == "Scouting" and int(pg.iloc[0]["volte"]) == 2
    assert len(pg) == 3


def test_ora_italiana():
    assert ora_italiana("2026-11-17T14:30:00+00:00") == "17/11/2026 15:30"     # ora solare
    assert ora_italiana("2026-07-01T14:30:00+00:00") == "01/07/2026 16:30"     # ora legale
    assert ora_italiana(None) == "–"
