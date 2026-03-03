import json
import os
import sys
import time

SCHOLAR_ID = os.environ.get("SCHOLAR_ID", "Zv_rC0AAAAAJ")


def get_stats_scholarly(scholar_id):
    """Fetch Google Scholar stats via scholarly library."""
    from scholarly import scholarly

    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=["basics", "indices", "publications"])

    citedby = author.get("citedby", 0)
    hindex = author.get("hindex", 0)
    i10index = author.get("i10index", 0)

    publications = {}
    for pub in author.get("publications", []):
        title = pub.get("bib", {}).get("title", "")
        num_citations = pub.get("num_citations", 0)
        pub_id = pub.get("author_pub_id", title)
        publications[pub_id] = {
            "title": title,
            "num_citations": num_citations,
        }

    return {
        "citedby": citedby,
        "hindex": hindex,
        "i10index": i10index,
        "publications": publications,
    }


def main():
    print(f"Fetching Google Scholar stats for {SCHOLAR_ID}...")

    data = None
    for attempt in range(3):
        try:
            data = get_stats_scholarly(SCHOLAR_ID)
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
