"""Caricamento veloce: timeout con somme cumulate, analisi preparate all'avvio, utenti in memoria."""

import pandas as pd

from basket import pbp


def _timeouts_lento(ev, finestra=120):
    """La versione precedente, filtro della cronaca a ogni timeout: il riferimento."""
    t_out = ev[ev["tipo"] == "timeout"]
    scoring = ev[ev["punti"] > 0]
    by_game = {pid: g for pid, g in scoring.groupby("partita_id")}
    rows = []
    for e in t_out.itertuples():
        g = by_game.get(e.partita_id)
        if g is None:
            continue
        t = e.secondi or 0
        dopo = g[(g["secondi"] > t) & (g["secondi"] <= t + finestra)]
        prima = g[(g["secondi"] > t - finestra) & (g["secondi"] <= t)]
        d_dopo = dopo.loc[dopo.squadra_id == e.squadra_id, "punti"].sum() - \
            dopo.loc[dopo.squadra_id != e.squadra_id, "punti"].sum()
        d_prima = prima.loc[prima.squadra_id == e.squadra_id, "punti"].sum() - \
            prima.loc[prima.squadra_id != e.squadra_id, "punti"].sum()
        rows.append((e.campionato_id, e.squadra_id, d_prima, d_dopo))
    d = pd.DataFrame(rows, columns=["campionato_id", "squadra_id", "diff_prima", "diff_dopo"])
    return d.groupby(["campionato_id", "squadra_id"]).agg(
        timeout=("diff_dopo", "size"), diff_prima=("diff_prima", "mean"),
        diff_dopo=("diff_dopo", "mean")).reset_index()


def test_timeouts_come_prima():
    righe = []
    for pid in ("p1", "p2"):
        for i, (sec, sq, tipo, punti) in enumerate([
                (30, 1, "tiro2_fatto", 2), (60, 2, "tiro3_fatto", 3), (100, 1, "timeout", 0),
                (100, 1, "tl_fatto", 1),  # stesso secondo del timeout: conta "prima"
                (150, 2, "tiro2_fatto", 2), (200, 1, "tiro3_fatto", 3), (220, 1, "tiro2_fatto", 2),
                (221, 2, "timeout", 0), (300, 2, "tiro2_fatto", 2), (341, 1, "tiro2_fatto", 2),
                (500, 1, "timeout", 0)]):          # nessun punto nei due minuti dopo
            righe.append({"partita_id": pid, "campionato_id": 7, "n": i, "secondi": sec,
                          "squadra_id": sq, "tipo": tipo, "punti": punti})
    ev = pd.DataFrame(righe)
    k = ["campionato_id", "squadra_id"]
    atteso = _timeouts_lento(ev).sort_values(k).reset_index(drop=True)
    pd.testing.assert_frame_equal(pbp.timeouts(ev).sort_values(k).reset_index(drop=True), atteso,
                                  check_dtype=False)
    assert pbp.timeouts(ev[ev["tipo"] != "timeout"]).empty


def test_analisi_preparate(tmp_path, monkeypatch):
    from basket import config, precalcolo
    from basket.contesto import Contesto
    from basket import db
    if not config.DB_PATH.exists():
        return
    monkeypatch.setattr(precalcolo, "CARTELLA", tmp_path)
    f = precalcolo.prepara(config.STAGIONE)
    assert f.exists()
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    assert precalcolo.carica(ctx)
    assert "profile" in vars(ctx) and "players" in vars(ctx)       # niente da ricalcolare
    rif = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    pd.testing.assert_frame_equal(ctx.profile, rif.profile)
    # un file rovinato non blocca: si ricalcola
    f.write_bytes(b"rovinato")
    assert not precalcolo.carica(Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE))


def test_utenti_in_memoria_e_dopo_le_modifiche(tmp_path):
    from basket.note import Archivio
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    a.add_user("mario", "h1", "Club", "staff")
    assert set(a.users()) == {"mario"}
    letture = []
    vero = a._users
    a._users = lambda x: letture.append(x) or vero(x)
    a.users(); a.users()
    assert letture == []                                   # dalla memoria
    a.set_active("mario", False)
    assert a.users() == {} and letture == [False]          # rilette subito dopo la modifica
    a.set_active("mario", True)
    a.set_password("mario", "h2", cambio=False)
    assert a.users()["mario"]["password_hash"] == "h2"
    assert "mario" in a.users(anche_disattivi=True)


def test_forze_e_prossima_partita_una_volta_sola():
    from basket import config, db
    from basket.contesto import Contesto
    if not config.DB_PATH.exists():
        return
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    camp = ctx.bs["campionato_id"].iloc[0]
    a = ctx.forze(camp)
    a.iloc[0, a.columns.get_loc("squadra_id")] = -1          # chi modifica la copia non rovina la memoria
    pd.testing.assert_frame_equal(ctx.forze(camp), ctx.forze(camp))
    assert -1 not in set(ctx.forze(camp)["squadra_id"])
    sid = int(ctx.bs["squadra_id"].iloc[0])
    g = ctx.next_game(sid)
    if g is not None:
        g["casa"] = "x"
        assert ctx.next_game(sid)["casa"] != "x"


def test_archivio_e_analisi_pesanti_preparati(tmp_path, monkeypatch):
    from basket import config, db, precalcolo
    from basket.contesto import Contesto
    if not config.DB_PATH.exists():
        return
    monkeypatch.setattr(precalcolo, "CARTELLA", tmp_path)
    assert precalcolo.storico() is None
    precalcolo.prepara(config.STAGIONE)
    precalcolo.prepara_storico()
    assert not precalcolo.storico().empty
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    assert precalcolo.carica(ctx)
    assert "_forze" in vars(ctx) and "ev" in vars(ctx)
    rif = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    pd.testing.assert_frame_equal(ctx.leverage.reset_index(drop=True), rif.leverage.reset_index(drop=True))


def test_scelta_squadra_in_ordine_e_filtri_per_telefono():
    from pathlib import Path
    radice = Path(__file__).resolve().parent.parent
    assert 'key="filtri"' in (radice / "streamlit_app.py").read_text()
    css = (radice / "dashboard" / "ui.py").read_text()
    assert ".st-key-filtri" in css and ".st-key-scegli_squadra" in css
    assert "short(r.squadra).lower()" in (radice / "dashboard" / "pagine.py").read_text()
