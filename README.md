# 🏀 Basketball Stats – Serie A2 e Serie B Nazionale 2026/27

Strumento di analisi statistica per la Serie A2 e la Serie B Nazionale (gironi A e B),
con dati da [legapallacanestro.com](https://www.legapallacanestro.com).

Funziona interamente nel cloud, senza un PC locale:

- **GitHub Actions** scarica le partite nuove ogni lunedì mattina e aggiorna database ed Excel;
- **Streamlit Community Cloud** pubblica la dashboard, da aprire da iPad (Safari).

---

## Cosa contiene

| Percorso | Contenuto |
|---|---|
| `data/lnp.sqlite` | Database SQLite (creato e aggiornato dal workflow) |
| `reports/riepilogo_x2627.xlsx` | Excel di riepilogo, rigenerato a ogni aggiornamento |
| `streamlit_app.py` | Dashboard |
| `basket/` | Codice: estrazione, database, analisi, scouting, export |
| `.github/workflows/update.yml` | Aggiornamento settimanale automatico |
| `.github/workflows/discovery.yml` | Ricognizione del sito (da usare solo se il sito cambia) |
| `tests/` | Test automatici del parser e delle formule |

### Fonte dati

- **Calendario e risultati**: endpoint JSON interno del sito
  `lnpstat.domino.it/getstatisticsfiles?task=schedule&year=x2627&league=ita2&round=N`.
- **Box score**: pagina HTML della partita, es.
  `legapallacanestro.com/wp/match/ita2_412/ita2/x2627`.

Codici campionato: `ita2` = Serie A2, `ita3_a` / `ita3_b` = Serie B Nazionale girone A / B.

L'estrazione è **incrementale**: scarica solo le partite non ancora presenti nel database e salta
le giornate già complete. Al massimo **1 richiesta al secondo** verso il sito.
Ogni partita viene controllata (somma dei punti dei giocatori = totale squadra = risultato
del calendario) prima di essere salvata.

### Database

Tabelle: `campionati`, `squadre`, `giocatori`, `partite`, `box_giocatore`, `box_squadra`
(più `calendario`, che contiene anche le partite ancora da giocare).

Statistiche per giocatore e partita: minuti, punti, tiri da 2 / da 3 / liberi fatti e tentati,
rimbalzi offensivi e difensivi, assist, perse, recuperate, stoppate date e subite,
falli commessi e subiti, valutazione.

> **Nota:** il **+/-** non è disponibile. Il sito non lo pubblica e il play-by-play
> non riporta le sostituzioni, quindi non si può ricostruire.

### Analisi

- Medie individuali e di squadra: totali, a partita e **per 40 minuti**.
- Avanzate: **possessi, pace, ORtg, DRtg, Net Rtg, eFG%, TS%, Four Factors**
  (eFG%, TOV%, OREB%, FT rate, in attacco e concessi), **usage rate, assist ratio**.
- **Trend ultime 5 partite** (giocatori e squadre) e **split casa/trasferta**.
- Giocatori, statistiche di "ruolo": **Game Score**, **AST%, OREB%, DREB%, REB%, STL%, BLK%,
  TOV%** individuali, quota di tiri da 3, frequenza ai liberi (FTA/FGA), doppie doppie,
  variabilità dei punti (costanza) e **profilo a percentili** rispetto al campionato.
- Squadre, profilo di contesto: **vittorie attese** (pitagorica) e **fortuna**, record nelle
  partite **punto a punto** (margine ≤ 5), **forza del calendario**, **punti della panchina**,
  **dipendenza dai primi 2 realizzatori**, distribuzione dei punti (2 / 3 / liberi),
  % di canestri assistiti, **differenza punti per quarto**.
- **Report di scouting** su una squadra: punti di forza e deboli rispetto alla media del
  campionato, Four Factors, giocatori chiave, ultime 5, casa/trasferta, punti per periodo,
  prossima partita.

<details>
<summary>Formule</summary>

| Metrica | Formula |
|---|---|
| Possessi | FGA − OREB + TOV + 0,44 × FTA (media delle due squadre) |
| ORtg / DRtg | 100 × punti fatti / subiti ÷ possessi |
| eFG% | (FGM + 0,5 × 3PM) / FGA |
| TS% | Punti / (2 × (FGA + 0,44 × FTA)) |
| TOV% | TOV / (FGA + 0,44 × FTA + TOV) |
| OREB% | OREB / (OREB + DREB avversari) |
| FT rate | Liberi segnati / FGA |
| USG% | 100 × (FGA + 0,44 FTA + TOV) × (min squadra / 5) / (min × (FGA + 0,44 FTA + TOV squadra)) |
| AST ratio | 100 × AST / (FGA + 0,44 × FTA + AST + TOV) |
| Game Score | PTS + 0,4 FGM − 0,7 FGA − 0,4 (FTA − FTM) + 0,7 OREB + 0,3 DREB + STL + 0,7 AST + 0,7 BLK − 0,4 PF − TOV |
| OREB% / DREB% individuale | rimbalzi del giocatore / rimbalzi disponibili mentre era in campo (stimati con la quota di minuti) |
| AST% | AST / (canestri di squadra mentre era in campo − propri canestri) |
| STL% / BLK% | recuperi / possessi avversari · stoppate / tiri da 2 avversari, mentre era in campo |
| Vittorie attese | PF¹⁴ / (PF¹⁴ + PS¹⁴) × partite |
| Fortuna | vittorie reali − vittorie attese |
| Forza calendario | Net rating medio degli avversari affrontati |

</details>

---

## Pubblicare la dashboard (da iPad)

Servono un account GitHub (già presente) e un account gratuito Streamlit Community Cloud.

1. **Porta il codice sul branch principale.** Su GitHub (app o Safari) apri la pull request del
   branch di sviluppo e premi **Merge**. Le esecuzioni programmate del lunedì partono solo dal
   branch principale (`main`).
2. **Crea i dati la prima volta.** Su github.com, nel repository: **Actions → Aggiornamento dati →
   Run workflow** (lascia i campi vuoti per scaricare tutto). Dopo qualche minuto compare un commit
   "Dati aggiornati" con `data/lnp.sqlite` e l'Excel.
3. Apri **[share.streamlit.io](https://share.streamlit.io)** in Safari e accedi con **Continue with GitHub**.
   Autorizza l'accesso al repository `basketball-stats`.
4. Premi **Create app → Deploy a public app from GitHub** e compila:
   - **Repository**: `pierfrancescooliva12-png/basketball-stats`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **App URL**: a scelta, es. `lnp-stats`
5. Premi **Deploy**. Il primo avvio richiede un paio di minuti.
6. In Safari: **Condividi → Aggiungi alla schermata Home** per aprire la dashboard come un'app.

La dashboard si aggiorna da sola: a ogni commit del workflow, Streamlit Cloud ricarica i dati.

> **Privacy:** sul piano gratuito l'app può essere pubblica oppure, dalle impostazioni
> dell'app (**Settings → Sharing**), visibile solo a chi inviti tramite email.

### Usare la dashboard

In alto ci sono i filtri **Campionato**, **Squadra** e **Giocatore**, sempre visibili anche con
l'iPad in verticale. Le schede:

- **Panoramica**: numeri del campionato, leader in 9 categorie, mappa attacco/difesa (ORtg vs DRtg).
- **Classifica**: con forma (ultime 5), Net rating, vittorie attese, fortuna, punto a punto, calendario.
- **Squadre**: avanzate, profilo, quarti (mappa di calore), medie, per 40', casa/trasferta, ultime 5.
- **Giocatori**: medie, avanzate, ruolo, per 40', totali, trend ultime 5, casa/trasferta.
- **Giocatore**: scheda con percentili nel campionato, andamento partita per partita, game log.
- **Scouting**: report sulla squadra selezionata (forza/debolezza, Four Factors, quarti,
  giocatori chiave), scaricabile in Markdown.
- **Partite**: box score completo con statistiche avanzate della partita.

---

## Aggiornamento dei dati

- **Automatico**: ogni **lunedì alle 07:00** (ora legale; 06:00 con l'ora solare).
- **Manuale**: **Actions → Aggiornamento dati → Run workflow**. Si può limitare a certi
  campionati (es. `ita2`) o giornate (es. `1-2` oppure `1,3,5-7`).
- **Excel**: `reports/riepilogo_x2627.xlsx`. Da iPad: aprilo su GitHub e premi
  **Download / View raw**, poi apri con Excel o Numbers.

Se una partita non si riesce a importare (per esempio perché il sito ha cambiato struttura),
le altre vengono comunque salvate, il workflow risulta **fallito** e GitHub invia una notifica
via email o app. In quel caso si può avviare **Actions → Ricognizione fonte dati** per
salvare la nuova struttura delle pagine nella cartella `discovery/output` e adeguare il parser.

### Cambio di stagione

In `basket/config.py` modifica `STAGIONE` (es. `x2728`) e `STAGIONE_LABEL`.
I dati delle stagioni precedenti restano nel database.

---

## Comandi (per riferimento)

```bash
pip install -r requirements-update.txt
python -m basket.update --campionati ita2 --giornate 1-2   # estrazione
python -m basket.export_excel                              # Excel
python -m basket.scouting "Forlì"                          # report in reports/
python -m pytest -q tests                                  # test
pip install -r requirements.txt && streamlit run streamlit_app.py
```
