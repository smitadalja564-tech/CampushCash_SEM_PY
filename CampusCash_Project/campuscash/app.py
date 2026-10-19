import io, calendar
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

from database import (initialize_database, ensure_user_defaults, get_connection, add_expense,
    update_expense, delete_expense, get_expenses, monthly_total, get_budget, save_budget,
    get_categories, save_setting, get_settings)
from auth import register_user, authenticate
from utils import money, valid_amount, valid_budget, valid_date, month_key
from styles import apply_styles, brand, page_header, metric

st.set_page_config(page_title="CampusCash · Student Finance", page_icon="💜", layout="wide",
                   initial_sidebar_state="expanded")
apply_styles()
try:
    backup = initialize_database()
except Exception as exc:
    st.error(f"Database initialization failed: {exc}")
    st.stop()

if "user" not in st.session_state: st.session_state.user = None
if "page" not in st.session_state: st.session_state.page = "Dashboard"
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "Login"

def login_view():
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center;padding:12px 0 20px">
        <div class="brand-mark" style="margin:auto;width:58px;height:58px;font-size:27px">C</div>
        <h1 style="margin-bottom:0">CampusCash</h1>
        <p style="color:#737B91">Your money. Your goals. Your future.</p>
        <p style="color:#737B91">A calmer way to understand your student finances.</p></div>""", unsafe_allow_html=True)
        mode = st.radio("Account", ["Login", "Create account"], horizontal=True,
                        index=0 if st.session_state.auth_mode == "Login" else 1)
        st.session_state.auth_mode = mode
        with st.form("auth_form", clear_on_submit=False):
            username = st.text_input("Username", max_chars=50)
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm password", type="password") if mode == "Create account" else None
            submitted = st.form_submit_button("Create account" if mode == "Create account" else "Sign in",
                                              type="primary", use_container_width=True)
        if submitted:
            if mode == "Create account":
                ok, message = register_user(username, password, confirm)
                if ok:
                    ensure_user_defaults(username)
                    st.success(message)
                    st.session_state.auth_mode = "Login"
                    st.rerun()
                else: st.error(message)
            elif authenticate(username, password):
                st.session_state.user = username.strip()
                ensure_user_defaults(st.session_state.user)
                st.rerun()
            else:
                st.error("We couldn't sign you in. Check your username and password.")
        st.caption("Passwords are stored as bcrypt hashes. Account recovery is not included.")
        if backup:
            st.info(f"Legacy database backup created at `{backup}`. Review the migration note in README.md.")

if not st.session_state.user:
    login_view()
    st.stop()

user = st.session_state.user
settings = get_settings(user)
currency = settings["currency"]
today = date.today()
default_month = today.strftime("%Y-%m")

def user_categories():
    return [c["name"] for c in get_categories(user)]

def current_month_picker(key="selected_month"):
    chosen = st.date_input("Choose a month", value=today.replace(day=1), key=key)
    return chosen.strftime("%Y-%m")

def expense_form(existing=None, form_key="expense_form"):
    existing = existing or {}
    cats = user_categories()
    if existing.get("category") and existing["category"] not in cats: cats.append(existing["category"])
    payments = ["Cash", "UPI", "Debit Card", "Credit Card", "Bank Transfer", "Other"]
    with st.form(form_key):
        a, b = st.columns(2)
        with a:
            d = st.date_input("Date *", value=date.fromisoformat(existing.get("date", today.isoformat())))
            category = st.selectbox("Category *", cats or ["Other"],
                                    index=(cats.index(existing["category"]) if existing.get("category") in cats else 0))
            amount = st.number_input("Amount (₹) *", min_value=0.0, value=float(existing.get("amount", 0)),
                                     step=50.0, format="%.2f")
        with b:
            pm0 = existing.get("payment_method", "UPI")
            payment = st.selectbox("Payment method *", payments, index=payments.index(pm0) if pm0 in payments else 0)
            merchant = st.text_input("Merchant / payee", value=existing.get("merchant", ""), max_chars=120)
            tags = st.text_input("Tags (comma-separated)", value=existing.get("tags", ""), max_chars=250)
        description = st.text_area("Description", value=existing.get("description", ""), max_chars=500)
        x, y = st.columns(2)
        with x: submitted = st.form_submit_button("Save expense", type="primary", use_container_width=True)
        with y: reset = st.form_submit_button("Reset form", use_container_width=True)
    if reset:
        st.rerun()
    if submitted:
        if not valid_date(d.isoformat()): st.error("Choose a valid date.")
        elif not category or not payment: st.error("Category and payment method are required.")
        elif not valid_amount(amount): st.error("Amount must be a finite number greater than zero.")
        else:
            data = {"date": d.isoformat(), "category": category, "amount": amount,
                    "payment_method": payment, "description": description.strip(),
                    "merchant": merchant.strip(), "tags": tags.strip()}
            return data
    return None

def chart_theme(fig, height=330):
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, sans-serif", color="#18213A"),
                      margin=dict(l=12,r=12,t=35,b=12), legend_title_text="")
    return fig

with st.sidebar:
    brand()
    st.markdown(f"<div style='padding:8px 0 16px;color:#737B91;font-size:13px'>Signed in as<br><b style='color:#18213A'>{user}</b></div>", unsafe_allow_html=True)
    pages = ["Dashboard", "Add Expense", "Transactions", "Budgets", "Analytics",
             "Reports & Export", "Categories", "Settings"]
    icons = {"Dashboard":"▦","Add Expense":"+","Transactions":"↔","Budgets":"◷",
             "Analytics":"⌁","Reports & Export":"⇩","Categories":"◇","Settings":"⚙"}
    for p in pages:
        if st.button(f"{icons[p]}   {p}", key=f"nav_{p}", use_container_width=True,
                     type="primary" if st.session_state.page == p else "secondary"):
            st.session_state.page = p
            st.rerun()
    st.markdown("---")
    st.caption("Small steps. Stronger habits.")
    if st.button("↪  Log out", use_container_width=True):
        st.session_state.user = None
        st.session_state.page = "Dashboard"
        st.rerun()

page = st.session_state.page

if page == "Dashboard":
    page_header("Your money, at a glance", "A clear picture of where your money went—and what you have left.")
    month = current_month_picker("dash_month")
    total, count = monthly_total(user, month)
    budget = get_budget(user, month)
    remaining = budget - total
    df = get_expenses(user, start=f"{month}-01", end=f"{month}-31")
    prev_date = date.fromisoformat(month + "-01")
    prev_month = (prev_date.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    prev_total, prev_count = monthly_total(user, prev_month)
    days_elapsed = min(today.day, calendar.monthrange(int(month[:4]), int(month[5:]))[1]) if month == default_month else calendar.monthrange(int(month[:4]), int(month[5:]))[1]
    avg_daily = total / max(days_elapsed, 1)
    pct = (total / budget * 100) if budget > 0 else 0
    cols = st.columns(3)
    with cols[0]: metric("Spent this month", money(total,currency), f"{count} transaction(s)", "↗")
    with cols[1]: metric("Monthly budget", money(budget,currency), "Set a limit that works for you", "◎")
    with cols[2]: metric("Budget remaining", money(remaining,currency), "Over budget" if remaining < 0 else "Available to spend", "✓")
    cols = st.columns(3)
    with cols[0]: metric("Budget used", f"{pct:.1f}%", "No budget set" if budget == 0 else f"{max(0,100-pct):.1f}% remaining", "◔")
    with cols[1]: metric("Transactions", str(count), f"Previous month: {prev_count}", "≡")
    with cols[2]: metric("Average per day", money(avg_daily,currency), f"Previous month spent: {money(prev_total,currency)}", "⌁")
    if budget > 0:
        st.progress(min(max(total / budget, 0), 1), text=f"Budget utilization · {pct:.1f}%")
        if pct >= 100: st.error(f"You've exceeded this month's budget by {money(total-budget,currency)}.")
        elif pct >= 90: st.warning("You've used at least 90% of this month's budget.")
        elif pct >= 75: st.warning("You've used at least 75% of this month's budget.")
    elif total == 0:
        st.info("Start with one expense to see your personal spending picture. Use **Add Expense** to begin.")
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Spending trend")
        trend = get_expenses(user, start=f"{month}-01", end=f"{month}-31")
        if not trend.empty:
            trend["date"] = pd.to_datetime(trend["date"])
            daily = trend.groupby("date", as_index=False)["amount"].sum()
            fig = px.line(daily, x="date", y="amount", markers=True, labels={"date":"Date","amount":"Spend (₹)"})
            fig.update_traces(line_color="#6C4CF1", fill="tozeroy", fillcolor="rgba(108,76,241,.10)")
            fig.update_yaxes(tickprefix="₹")
            st.plotly_chart(chart_theme(fig), use_container_width=True)
        else: st.info("No spending recorded for this month yet.")
    with right:
        st.subheader("Category mix")
        if not df.empty:
            cats = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            fig = px.pie(cats, names="category", values="amount", hole=.65,
                         color_discrete_sequence=["#6C4CF1","#4185F4","#20BFA9","#F3A712","#EC6AA7","#8B7CF6"])
            fig.update_traces(textposition="inside", textinfo="percent")
            st.plotly_chart(chart_theme(fig), use_container_width=True)
            st.caption(f"Highest category: **{cats.iloc[0]['category']}** · {money(cats.iloc[0]['amount'],currency)}")
        else: st.info("Your category chart will appear once you add expenses.")
    st.subheader("Recent transactions")
    recent = get_expenses(user, start=f"{month}-01", end=f"{month}-31").head(5)
    if recent.empty: st.caption("No transactions this month yet.")
    else:
        display = recent[["date","category","description","payment_method","amount"]].copy()
        display["amount"] = display["amount"].map(lambda x: money(x,currency))
        st.dataframe(display, use_container_width=True, hide_index=True)
    if st.button("＋ Add an expense", type="primary"):
        st.session_state.page = "Add Expense"; st.rerun()

elif page == "Add Expense":
    page_header("Add an expense", "Capture it now. Understand your habits later.")
    result = expense_form()
    if result:
        try:
            add_expense(user, result)
            st.success("Expense saved successfully.")
            st.session_state.page = "Transactions"
            st.rerun()
        except Exception as exc: st.error(f"Could not save expense: {exc}")

elif page == "Transactions":
    page_header("Transactions", "Search, filter, edit, and manage your spending.")
    with st.expander("Search & filters", expanded=True):
        c1,c2,c3 = st.columns(3)
        search = c1.text_input("Description, merchant or tag")
        categories = ["All"] + user_categories()
        category = c2.selectbox("Category", categories)
        payment = c3.selectbox("Payment method", ["All","Cash","UPI","Debit Card","Credit Card","Bank Transfer","Other"])
        c4,c5,c6,c7 = st.columns(4)
        start = c4.date_input("From", value=today.replace(day=1), key="tx_start")
        end = c5.date_input("To", value=today, key="tx_end")
        min_amt = c6.number_input("Minimum ₹", min_value=0.0, value=0.0, step=50.0)
        max_amt = c7.number_input("Maximum ₹ (0 = no limit)", min_value=0.0, value=0.0, step=100.0)
        sort = st.selectbox("Sort", ["newest","oldest","amount high","amount low"])
    if start > end: st.error("Start date must not be after end date."); st.stop()
    tx = get_expenses(user, start=start, end=end, category=category, payment=payment, search=search,
                      min_amount=min_amt if min_amt > 0 else None, max_amount=max_amt if max_amt > 0 else None, sort=sort)
    st.caption(f"{len(tx):,} matching transaction(s) · Total {money(tx['amount'].sum() if not tx.empty else 0,currency)}")
    if tx.empty: st.info("No transactions match those filters.")
    else:
        if len(tx) <= 250:
            view = tx.copy(); view["amount"] = view["amount"].map(lambda x: money(x,currency))
            st.dataframe(view, use_container_width=True, hide_index=True)
        else:
            st.caption("Showing the first 250 rows for a compact preview; exports include all matching rows.")
            view = tx.head(250).copy(); view["amount"] = view["amount"].map(lambda x: money(x,currency))
            st.dataframe(view, use_container_width=True, hide_index=True)
        st.subheader("Edit or delete a transaction")
        ids = tx["id"].astype(int).tolist()
        chosen = st.selectbox("Select transaction ID", ids, format_func=lambda i: f"#{i} · {tx.loc[tx.id==i,'date'].iloc[0]} · {tx.loc[tx.id==i,'category'].iloc[0]} · {money(tx.loc[tx.id==i,'amount'].iloc[0],currency)}")
        record = tx.loc[tx.id == chosen].iloc[0].to_dict()
        with st.expander("Edit selected transaction"):
            edited = expense_form(record, form_key=f"edit_{chosen}")
            if edited:
                if update_expense(user, chosen, edited):
                    st.success("Transaction updated."); st.rerun()
                else: st.error("Transaction was not found or you do not have permission to edit it.")
        with st.expander("Delete selected transaction"):
            st.warning("Deleting a transaction is permanent.")
            confirm = st.checkbox("I understand this transaction will be deleted.", key=f"confirm_del_{chosen}")
            if st.button("Delete transaction", type="primary", disabled=not confirm):
                if delete_expense(user, chosen): st.success("Transaction deleted."); st.rerun()
                else: st.error("Transaction was not found or you do not have permission to delete it.")

elif page == "Budgets":
    page_header("Budgets", "Give each month a plan, then track your progress.")
    month = current_month_picker("budget_month")
    existing = get_budget(user, month)
    total, count = monthly_total(user, month)
    budget_value = st.number_input("Monthly budget (₹)", min_value=0.0, value=float(existing), step=500.0, format="%.2f")
    if st.button("Save monthly budget", type="primary"):
        if valid_budget(budget_value):
            save_budget(user, month, budget_value)
            st.success(f"Budget for {month} saved.")
            st.rerun()
        else: st.error("Budget must be a finite non-negative amount.")
    remaining = budget_value - total
    a,b,c = st.columns(3)
    with a: metric("Budget",money(budget_value,currency),month,"◎")
    with b: metric("Spent",money(total,currency),f"{count} transactions","↗")
    with c: metric("Remaining",money(remaining,currency),"Over budget" if remaining < 0 else "Available","✓")
    pct = total / budget_value * 100 if budget_value else 0
    if budget_value:
        st.progress(min(max(total/budget_value,0),1),text=f"{pct:.1f}% utilized")
        if pct >= 100: st.error(f"Over budget by {money(total-budget_value,currency)}.")
        elif pct >= 90: st.warning("90% budget threshold reached.")
        elif pct >= 75: st.warning("75% budget threshold reached.")
    conn = get_connection()
    try:
        history = pd.read_sql_query("SELECT month,amount FROM budgets WHERE username=? ORDER BY month DESC",conn,params=(user,))
    finally: conn.close()
    st.subheader("Budget history")
    if history.empty: st.caption("Your saved monthly budgets will appear here.")
    else: st.dataframe(history, use_container_width=True, hide_index=True)

elif page == "Analytics":
    page_header("Analytics", "Explore your spending patterns with interactive charts.")
    c1,c2 = st.columns(2)
    start = c1.date_input("From date", value=today.replace(day=1), key="an_start")
    end = c2.date_input("To date", value=today, key="an_end")
    if start > end: st.error("Start date must be on or before end date."); st.stop()
    df = get_expenses(user, start=start, end=end)
    if df.empty: st.info("No expenses in this date range. Add a transaction to unlock analytics.")
    else:
        a,b = st.columns(2)
        with a:
            st.subheader("Category distribution")
            cat = df.groupby("category",as_index=False)["amount"].sum()
            fig=px.pie(cat,names="category",values="amount",hole=.62,color_discrete_sequence=["#6C4CF1","#4185F4","#20BFA9","#F3A712","#EC6AA7","#8B7CF6"])
            fig.update_traces(hovertemplate="%{label}<br>₹%{value:,.2f}<extra></extra>")
            st.plotly_chart(chart_theme(fig),use_container_width=True)
        with b:
            st.subheader("Daily spending")
            df["date"] = pd.to_datetime(df["date"])
            daily=df.groupby("date",as_index=False)["amount"].sum()
            fig=px.bar(daily,x="date",y="amount",labels={"date":"Date","amount":"Spend (₹)"},color_discrete_sequence=["#4185F4"])
            fig.update_yaxes(tickprefix="₹")
            st.plotly_chart(chart_theme(fig),use_container_width=True)
        c,d = st.columns(2)
        with c:
            st.subheader("Payment methods")
            pm=df.groupby("payment_method",as_index=False)["amount"].sum()
            fig=px.bar(pm,x="payment_method",y="amount",labels={"payment_method":"Payment","amount":"Spend (₹)"},color_discrete_sequence=["#20BFA9"])
            fig.update_yaxes(tickprefix="₹")
            st.plotly_chart(chart_theme(fig),use_container_width=True)
        with d:
            st.subheader("Monthly spending trend")
            df["month"]=pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
            monthly=df.groupby("month",as_index=False)["amount"].sum()
            fig=px.line(monthly,x="month",y="amount",markers=True,labels={"month":"Month","amount":"Spend (₹)"})
            fig.update_traces(line_color="#6C4CF1")
            fig.update_yaxes(tickprefix="₹")
            st.plotly_chart(chart_theme(fig),use_container_width=True)
        st.subheader("Top spending categories")
        top=cat.sort_values("amount",ascending=False).head(5)
        top["amount"]=top["amount"].map(lambda x:money(x,currency))
        st.dataframe(top,use_container_width=True,hide_index=True)
        st.caption(f"Average daily spending across dates with expenses: {money(df.groupby(df['date'].dt.date)['amount'].sum().mean(),currency)}.")

elif page == "Reports & Export":
    page_header("Reports & export", "Build a report for any period and take your data with you.")
    a,b=st.columns(2)
    start=a.date_input("Report from",value=today.replace(day=1),key="rep_start")
    end=b.date_input("Report to",value=today,key="rep_end")
    if start>end: st.error("Start date must not be after end date."); st.stop()
    df=get_expenses(user,start=start,end=end)
    total=float(df["amount"].sum()) if not df.empty else 0
    budget_month=month_key(start) if month_key(start)==month_key(end) else None
    budget=get_budget(user,budget_month) if budget_month else 0
    c1,c2,c3=st.columns(3)
    with c1: metric("Total spending",money(total,currency),f"{start} to {end}","↗")
    with c2: metric("Transactions",str(len(df)),"Matching records","≡")
    with c3: metric("Budget utilization",f"{total/budget*100:.1f}%" if budget else "N/A","Only shown for a single budget month","◔")
    st.subheader("Category summary")
    if df.empty: st.info("No records in this report range.")
    else:
        summary=df.groupby("category",as_index=False).agg(total=("amount","sum"),transactions=("id","count"))
        summary["total"]=summary["total"].round(2)
        st.dataframe(summary,use_container_width=True,hide_index=True)
    export=df.copy()
    export=export.rename(columns={"id":"Transaction ID","date":"Date","category":"Category","amount":"Amount (INR)",
                                  "payment_method":"Payment Method","description":"Description","merchant":"Merchant","tags":"Tags"})
    st.download_button("Download CSV",data=export.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"campuscash_{start}_{end}.csv",mime="text/csv",use_container_width=True)
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        export.to_excel(writer,index=False,sheet_name="Transactions")
        if not df.empty:
            df.groupby("category",as_index=False)["amount"].sum().to_excel(writer,index=False,sheet_name="By Category")
    st.download_button("Download Excel workbook",data=output.getvalue(),
                       file_name=f"campuscash_{start}_{end}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    st.markdown("#### Print-friendly summary")
    st.markdown(f"**CampusCash spending report**  \nPeriod: {start} — {end}  \nTotal: **{money(total,currency)}**  \nTransactions: **{len(df)}**")
    st.caption("Use your browser's Print command to print this summary. A dedicated PDF report is not included.")

elif page == "Categories":
    page_header("Categories", "Organize expenses around the way you actually spend.")
    cats=get_categories(user,include_archived=True)
    with st.expander("Add a category",expanded=True):
        with st.form("new_category"):
            name=st.text_input("Category name",max_chars=40).strip()
            color=st.color_picker("Color",value="#6C4CF1")
            add=st.form_submit_button("Add category",type="primary")
        if add:
            if not name: st.error("Enter a category name.")
            else:
                conn=get_connection()
                try:
                    conn.execute("INSERT INTO categories(username,name,color,icon) VALUES (?,?,?,'shapes')",(user,name,color))
                    conn.commit(); st.success("Category added."); st.rerun()
                except Exception as exc:
                    if "UNIQUE" in str(exc).upper(): st.error("That category already exists.")
                    else: st.error(f"Could not add category: {exc}")
                finally: conn.close()
    for cat in cats:
        with st.container(border=True):
            col1,col2,col3=st.columns([3,2,1])
            col1.markdown(f"<span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:{cat['color']};margin-right:8px'></span>**{cat['name']}**",unsafe_allow_html=True)
            col2.caption("Archived" if cat["archived"] else "Active")
            if not cat["archived"]:
                if col3.button("Archive",key=f"archive_{cat['id']}"):
                    conn=get_connection()
                    try:
                        conn.execute("UPDATE categories SET archived=1 WHERE id=? AND username=?",(cat["id"],user))
                        conn.commit()
                    finally: conn.close()
                    st.rerun()
            else:
                if col3.button("Restore",key=f"restore_{cat['id']}"):
                    conn=get_connection()
                    try:
                        conn.execute("UPDATE categories SET archived=0 WHERE id=? AND username=?",(cat["id"],user))
                        conn.commit()
                    finally: conn.close()
                    st.rerun()
    st.caption("Archiving preserves historical expense records. Renaming is intentionally not offered because category names are stored on historical transactions.")

elif page == "Settings":
    page_header("Settings", "Make CampusCash feel like your own.")
    st.subheader("Profile")
    st.text_input("Username",value=user,disabled=True)
    st.caption("Username changes are not supported in this version.")
    with st.form("settings_form"):
        currencies=["INR","USD","EUR","GBP"]
        cur=st.selectbox("Display currency",currencies,index=currencies.index(currency) if currency in currencies else 0)
        datefmt=st.selectbox("Preferred date format",["YYYY-MM-DD","DD/MM/YYYY","MM/DD/YYYY"],
                             index=["YYYY-MM-DD","DD/MM/YYYY","MM/DD/YYYY"].index(settings["date_format"]) if settings["date_format"] in ["YYYY-MM-DD","DD/MM/YYYY","MM/DD/YYYY"] else 0)
        appearance=st.selectbox("Appearance",["Light","Dark"],index=0 if settings["appearance"]=="Light" else 1)
        save=st.form_submit_button("Save preferences",type="primary")
    if save:
        save_setting(user,cur,datefmt,appearance)
        st.success("Preferences saved. Currency changes display formatting only; historical amounts are not converted.")
        st.rerun()
    st.subheader("Data & security")
    st.write("Your expenses are stored in a local SQLite database. Keep a backup of `student_expense.db` in a secure location.")
    st.write("Passwords are hashed using bcrypt. Password recovery and username changes are not included.")
    st.write("CampusCash · Student finance, made clearer.")
