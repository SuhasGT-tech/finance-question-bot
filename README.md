# Finance Question Bot

Fetches real finance questions people are asking on Reddit (+ optional StockTwits and
Quora-via-Google), and sends your client a Telegram digest automatically — for free,
using GitHub Actions as the scheduler.

## What it does
Every 3 hours (configurable), it:
1. Scans finance subreddits for new posts that look like genuine questions
2. Filters out posts that already got a lot of comments (i.e. already "answered" —
   less of a video opportunity)
3. Ranks by engagement (score minus existing comments)
4. Sends the top ~15 as a Telegram message
5. Remembers what it already sent, so you never get duplicates

## One-time setup (about 15–20 minutes)

### 1. Create a Telegram bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot`, follow the prompts, name it whatever you like
3. Copy the **token** it gives you (looks like `123456:ABC-def...`)
4. Send any message to your new bot (or add it to a group/channel)
5. Get your chat ID: visit this URL in a browser (replace TOKEN):
   `https://api.telegram.org/botTOKEN/getUpdates`
   Look for `"chat":{"id": 123456789 ...}` — that number is your `TELEGRAM_CHAT_ID`

### 2. Reddit — no setup needed!
This project reads Reddit's public JSON pages directly, so there's no app to
register, no client ID/secret, no login. It just works.

### 3. (Optional) Quora-via-Google setup
Only needed if you want the Quora supplement. Skip this if Reddit alone is enough to start.
1. Create a Programmable Search Engine: https://programmablesearchengine.google.com/
   → get your `GOOGLE_CSE_ID`
2. Create an API key: https://console.cloud.google.com/apis/credentials
   → get your `GOOGLE_CSE_API_KEY`
3. Set `quora_search.enabled: true` in `config.yaml`

### 4. Put this code in a GitHub repo
1. Create a new **private** GitHub repo
2. Push this folder's contents to it

### 5. Add your secrets to GitHub
In your repo: **Settings → Secrets and variables → Actions → New repository secret**
Add each of these:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- (optional) `GOOGLE_CSE_API_KEY`
- (optional) `GOOGLE_CSE_ID`

### 6. Turn it on
- Go to the **Actions** tab in your repo → you should see "Fetch Finance Questions"
- Click **Run workflow** to test it manually right away
- After that, it runs automatically every 3 hours (edit the cron schedule in
  `.github/workflows/fetch.yml` to change frequency)

## Customizing
Everything content-related lives in `config.yaml`:
- Add/remove subreddits
- Change what counts as a "question"
- Adjust engagement thresholds
- Add/remove StockTwits symbols

## Running locally (optional, for testing)
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=xxx
export TELEGRAM_CHAT_ID=xxx
python main.py
```

## Cost
$0. GitHub Actions free tier gives 2,000 minutes/month on private repos (this job
takes seconds to run), Reddit's API is free for this volume, Telegram Bot API is free,
StockTwits public endpoint is free. Only the optional Quora/Google step has a
100-query/day free cap, well beyond what you need for a 3-hourly digest.

## Note on Quora
There is no official Quora API, and scraping quora.com directly violates their
Terms of Service and gets blocked quickly anyway. This project intentionally does
NOT scrape Quora. The optional module instead reads Google's public search index
for Quora question pages — legal, but not real-time. If Quora coverage becomes
important later, it's worth revisiting with a paid data provider rather than scraping.
