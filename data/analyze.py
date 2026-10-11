
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
