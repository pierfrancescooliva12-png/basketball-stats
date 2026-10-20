"""La mia squadra · sviluppo dei giocatori: cosa fanno bene, cosa fanno male e le aree di
miglioramento con l'obiettivo, con le foto del sito e il report in PDF."""

import pandas as pd
import streamlit as st

from basket import sviluppo as SV
from basket.report_pdf import build_sviluppo, slug

from .stato import App, storico
from .ui import esc, note_html, section, show


@st.cache_data(show_spinner="Analizzo i giocatori…")
def _schede(_ctx, mtime: float, stagione: str, sid: int) -> list[dict]:
    return SV.squadra(_ctx, sid)


@st.cache_data(show_spinner="Preparo il PDF…")
def _pdf(_ctx, mtime: float, stagione: str, sid: int) -> bytes:
    return build_sviluppo(_ctx, sid)


@st.cache_data(show_spinner=False, ttl=6 * 3600)
def _pdf_giocatore(_ctx, mtime: float, stagione: str, sid: int, gid: str) -> bytes:
    from basket import report_giocatore as RG
    g = next((x for x in _schede(_ctx, mtime, stagione, sid) if x["giocatore_id"] == gid), None)
    return RG.build(_ctx, sid, gid, storico(mtime), g=g)


def _report(a: App, sid: int):
    """Funzione per le figurine: giocatore → (crea il PDF al clic, nome del file)."""
    from basket import report_giocatore as RG
    nomi = a.ctx.nomi_giocatori

    def per(gid):
        return (lambda: _pdf_giocatore(a.ctx, a.mtime, a.stagione, sid, gid)), RG.nome_file(nomi.get(gid, gid))
    return per


def _lista(voci, segno, colore, vuoto):
    if not voci:
        return f'<div style="opacity:.65;font-size:.85rem">{esc(vuoto)}</div>'
    return "".join(f'<div style="margin:2px 0 4px;font-size:.88rem"><b style="color:{colore}">{segno}</b> '
                   f'{esc(v)}</div>' for v in voci)


def _aree(aree):
    if not aree:
        return '<div style="opacity:.65;font-size:.85rem">Nessuna voce sotto il livello del ruolo.</div>'
    out = []
    for a in aree:
        quota = (a["da"] / a["a"] if a["a"] else 0) if a["alto"] else (a["a"] / a["da"] if a["da"] else 0)
        quota = max(4, min(100, round(100 * quota)))
        punti = f" · circa {a['punti_pg']:.1f} punti a partita".replace(".", ",") \
            if pd.notna(a["punti_pg"]) and a["punti_pg"] >= 0.3 else ""
        out.append(f'<div style="margin:2px 0 8px;font-size:.88rem"><b>{esc(a["voce"])}</b><br>'
                   f'<span style="opacity:.8">{esc(a["valore"])} → obiettivo <b>{esc(a["obiettivo"])}</b>'
                   f'{esc(punti)}</span><div style="height:6px;border-radius:3px;background:#e3e8f0;'
                   f'margin-top:3px"><div style="width:{quota}%;height:6px;border-radius:3px;'
                   f'background:#d95926"></div></div></div>')
    return "".join(out)


def _foto(g):
    if g.get("foto"):
        try:
            st.image(g["foto"], width=110)
            return
        except Exception:
            pass
    ini = "".join(x[0] for x in g["nome"].split()[:2]).upper()
    st.markdown(f'<div style="width:110px;height:136px;border-radius:10px;background:#0b1220;color:#5f7397;'
                f'display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:700">'
                f'{esc(ini)}</div>', unsafe_allow_html=True)


def render(a: App):
    sid = a.mia_squadra
    if sid is None:
        st.info("Scegli la tua squadra nella Home, oppure una squadra nel filtro in alto "
                "(con gli accessi per club è impostata automaticamente).")
        return
    nome = a.ctx.nomi_squadre.get(sid, str(sid))
    giocatori = _schede(a.ctx, a.mtime, a.stagione, sid)
    if not giocatori:
        st.info("Nessun giocatore con almeno 5 minuti a partita.")
        return
    st.download_button("⬇ Report sviluppo dei giocatori (PDF)", _pdf(a.ctx, a.mtime, a.stagione, sid),
                       file_name=f"sviluppo_giocatori_{slug(nome)}.pdf", mime="application/pdf", type="primary")
    note_html("Ogni giocatore è confrontato con i giocatori di rotazione del campionato dello stesso ruolo "
              "(esterni, ali, lunghi). Un'area di miglioramento è una voce in cui è tra i più bassi del ruolo; "
              "l'obiettivo è il valore normale del ruolo e, quando si può stimare, quanti punti a partita vale "
              "raggiungerlo. Rimbalzi, assist, recuperi e falli sono a partita con i minuti del giocatore; "
              "un'azione è un tiro, una coppia di liberi o una palla persa; i punti per tiro sono i punti "
              "segnati per ogni tiro tentato, liberi compresi. Con poche partite giocate i valori vanno confermati.")

    section("Priorità di lavoro", "la prima area di miglioramento di ogni giocatore", key=None)
    righe = []
    for g in giocatori:
        x = g["aree"][0] if g["aree"] else None
        righe.append({"Giocatore": g["nome"], "Min": g["numeri"][0][1],
                      "Priorità": x["voce"] if x else "–",
                      "Ora → obiettivo": f"{x['valore']} → {x['obiettivo']}" if x else "–",
                      "Punti in gioco": f"{x['punti_pg']:.1f}".replace(".", ",")
                      if x and pd.notna(x["punti_pg"]) else "–",
                      "Altre aree": len(g["aree"]) - 1 if x else 0})
    show(pd.DataFrame(righe), voci=[])

    from . import figurine_ui
    from .stato import tema_squadra
    figurine_ui.render(a, sid, "La rosa in figurine", "clic su un giocatore: il suo report PDF da inoltrare",
                       a.tema or tema_squadra(sid, nome), pdf=_report(a, sid))

    from .schede import obiettivi_singoli
    obiettivi_singoli(a, sid, avversaria=False)

    section("I giocatori", "cosa fanno bene, cosa fanno male, dove migliorare", key=None)
    report = _report(a, sid)
    nomi = ["Tutti"] + [g["nome"] for g in giocatori]
    scelta = st.selectbox("Giocatore", nomi, key="sviluppo_giocatore")
    for g in giocatori:
        if scelta != "Tutti" and g["nome"] != scelta:
            continue
        with st.container(border=True):
            c0, c1 = st.columns([1, 6])
            with c0:
                _foto(g)
                crea, file = report(g["giocatore_id"])
                st.download_button("⬇ PDF", crea, file_name=file, mime="application/pdf", on_click="ignore",
                                   key=f"svdl_{g['giocatore_id']}", help="Report individuale da inoltrare al giocatore")
            with c1:
                meta = [x for x in (f"#{g['maglia']}" if g.get("maglia") else None, g.get("ruolo"),
                                    f"{g['altezza']} cm" if g.get("altezza") else None,
                                    f"{g['eta']} anni" if g.get("eta") else None, f"{g['partite']} partite") if x]
                numeri = " · ".join(f"<b>{v}</b> {k.lower()}" for k, v in g["numeri"])
                an = g.get("andamento")
                trend = ""
                if an:
                    (pu, pm) = an["punti"]
                    trend = (f"<br>Ultime {an['ultime']} partite: {pu:.1f} punti (stagione {pm:.1f}) · "
                             f"<b>{an['tendenza']}</b>").replace(".", ",")
                st.markdown(f'<div style="font-size:1.25rem;font-weight:700">{esc(g["nome"])}</div>'
                            f'<div style="opacity:.7;font-size:.85rem">{esc(" · ".join(map(str, meta)))}</div>'
                            f'<div style="margin-top:6px">{numeri}</div>'
                            f'<div style="opacity:.7;font-size:.85rem">{esc(g["tiro"])}{trend}</div>',
                            unsafe_allow_html=True)
            b1, b2, b3 = st.columns(3)
            b1.markdown('<div style="font-weight:700;color:#2a78d6;margin-bottom:4px">COSA FA BENE</div>'
                        + _lista(g["forza"], "+", "#2a78d6", "—"), unsafe_allow_html=True)
            b2.markdown('<div style="font-weight:700;color:#d95926;margin-bottom:4px">COSA FA MALE</div>'
                        + _lista(g["deboli"], "−", "#d95926", "Nessun difetto evidente rispetto al campionato."),
                        unsafe_allow_html=True)
            b3.markdown('<div style="font-weight:700;margin-bottom:4px">AREE DI MIGLIORAMENTO</div>'
                        + _aree(g["aree"]), unsafe_allow_html=True)
