import json
import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Olist Seller Performance Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
[data-testid="stMetric"]{background:#808080!important;border:1px solid #E0E6ED!important;
border-radius:12px!important;padding:15px 20px!important;box-shadow:0 4px 8px rgba(0,0,0,.1)!important}
[data-testid="stMetricLabel"]>div{color:#fff!important;font-weight:600!important;font-size:16px!important}
[data-testid="stMetricValue"]>div{color:#fff!important;font-weight:700!important;font-size:28px!important}
</style>""", unsafe_allow_html=True)

st.title("📊 Olist Seller Performance Dashboard")
st.caption("Seller revenue, performance tiers, geographical distribution and revenue concentration.")

# =====================================================
# FILE PATHS (UPDATED FOR GITHUB & STREAMLIT CLOUD)
# =====================================================
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
FILES = {
    "sellers": DATA_DIR / "olist_sellers_dataset.csv",
    "items": DATA_DIR / "olist_order_items_dataset.csv",
    "orders": DATA_DIR / "olist_orders_dataset.csv"
}

missing = [str(p) for p in FILES.values() if not p.exists()]
if missing:
    st.error("Missing dataset files:\n\n" + "\n".join(missing))
    st.info("Ensure your CSV files are placed inside a 'data/' folder in your repository.")
    st.stop()

@st.cache_data
def load_datasets(paths):
    return tuple(pd.read_csv(p) for p in paths)

sellers_df, items_df, orders_df = load_datasets(tuple(FILES.values()))

REQ = {
    "sellers": {"seller_id", "seller_state"},
    "items": {"seller_id", "order_id", "price"},
    "orders": {"order_id", "customer_id", "order_purchase_timestamp"}
}
for name, df in (("sellers", sellers_df), ("items", items_df), ("orders", orders_df)):
    if REQ[name] - set(df.columns):
        st.error(f"{name} dataset missing columns: {', '.join(sorted(REQ[name]-set(df.columns)))}")
        st.stop()

items_df["price"] = pd.to_numeric(items_df["price"], errors="coerce")
items_df = items_df.dropna(subset=["seller_id", "order_id", "price"])

@st.cache_resource
def create_database():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    sellers_df.to_sql("sellers", conn, if_exists="replace", index=False)
    items_df.to_sql("order_items", conn, if_exists="replace", index=False)
    orders_df.to_sql("orders", conn, if_exists="replace", index=False)
    return conn

conn = create_database()

# ---------- Filters ----------
st.sidebar.header("Dashboard Filters")
STATES = ["All"] + sorted(sellers_df["seller_state"].dropna().unique().tolist())
selected_year = st.sidebar.selectbox("Year", ["All", "2016", "2017", "2018"])
selected_state = st.sidebar.multiselect("Seller State", STATES, default=["All"])
state_json = json.dumps([] if "All" in selected_state else list(selected_state))
st.sidebar.caption("Tier thresholds are based on total seller revenue in R$.")

FILTER_SQL = ("WHERE ((?='All') OR strftime('%Y', o.order_purchase_timestamp)=?) "
              "AND ((?='[]') OR s.seller_state IN (SELECT value FROM json_each(?)))")
JOIN_SQL = ("FROM sellers AS s JOIN order_items AS oi ON s.seller_id=oi.seller_id "
            "JOIN orders AS o ON oi.order_id=o.order_id")
PARAMS = (selected_year, selected_year, state_json, state_json)

# ---------- Queries ----------
kpi = pd.read_sql_query(f"""
WITH sr AS (SELECT s.seller_id, SUM(oi.price) AS rev {JOIN_SQL} {FILTER_SQL} GROUP BY s.seller_id)
SELECT COUNT(*) AS total_sellers, ROUND(SUM(rev),2) AS total_revenue,
       ROUND(MAX(rev),2) AS top_seller_revenue,
       SUM(rev>=100000) AS top_sellers,
       SUM(rev>=50000 AND rev<100000) AS high_performers,
       SUM(rev>=10000 AND rev<50000) AS mid_tier,
       SUM(rev<10000) AS standard_sellers
FROM sr;""", conn, params=PARAMS).iloc[0]

total_orders_kpi = pd.read_sql_query(
    "SELECT COUNT(DISTINCT order_id) AS total_orders FROM orders "
    "WHERE (?='All') OR strftime('%Y', order_purchase_timestamp)=?",
    conn, params=(selected_year, selected_year)).iloc[0]

top20 = pd.read_sql_query(f"""
SELECT s.seller_id, s.seller_state, ROUND(SUM(oi.price),2) AS total_revenue,
       COUNT(DISTINCT oi.order_id) AS total_orders
{JOIN_SQL} {FILTER_SQL} GROUP BY s.seller_id, s.seller_state
ORDER BY total_revenue DESC LIMIT 20;""", conn, params=PARAMS)

pareto = pd.read_sql_query(f"""
WITH sr AS (SELECT s.seller_id, SUM(oi.price) AS rev {JOIN_SQL} {FILTER_SQL} GROUP BY s.seller_id),
r AS (SELECT seller_id, rev, ROW_NUMBER() OVER (ORDER BY rev DESC, seller_id) rn,
      SUM(rev) OVER () gt FROM sr)
SELECT rn AS sellers_ranked, ROUND(rev,2) AS revenue,
       ROUND(100.0*SUM(rev) OVER (ORDER BY rn ROWS UNBOUNDED PRECEDING)/NULLIF(gt,0),2) AS cumulative_pct
FROM r ORDER BY rn;""", conn, params=PARAMS)

filtered = pd.read_sql_query(f"""
WITH sr AS (SELECT s.seller_id, s.seller_state, SUM(oi.price) AS total_revenue,
            COUNT(DISTINCT oi.order_id) AS total_orders {JOIN_SQL} {FILTER_SQL}
            GROUP BY s.seller_id, s.seller_state)
SELECT *, CASE WHEN total_revenue>=100000 THEN 'Top Seller'
               WHEN total_revenue>=50000 THEN 'High Performer'
               WHEN total_revenue>=10000 THEN 'Mid Tier'
               ELSE 'Standard' END AS seller_tier FROM sr;""", conn, params=PARAMS)

concentration = pd.read_sql_query(f"""
WITH sr AS (SELECT s.seller_id, SUM(oi.price) AS rev {JOIN_SQL} {FILTER_SQL} GROUP BY s.seller_id),
t40 AS (SELECT SUM(rev) r FROM (SELECT rev FROM sr ORDER BY rev DESC LIMIT 40))
SELECT (SELECT COUNT(*) FROM sr) total_sellers,
       ROUND(100.0*40/(SELECT COUNT(*) FROM sr),2) top_40_pct_of_sellers,
       (SELECT ROUND(r,2) FROM t40) top_40_revenue,
       ROUND(100.0*(SELECT r FROM t40)/(SELECT SUM(rev) FROM sr),2) top_40_pct_of_revenue""",
       conn, params=PARAMS).iloc[0]

# ---------- Chart data ----------
tier_order = ["Top Seller", "High Performer", "Mid Tier", "Standard"]
tier_chart = (filtered["seller_tier"].value_counts().reindex(tier_order, fill_value=0)
              .rename_axis("seller_tier").reset_index(name="seller_count"))
top20_sorted = top20.sort_values("total_revenue")
state_chart = (filtered.groupby("seller_state", as_index=False)
               .agg(revenue=("total_revenue","sum"), sellers=("seller_id","nunique")))
state_chart["revenue"] = pd.to_numeric(state_chart["revenue"], errors="coerce").fillna(0)
state_chart = state_chart.nlargest(20,"revenue").sort_values("revenue")

# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["Overview", "Seller Performance", "Detail & Method"])

with tab1:
    st.subheader("Headline KPIs")
    st.caption(
        "Headline indicators summarise the seller base, item revenue, the leading seller, "
        "and revenue concentration for the current filter selection. "
        "Revenue represents item prices only and excludes freight values."
    )
    top_40 = concentration["top_40_pct_of_revenue"] if concentration["total_sellers"] > 0 else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Item Revenue", f"R$ {(kpi['total_revenue'] or 0):,.2f}")
    c2.metric("Total Orders", f"{int(total_orders_kpi['total_orders'] or 0):,}")
    c3.metric("Total Sellers", f"{int(kpi['total_sellers'] or 0):,}")
    c4.metric("Top Seller Revenue", f"R$ {(kpi['top_seller_revenue'] or 0):,.2f}")
    
    st.divider(); st.subheader("Seller Tier Distribution")
    st.caption("Sellers are grouped according to their total item revenue during the selected period.")

    fig = px.pie(tier_chart, names="seller_tier", values="seller_count", hole=0.55,
                 title="Seller Distribution by Revenue Tier")
    fig.update_traces(textposition="inside", textinfo="label+percent",
                      textfont=dict(size=18, color="white"),
                      insidetextfont=dict(size=18, color="white"),
                      hovertemplate="<b>%{label}</b><br>Sellers: %{value:,}<br>Share: %{percent}<extra></extra>")
    fig.update_layout(title_font=dict(size=20), legend=dict(font=dict(size=16)),
                      margin=dict(t=60, b=40, l=40, r=40))
    fig.add_annotation(text=f"<b>{int(tier_chart['seller_count'].sum()):,}</b><br>Sellers",
                       x=0.5, y=0.5, font=dict(size=20, color="#333"), showarrow=False)
    st.plotly_chart(fig, use_container_width=True)
    
    standard_pct = 0.0
    if not tier_chart.empty and int(tier_chart["seller_count"].sum()) > 0:
        standard_count = int(tier_chart.loc[tier_chart["seller_tier"] == "Standard", "seller_count"].sum())
        seller_count = int(tier_chart["seller_count"].sum())
        standard_pct = 100 * standard_count / seller_count

    st.markdown("**Key insight**")
    st.write(
        f"**{standard_pct:.2f}%** of sellers with sales in this selection fall into "
        "the Standard tier (below R$10,000 in item revenue). This describes revenue "
        "scale, not seller effort, customer satisfaction, or profitability."
    )
    st.markdown("**Recommended action**")
    st.write(
        "Compare sellers across tiers by order volume, product mix, and average item "
        "revenue per order. Use these comparisons to identify realistic support and "
        "growth opportunities."
    )

with tab2:
    st.subheader("Top 20 Sellers by Revenue")
    st.caption(
        "Compares item revenue by seller registration state—not customer location. "
        "Interpret state totals alongside the number of sellers in each state."
    )
    st.plotly_chart(px.bar(top20_sorted, x="total_revenue", y="seller_id", orientation="h",
                           hover_data=["seller_state","total_orders"],
                           labels={"total_revenue":"Revenue (R$)","seller_id":"Seller ID",
                                   "seller_state":"State","total_orders":"Distinct Orders"},
                           title="Highest-Revenue Sellers"), use_container_width=True)
    st.divider()
    L, R = st.columns(2)
    with L:
        st.subheader("Top States by Seller Revenue")
        state_chart["seller_state"] = state_chart["seller_state"].astype(str)
        fs = px.bar(state_chart, x="revenue", y="seller_state", orientation="h",
                    hover_data=["sellers"],
                    labels={"revenue":"Revenue (R$)","seller_state":"Seller State",
                            "sellers":"Number of Sellers"},
                    title="Revenue Contribution by Seller State")
        fs.update_yaxes(type="category", categoryorder="array",
                        categoryarray=state_chart["seller_state"].tolist(),
                        tickmode="array", tickvals=state_chart["seller_state"].tolist(),
                        ticktext=state_chart["seller_state"].tolist(),
                        tickfont=dict(size=14), automargin=True)
        fs.update_traces(marker_line_width=0, width=0.75)
        fs.update_layout(margin=dict(t=60,b=40,l=80,r=40), title_font=dict(size=18), bargap=0.25)
        st.plotly_chart(fs, use_container_width=True)
        st.markdown("**Key insight**")
        st.write(
             "Sao Paulo accounts for a major share of total item revenue and sellers, making it Olist's dominant revenue-generating state. "
             "Parana and Minas Gerais are the next-largest contributors, highlighting a strong geographical concentration."
        )
        st.markdown("**Recommended action**")
        st.write(
             "Regional Operations and Seller Acquisition should investigate growth opportunities in states outside Sao Paulo. "
             "Data Analytics should compare average revenue per seller across states."
        )
    with R:
        st.subheader("Cumulative Revenue Contribution Curve")
        if not pareto.empty:
            fp = px.line(pareto, x="sellers_ranked", y="cumulative_pct",
                         labels={"sellers_ranked":"Seller Rank (highest revenue first)",
                                 "cumulative_pct":"Cumulative Revenue (%)"},
                         title="Cumulative Revenue Contribution by Seller Rank")
            fp.update_yaxes(range=[0,100])
            st.plotly_chart(fp, use_container_width=True)
        else:
            st.info("No sellers match the selected filters.")
        st.markdown("**Key insight**")
        st.write(
             "Revenue contribution is concentrated among the highest-ranked sellers. As more sellers are added, cumulative revenue increases at a slower rate."
        )
        st.markdown("**Recommended action**")
        st.write(
             "Key Account Management should monitor and retain high-value sellers, while Seller Management should identify growth opportunities among other sellers."
        )

with tab3:
    st.subheader("Advanced Feature: Revenue Concentration (Pareto Analysis)")
    st.caption(
        "Quantifies the share of sellers and item revenue represented by the 40 highest-revenue "
        "sellers in the current selection."
    )
    if concentration["total_sellers"] > 0:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Top 40 Sellers Revenue", f"R$ {concentration['top_40_revenue']:,.2f}")
        col_b.metric("Top 40 % Share of Revenue", f"{concentration['top_40_pct_of_revenue']:.2f}%")
        col_c.metric("Top 40 % of Sellers", f"{concentration['top_40_pct_of_sellers']:.2f}%")
    st.markdown("**Interpretation**")
    st.write(
        f"The highest-revenue {min(40, int(concentration['total_sellers']))} sellers contribute "
        f"**{float(concentration['top_40_pct_of_revenue'] or 0):.2f}%** of item revenue while "
        f"representing **{float(concentration['top_40_pct_of_sellers'] or 0):.2f}%** of sellers "
        "in this selection."
    )
    st.markdown("**Recommended action**")
    st.write(
        "Investigate what drives leading sellers' revenue and monitor retention exposure, "
        "while assessing opportunities to develop other sellers."
    )

    if not pareto.empty:
        p40 = pareto.head(40)
        fig = px.bar(p40, x="sellers_ranked", y="revenue",
                     title="Revenue Concentration — Top 40 Sellers (Pareto View)",
                     labels={"sellers_ranked":"Seller Rank","revenue":"Revenue (R$)"})
        fig.add_scatter(x=p40["sellers_ranked"], y=p40["cumulative_pct"], mode="lines+markers",
                        name="Cumulative %", yaxis="y2", line=dict(color="crimson", width=2))
        fig.update_layout(yaxis=dict(title="Revenue (R$)"),
                          yaxis2=dict(title="Cumulative Revenue (%)", overlaying="y",
                                      side="right", range=[0,100]),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"**Concentration insight:** The top 40 sellers account for "
                f"**{concentration['top_40_pct_of_revenue']:.2f}%** of total revenue under the current filters.")
    else:
        st.info("No sellers match the selected filters.")

    st.divider()
    st.subheader("Data Limitations, Method Notes & Recommendations")
    st.markdown("""
    **Methodology:**
    - **Revenue** was calculated as the sum of order-item `price`, excluding freight value.
    - Sellers are grouped into four tiers by total revenue: **Top Seller** ≥ R$ 100,000; High Performer ≥ R$ 50,000;
      **Mid Tier** ≥ R$ 10,000; **Standard** < R$ 10,000.
    - **Total Orders** counts distinct `order_id` in `order_items` to avoid multiple item rows being counted as multiple orders.   
    - **Year filter** uses `order_purchase_timestamp` (applies to seller revenue).
    - **State filter** uses the `seller_state` from the **sellers** table.
    - **Multi-state selection**: "All" includes every state.
    - **Revenue Concentration** was examined in two ways: **The Pareto Curve** and the **The Top 40 Revenue Share**.
    
    **Data Limitations:**
    - Due to partial coverage of the years **2016 and 2018**, annual comparisons were not included as this would make these years appear weaker compared to 2017.
    - The analysis only covers sales value (**Revenue**) and not **Profit** because data on production costs, operating expenses, and fees are unavailable.
    - **No product category or review-score data** is included in this particular view.
    - Sellers with **zero orders** in the filtered period are excluded entirely.
    - Geographic analysis reflects the **seller's** state, not the customer's delivery location.
    - Missing/malformed `price` values are dropped, slightly understating revenue.
    
    **Recommendations:**
    - **Seller Management** should identify promising Standard-tier sellers and provide targeted support.
    - **Key Account Management** should monitor top sellers and strengthen relationships to protect existing revenue.
    - **Business Strategy** should track revenue concentration and broaden the revenue base.
    - **Regional Operations** should investigate growth opportunities outside Sao Paulo.
    """)