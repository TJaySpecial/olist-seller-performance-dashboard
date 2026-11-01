# 📊 Olist E-Commerce: Seller Performance & Revenue Concentration Dashboard

**PORA Academy Cohort 7 · Data Analysis & AI Automation Capstone Project (Group 3)**

A production-grade, interactive Streamlit analytics web application built on an in-memory SQLite relational engine. This project evaluates marketplace seller performance, revenue tier distributions, state-level geographic dominance, and revenue concentration across Brazil using the Olist E-Commerce public dataset (2016–2018).

---

## 🎯 Executive Summary & Analytical Scope

The Olist Seller Performance Dashboard provides actionable business intelligence for e-commerce marketplace managers, key account teams, and regional expansion leads. Across 3,095 unique sellers generating **R$ 13,591,643.70** in item revenue across **99,441 distinct orders**:

* **Extreme Revenue Concentration:** The top 40 sellers (just 1.29% of active merchants) drive **29.54%** of total item revenue (R$ 4,014,922.70).
* **Tier Asymmetry:** **90.57%** of active merchants operate in the Standard tier (<R$ 10k revenue), while Mid Tier merchants generate **36.73%** of overall revenue despite accounting for only 8.14% of sellers.
* **Geographic Hegemony:** São Paulo (SP) houses **59.74%** of all active sellers and commands **64.41%** (R$ 8,753,396.21) of marketplace item revenue.

---

## 🚀 Live Application & Deployment

* **Live Interactive App:** [Olist Seller Performance Dashboard](https://olist-seller-performance-dashboard-dqecuzlywsh293hnkgcktd.streamlit.app/)
* **Local Web Server:** `http://localhost:8501`

---

## 📂 Repository Structure

```text
Project/
├── data/
│   ├── olist_sellers_dataset.csv       # Seller demographics & state mappings (3,095 rows)
│   ├── olist_order_items_dataset.csv   # Line-item pricing & seller-order linkages (112,650 rows)
│   └── olist_orders_dataset.csv        # Order lifecycle & timestamps (99,441 rows)
├── app.py                              # Main Streamlit application & SQLite query engine
├── requirements.txt                    # Project dependencies for production deployment
└── README.md                           # Documentation & analytical methodology
```

---

## ⚙️ Technical Architecture & Stack

* **Frontend / UI:** Streamlit (`st.tabs`, `st.metrics`, `st.sidebar`, Custom CSS styling)
* **Data Processing & Validation:** Python (`pandas`, `pathlib`, `json`)
* **Relational Backend Engine:** In-memory SQLite (`sqlite3`) using `@st.cache_resource` connection persistence to prevent concurrency and table lock errors across user interactions.
* **Security & Parametrization:** Parameterized SQL queries utilizing SQLite's native `json_each()` function for multi-state filtering, preventing SQL injection and formatting exceptions.
* **Data Visualizations:** Plotly Express (`px.pie`, `px.bar`, `px.line` with secondary dual-axis overlay).

---

## 📊 Detailed Tab Overview

### 1. Overview Tab
* **Headline Metrics:** Real-time summary cards for Total Item Revenue, Total Distinct Orders, Total Active Sellers, and Leading Seller Revenue.
* **Seller Tier Distribution:** Donut chart categorizing merchants into Standard (<R$ 10k), Mid Tier (R$ 10k–R$ 50k), High Performer (R$ 50k–R$ 100k), and Top Seller (≥R$ 100k).
* **Revenue Contribution by Tier:** Comparative bar chart highlighting revenue share vs. merchant share across tiers.

### 2. Seller Performance Tab
* **Top 20 Sellers by Revenue:** Horizontal bar visualization highlighting individual merchant sales with optional 8-character ID truncation.
* **Geographic Dominance:** State-level revenue rankings showing São Paulo's leading market share.
* **Cumulative Revenue Contribution:** Line chart displaying seller rank vs. cumulative percentage share of revenue.

### 3. Detail & Method Tab
* **Advanced Feature (Pareto Analysis):** Dual-axis chart plotting top 40 individual seller revenues alongside the cumulative percentage contribution curve.
* **Method Notes & Governance:** Explicit grain definitions, data cleaning rules, temporal boundaries (2016–2018), and limitations (exclusion of freight costs and profit margins).

---

## 💻 Local Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/TJaySpecialolist-seller-performance-dashboard.git
   cd olist-seller-performance-dashboard
   ```

2. **Ensure CSV Files are in Place:**
   Place the three required CSV files into the `data/` directory:
   * `olist_sellers_dataset.csv`
   * `olist_order_items_dataset.csv`
   * `olist_orders_dataset.csv`

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Dashboard:**
   ```bash
   streamlit run app.py
   ```

---

## 🛡️ Methodology & Data Governance Notes

1. **Revenue Grain:** Calculated strictly as `SUM(order_item_price)`. Freight charges are excluded to measure merchant sales performance directly.
2. **Order Disambiguation:** Orders are aggregated using `COUNT(DISTINCT order_id)` to prevent line-item fan-out errors.
3. **Temporal Scope:** Dataset covers 2016 to 2018. Due to partial coverage in 2016 and 2018, multi-year comparisons focus on relative distribution rather than annual growth rates.
4. **Geographical Mapping:** Refers to seller registration headquarters, not customer delivery destinations.
5. * **Revenue vs. Profitability:** Analysis focuses strictly on gross sales value (`price`) because cost of goods sold (COGS), seller fees, operating expenses, and taxes are not available in the dataset.