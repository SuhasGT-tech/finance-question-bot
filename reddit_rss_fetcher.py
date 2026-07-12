"""
Fetches finance-related "question" posts from Reddit via its public .rss
feeds (e.g. https://www.reddit.com/r/investing/new.rss) -- a different
code path from Reddit's .json/OAuth API, and one that has survived every
lockdown Reddit has done in 2026 (May's .json shutdown, the March human
verification requirement, the June old.reddit.com login wall). No key,
no OAuth app, no approval queue, no billing.

IMPORTANT TRADE-OFF: RSS/Atom feeds do not include score or comment count
(Reddit doesn't publish that data in this format). So results from this
fetcher are NOT filtered by min_score / max_comments_for_opportunity the
way reddit_fetcher.py (PullPush) results are -- there's nothing to filter
on. They're included as "found", not "found and pre-validated as popular".
score/num_comments are set to 0 (not "no engagement", just "unknown").

Uses Python's built-in xml parser -- no extra dependency needed.
"""

import re
import time
from datetime import datetime, timezone
from xml.etree import ElementTree

import requests

ATOM_NS = "{http://www.w3.org/2005/Atom}"
HEADERS = {
    "User-Agent": "finance-question-bot/1.0 (RSS reader; personal project)"
}

POST_ID_RE = re.compile(r"/comments/([a-z0-9]+)/")


def is_genuine_question(title: str, keywords: list) -> bool:
    t = title.strip().lower()
    if t.endswith("?"):
        return True
    starters = [kw.lower() for kw in keywords if kw != "?"]
    return any(t.startswith(kw) for kw in starters)


def contains_finance_keyword(title: str, keywords: list) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


def _parse_time(text: str):
    """Atom timestamps look like '2026-07-12T10:15:00+00:00' or end in 'Z'."""
    if not text:
        return None
    try:
        text = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return int(dt.timestamp())
    except Exception:
        return None


def fetch_reddit_rss_questions(config: dict) -> list:
    rss_config = config.get("reddit_rss", {})
    if not rss_config.get("enabled"):
        return []

    subreddits = config.get("subreddits", [])
    limit = rss_config.get("limit", 25)
    q_keywords = config.get("question_keywords", ["?"])
    f_keywords = config.get("finance_keywords", [])

    finance_only_subs = {
        "personalfinance", "investing", "stocks", "stockmarket",
        "financialplanning", "cryptocurrency", "tax",
        "povertyfinance", "dividends", "options",
    }

    results = []

    for sub_name in subreddits:
        url = f"https://www.reddit.com/r/{sub_name}/new.rss"

        for attempt in range(3):
            try:
                resp = requests.get(
                    url,
                    headers=HEADERS,
                    params={"limit": limit},
                    timeout=15,
                )

                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    print(f"[reddit_rss_fetcher] r/{sub_name} rate-limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    print(f"[reddit_rss_fetcher] r/{sub_name} returned {resp.status_code}")
                    break

                root = ElementTree.fromstring(resp.content)
                entries = root.findall(f"{ATOM_NS}entry")

                kept = 0
                for entry in entries:
                    title_el = entry.find(f"{ATOM_NS}title")
                    title = title_el.text if title_el is not None else ""
                    if not title:
                        continue

                    link_el = entry.find(f"{ATOM_NS}link")
                    post_url = link_el.get("href") if link_el is not None else ""

                    id_match = POST_ID_RE.search(post_url)
                    post_id = id_match.group(1) if id_match else None
                    if not post_id:
                        continue  # can't dedupe/track without a stable id

                    if not is_genuine_question(title, q_keywords):
                        continue
                    if f_keywords and sub_name.lower() not in finance_only_subs:
                        if not contains_finance_keyword(title, f_keywords):
                            continue

                    updated_el = entry.find(f"{ATOM_NS}updated")
                    published_el = entry.find(f"{ATOM_NS}published")
                    time_text = (
                        (published_el.text if published_el is not None else None)
                        or (updated_el.text if updated_el is not None else None)
                    )
                    created_utc = _parse_time(time_text) or int(datetime.now(timezone.utc).timestamp())

                    results.append({
                        "source": "reddit",
                        "subreddit": sub_name,
                        "id": post_id,
                        "title": title,
                        "url": post_url,
                        "score": 0,          # not available via RSS -- see module docstring
                        "num_comments": 0,   # not available via RSS -- see module docstring
                        "created_utc": created_utc,
                    })
                    kept += 1

                print(f"[reddit_rss_fetcher] r/{sub_name}: {len(entries)} raw, {kept} kept")
                break  # success, no retry needed

            except Exception as e:
                print(f"[reddit_rss_fetcher] Error fetching r/{sub_name}: {e}")
                break

        time.sleep(1.5)  # be polite between subreddits

    return results
