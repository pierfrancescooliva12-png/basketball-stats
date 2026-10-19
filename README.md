<p align="center"><img src="assets/logo/assist-logo.png" alt="ASSIST" width="560"></p>

# ASSIST – piattaforma di scouting per Serie A2 e Serie B Nazionale

**A**nalisi **S**tatistica e **S**couting **I**ntegrato per **S**taff **T**ecnici.

Piattaforma di analisi e scouting per la Serie A2 e la Serie B Nazionale (gironi A e B), con dati
da [legapallacanestro.com](https://www.legapallacanestro.com). Pensata per gli staff tecnici
(allenatore, assistenti, video analyst, direttore sportivo) e usabile da iPad.

Funziona interamente nel cloud, senza un PC locale:

- **GitHub Actions** scarica ogni mattina le partite nuove (box score, cronaca, anagrafica) e il
  calendario aggiornato (si gioca anche il sabato, il mercoledì e in altri giorni), aggiorna il database
  e l'Excel, e il lunedì invia via email il report PDF sulla prossima avversaria;
- **Streamlit Community Cloud** pubblica la dashboard, da aprire da iPad (Safari).

---

## Funzioni

La dashboard è organizzata in **aree**, con la navigazione in alto (comoda al tocco):

| Area | Pagine | Cosa offre |
|---|---|---|
| **Home** | – | La settimana dello staff: prossima avversaria (probabilità di vittoria, punteggio atteso, giorni di riposo, km di trasferta), ultima partita in sintesi, posizione e forma della propria squadra, avvisi, PDF pronti da scaricare |
| **Avversaria** | Scouting · Squadre | **Chiavi per vincere**: le tre chiavi della partita in parole, le leve dei Four Factors (valore atteso, obiettivo e quanto vale in probabilità raggiungerlo), ritmo conveniente, cosa cambia nelle loro e nelle vostre sconfitte, **giocatori chiave** ("tenere X sotto 12 punti: probabilità dal 30% al 35%", misurato come scarto rispetto al margine previsto, con chi compensa e il rendimento senza di lui). Report completo con frase di sintesi e **PDF per la riunione tecnica** (con le chiavi se la squadra dello staff è impostata): forza/debolezza, finali punto a punto, **rotazioni** (chi parte, quando entrano i cambi, chi chiude), quintetti più usati, **quintetti alti e bassi**, +/- e On-Off, chi serve chi, **origine dei punti fatti e concessi**, **momenti della partita**, break, bonus falli, timeout, profilo di tiro, problemi di falli, **riposo e trasferte**, note dello staff. |
| **Previsioni** | Anteprima e scenari · Proiezione della classifica · Affidabilità delle previsioni | Probabilità di vittoria **con forbice**, **perché questa previsione** (quanto pesano fattore campo, attacco, difesa, stagione precedente), **scenari "e se"** (assenze, campo neutro, correzioni dello staff), confronto voce per voce, Four Factors incrociati, riposo e km, precedenti; proiezione della classifica con incertezza; **validazione su 3 stagioni** e **registro delle previsioni** fatte prima delle partite |
| **Giocatori** | Elenco · Scheda · Mercato | **Mappa di tiro a zone** (area, media distanza, da 3, schiacciate) rispetto alla media del campionato, per stagione o singola partita, con la cronologia dei tiri (quarto, cronometro, punteggio, assist). Medie, avanzate, ruolo, andamento, casa/trasferta; scheda con frase di sintesi, anagrafica, **presenze**, percentili, +/- e On-Off, finali punto a punto, carriera, giocatori simili, note e **report individuale in PDF**. Mercato: fabbisogni della squadra con candidati, ricerca con filtri, **confronto tra due giocatori** (verdetto in parole, profilo su sei dimensioni in percentili per ruolo, cosa produce ogni possesso usato, numeri alla pari tra A2 e B Nazionale), **dalla B all'A2** (statistiche attese salendo di categoria), talenti di B Nazionale, chi è cresciuto, giocatori simili, liste di osservati |
| **La mia squadra** | La mia squadra · Live · Lavagna dei giochi · Avvisi | **Live**: la partita della propria squadra in diretta dalla cronaca della lega (aggiornata ogni 30 secondi); dal calendario la pagina sa quando si gioca, anche negli anticipi e nei turni infrasettimanali, e si apre da sola 20 minuti prima della palla a due; si possono seguire anche le altre partite in corso, con punteggio, probabilità di vittoria, parziali, falli di squadra e bonus, timeout rimasti, Four Factors contro la media della stagione, Leverage dei giocatori e **suggerimenti per lo staff** ordinati per urgenza (timeout sui parziali, giocatori carichi di falli, bonus, chi è caldo, rimbalzi concessi, palle perse, gestione dei finali); senza partita in corso si rivede una partita giocata fermandola a un minuto qualsiasi.  **Lavagna dei giochi**: lo staff disegna i propri giochi col dito (tagli, passaggi, palleggi, blocchi), a fasi animate con le note, con la **difesa facoltativa** (a uomo, zona 2-3, 3-2, 1-3-1, 1-2-2, box-and-one o manuale: le X si piazzano da sole a ogni fase e seguono la palla durante l'animazione; nella difesa a uomo si sceglie come difendere i pick and roll, cioè passa sopra, passa sotto, cambio, show alto, contenimento basso, fondo/ice o raddoppio con rotazione, e la lavagna suggerisce come adeguare l'attacco) il **video sincronizzato** (si apre una clip dal dispositivo, si segna nel video il momento di ogni fase e la lavagna, anche in 3D, segue il video in tempo reale, in pausa, al rallentatore e spostando il cursore; il video non viene caricato, nel gioco si salvano solo i tempi) la **bozza dal video** (si carica una clip, la prima volta in un palazzetto si toccano i 4 angoli dell'area e poi il campo si riconosce da solo, si indicano attacco e difesa in pochi momenti partendo da una proposta automatica: l'analisi su Modal ricostruisce percorsi, palleggi, passaggi, difesa reale e tempi delle fasi e la bozza si apre nella lavagna, già sincronizzata con la clip) e la **vista 3D** di riproduzione con quattro telecamere (dall'alto, tribuna, dietro il canestro, occhi del portatore), rotazione con il dito e velocità regolabile, salvati per il club e scaricabili in PDF fase per fase, con un **archivio di 63 schemi pronti** caricabili e modificabili, in 12 categorie: metà campo, pick and roll, contro i cambi, tiratori, gioco in post, transizione, contro la zona (2-3, 1-3-1, 3-2, match-up), giochi avanzati, rimesse dal fondo, rimesse laterali, fine quarto e fine partita (sotto di 2, sotto di 3, ultimo tiro); l'archivio intero si scarica in PDF; la stessa lavagna è nello Scouting per i giochi dell'avversaria, che finiscono nel PDF di scouting. **Aree da migliorare**: su cosa concentrarsi in parole, priorità di lavoro sui Four Factors con le vittorie in più raggiungendo l'obiettivo, punti regalati (palle perse, seconde occasioni, contropiede, liberi sbagliati, falli), momenti in cui perdete terreno, dettagli individuali che costano punti (liberi, tiro da 3, palle perse, scelta di tiro, falli), **quintetti migliori e peggiori** (Net rating pesato sui minuti insieme), cosa cambia quando perdete. **PDF completo della squadra** con tutte le voci della pagina (e i giochi della lavagna). KPI e posizione, obiettivi Four Factors, andamento, rendimento contro forti e deboli, **report post-partita** (anche in PDF); avvisi su assenze, cambi di quintetto, minuti, forma, massimi, serie |
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

- **Scouting** sulla squadra scelta (e ogni lunedì via email sulla prossima avversaria): si apre con il
  **piano partita** (probabilità, chiavi per vincere, consigli su come affrontarla in difesa, in attacco,
  per ritmo e momenti e nei finali), poi le chiavi in dettaglio e tutte le sezioni della pagina Scouting,
  con le note dello staff e i giochi disegnati;
- **La mia squadra**: tutte le voci della pagina in un documento;
- **post-partita** sulla propria ultima partita (allegato anche all'email del lunedì);
- **individuale** per il giocatore, con lo spazio per gli obiettivi concordati con lo staff.

**Previsioni: probabilità, non certezze**

Il modello stima la forza di ogni squadra (Net rating ristretto verso il valore della rosa nella
stagione precedente) e
ne ricava margine atteso e probabilità di vittoria. È validato su tutte le partite delle
stagioni 2024/25 e 2025/26 e delle prime giornate del 2026/27, in A2 e B Nazionale, usando ogni volta solo le partite giocate
prima (`python -m basket.validazione --salva`):

| Metrica (2.215 partite) | ASSIST | Vince sempre la squadra di casa | Vince chi ha il record migliore |
|---|---|---|---|
| Partite in cui vince la favorita | 66,7% | 60,2% | 62,4% |
| Brier score (più basso è meglio) | 0,211 | 0,240 | – |
| Errore medio sul margine | 9,6 punti | – | – |

Sono state provate anche altre migliorie (forza corretta per gli avversari affrontati, più peso
alle partite recenti, assenze nell'ultima partita, giorni di riposo): nessuna migliorava la
validazione, quindi non sono state adottate. Nell'ottobre 2026 sono stati provati anche un rating Elo con margine (Brier 0,2155), la
combinazione Elo + modello attuale (0,2124, differenza trascurabile), il fattore campo per squadra
e, come limite superiore, la conoscenza esatta degli assenti di ogni partita (Brier da 0,2125 a
0,2120): sul vincente il modello è vicino a quanto permettono questi dati. È stata aggiunta la stima
dei **punti totali** (ritmo × efficienza di attacco contro difesa): errore medio 12,5 punti contro
13,1 della media di campionato.

**Correzione per la fortuna nei tiri** (adottata): la forza delle squadre si calcola sui punti che
avrebbero fatto e subito con le percentuali da 3 e ai liberi attese invece di quelle della serata
(nell'attacco la percentuale della squadra pesa il 70%, nella difesa quella concessa solo il 20%, i
liberi degli avversari valgono la media). Brier da 0,2125 a 0,2110, favorita vincente dal 66,4% al
66,7%, errore sul margine da 9,71 a 9,62, migliore in entrambe le stagioni complete. Ridurre il peso
delle vittorie larghe (punti a partita decisa) invece non migliorava.

**Intervalli su misura**: la dispersione del margine dipende da quanto sono note le squadre (13,1
punti nelle prime 3 giornate, 11,85 da metà stagione) e quella dei totali dal campionato (15,0 in A2,
16,7 nel girone A di B). Gli intervalli "1 su 2" e "8 su 10" contengono il risultato reale il 51,6%
e l'80,7% delle volte.

**Pronostici della giornata** (Previsioni): tutte le partite in programma nei prossimi giorni, in A2 e
B Nazionale, con favorita e probabilità, scarto atteso, margine e punti totali con le fasce che
contengono il risultato in 1 partita su 2 e in 8 su 10, affidabilità (bassa a inizio stagione) e quante ne ha prese
il modello nella stagione in corso. Analisi statistica, non consigli di scommessa. Il punto di partenza dalla rosa invece sì: Brier
score da 0,214 a 0,213, accuratezza dal 65,9% al 66,2%.

Le probabilità sono calibrate: quando il modello dà la favorita tra il 70% e l'80%, la
favorita vince il 74,8% delle volte (prevista 74,6%). A ogni aggiornamento le previsioni delle partite ancora da
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
   branch di sviluppo e premi **Merge**. Le esecuzioni programmate partono solo da `main`.
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
ogni utente. Il primo accesso (amministratore) si crea dal sito: finché non c'è nessun utente, in
fondo alla Home c'è **Amministratore · crea le credenziali di accesso**, che produce il blocco da
incollare (solo l'hash, mai la password). In alternativa, da riga di comando:

```bash
python -m basket.accesso nuovo mario "Unieuro Forlì"
```

```toml
[utenti.mario]
password_hash = "pbkdf2_sha256$200000$…"
club = "Unieuro Forlì"
ruolo = "staff"
```

Gli accessi dei club si preparano dall'area **Admin › Amministrazione** (solo per gli admin):
scegli la squadra e il nome utente, il sito genera una password iniziale casuale e il blocco da
incollare nei Secrets. Dalla stessa pagina si genera una nuova password per un utente esistente.

Per un amministratore senza club basta omettere `club` e mettere `ruolo = "admin"`: vede tutte
le squadre e sceglie dalla Home quella da seguire.

Con almeno un utente configurato la dashboard mostra la schermata di accesso (dopo 5 tentativi
sbagliati di fila l'accesso si blocca per un minuto, poi per tempi doppi). La scheda **La mia squadra**
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

- **Automatico**: ogni giorno alle **07:00** (ora legale; 06:00 con l'ora solare); il report agli abbonati parte solo il lunedì.
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
| `basket/miglioramento.py` | Aree da migliorare della propria squadra |
| `basket/tiri.py` | Mappa di tiro a zone, cronologia dei tiri, stima del minuto nel video |
| `basket/lavagna.py`, `dashboard/lavagna/` | Lavagna dei giochi (propri e delle avversarie), difese automatiche e vista 3D (`lavagna.html`, three.js incluso in `componente/three.min.js`, licenza MIT), schemi pronti (`dashboard/lavagna/catalogo.py`, `schemi.py`, `archivio_*.py`) e disegno delle fasi nei PDF |
| `basket/chiavi.py` | Chiavi per vincere: leve dei Four Factors, ritmo, quando perdono, giocatori chiave |
| `basket/validazione.py` | Validazione retrospettiva, calibrazione, registro delle previsioni (`data/validazione.csv`) |
| `basket/mercato.py` | Storico per stagione, ruolo stimato, giocatori simili, talenti, progressi |
| `basket/avvisi.py` | Avvisi automatici e obiettivi della propria squadra |
| `basket/approfondimenti.py`, `luoghi.py` | Rotazioni, taglia dei quintetti, momenti, presenze, riposo e trasferte, dalla B all'A2, frasi di sintesi |
| `basket/report_extra.py` | Report PDF post-partita e individuale |
| `basket/report_mia.py` | PDF completo della propria squadra |
| `basket/confronto.py` | Confronto tra due giocatori con metriche avanzate |
| `basket/piano_partita.py` | Consigli su come affrontare un'avversaria, dal confronto con i dati della propria squadra |
| `basket/scouting.py`, `report_pdf.py`, `invio_email.py` | Report di scouting, PDF, invio email |
| `basket/accesso.py`, `note.py` | Login per club, note, osservati, obiettivi |
| `basket/glossario.py` | Spiegazioni delle statistiche (pulsanti "?") |
| `dashboard/`, `streamlit_app.py` | Dashboard (`pagine.py`: Home e aree; `analisi.py`: nuove sezioni; `previsioni_ui.py`: area Previsioni) |
| `assets/logo/` | Logo ASSIST (SVG e PNG; `build_logo.py` lo rigenera) |
| `video/` | Analisi delle clip (`analisi.py`: rilevamento YOLOX, movimento della telecamera, calibrazione con 4 tocchi o aggancio al palazzetto, tracciamento guidato, palla e passaggi, bozza del gioco), servizio su Modal con GPU T4 (`servizio_modal.py`, pubblicato dal sito con `MODAL_TOKEN_ID` e `MODAL_TOKEN_SECRET` nei Secrets) e servizio locale per lo sviluppo (`servizio_locale.py`, con `ASSIST_VIDEO_LOCALE=1` e `ASSIST_YOLOX`); interfaccia in `dashboard/video_ui.py` e `dashboard/tocchi/` |
| `basket/leverage.py`, `basket/live.py` | **Leverage** (adattamento della statistica NBA): probabilità di vittoria in partita tarata sulla cronaca 2025/26, swing di ogni azione contro l'esito opposto, merito ai giocatori in campo a somma zero; stato della partita in diretta e regole dei suggerimenti. In dashboard: probabilità e momenti decisivi nella pagina della partita, classifica Leverage nell'elenco giocatori, pagina Live |
| `tests/` | 82 test automatici (parser, formule, quintetti, nuove analisi, previsioni e validazione, chiavi per vincere, lavagna, PDF, accessi) |

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
