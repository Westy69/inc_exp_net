import io
import pandas as pd
import streamlit as st

# Safe import for reportlab
try:
  from reportlab.lib import colors
  from reportlab.lib.pagesizes import letter
  from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
  from reportlab.platypus import (
      Paragraph,
      SimpleDocTemplate,
      Spacer,
      Table,
      TableStyle,
  )

  REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
  REPORTLAB_AVAILABLE = False

st.set_page_config(
    page_title="Dynamic Income & Expense Analyzer", page_icon="💰", layout="wide"
)

st.title("💰 Dynamic Income & Expense Analyzer")
st.markdown(
    "Dynamically manage income streams, categorized expenses, and debt/loan"
    " amortizations with auto-calculated payments."
)

# -------------------------------------------------------------------------
# CATEGORY GUIDELINES / HELPER DICTIONARY
# -------------------------------------------------------------------------
category_help = {
    "House Hold Expenses": (
        "Includes property rates, Water Rates, Regional Rates, Ongoing home"
        " maintenance, repairs, body corporate fees, etc."
    ),
    "Vehicle Expenses": (
        "Vehicle Insurances, fuel," warrant of fitness (WOF), registration, tires, and scheduled"
        " servicing/maintenance."
    ),
    "Household Costs": (
        "Includes Supermarket groceries, power/electricity, gas, internet, mobile"
        "phone plans, and recurring household subscriptions (Netflix, Spotify, etc.)." 
        "Entertainment, lifestyle activities, takeaways, bakery food,"
        " coffees, restaurant dining, personal care, and clothing"
    
    ),
    "Insurances": (
        "Life, House, Contents etc."
    ),
}

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

# -------------------------------------------------------------------------
# PDF GENERATION FUNCTION
# -------------------------------------------------------------------------
def create_pdf(
    incomes, expenses, loans, summary_metrics, cat_summary_df, loan_total_monthly
):
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

  # Title
  elements.append(Paragraph("Dynamic Income & Expense Report", title_style))
  elements.append(Spacer(1, 10))

  # Summary Table
  elements.append(Paragraph("1. Financial Summary", heading_style))
  summary_data = [
      ["Metric", "Monthly Value"],
      ["Total Monthly Income", f"${summary_metrics['income']:,.2f}"],
      ["Total Monthly Expenses", f"${summary_metrics['expenses']:,.2f}"],
      ["Total Monthly Debt/Loans", f"${loan_total_monthly:,.2f}"],
      ["Net Surplus Funds", f"${summary_metrics['surplus']:,.2f}"],
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

  # Income Table
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

  # Loans & Debt Table
  if loans:
    elements.append(
        Paragraph("3. Debts & Loans Amortization Breakdown", heading_style)
    )
    loan_data = [[
        "Loan Name",
        "Balance",
        "Rate (%)",
        "Type",
        "Term (Yrs)",
        "Monthly Pmt",
        "Principal",
        "Interest",
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

  # Category Breakdown
  elements.append(Paragraph("4. Expense Breakdown by Category", heading_style))
  cat_data = [["Category", "Monthly Cost", "% of Total Expenses"]]
  for _, row in cat_summary_df.iterrows():
    cat_data.append(
        [row["Category"], row["Monthly Cost ($)"], row["% of Total Expenses"]]
    )
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

  # Detailed Expenses
  elements.append(Paragraph("5. Detailed Expense Items", heading_style))
  exp_data = [
      ["Category", "Expense Name", "Amount", "Frequency", "Monthly Equiv."]
  ]
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
    "Add multiple net income sources (e.g., Party 1 Salary, Party 2 Side Hustle)"
    " and set their payment frequency."
)

if "incomes" not in st.session_state:
  st.session_state.incomes = [
      {"name": "Party 1 - Primary Salary", "amount": 6000.0, "frequency": "Monthly"},
      {"name": "Party 2 - Salary", "amount": 3000.0, "frequency": "Monthly"},
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
    name = st.text_input(
        "Name",
        value=inc["name"],
        key=f"inc_name_{i}",
        label_visibility="collapsed",
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
      {"name": "New Income", "amount": 0.0, "frequency": "Monthly"}
  )
  st.rerun()

total_monthly_income = sum(item["monthly"] for item in st.session_state.incomes)
st.metric("Total Monthly Net Income", f"${total_monthly_income:,.2f}")

st.divider()

# -------------------------------------------------------------------------
# 2. DEBTS & LOANS (Amortization Calculator)
# -------------------------------------------------------------------------
st.header("2. Debts & Loans Amortization")
st.markdown(
    "Add liabilities, select repayment type (P&I or INT), set term and rate"
    " to auto-calculate monthly payments, principal, and interest splits."
)

if "loans" not in st.session_state:
  st.session_state.loans = [{
      "name": "Home Mortgage",
      "balance": 400000.0,
      "rate": 6.5,
      "type": "P&I",
      "term": 25,
  }]

loan_cols = st.columns([2.5, 1.8, 1.2, 1.2, 1.2, 1.5, 1.2, 1.2, 0.8])
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
  st.markdown("**Monthly Pmt**")
with loan_cols[6]:
  st.markdown("**Principal**")
with loan_cols[7]:
  st.markdown("**Interest**")
with loan_cols[8]:
  st.markdown("**Action**")

updated_loans = []
total_loan_monthly = 0.0
total_loan_principal = 0.0
total_loan_interest = 0.0

loan_types = ["P&I", "INT"]

for i, loan in enumerate(st.session_state.loans):
  lc1, lc2, lc3, lc4, lc5, lc6, lc7, lc8, lc9 = st.columns(
      [2.5, 1.8, 1.2, 1.2, 1.2, 1.5, 1.2, 1.2, 0.8]
  )
  with lc1:
    lname = st.text_input(
        "Loan Name",
        value=loan["name"],
        key=f"loan_name_{i}",
        label_visibility="collapsed",
    )
  with lc2:
    lbal = st.number_input(
        "Balance",
        min_value=0.0,
        step=1000.0,
        value=float(loan["balance"]),
        key=f"loan_bal_{i}",
        label_visibility="collapsed",
    )
  with lc3:
    lrate = st.number_input(
        "Rate (%)",
        min_value=0.0,
        step=0.1,
        value=float(loan["rate"]),
        key=f"loan_rate_{i}",
        label_visibility="collapsed",
    )
  with lc4:
    ltype = st.selectbox(
        "Type",
        loan_types,
        index=loan_types.index(loan["type"])
        if loan["type"] in loan_types
        else 0,
        key=f"loan_type_{i}",
        label_visibility="collapsed",
    )
  with lc5:
    lterm = st.number_input(
        "Term (Yrs)",
        min_value=1,
        max_value=50,
        step=1,
        value=int(loan["term"]),
        key=f"loan_term_{i}",
        label_visibility="collapsed",
    )

  # Calculations
  monthly_rate = (lrate / 100.0) / 12.0
  total_months = int(lterm * 12)
  monthly_interest = lbal * monthly_rate

  if ltype == "P&I":
    if monthly_rate > 0 and total_months > 0:
      monthly_payment = (
          lbal
          * (monthly_rate * (1 + monthly_rate) ** total_months)
          / ((1 + monthly_rate) ** total_months - 1)
      )
    else:
      monthly_payment = lbal / total_months if total_months > 0 else 0.0
    monthly_principal = monthly_payment - monthly_interest
  else:  # Interest Only
    monthly_payment = monthly_interest
    monthly_principal = 0.0

  with lc6:
    st.markdown(f"**${monthly_payment:,.2f}**")
  with lc7:
    st.markdown(f"${monthly_principal:,.2f}")
  with lc8:
    st.markdown(f"${monthly_interest:,.2f}")

  with lc9:
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
        "monthly_payment": monthly_payment,
        "monthly_principal": monthly_principal,
        "monthly_interest": monthly_interest,
    })

st.session_state.loans = updated_loans

if st.button("➕ Add Loan / Debt"):
  st.session_state.loans.append({
      "name": "New Loan",
      "balance": 10000.0,
      "rate": 5.0,
      "type": "P&I",
      "term": 5,
  })
  st.rerun()

st.metric("Total Monthly Debt Payments", f"${total_loan_monthly:,.2f}")

st.divider()

# -------------------------------------------------------------------------
# 3. EXPENSES BY CATEGORY
# -------------------------------------------------------------------------
st.header("3. Categorized Expenses-Not Including Mortgages or loan repayments")
st.markdown(
    "Add recurring expenses across specified categories. Amounts are"
    " automatically normalized to a monthly equivalent."
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
          "name": "add your first expense here",
          "amount": 400.0,
          "frequency": "Monthly",
      },
      {
          "category": "Vehicle Expenses",
          "name": (
              "Add your first expense here"
          ),
          "amount": 600.0,
          "frequency": "Monthly",
      },
      {
          "category": "Living Expenses",
          "name": "Add your first expense here",
          "amount": 1500.0,
          "frequency": "Monthly",
      },
      {
          "category": "Insurances",
          "name": "Add your first expense here",
             
          ),
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
          "amount": 0.0,
          "frequency": "Monthly",
      }
  )
  st.rerun()

# -------------------------------------------------------------------------
# 4. SUMMARY & BREAKDOWN
# -------------------------------------------------------------------------
st.divider()
st.header("4. Net Surplus & Category Breakdown")

if st.session_state.expenses or st.session_state.incomes or st.session_state.loans:
  exp_df = (
      pd.DataFrame(st.session_state.expenses)
      if st.session_state.expenses
      else pd.DataFrame(columns=["category", "name", "amount", "frequency", "monthly"])
  )
  total_monthly_expenses = exp_df["monthly"].sum() if not exp_df.empty else 0.0
  total_all_expenses = total_monthly_expenses + total_loan_monthly

  cat_summary = (
      exp_df.groupby("category")["monthly"].sum().reindex(categories).fillna(0)
      if not exp_df.empty
      else pd.Series(0, index=categories)
  )

  col1, col2, col3, col4 = st.columns(4)
  with col1:
    st.metric("Total Monthly Income", f"${total_monthly_income:,.2f}")
  with col2:
    st.metric("Total Monthly Expenses", f"${total_all_expenses:,.2f}")
  with col3:
    st.metric("Total Monthly Debt", f"${total_loan_monthly:,.2f}")
  with col4:
    net_surplus = total_monthly_income - total_all_expenses
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
              (cat_summary.values / total_all_expenses * 100)
              if total_all_expenses > 0
              else 0
          ),
      }
  )
  cat_df_display = cat_df.copy()
  cat_df_display["Monthly Cost ($)"] = cat_df_display["Monthly Cost ($)"].map(
      "${:,.2f}".format
  )
  cat_df_display["% of Total Expenses"] = cat_df_display[
      "% of Total Expenses"
  ].map("{:.1f}%".format)
  st.table(cat_df_display)

  if st.session_state.loans:
    st.subheader("Loans & Amortization Breakdown")
    loan_display_df = pd.DataFrame(st.session_state.loans)
    loan_display_df.columns = [
        "Loan Name",
        "Balance",
        "Rate (%)",
        "Type",
        "Term (Yrs)",
        "Monthly Payment",
        "Principal Component",
        "Interest Component",
    ]
    for col in [
        "Balance",
        "Monthly Payment",
        "Principal Component",
        "Interest Component",
    ]:
      loan_display_df[col] = loan_display_df[col].map("${:,.2f}".format)
    loan_display_df["Rate (%)"] = loan_display_df["Rate (%)"].map(
        "{:.2f}%".format
    )
    st.dataframe(loan_display_df, use_container_width=True)

  st.subheader("Detailed Expense Items")
  if not exp_df.empty:
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

  # -------------------------------------------------------------------------
  # EXPORT OPTIONS (CSV & Native PDF Download)
  # -------------------------------------------------------------------------
  st.divider()
  st.subheader("Export Options")

  col_csv, col_pdf = st.columns(2)

  with col_csv:
    csv_buffer = io.StringIO()
    csv_buffer.write("=== SUMMARY ===\n")
    csv_buffer.write(f"Total Monthly Income,{total_monthly_income}\n")
    csv_buffer.write(f"Total Monthly Expenses,{total_all_expenses}\n")
    csv_buffer.write(f"Total Monthly Debt,{total_loan_monthly}\n")
    csv_buffer.write(f"Net Surplus Funds,{net_surplus}\n\n")

    csv_buffer.write("=== INCOME STREAMS ===\n")
    inc_export_df = pd.DataFrame(st.session_state.incomes)
    if not inc_export_df.empty:
      inc_export_df.to_csv(csv_buffer, index=False)

    csv_buffer.write("\n=== LOANS & DEBTS ===\n")
    loan_export_df = pd.DataFrame(st.session_state.loans)
    if not loan_export_df.empty:
      loan_export_df.to_csv(csv_buffer, index=False)

    csv_buffer.write("\n=== EXPENSES ===\n")
    if not exp_df.empty:
      exp_df.to_csv(csv_buffer, index=False)

    st.download_button(
        label="📥 Download as CSV",
        data=csv_buffer.getvalue(),
        file_name="income_and_expense_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

  with col_pdf:
    if REPORTLAB_AVAILABLE:
      summary_metrics = {
          "income": total_monthly_income,
          "expenses": total_all_expenses,
          "surplus": net_surplus,
      }
      pdf_buffer = create_pdf(
          st.session_state.incomes,
          st.session_state.expenses,
          st.session_state.loans,
          summary_metrics,
          cat_df_display,
          total_loan_monthly,
      )
      st.download_button(
          label="📄 Download Report as PDF",
          data=pdf_buffer,
          file_name="income_and_expense_report.pdf",
          mime="application/pdf",
          use_container_width=True,
      )
    else:
      st.warning(
          "PDF Export unavailable: Please run `pip install reportlab` or add"
          " `reportlab` to requirements.txt"
      )

else:
  st.info("Add some income streams or expenses above to view the complete breakdown.")
