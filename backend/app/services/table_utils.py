import pandas as pd
import re
from collections import defaultdict
def auto_pivot_llm_table(table_data):
    """
    Accepts: table_data - a dict with keys:
        'columns': [col1, col2, col3],
        'rows': [ [val1, val2, val3], ... ]
    Returns: pivoted dict in table format (customer x months)
    Assumes columns: ['month', 'customer_name_e', 'value'] or ['customer_name_e', 'month', 'value']
    """

    # Detect column order
    columns = table_data["columns"]
    rows = table_data["rows"]
    # Find which is month and which is customer
    if columns[0].lower().startswith("month"):
        month_idx, customer_idx, value_idx = 0, 1, 2
    elif columns[1].lower().startswith("month"):
        customer_idx, month_idx, value_idx = 0, 1, 2
    else:
        raise ValueError("Cannot detect 'month' and 'customer' columns")

    # Unique months and customers (sorted for stability)
    months = sorted({row[month_idx] for row in rows})
    customers = sorted({row[customer_idx] for row in rows})

    # Build lookup: (customer, month) -> value
    lookup = {}
    for row in rows:
        customer = row[customer_idx]
        month = row[month_idx]
        value = row[value_idx]
        lookup[(customer, month)] = value

    # Build pivoted rows
    pivot_rows = []
    for customer in customers:
        row = [customer]
        for month in months:
            val = lookup.get((customer, month), None)  # Use 0 or None as needed
            row.append(val)
        pivot_rows.append(row)

    return {
        "type": "table",
        "title": table_data.get("title", "Pivoted Table"),
        "columns": [columns[customer_idx]] + months,
        "rows": pivot_rows,
    }


def add_year_totals(table_block):
    columns = table_block['columns'][:]  # Copy
    rows = table_block['rows']

    # 1. Extract all years from columns (e.g., "Jan-2023" -> 2023)
    month_pattern = re.compile(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{4})')
    year_col_indices = defaultdict(list)
    for idx, col in enumerate(columns):
        m = month_pattern.match(col)
        if m:
            year = m.group(1)
            year_col_indices[year].append(idx)

    # 2. Add each year total
    for year, idxs in sorted(year_col_indices.items()):
        columns.append(f"{year} Total")
        for row in rows:
            total = sum(row[i] or 0 for i in idxs)
            row.append(round(total, 3))

    # 3. Add grand total (all months)
    all_month_indices = [idx for idx, col in enumerate(columns) if month_pattern.match(col)]
    columns.append("Total")
    for row in rows:
        total = sum(row[i] or 0 for i in all_month_indices)
        row.append(round(total, 3))

    table_block['columns'] = columns
    table_block['rows'] = rows
    return table_block