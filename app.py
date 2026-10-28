import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Dynamic Income & Expense Analyzer", page_icon="💰", layout="wide"
)

st.title("💰 Dynamic Income & Expense Analyzer")
st.markdown(
    "Dynamically add income streams and recurring expenses across multiple frequencies, categorized for clean financial modeling."
)

# -------------------------------------------------------------------------
# 1. NET INCOMES FROM MULTIPLE PARTIES
# -------------------------------------------------------------------------
st.header("1. Net Income Streams")
st.markdown(
    "Add multiple net income sources (e.g., Party 1 Salary, Party 2 Side Hustle) and set their payment frequency."
)

if "incomes" not in st.session_state:
    st.session_state.incomes = [
        {"name": "Party 1 - Primary Salary", "amount": 6000.0, "frequency": "Monthly"},
        {"name": "Party 2 - Salary", "amount": 3000.0, "frequency": "Monthly"},
    ]

# Form or dynamic inputs for income
income_cols = st.columns([3, 2, 2, 1])
with income_cols[0]:
    st.markdown("**Income Source Name**")
with income_cols[1]:
    st.markdown("**Amount ($)**")
with income_cols[2]:
    st.markdown("**Frequency**")
with income_cols[3]:
    st.markdown("**Action**")

freq_multipliers = {
    "Weekly": 52 / 12,
    "Bi-Weekly": 26 / 12,
    "Monthly": 1.0,
    "Annual": 1 / 12,
}

updated_incomes = []
for i, inc in enumerate(st.session_state.incomes):
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    with c1:
        name = st.text_input(
            "Name", value=inc["name"], key=f"inc_name_{i}", label_visibility="collapsed"
        )
    with c2:
        amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=100.0,
            value=float(inc["amount"]),
            key=f"inc_amt_{i}",
            label_visibility="collapsed",
        )
    with c3:
        freq = st.selectbox(
            "Frequency",
            list(freq_multipliers.keys()),
            index=list(freq_multipliers.keys()).index(inc["frequency"]),
            key=f"inc_freq_{i}",
            label_visibility="collapsed",
        )
    with c4:
        remove = st.button("❌", key=f"inc_rem_{i}")

    if not remove:
        monthly_equiv = amount * freq_multipliers[freq]
        updated_incomes.append(
            {
                "name": name,
                "amount": amount,
                "frequency": freq,
                "monthly": monthly_equiv,
            }
        )

st.session_state.incomes = updated_incomes

if st.button("➕ Add Income Stream"):
    st.session_state.incomes.append(
        {"name": "New Income", "amount": 1000.0, "frequency": "Monthly"}
    )
    st.rerun()

# Calculate Total Monthly Income
total_monthly_income = sum(item["monthly"] for item in st.session_state.incomes)
st.metric("Total Monthly Net Income", f"${total_monthly_income:,.2f}")

st.divider()

# -------------------------------------------------------------------------
# 2. EXPENSES BY CATEGORY
# -------------------------------------------------------------------------
st.header("2. Categorized Expenses")
st.markdown(
    "Add recurring expenses across specified categories. Amounts are automatically normalized to a monthly equivalent."
)

categories = [
    "House Expenses",
    "Vehicle Expenses",
    "Household Costs",
    "Personal Expenses",
]

if "expenses" not in st.session_state:
    st.session_state.expenses = [
        {
            "category": "Household Expenses",
            "name": "Rates & Insurances, Maintenance Costs etc",
            "amount": 400.0,
            "frequency": "Monthly",
        },
        {
            "category": "Vehicle Expenses",
            "name": "Vehicle Payments, Insurances, Fuel, Registration, Tires, Warrent Of Fitness, Maintenance/Servicing",
            "amount": 600.0,
            "frequency": "Monthly",
        },
        {
            "category": "Household Costs",
            "name": "Groceries, Power, Gas, Internet & Subs",
            "amount": 1500.0,
            "frequency": "Monthly",
        },
        {
            "category": "Personal Expenses",
            "name": "Entertainment & Lifestyle, Takeaways, Bakery Food, Coffees, Restaurants etc",
            "amount": 500.0,
            "frequency": "Monthly",
        },
    ]

exp_cols = st.columns([2, 3, 2, 2, 1])
with exp_cols[0]:
    st.markdown("**Category**")
with exp_cols[1]:
    st.markdown("**Expense Name**")
with exp_cols[2]:
    st.markdown("**Amount ($)**")
with exp_cols[3]:
    st.markdown("**Frequency**")
with exp_cols[4]:
    st.markdown("**Action**")

updated_expenses = []
for i, exp in enumerate(st.session_state.expenses):
    c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
    with c1:
        cat = st.selectbox(
            "Category",
            categories,
            index=categories.index(exp["category"])
            if exp["category"] in categories
            else 0,
            key=f"exp_cat_{i}",
            label_visibility="collapsed",
        )
    with c2:
        ename = st.text_input(
            "Name",
            value=exp["name"],
            key=f"exp_name_{i}",
            label_visibility="collapsed",
        )
    with c3:
        eamt = st.number_input(
            "Amount",
            min_value=0.0,
            step=50.0,
            value=float(exp["amount"]),
            key=f"exp_amt_{i}",
            label_visibility="collapsed",
        )
    with c4:
        efreq = st.selectbox(
            "Frequency",
            list(freq_multipliers.keys()),
            index=list(freq_multipliers.keys()).index(exp["frequency"]),
            key=f"exp_freq_{i}",
            label_visibility="collapsed",
        )
    with c5:
        erem = st.button("❌", key=f"exp_rem_{i}")

    if not erem:
        monthly_equiv = eamt * freq_multipliers[efreq]
        updated_expenses.append(
            {
                "category": cat,
                "name": ename,
                "amount": eamt,
                "frequency": efreq,
                "monthly": monthly_equiv,
            }
        )

st.session_state.expenses = updated_expenses

if st.button("➕ Add Expense"):
    st.session_state.expenses.append(
        {
            "category": "Household Costs",
            "name": "New Expense",
            "amount": 100.0,
            "frequency": "Monthly",
        }
    )
    st.rerun()

# -------------------------------------------------------------------------
# 3. SUMMARY & BREAKDOWN
# -------------------------------------------------------------------------
st.divider()
st.header("3. Net Surplus & Category Breakdown")

if st.session_state.expenses:
    exp_df = pd.DataFrame(st.session_state.expenses)
    total_monthly_expenses = exp_df["monthly"].sum()

    # Category breakdown pivot
    cat_summary = (
        exp_df.groupby("category")["monthly"].sum().reindex(categories).fillna(0)
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Monthly Income", f"${total_monthly_income:,.2f}")
    with col2:
        st.metric("Total Monthly Expenses", f"${total_monthly_expenses:,.2f}")
    with col3:
        net_surplus = total_monthly_income - total_monthly_expenses
        st.metric(
            "Net Surplus Funds",
            f"${net_surplus:,.2f}",
            delta=f"${net_surplus:,.2f}",
        )

    st.subheader("Expense Breakdown by Category (Monthly)")
    cat_df = pd.DataFrame(
        {
            "Category": cat_summary.index,
            "Monthly Cost ($)": cat_summary.values,
            "% of Total Expenses": (
                (cat_summary.values / total_monthly_expenses * 100)
                if total_monthly_expenses > 0
                else 0
            ),
        }
    )
    cat_df["Monthly Cost ($)"] = cat_df["Monthly Cost ($)"].map("${:,.2f}".format)
    cat_df["% of Total Expenses"] = cat_df["% of Total Expenses"].map("{:.1f}%".format)
    st.table(cat_df)

    st.subheader("Detailed Expense Items")
    display_df = exp_df[["category", "name", "amount", "frequency", "monthly"]].copy()
    display_df.columns = [
        "Category",
        "Expense Item",
        "Amount",
        "Frequency",
        "Monthly Equivalent",
    ]
    display_df["Amount"] = display_df["Amount"].map("${:,.2f}".format)
    display_df["Monthly Equivalent"] = display_df["Monthly Equivalent"].map(
        "${:,.2f}".format
    )
    st.dataframe(display_df, use_container_width=True)
else:
    st.info("Add some expenses above to view the complete breakdown.")
