"""
Fetches finance-related "question" posts from Reddit via PullPush
(https://pullpush.io), a free, unauthenticated mirror/search API for Reddit
data. This replaces the old reddit.com/.json approach, which Reddit blocked
for all unauthenticated requests on May 30, 2026.

No Reddit developer app, no client_id/secret, no login, no approval queue.

Notes:
- PullPush is community-run, not officially affiliated with Reddit. It can
  have occasional outages and isn't perfectly real-time (usually minutes to
  a couple hours of lag), but it's the best free, no-approval option today.
- If PullPush is ever down or slow, this fetcher fails soft (logs a message,
  returns whatever it has) rather than crashing the whole pipeline.
"""

import requests
import time

PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"

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
            resp = requests.get(
                PULLPUSH_URL,
                headers=HEADERS,
                params={
                    "subreddit": sub_name,
                    "size": limit,
                    "sort": "desc",   # newest first
                    "sort_type": "created_utc",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                print(f"[reddit_fetcher] r/{sub_name} returned {resp.status_code}")
                continue

            data = resp.json()
            posts = data.get("data", [])

            for post in posts:
                title = post.get("title", "")
                score = post.get("score", 0) or 0
                num_comments = post.get("num_comments", 0) or 0

                if score < min_score:
                    continue
                if num_comments > max_comments:
                    continue
                if not looks_like_question(title, q_keywords):
                    continue
                if f_keywords and sub_name.lower() not in finance_only_subs:
                    if not contains_finance_keyword(title, f_keywords):
                        continue

                permalink = post.get("permalink") or f"/r/{sub_name}/comments/{post.get('id')}/"
                results.append({
                    "source": "reddit",
                    "subreddit": sub_name,
                    "id": post.get("id"),
                    "title": title,
                    "url": f"https://reddit.com{permalink}",
                    "score": score,
                    "num_comments": num_comments,
                    "created_utc": post.get("created_utc"),
                })

            # Be polite -- small delay between subreddits (PullPush is free
            # and community-run; don't hammer it)
            time.sleep(1.5)

        except Exception as e:
            print(f"[reddit_fetcher] Error fetching r/{sub_name} via PullPush: {e}")

    return results
