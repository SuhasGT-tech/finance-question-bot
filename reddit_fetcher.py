"""
Fetches finance-related "question" posts from Reddit using Reddit's PUBLIC JSON
endpoints (e.g. https://www.reddit.com/r/investing/new.json).

This requires NO Reddit developer app, NO client_id/secret, and NO login.
It works because Reddit exposes read-only JSON versions of every public page.

Note: this only works for public subreddits and is subject to normal rate limits
(keep requests modest -- this script already does, one request per subreddit
per run). Always send a descriptive User-Agent (required by Reddit or you'll get
blocked/throttled).
"""

import requests
import time

HEADERS = {
    "User-Agent": "finance-question-bot/1.0 (by u/your_username_here)"
}


def looks_like_question(title: str, keywords: list) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


def contains_finance_keyword(title: str, keywords: list) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


def fetch_reddit_questions(config: dict) -> list:
    results = []

    subreddits = config["subreddits"]
    limit = config.get("posts_per_subreddit", 25)
    min_score = config.get("min_score", 5)
    max_comments = config.get("max_comments_for_opportunity", 15)
    q_keywords = config.get("question_keywords", ["?"])
    f_keywords = config.get("finance_keywords", [])

    finance_only_subs = {
        "personalfinance", "investing", "stocks", "stockmarket",
        "financialplanning", "cryptocurrency", "tax",
        "povertyfinance", "dividends", "options",
    }

    for sub_name in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub_name}/new.json"
            resp = requests.get(
                url,
                headers=HEADERS,
                params={"limit": limit},
                timeout=10,
            )
            if resp.status_code != 200:
                print(f"[reddit_fetcher] r/{sub_name} returned {resp.status_code}")
                continue

            data = resp.json()
            posts = data.get("data", {}).get("children", [])

            for post_wrapper in posts:
                post = post_wrapper.get("data", {})
                title = post.get("title", "")
                score = post.get("score", 0)
                num_comments = post.get("num_comments", 0)

                if score < min_score:
                    continue
                if num_comments > max_comments:
                    continue
                if not looks_like_question(title, q_keywords):
                    continue
                if f_keywords and sub_name.lower() not in finance_only_subs:
                    if not contains_finance_keyword(title, f_keywords):
                        continue

                results.append({
                    "source": "reddit",
                    "subreddit": sub_name,
                    "id": post.get("id"),
                    "title": title,
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "score": score,
                    "num_comments": num_comments,
                    "created_utc": post.get("created_utc"),
                })

            # Be polite to Reddit's servers -- small delay between subreddits
            time.sleep(1.5)

        except Exception as e:
            print(f"[reddit_fetcher] Error fetching r/{sub_name}: {e}")

    return results
