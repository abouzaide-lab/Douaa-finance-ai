
import json
from pathlib import Path

import pandas as pd
import streamlit as st


# --------------------------------------------------
# إعدادات التطبيق
# --------------------------------------------------
st.set_page_config(
    page_title="نورة المالية | Douaa Finance AI",
    page_icon="📊",
    layout="wide"
)

st.title("📊 نورة المالية")
st.caption("مساعد تجريبي لتحليل الشركات والأسهم والسندات")

DATA_FILE = Path(__file__).parent / "data" / "saidal_2025.json"


# --------------------------------------------------
# دوال الحساب والتنسيق
# --------------------------------------------------
def money(value):
    if value is None:
        return "غير متاح"
    return f"{value:,.2f} دج"


def percent(value):
    if value is None:
        return "غير متاح"
    return f"{value:.2f}%"


def ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


# --------------------------------------------------
# دوال التفسير المالي
# --------------------------------------------------
def explain_margin(value, name):
    if value is None:
        return f"لا يمكن تفسير {name} بسبب نقص البيانات."

    if value < 0:
        return (
            f"{name} سلبي ({value:.2f}%)، "
            "وهذا يشير إلى نتيجة سالبة وفق هذا المؤشر."
        )

    if value == 0:
        return f"{name} يساوي صفرًا."

    if value < 5:
        return (
            f"{name} يبلغ {value:.2f}%. "
            "يُعد ذلك هامشًا منخفضًا نسبيًا كإشارة أولية، "
            "ويجب مقارنته بالسنوات السابقة وبشركات القطاع."
        )

    return (
        f"{name} يبلغ {value:.2f}%. "
        "يجب تقييمه بمقارنته بتاريخ الشركة وشركات القطاع."
    )


def explain_liquidity(value, name):
    if value is None:
        return f"لا يمكن حساب {name} بسبب نقص البيانات."

    if value < 1:
        return (
            f"{name} تبلغ {value:.2f} مرة. "
            "الأصول المستخدمة في هذا المؤشر أقل من الالتزامات "
            "قصيرة الأجل، ما يستدعي فحص السيولة والتدفقات النقدية."
        )

    if value <= 1.5:
        return (
            f"{name} تبلغ {value:.2f} مرة. "
            "ينبغي تقييم طبيعة الأصول ومواعيد استحقاق الالتزامات."
        )

    return (
        f"{name} تبلغ {value:.2f} مرة. "
        "التغطية أعلى وفق هذا المؤشر، لكن ذلك لا يضمن "
        "توفر النقد أو جودة الأصول."
    )


def explain_equity_share(value):
    if value is None:
        return "لا يمكن حساب نسبة حقوق الملكية إلى الأصول."

    if value < 0:
        return (
            f"النسبة تبلغ {value:.2f}%. "
            "تحقق من البيانات، فقد تشير إلى حقوق ملكية سالبة."
        )

    if value < 30:
        return (
            f"حقوق الملكية تمثل {value:.2f}% من الأصول. "
            "يجب فحص مصادر التمويل والديون وتكلفتها."
        )

    return (
        f"حقوق الملكية تمثل {value:.2f}% من الأصول. "
        "قيّم هذه النسبة مع حجم الديون وتكلفة التمويل "
        "ومستويات الشركات المماثلة."
    )


def explain_growth(old_value, new_value, name):
    if old_value is None or new_value is None:
        return f"لا تتوفر بيانات كافية لتفسير تغير {name}."

    if old_value == 0:
        if new_value > 0:
            return (
                f"انتقل {name} من صفر إلى قيمة موجبة؛ "
                "لا يمكن حساب نسبة نمو اعتيادية."
            )

        if new_value < 0:
            return (
                f"انتقل {name} من صفر إلى قيمة سالبة؛ "
                "لا يمكن حساب نسبة نمو اعتيادية."
            )

        return f"لم يتغير {name} عن الصفر."

    change = (new_value - old_value) / abs(old_value) * 100

    if change > 0:
        return f"{name} ارتفع بنسبة {change:.2f}% مقارنة بالسنة السابقة."

    if change < 0:
        return (
            f"{name} انخفض بنسبة {abs(change):.2f}% "
            "مقارنة بالسنة السابقة."
        )

    return f"{name} لم يتغير مقارنة بالسنة السابقة."


# --------------------------------------------------
# تحميل بيانات صيدال
# --------------------------------------------------
def load_saidal():
    if not DATA_FILE.exists():
        return None

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return None

        if not isinstance(data.get("records"), list):
            return None

        return data

    except (json.JSONDecodeError, OSError):
        return None


data = load_saidal()


# --------------------------------------------------
# إنشاء التبويبات
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📈 تحليل صيدال",
    "🏢 تحليل شركة",
    "🧾 حاسبة السندات"
])


# ==================================================
# التبويب الأول: تحليل صيدال
# ==================================================
with tab1:
    st.header("تحليل شركة صيدال")

    if data is None:
        st.error(
            "تعذر قراءة ملف البيانات. "
            "تحقق من data/saidal_2025.json."
        )

    else:
        records = {
            item["metric"]: item["value"]
            for item in data["records"]
            if isinstance(item, dict)
            and "metric" in item
            and "value" in item
        }

        comparative = data.get("comparative_data", {})
        if not isinstance(comparative, dict):
            comparative = {}

        old = comparative.get("2024", {})
        if not isinstance(old, dict):
            old = {}

        revenue = records.get("revenue")
        ebe = records.get("ebitda_ebe")
        operating = records.get("operating_result")
        profit = records.get("net_profit")

        st.caption(
            f"السنة المالية: {data.get('fiscal_year', 'غير محددة')} "
            "| العملة: الدينار الجزائري"
        )

        # المؤشرات الأساسية
        st.subheader("المؤشرات المالية")

        c1, c2, c3 = st.columns(3)
        c1.metric("الإيرادات", money(revenue))
        c2.metric("النتيجة التشغيلية", money(operating))
        c3.metric("صافي الربح", money(profit))

        # هوامش الربحية
        ebe_margin = ratio(ebe, revenue)
        operating_margin = ratio(operating, revenue)
        profit_margin = ratio(profit, revenue)

        st.subheader("هوامش الربحية")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "هامش EBE",
            percent(ebe_margin * 100 if ebe_margin is not None else None)
        )

        c2.metric(
            "هامش التشغيل",
            percent(
                operating_margin * 100
                if operating_margin is not None else None
            )
        )

        c3.metric(
            "هامش صافي الربح",
            percent(
                profit_margin * 100
                if profit_margin is not None else None
            )
        )

        # السيولة والملاءة
        st.subheader("السيولة والملاءة المالية")

        current_assets = records.get("current_assets")
        current_liabilities = records.get("current_liabilities")
        inventory = records.get("inventory")
        total_assets = records.get("total_assets")
        equity = records.get("equity")

        quick_assets = None
        if current_assets is not None and inventory is not None:
            quick_assets = current_assets - inventory

        current = ratio(current_assets, current_liabilities)
        quick = ratio(quick_assets, current_liabilities)
        equity_share = ratio(equity, total_assets)

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "السيولة الجارية",
            f"{current:.2f} مرة" if current is not None else "غير متاح"
        )

        c2.metric(
            "السيولة السريعة",
            f"{quick:.2f} مرة" if quick is not None else "غير متاح"
        )

        c3.metric(
            "حقوق الملكية / الأصول",
            percent(
                equity_share * 100
                if equity_share is not None else None
            )
        )

        # التفسير المالي
        st.subheader("🧠 تفسير نورة المالي")

        with st.expander("تفسير الربحية", expanded=True):
            st.write(explain_margin(
                ebe_margin * 100 if ebe_margin is not None else None,
                "هامش EBE"
            ))

            st.write(explain_margin(
                operating_margin * 100
                if operating_margin is not None else None,
                "هامش النتيجة التشغيلية"
            ))

            st.write(explain_margin(
                profit_margin * 100
                if profit_margin is not None else None,
                "هامش صافي الربح"
            ))

        with st.expander("تفسير السيولة والملاءة"):
            st.write(explain_liquidity(current, "السيولة الجارية"))
            st.write(explain_liquidity(quick, "السيولة السريعة"))

            st.write(explain_equity_share(
                equity_share * 100
                if equity_share is not None else None
            ))

        # المقارنة السنوية
        st.subheader("مقارنة 2024 و2025")

        labels = {
            "revenue": "الإيرادات",
            "ebitda_ebe": "فائض إجمالي الاستغلال EBE",
            "operating_result": "النتيجة التشغيلية",
            "net_profit": "صافي الربح"
        }

        rows = []

        for key, label in labels.items():
            current_value = records.get(key)
            old_value = old.get(key)

            growth = None

            if (
                current_value is not None
                and old_value is not None
                and old_value != 0
            ):
                growth = (
                    (current_value - old_value) / abs(old_value)
                ) * 100

            rows.append({
                "المؤشر": label,
                "2024 (دج)": old_value,
                "2025 (دج)": current_value,
                "التغير (%)": (
                    round(growth, 2)
                    if growth is not None else None
                )
            })

        table = pd.DataFrame(rows)
        st.dataframe(table, use_container_width=True)

        st.subheader("📊 ماذا تغير بين السنتين؟")

        for key, label in labels.items():
            st.write(
                "• " + explain_growth(
                    old.get(key),
                    records.get(key),
                    label
                )
            )

        # الرسم البياني
        chart_options = [
            key for key in labels
            if old.get(key) is not None
            and records.get(key) is not None
        ]

        if chart_options:
            selected = st.selectbox(
                "اختر مؤشرًا للرسم البياني",
                chart_options,
                format_func=lambda key: labels[key]
            )

            chart = pd.DataFrame({
                "السنة": ["2024", "2025"],
                "القيمة بالدينار": [
                    old[selected],
                    records[selected]
                ]
            }).set_index("السنة")

            st.bar_chart(chart)

        else:
            st.info(
                "لا تتوفر بيانات كافية للمقارنة. "
                "تحقق من comparative_data في ملف JSON."
            )

        # التقييم المالي العام
        st.subheader("🧭 التقييم المالي العام")

        st.caption(
            "تقييم أولي مبني على البيانات المتاحة، "
            "وليس توصية بشراء السهم أو بيعه."
        )

        st.markdown("### 1. الربحية")

        if revenue is None or revenue <= 0:
            st.info(
                "لا يمكن تقييم هوامش الربحية دون إيرادات موجبة."
            )
        elif profit is None:
            st.info("بيانات صافي الربح غير متاحة.")
        elif profit > 0:
            st.success(
                "صافي الربح موجب. تحقق من استدامة الأرباح "
                "ومقارنتها بالسنوات السابقة."
            )
        elif profit < 0:
            st.warning(
                "الشركة سجلت خسارة صافية في البيانات المدخلة."
            )
        else:
            st.warning("صافي الربح يساوي صفرًا.")

        st.markdown("### 2. السيولة")

        if current is None:
            st.info(
                "لا تتوفر بيانات كافية لحساب السيولة الجارية."
            )
        elif current < 1:
            st.warning(
                f"السيولة الجارية {current:.2f} مرة. "
                "الأصول المتداولة أقل من الالتزامات المتداولة؛ "
                "ينبغي فحص التدفقات النقدية ومواعيد الاستحقاق."
            )
        else:
            st.success(
                f"السيولة الجارية {current:.2f} مرة. "
                "الأصول المتداولة تغطي الالتزامات المتداولة "
                "حسابيًا، لكن ذلك لا يضمن توفر النقد."
            )

        st.markdown("### 3. الملاءة المالية")

        if equity_share is None:
            st.info(
                "لا تتوفر بيانات كافية لحساب حقوق الملكية إلى الأصول."
            )
        elif equity_share < 0:
            st.warning(
                "حقوق الملكية سالبة وفق البيانات المدخلة؛ "
                "يجب التحقق من التقرير المالي."
            )
        else:
            st.write(
                "نسبة حقوق الملكية إلى الأصول: "
                f"{equity_share * 100:.2f}%."
            )
            st.caption(
                "تُفسر النسبة مع حجم الديون وتكلفتها وطبيعة نشاط الشركة، "
                "ولا تكفي وحدها للحكم على الملاءة."
            )

        st.markdown("### 4. اتجاه صافي الربح")

        old_profit = old.get("net_profit")

        if profit is None or old_profit is None:
            st.info(
                "لا يمكن مقارنة صافي الربح دون بيانات السنتين."
            )
        elif old_profit == 0:
            st.info(
                "صافي ربح السنة السابقة يساوي صفرًا؛ "
                "لا تصلح نسبة النمو الاعتيادية لهذه الحالة."
            )
        else:
            profit_change = (
                (profit - old_profit) / abs(old_profit)
            ) * 100

            st.metric(
                "تغير صافي الربح",
                f"{profit_change:+.2f}%"
            )

            if profit_change > 0:
                st.success(
                    "ارتفع صافي الربح مقارنة بالسنة السابقة. "
                    "تحقق أيضًا من جودة الأرباح والتدفقات النقدية."
                )
            elif profit_change < 0:
                st.warning(
                    "انخفض صافي الربح مقارنة بالسنة السابقة."
                )
            else:
                st.info(
                    "صافي الربح لم يتغير مقارنة بالسنة السابقة."
                )

        st.markdown("### 5. موثوقية التقييم")

        required_metrics = [
            "revenue",
            "net_profit",
            "current_assets",
            "current_liabilities",
            "total_assets",
            "equity"
        ]

        missing_metrics = [
            metric for metric in required_metrics
            if records.get(metric) is None
        ]

        if missing_metrics:
            st.warning(
                "التقييم غير مكتمل. توجد مؤشرات مالية مفقودة "
                "قد تؤثر في دقته."
            )
            st.write("المؤشرات المفقودة:", ", ".join(missing_metrics))
        else:
            st.info(
                "المؤشرات الأساسية المطلوبة موجودة في ملف البيانات. "
                "يجب مع ذلك مراجعة الأرقام ومصدرها في التقرير الأصلي."
            )

        # تفاصيل مصدر البيانات
        with st.expander("تفاصيل جودة البيانات"):
            st.write("الشركة:", data.get("company", "غير محددة"))
            st.write("عدد المؤشرات:", len(records))
            st.write(
                "المصدر: التقرير المالي الذي أُدخلت بياناته "
                "في ملف JSON. يجب التحقق من القيم من التقرير الأصلي."
            )


# ==================================================
# التبويب الثاني: تحليل شركة يدويًا
# ==================================================
with tab2:
    st.header("تحليل شركة يدويًا")

    st.info(
        "أدخل الأرقام من تقرير مالي موثوق. "
        "هذه الحاسبة لا تجلب الأسعار أو التقارير تلقائيًا."
    )

    with st.form("company_analysis"):
        company = st.text_input("اسم الشركة")
        source = st.text_input("رابط التقرير أو مصدر البيانات")

        year = st.number_input(
            "السنة المالية",
            min_value=2000,
            max_value=2100,
            value=2025
        )

        st.subheader("البيانات المالية بالدينار الجزائري")

        revenue_input = st.number_input(
            "الإيرادات",
            min_value=0.0,
            value=0.0
        )

        profit_input = st.number_input(
            "صافي الربح أو الخسارة",
            value=0.0
        )

        debt_input = st.number_input(
            "إجمالي الديون",
            min_value=0.0,
            value=0.0
        )

        equity_input = st.number_input(
            "حقوق الملكية",
            value=0.0
        )

        total_assets_input = st.number_input(
            "إجمالي الأصول",
            min_value=0.0,
            value=0.0
        )

        submitted = st.form_submit_button("تحليل البيانات")

    if submitted:
        if not company.strip() or not source.strip():
            st.warning("أدخل اسم الشركة ومصدر البيانات.")

        else:
            st.subheader(f"نتائج تحليل {company}")

            st.write("السنة المالية:", int(year))
            st.write("المصدر:", source)

            c1, c2, c3 = st.columns(3)

            c1.metric("الإيرادات", money(revenue_input))
            c2.metric("صافي الربح", money(profit_input))

            margin = ratio(profit_input, revenue_input)

            c3.metric(
                "هامش صافي الربح",
                percent(margin * 100 if margin is not None else None)
            )

            c1, c2 = st.columns(2)

            debt_equity = ratio(debt_input, equity_input)
            assets_equity = ratio(equity_input, total_assets_input)

            c1.metric(
                "الديون / حقوق الملكية",
                f"{debt_equity:.2f} مرة"
                if debt_equity is not None else "غير متاح"
            )

            c2.metric(
                "حقوق الملكية / الأصول",
                percent(
                    assets_equity * 100
                    if assets_equity is not None else None
                )
            )

            if profit_input < 0:
                st.error("صافي الربح المدخل سالب، أي توجد خسارة.")
            elif profit_input > 0:
                st.success("صافي الربح المدخل موجب.")
            else:
                st.info("صافي الربح المدخل يساوي صفرًا.")

            st.caption(
                "النتائج حسابية وتعتمد على البيانات التي أدخلتها."
            )


# ==================================================
# التبويب الثالث: حاسبة السندات
# ==================================================
with tab3:
    st.header("حاسبة السندات")

    face_value = st.number_input(
        "القيمة الاسمية للسند (دج)",
        min_value=0.0,
        value=0.0,
        key="bond_face"
    )

    annual_rate = st.number_input(
        "معدل الفائدة السنوية (%)",
        min_value=0.0,
        value=0.0,
        key="bond_rate"
    )

    purchase_price = st.number_input(
        "سعر شراء السند (دج)",
        min_value=0.0,
        value=0.0,
        key="bond_price"
    )

    if st.button("حساب عائد السند"):
        if purchase_price <= 0:
            st.warning("أدخل سعر شراء موجبًا.")

        else:
            annual_interest = face_value * annual_rate / 100
            current_yield = annual_interest / purchase_price * 100

            c1, c2 = st.columns(2)

            c1.metric(
                "الفائدة السنوية النظرية",
                money(annual_interest)
            )

            c2.metric(
                "العائد الجاري التقريبي",
                percent(current_yield)
            )

            st.caption(
                "هذا العائد الجاري لا يساوي العائد حتى الاستحقاق. "
                "ولا يشمل الضرائب أو الرسوم أو مخاطر التعثر."
            )


# --------------------------------------------------
# تذييل التطبيق
# --------------------------------------------------
st.divider()

st.caption(
    "نورة المالية — أداة معلومات وتحليل تجريبية، "
    "وليست توصية استثمارية."
)
