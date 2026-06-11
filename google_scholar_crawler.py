import json
import os
import sys
import time
import urllib.request
import urllib.parse

SCHOLAR_ID = os.environ.get("SCHOLAR_ID", "Zv_rC0AAAAAJ")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")


def get_stats_serpapi(scholar_id, api_key):
    """Fetch Google Scholar author stats via SerpAPI."""
    if not api_key:
        print("ERROR: SERPAPI_KEY environment variable is not set.")
        sys.exit(1)

    # Fetch author profile (includes citations, h-index, i10-index)
    params = {
        "engine": "google_scholar_author",
        "author_id": scholar_id,
        "hl": "en",
        "api_key": api_key,
    }
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
    print(f"Fetching author profile from SerpAPI...")

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # Extract author stats from the author profile response
    author = data.get("author", {})
    citedby = 0
    hindex = 0
    i10index = 0

    # The citation table is in the "cited_by" section of the response
    cited_by_section = data.get("cited_by", {})
    # cited_by table has rows like [{ "citations": { "all": 1335 }, "hindex": { "all": 10 }, "i10index": { "all": 11 } }]
    for table_entry in cited_by_section.get("table", []):
        if "citations" in table_entry:
            citedby = table_entry["citations"].get("all", 0)
        if "hindex" in table_entry:
            hindex = table_entry["hindex"].get("all", 0)
        if "i10index" in table_entry:
            i10index = table_entry["i10index"].get("all", 0)

    # Extract publications with pagination
    publications = {}
    articles = data.get("articles", [])
    for article in articles:
        title = article.get("title", "")
        num_citations = 0
        cited_by_info = article.get("cited_by", {})
        if isinstance(cited_by_info, dict):
            num_citations = cited_by_info.get("total", 0)
        pub_id = article.get("result_id", scholar_id + ":" + title[:30])
        publications[pub_id] = {
            "title": title,
            "num_citations": num_citations,
        }

    # Paginate to get all publications
    next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
    page_num = 2
    while next_page_token:
        print(f"Fetching page {page_num} of publications...")
        pag_params = {
            "engine": "google_scholar_author",
            "author_id": scholar_id,
            "hl": "en",
            "api_key": api_key,
            "start": next_page_token,
            "num": "20",
        }
        pag_url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(pag_params)
        try:
            pag_req = urllib.request.Request(pag_url)
            with urllib.request.urlopen(pag_req, timeout=30) as pag_resp:
                pag_data = json.loads(pag_resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Pagination failed on page {page_num}: {e}")
            break

        pag_articles = pag_data.get("articles", [])
        if not pag_articles:
            break
        for article in pag_articles:
            title = article.get("title", "")
            num_citations = 0
            cited_by_info = article.get("cited_by", {})
            if isinstance(cited_by_info, dict):
                num_citations = cited_by_info.get("total", 0)
            pub_id = article.get("result_id", scholar_id + ":" + title[:30])
            publications[pub_id] = {
                "title": title,
                "num_citations": num_citations,
            }
        next_page_token = pag_data.get("serpapi_pagination", {}).get("next_page_token")
        page_num += 1
        time.sleep(1)  # Be nice to the API

    return {
        "citedby": citedby,
        "hindex": hindex,
        "i10index": i10index,
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
