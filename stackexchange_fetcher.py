"""
Fetches real finance questions from Stack Exchange's "Personal Finance &
Money" site (money.stackexchange.com) via the official public API
(https://api.stackexchange.com/2.3).

Why this instead of Reddit/Quora:
- Free, public, no billing account, no OAuth approval queue.
- 300 requests/day unauthenticated (plenty for this bot -- one run uses 1
  request). Can be raised to 10,000/day with a free key from
  stackapps.com if ever needed -- no card required.
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

    params = {
        "order": "desc",
        "sort": "creation",   # newest first -- real-time feed
        "site": site,
        "pagesize": pagesize,
        # No custom "filter" param needed -- the API's built-in "default"
        # filter already includes score, answer_count, link, title, etc.
    }
    if tags:
        params["tagged"] = ";".join(tags)

    results = []

    try:
        resp = requests.get(API_URL, params=params, timeout=15)

        if resp.status_code != 200:
            print(f"[stackexchange_fetcher] {site} returned {resp.status_code}: {resp.text[:200]}")
            return results

        data = resp.json()

        if data.get("error_id"):
            print(f"[stackexchange_fetcher] API error: {data.get('error_message')}")
            return results

        questions = data.get("items", [])

        for q in questions:
            score = q.get("score", 0) or 0
            answer_count = q.get("answer_count", 0) or 0

            if score < min_score:
                continue
            if answer_count > max_comments:
                continue

            results.append({
                "source": "stackexchange",
                "site": site,
                "id": str(q.get("question_id")),
                "title": q.get("title", ""),
                "url": q.get("link", ""),
                "score": score,
                "num_comments": answer_count,
                "created_utc": q.get("creation_date"),
            })

        print(f"[stackexchange_fetcher] {site}: {len(questions)} raw, {len(results)} kept")

    except Exception as e:
        print(f"[stackexchange_fetcher] Error fetching from {site}: {e}")

    return results
