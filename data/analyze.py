
import json
from pathlib import Path

# Find the financial data file
possible_paths = [
    Path("data/saidal_2025.json"),
    Path("saidal_2025.json")
]

data_file = next(
    (path for path in possible_paths if path.exists()),
    None
)

if data_file is None:
    print("ERROR: Financial data file not found.")
    print("Check the location of saidal_2025.json.")
    raise SystemExit(1)

# Load the data
with data_file.open("r", encoding="utf-8") as file:
    data = json.load(file)

print("=" * 50)
print("SAIDAL - FINANCIAL ANALYSIS")
print("Fiscal year:", data.get("fiscal_year"))
print("=" * 50)

for record in data.get("records", []):
    name = record.get("label_ar", record.get("metric", "Unknown"))
    value = record.get("value")
    unit = record.get("unit", "")
    previous = record.get("previous_year_value")
    change = record.get("change_percent")
    data_type = record.get("data_type", "unknown")

    if isinstance(value, (int, float)):
        if unit == "DZD":
            displayed_value = f"{value:,.2f} DZD"
        elif unit == "percent":
            displayed_value = f"{value:.2f}%"
        else:
            displayed_value = f"{value:,.2f} {unit}"
    else:
        displayed_value = str(value)

    print(f"\nIndicator: {name}")
    print(f"Value: {displayed_value}")
    print(f"Data type: {data_type}")

    if previous is not None:
        print(f"Previous year: {previous:,.2f}")

    if change is not None:
        print(f"Annual change: {change:.2f}%")

    if record.get("source_page") is not None:
        print(f"Source page: {record['source_page']}")

print("\nAnalysis completed.")
