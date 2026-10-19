"""Filtri sulle statistiche: si aggiungono una alla volta ("Assist a partita" · "più di" · 5)
e valgono tutti insieme. Ci sono anche alcune ricerche pronte da cui partire."""

import pandas as pd
import streamlit as st

from basket import filtri as F

from .ui import esc


def _stato(chiave: str) -> list[dict]:
    return st.session_state.setdefault(f"filtri_{chiave}", [])


def _nuovo(f: dict) -> dict:
    """Copia del filtro con un identificativo proprio (per le chiavi dei controlli)."""
    n = st.session_state.get("_filtri_n", 0) + 1
    st.session_state["_filtri_n"] = n
    return {**f, "id": n}


def render(df: pd.DataFrame, chiave: str) -> tuple[pd.DataFrame, list[dict]]:
    """Riquadro dei filtri sopra una tabella di giocatori. Restituisce le righe filtrate e i
    filtri attivi (per mostrarne le colonne)."""
    df = F.prepara(df)
    voci = F.disponibili(df)
    filtri = _stato(chiave)
    attivi = F.validi(filtri, df)
    titolo = "Filtri sulle statistiche" + (f" · {len(attivi)} attivi" if attivi else "")
    with st.expander(titolo, expanded=bool(attivi)):
        c1, c2, c3 = st.columns([2.2, 1, 1], vertical_alignment="bottom")
        pronto = c1.selectbox("Ricerca pronta", ["—"] + list(F.PRONTI), key=f"fp_{chiave}")
        if c2.button("Usa", key=f"fu_{chiave}", disabled=pronto == "—", width="stretch"):
            filtri[:] = [_nuovo(f) for f in F.PRONTI[pronto] if f["col"] in voci]
            st.rerun()
        if c3.button("Azzera", key=f"fz_{chiave}", disabled=not filtri, width="stretch"):
            filtri.clear()
            st.rerun()
        nomi = list(voci)
        for i, f in enumerate(filtri):
            a, b, c, d = st.columns([2.2, 1.1, 1, 0.4], vertical_alignment="bottom")
            col = a.selectbox("Statistica", nomi, index=nomi.index(f["col"]) if f["col"] in nomi else 0,
                              format_func=lambda k: voci[k][0], key=f"fc_{chiave}_{f['id']}",
                              label_visibility="visible" if i == 0 else "collapsed")
            op = b.selectbox("Condizione", list(F.OPERATORI), index=list(F.OPERATORI).index(f["op"]),
                             key=f"fo_{chiave}_{f['id']}", label_visibility="visible" if i == 0 else "collapsed")
            dec, passo = voci[col][2], voci[col][3]
            val = c.number_input("Valore", value=float(f["valore"]), step=passo,
                                 format=f"%.{dec}f",
                                 key=f"fv_{chiave}_{f['id']}", label_visibility="visible" if i == 0 else "collapsed")
            f.update(col=col, op=op, valore=val)
            if d.button("✕", key=f"fx_{chiave}_{f['id']}", help="Togli questo filtro"):
                filtri.pop(i)
                st.rerun()
        if st.button("+ Aggiungi filtro", key=f"fa_{chiave}"):
            filtri.append(_nuovo({"col": "assist_pg" if "assist_pg" in voci else nomi[0],
                                  "op": "più di", "valore": 5.0}))
            st.rerun()
        attivi = F.validi(filtri, df)
        out = F.applica(df, attivi)
        if attivi:
            st.markdown(f'<div class="note">Giocatori con <b>{esc(F.descrivi(attivi))}</b>: '
                        f'{len(out)} su {len(df)}. Le percentuali con pochi tentativi vanno '
                        f'lette con cautela (usa anche il filtro sui tentativi o sulle partite).</div>',
                        unsafe_allow_html=True)
    return (F.applica(df, attivi) if attivi else df), attivi


def colonne(filtri: list[dict]) -> dict:
    """{colonna: etichetta} delle statistiche filtrate, da aggiungere alla tabella."""
    return {f["col"]: F.CATALOGO[f["col"]][0] for f in filtri if f["col"] in F.CATALOGO}
