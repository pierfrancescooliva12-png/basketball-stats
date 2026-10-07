<p align="center"><img src="assets/logo/assist-logo.png" alt="ASSIST" width="560"></p>

# ASSIST – piattaforma di scouting per Serie A2 e Serie B Nazionale

**A**nalisi **S**tatistica e **S**couting **I**ntegrato per **S**taff **T**ecnici.

Piattaforma di analisi e scouting per la Serie A2 e la Serie B Nazionale (gironi A e B), con dati
da [legapallacanestro.com](https://www.legapallacanestro.com). Pensata per gli staff tecnici
(allenatore, assistenti, video analyst, direttore sportivo) e usabile da iPad.

Funziona interamente nel cloud, senza un PC locale:

- **GitHub Actions** scarica ogni lunedì mattina le partite nuove (box score, cronaca, anagrafica),
  aggiorna il database e l'Excel, e invia via email il report PDF sulla prossima avversaria;
- **Streamlit Community Cloud** pubblica la dashboard, da aprire da iPad (Safari).

---

## Funzioni

La dashboard è organizzata in **aree**, con la navigazione in alto (comoda al tocco):

| Area | Pagine | Cosa offre |
|---|---|---|
| **Home** | – | La settimana dello staff: prossima avversaria (probabilità di vittoria, punteggio atteso, giorni di riposo, km di trasferta), ultima partita in sintesi, posizione e forma della propria squadra, avvisi, PDF pronti da scaricare |
| **Avversaria** | Scouting · Squadre | Report completo con frase di sintesi e **PDF per la riunione tecnica**: forza/debolezza, finali punto a punto, **rotazioni** (chi parte, quando entrano i cambi, chi chiude), quintetti più usati, **quintetti alti e bassi**, +/- e On-Off, chi serve chi, **origine dei punti fatti e concessi**, **momenti della partita**, break, bonus falli, timeout, profilo di tiro, problemi di falli, **riposo e trasferte**, note dello staff. |
| **Previsioni** | Anteprima e scenari · Proiezione della classifica · Affidabilità delle previsioni | Probabilità di vittoria **con forbice**, **perché questa previsione** (quanto pesano fattore campo, attacco, difesa, stagione precedente), **scenari "e se"** (assenze, campo neutro, correzioni dello staff), confronto voce per voce, Four Factors incrociati, riposo e km, precedenti; proiezione della classifica con incertezza; **validazione su 3 stagioni** e **registro delle previsioni** fatte prima delle partite |
| **Giocatori** | Elenco · Scheda · Mercato | Medie, avanzate, ruolo, andamento, casa/trasferta; scheda con frase di sintesi, anagrafica, **presenze**, percentili, +/- e On-Off, finali punto a punto, carriera, giocatori simili, note e **report individuale in PDF**. Mercato: fabbisogni della squadra con candidati, ricerca con filtri, **dalla B all'A2** (statistiche attese salendo di categoria), talenti di B Nazionale, chi è cresciuto, giocatori simili, liste di osservati |
| **La mia squadra** | La mia squadra · Avvisi | KPI e posizione, obiettivi Four Factors, andamento, rendimento contro forti e deboli, **report post-partita** (anche in PDF); avvisi su assenze, cambi di quintetto, minuti, forma, massimi, serie |
| **Campionato** | Panoramica · Classifica · Partite | Numeri del campionato, leader, mappa attacco/difesa; classifica con forma, vittorie attese e forza del calendario; box score, avanzate e andamento di ogni partita |

**Leggere i numeri senza fatica**

- Interruttore **Esperto** in alto: spento mostra solo le colonne essenziali con nomi per esteso;
  acceso mostra tutte le metriche e le viste.
- Accanto ai valori principali c'è la **posizione nel campionato** (es. "3° su 20"); nelle
  tabelle i valori migliori sono evidenziati in blu e i peggiori in arancio.
- **"In una frase"**: le caratteristiche più marcate di squadre e giocatori, in parole.
- I campioni piccoli sono segnalati (**⚠ pochi dati**) e a inizio stagione il mercato parte
  dalla stagione precedente.
- Numeri e date nel formato italiano; ogni pagina ha un indirizzo che si può condividire
  (squadra, giocatore e stagione sono nel link).

**Report PDF**

- **Scouting** sulla squadra scelta (e ogni lunedì via email sulla prossima avversaria);
- **post-partita** sulla propria ultima partita (allegato anche all'email del lunedì);
- **individuale** per il giocatore, con lo spazio per gli obiettivi concordati con lo staff.

**Previsioni: probabilità, non certezze**

Il modello stima la forza di ogni squadra (Net rating ristretto verso la stagione precedente) e
ne ricava margine atteso e probabilità di vittoria. È validato su tutte le partite delle
stagioni 2024/25 e 2025/26 e delle prime giornate del 2026/27, in A2 e B Nazionale, usando ogni volta solo le partite giocate
prima (`python -m basket.validazione --salva`):

| Metrica (2.179 partite) | ASSIST | Vince sempre la squadra di casa | Vince chi ha il record migliore |
|---|---|---|---|
| Partite in cui vince la favorita | 65,9% | 60,2% | 62,3% |
| Brier score (più basso è meglio) | 0,214 | 0,240 | – |
| Errore medio sul margine | 9,7 punti | – | – |

Le probabilità sono calibrate: quando il modello dà la favorita tra il 70% e l'80%, la
favorita vince il 73,5% delle volte. Ogni lunedì le previsioni delle partite ancora da
giocare vengono registrate nella tabella `previsioni`, così il rendimento sulla stagione in
corso è verificabile. Le previsioni sono uno strumento di analisi per lo staff tecnico, non
destinato alle scommesse.

Accanto alle statistiche complesse c'è un **?** che apre la spiegazione (cosa misura, come si
calcola, come leggerla). Il glossario completo è in `basket/glossario.py`.

---

## Fonte dati e qualità

- **Calendario e risultati**: endpoint JSON interno `lnpstat.domino.it/getstatisticsfiles`.
- **Box score**: pagina HTML `legapallacanestro.com/wp/match/{gameid}/{campionato}/{stagione}`.
- **Cronaca (play-by-play)**: pagina `…/play-by-play` della partita.
- **Anagrafica**: pagina `legapallacanestro.com/giocatore/wp/{codice}`.

Codici: `ita2` = Serie A2, `ita3_a` / `ita3_b` = Serie B Nazionale girone A / B; stagioni
`x2627` = 2026/27, `x2526` = 2025/26, `x2425` = 2024/25.

Estrazione **incrementale** (solo dati nuovi), con **10 secondi tra una richiesta e l'altra**
come chiesto dal `robots.txt` del sito (`Crawl-delay: 10`). Il recupero dello storico avviene
a blocchi, nell'arco di più esecuzioni.
Controlli di qualità automatici:

- **Box score**: punti dei giocatori = totale squadra = risultato ufficiale. Le partite con box
  score ufficiale incompleto (ritmo stimato sotto 58 possessi per 40') contano per risultati e
  totali, ma sono escluse da percentuali e metriche avanzate.
- **Cronaca**: il punteggio ricostruito deve coincidere con quello ufficiale.
- **Quintetti**: la cronaca registra solo chi entra. Chi esce si deduce, e ogni partita viene
  verificata confrontando i minuti ricostruiti con quelli ufficiali (scarto massimo 3').
  +/-, On-Off e quintetti usano solo le partite verificate.
- **Rotazioni e quintetti per taglia**: solo dalle partite con quintetti verificati; la taglia
  usa l'altezza dell'anagrafica ufficiale.
- **Trasferte**: la città si ricava dal nome del palazzetto; le distanze sono stimate (linea
  d'aria + 25%). Coordinate delle città in `basket/luoghi.py`.
- **Dalla B all'A2**: la stima compare solo con almeno 12 giocatori passati tra le due categorie
  (stessa stagione o stagioni consecutive); lo storico 2024/25 la rende più solida.
- **Arbitri**: le fonti usate (box score, cronaca, calendario) non riportano la terna arbitrale,
  quindi l'analisi per arbitro non è disponibile.
- **Zone di tiro**: nella stagione 2026/27 la cronaca non distingue i canestri da 2 in area da
  quelli dalla media distanza. Il profilo per zona compare solo dove i dati lo permettono.

Le cronache sono salvate in file compressi, uno per partita (`data/cronaca/`), scritti una
volta e mai modificati, così il repository non cresce a ogni aggiornamento.

---

## Pubblicare la dashboard (da iPad)

1. **Porta il codice sul branch principale.** Su GitHub (app o Safari) apri la pull request del
   branch di sviluppo e premi **Merge**. Le esecuzioni programmate del lunedì partono solo da `main`.
2. **Dati**: il repository contiene già stagione in corso e 2025/26. Per aggiungerne altre o
   forzare un aggiornamento: **Actions → Aggiornamento dati → Run workflow** (campo *Stagioni*,
   es. `x2425`).
3. Apri **[share.streamlit.io](https://share.streamlit.io)** e accedi con **Continue with GitHub**.
4. **Create app → Deploy a public app from GitHub**: repository
   `pierfrancescooliva12-png/basketball-stats`, branch `main`, file `streamlit_app.py`.
5. **Deploy**. Poi in Safari: **Condividi → Aggiungi alla schermata Home**.

La dashboard si aggiorna da sola a ogni commit del workflow.

---

## Configurazione per l'uso commerciale

### Accessi per club

Nei *Secrets* dell'app su Streamlit Cloud (**App → Settings → Secrets**) aggiungi un blocco per
ogni utente. Per generare l'hash della password:

```bash
python -m basket.accesso nuovo mario "Unieuro Forlì"
```

```toml
[utenti.mario]
password_hash = "pbkdf2_sha256$200000$…"
club = "Unieuro Forlì"
ruolo = "staff"
```

Con almeno un utente configurato la dashboard chiede il login. La scheda **La mia squadra**
si imposta sulla squadra del club e note, liste di osservati e obiettivi restano **privati per
club**. Senza utenti la dashboard è in *modalità demo* (aperta a tutti).

### Archivio permanente di note e osservati

Di default note e liste sono salvate in un file locale che su Streamlit Cloud si perde a ogni
riavvio. Per renderle permanenti crea un database PostgreSQL gratuito (per esempio
[Supabase](https://supabase.com) o [Neon](https://neon.tech)) e aggiungi ai Secrets:

```toml
[database]
url = "postgresql+psycopg2://utente:password@host:5432/nome_db"
```

Le tabelle vengono create automaticamente al primo avvio.

### Report PDF via email ogni lunedì

In GitHub: **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Esempio |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | account e password per app |
| `MITTENTE` | `ASSIST <report@tuodominio.it>` |
| `ABBONATI` | `[{"email": "staff@club.it", "squadra": "Forlì"}]` |

Ogni lunedì, dopo l'aggiornamento, ogni abbonato riceve il PDF sulla **prossima avversaria**
della propria squadra. I PDF restano scaricabili anche dalla pagina del workflow (artefatto
`report-pdf`) e, in ogni momento, dalla scheda **Scouting** della dashboard.

### Formula del campionato

Le zone della proiezione di classifica (primo posto, prime 4, prime 8, ultimi 3) sono indicative.
Allineale alla formula ufficiale in `basket/config.py` (`ZONE_CLASSIFICA`).

### Prima di vendere il servizio

- **Diritti sui dati**: i dati sono estratti dal sito della Lega. Per un uso commerciale vanno
  verificati termini d'uso e diritti sulle banche dati, ed è consigliabile un accordo con LNP o
  con il fornitore delle statistiche.
- **Hosting**: Streamlit Community Cloud gratuito va bene per demo e prove. Per clienti paganti
  serve un hosting con livello di servizio garantito (Streamlit a pagamento, un servizio cloud,
  un server dedicato). Il codice non cambia.
- **Contratti**: prevedere limitazioni di responsabilità per errori o incompletezze della fonte
  (i controlli di qualità li segnalano ma non li eliminano) e l'informativa privacy sui dati dei
  giocatori.

---

## Aggiornamento dei dati

- **Automatico**: ogni **lunedì alle 07:00** (ora legale; 06:00 con l'ora solare).
- **Manuale**: **Actions → Aggiornamento dati → Run workflow**, con campi facoltativi per
  campionati, giornate, stagioni e numero massimo di anagrafiche.
- **Excel**: `reports/riepilogo_x2627.xlsx` (17 fogli, con rotazioni, momenti della partita e presenze).

Se qualcosa non si riesce a importare, il resto viene salvato comunque, il workflow risulta
**fallito** e GitHub invia una notifica. Se il sito cambia struttura, **Actions → Ricognizione
fonte dati** salva le pagine in `discovery/output` per adeguare il parser.

**Cambio di stagione**: in `basket/config.py` aggiorna `STAGIONE`, `STAGIONE_LABEL` e `STAGIONI`.

---

## Struttura del codice

| Percorso | Contenuto |
|---|---|
| `basket/scraper.py`, `client.py`, `update.py` | Estrazione (calendario, box score, cronaca, anagrafica) |
| `basket/db.py` | Database SQLite e file delle cronache |
| `basket/analysis.py` | Medie, per 40', avanzate, profilo di squadra, leader, percentili |
| `basket/pbp.py` | Cronaca: quintetti, +/-, On-Off, finali, assist, origine punti, break, falli, timeout |
| `basket/previsioni.py` | Forza delle squadre, probabilità di vittoria, fattori della previsione, scenari "e se", simulazione della stagione |
| `basket/validazione.py` | Validazione retrospettiva, calibrazione, registro delle previsioni (`data/validazione.csv`) |
| `basket/mercato.py` | Storico per stagione, ruolo stimato, giocatori simili, talenti, progressi |
| `basket/avvisi.py` | Avvisi automatici e obiettivi della propria squadra |
| `basket/approfondimenti.py`, `luoghi.py` | Rotazioni, taglia dei quintetti, momenti, presenze, riposo e trasferte, dalla B all'A2, frasi di sintesi |
| `basket/report_extra.py` | Report PDF post-partita e individuale |
| `basket/scouting.py`, `report_pdf.py`, `invio_email.py` | Report di scouting, PDF, invio email |
| `basket/accesso.py`, `note.py` | Login per club, note, osservati, obiettivi |
| `basket/glossario.py` | Spiegazioni delle statistiche (pulsanti "?") |
| `dashboard/`, `streamlit_app.py` | Dashboard (`pagine.py`: Home e aree; `analisi.py`: nuove sezioni; `previsioni_ui.py`: area Previsioni) |
| `assets/logo/` | Logo ASSIST (SVG e PNG; `build_logo.py` lo rigenera) |
| `tests/` | 41 test automatici (parser, formule, quintetti, nuove analisi, previsioni e validazione, PDF, accessi) |

```bash
pip install -r requirements-update.txt
python -m basket.update --campionati ita2 --giornate 1-2     # estrazione
python -m basket.export_excel                                # Excel
python -m basket.report_pdf "Forlì"                          # PDF di scouting
python -m basket.report_extra partita "Forlì"                # PDF post-partita
python -m basket.report_extra giocatore "Forlì" "Gaspardo"   # PDF individuale
python -m basket.validazione --salva --registra              # validazione e registro
python -m pytest -q tests                                    # test
pip install -r requirements.txt && streamlit run streamlit_app.py
```
