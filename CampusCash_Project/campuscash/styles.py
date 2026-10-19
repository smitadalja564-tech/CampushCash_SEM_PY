import streamlit as st

def apply_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root { --cc-purple:#6C4CF1; --cc-navy:#18213A; --cc-muted:#737B91; --cc-bg:#F7F7FC; }
    html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    .stApp { background:var(--cc-bg); color:var(--cc-navy); }
    [data-testid="stHeader"] { background:rgba(247,247,252,.92); }
    [data-testid="stSidebar"] { background:#fff; border-right:1px solid #E9E8F4; }
    [data-testid="stSidebar"] .block-container { padding-top:1.2rem; }
    .brand { display:flex; align-items:center; gap:10px; padding:4px 0 18px; }
    .brand-mark { display:grid; place-items:center; width:42px; height:42px; border-radius:14px;
       background:#6C4CF1; color:#fff; font-weight:800; font-size:20px; box-shadow:0 7px 18px #6c4cf133; }
    .brand-name { font-size:22px; font-weight:800; letter-spacing:-.7px; color:#18213A; }
    .brand-tag { color:#737B91; font-size:11px; margin-top:-3px; }
    .page-eyebrow { text-transform:uppercase; letter-spacing:1.5px; color:#6C4CF1; font-size:11px; font-weight:800; }
    h1,h2,h3 { color:#18213A !important; letter-spacing:-.5px; }
    .metric-card { background:#fff; border:1px solid #EAE9F4; border-radius:18px; padding:18px 19px;
       min-height:125px; box-shadow:0 4px 16px rgba(30,28,70,.035); }
    .metric-label { color:#737B91; font-size:13px; font-weight:600; margin-bottom:10px; }
    .metric-value { color:#18213A; font-size:clamp(20px,2.1vw,29px); font-weight:800; letter-spacing:-.8px; overflow-wrap:anywhere; }
    .metric-note { color:#737B91; font-size:12px; margin-top:8px; }
    .section-card { background:#fff; border:1px solid #EAE9F4; border-radius:18px; padding:18px; }
    .pill { display:inline-block; padding:5px 10px; border-radius:99px; background:#F0ECFF; color:#6C4CF1; font-size:12px; font-weight:700; }
    div.stButton > button, div.stFormSubmitButton > button { border-radius:11px; min-height:42px; font-weight:700; }
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, div[data-testid="stDateInput"] input,
    div[data-testid="stSelectbox"] [data-baseweb="select"] { border-radius:10px; }
    [data-testid="stDataFrame"] { border:1px solid #EAE9F4; border-radius:12px; overflow:hidden; }
    .small-muted { color:#737B91; font-size:13px; }
    @media (max-width: 640px) {
      .block-container { padding-left:1rem !important; padding-right:1rem !important; padding-top:1rem !important; }
      .metric-card { padding:14px; min-height:105px; border-radius:14px; }
      .metric-label { font-size:12px; }
      .metric-value { font-size:21px; }
      h1 { font-size:1.65rem !important; }
      h2 { font-size:1.25rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

def brand():
    st.markdown("""<div class="brand"><div class="brand-mark">C</div><div>
    <div class="brand-name">CampusCash</div><div class="brand-tag">YOUR MONEY. YOUR GOALS. YOUR FUTURE.</div>
    </div></div>""", unsafe_allow_html=True)

def page_header(title, subtitle):
    st.markdown(f'<div class="page-eyebrow">CampusCash workspace</div><h1 style="margin:4px 0 0">{title}</h1><p style="color:#737B91;margin-top:4px">{subtitle}</p>', unsafe_allow_html=True)

def metric(label, value, note="", icon=""):
    st.markdown(f"""<div class="metric-card"><div class="metric-label">{icon} &nbsp; {label}</div>
    <div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>""", unsafe_allow_html=True)
