import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


COSOB_URL = (
    "https://cosob.dz/emetteurs/informations-financieres/"
)

DATA_DIR = Path(__file__).parent
OUTPUT_FILE = DATA_DIR / "discovered_reports.json"


def classify_link(title, url):
    text = f"{title} {url}".lower()

    companies = {
        "saidal": "SAIDAL",
        "biopharm": "BIOPHARM",
        "aom-invest": "AOM Invest",
        "aurassi": "EGH El Aurassi",
        "alliance-assurances": "Alliance Assurances",
        "moustachir": "Moustachir",
        "cpa": "CPA",
        "bdl": "BDL",
    }

    company = None

    for keyword, name in companies.items():
        if keyword in text:
            company = name
            break

    year_match = re.search(r"20(?:0\d|1\d|2\d)", text)
    year = int(year_match.group()) if year_match else None

    is_pdf = url.lower().split("?")[0].endswith(".pdf")

    financial_terms = (
        "rapport annuel",
        "etats financiers",
        "états financiers",
        "informations financieres",
        "informations financières",
        "bilan",
        "tcr",
        "resultats financiers",
        "résultats financiers",
    )

    is_financial = any(
        term in text for term in financial_terms
    )

    if is_pdf and is_financial:
        category = "financial_document"
    elif company and is_financial:
        category = "company_financial_page"
    else:
        category = "other"

    return {
        "company": company,
        "year": year,
        "category": category,
    }


def discover_reports():
    response = requests.get(
        COSOB_URL,
        timeout=30,
        headers={"User-Agent": "NouraFinanceAI/1.0"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    reports = []
    seen_urls = set()

    for link in soup.find_all("a", href=True):
        title = " ".join(
            link.get_text(" ", strip=True).split()
        )
        url = urljoin(COSOB_URL, link["href"])

        if "cosob.dz" not in url.lower():
            continue

        details = classify_link(title, url)

        if details["category"] == "other":
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        reports.append({
            "title": title or "رابط دون عنوان",
            "url": url,
            **details,
            "discovered_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "source": "COSOB",
            "verification_status": "needs_review",
        })

    result = {
        "source": COSOB_URL,
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "reports_found": len(reports),
        "reports": reports,
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    financial_documents = sum(
        1 for report in reports
        if report["category"] == "financial_document"
    )

    company_pages = sum(
        1 for report in reports
        if report["category"] == "company_financial_page"
    )

    print(f"إجمالي الروابط المالية المحتملة: {len(reports)}")
    print(f"ملفات PDF المالية المحتملة: {financial_documents}")
    print(f"صفحات الشركات المالية: {company_pages}")

    for report in reports:
        print(
            f"- {report['company'] or 'شركة غير محددة'} | "
            f"{report['year'] or 'سنة غير محددة'} | "
            f"{report['category']} | {report['url']}"
        )

    return result


if __name__ == "__main__":
    try:
        discover_reports()
    except Exception as error:
        print(f"تعذر اكتشاف التقارير: {error}")
        raise
