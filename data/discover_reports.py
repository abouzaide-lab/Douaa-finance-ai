import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


COSOB_URL = "https://cosob.dz/emetteurs/informations-financieres/"

DATA_DIR = Path(__file__).parent
OUTPUT_FILE = DATA_DIR / "discovered_reports.json"


def discover_reports():
    response = requests.get(
        COSOB_URL,
        timeout=30,
        headers={
            "User-Agent": "NouraFinanceAI/1.0"
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    reports = []
    seen_urls = set()

    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())
        url = urljoin(COSOB_URL, link["href"])

        if "cosob.dz" not in url.lower():
            continue

        if not any(
            word in url.lower() or word in title.lower()
            for word in (
                "rapport",
                "financ",
                "said al",
                "saidal",
                "biopharm",
                "2025",
                "2026",
            )
        ):
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        reports.append({
            "title": title or "رابط دون عنوان",
            "url": url,
            "discovered_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "source": "COSOB",
            "verification_status": "needs_review",
        })

    result = {
        "source": COSOB_URL,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reports_found": len(reports),
        "reports": reports,
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return result


if __name__ == "__main__":
    try:
        result = discover_reports()
        print(f"عدد الروابط المكتشفة: {result['reports_found']}")

        for report in result["reports"]:
            print(f"- {report['title']}: {report['url']}")

    except Exception as error:
        print(f"تعذر اكتشاف التقارير: {error}")
