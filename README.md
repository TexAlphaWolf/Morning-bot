# 🤖 Morning News & Weather Bot — Railway Deploy

Bot Telegram che ogni mattina alle 8:00 ti invia:
- 🗓️ Previsioni meteo a 7 giorni
- 📰 Top news mondiali da 24 fonti (con deduplicazione)

---

## 📁 File del progetto

```
morning_bot.py   ← codice principale
requirements.txt ← dipendenze Python
Procfile         ← dice a Railway come avviare il bot
runtime.txt      ← versione Python
.gitignore       ← esclude file sensibili
```

---

## 🚀 Deploy su Railway (passo per passo)

### 1. Prepara le API keys

**Telegram Bot Token:**
1. Apri Telegram → cerca `@BotFather`
2. Scrivi `/newbot`, segui le istruzioni
3. Copia il token (es. `123456789:ABC-xyz...`)
4. Per trovare il tuo **Chat ID**: cerca `@userinfobot` su Telegram → scrivi `/start`

**OpenWeatherMap API Key (gratuita):**
1. Vai su https://openweathermap.org → Sign Up
2. Vai su *My API Keys* → copia la chiave
3. Aspetta ~10 minuti che si attivi

---

### 2. Crea un repository GitHub

```bash
# Crea una cartella e inizializza git
mkdir morning-bot && cd morning-bot

# Copia qui dentro tutti e 5 i file del progetto, poi:
git init
git add .
git commit -m "first commit"
```

Poi vai su https://github.com/new → crea un repo vuoto → segui le istruzioni per fare il push.

---

### 3. Deploy su Railway

1. Vai su https://railway.app → **Sign up with GitHub** (gratuito)
2. Click **New Project** → **Deploy from GitHub repo**
3. Seleziona il tuo repository `morning-bot`
4. Railway rileva automaticamente il `Procfile` e avvia il deploy

---

### 4. Configura le variabili d'ambiente

Nel progetto Railway, vai su **Variables** e aggiungi:

| Nome variabile       | Valore esempio              |
|----------------------|-----------------------------|
| `TELEGRAM_TOKEN`     | `123456789:ABC-xyz...`      |
| `TELEGRAM_CHAT_ID`   | `987654321`                 |
| `OPENWEATHER_API_KEY`| `abcdef1234567890`          |
| `CITY`               | `Turin` (la tua città in inglese) |
| `TIMEZONE`           | `Europe/Rome`               |
| `SEND_HOUR`          | `8`                         |
| `SEND_MINUTE`        | `0`                         |

⚠️ **Non scrivere mai le API keys nel codice!** Railway le inietta come variabili d'ambiente sicure.

---

### 5. Verifica che funzioni

Vai su **Deployments** → apri i log → dovresti vedere:
```
✅ Bot running on Railway — daily message at 08:00 (Europe/Rome)
```

Ogni mattina alle 8:00 riceverai il messaggio su Telegram! 🎉

---

## ⚙️ Personalizzazione

Modifica le variabili d'ambiente su Railway (senza toccare il codice):

- **Cambia orario**: modifica `SEND_HOUR` e `SEND_MINUTE`
- **Cambia città**: modifica `CITY` (sempre in inglese, es. `Milan`, `Naples`)
- **Cambia fuso orario**: modifica `TIMEZONE` (es. `America/New_York`)

---

## 💰 Costi Railway

Il piano **Hobby gratuito** include:
- $5 di crediti al mese (più che sufficienti per questo bot leggero)
- Nessuna carta di credito richiesta per iniziare
- Il bot consuma circa $0.50–1.00/mese → **praticamente gratuito**

---

## 🆘 Problemi comuni

**Il bot non manda messaggi:**
- Controlla che le variabili d'ambiente siano corrette
- Verifica nei log di Railway eventuali errori

**Errore meteo:**
- La chiave OpenWeatherMap impiega ~10 min ad attivarsi dopo la registrazione

**Messaggi duplicati:**
- Riavvia il deployment da Railway → Settings → Redeploy
