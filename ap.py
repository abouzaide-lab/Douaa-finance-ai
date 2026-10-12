
import json
from pathlib import Path

import pandas as pd
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Douaa Finance AI",
    page_icon="📊",
    layout="wide"
)

# Load financial data
DATA_FILE = Path(__file__).parent / "data" / "saidal_2025.json"

st.title("Douaa Finance AI")
st.subheader("Financial Analysis Dashboard")
st.caption("SAIDAL | Fiscal year 2025")

if not DATA_FILE.exists():
    st.error("Financial data file was not found.")
    st.stop()

try:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
except (json.JSONDecodeError, OSError) as error:
    st.error(f"Could not read financial data: {error}")
    st.stop()

records = {
    item["metric"]: item["value"]
    for item in data.get("records", [])
    if "metric" in item and "value" in item
}

previous = data.get("comparative_data", {}).get("2024", {})

def get_value(name):
    return records.get(name)

def ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator

def money(value):
    if value is None:
        return "N/A"
    return f"{value:,.2f} DZD"

def percent(value):
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"

# Profitability
revenue = get_value("revenue")
ebe = get_value("ebitda_ebe")
operating = get_value("operating_result")
profit = get_value("net_profit")

st.header("Profitability")

c1, c2, c3 = st.columns(3)

c1.metric("Revenue", money(revenue))
c2.metric("Operating result", money(operating))
c3.metric("Net profit", money(profit))

c4, c5, c6 = st.columns(3)

c4.metric("EBE margin", percent(ratio(ebe, revenue)))
c5.metric("Operating margin", percent(ratio(operating, revenue)))
c6.metric("Net profit margin", percent(ratio(profit, revenue)))

# Liquidity and financial structure
st.header("Liquidity and Financial Structure")

current_assets = get_value("current_assets")
current_liabilities = get_value("current_liabilities")
inventory = get_value("inventory")
total_assets = get_value("total_assets")
equity = get_value("equity")

quick_assets = None
if current_assets is not None and inventory is not None:
    quick_assets = current_assets - inventory

c1, c2, c3 = st.columns(3)

current_ratio = ratio(current_assets, current_liabilities)
quick_ratio = ratio(quick_assets, current_liabilities)
equity_ratio = ratio(equity, total_assets)

c1.metric(
    "Current ratio",
    f"{current_ratio:.2f}x" if current_ratio is not None else "N/A"
)
c2.metric(
    "Quick ratio",
    f"{quick_ratio:.2f}x" if quick_ratio is not None else "N/A"
)
c3.metric(
    "Equity / Total assets",
    percent(equity_ratio)
)

# 2024 vs 2025 comparison
st.header("2024 vs 2025 Comparison")

comparison_metrics = {
    "Revenue": "revenue",
    "EBE": "ebitda_ebe",
    "Operating result": "operating_result",
    "Net profit": "net_profit"
}

rows = []

for label, key in comparison_metrics.items():
    old = previous.get(key)
    new = records.get(key)

    growth = None
    if old is not None and old != 0 and new is not None:
        growth = (new - old) / abs(old) * 100

    rows.append({
        "Indicator": label,
        "2024 (DZD)": old,
        "2025 (DZD)": new,
        "Growth (%)": round(growth, 2) if growth is not None else None
    })

comparison = pd.DataFrame(rows)
st.dataframe(comparison, use_container_width=True)

# Chart
available = [
    label for label, key in comparison_metrics.items()
    if previous.get(key) is not None and records.get(key) is not None
]

if available:
    selected = st.selectbox("Choose an indicator for the chart", available)
    key = comparison_metrics[selected]

    chart_data = pd.DataFrame({
        "Year": ["2024", "2025"],
        "Amount (DZD)": [previous[key], records[key]]
    }).set_index("Year")

    st.bar_chart(chart_data)
else:
    st.info("Comparison data is incomplete. Check the 2024 values.")

# Data quality
st.header("Data Quality")
st.write("Company:", data.get("company", "Unknown"))
st.write("Fiscal year:", data.get("fiscal_year", "Unknown"))
st.write("Number of reported indicators:", len(records))

st.warning(
    "This dashboard provides financial information, not a guaranteed "
    "investment outcome or personalized investment advice. "
    "Verify reported figures against the original financial statements."
)
