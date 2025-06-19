import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import calendar
import time
import random

# Page configuration
st.set_page_config(
    page_title="FinTrack Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        background-attachment: fixed;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #1a2530 100%) !important;
        color: white;
        padding: 20px 15px;
        border-right: 1px solid #34495e;
    }
    
    /* Card styling */
    .card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 6px 15px rgba(0,0,0,0.08);
        margin-bottom: 25px;
        border: none;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(0,0,0,0.12);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #3498db 0%, #1a5276 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #2980b9 0%, #154360 100%);
        transform: translateY(-2px);
        box-shadow: 0 7px 14px rgba(50, 50, 93, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
    }
    
    /* Header styling */
    .header {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
        padding-bottom: 15px;
        border-bottom: 2px solid #e0e0e0;
    }
    
    /* Metric styling */
    .metric-value {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    
    /* Table styling */
    .dataframe {
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #3498db 0%, #2ecc71 100%);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        border-radius: 8px !important;
        background-color: #f0f0f0 !important;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3498db 0%, #2ecc71 100%) !important;
        color: white !important;
        font-weight: 600;
    }
    
    /* Custom success button */
    .success-btn {
        background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%) !important;
    }
    
    /* Custom danger button */
    .danger-btn {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) !important;
    }
    
    /* Notification badge */
    .notification-badge {
        position: absolute;
        top: -8px;
        right: -8px;
        background: #e74c3c;
        color: white;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for transactions
if 'transactions' not in st.session_state:
    sample_data = {
        'Date': [datetime.now() - timedelta(days=i) for i in range(30)],
        'Type': ['Expense' if i % 3 != 0 else 'Income' for i in range(30)],
        'Category': ['Food' if i % 5 == 0 else 'Transport' if i % 5 == 1 else 'Housing' if i % 5 == 2 else 'Entertainment' if i % 5 == 3 else 'Utilities' for i in range(30)],
        'Amount': [random.uniform(10, 300) for _ in range(30)],
        'Description': [f"Transaction {i+1}" for i in range(30)]
    }
    st.session_state.transactions = pd.DataFrame(sample_data)
    st.session_state.transactions['Amount'] = st.session_state.transactions['Amount'].apply(lambda x: round(x, 2))

# Initialize budgets
if 'budgets' not in st.session_state:
    st.session_state.budgets = {
        'Food': 500,
        'Transport': 300,
        'Housing': 1200,
        'Entertainment': 200,
        'Utilities': 250
    }

# Function to add transaction
def add_transaction(date, trans_type, category, amount, description):
    new_transaction = pd.DataFrame({
        'Date': [date],
        'Type': [trans_type],
        'Category': [category],
        'Amount': [amount],
        'Description': [description]
    })
    st.session_state.transactions = pd.concat(
        [st.session_state.transactions, new_transaction], 
        ignore_index=True
    )
    st.success("✅ Transaction added successfully!")
    time.sleep(1)
    st.experimental_rerun()

# Function to delete transaction
def delete_transaction(index):
    st.session_state.transactions = st.session_state.transactions.drop(index).reset_index(drop=True)
    st.success("🗑️ Transaction deleted successfully!")
    time.sleep(1)
    st.experimental_rerun()

# Function to update budget
def update_budget(category, amount):
    st.session_state.budgets[category] = amount
    st.success(f"📊 {category} budget updated to ${amount:.2f}!")
    time.sleep(1)
    st.experimental_rerun()

# Dashboard Page
def dashboard_page():
    st.markdown('<div class="header">Financial Dashboard</div>', unsafe_allow_html=True)
    
    # Calculate financial metrics
    if not st.session_state.transactions.empty:
        income = st.session_state.transactions[
            st.session_state.transactions['Type'] == 'Income']['Amount'].sum()
        expenses = st.session_state.transactions[
            st.session_state.transactions['Type'] == 'Expense']['Amount'].sum()
        balance = income - expenses
        
        # Calculate budget utilization
        expense_df = st.session_state.transactions[
            st.session_state.transactions['Type'] == 'Expense'
        ]
        budget_utilization = {}
        for category, budget in st.session_state.budgets.items():
            cat_expenses = expense_df[expense_df['Category'] == category]['Amount'].sum()
            utilization = min(cat_expenses / budget * 100, 100) if budget > 0 else 0
            budget_utilization[category] = utilization
    else:
        income = expenses = balance = 0
        budget_utilization = {}
    
    # Summary cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="card">
            <h3>Total Income</h3>
            <div class="metric-value" style="color:#27ae60;">${income:,.2f}</div>
            <div style="color:#7f8c8d; margin-top:10px;">↑ 12% from last month</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="card">
            <h3>Total Expenses</h3>
            <div class="metric-value" style="color:#e74c3c;">${expenses:,.2f}</div>
            <div style="color:#7f8c8d; margin-top:10px;">↑ 8% from last month</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="card">
            <h3>Current Balance</h3>
            <div class="metric-value" style="color:{'#27ae60' if balance >= 0 else '#e74c3c'};">${balance:,.2f}</div>
            <div style="color:#7f8c8d; margin-top:10px;">{f"↓ ${abs(balance-income):,.2f} from last month" if balance < income else "↑ Good progress"}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts row
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Expense trend chart
        st.markdown("""
        <div class="card">
            <h3 style="margin-top:0;">Monthly Expense Trend</h3>
        """, unsafe_allow_html=True)
        
        if not st.session_state.transactions.empty:
            expense_df = st.session_state.transactions[
                st.session_state.transactions['Type'] == 'Expense'
            ].copy()
            expense_df['Month'] = expense_df['Date'].dt.strftime('%Y-%m')
            monthly_expenses = expense_df.groupby('Month')['Amount'].sum().reset_index()
            
            fig = px.line(
                monthly_expenses, 
                x='Month', 
                y='Amount',
                markers=True,
                line_shape='spline',
                template='plotly_white'
            )
            fig.update_traces(line=dict(width=3, color='#e74c3c'), marker=dict(size=8))
            fig.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                hovermode="x unified",
                xaxis_title=None,
                yaxis_title=None
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expenses recorded yet")
            
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # Budget utilization
        st.markdown("""
        <div class="card">
            <h3 style="margin-top:0;">Budget Utilization</h3>
        """, unsafe_allow_html=True)
        
        if budget_utilization:
            for category, utilization in budget_utilization.items():
                st.markdown(f"<div style='font-weight:500; margin-bottom:5px;'>{category}</div>", unsafe_allow_html=True)
                st.progress(int(utilization), text=f"{utilization:.1f}%")
        else:
            st.info("No budget data available")
            
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Recent transactions and net worth
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3 style="margin-top:0;">Recent Transactions</h3>
        """, unsafe_allow_html=True)
        
        if not st.session_state.transactions.empty:
            recent_df = st.session_state.transactions.sort_values('Date', ascending=False).head(8).copy()
            
            # Create a styled table
            st.dataframe(
                recent_df.style
                .applymap(lambda x: 'color: #27ae60' if x == 'Income' else 'color: #e74c3c', subset=['Type'])
                .format({'Amount': '${:,.2f}'})
                .set_properties(**{'text-align': 'left', 'padding': '8px'})
                .set_table_styles([
                    {'selector': 'thead', 'props': [('background-color', '#2c3e50'), ('color', 'white')]},
                    {'selector': 'tr:hover', 'props': [('background-color', '#f5f5f5')]}
                ]),
                height=350
            )
        else:
            st.info("No transactions recorded yet")
            
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # Net worth projection
        st.markdown("""
        <div class="card">
            <h3 style="margin-top:0;">Net Worth Projection</h3>
        """, unsafe_allow_html=True)
        
        if not st.session_state.transactions.empty:
            # Create projection data
            months = 6
            current_net_worth = balance
            projection = [current_net_worth]
            
            for i in range(1, months+1):
                # Simple projection based on average income/expense
                avg_income = income / len(st.session_state.transactions) * 30  # approx monthly
                avg_expense = expenses / len(st.session_state.transactions) * 30  # approx monthly
                projection.append(projection[-1] + (avg_income - avg_expense))
            
            months_list = [datetime.now().strftime('%b %Y')]
            for i in range(1, months+1):
                future_date = datetime.now() + timedelta(days=30*i)
                months_list.append(future_date.strftime('%b %Y'))
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=months_list, 
                y=projection,
                mode='lines+markers',
                line=dict(width=3, color='#3498db'),
                marker=dict(size=8, color='#2980b9')
            ))
            
            fig.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_title=None,
                yaxis_title=None,
                hovermode="x unified",
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for projection")
            
        st.markdown("</div>", unsafe_allow_html=True)

# Transactions Page
def transactions_page():
    st.markdown('<div class="header">Transaction Management</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Add transaction form
        with st.form("transaction_form", clear_on_submit=True):
            st.subheader("Add New Transaction")
            
            date = st.date_input("Date", datetime.today())
            trans_type = st.selectbox("Type", ["Income", "Expense"])
            
            if trans_type == "Income":
                category = st.selectbox("Category", ["Salary", "Investment", "Freelance", "Bonus", "Other"])
            else:
                category = st.selectbox("Category", ["Food", "Transport", "Housing", "Entertainment", "Utilities", "Healthcare", "Shopping"])
            
            amount = st.number_input("Amount", min_value=0.01, step=1.0, format="%.2f")
            description = st.text_area("Description")
            
            submitted = st.form_submit_button("Add Transaction", use_container_width=True)
            if submitted:
                add_transaction(date, trans_type, category, amount, description)
    
    with col2:
        # Transaction list with filtering
        st.subheader("Transaction History")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_type = st.selectbox("Filter by Type", ["All", "Income", "Expense"])
        with col2:
            filter_category = st.selectbox("Filter by Category", ["All"] + list(st.session_state.transactions['Category'].unique()))
        with col3:
            date_range = st.selectbox("Date Range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        
        # Apply filters
        filtered_df = st.session_state.transactions.copy()
        
        if filter_type != "All":
            filtered_df = filtered_df[filtered_df['Type'] == filter_type]
        
        if filter_category != "All":
            filtered_df = filtered_df[filtered_df['Category'] == filter_category]
        
        if date_range != "All time":
            days = 7 if date_range == "Last 7 days" else 30 if date_range == "Last 30 days" else 90
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_df = filtered_df[filtered_df['Date'] >= cutoff_date]
        
        # Display transactions
        if not filtered_df.empty:
            # Display in a table with delete buttons
            for i, row in filtered_df.sort_values('Date', ascending=False).iterrows():
                with st.container():
                    cols = st.columns([1, 1, 1, 1, 3, 1])
                    cols[0].write(row['Date'].strftime('%b %d'))
                    
                    # Color code type
                    if row['Type'] == 'Income':
                        cols[1].markdown(f"<span style='color:#27ae60; font-weight:500;'>Income</span>", unsafe_allow_html=True)
                    else:
                        cols[1].markdown(f"<span style='color:#e74c3c; font-weight:500;'>Expense</span>", unsafe_allow_html=True)
                    
                    cols[2].markdown(f"<span style='font-weight:500;'>{row['Category']}</span>", unsafe_allow_html=True)
                    
                    # Format amount
                    if row['Type'] == 'Income':
                        cols[3].markdown(f"<span style='color:#27ae60; font-weight:700;'>+${row['Amount']:,.2f}</span>", unsafe_allow_html=True)
                    else:
                        cols[3].markdown(f"<span style='color:#e74c3c; font-weight:700;'>-${row['Amount']:,.2f}</span>", unsafe_allow_html=True)
                    
                    cols[4].write(row['Description'])
                    
                    # Delete button with confirmation
                    if cols[5].button("🗑️", key=f"del_{i}"):
                        delete_transaction(i)
        else:
            st.info("No transactions found with current filters")

# Budgets Page
def budgets_page():
    st.markdown('<div class="header">Budget Management</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Budget overview
        st.subheader("Current Budgets")
        
        # Calculate budget utilization
        expense_df = st.session_state.transactions[
            st.session_state.transactions['Type'] == 'Expense'
        ]
        
        budget_data = []
        for category, budget in st.session_state.budgets.items():
            spent = expense_df[expense_df['Category'] == category]['Amount'].sum()
            remaining = max(budget - spent, 0)
            utilization = min(spent / budget * 100, 100) if budget > 0 else 0
            
            budget_data.append({
                'Category': category,
                'Budget': budget,
                'Spent': spent,
                'Remaining': remaining,
                'Utilization': utilization
            })
        
        budget_df = pd.DataFrame(budget_data)
        
        if not budget_df.empty:
            for _, row in budget_df.iterrows():
                with st.container():
                    st.markdown(f"**{row['Category']}**")
                    
                    cols = st.columns([2, 1])
                    with cols[0]:
                        st.metric("Budget", f"${row['Budget']:,.2f}")
                    with cols[1]:
                        st.metric("Spent", f"${row['Spent']:,.2f}", delta=f"-${row['Budget'] - row['Spent']:,.2f} remaining")
                    
                    # Progress bar
                    st.progress(int(row['Utilization']), text=f"{row['Utilization']:.1f}%")
                    
                    st.divider()
        else:
            st.info("No budgets set up yet")
    
    with col2:
        # Set/update budgets
        st.subheader("Set Budgets")
        
        with st.form("budget_form"):
            category = st.selectbox("Category", ["Food", "Transport", "Housing", "Entertainment", "Utilities", "Healthcare", "Shopping"])
            amount = st.number_input("Monthly Budget", min_value=1, value=st.session_state.budgets.get(category, 300))
            
            submitted = st.form_submit_button("Update Budget", use_container_width=True)
            if submitted:
                update_budget(category, amount)
        
        # Budget vs Actual chart
        st.subheader("Budget vs Actual")
        
        if not budget_df.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=budget_df['Category'],
                y=budget_df['Budget'],
                name='Budget',
                marker_color='#3498db'
            ))
            
            fig.add_trace(go.Bar(
                x=budget_df['Category'],
                y=budget_df['Spent'],
                name='Spent',
                marker_color='#e74c3c'
            ))
            
            fig.update_layout(
                barmode='group',
                height=400,
                margin=dict(l=0, r=0, t=40, b=0),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No budget data available")

# Reports Page
def reports_page():
    st.markdown('<div class="header">Financial Reports</div>', unsafe_allow_html=True)
    
    if st.session_state.transactions.empty:
        st.info("No data available for reports")
        return
    
    # Time range selector
    col1, col2, col3 = st.columns(3)
    min_date = st.session_state.transactions['Date'].min()
    max_date = st.session_state.transactions['Date'].max()
    
    with col1:
        start_date = st.date_input("Start Date", min_date)
    with col2:
        end_date = st.date_input("End Date", max_date)
    with col3:
        report_type = st.selectbox("Report Type", ["Summary", "Income Analysis", "Expense Analysis", "Category Breakdown"])
    
    filtered_df = st.session_state.transactions[
        (st.session_state.transactions['Date'] >= pd.Timestamp(start_date)) &
        (st.session_state.transactions['Date'] <= pd.Timestamp(end_date))
    ]
    
    if filtered_df.empty:
        st.warning("No transactions in selected date range")
        return
    
    # Tabs for different reports
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Income", "Expenses", "Categories"])
    
    with tab1:
        # Summary report
        st.subheader("Financial Summary")
        
        col1, col2, col3 = st.columns(3)
        income = filtered_df[filtered_df['Type'] == 'Income']['Amount'].sum()
        expenses = filtered_df[filtered_df['Type'] == 'Expense']['Amount'].sum()
        balance = income - expenses
        
        with col1:
            st.metric("Total Income", f"${income:,.2f}")
        with col2:
            st.metric("Total Expenses", f"${expenses:,.2f}")
        with col3:
            st.metric("Net Balance", f"${balance:,.2f}", delta_color="inverse")
        
        # Income vs Expense comparison
        st.subheader("Income vs Expenses")
        comparison_df = filtered_df.groupby('Type')['Amount'].sum().reset_index()
        fig = px.bar(
            comparison_df, 
            x='Type', 
            y='Amount',
            color='Type',
            color_discrete_map={'Income': '#27ae60', 'Expense': '#e74c3c'},
            text_auto='.2s'
        )
        fig.update_layout(
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Income analysis
        st.subheader("Income Analysis")
        
        income_df = filtered_df[filtered_df['Type'] == 'Income']
        
        if not income_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Income by Category**")
                cat_income = income_df.groupby('Category')['Amount'].sum().reset_index()
                fig = px.pie(
                    cat_income, 
                    names='Category', 
                    values='Amount',
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Greens
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Income Trend**")
                income_df['Week'] = income_df['Date'].dt.strftime('%Y-%U')
                weekly_income = income_df.groupby('Week')['Amount'].sum().reset_index()
                fig = px.line(
                    weekly_income, 
                    x='Week', 
                    y='Amount',
                    markers=True,
                    line_shape='spline',
                    color_discrete_sequence=['#27ae60']
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No income data in selected period")
    
    with tab3:
        # Expense analysis
        st.subheader("Expense Analysis")
        
        expense_df = filtered_df[filtered_df['Type'] == 'Expense']
        
        if not expense_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Expenses by Category**")
                cat_expense = expense_df.groupby('Category')['Amount'].sum().reset_index()
                fig = px.pie(
                    cat_expense, 
                    names='Category', 
                    values='Amount',
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Reds
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Expense Trend**")
                expense_df['Week'] = expense_df['Date'].dt.strftime('%Y-%U')
                weekly_expense = expense_df.groupby('Week')['Amount'].sum().reset_index()
                fig = px.line(
                    weekly_expense, 
                    x='Week', 
                    y='Amount',
                    markers=True,
                    line_shape='spline',
                    color_discrete_sequence=['#e74c3c']
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data in selected period")
    
    with tab4:
        # Category breakdown
        st.subheader("Category Breakdown")
        
        # All categories
        cat_df = filtered_df.groupby(['Category', 'Type'])['Amount'].sum().unstack().reset_index().fillna(0)
        cat_df['Net'] = cat_df.get('Income', 0) - cat_df.get('Expense', 0)
        
        fig = px.bar(
            cat_df, 
            x='Category', 
            y=['Income', 'Expense'],
            barmode='group',
            color_discrete_map={'Income': '#27ae60', 'Expense': '#e74c3c'}
        )
        fig.update_layout(
            height=500,
            legend_title=None
        )
        st.plotly_chart(fig, use_container_width=True)

# Main App
def main():
    # Sidebar navigation
    with st.sidebar:
        # Logo and title
        st.markdown("<div style='text-align:center; margin-bottom:30px;'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135679.png", width=80)
        st.markdown("<h1 style='color:white;'>FinTrack Pro</h1>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation
        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Transactions", "Budgets", "Reports"],
            icons=["speedometer", "cash-coin", "wallet", "bar-chart"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#1a2530"},
                "icon": {"color": "#3498db", "font-size": "20px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "8px 0",
                    "border-radius": "8px",
                    "padding": "12px 16px",
                    "color": "white"
                },
                "nav-link:hover": {
                    "background": "rgba(52, 152, 219, 0.3)",
                },
                "nav-link-selected": {
                    "background": "#3498db",
                    "font-weight": "600"
                }
            }
        )
        
        # Stats summary
        st.markdown("---")
        st.markdown("<h4 style='color:white;'>Financial Summary</h4>", unsafe_allow_html=True)
        
        if not st.session_state.transactions.empty:
            income = st.session_state.transactions[
                st.session_state.transactions['Type'] == 'Income']['Amount'].sum()
            expenses = st.session_state.transactions[
                st.session_state.transactions['Type'] == 'Expense']['Amount'].sum()
            balance = income - expenses
            
            st.markdown(f"<p style='color:#27ae60; font-size:18px;'>Income: <b>${income:,.2f}</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:#e74c3c; font-size:18px;'>Expenses: <b>${expenses:,.2f}</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:{'#27ae60' if balance >= 0 else '#e74c3c'}; font-size:20px;'>Balance: <b>${balance:,.2f}</b></p>", unsafe_allow_html=True)
        else:
            st.info("No transactions yet")
        
        # Footer
        st.markdown("---")
        st.markdown("<div style='text-align:center; color:#95a5a6; margin-top:30px;'>FinTrack Pro v2.0<br>© 2023 Financial Solutions</div>", unsafe_allow_html=True)
    
    # Page selection
    if selected == "Dashboard":
        dashboard_page()
    elif selected == "Transactions":
        transactions_page()
    elif selected == "Budgets":
        budgets_page()
    elif selected == "Reports":
        reports_page()

if __name__ == "__main__":
    main()