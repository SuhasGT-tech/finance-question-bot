"""
Fetches finance-related "question" posts from Reddit via the PullPush API
(https://pullpush.io) -- a free, no-signup mirror of Reddit's search data that
isn't blocked for cloud/data-center IPs the way Reddit's own endpoints are.

Key fix vs. earlier version: this now explicitly requests only RECENT posts
(controlled by `recency_hours` in config.yaml) sorted newest-first, instead of
pulling whatever PullPush happens to return (which could be over a year old).
"""

import requests
import time

BASE_URL = "https://api.pullpush.io/reddit/search/submission/"


def is_genuine_question(title: str, keywords: list) -> bool:
    """
    Stricter check: a real question either ends with '?' or clearly opens
    with a question phrase. This avoids picking up statements/rants that
    merely contain a keyword like 'how to' buried mid-sentence.
    """
    t = title.strip().lower()
    if t.endswith("?"):
        return True
    # Only count keyword phrases if they appear at/near the start,
    # which is how real questions are usually phrased.
    starters = [kw.lower() for kw in keywords if kw != "?"]
    return any(t.startswith(kw) for kw in starters)


def contains_finance_keyword(title: str, keywords: list) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


def fetch_reddit_questions(config: dict) -> list:
    results = []

    subreddits = config["subreddits"]
    limit = config.get("posts_per_subreddit", 25)
    min_score = config.get("min_score", 1)
    max_comments = config.get("max_comments_for_opportunity", 15)
    q_keywords = config.get("question_keywords", ["?"])
    f_keywords = config.get("finance_keywords", [])
    recency_hours = config.get("recency_hours", 48)

    finance_only_subs = {
        "personalfinance", "investing", "stocks", "stockmarket",
        "financialplanning", "cryptocurrency", "tax",
        "povertyfinance", "dividends", "options",
    }

    for sub_name in subreddits:
        after_timestamp = int(time.time()) - (recency_hours * 3600)

        for attempt in range(3):
            try:
                resp = requests.get(
                    BASE_URL,
                    params={
                        "subreddit": sub_name,
                        "size": limit,
                        "sort": "desc",
                        "sort_type": "created_utc",
                        "after": after_timestamp,  # precise unix timestamp, more reliable than "48h"
                    },
                    timeout=15,
                )

                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    print(f"[reddit_fetcher] r/{sub_name} rate-limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    print(f"[reddit_fetcher] r/{sub_name} returned {resp.status_code}: {resp.text[:200]}")
                    break

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
                    if not is_genuine_question(title, q_keywords):
                        continue
                    if f_keywords and sub_name.lower() not in finance_only_subs:
                        if not contains_finance_keyword(title, f_keywords):
                            continue

                    permalink = post.get("permalink", "")
                    url = f"https://reddit.com{permalink}" if permalink else post.get("url", "")

                    results.append({
                        "source": "reddit",
                        "subreddit": sub_name,
                        "id": post.get("id"),
                        "title": title,
                        "url": url,
                        "score": score,
                        "num_comments": num_comments,
                        "created_utc": post.get("created_utc"),
                    })

                break  # success, no need to retry

            except Exception as e:
                print(f"[reddit_fetcher] Error fetching r/{sub_name}: {e}")
                break

        time.sleep(1.5)  # be polite to the free API between subreddits

    return results
