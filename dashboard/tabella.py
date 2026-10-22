"""Tabelle del sito nello stile "Match day": intestazione blu notte, numeri nel font del sito,
ordinamento con un clic sull'intestazione, ricerca, CSV, intestazione e colonna del nome fisse
mentre si scorre. Verde e rosso solo sui migliori e peggiori, barre nelle celle dove servono,
la propria squadra evidenziata e il logo accanto al nome della squadra.

La tabella è un piccolo componente HTML (serve il JavaScript per ordinare e cercare): i dati
arrivano già formattati da Python, il browser li ordina e li filtra."""

import json
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from basket.figurine import maiuscole

RIGA, TESTA, BARRA, LEGENDA = 38, 44, 53, 33
MASSIMO_RIGHE = 800              # oltre, la griglia standard di Streamlit regge meglio

CSS = """
:root{--navy:#141413;--navy2:#2b2b29;--accent:#e8631c;--text:#141413;--text2:#3d3d3a;--muted:#6f6d66;
--line:#e3e0d4;--surface:#fffefb;--zebra:#faf9f5;--hover:#f3f1ea;--pos:#1f7a45;--neg:#b8432f;--posbg:#e4f1e6;
--negbg:#f8e6e0;--mia:#fbefe4;--testa:#f3f1ea}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:transparent;font-family:'Instrument Sans',system-ui,sans-serif;color:var(--text)}
.tab{display:flex;flex-direction:column;height:100%;background:var(--surface);border:1px solid var(--line);
  border-radius:12px;overflow:hidden}
.bar{display:flex;gap:10px;align-items:center;padding:9px 10px;border-bottom:1px solid var(--line);flex:none}
.bar input{flex:1;min-width:120px;max-width:260px;border:1px solid var(--line);border-radius:999px;
  padding:6px 10px 6px 30px;font:inherit;font-size:.88rem;color:var(--text);background:#f8fafc url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' fill='none' stroke='%237b8496' stroke-width='2'%3E%3Ccircle cx='6' cy='6' r='4.5'/%3E%3Cpath d='M9.5 9.5 13 13'/%3E%3C/svg%3E") 10px center no-repeat}
.bar input:focus{outline:2px solid var(--accent);outline-offset:-1px;background-color:#fff}
.bar .n{color:var(--muted);font-size:.8rem;margin-right:auto;white-space:nowrap}
.bar button{border:1px solid var(--line);background:#f0eee6;border-radius:999px;padding:5px 12px;
  font:500 .8rem 'Instrument Sans',sans-serif;color:var(--text);cursor:pointer;white-space:nowrap}
.bar button:hover{border-color:#cfd6e2;color:var(--text)}
.wrap{overflow:auto;flex:1;min-height:0}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:.9rem}
thead th{position:sticky;top:0;z-index:2;background:var(--testa);color:var(--text);font:500 .8rem 'Instrument Sans',sans-serif;
  letter-spacing:0;text-transform:none;text-align:right;padding:10px 10px 9px;white-space:nowrap;
  cursor:pointer;user-select:none;border-bottom:1px solid var(--text)}
thead th.t{text-align:left}
thead th:hover{background:#e9e6db}
thead th .ar{display:inline-block;width:9px;margin-left:4px;opacity:.3;font-size:.6rem}
thead th.on{color:var(--accent)} thead th.on .ar{opacity:1}
tbody td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap;
  font-variant-numeric:tabular-nums;background:var(--surface);height:38px}
tbody tr:nth-child(even) td{background:var(--zebra)}
tbody tr:hover td{background:var(--hover)}
tbody tr.mia td{background:var(--mia)} tbody tr.mia td:first-child{box-shadow:inset 4px 0 0 var(--accent)}
td.t{text-align:left;max-width:340px;overflow:hidden;text-overflow:ellipsis}
td.t.lungo{white-space:normal;min-width:220px;max-width:460px;line-height:1.35}
th.fix,td.fix{position:sticky;left:0;z-index:1} thead th.fix{z-index:3}
td.fix{box-shadow:1px 0 0 var(--line)}
.sq{display:flex;align-items:center;gap:8px;font-weight:600}
.sq img{width:22px;height:22px;object-fit:contain;flex:none}
.sq .lg{width:22px;height:22px;border-radius:50%;background:var(--navy2);color:#fff;font:600 .5rem 'Instrument Sans',sans-serif;
  display:flex;align-items:center;justify-content:center;flex:none;letter-spacing:.02em}
.nm{font-weight:600}
.num{font:500 .92rem 'Instrument Sans',sans-serif;letter-spacing:0}
.chip{display:inline-block;min-width:44px;padding:1px 7px;border-radius:5px}
.chip.top{background:var(--posbg);color:var(--pos);font-weight:700}
.chip.low{background:var(--negbg);color:var(--neg);font-weight:700}
.cb{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.cb .tr{width:56px;height:6px;border-radius:3px;background:#e9edf3;display:flex;flex:none}
.cb i{display:block;height:6px;border-radius:3px;background:var(--navy2)}
.fm{display:inline-flex;gap:3px}
.fm b{width:18px;height:18px;border-radius:50%;font:600 .62rem 'Instrument Sans',sans-serif;color:#fff;display:flex;
  align-items:center;justify-content:center}
.fm b.V{background:var(--pos)} .fm b.P{background:#cfcabb}
.sg.p{color:var(--pos)} .sg.n{color:var(--neg)}
.vuoto{color:var(--muted)}
.leg{display:flex;gap:16px;flex-wrap:wrap;color:var(--muted);font-size:.76rem;padding:8px 12px;
  border-top:1px solid var(--line);flex:none}
.leg span{display:inline-flex;gap:6px;align-items:center}
.leg i{width:12px;height:12px;border-radius:3px;display:inline-block}
.nulla{padding:22px;text-align:center;color:var(--muted);font-size:.9rem}
"""

JS = r"""
const T=JSON.parse(document.getElementById("dati").textContent);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const it=(v,d)=>Number(v).toLocaleString("it-IT",{minimumFractionDigits:d,maximumFractionDigits:d,useGrouping:Math.abs(v)>=10000});
const cols=T.cols, rows=T.rows;
let sort={i:null,dir:-1}, q="";
const root=document.getElementById("t");
root.innerHTML=`<div class="tab">${T.barra?`<div class="bar">${T.cerca?'<input placeholder="Cerca…" aria-label="Cerca nella tabella">':''}<span class="n"></span><button>⬇ CSV</button></div>`:''}
<div class="wrap"><table><thead><tr></tr></thead><tbody></tbody></table></div>${T.legenda?`<div class="leg">${T.legenda}</div>`:''}</div>`;
const th=root.querySelector("thead tr"), tb=root.querySelector("tbody"), n=root.querySelector(".n");
th.innerHTML=cols.map((c,i)=>`<th data-i="${i}" class="${c.t?'t':''} ${c.fix?'fix':''}" title="${esc(c.tip||'Ordina per '+c.l)}">${esc(c.l)}<span class="ar">▼</span></th>`).join("");
function cella(c,r){
  const v=r[c.i];
  const fix=c.fix?' fix':'';
  if(v===null||v===undefined) return `<td class="${c.t?'t':''}${fix}"><span class="vuoto">–</span></td>`;
  if(c.tipo==="squadra"){ const l=T.loghi[v];
    return `<td class="t${fix}"><div class="sq">${l?`<img src="${l}" alt="">`:`<span class="lg">${esc(T.sigle[v]||'')}</span>`}<span>${esc(v)}</span></div></td>`;}
  if(c.tipo==="forma") return `<td><span class="fm">${[...String(v).replace(/\s/g,"")].map(x=>`<b class="${x==='V'?'V':'P'}">${esc(x)}</b>`).join("")}</span></td>`;
  if(c.tipo==="testo") return `<td class="t${c.lungo?' lungo':''}${fix}">${c.nome?`<span class="nm">${esc(v)}</span>`:esc(v)}</td>`;
  const txt=(c.segno&&v>0?"+":"")+it(v,c.d)+(c.suf||"");
  let cls="num"+(c.segno?(v>0?" sg p":v<0?" sg n":""):"");
  if(c.alto!==undefined&&c.alto!==null){
    const top=c.alto?v>=c.hi:v<=c.hi, low=c.alto?v<=c.lo:v>=c.lo;
    if(top) return `<td><span class="${cls} chip top">${txt}</span></td>`;
    if(low) return `<td><span class="${cls} chip low">${txt}</span></td>`;}
  if(c.bar){ const w=Math.max(3,Math.min(100,100*(v-c.bar[0])/((c.bar[1]-c.bar[0])||1)));
    return `<td><div class="cb"><span class="${cls}">${txt}</span><span class="tr"><i style="width:${w}%"></i></span></div></td>`;}
  return `<td><span class="${cls}">${txt}</span></td>`;
}
function chiave(r,c){ return c.k!==undefined? r[c.k] : r[c.i]; }
function draw(){
  let d=rows;
  if(q) d=rows.filter(r=>cols.some(c=>c.t&&r[c.i]!=null&&String(r[c.i]).toLowerCase().includes(q)));
  if(sort.i!==null){ const c=cols[sort.i];
    d=[...d].sort((a,b)=>{const x=chiave(a,c),y=chiave(b,c);
      if(x===null||x===undefined) return 1; if(y===null||y===undefined) return -1;
      return (typeof x==="string"?x.localeCompare(y,"it"):x-y)*sort.dir;});}
  tb.innerHTML=d.length?d.map(r=>`<tr class="${r[r.length-1]?'mia':''}">${cols.map(c=>cella(c,r)).join("")}</tr>`).join("")
    :`<tr><td colspan="${cols.length}" class="nulla">Nessuna riga corrisponde alla ricerca.</td></tr>`;
  if(n) n.textContent=d.length===rows.length?`${rows.length} ${rows.length===1?'riga':'righe'}`:`${d.length} di ${rows.length}`;
  th.querySelectorAll("th").forEach(h=>{const on=+h.dataset.i===sort.i; h.classList.toggle("on",on);
    h.setAttribute("aria-sort",on?(sort.dir===1?"ascending":"descending"):"none");
    h.querySelector(".ar").textContent=on&&sort.dir===1?"▲":"▼";});
}
th.addEventListener("click",e=>{const h=e.target.closest("th"); if(!h) return; const i=+h.dataset.i, c=cols[i];
  // primo clic: testi dalla A alla Z, numeri dal migliore (o dal più alto)
  const primo=c.t?1:(c.alto===false?1:-1);
  sort={i, dir: sort.i===i ? -sort.dir : primo}; draw();});
const inp=root.querySelector("input"); if(inp) inp.addEventListener("input",e=>{q=e.target.value.trim().toLowerCase(); draw();});
const btn=root.querySelector("button"); if(btn) btn.addEventListener("click",()=>{
  const cel=v=>{if(v===null||v===undefined) return ""; const s=typeof v==="number"?String(v).replace(".",","):String(v);
    return /[;"\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;};
  const csv="﻿"+[cols.map(c=>cel(c.l)).join(";")].concat(rows.map(r=>cols.map(c=>cel(r[c.i])).join(";"))).join("\n");
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download=(T.file||"tabella")+".csv"; document.body.appendChild(a); a.click(); a.remove();});
draw();
"""

FONT = ('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/'
        'css2?family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">')


def _sigla(nome: str) -> str:
    from .ui import short
    parole = [p for p in short(nome).split() if p[:1].isalpha()]
    if len(parole) == 1:
        return parole[0][:3].upper()
    return "".join(p[0] for p in parole[:2]).upper()


_DATA = re.compile(r"^(\d{2})/(\d{2})/(\d{4})")
_NUMERO = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)")


def _chiave_testo(v):
    """Chiave d'ordinamento per i testi: date gg/mm/aaaa, testi che iniziano con un numero
    ("18,3% (13,2)"), altrimenti il testo."""
    if v is None:
        return None
    s = str(v)
    m = _DATA.match(s)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"
    m = _NUMERO.match(s)
    if m:
        return float(m.group(1).replace(",", "."))
    return s.lower()


def _soglie(valori: pd.Series, alto: bool, rif: pd.Series | None):
    """Valori oltre i quali una cella è verde (migliori) o rossa (peggiori)."""
    if rif is not None and rif.notna().sum() >= 10:
        r = rif.dropna()
        hi, lo = r.quantile(0.85), r.quantile(0.15)
    else:
        v = valori.dropna().sort_values()
        if len(v) < 4:
            return None
        k = 1 if len(v) < 15 else (2 if len(v) < 30 else 3)       # poche righe: solo il primo e l'ultimo
        lo, hi = v.iloc[k - 1], v.iloc[-k]
        if lo == hi:
            return None
    return (lo, hi) if alto else (hi, lo)


def _tema() -> dict:
    return st.session_state.get("_tema_tabelle") or {}


def render(df: pd.DataFrame, height: int | None = None, progress: dict | None = None,
           colori: dict | None = None, rif: dict | None = None, file: str = "tabella",
           chiavi_nome=("Giocatore", "Squadra", "Quintetto", "Voce", "Metrica", "Fattore")) -> None:
    """Disegna la tabella. progress: {colonna: (min, max)} per le barre (max None = il massimo
    della colonna); colori: {colonna: True se più alto è meglio}; rif: {colonna: valori del
    campionato} per confrontare i colori con tutto il campionato invece che con la tabella."""
    df = df.reset_index(drop=True)
    tema = _tema()
    mia = tema.get("mia_nome")
    sids = tema.get("sids") or {}                # nome squadra → id (per i loghi)
    cols, dati, chiavi = [], [], []
    loghi, sigle = {}, {}
    ha_mia = False
    pin = len(df.columns) > 5
    for j, c in enumerate(df.columns):
        s = df[c]
        nome = str(c)
        spec = {"i": j, "l": nome}
        if pd.api.types.is_bool_dtype(s):
            s = s.map({True: "Sì", False: "No"})
        if pd.api.types.is_numeric_dtype(s):
            intero = pd.api.types.is_integer_dtype(s)
            due = any(k in nome for k in ("rate", "FTA/FGA", "Variabilità", "Brier", "Ass/Perse",
                                           "per palla persa", "AST/TO"))
            spec["d"] = 0 if intero else (2 if due else 1)
            if nome.startswith(("Diff", "Net", "+/-", "On-Off", "Fortuna", "Margine", "Scarto")) \
                    or nome in ("±", "Saldo"):
                spec["segno"] = 1
            if nome.endswith("%") and not nome.startswith(("V%", "Prob")):
                spec["suf"] = "%" if s.dropna().between(-1, 101).all() else ""
            if colori and c in colori:
                sg = _soglie(pd.to_numeric(s, errors="coerce"), bool(colori[c]),
                             (rif or {}).get(c))
                if sg is not None:
                    spec["alto"], spec["lo"], spec["hi"] = bool(colori[c]), float(sg[0]), float(sg[1])
            if progress and c in progress:
                lo, hi = progress[c]
                hi = float(s.max()) if hi is None and s.notna().any() else (hi or 1)
                spec["bar"] = [float(lo), float(hi)]
            col = [None if pd.isna(v) else round(float(v), spec["d"]) for v in s]
        else:
            spec["t"] = 1
            if nome == "Squadra" or nome.startswith("Squadra"):
                spec["tipo"] = "squadra"
            elif nome.lower().startswith(("ultime 5", "forma")) and s.dropna().astype(str).str.fullmatch(
                    r"[VP ]+").all():
                spec["tipo"] = "forma"
                spec.pop("t")
            else:
                spec["tipo"] = "testo"
            if nome in chiavi_nome:
                spec["nome"] = 1
            if nome.startswith("Data"):
                from .ui import it
                s = s.map(lambda v: it(v) if isinstance(v, str) else v)
            if nome == "Giocatore":
                s = s.map(maiuscole)
            col = [None if (v is None or (not isinstance(v, str) and pd.isna(v)) or v in ("–", "-", ""))
                   else str(v) for v in s]
            lunghi = [len(v) for v in col if v]
            if lunghi and max(lunghi) > 60:
                spec["lungo"] = 1
            k = [_chiave_testo(v) for v in col]
            if nome.startswith("Data") or (spec["tipo"] == "testo" and any(isinstance(x, float) for x in k)
                                           and all(x is None or isinstance(x, float) for x in k)):
                spec["k"] = len(df.columns) + len(chiavi)     # posizione della chiave nella riga
                chiavi.append(k)
            if spec["tipo"] == "squadra":
                nomi = sorted(set(x for x in col if x))
                sigle.update({v: _sigla(v) for v in nomi})
                ids = {v: sids[v] for v in nomi if v in sids}
                if ids and len(ids) <= 40:
                    try:
                        from .stato import loghi_piccoli
                        mini = loghi_piccoli(tuple(sorted(set(ids.values()))))
                        loghi.update({v: mini[i] for v, i in ids.items() if mini.get(i)})
                    except Exception:
                        pass                     # senza loghi restano le sigle
            if pin and not any(x.get("fix") for x in cols) and nome in chiavi_nome and j <= 1:
                spec["fix"] = 1
        cols.append(spec)
        dati.append(col)
    righe = []
    for r in range(len(df)):
        m = bool(mia) and any(cols[j].get("tipo") == "squadra" and dati[j][r] == mia for j in range(len(cols)))
        ha_mia = ha_mia or m
        righe.append([dati[j][r] for j in range(len(cols))] + [ch[r] for ch in chiavi] + [m])
    legenda = []
    if any("alto" in x for x in cols):
        if rif and any(c in rif for c in (colori or {})):
            legenda.append('<span><i style="background:var(--posbg);border:1px solid var(--pos)"></i>tra i migliori '
                           'del campionato</span><span><i style="background:var(--negbg);border:1px solid var(--neg)">'
                           '</i>tra i peggiori</span>')
        else:
            legenda.append('<span><i style="background:var(--posbg);border:1px solid var(--pos)"></i>i migliori della '
                           'tabella</span><span><i style="background:var(--negbg);border:1px solid var(--neg)"></i>'
                           'i peggiori</span>')
    if ha_mia:
        legenda.append('<span><i style="background:var(--mia);box-shadow:inset 3px 0 0 var(--accent)"></i>'
                       'la tua squadra</span>')
    n = len(righe)
    barra = True
    payload = {"cols": cols, "rows": righe, "loghi": loghi, "sigle": sigle, "barra": barra,
               "cerca": n > 8, "legenda": "".join(legenda), "file": file}
    stile = ""
    if tema.get("accent"):
        stile = (f":root{{--accent:{tema['accent']};--navy2:{tema.get('navy', '#2b2b29')};"
                 f"--mia:{tema.get('mia', '#fbefe4')}}}")
    naturale = TESTA + RIGA * max(n, 1) + (BARRA if barra else 0) + (LEGENDA if legenda else 0) + 4
    alto = naturale if n <= 25 else min(naturale, max(height or 0, 640))
    dati_json = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    html = (f'<!doctype html><html lang="it"><head><meta charset="utf-8">{FONT}<style>{CSS}{stile}</style></head>'
            f'<body><div id="t" style="height:100%"></div><script type="application/json" id="dati">{dati_json}'
            f'</script><script>{JS}</script></body></html>')
    components.html(html, height=alto, scrolling=False)
