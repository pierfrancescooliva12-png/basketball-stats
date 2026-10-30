"""La mia squadra: efficienza delle situazioni segnalate dallo staff nella Lavagna sul video, per tipo di
azione, per schema o per le due cose insieme (una non esclude l'altra)."""

import pandas as pd
import streamlit as st

from basket import situazioni as SI

from .stato import App
from .ui import note_html, section, show

VISTE = {"Tipo di azione": ["azione"], "Schema": ["schema"], "Azione e schema insieme": ["azione", "schema"]}
NOMI = {"azione": "Tipo di azione", "schema": "Schema"}


def _f(x, d=1):
    return "–" if pd.isna(x) else f"{x:.{d}f}".replace(".", ",")


def render(a: App, sid: int):
    section("Situazioni segnalate sul video", "come finiscono le situazioni che lo staff segna nella Lavagna sul "
            "video: per tipo di azione, per schema o per tutte e due")
    memorie = {k.split(":", 1)[1]: v for k, v in a.archivio.video_dati_tutti(a.club, "partita:").items()}
    sit = SI.situazioni(memorie, a.ctx.ev, sid)
    if sit.empty:
        note_html("Ancora nessuna situazione segnalata nelle vostre partite. Nella Lavagna sul video scegli la "
                  "partita, sincronizza il video con il cronometro e, mentre guardi, tocca i tasti «Azione» (pick and "
                  "roll centrale, transizione…) e «Schema» (con i nomi dei vostri giochi): qui vedrai quanti punti "
                  "porta ogni situazione.")
        return
    c1, c2 = st.columns(2)
    chi = c1.radio("In attacco", ["Noi", "Gli avversari"], horizontal=True, key="sit_chi")
    vista = c2.radio("Raggruppa per", list(VISTE), horizontal=True, key="sit_vista")
    attacco = "noi" if chi == "Noi" else "loro"
    per = VISTE[vista]
    tab = SI.riepilogo(sit, per, attacco)
    me = a.profile.set_index("squadra_id").loc[sid]
    media = me["ortg"] if attacco == "noi" else me["drtg"]          # punti ogni 100 possessi
    contate = sit[sit["attacco"] == attacco]
    senza_tempo, senza_esito = int((~sit["con_tempo"]).sum()), int((sit["con_tempo"] & sit["esito"].isna()).sum())
    note_html(f"{len(contate)} situazioni con {'voi' if attacco == 'noi' else 'gli avversari'} in attacco, in "
              f"{contate['partita_id'].nunique()} partite. Si contano i punti segnati in quel possesso (canestro, "
              "liberi, anche dopo un rimbalzo offensivo) ogni 100 situazioni, la stessa scala del rating: la media "
              f"{'del vostro attacco' if attacco == 'noi' else 'concessa dalla vostra difesa'} è {_f(media, 0)} punti "
              "ogni 100 possessi. Con meno di 5 situazioni il dato è solo indicativo.")
    if tab.empty:
        note_html("Nessuna situazione con questo raggruppamento: per «Azione e schema insieme» servono situazioni con "
                  "entrambi i tasti.")
    else:
        out = pd.DataFrame({NOMI[k]: tab[k] for k in per})
        out["Situazioni"] = tab["situazioni"].astype(int)
        out["Punti"] = tab["punti"].astype(int)
        out["Punti ogni 100"] = (100 * tab["punti_per_situazione"]).round(0).astype(int)
        out["Rispetto alla media"] = (100 * tab["punti_per_situazione"] - media).round(0).astype(int)
        out["Canestri / tiri"] = [f"{int(c)}/{int(t)}" + (f" ({_f(p)}%)" if pd.notna(p) else "")
                                  for c, t, p in zip(tab["canestri"], tab["tiri"], tab["perc_tiro"])]
        out["Palle perse"] = tab["perse"].astype(int)
        out["Finite ai liberi"] = tab["liberi"].astype(int)
        out["Partite"] = tab["partite"].astype(int)
        show(out.reset_index(drop=True), colori={"Rispetto alla media": attacco == "noi"}, voci=[])
    if senza_tempo or senza_esito:
        note_html("Non contate: " + ", ".join(
            x for x in [f"{senza_tempo} segnalazioni senza tempo di gioco (video non sincronizzato)" if senza_tempo else "",
                        f"{senza_esito} senza una fine del possesso nella cronaca entro 24 secondi" if senza_esito else ""]
            if x) + ".")
