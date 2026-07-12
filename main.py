"""
Main entry point. Run this on a schedule (see .github/workflows/fetch.yml).

Flow:
1. Load config.yaml
2. Fetch questions from Reddit (+ StockTwits, Quora, Stack Exchange)
3. Filter out anything already sent before (state.json)
4. Rank by engagement (score + comments)
5. Send top N as a Telegram digest
6. Merge results into latest_questions.json (dashboard accumulates history)
"""

import json
import os
from datetime import datetime, timezone
import yaml

from reddit_fetcher import fetch_reddit_questions
from stocktwits_fetcher import fetch_stocktwits_questions
from quora_search import fetch_quora_questions
from stackexchange_fetcher import fetch_stackexchange_questions
from telegram_notifier import send_telegram_digest

STATE_FILE = "state.json"
DASHBOARD_FILE = "latest_questions.json"
MAX_ITEMS_PER_DIGEST = 15
MAX_STATE_IDS = 2000
MAX_DASHBOARD_ITEMS = 3000  # dashboard accumulates across runs, capped here


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"sent_ids": []}


def save_state(state):
    state["sent_ids"] = state["sent_ids"][-MAX_STATE_IDS:]
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def save_dashboard(items, generated_at):
    """Merge this run's questions into the existing dashboard file instead
    of overwriting it, so the dashboard accumulates history across runs.
    Deduped by (source, id); capped at MAX_DASHBOARD_ITEMS, oldest first out."""
    existing_by_key = {}

    if os.path.exists(DASHBOARD_FILE):
        try:
            with open(DASHBOARD_FILE, "r") as f:
                old_data = json.load(f)
            for q in old_data.get("questions", []):
                key = f"{q.get('source')}:{q.get('id')}"
                existing_by_key[key] = q
        except Exception as e:
            print(f"[main] Could not read existing dashboard file, starting fresh: {e}")

    for item in items:
        key = f"{item.get('source')}:{item.get('id')}"
        existing_by_key[key] = item

    merged = list(existing_by_key.values())
    merged.sort(key=lambda x: x.get("created_utc") or 0, reverse=True)
    merged = merged[:MAX_DASHBOARD_ITEMS]

    payload = {
        "generated_at": generated_at,
        "count": len(merged),
        "questions": merged,
    }
    with open(DASHBOARD_FILE, "w") as f:
        json.dump(payload, f, indent=2)


def main():
    config = load_config()
    state = load_state()
    sent_ids = set(state.get("sent_ids", []))

    all_items = []
    all_items += fetch_reddit_questions(config)
    all_items += fetch_stocktwits_questions(config)
    all_items += fetch_quora_questions(config)
    all_items += fetch_stackexchange_questions(config)

    new_items = [item for item in all_items if item["id"] not in sent_ids]
    new_items.sort(key=lambda x: (x.get("score", 0) - x.get("num_comments", 0)), reverse=True)
    top_items = new_items[:MAX_ITEMS_PER_DIGEST]

    print(f"Found {len(all_items)} total, {len(new_items)} new, sending {len(top_items)}.")

    all_items_sorted = sorted(
        all_items, key=lambda x: (x.get("score", 0) - x.get("num_comments", 0)), reverse=True
    )
    save_dashboard(all_items_sorted, datetime.now(timezone.utc).isoformat())

    if top_items:
        send_telegram_digest(top_items)
        state["sent_ids"] = list(sent_ids) + [item["id"] for item in top_items]
        save_state(state)
    else:
        print("Nothing new to send this run.")


if __name__ == "__main__":
    main()
