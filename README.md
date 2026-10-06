# 🏀 LNP Stats – piattaforma di scouting per Serie A2 e Serie B Nazionale

Piattaforma di analisi e scouting per la Serie A2 e la Serie B Nazionale (gironi A e B), con dati
da [legapallacanestro.com](https://www.legapallacanestro.com). Pensata per gli staff tecnici
(allenatore, assistenti, video analyst, direttore sportivo) e usabile da iPad.

Funziona interamente nel cloud, senza un PC locale:

- **GitHub Actions** scarica ogni lunedì mattina le partite nuove (box score, cronaca, anagrafica),
  aggiorna il database e l'Excel, e invia via email il report PDF sulla prossima avversaria;
- **Streamlit Community Cloud** pubblica la dashboard, da aprire da iPad (Safari).

---

## Funzioni

| Area | Cosa offre |
|---|---|
| **Panoramica** | Numeri del campionato, leader in 9 categorie, mappa attacco/difesa |
| **Classifica** | Forma, Net rating, vittorie attese e "fortuna", partite punto a punto, forza del calendario |
| **Squadre** | Avanzate, Four Factors, profilo (panchina, dipendenza dai top 2, distribuzione punti), mappa dei quarti |
| **Giocatori** | Medie, totali, per 40', avanzate, "ruolo" (AST%, REB%, STL%, BLK%…), trend, casa/trasferta |
| **Giocatore** | Scheda con anagrafica, percentili, +/- e On-Off, finali punto a punto, carriera, giocatori simili, note |
| **Scouting** | Report completo sull'avversaria + **PDF per la riunione tecnica**: forza/debolezza, finali punto a punto, chi serve chi, origine dei punti, break, bonus falli, timeout, quintetti più usati, +/- e On-Off, profilo di tiro, problemi di falli, note dello staff |
| **Anteprima** | Probabilità di vittoria e punteggio atteso, confronto voce per voce, Four Factors incrociati, giocatori chiave, precedenti, proiezione della classifica (simulazione) |
| **Mercato** | **Fabbisogni della squadra selezionata**: carenze rispetto al campionato tradotte nel tipo di giocatore utile (tiratore, playmaker, rimbalzista, protettore del ferro, difensore perimetrale, attaccante del ferro, realizzatore), con motivazione, migliore già in rosa e candidati ordinati per adattamento al profilo. Poi ricerca con filtri (categoria, ruolo stimato, età, nazionalità, minuti, usage, TS%), talenti di B Nazionale, chi è cresciuto rispetto alla stagione precedente, giocatori simili, liste di osservati del club |
| **Avvisi** | Assenze di giocatori importanti, cambi di quintetto, minuti in crescita o calo, giocatori in forma, massimi stagionali, serie di risultati |
| **La mia squadra** | KPI e posizione nel campionato, obiettivi Four Factors dello staff, andamento, rendimento contro le forti e contro le deboli |
| **Partite** | Box score, statistiche avanzate, grafico dell'andamento, link al video su LNP Pass |

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
- **Zone di tiro**: nella stagione 2026/27 la cronaca non distingue i canestri da 2 in area da
  quelli dalla media distanza. Il profilo per zona compare solo dove i dati lo permettono.

Le cronache sono salvate in file compressi, uno per partita (`data/cronaca/`), scritti una
volta e mai modificati, così il repository non cresce a ogni aggiornamento.

---

## Pubblicare la dashboard (da iPad)

1. **Porta il codice sul branch principale.** Su GitHub (app o Safari) apri la pull request del
   branch di sviluppo e premi **Merge**. Le esecuzioni programmate del lunedì partono solo da `main`.
2. **Crea i dati la prima volta** (se non ci sono già): **Actions → Aggiornamento dati → Run
   workflow**. Nel campo *Stagioni* scrivi `x2627,x2526` per avere anche lo storico; nel campo
   *Anagrafica* scrivi `3000` per scaricare tutti i giocatori.
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
| `MITTENTE` | `LNP Stats <report@tuodominio.it>` |
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
- **Excel**: `reports/riepilogo_x2627.xlsx` (14 fogli).

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
| `basket/previsioni.py` | Forza delle squadre, probabilità di vittoria, simulazione della stagione |
| `basket/mercato.py` | Storico per stagione, ruolo stimato, giocatori simili, talenti, progressi |
| `basket/avvisi.py` | Avvisi automatici e obiettivi della propria squadra |
| `basket/scouting.py`, `report_pdf.py`, `invio_email.py` | Report di scouting, PDF, invio email |
| `basket/accesso.py`, `note.py` | Login per club, note, osservati, obiettivi |
| `basket/glossario.py` | Spiegazioni delle statistiche (pulsanti "?") |
| `dashboard/`, `streamlit_app.py` | Dashboard |
| `tests/` | 27 test automatici (parser, formule, quintetti, PDF, accessi) |

```bash
pip install -r requirements-update.txt
python -m basket.update --campionati ita2 --giornate 1-2     # estrazione
python -m basket.export_excel                                # Excel
python -m basket.report_pdf "Forlì"                          # PDF di scouting
python -m pytest -q tests                                    # test
pip install -r requirements.txt && streamlit run streamlit_app.py
```
