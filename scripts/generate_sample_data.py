#!/usr/bin/env python3
"""
Generate sample Meesho export files for testing GST Automation
"""
import pandas as pd
from pathlib import Path
import random

# Create test_data directory
test_dir = Path("/app/test_data")
test_dir.mkdir(exist_ok=True)

# Sample state names
states = [
    "Maharashtra", "Karnataka", "Tamil Nadu", "Gujarat", "Delhi",
    "Uttar Pradesh", "West Bengal", "Rajasthan", "Punjab", "Haryana"
]

# Valid GST rates
gst_rates = [5, 12, 18, 28]

# Generate TCS Sales data
print("Generating TCS Sales file...")
tcs_sales_data = []
for i in range(50):
    tcs_sales_data.append({
        "gst_rate": random.choice(gst_rates),
        "total_taxable_sale_value": round(random.uniform(100, 5000), 2),
        "end_customer_state_new": random.choice(states),
        "order_id": f"ORD{1000 + i}",
        "product_name": f"Product {i % 10 + 1}"
    })

tcs_sales_df = pd.DataFrame(tcs_sales_data)
tcs_sales_df.to_excel(test_dir / "tcs_sales.xlsx", index=False)
print(f"✓ Created tcs_sales.xlsx with {len(tcs_sales_data)} rows")

# Generate TCS Sales Return data
print("Generating TCS Sales Return file...")
tcs_returns_data = []
for i in range(10):
    tcs_returns_data.append({
        "gst_rate": random.choice(gst_rates),
        "total_taxable_sale_value": round(random.uniform(100, 2000), 2),
        "end_customer_state_new": random.choice(states),
        "order_id": f"RET{1000 + i}",
        "product_name": f"Product {i % 5 + 1}"
    })

tcs_returns_df = pd.DataFrame(tcs_returns_data)
tcs_returns_df.to_excel(test_dir / "tcs_sales_return.xlsx", index=False)
print(f"✓ Created tcs_sales_return.xlsx with {len(tcs_returns_data)} rows")

# Generate Tax Invoice Details
print("Generating Tax Invoice Details file...")
tax_invoice_data = []
for i in range(60):
    tax_invoice_data.append({
        "Type": "Invoice",
        "Invoice No.": f"INV-2025-{1001 + i:04d}",
        "Invoice Date": f"2025-01-{(i % 28) + 1:02d}",
        "Customer Name": f"Customer {i % 20 + 1}",
        "Amount": round(random.uniform(500, 10000), 2)
    })

tax_invoice_df = pd.DataFrame(tax_invoice_data)
tax_invoice_df.to_excel(test_dir / "Tax_invoice_details.xlsx", index=False)
print(f"✓ Created Tax_invoice_details.xlsx with {len(tax_invoice_data)} rows")

# Create a ZIP file with all the files
print("\nCreating ZIP archive...")
import zipfile

zip_path = test_dir / "meesho_export_sample.zip"
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(test_dir / "tcs_sales.xlsx", "tcs_sales.xlsx")
    zipf.write(test_dir / "tcs_sales_return.xlsx", "tcs_sales_return.xlsx")
    zipf.write(test_dir / "Tax_invoice_details.xlsx", "Tax_invoice_details.xlsx")

print(f"✓ Created meesho_export_sample.zip")

print("\n✅ Test files created successfully in /app/test_data/")
print("Files created:")
print("  - tcs_sales.xlsx")
print("  - tcs_sales_return.xlsx")
print("  - Tax_invoice_details.xlsx")
print("  - meesho_export_sample.zip (contains all three files)")
