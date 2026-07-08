"""
Optional supplement: finds Quora finance QUESTIONS via Google Custom Search API
(free tier: 100 queries/day). This is NOT real-time and NOT a Quora scraper --
it just surfaces publicly indexed Quora question pages that Google has crawled.

This respects Quora's terms (we never touch quora.com directly, no scraping,
no bypassing their bot protection) -- we only read Google's search index.

Setup:
1. Create a Custom Search Engine at https://programmablesearchengine.google.com/
   - Set it to search the entire web, restrict results to quora.com if you like
2. Get an API key at https://console.cloud.google.com/apis/credentials
3. Set as env vars / GitHub secrets: GOOGLE_CSE_ID, GOOGLE_CSE_API_KEY
"""

import os
import requests

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


def fetch_quora_questions(config: dict) -> list:
    q_config = config.get("quora_search", {})
    if not q_config.get("enabled"):
        return []

    api_key = os.environ.get("GOOGLE_CSE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        print("[quora_search] Missing GOOGLE_CSE_API_KEY / GOOGLE_CSE_ID, skipping.")
        return []

    query = q_config.get("query", "site:quora.com finance question")
    max_results = q_config.get("max_results", 10)

    try:
        resp = requests.get(SEARCH_URL, params={
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": min(max_results, 10),
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[quora_search] Error: {e}")
        return []

    results = []
    for item in data.get("items", []):
        results.append({
            "source": "quora",
            "id": item.get("link"),
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "score": 0,
            "num_comments": 0,
            "created_utc": None,
        })
    return results
