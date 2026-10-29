import copy
import io
import uuid
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Safe import for reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    REPORTLAB_AVAILABLE = False

st.set_page_config(
    page_title="Dynamic Income & Expense Analyzer",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Dynamic Income & Expense Analyzer")
st.markdown(
    "Dynamically manage income streams, categorized expenses, and debt/loan "
    "amortizations with auto-calculated payments and velocity banking simulations."
)

# -------------------------------------------------------------------------
# CATEGORY GUIDELINES / HELPER DICTIONARY
# -------------------------------------------------------------------------
category_help = {
    "House Hold Expenses": (
        "Includes property rates, ongoing home maintenance, repairs, body "
        "corporate fees, etc."
    ),
    "Vehicle Expenses": (
        "Vehicle insurances, fuel, Warrant of fitness (WOF), "
        "Registration/Licencing, Tires, and scheduled "
        "servicing/maintenance, Unplanned Repairs."
    ),
    "Living Expenses": (
        "Includes supermarket groceries, power/Electricity, gas, internet, "
        "Mobile Phone, & recurring household subscriptions (Netflix, Spotify, "
        "etc.)."
    ),
    "Insurances": "Life, Loss of Income, Contents, House Cover etc.",
}

# -------------------------------------------------------------------------
# SIDEBAR: VELOCITY BANKING & LOC SETTINGS
# -------------------------------------------------------------------------
st.sidebar.header("⚡ Line of Credit (LOC) Settings")
loc_limit = st.sidebar.number_input(
    "LOC Total Limit ($)", value=200000.0, step=5000.0
)
loc_interest_rate = (
    st.sidebar.number_input(
        "LOC Annual Interest Rate (%)", value=6.2, step=0.1
    )
    / 100.0
)
loc_current_balance = st.sidebar.number_input(
    "Current LOC Balance ($)", value=137000.0, step=1000.0
)
max_chunk_ratio = (
    st.sidebar.slider("Max % of LOC Limit to use for a Chunk", 20, 90, 90)
    / 100.0
)
safety_buffer = st.sidebar.number_input(
    "Safety Buffer / Emergency Reserve ($)", value=1000.0, step=100.0
)

st.sidebar.header("🎯 Priority Strategy Selection")
strategy_mode = st.sidebar.selectbox(
    "Select Strategy Option",
    [
        "Auto-Select Best Strategy (Compare All)",
        "Highest Interest First (Avalanche)",
        "Lowest Balance First (Snowball)",
    ],
)

st.sidebar.divider()

# -------------------------------------------------------------------------
# GLOBAL ACTIONS (Clear Amounts, Full Reset)
# -------------------------------------------------------------------------
col_act1, col_act2, col_act3 = st.columns([1.5, 1.5, 4])

def clear_amounts():
    """Zeroes out all numeric amount inputs across session state and lists."""
    for key in list(st.session_state.keys()):
        if key.startswith("inc_amt_") or key.startswith("exp_amt_"):
            st.session_state[key] = 0.0
        elif key.startswith("loan_bal_") or key.startswith("loan_rate_"):
            st.session_state[key] = 0.0
    if "incomes" in st.session_state:
        for item in st.session_state.incomes:
            item["amount"] = 0.0
    if "expenses" in st.session_state:
        for item in st.session_state.expenses:
            item["amount"] = 0.0
    if "loans" in st.session_state:
        for item in st.session_state.loans:
            item["balance"] = 0.0
            item["rate"] = 0.0

def reset_form():
    """Completely resets all session state keys."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

with col_act1:
    st.button("🧹 Clear / Zero Amounts", on_click=clear_amounts, use_container_width=True)

with col_act2:
    if st.button("🔄 Reset All Data", use_container_width=True):
        reset_form()
        st.rerun()

# -------------------------------------------------------------------------
# PDF GENERATION FUNCTION
# -------------------------------------------------------------------------
def create_pdf(incomes, expenses, loans, summary_metrics, cat_summary_df, loan_total_monthly, lifetime_loan_summary):
    if not REPORTLAB_AVAILABLE:
        return None
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=10,
        spaceAfter=6,
    )
    normal_style = styles["Normal"]

    elements.append(Paragraph("VortexCoach Income & Expense Report", title_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("1. Financial Summary", heading_style))
    summary_data = [
        ["Metric", "Monthly Value"],
        ["Total Monthly Income", f"${summary_metrics['income']:,.2f}"],
        ["Total Monthly Expenses", f"${summary_metrics['expenses']:,.2f}"],
        ["Total Monthly Debt/Loans", f"${loan_total_monthly:,.2f}"],
        ["Net Surplus Funds", f"${summary_metrics['surplus']:,.2f}"],
        ["Total Principal Borrowed", f"${lifetime_loan_summary['total_principal']:,.2f}"],
        ["Total Lifetime Interest", f"${lifetime_loan_summary['total_interest']:,.2f}"],
        ["Total Lifetime Payments", f"${lifetime_loan_summary['total_payments']:,.2f}"],
    ]
    t_summary = Table(summary_data, colWidths=[250, 250])
    t_summary.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ])
    )
    elements.append(t_summary)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("2. Net Income Streams", heading_style))
    inc_data = [["Source Name", "Amount", "Frequency", "Monthly Equivalent"]]
    for inc in incomes:
        inc_data.append([
            inc["name"],
            f"${inc['amount']:,.2f}",
            inc["frequency"],
            f"${inc['monthly']:,.2f}",
        ])
    t_inc = Table(inc_data, colWidths=[200, 100, 100, 100])
    t_inc.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#059669")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(t_inc)
    elements.append(Spacer(1, 15))

    if loans:
        elements.append(Paragraph("3. Debts & Loans Amortization Breakdown", heading_style))
        loan_data = [[
            "Loan Name", "Balance", "Rate (%)", "Type", 
            "Term (Yrs)", "Monthly Pmt", "Principal", "Interest"
        ]]
        for l in loans:
            loan_data.append([
                l["name"],
                f"${l['balance']:,.2f}",
                f"{l['rate']:.2f}%",
                l["type"],
                str(l["term"]),
                f"${l['monthly_payment']:,.2f}",
                f"${l['monthly_principal']:,.2f}",
                f"${l['monthly_interest']:,.2f}",
            ])
        t_loan = Table(loan_data, colWidths=[110, 60, 50, 45, 55, 65, 60, 55])
        t_loan.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7C3AED")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elements.append(t_loan)
        elements.append(Spacer(1, 15))

    elements.append(Paragraph("4. Expense Breakdown by Category", heading_style))
    cat_data = [["Category", "Monthly Cost", "% of Total Expenses"]]
    for _, row in cat_summary_df.iterrows():
        cat_data.append([
            row["Category"],
            str(row["Monthly Cost ($)"]),
            str(row["% of Total Expenses"])
        ])
    t_cat = Table(cat_data, colWidths=[200, 150, 150])
    t_cat.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D97706")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(t_cat)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("5. Detailed Expense Items", heading_style))
    exp_data = [["Category", "Expense Name", "Amount", "Frequency", "Monthly Equiv."]]
    for exp in expenses:
        exp_data.append([
            exp["category"],
            Paragraph(exp["name"], normal_style),
            f"${exp['amount']:,.2f}",
            exp["frequency"],
            f"${exp['monthly']:,.2f}",
        ])
    t_exp = Table(exp_data, colWidths=[110, 190, 65, 65, 70])
    t_exp.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4B5563")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(t_exp)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------------------------------
# 1. NET INCOMES FROM MULTIPLE PARTIES
# -------------------------------------------------------------------------
st.header("1. Net Income Streams")
st.markdown(
    "Add multiple net income sources (e.g., Party 1 Salary, Party 2 Side Hustle) "
    "and set their payment frequency."
)

if "incomes" not in st.session_state:
    st.session_state.incomes = [
        {"name": "Party 1 - Primary Salary", "amount": 7000.0, "frequency": "Monthly"},
        {"name": "Party 2 - Salary", "amount": 5000.0, "frequency": "Monthly"},
    ]

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
        name = st.text_input("Name", value=inc["name"], key=f"inc_name_{i}", label_visibility="collapsed")
    with c2:
        amount = st.number_input("Amount", min_value=0.0, step=100.0, value=float(inc["amount"]), key=f"inc_amt_{i}", label_visibility="collapsed")
    with c3:
        freq = st.selectbox("Frequency", list(freq_multipliers.keys()), index=list(freq_multipliers.keys()).index(inc["frequency"]), key=f"inc_freq_{i}", label_visibility="collapsed")
    with c4:
        remove = st.button("❌", key=f"inc_rem_{i}")
    
    if not remove:
        monthly_equiv = amount * freq_multipliers[freq]
        updated_incomes.append({
            "name": name,
            "amount": amount,
            "frequency": freq,
            "monthly": monthly_equiv,
        })

st.session_state.incomes = updated_incomes

if st.button("➕ Add Income Stream"):
    st.session_state.incomes.append({"name": "New Income", "amount": 0.0, "frequency": "Monthly"})
    st.rerun()

total_monthly_income = sum(item["monthly"] for item in st.session_state.incomes)
st.metric("Total Monthly Net Income", f"${total_monthly_income:,.2f}")
st.divider()

# -------------------------------------------------------------------------
# 2. DEBTS & LOANS (Amortization Calculator)
# -------------------------------------------------------------------------
st.header("2. Debts & Loans Amortization")
st.markdown(
    "Add liabilities, select repayment type (P&I or INT), set term and rate "
    "to auto-calculate monthly payments, principal, and interest splits."
)

if "loans" not in st.session_state:
    st.session_state.loans = [{
        "name": "Home Mortgage",
        "balance": 120000.0,
        "rate": 6.5,
        "type": "P&I",
        "term": 13,
        "fixed_lock_months": 12,
    }, {
        "name": "Green Loan",
        "balance": 27600.0,
        "rate": 1.0,
        "type": "P&I",
        "term": 13,
        "fixed_lock_months": 36,
    }
    ]

loan_cols = st.columns([2.2, 1.5, 1.0, 1.0, 1.0, 1.2, 1.2, 1.0, 1.0, 0.6])
with loan_cols[0]:
    st.markdown("**Loan Name**")
with loan_cols[1]:
    st.markdown("**Balance ($)**")
with loan_cols[2]:
    st.markdown("**Rate (%)**")
with loan_cols[3]:
    st.markdown("**Type**")
with loan_cols[4]:
    st.markdown("**Term (Yrs)**")
with loan_cols[5]:
    st.markdown("**Fixed Lock**")
with loan_cols[6]:
    st.markdown("**Monthly Pmt**")
with loan_cols[7]:
    st.markdown("**Principal**")
with loan_cols[8]:
    st.markdown("**Interest**")
with loan_cols[9]:
    st.markdown("**Action**")

updated_loans = []
total_loan_monthly = 0.0
total_loan_principal = 0.0
total_loan_interest = 0.0
loan_types = ["P&I", "INT"]
lock_options = [0, 12, 24, 36, 48, 60]

for i, loan in enumerate(st.session_state.loans):
    lc1, lc2, lc3, lc4, lc5, lc6, lc7, lc8, lc9, lc10 = st.columns([2.2, 1.5, 1.0, 1.0, 1.0, 1.2, 1.2, 1.0, 1.0, 0.6])
    with lc1:
        lname = st.text_input("Loan Name", value=loan["name"], key=f"loan_name_{i}", label_visibility="collapsed")
    with lc2:
        lbal = st.number_input("Balance", min_value=0.0, step=1000.0, value=float(loan["balance"]), key=f"loan_bal_{i}", label_visibility="collapsed")
    with lc3:
        lrate = st.number_input("Rate (%)", min_value=0.0, step=0.1, value=float(loan["rate"]), key=f"loan_rate_{i}", label_visibility="collapsed")
    with lc4:
        ltype = st.selectbox("Type", loan_types, index=loan_types.index(loan["type"]) if loan["type"] in loan_types else 0, key=f"loan_type_{i}", label_visibility="collapsed")
    with lc5:
        lterm = st.number_input("Term (Yrs)", min_value=1, max_value=50, step=1, value=int(loan["term"]), key=f"loan_term_{i}", label_visibility="collapsed")
    with lc6:
        current_lock = loan.get("fixed_lock_months", 0)
        llock = st.selectbox("Lock", lock_options, index=lock_options.index(current_lock) if current_lock in lock_options else 0, key=f"loan_lock_{i}", label_visibility="collapsed")

    # Calculations
    monthly_rate = (lrate / 100.0) / 12.0
    total_months = int(lterm * 12)
    monthly_interest = lbal * monthly_rate

    if ltype == "P&I":
        if monthly_rate > 0 and total_months > 0:
            monthly_payment = (
                lbal * (monthly_rate * (1 + monthly_rate) ** total_months) /
                ((1 + monthly_rate) ** total_months - 1)
            )
        else:
            monthly_payment = lbal / total_months if total_months > 0 else 0.0
        monthly_principal = monthly_payment - monthly_interest
    else:  # Interest Only
        monthly_payment = monthly_interest
        monthly_principal = 0.0

    with lc7:
        st.markdown(f"**${monthly_payment:,.2f}**")
    with lc8:
        st.markdown(f"${monthly_principal:,.2f}")
    with lc9:
        st.markdown(f"${monthly_interest:,.2f}")
    with lc10:
        lrem = st.button("❌", key=f"loan_rem_{i}")

    if not lrem:
        total_loan_monthly += monthly_payment
        total_loan_principal += monthly_principal
        total_loan_interest += monthly_interest
        updated_loans.append({
            "name": lname,
            "balance": lbal,
            "rate": lrate,
            "type": ltype,
            "term": lterm,
            "fixed_lock_months": llock,
            "monthly_payment": monthly_payment,
            "monthly_principal": monthly_principal,
            "monthly_interest": monthly_interest,
        })

st.session_state.loans = updated_loans

if st.button("➕ Add Loan / Debt"):
    st.session_state.loans.append({"name": "New Loan", "balance": 10000.0, "rate": 5.0, "type": "P&I", "term": 5, "fixed_lock_months": 0})
    st.rerun()

st.metric("Total Monthly Debt Payments", f"${total_loan_monthly:,.2f}")
st.divider()

# -------------------------------------------------------------------------
# 3. EXPENSES BY CATEGORY
# -------------------------------------------------------------------------

st.markdown("### 3. Categorized Expenses - <span style='color: red; text-decoration: underline; font-weight: bold;'>Not Including Mortgages or loan repayments</span>",
    unsafe_allow_html=True,
)

categories = [
    "House Hold Expenses",
    "Vehicle Expenses",
    "Living Expenses",
    "Insurances",
]

with st.expander("ℹ️ Click here for Category Descriptions & Examples"):
    for cat_name, description in category_help.items():
        st.markdown(f"**{cat_name}:** {description}")

if "expenses" not in st.session_state:
    st.session_state.expenses = [
        {
            "category": "House Hold Expenses",
            "name": "House Insurance, Council Rates, Regional Rates, Water Rates, Maintenance Costs etc",
            "amount": 400.0,
            "frequency": "Monthly",
        },
        {
            "category": "Vehicle Expenses",
            "name": "Insurances, Fuel, Registration, Tires, Warrant Of Fitness, Maintenance/Servicing",
            "amount": 600.0,
            "frequency": "Monthly",
        },
        {
            "category": "Living Expenses",
            "name": "Food, Bakery, Entertainment, Personal care, Medical Costs, Power, Gas, Internet Netflix etc",
            "amount": 1500.0,
            "frequency": "Monthly",
        },
        {
            "category": "Insurances",
            "name": "Life, Medical, Contents, Loss of Income etc",
            "amount": 3000.0,
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
        cat = st.selectbox("Category", categories, index=categories.index(exp["category"]) if exp["category"] in categories else 0, key=f"exp_cat_{i}", label_visibility="collapsed")
    with c2:
        ename = st.text_input("Name", value=exp["name"], key=f"exp_name_{i}", label_visibility="collapsed")
    with c3:
        eamt = st.number_input("Amount", min_value=0.0, step=50.0, value=float(exp["amount"]), key=f"exp_amt_{i}", label_visibility="collapsed")
    with c4:
        efreq = st.selectbox("Frequency", list(freq_multipliers.keys()), index=list(freq_multipliers.keys()).index(exp["frequency"]), key=f"exp_freq_{i}", label_visibility="collapsed")
    with c5:
        erem = st.button("❌", key=f"exp_rem_{i}")

    if not erem:
        monthly_equiv = eamt * freq_multipliers[efreq]
        updated_expenses.append({
            "category": cat,
            "name": ename,
            "amount": eamt,
            "frequency": efreq,
            "monthly": monthly_equiv,
        })

st.session_state.expenses = updated_expenses

if st.button("➕ Add Expense Item"):
    st.session_state.expenses.append({
        "category": "Living Expenses",
        "name": "New Expense",
        "amount": 0.0,
        "frequency": "Monthly",
    })
    st.rerun()

total_monthly_expenses = sum(item["monthly"] for item in st.session_state.expenses)
st.metric("Total Monthly Expenses", f"${total_monthly_expenses:,.2f}")
st.divider()

# -------------------------------------------------------------------------
# 4. SUMMARY & EXPORT
# -------------------------------------------------------------------------
st.header("4. Summary & Reports")

net_surplus = total_monthly_income - (total_monthly_expenses + total_loan_monthly)

# Calculate lifetime loan commitments
total_principal_borrowed = 0.0
total_life_interest = 0.0
total_life_payments = 0.0

for loan in st.session_state.loans:
    bal = float(loan["balance"])
    r_rate = float(loan["rate"]) / 100.0
    t_yrs = int(loan["term"])
    l_type = loan["type"]
    
    total_principal_borrowed += bal
    m_rate = r_rate / 12.0
    t_months = t_yrs * 12
    
    if l_type == "INT":
        m_pmt = bal * m_rate
        l_interest = m_pmt * t_months
        total_life_interest += l_interest
        total_life_payments += bal + l_interest
    else:
        if m_rate > 0 and t_months > 0:
            m_pmt = bal * (m_rate * (1 + m_rate) ** t_months) / ((1 + m_rate) ** t_months - 1)
        else:
            m_pmt = bal / t_months if t_months > 0 else 0.0
        l_pmts = m_pmt * t_months
        total_life_payments += l_pmts
        total_life_interest += l_pmts - bal

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
col_s1.metric("Total Income", f"${total_monthly_income:,.2f}")
col_s2.metric("Total Expenses", f"${total_monthly_expenses:,.2f}")
col_s3.metric("Total Debt Pmt", f"${total_loan_monthly:,.2f}")
col_s4.metric("Net Surplus", f"${net_surplus:,.2f}", delta=f"${net_surplus:,.2f}")

st.markdown("### Lifetime Loan Commitments")
col_l1, col_l2, col_l3 = st.columns(3)
col_l1.metric("Total Principal Borrowed", f"${total_principal_borrowed:,.2f}")
col_l2.metric("Total Life Interest", f"${total_life_interest:,.2f}")
col_l3.metric("Total Lifetime Payments", f"${total_life_payments:,.2f}")

cat_totals = {}
for cat in categories:
    cat_totals[cat] = sum(e["monthly"] for e in st.session_state.expenses if e["category"] == cat)

cat_df = pd.DataFrame(list(cat_totals.items()), columns=["Category", "Monthly Cost ($)"])
cat_df["Monthly Cost ($)"] = cat_df["Monthly Cost ($)"].apply(lambda x: f"${x:,.2f}")
if total_monthly_expenses > 0:
    cat_df["% of Total Expenses"] = [
        f"{(cat_totals[c] / total_monthly_expenses) * 100:.1f}%" for c in cat_df["Category"]
    ]
else:
    cat_df["% of Total Expenses"] = "0.0%"

st.subheader("Expense Breakdown by Category")
st.dataframe(cat_df, use_container_width=True)

st.subheader("Export Configuration")

if REPORTLAB_AVAILABLE:
    summary_metrics = {
        "income": total_monthly_income,
        "expenses": total_monthly_expenses,
        "surplus": net_surplus,
    }
    lifetime_loan_summary = {
        "total_principal": total_principal_borrowed,
        "total_interest": total_life_interest,
        "total_payments": total_life_payments,
    }
    pdf_buffer = create_pdf(
        st.session_state.incomes,
        st.session_state.expenses,
        st.session_state.loans,
        summary_metrics,
        cat_df,
        total_loan_monthly,
        lifetime_loan_summary,
    )
    if pdf_buffer:
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_buffer,
            file_name="financial_report.pdf",
            mime="application/pdf",
        )
else:
    st.info("ReportLab is not installed; PDF report generation is currently disabled.")

st.divider()

# -------------------------------------------------------------------------
# 5. VORTEX BANKING & DEBT PAYOFF SIMULATION ENGINE
# -------------------------------------------------------------------------
st.header("⚡ Vortex Coach Rapid Debt Payoff Strategy Simulation")
st.markdown(
    "Run simulations using your live debt tables, cash flow surplus, and Line of Credit (LOC) settings."
)

def sort_debts(debts, strategy):
    if strategy == "Highest Interest First (Avalanche)":
        return sorted(debts, key=lambda x: x["rate"], reverse=True)
    elif strategy == "Lowest Balance First (Snowball)":
        return sorted(debts, key=lambda x: x["balance"])
    return debts

def run_velocity_simulation(
    debts_input,
    income,
    expenses,
    loc_limit,
    loc_rate,
    loc_start_bal,
    max_chunk_pct,
    buffer,
    strategy,
):
    debts = copy.deepcopy(debts_input)
    for d in debts:
        if d["rate"] > 1.0:
            d["rate"] = d["rate"] / 100.0

    loc_bal = loc_start_bal
    max_chunk_allowed = loc_limit * max_chunk_pct

    month = 0
    max_months = 360
    logs = []

    total_interest_debts = 0.0
    total_interest_loc = 0.0

    while month < max_months:
        month += 1

        active_debts = [d for d in debts if d["balance"] > 0.01]
        if not active_debts and loc_bal <= 0.01:
            break

        total_min_payments = sum(d.get("monthly_payment", d.get("min_pay", 0)) for d in active_debts)
        monthly_cash_flow = income - expenses - total_min_payments

        if monthly_cash_flow < 0:
            st.error(
                f"Month {month}: Expenses and Minimum Payments exceed Monthly Income!"
                " Positive cash flow is required."
            )
            return None

        for d in active_debts:
            lock_months = d.get("fixed_lock_months", 0)
            if month == lock_months and d["balance"] > 0.01:
                rem_bal = d["balance"]
                d["balance"] = 0
                loc_bal += rem_bal

        unlocked_debts = [
            d
            for d in active_debts
            if d["balance"] > 0.01 and month > d.get("fixed_lock_months", 0)
        ]
        unlocked_debts = sort_debts(unlocked_debts, strategy)

        loc_available = max_chunk_allowed - loc_bal
        if loc_available > 500 and unlocked_debts:
            target_debt = unlocked_debts[0]
            chunk_amount = min(target_debt["balance"], loc_available)

            if chunk_amount > 0:
                target_debt["balance"] -= chunk_amount
                loc_bal += chunk_amount

        loc_interest_month = (loc_bal * loc_rate) / 12.0
        total_interest_loc += loc_interest_month
        loc_bal += loc_interest_month

        paydown_to_loc = min(monthly_cash_flow, loc_bal)
        loc_bal -= paydown_to_loc
        remaining_cash_flow = monthly_cash_flow - paydown_to_loc

        for d in active_debts:
            monthly_interest = (d["balance"] * d["rate"]) / 12.0
            total_interest_debts += monthly_interest
            d["balance"] += monthly_interest

            min_p = d.get("monthly_payment", d.get("min_pay", 0))
            pay = min(min_p, d["balance"])
            d["balance"] -= pay

            if (
                remaining_cash_flow > 0
                and unlocked_debts
                and d == unlocked_debts[0]
            ):
                extra = min(remaining_cash_flow, d["balance"])
                d["balance"] -= extra
                remaining_cash_flow -= extra

        total_debt_bal = sum(d["balance"] for d in debts)

        # Record individual loan balances for the Vortex method tracking chart
        loan_snapshot = {f"Loan_{d['name']}": round(d["balance"], 2) for d in debts}

        log_entry = {
            "Month": month,
            "Total Debt Balance": round(total_debt_bal, 2),
            "LOC Balance": round(loc_bal, 2),
            "Combined Balance": round(total_debt_bal + loc_bal, 2),
            "Monthly Cash Flow": round(monthly_cash_flow, 2),
            "Interest Paid (LOC)": round(total_interest_loc, 2),
            "Interest Paid (Debts)": round(total_interest_debts, 2),
            "Total Interest Paid": round(
                total_interest_loc + total_interest_debts, 2
            ),
        }
        log_entry.update(loan_snapshot)
        logs.append(log_entry)

    return pd.DataFrame(logs)

if st.button("🚀 Run Payoff Simulation", type="primary"):
    if "loans" not in st.session_state or not st.session_state.loans:
        st.warning("Please add at least one debt or loan item.")
    else:
        strategies_to_test = [
            "Highest Interest First (Avalanche)",
            "Lowest Balance First (Snowball)",
        ]

        all_results = {}
        summary_data = []

        for strat in strategies_to_test:
            res_df = run_velocity_simulation(
                st.session_state.loans,
                total_monthly_income,
                total_monthly_expenses,
                loc_limit,
                loc_interest_rate,
                loc_current_balance,
                max_chunk_ratio,
                safety_buffer,
                strat,
            )
            if res_df is not None and not res_df.empty:
                all_results[strat] = res_df
                summary_data.append({
                    "Strategy": strat,
                    "Months to Debt-Free": res_df["Month"].max(),
                    "Total Interest Paid ($)": res_df["Total Interest Paid"].max(),
                    "Final Monthly Cash Flow ($)": res_df["Monthly Cash Flow"].iloc[-1],
                })

        summary_df = pd.DataFrame(summary_data)

        if not summary_df.empty:
            best_row = summary_df.loc[summary_df["Total Interest Paid ($)"].idxmin()]
            best_strategy = best_row["Strategy"]

            st.success(
                f"🏆 **Optimal Strategy Auto-Selected:** {best_strategy} "
                f"(Total Interest: ${best_row['Total Interest Paid ($)']:,.2f} | "
                f"Timeline: {best_row['Months to Debt-Free']} Months)"
            )

            st.dataframe(
                summary_df.style.format({
                    "Total Interest Paid ($)": "${:,.2f}",
                    "Final Monthly Cash Flow ($)": "${:,.2f}",
                }),
                use_container_width=True,
            )

            active_strat = (
                best_strategy
                if strategy_mode == "Auto-Select Best Strategy (Compare All)"
                else strategy_mode
            )
            results_df = all_results.get(
                active_strat, list(all_results.values())[0]
            )

            # Save simulation results into session state for secondary chart button access
            st.session_state.simulation_results = results_df
            st.session_state.active_strategy_name = active_strat

            total_months = results_df["Month"].max()
            total_interest = results_df["Total Interest Paid"].max()

            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Debt-Free Timeline",
                f"{total_months} Months",
                f"{round(total_months/12, 1)} Years",
            )
            m2.metric("Total Interest Paid", f"${total_interest:,.2f}")
            m3.metric(
                "Final Monthly Cash Flow",
                f"${results_df['Monthly Cash Flow'].iloc[-1]:,.2f}",
            )

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=results_df["Month"],
                    y=results_df["Total Debt Balance"],
                    name="Traditional Debts Balance",
                    line=dict(color="orange", width=2),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=results_df["Month"],
                    y=results_df["LOC Balance"],
                    name="Line of Credit Balance",
                    line=dict(color="firebrick", width=2, dash="dash"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=results_df["Month"],
                    y=results_df["Combined Balance"],
                    name="Total Combined Liability",
                    line=dict(color="green", width=3),
                )
            )

            fig.update_layout(
                title=f"Debt Paydown & LOC Chunking Trajectory ({active_strat})",
                xaxis_title="Months",
                yaxis_title="Balance ($)",
                hovermode="x unified",
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("🔍 View Month-by-Month Amortization Schedule"):
                st.dataframe(results_df, use_container_width=True)

# -------------------------------------------------------------------------
# 6. VORTEX METHOD: INDIVIDUAL LOAN P&I RAPID PAYDOWN TRACKING
# -------------------------------------------------------------------------
if "simulation_results" in st.session_state and st.session_state.simulation_results is not None:
    st.divider()
    st.subheader("🌀 Vortex Method: Individual Loan Paydown Tracking (P&I)")
    st.markdown(
        "Compare how each individual loan and your Line of Credit amortize down simultaneously "
        "under the rapid paydown Vortex strategy."
    )

    if st.button("📊 Generate Vortex Individual Loan Comparison Chart"):
        res_df = st.session_state.simulation_results
        strat_name = st.session_state.get("active_strategy_name", "Selected Strategy")

        fig_vortex = go.Figure()

        # Plot individual loan curves stored during simulation
        for col in res_df.columns:
            if col.startswith("Loan_"):
                loan_label = col.replace("Loan_", "")
                fig_vortex.add_trace(
                    go.Scatter(
                        x=res_df["Month"],
                        y=res_df[col],
                        name=f"{loan_label} Balance",
                        mode="lines",
                        line=dict(width=2),
                    )
                )

        # Plot Line of Credit curve
        if "LOC Balance" in res_df.columns:
            fig_vortex.add_trace(
                go.Scatter(
                    x=res_df["Month"],
                    y=res_df["LOC Balance"],
                    name="Line of Credit (LOC) Balance",
                    mode="lines",
                    line=dict(color="firebrick", width=2, dash="dash"),
                )
            )

        fig_vortex.update_layout(
            title=f"Vortex Rapid Paydown Breakdown by Loan ({strat_name})",
            xaxis_title="Months",
            yaxis_title="Principal Balance ($)",
            hovermode="x unified",
            template="plotly_white",
        )
        st.plotly_chart(fig_vortex, use_container_width=True)
