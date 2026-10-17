import json
import re
from pathlib import Path
import pandas as pd
import streamlit as st
import fitz

# --------------------------------------------------
# استخراج المؤشرات المالية من النص العربي والفرنسي
# --------------------------------------------------

FINANCIAL_INDICATORS = {
    "revenue": {
        "label": "رقم الأعمال",
        "patterns": [
            r"chiffre\s+d['’]affaires",
            r"revenus?\s+d['’]activit[eé]",
            r"رقم\s+الأعمال",
            r"إيرادات"
        ]
    },
    "operating_result": {
        "label": "النتيجة التشغيلية",
        "patterns": [
            r"r[eé]sultat\s+op[eé]rationnel",
            r"r[eé]sultat\s+d['’]exploitation",
            r"النتيجة\s+التشغيلية",
            r"نتيجة\s+الاستغلال"
        ]
    },
    "net_profit": {
        "label": "صافي الربح",
        "patterns": [
            r"r[eé]sultat\s+net",
            r"b[eé]n[eé]fice\s+net",
            r"صافي\s+الربح",
            r"النتيجة\s+الصافية"
        ]
    },
    "current_assets": {
        "label": "الأصول المتداولة",
        "patterns": [
            r"actif\s+circulant",
            r"actifs?\s+courants?",
            r"الأصول\s+المتداولة"
        ]
    },
    "current_liabilities": {
        "label": "الخصوم المتداولة",
        "patterns": [
            r"passif\s+circulant",
            r"passifs?\s+courants?",
            r"الخصوم\s+المتداولة"
        ]
    },
    "total_assets": {
        "label": "إجمالي الأصول",
        "patterns": [
            r"total\s+(?:de\s+)?l['’]actif",
            r"total\s+actif",
            r"إجمالي\s+الأصول",
            r"مجموع\s+الأصول"
        ]
    },
    "equity": {
        "label": "حقوق الملكية",
        "patterns": [
            r"capitaux\s+propres",
            r"حقوق\s+الملكية",
            r"الأموال\s+الخاصة"
        ]
    }
}


def parse_financial_number(text):
    """
    يحاول تحويل رقم مكتوب بالصيغة الفرنسية أو الإنجليزية
    إلى قيمة عددية. يعيد None إذا لم يتمكن من تفسيره.
    """
    if not text:
        return None

    value = text.strip()
    value = value.replace("\u00a0", "")
    value = value.replace("\u202f", "")
    value = value.replace(" ", "")
    value = value.replace("’", "'")

    # إزالة رموز العملات والفواصل النصية
    value = re.sub(r"(?i)(DZD|DA|EUR|USD|دج)", "", value)
    value = value.strip(":")

    if not re.fullmatch(r"[+-]?\d[\d.,]*", value):
        return None

    # إذا اجتمعت النقطة والفاصلة، نعتبر آخرهما فاصلًا عشريًا
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "")
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")

    elif "," in value:
        parts = value.split(",")
        if len(parts[-1]) in (1, 2):
            value = "".join(parts[:-1]) + "." + parts[-1]
        else:
            value = "".join(parts)

    elif "." in value:
        parts = value.split(".")
        if len(parts[-1]) not in (1, 2):
            value = "".join(parts)

    try:
        return float(value)
    except ValueError:
        return None


def extract_financial_indicators(text):
    """
    استخراج أولي للمؤشرات المالية بالعربية والفرنسية.
    يستبعد السنوات والنسب الواضحة، ويحتفظ بالنص الأصلي للمراجعة.
    """
    results = []

    if not text:
        return results

    lines = text.splitlines()

    ratio_terms = [
        "valeur ajoutée / chiffre d'affaires",
        "excédent brut d'exploitation/ chiffre d'affaires",
        "excédent brut d'exploitation / chiffre d'affaires",
        "résultat opérationnel / chiffre d'affaires",
        "charges du personnel/chiffre d'affaires",
        "charges du personnel / chiffre d'affaires",
        "marge",
        "ratio",
        "النسبة",
        "هامش الربح",
    ]

    for line_number, line in enumerate(lines):
        normalized_line = re.sub(r"\s+", " ", line).strip()

        if not normalized_line:
            continue

        lower_line = normalized_line.lower()

        # تجاهل الأسطر التي تصف نسبًا مالية
        if any(term in lower_line for term in ratio_terms):
            continue

        for key, indicator in FINANCIAL_INDICATORS.items():
            for pattern in indicator["patterns"]:
                match = re.search(
                    pattern,
                    normalized_line,
                    flags=re.IGNORECASE
                )

                if not match:
                    continue

                remainder = normalized_line[match.end():]

                # استخراج الأرقام الواقعة بعد اسم المؤشر
                number_matches = re.findall(
                    r"(?<![\w/])[-+]?\d(?:[\d\u00a0\u202f ]*\d)?(?:[.,]\d+)*",
                    remainder
                )

                value = None

                for candidate in number_matches:
                    candidate = candidate.strip()
                    parsed = parse_financial_number(candidate)

                    if parsed is None:
                        continue

                    # لا نعتمد السنة كقيمة مالية
                    if parsed.is_integer() and 2000 <= parsed <= 2100:
                        continue

                    value = parsed
                    break

                # نفحص السطر التالي فقط إذا كان قصيرًا ويبدو أنه يحتوي قيمة
                if value is None and line_number + 1 < len(lines):
                    next_line = re.sub(
                        r"\s+", " ", lines[line_number + 1]
                    ).strip()

                    next_lower = next_line.lower()

                    if (
                        next_line
                        and len(next_line) <= 100
                        and not any(term in next_lower for term in ratio_terms)
                    ):
                        next_numbers = re.findall(
                            r"(?<![\w/])[-+]?\d(?:[\d\u00a0\u202f ]*\d)?(?:[.,]\d+)*",
                            next_line
                        )

                        for candidate in next_numbers:
                            parsed = parse_financial_number(candidate.strip())

                            if parsed is None:
                                continue

                            if parsed.is_integer() and 2000 <= parsed <= 2100:
                                continue

                            value = parsed
                            break

                if value is not None:
                    results.append({
                        "المؤشر": indicator["label"],
                        "اسم المؤشر البرمجي": key,
                        "القيمة المستخرجة": value,
                        "السطر": line_number + 1,
                        "النص الأصلي": normalized_line,
                        "حالة المراجعة": "يحتاج إلى التحقق"
                    })

                # نكتفي بأول تطابق لهذا المؤشر في هذا السطر
                break

    return results
st.set_page_config(page_title="دعاء المالية | Douaa Finance AI", page_icon="📊", layout="wide")
st.title("📊 دعاء المالية")
st.caption("مساعد تجريبي لتحليل الشركات والأسهم والسندات")

DATA_DIR = Path(__file__).parent / "data"

def load_companies():
    loaded = {}

    if not DATA_DIR.exists():
        return loaded

    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                obj = json.load(f)

            # قبول ملفات الشركات التي تحتوي على سجلات مالية
            if (
                isinstance(obj, dict)
                and isinstance(obj.get("records"), list)
                and obj.get("company")
                and obj.get("company_name")
                and obj.get("fiscal_year")
            ):
                loaded[path.stem] = obj

        except (json.JSONDecodeError, OSError) as exc:
            st.warning(f"تعذر تحميل {path.name}: {exc}")

    return loaded

companies = load_companies()
data = companies.get("saidal_2025", {})

def money(value):
    try:
        return "غير متاح" if value is None else f"{float(value):,.2f} دج"
    except (TypeError, ValueError):
        return "غير متاح"

def percent(value):
    try:
        return "غير متاح" if value is None else f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "غير متاح"

def ratio(a, b):
    try:
        return None if a is None or b is None or float(b) == 0 else float(a) / float(b)
    except (TypeError, ValueError, ZeroDivisionError):
        return None

def records_to_values(obj):
    values = {}
    records = obj.get("records", []) if isinstance(obj, dict) else []
    if not isinstance(records, list):
        return values
    for item in records:
        if isinstance(item, dict) and item.get("metric") and item.get("value") is not None:
            try:
                values[item["metric"]] = float(item["value"])
            except (TypeError, ValueError):
                pass
    return values
# أسماء المؤشرات المالية باللغة العربية
METRIC_LABELS = {
    "revenue": "رقم الأعمال",
    "ebitda_ebe": "الفائض الإجمالي للاستغلال (EBE)",
    "operating_result": "النتيجة التشغيلية",
    "net_profit": "صافي الربح",
    "equity": "حقوق الملكية",
    "total_assets": "إجمالي الأصول",
    "current_assets": "الأصول المتداولة",
    "current_liabilities": "الخصوم المتداولة",
    "inventory": "المخزون",
    "total_debt": "إجمالي الديون",
    "self_financing_capacity": "القدرة على التمويل الذاتي",
    "capital_expenditure": "نفقات الاستثمار",
    "roe": "العائد على حقوق الملكية (ROE)"
}

def display_name(key, obj):
    if not isinstance(obj, dict):
        return key.replace("_", " ").title()

    names = {
        "saidal": "صيدال",
        "said al": "صيدال",
        "biopharm": "بيوفارم"
    }

    company = str(obj.get("company_name") or obj.get("company") or "").strip()

    if company:
        normalized = company.lower()
        if normalized in names:
            return names[normalized]
        return company

    key_lower = key.lower()

    if "saidal" in key_lower:
        return "صيدال"

    if "biopharm" in key_lower:
        return "بيوفارم"

    return key.replace("_", " ").title()

def fiscal_year(obj):
    if not isinstance(obj, dict):
        return "غير محددة"

    return obj.get(
        "fiscal_year",
        obj.get("report_year", "غير محددة")
    )


def show_data_verification(obj):
    if not isinstance(obj, dict):
        st.warning("تعذر التحقق من بنية بيانات الشركة.")
        return

    status = obj.get("verification_status", "unknown")
    source = obj.get("source", "المصدر غير محدد")
    source_url = obj.get("source_url")
    year = fiscal_year(obj)

    st.subheader("🔎 مصدر البيانات والتحقق منها")
    st.write(f"السنة المالية: {year}")
    st.write(f"المصدر: {source}")

    if status == "verified":
        st.success("تم التحقق من البيانات وفق المصدر المسجل.")
    elif status == "pending_primary_source_review":
        st.warning(
            "الأرقام مسجلة، لكن مطابقتها مع التقرير المالي الأصلي "
            "لم تكتمل بعد."
        )
    else:
        st.info("حالة التحقق من البيانات تحتاج إلى مراجعة.")

    if source_url:
        st.markdown(f"[فتح التقرير الأصلي]({source_url})")

    records = obj.get("records", [])

    pending = [
        record.get("label", record.get("metric", "مؤشر غير مسمى"))
        for record in records
        if record.get("verification_status") != "verified"
    ]

    if pending:
        st.write("المؤشرات التي تحتاج إلى مراجعة:")
        for label in pending:
            st.write(f"• {label}")
def explain_margin(value, name):
    if value is None:
        return f"لا يمكن تفسير {name} بسبب نقص البيانات."
    if value < 0:
        return f"{name} سلبي ({value:.2f}%)، وهذا يشير إلى نتيجة سالبة وفق هذا المؤشر."
    if value == 0:
        return f"{name} يساوي صفرًا."
    if value < 5:
        return f"{name} يبلغ {value:.2f}%. يُعد هامشًا منخفضًا نسبيًا كإشارة أولية؛ قارنه بالسنوات السابقة وشركات القطاع."
    return f"{name} يبلغ {value:.2f}%. قيّمه بمقارنته بتاريخ الشركة وشركات القطاع."

def explain_liquidity(value, name):
    if value is None:
        return f"لا يمكن حساب {name} بسبب نقص البيانات."
    if value < 1:
        return f"{name} تبلغ {value:.2f} مرة. الأصول المستخدمة أقل من الالتزامات قصيرة الأجل؛ افحص السيولة والتدفقات النقدية."
    if value <= 1.5:
        return f"{name} تبلغ {value:.2f} مرة. ينبغي تقييم طبيعة الأصول ومواعيد استحقاق الالتزامات."
    return f"{name} تبلغ {value:.2f} مرة. التغطية أعلى وفق هذا المؤشر، لكن ذلك لا يضمن توفر النقد أو جودة الأصول."

def explain_equity_share(value):
    if value is None:
        return "لا يمكن حساب نسبة حقوق الملكية إلى الأصول."
    if value < 0:
        return f"النسبة تبلغ {value:.2f}%. تحقق من البيانات، فقد تشير إلى حقوق ملكية سالبة."
    if value < 30:
        return f"حقوق الملكية تمثل {value:.2f}% من الأصول. افحص مصادر التمويل والديون وتكلفتها."
    return f"حقوق الملكية تمثل {value:.2f}% من الأصول. قيّمها مع حجم الديون وتكلفة التمويل والشركات المماثلة."

def explain_growth(old, new, name):
    if old is None or new is None:
        return f"لا تتوفر بيانات كافية لتفسير تغير {name}."
    if old == 0:
        return f"لم يتغير {name} عن الصفر." if new == 0 else f"انتقل {name} من صفر؛ لا يمكن حساب نسبة نمو اعتيادية."
    change = (new - old) / abs(old) * 100
    if change > 0:
        return f"{name} ارتفع بنسبة {change:.2f}% مقارنة بالسنة السابقة."
    if change < 0:
        return f"{name} انخفض بنسبة {abs(change):.2f}% مقارنة بالسنة السابقة."
    return f"{name} لم يتغير مقارنة بالسنة السابقة."

# التبويبات
tab1, tab2, tab3 = st.tabs(["📈 تحليل صيدال", "🏢 تحليل شركة", "🧾 حاسبة السندات"])

with tab1:
    st.header("تحليل شركة صيدال")
    if not data or not isinstance(data.get("records"), list):
        st.error("تعذر قراءة بيانات صيدال. تحقق من data/saidal_2025.json وصحة محتواه.")
    else:
        vals = records_to_values(data)
        comp = data.get("comparative_data", {})
        old = comp.get("2024", {}) if isinstance(comp, dict) else {}
        if not isinstance(old, dict): old = {}
        revenue, ebe = vals.get("revenue"), vals.get("ebitda_ebe")
        operating, profit = vals.get("operating_result"), vals.get("net_profit")
        st.caption(f"السنة المالية: {data.get('fiscal_year', 'غير محددة')} | العملة: الدينار الجزائري")
        st.subheader("المؤشرات المالية")
        c1, c2, c3 = st.columns(3)
        c1.metric("الإيرادات", money(revenue)); c2.metric("النتيجة التشغيلية", money(operating)); c3.metric("صافي الربح", money(profit))
        ebe_m, op_m, profit_m = ratio(ebe, revenue), ratio(operating, revenue), ratio(profit, revenue)
        st.subheader("هوامش الربحية")
        c1, c2, c3 = st.columns(3)
        c1.metric("هامش EBE", percent(ebe_m * 100 if ebe_m is not None else None))
        c2.metric("هامش التشغيل", percent(op_m * 100 if op_m is not None else None))
        c3.metric("هامش صافي الربح", percent(profit_m * 100 if profit_m is not None else None))
        ca, cl, inv = vals.get("current_assets"), vals.get("current_liabilities"), vals.get("inventory")
        ta, eq = vals.get("total_assets"), vals.get("equity")
        quick_assets = ca - inv if ca is not None and inv is not None else None
        current, quick, eq_share = ratio(ca, cl), ratio(quick_assets, cl), ratio(eq, ta)
        st.subheader("السيولة والملاءة المالية")
        c1, c2, c3 = st.columns(3)
        c1.metric("السيولة الجارية", f"{current:.2f} مرة" if current is not None else "غير متاح")
        c2.metric("السيولة السريعة", f"{quick:.2f} مرة" if quick is not None else "غير متاح")
        c3.metric("حقوق الملكية / الأصول", percent(eq_share * 100 if eq_share is not None else None))
        st.subheader("🧠 تفسير نورة المالي")
        with st.expander("تفسير الربحية", expanded=True):
            st.write(explain_margin(ebe_m * 100 if ebe_m is not None else None, "هامش EBE"))
            st.write(explain_margin(op_m * 100 if op_m is not None else None, "هامش النتيجة التشغيلية"))
            st.write(explain_margin(profit_m * 100 if profit_m is not None else None, "هامش صافي الربح"))
        with st.expander("تفسير السيولة والملاءة"):
            st.write(explain_liquidity(current, "السيولة الجارية")); st.write(explain_liquidity(quick, "السيولة السريعة"))
            st.write(explain_equity_share(eq_share * 100 if eq_share is not None else None))
        st.subheader("مقارنة 2024 و2025")
        labels = {"revenue":"الإيرادات", "ebitda_ebe":"فائض إجمالي الاستغلال EBE", "operating_result":"النتيجة التشغيلية", "net_profit":"صافي الربح"}
        rows = []
        for key, label in labels.items():
            now, before = vals.get(key), old.get(key)
            growth = (now-before)/abs(before)*100 if now is not None and before is not None and before != 0 else None
            rows.append({"المؤشر":label, "2024 (دج)":before, "2025 (دج)":now, "التغير (%)":round(growth, 2) if growth is not None else None})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.subheader("📊 ماذا تغير بين السنتين؟")
        for key, label in labels.items(): st.write("• " + explain_growth(old.get(key), vals.get(key), label))
        chart_keys = [key for key in labels if old.get(key) is not None and vals.get(key) is not None]
        if chart_keys:
            selected = st.selectbox("اختر مؤشرًا للرسم البياني", chart_keys, format_func=lambda k: labels[k], key="saidal_chart_metric")
            st.bar_chart(pd.DataFrame({"السنة":["2024","2025"], "القيمة بالدينار":[old[selected], vals[selected]]}).set_index("السنة"))
        else:
            st.info("لا تتوفر بيانات كافية للمقارنة. تحقق من comparative_data في ملف JSON.")
        st.subheader("🧭 التقييم المالي العام")
        st.caption("تقييم أولي مبني على البيانات المتاحة، وليس توصية بشراء السهم أو بيعه.")
        if revenue is None or revenue <= 0: st.info("لا يمكن تقييم هوامش الربحية دون إيرادات موجبة.")
        elif profit is None: st.info("بيانات صافي الربح غير متاحة.")
        elif profit > 0: st.success("صافي الربح موجب. تحقق من استدامة الأرباح ومقارنتها بالسنوات السابقة.")
        elif profit < 0: st.warning("الشركة سجلت خسارة صافية في البيانات المدخلة.")
        else: st.warning("صافي الربح يساوي صفرًا.")
        if current is None: st.info("لا تتوفر بيانات كافية لحساب السيولة الجارية.")
        elif current < 1: st.warning(f"السيولة الجارية {current:.2f} مرة؛ افحص التدفقات النقدية ومواعيد الاستحقاق.")
        else: st.success(f"السيولة الجارية {current:.2f} مرة. التغطية الحسابية لا تضمن توفر النقد.")
        if eq_share is None: st.info("لا تتوفر بيانات كافية لحساب حقوق الملكية إلى الأصول.")
        else: st.write(f"نسبة حقوق الملكية إلى الأصول: {eq_share*100:.2f}%.")
        old_profit = old.get("net_profit")
        if profit is None or old_profit is None: st.info("لا يمكن مقارنة صافي الربح دون بيانات السنتين.")
        elif old_profit == 0: st.info("صافي ربح السنة السابقة يساوي صفرًا؛ لا تصلح نسبة النمو الاعتيادية.")
        else:
            change = (profit-old_profit)/abs(old_profit)*100
            st.metric("تغير صافي الربح", f"{change:+.2f}%")
            if change > 0: st.success("ارتفع صافي الربح مقارنة بالسنة السابقة.")
            elif change < 0: st.warning("انخفض صافي الربح مقارنة بالسنة السابقة.")
            else: st.info("صافي الربح لم يتغير مقارنة بالسنة السابقة.")
        required = ["revenue", "net_profit", "current_assets", "current_liabilities", "total_assets", "equity"]
        missing = [key for key in required if vals.get(key) is None]
        if missing: st.warning("التقييم غير مكتمل. المؤشرات المفقودة: " + ", ".join(missing))
        else: st.info("المؤشرات الأساسية موجودة؛ راجع الأرقام في التقرير الأصلي.")
        with st.expander("تفاصيل جودة البيانات"):
            st.write("الشركة:", data.get("company", "غير محددة")); st.write("عدد المؤشرات:", len(vals))
            st.write("تحقق من القيم ومصدرها في التقرير المالي الأصلي.")

with tab2:
    st.header("تحليل شركة يدويًا")
    st.info("أدخل الأرقام من تقرير مالي موثوق. لا يجلب هذا النموذج التقارير تلقائيًا.")
    with st.form("company_analysis"):
        manual_name = st.text_input("اسم الشركة", key="manual_company_name")
        source = st.text_input("رابط التقرير أو مصدر البيانات", key="manual_company_source")
        year = st.number_input("السنة المالية", min_value=2000, max_value=2100, value=2025, key="manual_company_year")
        st.subheader("البيانات المالية بالدينار الجزائري")
        rev = st.number_input("الإيرادات", min_value=0.0, value=0.0, key="manual_revenue")
        prof = st.number_input("صافي الربح أو الخسارة", value=0.0, key="manual_profit")
        debt = st.number_input("إجمالي الديون", min_value=0.0, value=0.0, key="manual_debt")
        equity = st.number_input("حقوق الملكية", value=0.0, key="manual_equity")
        assets = st.number_input("إجمالي الأصول", min_value=0.0, value=0.0, key="manual_assets")
        submitted = st.form_submit_button("تحليل البيانات")
    if submitted:
        if not manual_name.strip() or not source.strip(): st.warning("أدخل اسم الشركة ومصدر البيانات.")
        else:
            st.subheader(f"نتائج تحليل {manual_name}"); st.write("السنة المالية:", int(year)); st.write("المصدر:", source)
            m = ratio(prof, rev); de = ratio(debt, equity); es = ratio(equity, assets)
            c1,c2,c3 = st.columns(3); c1.metric("الإيرادات", money(rev)); c2.metric("صافي الربح", money(prof)); c3.metric("هامش صافي الربح", percent(m*100 if m is not None else None))
            c1,c2 = st.columns(2); c1.metric("الديون / حقوق الملكية", f"{de:.2f} مرة" if de is not None else "غير متاح"); c2.metric("حقوق الملكية / الأصول", percent(es*100 if es is not None else None))
            if prof < 0: st.error("صافي الربح المدخل سالب، أي توجد خسارة.")
            elif prof > 0: st.success("صافي الربح المدخل موجب.")
            else: st.info("صافي الربح المدخل يساوي صفرًا.")
            st.subheader("🧭 التقييم المالي الأولي")
            if rev <= 0: st.warning("لا يمكن تقييم هامش الربح لأن الإيرادات تساوي صفرًا.")
            else:
                mp = prof/rev*100
                if mp >= 15: st.success(f"هامش الربح {mp:.2f}%: مرتفع وفق هذا المؤشر وحده.")
                elif mp > 5: st.info(f"هامش الربح {mp:.2f}%: متوسط وفق هذا المؤشر وحده.")
                elif mp >= 0: st.warning(f"هامش الربح {mp:.2f}%: منخفض أو محدود.")
                else: st.error(f"هامش الربح {mp:.2f}%: توجد خسارة وفق البيانات المدخلة.")
            if equity <= 0: st.warning("لا يمكن تقييم نسبة الديون إلى حقوق الملكية عندما تكون حقوق الملكية صفرًا أو سالبة.")
            elif de < 0.5: st.success(f"الديون إلى حقوق الملكية: {de:.2f} مرة؛ منخفضة نسبيًا وفق هذا المؤشر.")
            elif de <= 1: st.info(f"الديون إلى حقوق الملكية: {de:.2f} مرة؛ قارنها بمتوسط القطاع.")
            else: st.warning(f"الديون إلى حقوق الملكية: {de:.2f} مرة؛ راجع مستوى المديونية.")
            missing = []
            if rev <= 0: missing.append("الإيرادات غير متوفرة أو تساوي صفرًا")
            if assets <= 0: missing.append("إجمالي الأصول غير متوفر")
            if equity <= 0: missing.append("حقوق الملكية غير موجبة")
            if missing: st.warning("راجع: " + "؛ ".join(missing))
            else: st.success("الحقول الأساسية موجبة، لكن ذلك لا يثبت صحة الأرقام.")
            st.caption("هذا تقييم أولي وليس توصية بالشراء أو البيع؛ تختلف النسب المناسبة حسب القطاع.")

    # مقارنة الشركات: قراءة تلقائية من ملفات data/*.json
    st.divider(); st.header("⚖️ مقارنة الشركات")
    st.caption("أي ملف JSON صالح داخل مجلد data سيظهر هنا تلقائيًا.")
    manual_key = "__manual__"
    keys = list(companies.keys())
    choices = keys + [manual_key]
    def option_label(key):
        return "إدخال بيانات يدويًا" if key == manual_key else f"{display_name(key, companies[key])} — {fiscal_year(companies[key])}"
    default_a = "saidal_2025" if "saidal_2025" in keys else (keys[0] if keys else manual_key)
    default_b = next((key for key in keys if key != default_a), manual_key)
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("الشركة الأولى")
        selected_a = st.selectbox("اختر الشركة الأولى", choices, index=choices.index(default_a), format_func=option_label, key="compare_select_a")
    with col_b:
        st.subheader("الشركة الثانية")
        selected_b = st.selectbox("اختر الشركة الثانية", choices, index=choices.index(default_b), format_func=option_label, key="compare_select_b")
    if not keys: st.warning("لم يتم العثور على ملفات شركات في مجلد data. يمكنك استخدام الإدخال اليدوي.")

    def manual_company(side, prefix):
        st.markdown(f"**بيانات {side} — إدخال يدوي**")
        name = st.text_input("اسم الشركة", key=f"{prefix}_name").strip()
        revenue_value = st.number_input("الإيرادات (دج)", min_value=0.0, key=f"{prefix}_revenue")
        profit_value = st.number_input("صافي الربح أو الخسارة (دج)", key=f"{prefix}_profit")
        equity_value = st.number_input("حقوق الملكية (دج)", key=f"{prefix}_equity")
        debt_value = st.number_input("إجمالي الديون (دج) إذا كانت معروفة", min_value=0.0, key=f"{prefix}_debt")
        return {"name":name, "revenue":revenue_value, "net_profit":profit_value, "equity":equity_value, "total_debt":debt_value, "year":"يدوي", "debt_available":True}
    def loaded_company(key):
        obj = companies[key]; v = records_to_values(obj)
        return {"name":display_name(key,obj), "revenue":v.get("revenue"), "net_profit":v.get("net_profit"), "equity":v.get("equity"), "total_debt":v.get("total_debt"), "year":fiscal_year(obj), "debt_available":v.get("total_debt") is not None}
    if selected_a == manual_key: a = manual_company("الشركة الأولى", "compare_manual_a")
    else:
        a = loaded_company(selected_a); st.caption(f"الشركة الأولى: بيانات ملف {a['name']}، سنة {a['year']}.")
    if selected_b == manual_key: b = manual_company("الشركة الثانية", "compare_manual_b")
    else:
        b = loaded_company(selected_b); st.caption(f"الشركة الثانية: بيانات ملف {b['name']}، سنة {b['year']}.")
    if st.button("مقارنة الشركتين", type="primary", key="compare_companies_button"):
        if not a["name"] or not b["name"]: st.warning("أدخل اسم الشركة لكل طرف اخترت له الإدخال اليدوي.")
        elif selected_a == selected_b and selected_a != manual_key: st.warning("اختر شركتين مختلفتين للمقارنة.")
        else:
            st.subheader(f"نتائج المقارنة: {a['name']} و{b['name']}")
            st.caption(f"السنة المالية: {a['year']} مقابل {b['year']}")
            c1,c2 = st.columns(2); c1.metric(a["name"]+" — الإيرادات", money(a["revenue"])); c2.metric(b["name"]+" — الإيرادات", money(b["revenue"]))
            ma = ratio(a["net_profit"], a["revenue"])
            mb = ratio(b["net_profit"], b["revenue"])

            da = (
                ratio(a["total_debt"], a["equity"])
                if a["debt_available"] else None
            )
            db = (
                ratio(b["total_debt"], b["equity"])
                if b["debt_available"] else None
            )

            st.subheader("📊 جدول المقارنة المالية")

            comparison_rows = [
                {
                    "المؤشر المالي": "رقم الأعمال",
                    a["name"]: money(a["revenue"]),
                    b["name"]: money(b["revenue"]),
                },
                {
                    "المؤشر المالي": "صافي الربح",
                    a["name"]: money(a["net_profit"]),
                    b["name"]: money(b["net_profit"]),
                },
                {
                    "المؤشر المالي": "هامش صافي الربح",
                    a["name"]: percent(ma * 100 if ma is not None else None),
                    b["name"]: percent(mb * 100 if mb is not None else None),
                },
                {
                    "المؤشر المالي": "إجمالي الديون",
                    a["name"]: money(a["total_debt"]),
                    b["name"]: money(b["total_debt"]),
                },
                {
                    "المؤشر المالي": "حقوق الملكية",
                    a["name"]: money(a["equity"]),
                    b["name"]: money(b["equity"]),
                },
                {
                    "المؤشر المالي": "الديون إلى حقوق الملكية",
                    a["name"]: f"{da:.2f} مرة" if da is not None else "غير متوفر",
                    b["name"]: f"{db:.2f} مرة" if db is not None else "غير متوفر",
                },
            ]

            st.dataframe(
                pd.DataFrame(comparison_rows),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("🧠 تفسير المقارنة")

            if ma is None or mb is None:
                st.info(
                    "تعذرت مقارنة هامش الربح؛ تحقق من توفر الإيرادات وصافي الربح."
                )
            elif ma > mb:
                st.info(
                    f"{a['name']} لديها هامش صافي ربح أعلى وفق البيانات المتاحة."
                )
            elif mb > ma:
                st.info(
                    f"{b['name']} لديها هامش صافي ربح أعلى وفق البيانات المتاحة."
                )
            else:
                st.info("هامش صافي الربح متساوٍ بين الشركتين.")

            if da is None or db is None:
                st.info(
                    "لا يمكن مقارنة المديونية بدقة إذا لم يتوفر إجمالي الديون "
                    "وحقوق الملكية في الملف."
                )
            elif da < db:
                st.info(
                    f"{a['name']} لديها نسبة ديون إلى حقوق ملكية أقل."
                )
            elif db < da:
                st.info(
                    f"{b['name']} لديها نسبة ديون إلى حقوق ملكية أقل."
                )
            else:
                st.info("نسبة الديون إلى حقوق الملكية متساوية.")

            st.caption(
                "تعتمد النتائج على البيانات المحفوظة أو المدخلة، "
                "ولا تكفي وحدها لتقييم السهم أو اتخاذ قرار استثماري."
            )
with tab3:
    st.header("حاسبة السندات")
    face_value = st.number_input("القيمة الاسمية للسند (دج)", min_value=0.0, value=0.0, key="bond_face")
    annual_rate = st.number_input("معدل الفائدة السنوية (%)", min_value=0.0, value=0.0, key="bond_rate")
    purchase_price = st.number_input("سعر شراء السند (دج)", min_value=0.0, value=0.0, key="bond_price")
    if st.button("حساب عائد السند", key="calculate_bond"):
        if purchase_price <= 0: st.warning("أدخل سعر شراء موجبًا.")
        else:
            interest = face_value * annual_rate / 100
            yield_value = interest / purchase_price * 100
            c1,c2 = st.columns(2); c1.metric("الفائدة السنوية النظرية", money(interest)); c2.metric("العائد الجاري التقريبي", percent(yield_value))
            st.caption("العائد الجاري لا يساوي العائد حتى الاستحقاق، ولا يشمل الضرائب أو الرسوم أو مخاطر التعثر.")
# --------------------------------------------------
# استيراد التقارير المالية
# --------------------------------------------------

st.divider()
st.header("📥 استيراد التقارير المالية")
st.write(
    "ارفع تقرير الشركة بصيغة PDF لاستخراج النصوص "
    "ومراجعة البيانات قبل اعتمادها."
)

uploaded_report = st.file_uploader(
    "اختر التقرير المالي PDF",
    type=["pdf"],
    key="financial_report_uploader"
)

if uploaded_report is not None:
    st.success("تم رفع الملف بنجاح.")

    st.write("اسم الملف:", uploaded_report.name)

    report_type = st.selectbox(
        "نوع القوائم المالية",
        [
            "غير محدد بعد",
            "فردية (Individual)",
            "موحّدة (Consolidated)"
        ],
        key="report_type"
    )

    report_year = st.number_input(
        "السنة المالية",
        min_value=2000,
        max_value=2100,
        value=2025,
        step=1,
        key="report_year"
    )

    if st.button("🔍 استخراج نص التقرير", key="extract_report"):
        try:
            pdf_bytes = uploaded_report.getvalue()

            with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
                page_count = len(pdf)
                extracted_pages = []

                for page_number, page in enumerate(pdf, start=1):
                    page_text = page.get_text("text")

                    extracted_pages.append(
                        f"\n--- الصفحة {page_number} ---\n"
                        f"{page_text}"
                    )

            full_text = "\n".join(extracted_pages)

            st.session_state["report_text"] = full_text
            st.session_state["report_filename"] = uploaded_report.name

            # استخراج المؤشرات المالية
            indicators = extract_financial_indicators(full_text)
            st.session_state["financial_indicators"] = indicators
            st.session_state["financial_indicators"] = indicators

            st.success(
                f"اكتمل استخراج النصوص من {page_count} صفحة."
            )

            if full_text.strip():
                st.text_area(
                    "📄 النص المستخرج — راجعه قبل استخدامه",
                    value=full_text[:20000],
                    height=350,
                    key="extracted_text_preview"
                )

                st.caption(
                    "المعاينة تعرض أول 20,000 حرف فقط. "
                    "الأرقام المستخرجة أولية وتحتاج إلى المراجعة."
                )

                # عرض المؤشرات المالية المستخرجة
                if indicators:
                    st.subheader("📊 المؤشرات المالية المستخرجة")

                    st.info(
                        "تحقق من كل رقم في التقرير الأصلي "
                        "قبل استخدامه في التحليل المالي."
                    )

                    indicators_df = pd.DataFrame(indicators)

                    st.dataframe(
                        indicators_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning(
                        "لم يتم العثور على مؤشرات مالية مطابقة. "
                        "قد يحتاج التقرير إلى قواعد استخراج إضافية."
                    )

            else:
                st.warning(
                    "لم يُعثر على نص قابل للاستخراج. "
                    "قد يكون التقرير ممسوحًا ضوئيًا ويحتاج إلى OCR."
                )

        except Exception as exc:
            st.error(f"تعذر قراءة التقرير: {exc}")
            # --------------------------------------------------
# مراجعة المؤشرات المالية واعتمادها
# --------------------------------------------------

st.divider()
st.header("📝 مراجعة واعتماد البيانات المالية")

review_indicators = st.session_state.get(
    "financial_indicators", []
)

if review_indicators:
    st.info(
        "راجع القيم المستخرجة وصححها قبل اعتمادها. "
        "لن تُحفظ أي قيمة إلا إذا اخترت اعتمادها."
    )

    # إنشاء جدول المراجعة مرة واحدة فقط
    if "financial_review_df" not in st.session_state:
        review_df = pd.DataFrame(review_indicators)

        review_df["اعتماد القيمة"] = False

        review_df["القيمة المصححة"] = (
            review_df["القيمة المستخرجة"]
        )

        review_df["السنة المالية"] = int(
            st.session_state.get("report_year", 2025)
        )

        review_df["نطاق القوائم"] = st.session_state.get(
            "report_type",
            "غير محدد بعد"
        )

        st.session_state["financial_review_df"] = review_df

    # عرض الجدول مع الاحتفاظ بالتعديلات
    edited_df = st.data_editor(
        st.session_state["financial_review_df"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=[
            "المؤشر",
            "اسم المؤشر البرمجي",
            "السطر",
            "النص الأصلي",
            "حالة المراجعة",
            "القيمة المستخرجة"
        ],
        column_config={
            "اعتماد القيمة": st.column_config.CheckboxColumn(
                "اعتماد؟",
                help="حدد هذا الخيار إذا تحققت من صحة الرقم."
            ),
            "القيمة المصححة": st.column_config.NumberColumn(
                "القيمة المالية الصحيحة",
                help="صحح الرقم وفقًا للتقرير الأصلي.",
                format="%.2f"
            ),
            "السنة المالية": st.column_config.NumberColumn(
                "السنة المالية",
                min_value=2000,
                max_value=2100,
                step=1
            ),
            "نطاق القوائم": st.column_config.SelectboxColumn(
                "نطاق القوائم",
                options=[
                    "غير محدد بعد",
                    "فردية (Individual)",
                    "موحّدة (Consolidated)"
                ],
                required=True
            )
        },
        key="financial_review_editor"
    )

    # الاحتفاظ بالبيانات المعدلة
    st.session_state["financial_review_df"] = edited_df

    st.caption(
        "تأكد من السنة والقيمة ونطاق القوائم المالية قبل الاعتماد."
    )

    if st.button(
        "💾 اعتماد البيانات المحددة",
        key="approve_financial_data"
    ):
        approved_rows = edited_df[
            edited_df["اعتماد القيمة"] == True
        ]

        if approved_rows.empty:
            st.warning("حدد قيمة واحدة على الأقل لاعتمادها.")
        else:
            valid_rows = approved_rows[
                approved_rows["القيمة المصححة"].notna()
                & approved_rows["السنة المالية"].notna()
            ]

            if valid_rows.empty:
                st.warning(
                    "لا توجد قيم مكتملة. تحقق من الأرقام والسنوات."
                )
            else:
                approved_records = []

                for _, row in valid_rows.iterrows():
                    approved_records.append({
                        "indicator": row["اسم المؤشر البرمجي"],
                        "label": row["المؤشر"],
                        "value": float(row["القيمة المصححة"]),
                        "year": int(row["السنة المالية"]),
                        "scope": row["نطاق القوائم"],
                        "source_file": st.session_state.get(
                            "report_filename", ""
                        ),
                        "source_line": int(row["السطر"]),
                        "source_text": row["النص الأصلي"],
                        "verification_status": "user_verified",
                        "data_type": "reported"
                    })

                st.session_state["approved_financial_records"] = (
                    approved_records
                )

                st.success(
                    f"تم اعتماد {len(approved_records)} قيمة في الجلسة الحالية."
                )

                                # عرض البيانات المعتمدة في جدول مالي
                st.subheader("📊 البيانات المالية المعتمدة")

                display_rows = []

                for record in approved_records:
                    value = record["value"]

                    display_rows.append({
                        "المؤشر المالي": record["label"],
                        "القيمة بالدينار": f"{value:,.2f} دج",
                        "السنة المالية": record["year"],
                        "نطاق القوائم": record["scope"],
                        "حالة التحقق": "تم التحقق يدويًا"
                    })

                display_df = pd.DataFrame(display_rows)

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )

                # تجهيز ملف JSON قابل للتنزيل
                export_data = {
                    "company": "SAIDAL",
                    "company_name": "صيدال",
                    "fiscal_year": int(
                        st.session_state.get("report_year", 2025)
                    ),
                    "currency": "DZD",
                    "scope": st.session_state.get(
                        "report_type", "غير محدد بعد"
                    ),
                    "source_file": st.session_state.get(
                        "report_filename", ""
                    ),
                    "records": approved_records
                }

                json_bytes = json.dumps(
                    export_data,
                    ensure_ascii=False,
                    indent=2
                ).encode("utf-8")

                st.download_button(
                    label="📥 تنزيل البيانات المالية المعتمدة",
                    data=json_bytes,
                    file_name=(
                        f"saidal_{export_data['fiscal_year']}_reviewed.json"
                    ),
                    mime="application/json",
                    key="download_approved_financial_data"
                )

else:
    st.info(
        "ارفع تقريرًا ماليًا واستخرج النصوص أولًا "
        "حتى تظهر المؤشرات هنا للمراجعة."
    )
st.divider()
st.caption("دعاء المالية — أداة معلومات وتحليل تجريبية، وليست توصية استثمارية.")
