
import json
from pathlib import Path

# Locate the JSON file
paths = [
    Path("data/saidal_2025.json"),
    Path("saidal_2025.json")
]

data_path = next((p for p in paths if p.exists()), None)

if data_path is None:
    raise SystemExit(
        "Data file not found. Check saidal_2025.json."
    )

with data_path.open("r", encoding="utf-8") as file:
    data = json.load(file)

# Build a dictionary from the reported data
metrics = {
    record["metric"]: record["value"]
    for record in data.get("records", [])
    if "metric" in record and "value" in record
}

def get_value(name):
    return metrics.get(name)

def calculate_ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100

def show_result(name, value, explanation):
    print(f"\n{name}")

    if value is None:
        print("Not enough data to calculate this indicator.")
        return

    print(f"Result: {value:.2f}%")
    print(f"Interpretation: {explanation}")

revenue = get_value("revenue")
ebitda = get_value("ebitda_ebe")
operating_result = get_value("operating_result")
net_profit = get_value("net_profit")

print("=" * 48)
print("SAIDAL FINANCIAL ANALYSIS")
print("Fiscal year:", data.get("fiscal_year"))
print("=" * 48)

# Profitability ratios
show_result(
    "EBITDA / EBE margin",
    calculate_ratio(ebitda, revenue),
    "Measures operating performance before depreciation, "
    "amortization, financing costs and taxes."
)

show_result(
    "Operating margin",
    calculate_ratio(operating_result, revenue),
    "Measures operating profit relative to revenue."
)

show_result(
    "Net profit margin",
    calculate_ratio(net_profit, revenue),
    "Measures net profit generated per 100 DZD of revenue."
)

# Liquidity and solvency analysis
current_assets = get_value("current_assets")
current_liabilities = get_value("current_liabilities")
inventory = get_value("inventory")
total_assets = get_value("total_assets")
equity = get_value("equity")

print("\n" + "=" * 48)
print("LIQUIDITY AND SOLVENCY")
print("=" * 48)

def show_multiple(name, numerator, denominator, explanation):
    print(f"\n{name}")

    if numerator is None or denominator in (None, 0):
        print("Not enough data to calculate.")
        return

    result = numerator / denominator
    print(f"Result: {result:.2f}x")
    print(f"Interpretation: {explanation}")

show_multiple(
    "Current ratio",
    current_assets,
    current_liabilities,
    "Compares current assets with current liabilities."
)

quick_assets = None
if current_assets is not None and inventory is not None:
    quick_assets = current_assets - inventory

show_multiple(
    "Quick ratio",
    quick_assets,
    current_liabilities,
    "Excludes inventory from current assets."
)

show_result(
    "Equity / Total assets",
    calculate_ratio(equity, total_assets),
    "Shows the percentage of assets financed by equity."
)
# Year-over-year comparison: 2024 vs 2025
print("\n" + "=" * 48)
print("SAIDAL YEAR-OVER-YEAR COMPARISON")
print("=" * 48)

previous_year = data.get("comparative_data", {}).get("2024", {})

comparison_metrics = {
    "revenue": "Revenue",
    "ebitda_ebe": "EBE / EBITDA",
    "operating_result": "Operating result",
    "net_profit": "Net profit"
}

for metric, label in comparison_metrics.items():
    current = get_value(metric)
    previous = previous_year.get(metric)

    print(f"\n{label}")

    if current is None or previous in (None, 0):
        print("Not enough data to compare.")
        continue

    change = current - previous
    growth = (change / abs(previous)) * 100

    print(f"2024: {previous:,.2f} DZD")
    print(f"2025: {current:,.2f} DZD")
    print(f"Change: {change:,.2f} DZD")
    print(f"Growth: {growth:+.2f}%")

# Data-quality checks
print("\n" + "=" * 48)
print("DATA QUALITY CHECK")
print("=" * 48)

required = [
    "revenue",
    "ebitda_ebe",
    "operating_result",
    "net_profit",
    "current_assets",
    "current_liabilities",
    "inventory",
    "total_assets",
    "equity"
]

missing = [name for name in required if name not in metrics]

if missing:
    print("Missing indicators:")
    for name in missing:
        print("-", name)
else:
    print("All required indicators are present.")

print("\nAnalysis finished.")
print("This is financial analysis, not investment advice.")
