# Gestionale Magazzino

Programma per Windows per gestire il magazzino di una piccola attivita': anagrafica
prodotti, ingressi/uscite merce, avvisi di riordino, notifiche sulla variazione dei
prezzi di acquisto ed esportazione di un catalogo prodotti in PDF per i clienti.

## Funzionalita'

- **Prodotti**: anagrafica con codice, categoria, quantita', unita' di misura,
  soglia di riordino, prezzo di vendita, fornitore.
- **Ingressi/Uscite**: registra ogni carico (acquisto) e scarico (vendita/uso) di
  merce, con storico completo dei movimenti.
- **Avviso riordino**: nella Dashboard vedi subito quali prodotti sono scesi sotto
  la soglia minima impostata.
- **Notifica variazione prezzo**: quando registri un ingresso con un nuovo prezzo
  di acquisto, il programma lo confronta con il prezzo dell'ultimo ordine e ti
  avvisa se la variazione supera la percentuale che imposti (default 10%).
- **Catalogo PDF**: esporta in un click un PDF con i prodotti (raggruppati per
  categoria) da mandare ai clienti, con il nome della tua attivita' in testa.
- **Backup su Google Drive**: il database e' sempre salvato in locale; con un
  click puoi copiarlo anche in una cartella sincronizzata con Google Drive (vedi
  sotto), cosi' hai una copia sempre aggiornata online.

## Come funziona il salvataggio dati / Google Drive

Il programma NON richiede account o configurazioni complicate: usa un piccolo
database locale (file `magazzino.db`) che si trova sempre accanto al programma.

Per avere anche una copia automatica su Google Drive, il modo piu' semplice e
affidabile per un singolo PC e':

1. Installa **Google Drive per desktop** (gratuito, di Google) sul PC dove gira
   il gestionale: https://www.google.com/intl/it/drive/download/
2. Durante l'installazione scegli una cartella del PC che verra' sincronizzata
   con il tuo Google Drive (es. `G:\Il mio Drive\Gestionale`).
3. Nel programma vai su **Impostazioni > Backup e Google Drive**, clicca
   "Sfoglia" e seleziona quella cartella.
4. Da quel momento, ogni volta che premi **"Esegui backup ora"** (oppure ad ogni
   chiusura del programma, se attivi l'opzione automatica) viene salvata li'
   una copia del database, che Google Drive caricherà automaticamente online.

Questo approccio evita di dover creare credenziali/API Google (procedura lunga e
tecnica) e funziona comunque perfettamente per un utilizzo singolo utente.

## Come ottenere il file .exe pronto (senza installare nulla) — CONSIGLIATO

Il modo piu' semplice: far compilare l'eseguibile gratuitamente da GitHub,
senza bisogno di installare Python sul PC. Serve solo un account gratuito su
github.com. Segui questi passaggi una sola volta:

1. Vai su **https://github.com** e crea un account gratuito (se non ne hai
   gia' uno).
2. Clicca in alto a destra sul **"+"** e scegli **"New repository"**.
   Dagli un nome a piacere (es. `gestionale-magazzino`), lascialo **Public**
   o **Private** come preferisci, e clicca **"Create repository"**.
3. Nella pagina del repository appena creato, clicca **"uploading an existing
   file"** (o "Add file" > "Upload files").
4. Trascina dentro **tutto il contenuto** della cartella `gestionale` che hai
   ricevuto (compresa la sottocartella nascosta `.github` con dentro il file
   `build-exe.yml`: se il tuo browser non la mostra trascinando la cartella,
   trascina i file uno per uno oppure carica direttamente lo zip e poi
   estrailo con l'apposito comando "Add file > Upload" ripetuto per ogni file).
5. In basso clicca **"Commit changes"** per confermare il caricamento.
6. Vai sulla scheda **"Actions"** in alto nel repository: dopo pochi secondi
   vedrai partire automaticamente un'operazione chiamata **"Crea eseguibile
   Windows"** con un pallino giallo che gira (in corso). Aspetta 2-3 minuti
   finche' diventa un segno di spunta verde ✔.
7. Clicca su quell'operazione completata, scorri in basso fino alla sezione
   **"Artifacts"** e clicca su **"GestionaleMagazzino-Windows"** per scaricare
   uno zip contenente il file **GestionaleMagazzino.exe** gia' pronto.
8. Estrai lo zip scaricato e sposta `GestionaleMagazzino.exe` dove preferisci
   sul PC Windows (es. sul Desktop): da li' in poi si avvia con un doppio
   click, senza bisogno di installare nulla.

Ogni volta che modifichi il codice e lo ricarichi su GitHub, un nuovo file
.exe aggiornato verra' ricompilato automaticamente allo stesso modo.

## Alternativa: creare l'exe manualmente su un PC Windows

Se preferisci non usare GitHub, puoi compilare l'eseguibile direttamente su un
PC Windows con Python 3.10 o superiore installato
(https://www.python.org/downloads/ - durante l'installazione spunta "Add
Python to PATH").

1. Copia l'intera cartella `gestionale` sul PC Windows.
2. Apri la cartella e fai doppio click su **`crea_eseguibile.bat`**.
3. Attendi il completamento (la prima volta scarica alcune librerie, puo'
   richiedere qualche minuto).
4. Il programma pronto si trovera' in `dist\GestionaleMagazzino.exe`.

In alternativa, se preferite non creare l'exe, il programma si puo' avviare
direttamente con Python installando le dipendenze (`pip install -r
requirements.txt`) e lanciando `python main.py`.

## Struttura dei file

```
gestionale/
├── main.py              -> avvia il programma
├── app.py                -> interfaccia grafica (tutte le schermate)
├── db.py                  -> gestione del database (SQLite)
├── pdf_export.py          -> generazione del catalogo PDF
├── requirements.txt       -> librerie necessarie
├── crea_eseguibile.bat    -> script per creare il file .exe
└── magazzino.db            -> il database (creato automaticamente al primo avvio)
```

## Personalizzazioni consigliate prima di iniziare

- Vai su **Impostazioni** e inserisci il nome dell'attivita' (comparira' sul
  catalogo PDF) e la percentuale di variazione prezzo che vuoi monitorare.
- Inserisci i primi prodotti da **Prodotti > + Nuovo prodotto**.
- Da **Ingressi/Uscite** registra i movimenti di magazzino man mano che
  arrivano o escono merci: e' li' che il sistema calcola avvisi di riordino e
  variazioni di prezzo.

## Possibili estensioni future

Se in futuro servisse far usare il programma a piu' postazioni contemporaneamente
(rete locale, piu' commessi), oppure una vera sincronizzazione automatica e
bidirezionale con Google Drive/Sheets, si puo' evolvere il programma verso un
database condiviso (es. su un server locale) o un'app web: siamo felici di
aiutarvi quando sarete a quel punto.
