
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Noura Finance AI",
    page_icon="📊",
    layout="centered"
)

st.title("📊 نورة المالية")
st.subheader("تحليل الشركات والأسهم والسندات الجزائرية")

st.info(
    "نسخة تجريبية: أدخل البيانات من مصادر موثوقة. "
    "لا توجد أسعار مباشرة متصلة بالبورصة في هذه النسخة."
)

company = st.text_input("اسم الشركة")
source = st.text_input("رابط مصدر البيانات")
report_date = st.date_input("تاريخ البيانات")

st.header("البيانات المالية (دج)")

col1, col2 = st.columns(2)

with col1:
    revenue = st.number_input(
        "الإيرادات السنوية",
        min_value=0.0,
        value=0.0
    )
    net_profit = st.number_input(
        "صافي الربح",
        value=0.0
    )

with col2:
    total_debt = st.number_input(
        "إجمالي الديون",
        min_value=0.0,
        value=0.0
    )
    equity = st.number_input(
        "حقوق الملكية",
        min_value=0.0,
        value=0.0
    )

if st.button("تحليل البيانات", type="primary"):
    if not company.strip():
        st.warning("أدخل اسم الشركة أولاً.")
    elif not source.strip():
        st.warning("أدخل رابط مصدر البيانات للتحقق منها.")
    else:
        st.header("نتائج التحليل")
        st.write("**الشركة:**", company)
        st.write("**تاريخ البيانات:**", report_date)
        st.write("**المصدر:**", source)

        if revenue > 0:
            margin = net_profit / revenue * 100
            st.metric("هامش صافي الربح", f"{margin:.2f}%")
        else:
            st.warning("لا يمكن حساب هامش الربح دون إيرادات موجبة.")

        if equity > 0:
            debt_equity = total_debt / equity
            st.metric(
                "نسبة الديون إلى حقوق الملكية",
                f"{debt_equity:.2f}"
            )
        else:
            st.warning(
                "لا يمكن حساب نسبة الديون إلى حقوق الملكية "
                "دون حقوق ملكية موجبة."
            )

        if net_profit < 0:
            st.error("الشركة سجلت خسارة وفق الرقم المدخل.")
        elif net_profit > 0:
            st.success("صافي الربح المدخل موجب.")

        st.caption(
            "النتائج حسابية وتعتمد على الأرقام المدخلة، "
            "وليست توصية بشراء أو بيع ورقة مالية."
        )

st.divider()
st.header("🧾 حاسبة السندات")

face_value = st.number_input(
    "القيمة الاسمية للسند (دج)",
    min_value=0.0,
    value=0.0,
    key="face"
)

annual_rate = st.number_input(
    "الفائدة السنوية (%)",
    min_value=0.0,
    value=0.0,
    key="rate"
)

purchase_price = st.number_input(
    "سعر شراء السند (دج)",
    min_value=0.0,
    value=0.0,
    key="price"
)

if st.button("حساب عائد الفائدة"):
    if purchase_price > 0:
        annual_interest = face_value * annual_rate / 100
        current_yield = annual_interest / purchase_price * 100

        st.metric(
            "الفائدة السنوية النظرية",
            f"{annual_interest:,.2f} دج"
        )
        st.metric(
            "العائد الجاري التقريبي",
            f"{current_yield:.2f}%"
        )
        st.caption(
            "هذا عائد جارٍ تقريبي، وليس العائد حتى الاستحقاق. "
            "لا يشمل الضرائب أو الرسوم أو مخاطر التعثر."
        )
    else:
        st.warning("أدخل سعر شراء موجباً.")
