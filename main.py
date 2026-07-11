"""
Main entry point. Run this on a schedule (see .github/workflows/fetch.yml).

Flow:
1. Load config.yaml
2. Fetch questions from Reddit (+ optional StockTwits, + optional Quora)
3. Filter out anything already sent before (state.json)
4. Rank by engagement (score + comments)
5. Send top N as a Telegram digest
6. Save updated state.json (so the workflow can commit it back)
"""

import json
import os
from datetime import datetime, timezone
import yaml

from reddit_fetcher import fetch_reddit_questions
from stocktwits_fetcher import fetch_stocktwits_questions
from stackexchange_fetcher import fetch_stackexchange_questions
from quora_search import fetch_quora_questions
from telegram_notifier import send_telegram_digest

STATE_FILE = "state.json"
DASHBOARD_FILE = "latest_questions.json"
MAX_ITEMS_PER_DIGEST = 15
MAX_STATE_IDS = 2000  # cap so the state file doesn't grow forever
MAX_DASHBOARD_ITEMS = 100  # how many questions the live dashboard shows


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"sent_ids": []}


def save_state(state):
    # Keep only the most recent MAX_STATE_IDS to avoid unbounded growth
    state["sent_ids"] = state["sent_ids"][-MAX_STATE_IDS:]
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def save_dashboard(items, generated_at):
    """Write the latest ranked questions to a JSON file the live dashboard
    reads directly from GitHub (via raw.githubusercontent.com), so the
    client always sees fresh data with no extra hosting needed."""
    payload = {
        "generated_at": generated_at,
        "count": len(items[:MAX_DASHBOARD_ITEMS]),
        "questions": items[:MAX_DASHBOARD_ITEMS],
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

    # Dedup against previously sent items
    new_items = [item for item in all_items if item["id"] not in sent_ids]

    # Rank: prioritize high engagement, low answer count (real opportunity)
    new_items.sort(key=lambda x: (x.get("score", 0) - x.get("num_comments", 0)), reverse=True)

    top_items = new_items[:MAX_ITEMS_PER_DIGEST]

    print(f"Found {len(all_items)} total, {len(new_items)} new, sending {len(top_items)}.")

    # Always refresh the dashboard file, even if nothing new to send --
    # the client's live view should reflect "here's what's out there right
    # now", ranked by the same engagement score, regardless of Telegram state.
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
