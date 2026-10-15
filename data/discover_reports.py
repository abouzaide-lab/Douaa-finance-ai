import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


COSOB_URL = (
    "https://cosob.dz/emetteurs/informations-financieres/"
)

DATA_DIR = Path(__file__).parent
OUTPUT_FILE = DATA_DIR / "discovered_reports.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 NouraFinanceAI/1.0"
}

COMPANIES = {
    "saidal": "SAIDAL",
    "biopharm": "BIOPHARM",
    "aom invest": "AOM Invest",
    "aom-invest": "AOM Invest",
    "aurassi": "EGH El Aurassi",
    "alliance assurances": "Alliance Assurances",
    "alliance-assurances": "Alliance Assurances",
    "moustachir": "Moustachir",
    "cpa": "CPA",
    "bdl": "BDL",
    "nca rouiba": "NCA Rouiba",
}

FINANCIAL_TERMS = (
    "rapport annuel",
    "rapport financier",
    "etats financiers",
    "états financiers",
    "informations financieres",
    "informations financières",
    "bilan",
    "tcr",
    "financial statements",
)

# لا نستخدم سنة مجلد الرفع مثل /2024/05/
# لأنها قد لا تكون سنة التقرير المالي.
YEAR_PATTERN = re.compile(
    r"(?<!\d)(20(?:0\d|1\d|2\d))(?!\d)"
)


def identify_company(text):
    normalized = text.lower()

    for keyword, company in COMPANIES.items():
        if keyword in normalized:
            return company

    return None


def extract_report_year(text):
    """
    نستخرج السنة من اسم التقرير أو عنوانه.
    لا نستخرجها من مجلدات الرابط.
    """
    normalized = text.lower()

    matches = YEAR_PATTERN.findall(normalized)

    if not matches:
        return None

    # نعطي الأولوية لسنة قريبة من كلمات التقرير المالي.
    for match in re.finditer(
        r"(rapport|financier|financiers|bilan|exercice|"
        r"etats financiers|états financiers)",
        normalized,
    ):
        start = max(0, match.start() - 70)
        end = min(len(normalized), match.end() + 100)

        nearby_years = YEAR_PATTERN.findall(
            normalized[start:end]
        )

        if nearby_years:
            return int(nearby_years[-1])

    return int(matches[-1])


def classify_link(title, url):
    path = urlparse(url).path.lower()
    text = f"{title} {path}".lower()

    company = identify_company(text)

    is_pdf = path.endswith(".pdf")

    is_financial = any(
        term in text for term in FINANCIAL_TERMS
    )

    if is_pdf and is_financial:
        category = "financial_document"
    elif company and (
        "informations-financieres" in path
        or "informations-financiere" in path
        or "rapport-annuel" in path
    ):
        category = "company_financial_page"
    elif company and is_financial:
        category = "company_financial_page"
    else:
        category = "other"

    year = extract_report_year(text)

    return {
        "company": company,
        "year": year,
        "category": category,
    }


def fetch_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def discover_reports():
    soup = fetch_page(COSOB_URL)

    # نبدأ بصفحة COSOB الرئيسية للمعلومات المالية.
    pages_to_visit = {COSOB_URL}
    reports = {}
    visited_pages = set()

    while pages_to_visit:
        page_url = pages_to_visit.pop()

        if page_url in visited_pages:
            continue

        visited_pages.add(page_url)

        try:
            page = (
                soup
                if page_url == COSOB_URL
                else fetch_page(page_url)
            )
        except requests.RequestException as error:
            print(f"تعذر فتح الصفحة {page_url}: {error}")
            continue

        for link in page.find_all("a", href=True):
            title = " ".join(
                link.get_text(" ", strip=True).split()
            )

            url = urljoin(page_url, link["href"])
            parsed = urlparse(url)

            if parsed.netloc.lower() not in (
                "cosob.dz",
                "www.cosob.dz",
            ):
                continue

            if parsed.scheme not in ("http", "https"):
                continue

            # نتجنب تكرار الصفحة نفسها مع اختلاف #tabs.
            clean_url = (
                parsed.scheme
                + "://"
                + parsed.netloc
                + parsed.path
                + ("?" + parsed.query if parsed.query else "")
            )

            details = classify_link(title, clean_url)

            if details["category"] == "company_financial_page":
                if clean_url not in visited_pages:
                    pages_to_visit.add(clean_url)

            if details["category"] == "other":
                continue

            if clean_url in reports:
                continue

            reports[clean_url] = {
                "title": title or "رابط دون عنوان",
                "url": clean_url,
                **details,
                "discovered_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "source": "COSOB",
                "verification_status": "needs_review",
            }

    result = {
        "source": COSOB_URL,
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "reports_found": len(reports),
        "reports": list(reports.values()),
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    documents = [
        item for item in reports.values()
        if item["category"] == "financial_document"
    ]

    company_pages = [
        item for item in reports.values()
        if item["category"] == "company_financial_page"
    ]

    print(f"إجمالي النتائج المحتملة: {len(reports)}")
    print(f"ملفات PDF المالية المحتملة: {len(documents)}")
    print(f"صفحات الشركات المالية: {len(company_pages)}")

    for report in reports.values():
        print(
            f"- {report['company'] or 'شركة غير محددة'} | "
            f"{report['year'] or 'السنة غير محددة'} | "
            f"{report['category']} | {report['url']}"
        )

    return result


if __name__ == "__main__":
    discover_reports()
