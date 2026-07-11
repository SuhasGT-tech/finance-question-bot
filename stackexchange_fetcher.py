"""
Fetches real finance questions from Stack Exchange's "Personal Finance &
Money" site (money.stackexchange.com) via the official public API
(https://api.stackexchange.com/2.3).

Why this instead of Reddit/Quora:
- Free, public, no billing account, no OAuth approval queue.
- 300 requests/day unauthenticated (plenty for this bot -- one run uses
  a handful of requests, one per tag). Can be raised to 10,000/day with
  a free key from stackapps.com if ever needed -- no card required.
- Works fine from GitHub Actions -- no IP blocking like Reddit/StockTwits.
- Every result is already a genuine question by construction (Stack
  Exchange doesn't allow non-question posts), so no keyword guessing needed.
"""

import requests

API_URL = "https://api.stackexchange.com/2.3/questions"


def fetch_stackexchange_questions(config: dict) -> list:
    se_config = config.get("stackexchange", {})
    if not se_config.get("enabled"):
        return []

    site = se_config.get("site", "money")
    pagesize = se_config.get("pagesize", 25)
    tags = se_config.get("tags", [])

    max_comments = config.get("max_comments_for_opportunity", 15)
    min_score = config.get("min_score", 0)  # SE questions start at 0, unlike Reddit

    # IMPORTANT: Stack Exchange's `tagged` param is an AND match -- a
    # question must have ALL listed tags to match, not just one. To get
    # topic variety we instead run one query per tag and merge/dedupe the
    # results, rather than one query with every tag combined (which would
    # almost always return nothing).
    tag_groups = tags if tags else [None]  # None = no tag filter, just newest

    results = []
    seen_ids = set()

    for tag in tag_groups:
        params = {
            "order": "desc",
            "sort": "creation",   # newest first -- real-time feed
            "site": site,
            "pagesize": pagesize,
        }
        if tag:
            params["tagged"] = tag

        try:
            resp = requests.get(API_URL, params=params, timeout=15)

            if resp.status_code != 200:
                print(f"[stackexchange_fetcher] {site} (tag={tag}) returned {resp.status_code}: {resp.text[:200]}")
                continue

            data = resp.json()

            if data.get("error_id"):
                print(f"[stackexchange_fetcher] API error (tag={tag}): {data.get('error_message')}")
                continue

            questions = data.get("items", [])
            kept = 0

            for q in questions:
                qid = q.get("question_id")
                if qid in seen_ids:
                    continue  # already picked up via another tag

                score = q.get("score", 0) or 0
                answer_count = q.get("answer_count", 0) or 0

                if score < min_score:
                    continue
                if answer_count > max_comments:
                    continue

                seen_ids.add(qid)
                results.append({
                    "source": "stackexchange",
                    "site": site,
                    "id": str(qid),
                    "title": q.get("title", ""),
                    "url": q.get("link", ""),
                    "score": score,
                    "num_comments": answer_count,
                    "created_utc": q.get("creation_date"),
                })
                kept += 1

            print(f"[stackexchange_fetcher] {site} (tag={tag}): {len(questions)} raw, {kept} kept")

        except Exception as e:
            print(f"[stackexchange_fetcher] Error fetching from {site} (tag={tag}): {e}")

    return results
