# Rassegna stampa Foggia → Telegram

Bot che ogni 15 minuti legge 84 fonti su Foggia e provincia e invia su Telegram solo le notizie di **cronaca, politica, sport e ordine e sicurezza pubblica**, senza doppioni. Gira sui server di GitHub: il telefono può restare spento.

## File

| File | A cosa serve |
|---|---|
| `bot.py` | Il programma |
| `feeds.json` | Elenco delle fonti (si possono aggiungere o togliere) |
| `argomenti.json` | Parole chiave delle quattro categorie e parole da escludere |
| `inviate.json` | Memoria delle notizie già inviate (si aggiorna da sola) |
| `requirements.txt` | Librerie necessarie |
| `.github/workflows/rassegna.yml` | Dice a GitHub di avviare il bot ogni 15 minuti |

## Configurazione dal telefono

### 1. Crea il bot Telegram
1. In Telegram cerca **@BotFather** e scrivi `/newbot`.
2. Scegli un nome e un username che finisca con `bot`.
3. Copia il **token** che ti dà (tipo `123456789:AA…`). Non condividerlo.

### 2. Aggiungi il bot alla chat e trova l'ID
- **Canale:** aggiungi il bot come amministratore. Se il canale è pubblico, l'ID è `@nomecanale`.
- **Gruppo o canale privato:** aggiungi il bot (nei canali come amministratore), scrivi un messaggio nella chat, poi apri nel browser
  `https://api.telegram.org/botIL_TUO_TOKEN/getUpdates`
  e cerca `"chat":{"id":-100…`. Quel numero, segno meno compreso, è l'ID.

### 3. Crea il repository su GitHub
1. Su github.com crea un account (se non l'hai) e tocca **+ → New repository**.
2. Nome: `rassegna-foggia`. Scegli **Public** (vedi la nota sui costi in fondo).
3. Tocca **Create repository**.

### 4. Carica i file
1. Nel repository tocca **uploading an existing file** (oppure **Add file → Upload files**).
2. Seleziona `bot.py`, `feeds.json`, `argomenti.json`, `inviate.json`, `requirements.txt`, `README.md` e tocca **Commit changes**.
3. Poi **Add file → Create new file**. Come nome scrivi esattamente
   `.github/workflows/rassegna.yml`
   (le barre creano le cartelle), incolla il contenuto del file `rassegna.yml` e tocca **Commit changes**.

### 5. Inserisci token e chat ID
**Settings → Secrets and variables → Actions → New repository secret**, due volte:
- Nome `TELEGRAM_TOKEN`, valore: il token del punto 1
- Nome `TELEGRAM_CHAT_ID`, valore: l'ID del punto 2

### 6. Avvia
1. Tocca **Actions**. Se GitHub chiede di abilitare i workflow, conferma.
2. Apri **Rassegna stampa Foggia → Run workflow**.
3. Dopo un paio di minuti l'esecuzione diventa verde e le notizie arrivano in chat. Da quel momento parte da solo ogni 15 minuti.

Al primo avvio arrivano insieme le notizie delle ultime 3 ore.

## Personalizzare
- **Categorie:** in `bot.py`, riga `CATEGORIE_ATTIVE`. Togli `"sport"` per non riceverlo più.
- **Finestra di tempo:** in `bot.py`, `ORE_MASSIME`.
- **Parole chiave:** in `argomenti.json`. Una parola che finisce con `*` vale anche come inizio di parola (`arrest*` = arresto, arrestati…).
- **Fonti:** in `feeds.json`, copia una riga dell'elenco `feeds` e cambia nome e url.

I file si modificano dal telefono aprendoli su GitHub e toccando la matita.

## Se qualcosa non va
- **Esecuzione rossa con «Mancano TELEGRAM_TOKEN…»:** ricontrolla i nomi dei Secrets (punto 5).
- **«Token o chat ID non validi»:** token sbagliato, ID sbagliato o bot non aggiunto alla chat.
- **Errore nel passaggio «Salva l'elenco»:** Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.
- Le righe `! NomeFonte: HTTP 403` nel registro sono normali: quel sito ha rifiutato la lettura in quel giro e il bot va avanti con le altre fonti.

## Note
- **Costi:** sui repository pubblici GitHub Actions è gratuito. Sui privati c'è un tetto di minuti gratuiti al mese che un avvio ogni 15 minuti rischia di superare.
- **Orari:** GitHub può avviare le esecuzioni con qualche minuto di ritardo nelle ore di punta.
- **Inattività:** se nel repository non succede nulla per 60 giorni, GitHub può sospendere le esecuzioni automatiche e manda un'email: basta riattivarle dalla scheda Actions.
