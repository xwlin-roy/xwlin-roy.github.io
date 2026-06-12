import json
import os
import sys
import time
import urllib.parse
import urllib.request

SCHOLAR_ID = os.environ.get("SCHOLAR_ID", "Zv_rC0AAAAAJ")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
PAGE_SIZE = 100


def fetch_json(params):
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_stats_serpapi(scholar_id, api_key):
    """Fetch Google Scholar author stats via SerpAPI."""
    if not api_key:
        print("ERROR: SERPAPI_KEY environment variable is not set.")
        sys.exit(1)

    base_params = {
        "engine": "google_scholar_author",
        "author_id": scholar_id,
        "hl": "en",
        "api_key": api_key,
        "num": str(PAGE_SIZE),
    }
    print("Fetching author profile from SerpAPI...")
    data = fetch_json(base_params)

    # Citation table rows: {"citations": {"all": N}}, {"h_index": {"all": N}}, {"i10_index": {"all": N}}
    metrics = {}
    for row in data.get("cited_by", {}).get("table", []):
        for key, values in row.items():
            metrics[key.replace("_", "")] = values.get("all", 0)

    publications = {}
    while True:
        articles = data.get("articles", [])
        for article in articles:
            title = article.get("title", "")
            pub_id = article.get("citation_id") or scholar_id + ":" + title[:30]
            publications[pub_id] = {
                "title": title,
                "num_citations": (article.get("cited_by") or {}).get("value") or 0,
            }
        if len(articles) < PAGE_SIZE:
            break
        print(f"Fetching next page (start={len(publications)})...")
        time.sleep(1)
        data = fetch_json({**base_params, "start": str(len(publications))})

    return {
        "citedby": metrics.get("citations", 0),
        "hindex": metrics.get("hindex", 0),
        "i10index": metrics.get("i10index", 0),
        "publications": publications,
    }


def main():
    print(f"Fetching Google Scholar stats for {SCHOLAR_ID} via SerpAPI...")

    data = None
    for attempt in range(3):
        try:
            data = get_stats_serpapi(SCHOLAR_ID, SERPAPI_KEY)
            if data and data.get("citedby", 0) > 0:
                break
            print(f"Attempt {attempt + 1}: Got 0 citations, retrying...")
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
        data = None
        time.sleep(5 * (attempt + 1))

    if not data or data.get("citedby", 0) == 0:
        print("ERROR: Could not fetch valid citation data. Aborting to preserve existing data.")
        sys.exit(1)

    print(f"Total citations: {data['citedby']}, h-index: {data['hindex']}, i10-index: {data['i10index']}")
    print(f"Total publications fetched: {len(data['publications'])}")

    with open("gs_data.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    shieldsio_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(data["citedby"]),
        "color": "9cf",
        "namedLogo": "Google Scholar",
    }
    with open("gs_data_shieldsio.json", "w") as f:
        json.dump(shieldsio_data, f, indent=2)

    print("Done! Files written: gs_data.json, gs_data_shieldsio.json")


if __name__ == "__main__":
    main()
