
# 📊 Sales Analytics Chatbot Backend — PostgreSQL Data Pipeline Guide

This guide documents the full, production-quality process for migrating 3.75 million sales records into PostgreSQL for the Sales Analytics Chatbot project.  
It covers installation, secure database setup, permissions, bulk data upload, data QA, and backend integration best practices.

---

## **1. PostgreSQL Installation**

### **A. On Windows**
- Download and install from [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
- Set a secure password for the `postgres` user during install.

### **B. On Linux (Ubuntu Example)**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

---

## **2. Secure Database and User Creation**

Open the **SQL Shell (psql)** (on Windows, from the Start Menu).

```sql
-- Replace with your preferred username/password
CREATE USER chatbot_user WITH PASSWORD 'AsdZxc@123';
CREATE DATABASE chatbot_data OWNER chatbot_user;
GRANT ALL PRIVILEGES ON DATABASE chatbot_data TO chatbot_user;
```

---

## **3. Table Creation (sales_data Schema)**

Connect to the new database:

```sql
\c chatbot_data
```

Then create the table:

```sql
CREATE TABLE sales_data (
    id SERIAL PRIMARY KEY,
    tran_type VARCHAR(32),
    promo VARCHAR(8),
    mm INT,
    yy INT,
    division_code INT,
    division_name VARCHAR(64),
    manager_code VARCHAR(16),
    manager_name VARCHAR(64),
    su_code VARCHAR(16),
    su_name VARCHAR(64),
    salesman_code VARCHAR(32),
    salesman_name_e VARCHAR(64),
    customer_code VARCHAR(32),
    customer_name_e VARCHAR(128),
    customer_code_child VARCHAR(32),
    customer_name_e_child VARCHAR(128),
    brandname VARCHAR(64),
    item_code VARCHAR(32),
    item_name_e VARCHAR(128),
    item_rec_code VARCHAR(32),
    item_rec_name VARCHAR(128),
    sales_value NUMERIC(18,3),
    sales_qty NUMERIC(18,3),
    sales_prof NUMERIC(18,3),
    sr_reason_description VARCHAR(128),
    child_channel VARCHAR(32),
    job_date DATE,
    job_no VARCHAR(32),
    foc_value NUMERIC(18,3),
    actual_discount_value NUMERIC(18,3),
    div_typ VARCHAR(16),
    current_sm VARCHAR(32),
    shelf_life NUMERIC(8,1),
    div_type VARCHAR(32),
    warehouse_name VARCHAR(64),
    comp_code VARCHAR(16),
    branch VARCHAR(16),
    sub_branch VARCHAR(16)
);
```

---

## **4. Grant Permissions to Sequences**

**Critical for bulk inserts with `SERIAL` primary key:**

```sql
GRANT USAGE, SELECT ON SEQUENCE sales_data_id_seq TO chatbot_user;
```

---

## **5. Bulk Data Migration (Python Script)**

**Requirements:**  
- Python 3.8+
- `pip install pandas sqlalchemy psycopg2-binary`

**Example script (`import_sales_data.py`):**

```python
import pandas as pd
from sqlalchemy import create_engine

CSV_PATH = "C:/path/to/full_sales_data.csv"
POSTGRES_URL = "postgresql+psycopg2://chatbot_user:AsdZxc%40123@localhost:5432/chatbot_data"
TABLE_NAME = "sales_data"
chunksize = 50000

dtype_map = {
    'tran_type': str,
    'promo': str,
    'mm': int,
    'yy': int,
    'division_code': int,
    'division_name': str,
    'manager_code': str,
    'manager_name': str,
    'su_code': str,
    'su_name': str,
    'salesman_code': str,
    'salesman_name_e': str,
    'customer_code': str,
    'customer_name_e': str,
    'customer_code_child': str,
    'customer_name_e_child': str,
    'brandname': str,
    'item_code': str,
    'item_name_e': str,
    'item_rec_code': str,
    'item_rec_name': str,
    'sales_value': float,
    'sales_qty': float,
    'sales_prof': float,
    'sr_reason_description': str,
    'child_channel': str,
    'job_date': str,
    'job_no': str,
    'foc_value': float,
    'actual_discount_value': float,
    'div_typ': str,
    'current_sm': str,
    'shelf_life': float,
    'div_type': str,
    'warehouse_name': str,
    'comp_code': str,
    'branch': str,
    'sub_branch': str,
}

engine = create_engine(POSTGRES_URL)
for chunk in pd.read_csv(CSV_PATH, dtype=dtype_map, chunksize=chunksize, low_memory=False):
    chunk.columns = [col.lower() for col in chunk.columns]
    chunk['job_date'] = pd.to_datetime(chunk['job_date'], format='%Y-%m-%d', errors='coerce')
    chunk.to_sql(TABLE_NAME, engine, if_exists='append', index=False)
    print(f"Uploaded {len(chunk)} rows...")

print("✅ CSV upload to PostgreSQL completed!")
```

---

## **6. Post-Import: Data QA and Validation**

### **What We Observed (Validation Results):**
- **No null `job_date` values:** All rows have valid dates.
- **Distinct `tran_type` values:** Only `'Sales'` and `'Sales Return'`, as expected.
- **Minimum `sales_value`:** `-31,350.000`  
- **Maximum `sales_value`:** `34,925.000`
- **Rows where `sales_value` <= 0:** `827,537` (likely returns, credits, or promotions)
- **Data types:** All columns are correctly typed and validated by the database schema.
- **No import errors or data loss observed.**

**These checks confirm a healthy, business-meaningful data import. If negative/zero values are expected for returns or credits, this result is fully correct and analytics-ready.**

---

## **7. Add Analytics Indexes (Highly Recommended)**

```sql
CREATE INDEX idx_sales_job_date ON sales_data(job_date);
CREATE INDEX idx_sales_customer_code ON sales_data(customer_code);
CREATE INDEX idx_sales_item_code ON sales_data(item_code);
CREATE INDEX idx_sales_salesman_code ON sales_data(salesman_code);
```

---

## **8. Troubleshooting Permissions**

If you see a permission error about sequences, re-run:
```sql
GRANT USAGE, SELECT ON SEQUENCE sales_data_id_seq TO chatbot_user;
```

---

## **9. Backend Integration**

- Point your FastAPI/SQLAlchemy config to:
  ```
  postgresql+psycopg2://chatbot_user:AsdZxc%40123@localhost:5432/chatbot_data
  ```
- Ensure your `.env` is updated accordingly.

---

## **10. Best Practices / Notes**

- Use chunked import for speed and reliability (`chunksize=50000` is recommended for large files).
- Always lower-case your column names before import to PostgreSQL.
- Use explicit types in your pandas import for data consistency and speed.
- **Negative or zero `sales_value`** is expected for returns—confirm business logic before excluding.

---

## **Support**

For advanced analytics, role-based access, or scaling, see the `/docs` or contact the backend development team.

---

**This guide ensures a smooth, scalable, and robust data foundation for your Sales Analytics Chatbot and business intelligence backend.**
