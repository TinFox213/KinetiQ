# Phase 01: Domain Data Engineering & Synthetic Ground-Truth Engine

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** Data Engineering & Database Schema

---

## 1\. Objective & Scope

The goal of Phase 01 is to build a robust, self-generating retail data layer that models a multi-store retail chain (3 stores: Downtown Express, Suburban Supercenter, Highway Hub) across 250 SKUs over a rolling 90-day window. The synthetic data generator must synthesize realistic retail patterns:

1. Fast-moving staples with Poisson demand.  
2. Perishables with shelf-life limits and expiration shrinkage.  
3. Slow-moving specialty items that accumulate dead stock.  
4. Sudden stockouts (inventory hitting zero, sales truncated).  
5. Promotional sales spikes and phantom inventory drops.

---

## 2\. Relational Database Schema (SQLite / DuckDB)

\-- 1\. Stores Table

CREATE TABLE IF NOT EXISTS stores (

    store\_id TEXT PRIMARY KEY,

    name TEXT NOT NULL,

    city TEXT NOT NULL,

    store\_type TEXT NOT NULL, \-- 'Urban Express', 'Suburban Super', 'Highway Transit'

    sq\_ft INTEGER NOT NULL,

    manager\_name TEXT NOT NULL

);

\-- 2\. Suppliers Table

CREATE TABLE IF NOT EXISTS suppliers (

    supplier\_id TEXT PRIMARY KEY,

    supplier\_name TEXT NOT NULL,

    lead\_time\_days INTEGER NOT NULL,

    min\_order\_qty INTEGER NOT NULL,

    reliability\_score REAL NOT NULL \-- e.g., 0.95

);

\-- 3\. Products Catalog Table

CREATE TABLE IF NOT EXISTS products (

    sku\_id TEXT PRIMARY KEY,

    product\_name TEXT NOT NULL,

    category TEXT NOT NULL, \-- 'Dairy & Eggs', 'Bakery', 'Beverages', 'Snacks', 'Pantry'

    sub\_category TEXT NOT NULL,

    cost\_price REAL NOT NULL,

    retail\_price REAL NOT NULL,

    is\_perishable BOOLEAN NOT NULL,

    shelf\_life\_days INTEGER,

    supplier\_id TEXT NOT NULL,

    FOREIGN KEY (supplier\_id) REFERENCES suppliers(supplier\_id)

);

\-- 4\. Inventory Snapshots Table (Daily record per store & SKU)

CREATE TABLE IF NOT EXISTS inventory\_snapshots (

    snapshot\_date DATE NOT NULL,

    store\_id TEXT NOT NULL,

    sku\_id TEXT NOT NULL,

    on\_hand\_units INTEGER NOT NULL,

    reserved\_units INTEGER DEFAULT 0,

    days\_since\_last\_sale INTEGER DEFAULT 0,

    PRIMARY KEY (snapshot\_date, store\_id, sku\_id),

    FOREIGN KEY (store\_id) REFERENCES stores(store\_id),

    FOREIGN KEY (sku\_id) REFERENCES products(sku\_id)

);

\-- 5\. Daily Sales Table

CREATE TABLE IF NOT EXISTS daily\_sales (

    sale\_date DATE NOT NULL,

    store\_id TEXT NOT NULL,

    sku\_id TEXT NOT NULL,

    units\_sold INTEGER NOT NULL,

    gross\_revenue REAL NOT NULL,

    had\_stockout BOOLEAN DEFAULT 0,

    PRIMARY KEY (sale\_date, store\_id, sku\_id),

    FOREIGN KEY (store\_id) REFERENCES stores(store\_id),

    FOREIGN KEY (sku\_id) REFERENCES products(sku\_id)

);

\-- 6\. Inter-Store Transfers Log

CREATE TABLE IF NOT EXISTS store\_transfers (

    transfer\_id TEXT PRIMARY KEY,

    created\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,

    from\_store\_id TEXT NOT NULL,

    to\_store\_id TEXT NOT NULL,

    sku\_id TEXT NOT NULL,

    units INTEGER NOT NULL,

    status TEXT NOT NULL \-- 'PENDING', 'IN\_TRANSIT', 'COMPLETED'

);

---

## 3\. Data Generator Engine (`src/data/generator.py`)

### Mathematical Distribution Principles:

- **Fast-Moving Goods:** Daily sales $X \\sim \\text{Poisson}(\\lambda \= 12 \\text{ to } 25)$.  
- **Medium-Moving Goods:** Daily sales $X \\sim \\text{Poisson}(\\lambda \= 3 \\text{ to } 8)$.  
- **Slow-Moving / Dead Stock:** Daily sales $X \\sim \\text{Bernoulli}(p \= 0.05 \\text{ to } 0.10)$, creating long 0-sales runs.  
- **Stock Depletion & Replenishment Logic:** $$\\text{Stock}*{t} \= \\max(0, \\text{Stock}*{t-1} \- \\text{Sales}\_t) \+ \\text{Replenishment}*t$$ If $\\text{Stock}*{t-1} \< \\text{Demand}\_t$, $\\text{UnitsSold}*t \= \\text{Stock}*{t-1}$, $\\text{had\_stockout} \= 1$, and $\\text{Stock}\_t \= 0$.

### Implementation Code Skeleton:

import sqlite3

import random

from datetime import date, timedelta

import numpy as np

def generate\_retail\_dataset(db\_path="data/retail\_inventory.db", days=90):

    conn \= sqlite3.connect(db\_path)

    cur \= conn.cursor()

    \# Execute schema

    \# Seed 3 stores: STORE\_01 (Downtown), STORE\_02 (Suburban), STORE\_03 (Highway)

    \# Seed 5 suppliers (Lead times: 2 to 6 days)

    \# Seed 250 realistic SKUs

    \# Simulate 90 days of transactions

    conn.commit()

    conn.close()

---

## 4\. Antigravity AI Implementation Prompt

@Antigravity: Implement \`src/data/generator.py\` and \`src/data/schema.sql\`.

Ensure the generator executes in under 3 seconds using batch \`executemany\` statements.

Create distinct SKU behaviors:

1\. SKU\_1001 to SKU\_1030: Fast perishables (Milk, Sourdough) with 4-day shelf life.

2\. SKU\_1031 to SKU\_1060: High velocity snacks with occasional supplier stockouts.

3\. SKU\_1061 to SKU\_1090: Stagnant specialty items with 0 sales for 35+ days in Store 1, but active in Store 3 (ideal for arbitrage).

Ensure all foreign keys match and write a pytest in \`tests/test\_data\_generator.py\` verifying row counts and zero null values.  
