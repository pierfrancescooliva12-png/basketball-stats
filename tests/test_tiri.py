"""Mappa di tiro a zone, cronologia dei tiri e sincronizzazione con il video."""

import pandas as pd
import pytest

from basket import tiri as T
from basket.note import Archivio


def _ev():
    righe = [
        # n, periodo, secondi, squadra, giocatore, tipo, zona, casa, ospite
        (0, 1, 30, 1, "a", "tiro2_fatto", "area", 2, 0),
        (1, 1, 30, 1, "b", "assist", None, 2, 0),
        (2, 1, 80, 2, "c", "tiro3_sbagliato", "tre", 2, 0),
        (3, 1, 90, 1, "a", "tiro2_sbagliato", "fuori_area", 2, 0),
        (4, 2, 700, 1, "a", "tiro3_fatto", "tre", 5, 0),
        (5, 2, 700, 2, "c", "assist", None, 5, 0),          # assist dell'altra squadra: ignorato
        (6, 2, 760, 1, "b", "tiro2_fatto", "schiacciata", 7, 0),
        (7, 2, 770, 1, "a", "tl_fatto", None, 8, 0),
    ]
    ev = pd.DataFrame(righe, columns=["n", "periodo", "secondi", "squadra_id", "giocatore_id",
                                      "tipo", "zona", "punti_casa", "punti_ospite"])
    return ev.assign(partita_id="p1", data="2025-10-05", avversario_id=2, campionato_id="ita2")


def test_tiri_zone_tempo_assist():
    t = T.tiri(_ev())
    assert len(t) == 5                                   # i liberi non sono tiri dal campo
    assert list(t["zona_mappa"]) == ["area", "tre", "media", "tre", "schiacciata"]
    assert t.loc[0, "assist_id"] == "b" and pd.isna(t.loc[3, "assist_id"])
    assert t.loc[0, "tempo"] == "09:30" and t.loc[3, "tempo"] == "08:20"   # 2° quarto, 100" giocati
    assert t.loc[3, "punteggio"] == "5-0"


def test_riepilogo_e_mappa():
    t = T.tiri(_ev())
    a = t[t["giocatore_id"] == "a"]
    r = T.confronto(a, t, partite=1).set_index("zona")
    assert r.loc["area", "tentati"] == 1 and r.loc["tre", "pct"] == 100
    assert r.loc["area_tot", "tentati"] == 1                       # nessuna schiacciata di "a"
    assert T.confronto(t, t).set_index("zona").loc["area_tot", "tentati"] == 2
    svg = T.svg_mappa(T.confronto(a, t), minimo=1)
    assert svg.count("<text") >= 6 and "Da 3" in svg


def test_video_e_formati():
    assert T.cronometro(5, 2450) == "04:10"                        # supplementare da 5'
    inizi = {1: 600, 2: 2100}
    # 1° quarto: dal ritmo misurato tra l'inizio del 1° e del 2° (pausa 2')
    assert T.stima_video(1, 300, inizi) == pytest.approx(600 + 300 * (2100 - 600 - 120) / 600)
    assert T.stima_video(2, 900, inizi) == pytest.approx(2100 + 300 * T.SECONDI_REALI_PER_SECONDO)
    assert T.stima_video(3, 1300, inizi) is None
    assert T.leggi_hms("1:02:30") == 3750 and T.leggi_hms("62:30") == 3750
    assert T.hms(3750) == "1:02:30" and T.leggi_hms("x") is None


def test_archivio_sincronizzazione(tmp_path):
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    a.set_video_sync("club", "p1", {1: 600, 2: None, 3: 4300})
    assert a.video_sync("club", "p1") == {1: 600, 3: 4300}
    assert a.video_sync("altro", "p1") == {}
