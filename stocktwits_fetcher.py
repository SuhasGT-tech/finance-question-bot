"""
Fetches recent messages from StockTwits (free public API, no key required)
for configured symbols. Useful for spotting what retail investors are
currently asking/discussing about specific tickers.

API docs: https://api.stocktwits.com/developers/docs
Note: StockTwits rate-limits unauthenticated requests, so keep symbol list short.
"""

import requests

BASE_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"


def fetch_stocktwits_questions(config: dict) -> list:
    st_config = config.get("stocktwits", {})
    if not st_config.get("enabled"):
        return []

    symbols = st_config.get("symbols", [])
    results = []

    for symbol in symbols:
        try:
            resp = requests.get(BASE_URL.format(symbol=symbol), timeout=10)
            if resp.status_code != 200:
                print(f"[stocktwits_fetcher] {symbol} returned {resp.status_code}")
                continue
            data = resp.json()
            messages = data.get("messages", [])
            for msg in messages:
                body = msg.get("body", "")
                if "?" not in body:
                    continue  # only keep genuine questions
                results.append({
                    "source": "stocktwits",
                    "symbol": symbol,
                    "id": str(msg.get("id")),
                    "title": body,
                    "url": f"https://stocktwits.com/symbol/{symbol}",
                    "score": msg.get("likes", {}).get("total", 0) if msg.get("likes") else 0,
                    "num_comments": 0,
                    "created_utc": msg.get("created_at"),
                })
        except Exception as e:
            print(f"[stocktwits_fetcher] Error fetching {symbol}: {e}")

    return results
