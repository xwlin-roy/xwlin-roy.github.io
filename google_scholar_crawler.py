import json
import os
import sys
import time
import requests

SCHOLAR_ID = os.environ.get("SCHOLAR_ID", "Zv_rC0AAAAAJ")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")


def get_stats_serpapi(scholar_id, api_key):
    """Fetch Google Scholar stats via SerpAPI (reliable, no anti-bot issues)."""
    # Get author profile
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar_author",
        "author_id": scholar_id,
        "api_key": api_key,
        "num": 100,
    }

    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Extract citation stats from the table
    cited_by = data.get("cited_by", {})
    table = cited_by.get("table", [])
    
    citedby = 0
    hindex = 0
    i10index = 0
    for row in table:
        if "citations" in row:
            citedby = row["citations"].get("all", 0)
        elif "h_index" in row:
            hindex = row["h_index"].get("all", 0)
        elif "i10_index" in row:
            i10index = row["i10_index"].get("all", 0)

    # Extract per-publication citations
    publications = {}
    for article in data.get("articles", []):
        title = article.get("title", "")
        num_citations = article.get("cited_by", {}).get("value", 0)
        link = article.get("citation_id", title)
        publications[link] = {
            "title": title,
            "num_citations": num_citations,
        }

    return {
        "citedby": citedby,
        "hindex": hindex,
        "i10index": i10index,
        "publications": publications,
    }


def get_stats_direct(scholar_id):
    """Fallback: scrape Google Scholar directly (may fail on GitHub Actions)."""
    from bs4 import BeautifulSoup
    import re

    url = f"https://scholar.google.com/citations?user={scholar_id}&hl=en"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            table = soup.find("table", id="gsc_rsb_st")
            if not table:
                print(f"Attempt {attempt + 1}: No stats table found, retrying...")
                time.sleep(5 * (attempt + 1))
                continue

            rows = table.find_all("tr")
            stats = {}
            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 3:
                    label = cells[0].get_text(strip=True).lower().replace("-", "")
                    stats[label] = int(cells[1].get_text(strip=True))

            citedby = stats.get("citations", 0)
            if citedby == 0:
                print(f"Attempt {attempt + 1}: Got 0 citations, retrying...")
                time.sleep(5 * (attempt + 1))
                continue

            hindex = stats.get("hindex", 0)
            i10index = stats.get("i10index", 0)

            publications = {}
            pub_rows = soup.select("tr.gsc_a_tr")
            for pub_row in pub_rows:
                title_el = pub_row.select_one("a.gsc_a_at")
                cite_el = pub_row.select_one("a.gsc_a_ac")
                if title_el and cite_el:
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    match = re.search(r"citation_for_view=([^&]+)", href)
                    paper_id = match.group(1) if match else title
                    cite_text = cite_el.get_text(strip=True)
                    num_citations = int(cite_text) if cite_text.isdigit() else 0
                    publications[paper_id] = {
                        "title": title,
                        "num_citations": num_citations,
                    }

            return {
                "citedby": citedby,
                "hindex": hindex,
                "i10index": i10index,
                "publications": publications,
            }

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(5 * (attempt + 1))

    return None


def main():
    print(f"Fetching Google Scholar stats for {SCHOLAR_ID}...")

    data = None

    # Try SerpAPI first (most reliable)
    if SERPAPI_KEY:
        print("Using SerpAPI...")
        try:
            data = get_stats_serpapi(SCHOLAR_ID, SERPAPI_KEY)
        except Exception as e:
            print(f"SerpAPI failed: {e}")

    # Fallback to direct scraping
    if not data or data.get("citedby", 0) == 0:
        print("Using direct scraping...")
        data = get_stats_direct(SCHOLAR_ID)

    if not data or data.get("citedby", 0) == 0:
        print("ERROR: Could not fetch valid citation data. Aborting to preserve existing data.")
        sys.exit(1)

    print(f"Total citations: {data['citedby']}, h-index: {data['hindex']}")

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
