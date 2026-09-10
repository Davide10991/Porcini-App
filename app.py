import streamlit as st
import pandas as pd
import requests
import re
import base64
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
TZ_ROMA = ZoneInfo("Europe/Rome")
from math import radians, sin, cos, sqrt, atan2, exp
import io
import gzip
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

try:
    from meteostat import Stations, Daily
    METEOSTAT_OK = True
except Exception:
    METEOSTAT_OK = False

st.set_page_config(
    page_title="Boletus Map",
    page_icon="sfondo_login.jpg",
    layout="wide",
    initial_sidebar_state="expanded",
)

ADMIN_USER = "Davide1099"
ADMIN_PASS = "Ciccione99"
GUEST_PASS = "Porcino1"

if "app_ok" not in st.session_state:
    st.session_state["app_ok"] = False
if "ruolo" not in st.session_state:
    st.session_state["ruolo"] = "guest"


def _sfondo_url(nome):
    p = Path(__file__).resolve().parent / nome
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    return ""


_sfondo = (
    _sfondo_url("sfondo_app.jpg")
    if st.session_state.get("app_ok")
    else _sfondo_url("sfondo_login.jpg")
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500&family=Syne:wght@500;700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'IBM Plex Sans', sans-serif; }
    .stApp {
        background:
            radial-gradient(900px 520px at 8% -8%, rgba(196, 86, 42, .22), transparent 52%),
            radial-gradient(700px 480px at 108% 12%, rgba(90, 168, 92, .18), transparent 48%),
            linear-gradient(180deg, rgba(4,10,7,.72) 0%, rgba(6,12,8,.46) 42%, rgba(3,8,6,.78) 100%),
            url('__SFONDO__')
            center/cover fixed no-repeat,
            #06110c;
    }
    .stApp::before {
        content: "";
        position: fixed; inset: 0; pointer-events: none; z-index: 0;
        background-image:
            radial-gradient(1.2px 1.2px at 12% 18%, rgba(232,210,150,.35), transparent 60%),
            radial-gradient(1px 1px at 28% 62%, rgba(180,230,170,.28), transparent 60%),
            radial-gradient(1.4px 1.4px at 71% 24%, rgba(232,210,150,.28), transparent 60%),
            radial-gradient(1px 1px at 84% 78%, rgba(196,86,42,.35), transparent 60%);
        animation: spore 18s linear infinite;
        opacity: .5;
    }
    .stApp::after {
        content: "🍄‍🟫";
        position: fixed; right: 14px; bottom: 16px; font-size: 1.7rem;
        animation: floaty 7.5s ease-in-out infinite; opacity: .34; z-index: 0; pointer-events: none;
    }
    @keyframes floaty { 0%,100% { transform: translateY(0) rotate(-8deg);} 50% { transform: translateY(-14px) rotate(10deg);} }
    @keyframes spore { 0% { transform: translateY(0);} 100% { transform: translateY(-28px);} }
    h1, h2, h3 {
        font-family: 'Fraunces', serif !important;
        letter-spacing: -.02em;
        color: #f6f1e4 !important;
        text-shadow: 0 2px 18px rgba(0,0,0,.7);
    }
    .stApp p, .stApp li, .stApp span, .stApp label, .stApp .stMarkdown {
        color: #e7efe4 !important;
        text-shadow: 0 1px 6px rgba(0,0,0,.4);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(8,18,12,.97), rgba(6,12,9,.94)) !important;
        backdrop-filter: blur(18px);
        border-right: 1px solid rgba(110, 170, 100, .28);
        box-shadow: 10px 0 40px rgba(0,0,0,.4);
    }
    [data-testid="stSidebar"] * { color: #e8f3e4 !important; text-shadow: none !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] .stMarkdown {
        color: #e8f3e4 !important; font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] { display: block !important; }
    .block-container { position: relative; z-index: 1; padding-top: 1.2rem !important; max-width: 1280px; }
    div[data-testid="stMetric"] {
        background:
            radial-gradient(120% 80% at 50% -20%, rgba(196,86,42,.28), transparent 55%),
            linear-gradient(180deg, rgba(18,32,22,.55), rgba(8,16,12,.72));
        border: 1px solid rgba(168, 214, 150, .28);
        border-radius: 28px 28px 18px 18px;
        padding: 16px 16px 12px;
        backdrop-filter: blur(16px);
        box-shadow: 0 14px 34px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.12);
        animation: fadeup .7s ease both;
        position: relative;
    }
    div[data-testid="stMetric"]::before {
        content: "";
        position: absolute; left: 18%; right: 18%; top: -7px; height: 10px;
        background: #c4562a; border-radius: 10px 10px 4px 4px;
    }
    div[data-testid="stMetric"] label { color: #b7e0b0 !important; letter-spacing: .12em; text-transform: uppercase; font-size: .68rem !important; font-family: 'Syne', sans-serif !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f7f4ea !important; font-family: 'Fraunces', serif; font-size: 2.15rem !important; }
    @keyframes fadeup { from { opacity: 0; transform: translateY(10px);} to { opacity: 1; transform: none;} }
    .stButton>button { border-radius: 16px !important; font-weight: 700; font-family: 'Syne', sans-serif; }
    .stButton>button:hover { transform: translateY(-1px); }
    button[kind="primary"] { background: linear-gradient(180deg, #d86a38, #9a3d1c) !important; color: #fff8f0 !important; border: none !important; }
    [data-testid="stSidebar"] button { color: #10210f !important; background-color: #d7ecc8 !important; border: 1px solid #6aa25c !important; }
    [data-testid="stSidebar"] button p, [data-testid="stSidebar"] button span, [data-testid="stSidebar"] button div { color: #10210f !important; }
    [data-testid="stSidebar"] button[kind="primary"] { color: #fff8f0 !important; background: linear-gradient(180deg, #d86a38, #9a3d1c) !important; border: none !important; }
    [data-testid="stSidebar"] button[kind="primary"] p,
    [data-testid="stSidebar"] button[kind="primary"] span,
    [data-testid="stSidebar"] button[kind="primary"] div { color: #ffffff !important; }
    #MainMenu, footer, .stDeployButton, [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
    [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] {
        display: flex !important; visibility: visible !important; opacity: 1 !important;
        width: 44px !important; height: 44px !important; border-radius: 14px !important;
        background: rgba(215,236,200,.94) !important; border: 1px solid #6aa25c !important; z-index: 1000 !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg, [data-testid="stSidebarCollapseButton"] svg { display: none !important; }
    [data-testid="stSidebarCollapsedControl"]::before, [data-testid="collapsedControl"]::before, [data-testid="stSidebarCollapseButton"]::before {
        content: "🍄‍🟫"; font-size: 1.7rem; line-height: 1;
    }
    .login-card {
        max-width: 460px; margin: 9vh auto 8px; padding: 40px 28px 24px;
        background: radial-gradient(500px 180px at 50% -20%, rgba(196,86,42,.28), transparent 70%),
            linear-gradient(165deg, rgba(10,22,14,.78), rgba(6,14,10,.52));
        border-radius: 36px 16px 36px 16px; border: 1px solid rgba(168,214,150,.32);
        box-shadow: 0 28px 70px rgba(0,0,0,.5); backdrop-filter: blur(22px);
        animation: fadeup .7s ease; text-align: center; color: #fff6e6; position: relative;
    }
    .login-card::before { content: "🍄‍🟫"; display: block; font-size: 2.4rem; margin-bottom: 8px; animation: floaty 5.5s ease-in-out infinite; }
    .login-card .kicker { letter-spacing: .26em; text-transform: uppercase; font-size: .68rem; color: #b7e0b0 !important; margin: 0 0 8px; font-family: 'Syne', sans-serif !important; }
    .login-card h1 { color: #fff6e6 !important; font-size: 2.35rem; margin: 0 0 8px; }
    .login-card p { color: #e7efe4 !important; margin: 0; }
    .login-card .chip-row { justify-content: center; }
    .login-wrap { max-width: 460px; margin: 0 auto 18vh; }
    .login-wrap [data-testid="stTextInput"] input {
        background: rgba(215,236,200,.1) !important; color: #fff8ea !important;
        border: 1px solid rgba(168,214,150,.35) !important; border-radius: 14px !important;
    }
    .login-wrap button[kind="primary"] {
        background: linear-gradient(180deg, #d86a38, #9a3d1c) !important; color: #fff8f0 !important; border: none !important; border-radius: 14px !important;
    }
    .hero {
        background: radial-gradient(520px 220px at 50% -40%, rgba(196,86,42,.28), transparent 60%),
            linear-gradient(160deg, rgba(8,20,14,.7), rgba(10,18,12,.38));
        border: 1px solid rgba(168,214,150,.28); border-radius: 40px 14px 40px 14px;
        padding: 28px 22px 22px; margin: 0 0 18px; backdrop-filter: blur(20px);
        box-shadow: 0 22px 50px rgba(0,0,0,.32); position: relative; overflow: hidden; text-align: center;
    }
    .hero-title { display: grid; grid-template-columns: 2.4rem minmax(0,1fr) 2.4rem; align-items: center; width: 100%; }
    .hero-fungo { font-size: clamp(1.6rem, 5vw, 2.4rem); text-align: center; }
    .hero h1 { font-size: clamp(1.7rem, 6.2vw, 3.1rem); margin: 0; text-align: center; }
    .hero .kicker { letter-spacing: .28em; text-transform: uppercase; font-size: .68rem; color: #b7e0b0 !important; margin: 0 0 8px; font-family: 'Syne', sans-serif !important; }
    .hero .lede, .login-card .lede {
        max-width: 22rem; opacity: .95; margin: 12px auto 0; line-height: 1.4;
        text-align: center !important; font-size: .95rem;
    }
    .hero .chip-row { justify-content: center; }
    .chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
    .chip {
        border: 1px solid rgba(168,214,150,.4); background: rgba(90,168,92,.12); color: #eaf6e6;
        border-radius: 999px; padding: 5px 13px; font-size: .76rem; letter-spacing: .08em; font-family: 'Syne', sans-serif;
    }
    .stApp [data-testid="stHeading"] h2 { border-bottom: 1px solid rgba(168,214,150,.22); padding-bottom: .35rem; }
    iframe, .stFolium, [data-testid="stIFrame"] {
        border-radius: 28px 10px 28px 10px !important; overflow: hidden;
        box-shadow: 0 16px 40px rgba(0,0,0,.3); border: 1px solid rgba(168,214,150,.22);
    }
    [data-testid="stExpander"] {
        background: rgba(8,18,12,.62) !important;
        border: 1px solid rgba(232,214,160,.4) !important;
        border-radius: 18px !important; margin-bottom: 10px;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary:hover,
    [data-testid="stExpander"] summary:focus,
    [data-testid="stExpander"] summary:active,
    [data-testid="stExpander"] details[open] > summary,
    [data-testid="stExpander"] button,
    [data-testid="stExpander"] button:hover,
    [data-testid="stExpander"] button:focus,
    [data-testid="stExpander"] button:active {
        background: #163016 !important;
        background-color: #163016 !important;
        color: #fff6e6 !important;
        box-shadow: none !important;
    }
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stExpander"] summary p {
        color: #fff6e6 !important;
        font-size: 1.12rem !important;
        font-weight: 700 !important;
    }
    .stProgress > div > div { background: linear-gradient(90deg, #6aa25c, #d86a38) !important; }
    [data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; }
    .bmap-table { overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100%; border-radius: 18px; border: 1px solid rgba(232,214,160,.28); background: rgba(10,22,14,.78); }
    .bmap-table table { width: max-content; min-width: 100%; border-collapse: collapse; color: #fff6e6; font-size: .88rem; }
    .bmap-table th { background: #163016; color: #e8d6a0; text-align: left; padding: 10px 12px; font-weight: 700; white-space: nowrap; }
    .bmap-table td { padding: 8px 12px; border-top: 1px solid rgba(168,214,150,.16); color: #f3ead2; white-space: nowrap; }
    .bmap-table tr:nth-child(even) td { background: rgba(22,48,22,.45); }
    [data-testid="stSidebar"] .block-container { padding-top: .6rem; }
    [data-testid="stSidebar"] hr { border-color: rgba(168,214,150,.2) !important; }
    [data-testid="stSidebar"] [data-testid="stCheckbox"] {
        background: rgba(215,236,200,.06); border: 1px solid rgba(168,214,150,.2);
        border-radius: 14px; padding: 2px 8px; margin-bottom: 6px;
    }
    [data-testid="stSidebar"] [data-testid="stCheckbox"]:hover { border-color: rgba(168,214,150,.5); background: rgba(90,168,92,.14); }
    [data-testid="stSidebar"] [data-baseweb="checkbox"] span[data-checked="true"] { background: #d86a38 !important; border-color: #d86a38 !important; }
    [data-testid="stSidebar"] .stSlider [role="slider"] { background-color: #d86a38 !important; border: 2px solid #f3ead2 !important; }
    [data-testid="stSidebar"] .stSlider > div > div > div > div { background: linear-gradient(90deg, #3f6d3a, #d86a38) !important; }
    [data-testid="stSidebar"] [data-testid="stTextInput"] input,
    [data-testid="stSidebar"] input[type="text"],
    [data-testid="stSidebar"] input[type="search"] {
        background: #10210f !important;
        color: #f4ffe8 !important;
        -webkit-text-fill-color: #f4ffe8 !important;
        caret-color: #d86a38 !important;
        border: 1px solid #6aa25c !important;
        border-radius: 12px !important;
    }
    [data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
        color: #9cbf96 !important;
        -webkit-text-fill-color: #9cbf96 !important;
        opacity: 1 !important;
    }
    .side-hero {
        background: radial-gradient(280px 120px at 20% 0%, rgba(196,86,42,.22), transparent 70%),
            linear-gradient(180deg, rgba(215,236,200,.1), rgba(8,18,12,.08));
        border: 1px solid rgba(168,214,150,.24); border-radius: 20px; padding: 16px 14px 14px; margin: 0 0 14px; text-align: center;
    }
    .side-hero-emoji { font-size: 2.4rem; animation: floaty 5.5s ease-in-out infinite; }
    .side-hero h3 { margin: 0; font-size: 1.45rem; }
    .side-hero p { margin: 6px 0 0; font-size: .86rem; opacity: .9; }
    .side-quote { font-family: 'Fraunces', serif !important; font-style: italic; font-size: .92rem !important; line-height: 1.45 !important; text-align: left; color: #e7efe4 !important; }
        </style>
    """.replace("__SFONDO__", _sfondo),
    unsafe_allow_html=True,
)
if "app_ok" not in st.session_state:
    st.session_state["app_ok"] = False
if "ruolo" not in st.session_state:
    st.session_state["ruolo"] = "guest"

if not st.session_state["app_ok"]:
    st.markdown(
        """
        <div class="login-card">
          <p class="kicker">Centro Italia</p>
          <h1>Boletus Map</h1>
          <p class="lede">Mappa interattiva crescita Boletus<br>&amp;<br>Mappa Live piogge (dati presi direttamente dal sito della Protezione Civile)</p>
          <div class="chip-row">
            <span class="chip">Abruzzo</span>
            <span class="chip">Molise</span>
            <span class="chip">Lazio</span>
            <span class="chip">Campania</span>
            <span class="chip">Marche</span>
            <span class="chip">Umbria</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    pw = st.text_input("Password", type="password", placeholder="Password del bosco", label_visibility="collapsed")
    if st.button("Entra nel bosco", type="primary", use_container_width=True):
        if pw == GUEST_PASS:
            st.session_state["app_ok"] = True
            st.session_state["ruolo"] = "guest"
            st.rerun()
        else:
            st.error("Password errata")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

IS_ADMIN = False

# attesa pioggia (FM): faggio 15 | castagno 13 | quercia 12 — durata buttata 15-20 gg
PUNTI = [
    # ===================== ABRUZZO =====================
    {"nome": "Gran Sasso - Campo Imperatore", "lat": 42.450, "lon": 13.550, "tipo": "faggio", "quota": 1600, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Pietracamela", "lat": 42.510, "lon": 13.555, "tipo": "faggio", "quota": 1500, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Prati di Tivo", "lat": 42.505, "lon": 13.570, "tipo": "faggio", "quota": 1450, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Castelli", "lat": 42.488, "lon": 13.712, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Santo Stefano di Sessanio", "lat": 42.343, "lon": 13.644, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Majella - Blockhaus", "lat": 42.140, "lon": 14.110, "tipo": "faggio", "quota": 1700, "regione": "Abruzzo"},
    {"nome": "Majella - Passolanciano", "lat": 42.170, "lon": 14.120, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Majella - Caramanico Terme", "lat": 42.156, "lon": 14.005, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Majella - Pacentro", "lat": 42.050, "lon": 13.995, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Majella - Palena", "lat": 41.984, "lon": 14.137, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Majella - Pescocostanzo", "lat": 41.887, "lon": 14.066, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Majella - Rivisondoli", "lat": 41.871, "lon": 14.070, "tipo": "faggio", "quota": 1350, "regione": "Abruzzo"},
    {"nome": "Sirente-Velino - Ovindoli", "lat": 42.137, "lon": 13.527, "tipo": "faggio", "quota": 1450, "regione": "Abruzzo"},
    {"nome": "Sirente-Velino - Rocca di Mezzo", "lat": 42.206, "lon": 13.519, "tipo": "faggio", "quota": 1320, "regione": "Abruzzo"},
    {"nome": "Sirente-Velino - Celano", "lat": 42.085, "lon": 13.540, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Campotosto", "lat": 42.560, "lon": 13.330, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Amatrice lato Abruzzo", "lat": 42.630, "lon": 13.350, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Pescasseroli", "lat": 41.808, "lon": 13.789, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Opi", "lat": 41.780, "lon": 13.830, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Villetta Barrea", "lat": 41.776, "lon": 13.939, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Civitella Alfedena", "lat": 41.765, "lon": 13.943, "tipo": "faggio", "quota": 1120, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Scanno", "lat": 41.904, "lon": 13.879, "tipo": "faggio", "quota": 1050, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Villalago", "lat": 41.935, "lon": 13.836, "tipo": "faggio", "quota": 930, "regione": "Abruzzo"},
    {"nome": "Monti Marsicani - Gioia dei Marsi", "lat": 41.955, "lon": 13.690, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Altopiano delle Cinquemiglia", "lat": 41.870, "lon": 14.050, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Bosco di Sant'Antonio - Pescocostanzo", "lat": 41.900, "lon": 14.050, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Castel del Giudice lato Abruzzo", "lat": 41.860, "lon": 14.230, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Roccaraso", "lat": 41.850, "lon": 14.078, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Pescocostanzo faggete", "lat": 41.895, "lon": 14.080, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Chieti collinare - Guardiagrele", "lat": 42.190, "lon": 14.220, "tipo": "quercia", "quota": 600, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Cermignano", "lat": 42.590, "lon": 13.800, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Monti Frentani - Palombaro", "lat": 42.125, "lon": 14.230, "tipo": "castagno", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Assergi / Fonte Cerreto", "lat": 42.410, "lon": 13.508, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Isola del Gran Sasso", "lat": 42.503, "lon": 13.655, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Farindola", "lat": 42.443, "lon": 13.822, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Castel del Monte", "lat": 42.365, "lon": 13.726, "tipo": "faggio", "quota": 1350, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Calascio", "lat": 42.327, "lon": 13.697, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Campo Felice - Lucoli", "lat": 42.257, "lon": 13.394, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Sirente - Rocca di Cambio", "lat": 42.236, "lon": 13.488, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Sirente - Secinaro", "lat": 42.153, "lon": 13.681, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Sirente - Gagliano Aterno", "lat": 42.125, "lon": 13.700, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Velino - Magliano de' Marsi", "lat": 42.092, "lon": 13.364, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Cortino", "lat": 42.622, "lon": 13.508, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Rocca Santa Maria", "lat": 42.687, "lon": 13.528, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Valle Castellana", "lat": 42.736, "lon": 13.497, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Crognaleto", "lat": 42.588, "lon": 13.489, "tipo": "faggio", "quota": 1150, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Barrea", "lat": 41.756, "lon": 13.993, "tipo": "faggio", "quota": 1060, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Alfedena", "lat": 41.737, "lon": 14.035, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Scontrone", "lat": 41.747, "lon": 14.039, "tipo": "faggio", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Bisegna", "lat": 41.921, "lon": 13.758, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Ortona dei Marsi", "lat": 41.997, "lon": 13.728, "tipo": "faggio", "quota": 1050, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Villavallelonga", "lat": 41.867, "lon": 13.621, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Collelongo", "lat": 41.887, "lon": 13.585, "tipo": "faggio", "quota": 950, "regione": "Abruzzo"},
    {"nome": "Val Fondillo / Camosciara", "lat": 41.767, "lon": 13.852, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Passo Godi", "lat": 41.850, "lon": 13.920, "tipo": "faggio", "quota": 1550, "regione": "Abruzzo"},
    {"nome": "Monte Greco - Castel di Sangro", "lat": 41.784, "lon": 14.107, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Pescocostanzo / Aremogna", "lat": 41.830, "lon": 14.050, "tipo": "faggio", "quota": 1500, "regione": "Abruzzo"},
    {"nome": "Majella - Pretoro", "lat": 42.220, "lon": 14.143, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Majella - Pennapiedimonte", "lat": 42.155, "lon": 14.194, "tipo": "faggio", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Majella - Fara San Martino", "lat": 42.090, "lon": 14.205, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Majella - Lama dei Peligni", "lat": 42.043, "lon": 14.187, "tipo": "faggio", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Majella - Lettopalena", "lat": 41.983, "lon": 14.157, "tipo": "faggio", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Majella - Roccamorice", "lat": 42.213, "lon": 14.028, "tipo": "faggio", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Majella - Abbateggio", "lat": 42.224, "lon": 14.013, "tipo": "quercia", "quota": 500, "regione": "Abruzzo"},
    {"nome": "Morrone - Pacentro / Sulmona", "lat": 42.051, "lon": 13.948, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Morrone - Popoli", "lat": 42.174, "lon": 13.832, "tipo": "quercia", "quota": 500, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Gamberale", "lat": 41.904, "lon": 14.208, "tipo": "faggio", "quota": 1350, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Pizzoferrato", "lat": 41.919, "lon": 14.236, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Quadri", "lat": 41.924, "lon": 14.288, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Alto Vastese - Castiglione Messer Marino", "lat": 41.868, "lon": 14.452, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Alto Vastese - Schiavi d'Abruzzo", "lat": 41.815, "lon": 14.485, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Frentani - Roccascalegna", "lat": 42.062, "lon": 14.308, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Frentani - Gessopalena", "lat": 42.055, "lon": 14.273, "tipo": "castagno", "quota": 650, "regione": "Abruzzo"},
    {"nome": "Frentani - Torricella Peligna", "lat": 42.025, "lon": 14.259, "tipo": "castagno", "quota": 750, "regione": "Abruzzo"},
    # Val di Sangro / Costa dei Trabocchi / Vastese (macrozona Atessa-Gissi-Vasto)
    {"nome": "Lecceta di Torino di Sangro", "lat": 42.227, "lon": 14.548, "tipo": "quercia", "quota": 80, "regione": "Abruzzo"},
    {"nome": "Boschi ripariali Fiume Osento", "lat": 42.167, "lon": 14.531, "tipo": "quercia", "quota": 80, "regione": "Abruzzo"},
    {"nome": "Bosco di Don Venanzio - Pollutri", "lat": 42.138, "lon": 14.615, "tipo": "quercia", "quota": 30, "regione": "Abruzzo"},
    {"nome": "Punta Aderci - foce Sinello", "lat": 42.175, "lon": 14.678, "tipo": "quercia", "quota": 25, "regione": "Abruzzo"},
    {"nome": "Bosco di Mozzagrogna / Sangro", "lat": 42.164, "lon": 14.448, "tipo": "quercia", "quota": 120, "regione": "Abruzzo"},
    {"nome": "Atessa - Fontecampana / Vallaspra", "lat": 42.070, "lon": 14.430, "tipo": "quercia", "quota": 400, "regione": "Abruzzo"},
    {"nome": "Monte Pallano - crinale", "lat": 42.038, "lon": 14.405, "tipo": "faggio", "quota": 950, "regione": "Abruzzo"},
    {"nome": "Monte Pallano - Lecceta Isca d'Archi", "lat": 42.090, "lon": 14.380, "tipo": "quercia", "quota": 450, "regione": "Abruzzo"},
    {"nome": "Tornareccio - cerrete Pallano", "lat": 42.030, "lon": 14.420, "tipo": "quercia", "quota": 600, "regione": "Abruzzo"},
    {"nome": "Bomba - versante Pallano", "lat": 42.033, "lon": 14.367, "tipo": "quercia", "quota": 450, "regione": "Abruzzo"},
    {"nome": "Archi - Isca d'Archi", "lat": 42.090, "lon": 14.381, "tipo": "quercia", "quota": 440, "regione": "Abruzzo"},
    {"nome": "Gissi - colline cerrete", "lat": 42.020, "lon": 14.548, "tipo": "quercia", "quota": 480, "regione": "Abruzzo"},
    {"nome": "Monte Sorbo - Carpineto Sinello", "lat": 41.990, "lon": 14.520, "tipo": "quercia", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Carpineto Sinello - Colle S. Giovanni", "lat": 41.965, "lon": 14.534, "tipo": "castagno", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Carunchio - Bosco Carunchino", "lat": 41.910, "lon": 14.530, "tipo": "quercia", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Palmoli - Fiume Treste", "lat": 41.940, "lon": 14.580, "tipo": "quercia", "quota": 650, "regione": "Abruzzo"},
    {"nome": "San Buono - Frentani", "lat": 41.981, "lon": 14.571, "tipo": "quercia", "quota": 480, "regione": "Abruzzo"},
    {"nome": "Casoli - Lecceta Colleforeste", "lat": 42.120, "lon": 14.290, "tipo": "quercia", "quota": 350, "regione": "Abruzzo"},
    {"nome": "Fossacesia - collina Trabocchi", "lat": 42.250, "lon": 14.450, "tipo": "quercia", "quota": 80, "regione": "Abruzzo"},
    {"nome": "Casalbordino - collina Osento", "lat": 42.150, "lon": 14.590, "tipo": "quercia", "quota": 200, "regione": "Abruzzo"},
    {"nome": "Scerni - querceti", "lat": 42.110, "lon": 14.570, "tipo": "quercia", "quota": 250, "regione": "Abruzzo"},
    {"nome": "Paglieta - boschi Sangro", "lat": 42.160, "lon": 14.430, "tipo": "quercia", "quota": 200, "regione": "Abruzzo"},
    {"nome": "Cupello - hinterland Vasto", "lat": 42.050, "lon": 14.620, "tipo": "quercia", "quota": 220, "regione": "Abruzzo"},
    {"nome": "Villalfonsina - Osento", "lat": 42.160, "lon": 14.570, "tipo": "quercia", "quota": 150, "regione": "Abruzzo"},
    {"nome": "Lanciano - colline boschive", "lat": 42.218, "lon": 14.390, "tipo": "quercia", "quota": 280, "regione": "Abruzzo"},
    {"nome": "Vasto - collina Penna", "lat": 42.110, "lon": 14.708, "tipo": "quercia", "quota": 140, "regione": "Abruzzo"},
    {"nome": "Casalanguida - colline", "lat": 42.039, "lon": 14.488, "tipo": "quercia", "quota": 520, "regione": "Abruzzo"},
    {"nome": "Furci - Frentani", "lat": 41.950, "lon": 14.580, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Montazzoli - Alto Vastese", "lat": 41.983, "lon": 14.450, "tipo": "castagno", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Rosello - Abetina", "lat": 41.858, "lon": 14.350, "tipo": "faggio", "quota": 950, "regione": "Abruzzo"},
    {"nome": "Lentella - colline Trigno", "lat": 41.997, "lon": 14.677, "tipo": "quercia", "quota": 400, "regione": "Abruzzo"},
    {"nome": "Colline Vestine - Penne", "lat": 42.455, "lon": 13.930, "tipo": "quercia", "quota": 450, "regione": "Abruzzo"},
    {"nome": "Carsoli - Oricola / Pereto", "lat": 42.049, "lon": 13.039, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Tagliacozzo - Cappadocia", "lat": 42.008, "lon": 13.280, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Marsica - Cocullo", "lat": 42.033, "lon": 13.775, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Civitella del Tronto", "lat": 42.773, "lon": 13.675, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Campli", "lat": 42.726, "lon": 13.686, "tipo": "quercia", "quota": 500, "regione": "Abruzzo"},

    # ===================== MOLISE =====================
    {"nome": "Capracotta - faggete", "lat": 41.834, "lon": 14.265, "tipo": "faggio", "quota": 1420, "regione": "Molise"},
    {"nome": "Pescopennataro - Abeti Soprani", "lat": 41.861, "lon": 14.294, "tipo": "faggio", "quota": 1450, "regione": "Molise"},
    {"nome": "Vastogirardi - Bosco Pennataro", "lat": 41.749, "lon": 14.197, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Collemeluccio - Selvapiana", "lat": 41.718, "lon": 14.350, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Montedimezzo", "lat": 41.775, "lon": 14.261, "tipo": "faggio", "quota": 1000, "regione": "Molise"},
    {"nome": "Agnone - Alto Molise", "lat": 41.810, "lon": 14.379, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Carovilli", "lat": 41.714, "lon": 14.296, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Frosolone - Montagnola", "lat": 41.601, "lon": 14.449, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Mainarde - Castel San Vincenzo", "lat": 41.656, "lon": 14.061, "tipo": "faggio", "quota": 1200, "regione": "Molise"},
    {"nome": "Pizzone - Mainarde", "lat": 41.667, "lon": 14.034, "tipo": "faggio", "quota": 1300, "regione": "Molise"},
    {"nome": "Rocchetta a Volturno", "lat": 41.629, "lon": 14.091, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Cerro al Volturno", "lat": 41.657, "lon": 14.102, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Bojano - versante Matese", "lat": 41.485, "lon": 14.473, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Guardiaregia - Matese", "lat": 41.436, "lon": 14.504, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "San Massimo - Matese", "lat": 41.490, "lon": 14.410, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Cantalupo nel Sannio", "lat": 41.523, "lon": 14.394, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Campitello Matese", "lat": 41.463, "lon": 14.394, "tipo": "faggio", "quota": 1450, "regione": "Molise"},
    {"nome": "Monte Miletto", "lat": 41.452, "lon": 14.350, "tipo": "faggio", "quota": 1700, "regione": "Molise"},
    {"nome": "Roccamandolfi - Matese", "lat": 41.493, "lon": 14.351, "tipo": "faggio", "quota": 1400, "regione": "Molise"},
    {"nome": "Pietrabbondante", "lat": 41.748, "lon": 14.385, "tipo": "castagno", "quota": 800, "regione": "Molise"},
    {"nome": "San Pietro Avellana", "lat": 41.792, "lon": 14.183, "tipo": "faggio", "quota": 960, "regione": "Molise"},
    {"nome": "Castel del Giudice", "lat": 41.856, "lon": 14.232, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Isernia - Pineta e colline", "lat": 41.594, "lon": 14.231, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Campobasso - colline boschive", "lat": 41.560, "lon": 14.660, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Capracotta - Prato Gentile", "lat": 41.850, "lon": 14.280, "tipo": "faggio", "quota": 1600, "regione": "Molise"},
    {"nome": "Monte Capraro", "lat": 41.820, "lon": 14.250, "tipo": "faggio", "quota": 1700, "regione": "Molise"},
    {"nome": "Monte Campo", "lat": 41.800, "lon": 14.310, "tipo": "faggio", "quota": 1740, "regione": "Molise"},
    {"nome": "Pescolanciano", "lat": 41.679, "lon": 14.248, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Roccasicura", "lat": 41.697, "lon": 14.236, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Rionero Sannitico", "lat": 41.713, "lon": 14.140, "tipo": "faggio", "quota": 1050, "regione": "Molise"},
    {"nome": "Forlì del Sannio", "lat": 41.695, "lon": 14.180, "tipo": "faggio", "quota": 600, "regione": "Molise"},
    {"nome": "Acquaviva d'Isernia", "lat": 41.673, "lon": 14.148, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Sessano del Molise", "lat": 41.639, "lon": 14.328, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Chiauci", "lat": 41.677, "lon": 14.385, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Civitanova del Sannio", "lat": 41.667, "lon": 14.393, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Bagnoli del Trigno", "lat": 41.703, "lon": 14.451, "tipo": "castagno", "quota": 750, "regione": "Molise"},
    {"nome": "Salcito", "lat": 41.726, "lon": 14.511, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Trivento", "lat": 41.776, "lon": 14.546, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Poggio Sannita", "lat": 41.779, "lon": 14.584, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Belmonte del Sannio", "lat": 41.824, "lon": 14.423, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Castelverrino", "lat": 41.766, "lon": 14.397, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Longano", "lat": 41.522, "lon": 14.247, "tipo": "faggio", "quota": 700, "regione": "Molise"},
    {"nome": "Castelpizzuto", "lat": 41.519, "lon": 14.292, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Santa Maria del Molise", "lat": 41.553, "lon": 14.367, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Macchiagodena", "lat": 41.560, "lon": 14.409, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Sant'Elena Sannita", "lat": 41.575, "lon": 14.472, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Duronia", "lat": 41.659, "lon": 14.460, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Torella del Sannio", "lat": 41.640, "lon": 14.521, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Casalciprano", "lat": 41.580, "lon": 14.529, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Spinete", "lat": 41.544, "lon": 14.488, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "San Polo Matese", "lat": 41.460, "lon": 14.495, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Campochiaro", "lat": 41.448, "lon": 14.507, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Sepino", "lat": 41.408, "lon": 14.617, "tipo": "faggio", "quota": 700, "regione": "Molise"},
    {"nome": "Sassinoro", "lat": 41.375, "lon": 14.665, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Cercemaggiore", "lat": 41.461, "lon": 14.724, "tipo": "castagno", "quota": 800, "regione": "Molise"},
    {"nome": "Riccia", "lat": 41.483, "lon": 14.836, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Campolieto", "lat": 41.633, "lon": 14.767, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Castropignano", "lat": 41.619, "lon": 14.559, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Filignano", "lat": 41.545, "lon": 14.057, "tipo": "faggio", "quota": 650, "regione": "Molise"},
    {"nome": "Scapoli", "lat": 41.615, "lon": 14.059, "tipo": "faggio", "quota": 650, "regione": "Molise"},
    {"nome": "Colli a Volturno", "lat": 41.599, "lon": 14.103, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Montaquila", "lat": 41.562, "lon": 14.119, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Venafro - monti", "lat": 41.483, "lon": 14.045, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Conca Casale", "lat": 41.496, "lon": 14.007, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Miranda", "lat": 41.643, "lon": 14.247, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Pesche", "lat": 41.617, "lon": 14.278, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    # Boschi interni Molise mancanti (Alto Molise, Montagnola, Biferno, Fortore)
    {"nome": "Pesche - Monte Totila", "lat": 41.630, "lon": 14.300, "tipo": "faggio", "quota": 950, "regione": "Molise"},
    {"nome": "Collemeluccio - abetine", "lat": 41.705, "lon": 14.347, "tipo": "abete_bianco", "quota": 950, "regione": "Molise"},
    {"nome": "Selvapiana - Castiglione La Cocozza", "lat": 41.730, "lon": 14.320, "tipo": "faggio", "quota": 1000, "regione": "Molise"},
    {"nome": "Monte Miglio - Pennataro", "lat": 41.770, "lon": 14.210, "tipo": "faggio", "quota": 1200, "regione": "Molise"},
    {"nome": "Monte Cavallerizzo", "lat": 41.760, "lon": 14.230, "tipo": "faggio", "quota": 1150, "regione": "Molise"},
    {"nome": "Monte Castelbarone", "lat": 41.845, "lon": 14.250, "tipo": "faggio", "quota": 1300, "regione": "Molise"},
    {"nome": "Sorgenti del Verde - Pescopennataro", "lat": 41.855, "lon": 14.270, "tipo": "abete_bianco", "quota": 1400, "regione": "Molise"},
    {"nome": "Isola della Fonte della Luna", "lat": 41.790, "lon": 14.220, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Bosco Vallazzuna", "lat": 41.780, "lon": 14.300, "tipo": "faggio", "quota": 950, "regione": "Molise"},
    {"nome": "Pescolanciano - cerrete MaB", "lat": 41.680, "lon": 14.248, "tipo": "quercia", "quota": 800, "regione": "Molise"},
    {"nome": "Cerreto sul Volturno", "lat": 41.659, "lon": 14.102, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Montagnola Molisana - Frosolone est", "lat": 41.590, "lon": 14.480, "tipo": "faggio", "quota": 1200, "regione": "Molise"},
    {"nome": "Montagnola - Civitanova / Chiauci", "lat": 41.660, "lon": 14.400, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Roccavivara - faggete interne", "lat": 41.833, "lon": 14.598, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Castelmauro - colline interne", "lat": 41.830, "lon": 14.711, "tipo": "quercia", "quota": 700, "regione": "Molise"},
    {"nome": "Montefalcone nel Sannio - Selva", "lat": 41.755, "lon": 14.638, "tipo": "quercia", "quota": 750, "regione": "Molise"},
    {"nome": "Monte Mauro - Selva di Montefalcone", "lat": 41.740, "lon": 14.620, "tipo": "quercia", "quota": 800, "regione": "Molise"},
    {"nome": "Bosco Cerreto - Molise interno", "lat": 41.620, "lon": 14.700, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Bosco Ficarola", "lat": 41.640, "lon": 14.740, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Bosco Difesa - Ripabottoni", "lat": 41.688, "lon": 14.809, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Boschi di Castellino e Morrone", "lat": 41.650, "lon": 14.770, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Morrone del Sannio", "lat": 41.712, "lon": 14.776, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Castellino del Biferno", "lat": 41.702, "lon": 14.732, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Lucito", "lat": 41.632, "lon": 14.687, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Petrella Tifernina", "lat": 41.692, "lon": 14.697, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Limosano", "lat": 41.676, "lon": 14.623, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Civitacampomarano", "lat": 41.780, "lon": 14.689, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Oratino", "lat": 41.586, "lon": 14.584, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Busso", "lat": 41.558, "lon": 14.561, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Baranello", "lat": 41.526, "lon": 14.560, "tipo": "castagno", "quota": 640, "regione": "Molise"},
    {"nome": "Vinchiaturo - Sella / Monte Vairano", "lat": 41.493, "lon": 14.592, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "San Giuliano del Sannio", "lat": 41.456, "lon": 14.641, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Guardiaregia - Oasi WWF", "lat": 41.436, "lon": 14.543, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Casacalenda - boschi Fortore", "lat": 41.738, "lon": 14.847, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Bonefro", "lat": 41.705, "lon": 14.933, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Sant'Elia a Pianisi", "lat": 41.622, "lon": 14.875, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Ripabottoni", "lat": 41.688, "lon": 14.809, "tipo": "quercia", "quota": 620, "regione": "Molise"},
    {"nome": "Colletorto", "lat": 41.662, "lon": 14.968, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "San Giovanni in Galdo", "lat": 41.590, "lon": 14.750, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Toro", "lat": 41.573, "lon": 14.762, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Jelsi", "lat": 41.518, "lon": 14.798, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Gildone", "lat": 41.508, "lon": 14.740, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Ferrazzano", "lat": 41.530, "lon": 14.672, "tipo": "quercia", "quota": 700, "regione": "Molise"},
    {"nome": "Mirabello Sannitico", "lat": 41.515, "lon": 14.673, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Campodipietra", "lat": 41.557, "lon": 14.743, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Cantalupo nel Sannio - faggete", "lat": 41.523, "lon": 14.394, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Valle Porcina - Vandra", "lat": 41.620, "lon": 14.080, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Monte Sammucro - Corno", "lat": 41.590, "lon": 13.980, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Monte Cesima", "lat": 41.520, "lon": 13.990, "tipo": "faggio", "quota": 1000, "regione": "Molise"},

    # ===================== LAZIO =====================
    {"nome": "Terminillo", "lat": 42.473, "lon": 12.997, "tipo": "faggio", "quota": 1500, "regione": "Lazio"},
    {"nome": "Terminillo - Pian de Valli", "lat": 42.466, "lon": 12.987, "tipo": "faggio", "quota": 1600, "regione": "Lazio"},
    {"nome": "Monti della Laga - Amatrice", "lat": 42.628, "lon": 13.290, "tipo": "faggio", "quota": 1300, "regione": "Lazio"},
    {"nome": "Monti della Laga - Accumoli", "lat": 42.694, "lon": 13.247, "tipo": "faggio", "quota": 1200, "regione": "Lazio"},
    {"nome": "Monti Reatini - Leonessa", "lat": 42.569, "lon": 12.960, "tipo": "faggio", "quota": 1100, "regione": "Lazio"},
    {"nome": "Monti Reatini - Cittareale", "lat": 42.617, "lon": 13.158, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Simbruini - Vallepietra", "lat": 41.926, "lon": 13.231, "tipo": "faggio", "quota": 1200, "regione": "Lazio"},
    {"nome": "Simbruini - Subiaco", "lat": 41.925, "lon": 13.093, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Simbruini - Camerata Nuova", "lat": 42.018, "lon": 13.106, "tipo": "faggio", "quota": 1100, "regione": "Lazio"},
    {"nome": "Simbruini - Filettino", "lat": 41.883, "lon": 13.325, "tipo": "faggio", "quota": 1100, "regione": "Lazio"},
    {"nome": "Ernici - Guarcino", "lat": 41.799, "lon": 13.314, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Ernici - Fiuggi boschi", "lat": 41.797, "lon": 13.220, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Monti Lucretili - Licenza", "lat": 42.074, "lon": 12.900, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Lucretili - Palombara", "lat": 42.068, "lon": 12.768, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Monti Prenestini - Capranica Prenestina", "lat": 41.863, "lon": 13.001, "tipo": "castagno", "quota": 850, "regione": "Lazio"},
    {"nome": "Castelli Romani - Nemi / Velletri", "lat": 41.718, "lon": 12.714, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Castelli Romani - Monte Cavo", "lat": 41.750, "lon": 12.717, "tipo": "castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Monti Lepini - Carpineto Romano", "lat": 41.605, "lon": 13.085, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Monti Lepini - Norma", "lat": 41.585, "lon": 12.972, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Ausoni - Sonnino", "lat": 41.414, "lon": 13.244, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Aurunci - Maranola", "lat": 41.290, "lon": 13.627, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Aurunci - Itri boschi", "lat": 41.290, "lon": 13.530, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Cimini - Soriano nel Cimino", "lat": 42.418, "lon": 12.234, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Cimini - Viterbo faggete", "lat": 42.400, "lon": 12.180, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Monte Amiata laziale / Alto Lazio", "lat": 42.700, "lon": 11.850, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Monti della Tolfa", "lat": 42.150, "lon": 11.950, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Sabini - Poggio Moiano", "lat": 42.200, "lon": 12.880, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Sabina - Tarano / San Polo", "lat": 42.357, "lon": 12.597, "tipo": "quercia", "quota": 280, "regione": "Lazio"},
    {"nome": "Sabina - Montebuono", "lat": 42.368, "lon": 12.594, "tipo": "quercia", "quota": 300, "regione": "Lazio"},
    {"nome": "Sabina - Collevecchio boschi", "lat": 42.333, "lon": 12.553, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Sabina - Torri in Sabina", "lat": 42.353, "lon": 12.638, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Sabina - Casperia / Roccantica", "lat": 42.330, "lon": 12.672, "tipo": "castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Sabina - Cottanello", "lat": 42.406, "lon": 12.685, "tipo": "quercia", "quota": 550, "regione": "Lazio"},
    {"nome": "Sabina - Magliano Sabina", "lat": 42.361, "lon": 12.483, "tipo": "quercia", "quota": 220, "regione": "Lazio"},
    {"nome": "Sabina - Stimigliano / Selci", "lat": 42.300, "lon": 12.563, "tipo": "quercia", "quota": 220, "regione": "Lazio"},
    {"nome": "Sabina - Poggio Mirteto", "lat": 42.268, "lon": 12.688, "tipo": "quercia", "quota": 350, "regione": "Lazio"},
    {"nome": "Sabina - Montopoli di Sabina", "lat": 42.247, "lon": 12.692, "tipo": "quercia", "quota": 300, "regione": "Lazio"},
    {"nome": "Sabina - Fara in Sabina / Farfa", "lat": 42.209, "lon": 12.718, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Sabina - Poggio Catino", "lat": 42.293, "lon": 12.698, "tipo": "castagno", "quota": 450, "regione": "Lazio"},
    {"nome": "Sabina - Toffia", "lat": 42.215, "lon": 12.755, "tipo": "quercia", "quota": 280, "regione": "Lazio"},
    {"nome": "Riserva Tevere-Farfa - Nazzano", "lat": 42.229, "lon": 12.611, "tipo": "quercia", "quota": 80, "regione": "Lazio"},
    {"nome": "Monte Soratte - Sant'Oreste", "lat": 42.233, "lon": 12.525, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Sabina - Vacone / Configni", "lat": 42.385, "lon": 12.645, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Sabina - Greccio boschi", "lat": 42.455, "lon": 12.755, "tipo": "quercia", "quota": 550, "regione": "Lazio"},
    {"nome": "Sabina - Contigliano", "lat": 42.411, "lon": 12.766, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Parco dei Monti Simbruini - Cervara", "lat": 41.988, "lon": 13.067, "tipo": "faggio", "quota": 1050, "regione": "Lazio"},
    {"nome": "Terminillo - Micigliano", "lat": 42.452, "lon": 13.053, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Terminillo - Posta", "lat": 42.525, "lon": 13.097, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Reatini - Antrodoco", "lat": 42.416, "lon": 13.079, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Monti Reatini - Morro Reatino", "lat": 42.449, "lon": 12.834, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Reatini - Rivodutri", "lat": 42.517, "lon": 12.856, "tipo": "quercia", "quota": 550, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Fiamignano", "lat": 42.268, "lon": 13.126, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Pescorocchiano", "lat": 42.207, "lon": 13.146, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Petrella Salto", "lat": 42.296, "lon": 13.068, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Varco Sabino", "lat": 42.240, "lon": 13.019, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Sabina - Orvinio", "lat": 42.133, "lon": 12.993, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Sabina - Collalto Sabino", "lat": 42.226, "lon": 13.049, "tipo": "faggio", "quota": 950, "regione": "Lazio"},
    {"nome": "Sabina - Turania", "lat": 42.139, "lon": 13.008, "tipo": "castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Lucretili - Percile", "lat": 42.095, "lon": 12.905, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Lucretili - Orvinio / Pozzaglia", "lat": 42.170, "lon": 12.964, "tipo": "castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Lucretili - Monte Gennaro", "lat": 42.055, "lon": 12.833, "tipo": "castagno", "quota": 1000, "regione": "Lazio"},
    {"nome": "Lucretili - Monteflavio", "lat": 42.109, "lon": 12.831, "tipo": "castagno", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Monte Livata", "lat": 41.950, "lon": 13.120, "tipo": "faggio", "quota": 1400, "regione": "Lazio"},
    {"nome": "Simbruini - Jenne", "lat": 41.889, "lon": 13.169, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Trevi nel Lazio", "lat": 41.863, "lon": 13.253, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Simbruini - Altipiani di Arcinazzo", "lat": 41.879, "lon": 13.114, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Rocca di Botte", "lat": 42.026, "lon": 13.068, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Ernici - Collepardo", "lat": 41.765, "lon": 13.368, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Ernici - Vico nel Lazio", "lat": 41.777, "lon": 13.341, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Ernici - Veroli", "lat": 41.691, "lon": 13.418, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Ernici - Alatri", "lat": 41.726, "lon": 13.342, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - San Donato", "lat": 41.708, "lon": 13.813, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Valle di Comino - Settefrati", "lat": 41.670, "lon": 13.851, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Valle di Comino - Picinisco", "lat": 41.647, "lon": 13.868, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Valle di Comino - Villa Latina", "lat": 41.615, "lon": 13.836, "tipo": "faggio", "quota": 600, "regione": "Lazio"},
    {"nome": "Valle di Comino - Atina", "lat": 41.620, "lon": 13.802, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - Alvito", "lat": 41.690, "lon": 13.744, "tipo": "faggio", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - Pescosolido", "lat": 41.749, "lon": 13.657, "tipo": "faggio", "quota": 550, "regione": "Lazio"},
    {"nome": "Valle di Comino - Campoli Appennino", "lat": 41.736, "lon": 13.683, "tipo": "faggio", "quota": 650, "regione": "Lazio"},
    {"nome": "Mainarde laziali - Vallerotonda", "lat": 41.551, "lon": 13.911, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Mainarde laziali - San Biagio Saracinisco", "lat": 41.613, "lon": 13.932, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Cassinate - Terelle", "lat": 41.552, "lon": 13.778, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Prenestini - Capranica / Piglio", "lat": 41.828, "lon": 13.144, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Lepini - Segni", "lat": 41.690, "lon": 13.016, "tipo": "castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Lepini - Montelanico", "lat": 41.651, "lon": 13.040, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Lepini - Bassiano", "lat": 41.549, "lon": 13.088, "tipo": "faggio", "quota": 550, "regione": "Lazio"},
    {"nome": "Lepini - Sezze / Sermoneta", "lat": 41.498, "lon": 13.060, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Ausoni - Priverno", "lat": 41.472, "lon": 13.181, "tipo": "quercia", "quota": 150, "regione": "Lazio"},
    {"nome": "Ausoni - Prossedi / Roccagorga", "lat": 41.500, "lon": 13.236, "tipo": "quercia", "quota": 300, "regione": "Lazio"},
    {"nome": "Ausoni - Lenola", "lat": 41.339, "lon": 13.359, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Ausoni - Campodimele", "lat": 41.388, "lon": 13.386, "tipo": "castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Aurunci - Spigno Saturnia", "lat": 41.297, "lon": 13.735, "tipo": "quercia", "quota": 200, "regione": "Lazio"},
    {"nome": "Aurunci - Esperia", "lat": 41.385, "lon": 13.685, "tipo": "quercia", "quota": 350, "regione": "Lazio"},
    {"nome": "Cimini - Caprarola", "lat": 42.327, "lon": 12.237, "tipo": "castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Cimini - Canepina", "lat": 42.383, "lon": 12.223, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Cimini - Ronciglione", "lat": 42.289, "lon": 12.197, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Cimini - Monte Cimino", "lat": 42.408, "lon": 12.203, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Alto Lazio - Acquapendente", "lat": 42.744, "lon": 11.865, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Alto Lazio - San Lorenzo Nuovo", "lat": 42.687, "lon": 11.907, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Selva del Lamone - Farnese", "lat": 42.549, "lon": 11.726, "tipo": "quercia", "quota": 350, "regione": "Lazio"},
    {"nome": "Tolfa - Allumiere", "lat": 42.157, "lon": 11.904, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Bracciano - Manziana / Oriolo", "lat": 42.130, "lon": 12.127, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Veio - Sacrofano / Formello", "lat": 42.106, "lon": 12.345, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Castelli Romani - Rocca di Papa", "lat": 41.766, "lon": 12.710, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Castelli Romani - Tuscolo / Monte Porzio", "lat": 41.807, "lon": 12.716, "tipo": "quercia", "quota": 600, "regione": "Lazio"},

    # ===================== CAMPANIA =====================
    {"nome": "Matese - Piedimonte alto", "lat": 41.355, "lon": 14.371, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Lago del Matese", "lat": 41.410, "lon": 14.400, "tipo": "faggio", "quota": 1010, "regione": "Campania"},
    {"nome": "San Gregorio Matese", "lat": 41.385, "lon": 14.380, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Gallo Matese", "lat": 41.465, "lon": 14.225, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Letino", "lat": 41.450, "lon": 14.250, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Cusano Mutri - Mutria", "lat": 41.330, "lon": 14.520, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Cusano Mutri - Piano Melaina", "lat": 41.345, "lon": 14.505, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Bocca della Selva", "lat": 41.408, "lon": 14.355, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Piedimonte Matese - boschi", "lat": 41.357, "lon": 14.373, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Castello del Matese - faggete", "lat": 41.375, "lon": 14.390, "tipo": "faggio", "quota": 1050, "regione": "Campania"},
    {"nome": "San Potito Sannitico", "lat": 41.338, "lon": 14.392, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Gioia Sannitica - Matese", "lat": 41.300, "lon": 14.347, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Alife - piede Matese", "lat": 41.326, "lon": 14.334, "tipo": "quercia", "quota": 200, "regione": "Campania"},
    {"nome": "Capriati a Volturno", "lat": 41.468, "lon": 14.146, "tipo": "faggio", "quota": 450, "regione": "Campania"},
    {"nome": "Fontegreca", "lat": 41.462, "lon": 14.184, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Prata Sannita", "lat": 41.433, "lon": 14.203, "tipo": "faggio", "quota": 370, "regione": "Campania"},
    {"nome": "Valle Agricola", "lat": 41.425, "lon": 14.255, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Gallo Matese - lago", "lat": 41.466, "lon": 14.225, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Letino - lago", "lat": 41.453, "lon": 14.255, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Roccamonfina - cratere", "lat": 41.295, "lon": 13.982, "tipo": "castagno", "quota": 850, "regione": "Campania"},
    {"nome": "Roccamonfina - Monte Santa Croce", "lat": 41.305, "lon": 13.968, "tipo": "castagno", "quota": 1000, "regione": "Campania"},
    {"nome": "Roccamonfina - castagneti", "lat": 41.288, "lon": 13.995, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Conca della Campania", "lat": 41.332, "lon": 13.991, "tipo": "quercia", "quota": 520, "regione": "Campania"},
    {"nome": "Galluccio - Roccamonfina", "lat": 41.352, "lon": 13.954, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Tora e Piccilli", "lat": 41.337, "lon": 14.025, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Marzano Appio", "lat": 41.318, "lon": 14.045, "tipo": "quercia", "quota": 480, "regione": "Campania"},
    {"nome": "Teano - colline boschive", "lat": 41.251, "lon": 14.067, "tipo": "quercia", "quota": 280, "regione": "Campania"},
    {"nome": "Sessa Aurunca - versante Roccamonfina", "lat": 41.255, "lon": 13.955, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Mignano Monte Lungo", "lat": 41.405, "lon": 13.985, "tipo": "quercia", "quota": 180, "regione": "Campania"},
    {"nome": "Presenzano", "lat": 41.374, "lon": 14.088, "tipo": "quercia", "quota": 220, "regione": "Campania"},
    {"nome": "San Pietro Infine", "lat": 41.447, "lon": 13.960, "tipo": "quercia", "quota": 180, "regione": "Campania"},
    {"nome": "Pietraroja", "lat": 41.347, "lon": 14.550, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Castello del Matese", "lat": 41.368, "lon": 14.378, "tipo": "faggio", "quota": 800, "regione": "Campania"},
    {"nome": "Taburno - Camposauro", "lat": 41.100, "lon": 14.600, "tipo": "castagno", "quota": 900, "regione": "Campania"},
    {"nome": "Partenio - Montevergine", "lat": 40.936, "lon": 14.727, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Partenio - Avella", "lat": 40.960, "lon": 14.600, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Picentini - Montella", "lat": 40.844, "lon": 15.018, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Picentini - Bagnoli Irpino", "lat": 40.833, "lon": 15.072, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Picentini - Laceno", "lat": 40.800, "lon": 15.100, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Picentini - Serino", "lat": 40.795, "lon": 14.872, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Terminio - Cervialto", "lat": 40.830, "lon": 15.030, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Alburni - Sicignano", "lat": 40.560, "lon": 15.305, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Alburni - Ottati", "lat": 40.463, "lon": 15.321, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Corleto Monforte", "lat": 40.437, "lon": 15.380, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Cilento - Piaggine", "lat": 40.345, "lon": 15.378, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Rofrano", "lat": 40.212, "lon": 15.428, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Cilento - Monte Cervati", "lat": 40.285, "lon": 15.410, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Cilento - Sanza", "lat": 40.244, "lon": 15.553, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Monti Lattari - Agerola", "lat": 40.638, "lon": 14.539, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Monti Lattari - Pimonte", "lat": 40.675, "lon": 14.510, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Monte Faito", "lat": 40.650, "lon": 14.500, "tipo": "castagno", "quota": 1100, "regione": "Campania"},
    {"nome": "Sannio - Morcone", "lat": 41.344, "lon": 14.667, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Irpinia - Trevico", "lat": 41.048, "lon": 15.233, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Irpinia - Bagnoli / Laceno basso", "lat": 40.820, "lon": 15.080, "tipo": "castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Matese - Faicchio", "lat": 41.278, "lon": 14.478, "tipo": "quercia", "quota": 200, "regione": "Campania"},
    {"nome": "Matese - Cerreto Sannita", "lat": 41.284, "lon": 14.557, "tipo": "quercia", "quota": 300, "regione": "Campania"},
    {"nome": "Matese - Pontelandolfo", "lat": 41.292, "lon": 14.689, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Fortore - San Bartolomeo in Galdo", "lat": 41.416, "lon": 15.017, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Fortore - Baselice", "lat": 41.394, "lon": 14.974, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Fortore - Circello", "lat": 41.355, "lon": 14.809, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Fortore - Colle Sannita", "lat": 41.373, "lon": 14.833, "tipo": "castagno", "quota": 750, "regione": "Campania"},
    {"nome": "Irpinia - Ariano Irpino", "lat": 41.153, "lon": 15.088, "tipo": "castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Irpinia - Greci", "lat": 41.191, "lon": 15.169, "tipo": "castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Irpinia - Savignano Irpino", "lat": 41.227, "lon": 15.179, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Irpinia - Zungoli", "lat": 41.126, "lon": 15.202, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Irpinia - Bisaccia", "lat": 41.013, "lon": 15.375, "tipo": "castagno", "quota": 850, "regione": "Campania"},
    {"nome": "Irpinia - Andretta", "lat": 40.937, "lon": 15.325, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Irpinia - Calitri", "lat": 40.921, "lon": 15.436, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Irpinia - Lioni", "lat": 40.878, "lon": 15.188, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Irpinia - Teora", "lat": 40.852, "lon": 15.253, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Irpinia - Caposele", "lat": 40.815, "lon": 15.223, "tipo": "faggio", "quota": 450, "regione": "Campania"},
    {"nome": "Irpinia - Calabritto", "lat": 40.783, "lon": 15.223, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Irpinia - Senerchia", "lat": 40.741, "lon": 15.204, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Picentini - Nusco", "lat": 40.887, "lon": 15.087, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Picentini - Cassano Irpino", "lat": 40.870, "lon": 15.026, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Picentini - Volturara Irpina", "lat": 40.883, "lon": 14.918, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Picentini - Acerno", "lat": 40.737, "lon": 15.056, "tipo": "faggio", "quota": 750, "regione": "Campania"},
    {"nome": "Picentini - Giffoni Valle Piana", "lat": 40.718, "lon": 14.942, "tipo": "quercia", "quota": 250, "regione": "Campania"},
    {"nome": "Partenio - Summonte", "lat": 40.947, "lon": 14.775, "tipo": "faggio", "quota": 750, "regione": "Campania"},
    {"nome": "Partenio - Ospedaletto d'Alpinolo", "lat": 40.939, "lon": 14.746, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Partenio - Mercogliano", "lat": 40.920, "lon": 14.743, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Partenio - Baiano", "lat": 40.952, "lon": 14.617, "tipo": "quercia", "quota": 200, "regione": "Campania"},
    {"nome": "Taburno - Vitulano", "lat": 41.117, "lon": 14.658, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Taburno - Foglianise", "lat": 41.161, "lon": 14.671, "tipo": "quercia", "quota": 350, "regione": "Campania"},
    {"nome": "Taburno - Cautano", "lat": 41.150, "lon": 14.644, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Alburni - Petina", "lat": 40.532, "lon": 15.347, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Alburni - Sant'Angelo a Fasanella", "lat": 40.456, "lon": 15.341, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Alburni - Castelcivita", "lat": 40.495, "lon": 15.234, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Alburni - Sicignano / Postiglione", "lat": 40.559, "lon": 15.232, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Valle dell'Angelo", "lat": 40.344, "lon": 15.366, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Laurino", "lat": 40.339, "lon": 15.339, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Cilento - Roscigno", "lat": 40.400, "lon": 15.346, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Cilento - Sacco", "lat": 40.377, "lon": 15.379, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Novi Velia", "lat": 40.224, "lon": 15.286, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Vallo della Lucania", "lat": 40.230, "lon": 15.266, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Cilento - Montano Antilia", "lat": 40.163, "lon": 15.366, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Cilento - Cuccaro Vetere", "lat": 40.164, "lon": 15.321, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Monte Stella", "lat": 40.233, "lon": 15.140, "tipo": "castagno", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Stio", "lat": 40.310, "lon": 15.252, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Magliano Vetere", "lat": 40.346, "lon": 15.236, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Monte Soprano / Trentinara", "lat": 40.400, "lon": 15.115, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Cilento - San Giovanni a Piro", "lat": 40.051, "lon": 15.453, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Cilento - Roccagloriosa", "lat": 40.106, "lon": 15.429, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Vallo di Diano - Teggiano", "lat": 40.379, "lon": 15.540, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Vallo di Diano - Sassano", "lat": 40.340, "lon": 15.566, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Vallo di Diano - Monte San Giacomo", "lat": 40.344, "lon": 15.535, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Vallo di Diano - Padula", "lat": 40.337, "lon": 15.656, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Vallo di Diano - Montesano sulla Marcellana", "lat": 40.276, "lon": 15.705, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Vallo di Diano - Casalbuono", "lat": 40.214, "lon": 15.686, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Vallo di Diano - Sala Consilina", "lat": 40.399, "lon": 15.596, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Tanagro - Atena Lucana", "lat": 40.455, "lon": 15.557, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Tanagro - Auletta / Pertosa", "lat": 40.561, "lon": 15.394, "tipo": "quercia", "quota": 300, "regione": "Campania"},
    {"nome": "Alto Sele - Colliano", "lat": 40.726, "lon": 15.289, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Alto Sele - Valva", "lat": 40.739, "lon": 15.270, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Alto Sele - Laviano", "lat": 40.786, "lon": 15.310, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Monti Lattari - Tramonti", "lat": 40.695, "lon": 14.640, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Monti Lattari - Scala / Ravello", "lat": 40.653, "lon": 14.608, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Monti Lattari - Gragnano / Lettere", "lat": 40.689, "lon": 14.515, "tipo": "quercia", "quota": 350, "regione": "Campania"},
    {"nome": "Monti Lattari - Vico Equense", "lat": 40.661, "lon": 14.427, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Abetina di Rosello", "lat": 41.901, "lon": 14.349, "tipo": "abete_bianco", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Laga - Bosco della Martese / Ceppo", "lat": 42.700, "lon": 13.480, "tipo": "abete_bianco", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Laga - Cortino / Altovia", "lat": 42.627, "lon": 13.507, "tipo": "abete_bianco", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Laga - Monte Pelone", "lat": 42.735, "lon": 13.460, "tipo": "abete_bianco", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Piana dell'Abete / Segadacqua", "lat": 42.548, "lon": 13.478, "tipo": "abete_bianco", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Fonte Vetica abeti", "lat": 42.448, "lon": 13.575, "tipo": "abete_rosso", "quota": 1600, "regione": "Abruzzo"},
    {"nome": "PNALM - Selva di Ornano", "lat": 41.790, "lon": 13.820, "tipo": "abete_bianco", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Aremogna abeti", "lat": 41.808, "lon": 14.045, "tipo": "abete_rosso", "quota": 1500, "regione": "Abruzzo"},
    {"nome": "Abeti Soprani - Pescopennataro", "lat": 41.878, "lon": 14.294, "tipo": "abete_bianco", "quota": 1200, "regione": "Molise"},
    {"nome": "Sant'Angelo del Pesco - abetine", "lat": 41.889, "lon": 14.255, "tipo": "abete_bianco", "quota": 1100, "regione": "Molise"},
    {"nome": "Capracotta - abete bianco", "lat": 41.833, "lon": 14.266, "tipo": "abete_bianco", "quota": 1400, "regione": "Molise"},
    {"nome": "Terminillo - rimboschimenti abete", "lat": 42.473, "lon": 12.997, "tipo": "abete_rosso", "quota": 1600, "regione": "Lazio"},
    {"nome": "Monti della Duchessa - conifere", "lat": 42.180, "lon": 13.330, "tipo": "abete_rosso", "quota": 1500, "regione": "Lazio"},
    {"nome": "Matese - rimboschimenti abete", "lat": 41.460, "lon": 14.380, "tipo": "abete_rosso", "quota": 1400, "regione": "Campania"},
    # Marche
    {"nome": "Sibillini - Ussita", "lat": 42.944, "lon": 13.166, "tipo": "faggio", "quota": 1200, "regione": "Marche"},
    {"nome": "Sibillini - Visso", "lat": 42.931, "lon": 13.088, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Sibillini - Castelsantangelo sul Nera", "lat": 42.895, "lon": 13.153, "tipo": "faggio", "quota": 1300, "regione": "Marche"},
    {"nome": "Sibillini - Bolognola", "lat": 42.993, "lon": 13.228, "tipo": "faggio", "quota": 1400, "regione": "Marche"},
    {"nome": "Sibillini - Fiastra / Lago", "lat": 43.037, "lon": 13.169, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Sibillini - Sarnano", "lat": 43.035, "lon": 13.237, "tipo": "faggio", "quota": 850, "regione": "Marche"},
    {"nome": "Sibillini - Amandola", "lat": 42.980, "lon": 13.353, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Sibillini - Montefortino", "lat": 42.943, "lon": 13.340, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Sibillini - Montemonaco", "lat": 42.898, "lon": 13.330, "tipo": "faggio", "quota": 1200, "regione": "Marche"},
    {"nome": "Sibillini - Montegallo", "lat": 42.842, "lon": 13.332, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Laga Marche - Arquata del Tronto", "lat": 42.773, "lon": 13.296, "tipo": "faggio", "quota": 1200, "regione": "Marche"},
    {"nome": "Laga Marche - Acquasanta Terme", "lat": 42.770, "lon": 13.410, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Monte Ceresa - Montegallo / Rocca", "lat": 42.855, "lon": 13.370, "tipo": "faggio", "quota": 1000, "regione": "Marche"},
    {"nome": "Monte Catria - Frontone", "lat": 43.520, "lon": 12.738, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Monte Catria - Cantiano", "lat": 43.451, "lon": 12.628, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Monte Nerone - Piobbico", "lat": 43.588, "lon": 12.510, "tipo": "faggio", "quota": 1000, "regione": "Marche"},
    {"nome": "Monte Nerone - Apecchio", "lat": 43.559, "lon": 12.418, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Monte Cucco Marche - Scheggia Passo", "lat": 43.404, "lon": 12.666, "tipo": "faggio", "quota": 800, "regione": "Marche"},
    {"nome": "Montefeltro - Carpegna", "lat": 43.781, "lon": 12.333, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Montefeltro - Pennabilli", "lat": 43.817, "lon": 12.262, "tipo": "faggio", "quota": 800, "regione": "Marche"},
    {"nome": "Alpe della Luna - Borgo Pace", "lat": 43.648, "lon": 12.293, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Alpe della Luna - Mercatello sul Metauro", "lat": 43.647, "lon": 12.336, "tipo": "faggio", "quota": 850, "regione": "Marche"},
    {"nome": "Furlo - Acqualagna", "lat": 43.627, "lon": 12.675, "tipo": "quercia", "quota": 350, "regione": "Marche"},
    {"nome": "Monte San Vicino - Apiro", "lat": 43.393, "lon": 13.131, "tipo": "faggio", "quota": 800, "regione": "Marche"},
    {"nome": "Monte San Vicino - Cingoli", "lat": 43.374, "lon": 13.216, "tipo": "quercia", "quota": 600, "regione": "Marche"},
    {"nome": "Genga / Frasassi", "lat": 43.430, "lon": 12.935, "tipo": "quercia", "quota": 400, "regione": "Marche"},
    {"nome": "Fabriano - boschi Giano", "lat": 43.336, "lon": 12.904, "tipo": "castagno", "quota": 500, "regione": "Marche"},
    {"nome": "Sassoferrato - Montelago", "lat": 43.436, "lon": 12.834, "tipo": "faggio", "quota": 700, "regione": "Marche"},
    {"nome": "Camerino - castagneti", "lat": 43.136, "lon": 13.068, "tipo": "castagno", "quota": 650, "regione": "Marche"},
    {"nome": "Muccia - Valle del Chienti", "lat": 43.082, "lon": 13.043, "tipo": "castagno", "quota": 550, "regione": "Marche"},
    {"nome": "Pievebovigliana / Val di Fiastra", "lat": 43.123, "lon": 13.125, "tipo": "castagno", "quota": 550, "regione": "Marche"},
    {"nome": "Sarnano - castagneti", "lat": 43.035, "lon": 13.251, "tipo": "castagno", "quota": 700, "regione": "Marche"},
    {"nome": "Cagli - Monte Petrano", "lat": 43.547, "lon": 12.647, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Serra Sant'Abbondio - Catria", "lat": 43.488, "lon": 12.771, "tipo": "faggio", "quota": 750, "regione": "Marche"},
    {"nome": "Pergola - colline cesane", "lat": 43.562, "lon": 12.837, "tipo": "quercia", "quota": 350, "regione": "Marche"},
    {"nome": "Urbino - Cesane", "lat": 43.726, "lon": 12.636, "tipo": "quercia", "quota": 450, "regione": "Marche"},
    {"nome": "Monte Conero - Sirolo", "lat": 43.522, "lon": 13.601, "tipo": "quercia", "quota": 350, "regione": "Marche"},
    {"nome": "Filottrano - colline", "lat": 43.438, "lon": 13.351, "tipo": "quercia", "quota": 250, "regione": "Marche"},
    {"nome": "Cingoli - querceti", "lat": 43.359, "lon": 13.208, "tipo": "quercia", "quota": 450, "regione": "Marche"},
    {"nome": "San Ginesio - colline", "lat": 43.107, "lon": 13.321, "tipo": "quercia", "quota": 600, "regione": "Marche"},
    {"nome": "Amandola - castagneti", "lat": 42.980, "lon": 13.353, "tipo": "castagno", "quota": 700, "regione": "Marche"},
    {"nome": "Sibillini - Pintura di Bolognola abeti", "lat": 42.995, "lon": 13.215, "tipo": "abete_bianco", "quota": 1450, "regione": "Marche"},
    {"nome": "Catria - versante abetine", "lat": 43.462, "lon": 12.705, "tipo": "abete_bianco", "quota": 1300, "regione": "Marche"},
    # Umbria
    {"nome": "Sibillini Umbria - Norcia", "lat": 42.793, "lon": 13.094, "tipo": "faggio", "quota": 1100, "regione": "Umbria"},
    {"nome": "Sibillini Umbria - Castelluccio", "lat": 42.829, "lon": 13.207, "tipo": "faggio", "quota": 1450, "regione": "Umbria"},
    {"nome": "Valnerina - Preci", "lat": 42.880, "lon": 13.037, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Valnerina - Cerreto di Spoleto", "lat": 42.822, "lon": 12.917, "tipo": "faggio", "quota": 800, "regione": "Umbria"},
    {"nome": "Valnerina - Sellano", "lat": 42.888, "lon": 12.923, "tipo": "faggio", "quota": 750, "regione": "Umbria"},
    {"nome": "Valnerina - Cascia", "lat": 42.718, "lon": 13.013, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Monteleone di Spoleto", "lat": 42.651, "lon": 12.952, "tipo": "faggio", "quota": 950, "regione": "Umbria"},
    {"nome": "Monte Cucco - Sigillo", "lat": 43.331, "lon": 12.742, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Monte Cucco - Costacciaro", "lat": 43.359, "lon": 12.712, "tipo": "faggio", "quota": 850, "regione": "Umbria"},
    {"nome": "Monte Cucco - Scheggia", "lat": 43.404, "lon": 12.666, "tipo": "faggio", "quota": 700, "regione": "Umbria"},
    {"nome": "Gubbio - Monte Ingino", "lat": 43.355, "lon": 12.578, "tipo": "faggio", "quota": 700, "regione": "Umbria"},
    {"nome": "Gubbio - castagneti", "lat": 43.351, "lon": 12.573, "tipo": "castagno", "quota": 550, "regione": "Umbria"},
    {"nome": "Pietralunga - Foresta", "lat": 43.437, "lon": 12.435, "tipo": "faggio", "quota": 650, "regione": "Umbria"},
    {"nome": "Città di Castello - Alpe della Luna", "lat": 43.540, "lon": 12.240, "tipo": "faggio", "quota": 800, "regione": "Umbria"},
    {"nome": "San Giustino - Monte Santa Maria", "lat": 43.547, "lon": 12.175, "tipo": "faggio", "quota": 700, "regione": "Umbria"},
    {"nome": "Umbertide - colline Tevere", "lat": 43.306, "lon": 12.328, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Monte Tezio - Perugia", "lat": 43.198, "lon": 12.347, "tipo": "quercia", "quota": 650, "regione": "Umbria"},
    {"nome": "Monte Subasio - Assisi", "lat": 43.074, "lon": 12.651, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Monte Subasio - Spello", "lat": 43.000, "lon": 12.672, "tipo": "quercia", "quota": 450, "regione": "Umbria"},
    {"nome": "Colfiorito - Foligno", "lat": 43.027, "lon": 12.890, "tipo": "faggio", "quota": 800, "regione": "Umbria"},
    {"nome": "Nocera Umbra - Monte Pennino", "lat": 43.115, "lon": 12.854, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Nocera Umbra - castagneti", "lat": 43.114, "lon": 12.786, "tipo": "castagno", "quota": 550, "regione": "Umbria"},
    {"nome": "Spoleto - Monteluco", "lat": 42.724, "lon": 12.748, "tipo": "faggio", "quota": 750, "regione": "Umbria"},
    {"nome": "Monti Martani - Massa Martana", "lat": 42.777, "lon": 12.525, "tipo": "quercia", "quota": 600, "regione": "Umbria"},
    {"nome": "Monte Peglia - San Venanzo", "lat": 42.869, "lon": 12.268, "tipo": "quercia", "quota": 650, "regione": "Umbria"},
    {"nome": "Orvieto - selva Querce", "lat": 42.718, "lon": 12.110, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Piegaro - boschi Nestore", "lat": 42.966, "lon": 12.085, "tipo": "quercia", "quota": 400, "regione": "Umbria"},
    {"nome": "Trasimeno - Castiglione del Lago", "lat": 43.127, "lon": 12.045, "tipo": "quercia", "quota": 300, "regione": "Umbria"},
    {"nome": "Trasimeno - Magione / Montecolognola", "lat": 43.143, "lon": 12.203, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Amerini - Amelia", "lat": 42.553, "lon": 12.416, "tipo": "quercia", "quota": 400, "regione": "Umbria"},
    {"nome": "Narni - boschi Serra", "lat": 42.519, "lon": 12.515, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Terni - Monte Torre Maggiore", "lat": 42.620, "lon": 12.580, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Ferentillo - Valnerina bassa", "lat": 42.621, "lon": 12.791, "tipo": "castagno", "quota": 400, "regione": "Umbria"},
    {"nome": "Scheggino - Valnerina", "lat": 42.712, "lon": 12.830, "tipo": "castagno", "quota": 450, "regione": "Umbria"},
    {"nome": "Cascia - castagneti", "lat": 42.717, "lon": 13.013, "tipo": "castagno", "quota": 700, "regione": "Umbria"},
    {"nome": "Norcia - Piano di Santa Scolastica", "lat": 42.793, "lon": 13.094, "tipo": "castagno", "quota": 650, "regione": "Umbria"},
    {"nome": "Valnerina - abetine Cerreto", "lat": 42.822, "lon": 12.917, "tipo": "abete_bianco", "quota": 1000, "regione": "Umbria"},
    {"nome": "Monte Cucco - abetine Pian delle Macinare", "lat": 43.350, "lon": 12.740, "tipo": "abete_bianco", "quota": 1100, "regione": "Umbria"},
]

# Stazioni ufficiali (WMO / Aeronautica / aeroporti) nelle 4 regioni e dintorni
STAZIONI = [
    {"id": "16214", "nome": "L'Aquila Preturo", "lat": 42.38, "lon": 13.31},
    {"id": "16219", "nome": "Campo Imperatore", "lat": 42.44, "lon": 13.56},
    {"id": "16220", "nome": "Pescara", "lat": 42.43, "lon": 14.18},
    {"id": "16230", "nome": "Pescara Aeroporto", "lat": 42.43, "lon": 14.18},
    {"id": "16232", "nome": "Termoli", "lat": 42.00, "lon": 15.00},
    {"id": "16224", "nome": "Campobasso", "lat": 41.57, "lon": 14.65},
    {"id": "16252", "nome": "Isernia", "lat": 41.59, "lon": 14.23},
    {"id": "16253", "nome": "Capracotta", "lat": 41.83, "lon": 14.26},
    {"id": "16261", "nome": "Grazzanise (CE)", "lat": 41.06, "lon": 14.08},
    {"id": "16289", "nome": "Napoli Capodichino", "lat": 40.88, "lon": 14.29},
    {"id": "16310", "nome": "Salerno Pontecagnano", "lat": 40.62, "lon": 14.91},
    {"id": "16312", "nome": "Trevico", "lat": 41.05, "lon": 15.23},
    {"id": "16320", "nome": "Capo Palinuro", "lat": 40.03, "lon": 15.28},
    {"id": "16239", "nome": "Roma Ciampino", "lat": 41.80, "lon": 12.59},
    {"id": "16242", "nome": "Roma Fiumicino", "lat": 41.80, "lon": 12.23},
    {"id": "16234", "nome": "Viterbo", "lat": 42.43, "lon": 12.06},
    {"id": "16221", "nome": "Rieti", "lat": 42.43, "lon": 12.86},
    {"id": "16206", "nome": "Terminillo", "lat": 42.47, "lon": 12.98},
    {"id": "16235", "nome": "Monte Terminillo Osservatorio", "lat": 42.47, "lon": 12.99},
    {"id": "16294", "nome": "Capo Palinuro / Cilento", "lat": 40.03, "lon": 15.28},
    {"id": "16258", "nome": "Latina", "lat": 41.55, "lon": 12.90},
    {"id": "16244", "nome": "Pratica di Mare", "lat": 41.65, "lon": 12.45},
    {"id": "16280", "nome": "Frosinone", "lat": 41.64, "lon": 13.30},
    {"id": "16191", "nome": "Ancona Falconara", "lat": 43.62, "lon": 13.36},
    {"id": "16190", "nome": "Frontone", "lat": 43.52, "lon": 12.73},
    {"id": "16181", "nome": "Perugia Sant'Egidio", "lat": 43.10, "lon": 12.50},
    {"id": "16179", "nome": "Terminillo / Leonessa confine", "lat": 42.47, "lon": 12.99},
]


def distanza_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def mn_login(email, password):
    """Ritorna (token, errore). Una sola chiamata: il login ha limite stretto (429)."""
    if not email or not password:
        return None, "Inserisci email e password di myMeteoNetwork."
    try:
        r = requests.post(
            "https://api.meteonetwork.it/v3/login",
            data={
                "email": email,
                "username": email,
                "user": email,
                "password": password,
            },
            headers={"User-Agent": "PorciniPredictor/1.0 (uso personale)"},
            timeout=20,
        )
    except Exception as e:
        return None, f"Rete: {e}"
    if r.status_code == 429:
        return None, (
            "Troppe richieste a MeteoNetwork (HTTP 429). "
            "Non riprovare subito: aspetta almeno 30–60 minuti. "
            "Poi usa il pulsante «Collega MeteoNetwork» una volta sola, oppure incolla un token già salvato."
        )
    if r.status_code != 200:
        return None, f"Login API non riuscito. HTTP {r.status_code}: {r.text[:240]}"
    try:
        js = r.json()
    except Exception:
        return None, f"Risposta login non valida: {r.text[:200]}"
    data = js.get("data") if isinstance(js.get("data"), dict) else {}
    token = js.get("access_token") or js.get("token") or data.get("token") or data.get("access_token")
    if token:
        return str(token), None
    return None, f"Nessun token nella risposta: {r.text[:240]}"


def _parse_stazioni_mn(js):
    if isinstance(js, dict):
        js = js.get("data") or js.get("stations") or js.get("items") or []
    if not isinstance(js, list):
        return []
    out = []
    for s in js:
        if not isinstance(s, dict):
            continue
        try:
            lat = float(s.get("latitude") or s.get("lat"))
            lon = float(s.get("longitude") or s.get("lon"))
            code = s.get("station_code") or s.get("code") or s.get("id")
            nome = s.get("name") or s.get("place") or s.get("area") or code
            regione = s.get("region_name") or s.get("region") or ""
            quota_s = s.get("altitude") or s.get("elevation") or s.get("alt")
            try:
                quota_s = float(quota_s) if quota_s not in (None, "") else None
            except Exception:
                quota_s = None
            if code and lat and lon:
                out.append({
                    "code": str(code),
                    "nome": str(nome),
                    "lat": lat,
                    "lon": lon,
                    "regione": str(regione),
                    "quota": quota_s,
                })
        except Exception:
            continue
    return out


@st.cache_data(ttl=3600)
def mn_elenco_stazioni(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "PorciniPredictor/1.0 (uso personale)",
    }
    tentativi = [
        ("https://api.meteonetwork.it/v3/stations", {"country": "IT"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Molise"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Abruzzo"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Lazio"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Campania"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Marche"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Umbria"}),
        ("https://api.meteonetwork.it/v3/data-realtime", {"country": "IT", "region": "Molise"}),
    ]
    ultimo = "nessuna risposta"
    trovate = []
    seen = set()
    for url, params in tentativi:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
        except Exception as e:
            ultimo = str(e)
            continue
        ultimo = f"HTTP {r.status_code}: {r.text[:180]}"
        if r.status_code != 200:
            continue
        try:
            js = r.json()
        except Exception:
            continue
        for s in _parse_stazioni_mn(js):
            if s["code"] not in seen:
                seen.add(s["code"])
                trovate.append(s)
        if trovate:
            return trovate
    # memorizza il motivo per la sidebar (cache-friendly: lo mettiamo in un dict fittizio no)
    st.session_state["mn_elenco_errore"] = ultimo
    return []


@st.cache_data(ttl=1800)
def _path_codici_salvati():
    return Path(__file__).resolve().parent / "mn_codici_utente.txt"


def carica_codici_salvati():
    out = []
    seen = set()
    path = _path_codici_salvati()
    if path.exists():
        try:
            for p in path.read_text(encoding="utf-8").replace(";", ",").split(","):
                c = p.strip().lower()
                if c and c not in seen:
                    seen.add(c)
                    out.append(c)
        except Exception:
            pass
    for c in (st.session_state.get("mn_codici_lista") or []):
        c = str(c).strip().lower()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def salva_codici_utente(lista):
    puliti = []
    seen = set()
    for c in lista:
        c = str(c).strip().lower()
        if c and c not in seen:
            seen.add(c)
            puliti.append(c)
    st.session_state["mn_codici_lista"] = puliti
    try:
        _path_codici_salvati().write_text(", ".join(puliti), encoding="utf-8")
    except Exception:
        pass
    return puliti


def mn_stazioni_da_codici(token, codici):
    """STANDARD: /stations/{code} (singola) + realtime. Poche chiamate, mai in parallelo."""
    if not token or not codici:
        return []
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "PorciniPredictor/1.0 (uso personale)",
    }
    out = []
    for raw in str(codici).replace(";", ",").split(","):
        code = raw.strip().split("/")[-1].split("?")[0].strip().lower()
        if not code:
            continue
        row = None
        for url in (
            f"https://api.meteonetwork.it/v3/stations/{code}",
            f"https://api.meteonetwork.it/v3/data-realtime/{code}",
        ):
            try:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code != 200:
                    continue
                js = r.json()
                cand = js[0] if isinstance(js, list) and js else js
                if isinstance(cand, dict):
                    row = cand
                    break
            except Exception:
                continue
        if not row:
            continue
        lat = row.get("latitude") or row.get("lat")
        lon = row.get("longitude") or row.get("lon")
        if lat is None or lon is None:
            continue
        quota_s = row.get("altitude") or row.get("elevation")
        try:
            quota_s = float(quota_s) if quota_s not in (None, "") else None
        except Exception:
            quota_s = None
        out.append({
            "code": str(row.get("station_code") or code),
            "nome": str(
                row.get("name") or row.get("place_name") or row.get("place") or row.get("area") or code
            ),
            "lat": float(lat),
            "lon": float(lon),
            "regione": str(row.get("region") or row.get("region_name") or ""),
            "quota": quota_s,
        })
    return out


def punteggio_vicinanza(dist_km, d_quota, max_dist=45):
    """Più basso è meglio. Penalizza stazioni lontane o a quota molto diversa."""
    if dist_km is None or dist_km > max_dist:
        return 9999
    dq = abs(d_quota) if d_quota is not None else 300
    return dist_km + dq / 80.0


def mn_stazioni_vicine(lat, lon, stazioni, quota=None, n=5, max_km=40):
    if not stazioni:
        return []
    ranked = []
    for s in stazioni:
        d = distanza_km(lat, lon, s["lat"], s["lon"])
        if d > max_km:
            continue
        q_st = s.get("quota") or s.get("altitude")
        dq = (quota - q_st) if (quota is not None and q_st not in (None, "")) else None
        ranked.append((punteggio_vicinanza(d, dq, max_km), d, s))
    ranked.sort(key=lambda x: x[0])
    out = []
    for _, d, s in ranked[:n]:
        s2 = dict(s)
        s2["distanza_km"] = round(d, 1)
        out.append(s2)
    return out


def mn_stazione_vicina(lat, lon, stazioni, quota=None):
    vicine = mn_stazioni_vicine(lat, lon, stazioni, quota=quota, n=1)
    if not vicine:
        return None, None
    return vicine[0], vicine[0]["distanza_km"]


def _mn_rows_to_df(righe):
    records = []
    for row in righe:
        if not isinstance(row, dict):
            continue
        rain = row.get("daily_rain")
        if rain is None:
            rain = row.get("rain") or row.get("precipitation") or row.get("prec")
        tmax = row.get("current_tmax") or row.get("tmax") or row.get("temperature")
        tmin = row.get("current_tmin") or row.get("tmin")
        tmed = row.get("current_tmed") or row.get("tmed") or row.get("temperature")
        data = (
            row.get("observation_date")
            or row.get("date")
            or row.get("observation_time_local")
            or row.get("day")
            or ""
        )
        try:
            precip = float(rain) if rain not in (None, "") else 0.0
        except Exception:
            precip = 0.0
        records.append({
            "date": str(data)[:10],
            "precip": precip,
            "t_max": float(tmax) if tmax not in (None, "") else None,
            "t_min": float(tmin) if tmin not in (None, "") else None,
            "t_mean": float(tmed) if tmed not in (None, "") else None,
        })
    if not records:
        return None
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
    return df.fillna(0)


def _path_giorni_salvati():
    return Path(__file__).resolve().parent / "mn_giorni_utente.json"


# Agosto 2026 Bagnolo Amatrice (laz201) da tabella FM / pluviometro
SEED_LAZ201_AGO2026 = {
    "2026-08-01": 0.0, "2026-08-02": 0.0, "2026-08-03": 0.0, "2026-08-04": 0.51,
    "2026-08-05": 0.0, "2026-08-06": 0.0, "2026-08-07": 0.0, "2026-08-08": 0.0,
    "2026-08-09": 0.0, "2026-08-10": 0.0, "2026-08-11": 1.52, "2026-08-12": 0.0,
    "2026-08-13": 0.0, "2026-08-14": 0.0, "2026-08-15": 0.0, "2026-08-16": 4.06,
    "2026-08-17": 2.03, "2026-08-18": 0.0, "2026-08-19": 0.0, "2026-08-20": 0.0,
    "2026-08-21": 6.60, "2026-08-22": 0.0, "2026-08-23": 0.0, "2026-08-24": 0.0,
    "2026-08-25": 3.30, "2026-08-26": 0.0, "2026-08-27": 0.0, "2026-08-28": 4.32,
    "2026-08-29": 0.25, "2026-08-30": 0.0, "2026-08-31": 0.0,
}


def _carica_giorni_file():
    store = st.session_state.setdefault("mn_giorni", {})
    path = _path_giorni_salvati()
    if path.exists() and not st.session_state.get("mn_giorni_file_ok"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                store.update(data)
            st.session_state["mn_giorni_file_ok"] = True
        except Exception:
            pass
        _salva_giorni_file()
    if not st.session_state.get("seed_laz201_ok"):
        for giorno, mm in SEED_LAZ201_AGO2026.items():
            chiave = f"laz201|{giorno}"
            if chiave not in store:
                store[chiave] = {"date": giorno, "precip": mm}
        st.session_state["mn_giorni"] = store
        st.session_state["seed_laz201_ok"] = True
        _salva_giorni_file()
    return store


def _salva_giorni_file():
    """Archivio rotante: tengo 31 giorni, cancello tutto ciò che è più vecchio di un mese."""
    try:
        store = dict(st.session_state.get("mn_giorni") or {})
        limite = (datetime.now().date() - timedelta(days=31)).isoformat()
        pulito = {}
        for k, v in store.items():
            d = ""
            if isinstance(v, dict):
                d = str(v.get("date") or "")[:10]
            if not d and "|" in str(k):
                d = str(k).rsplit("|", 1)[-1][:10]
            if d >= limite:
                pulito[k] = v
        st.session_state["mn_giorni"] = pulito
        _path_giorni_salvati().write_text(
            json.dumps(pulito, ensure_ascii=False),
            encoding="utf-8",
        )
        _push_giorni_github(pulito)
    except Exception:
        pass


def _push_giorni_github(store):
    """Se nei Secrets c'è GITHUB_TOKEN, aggiorna mn_giorni_utente.json sul repo."""
    try:
        last = float(st.session_state.get("mn_push_ts") or 0)
        if time.time() - last < 90:
            return
        tok = ""
        repo = ""
        branch = "main"
        try:
            tok = str(st.secrets.get("GITHUB_TOKEN") or "")
            repo = str(st.secrets.get("GITHUB_REPO") or "")
            branch = str(st.secrets.get("GITHUB_BRANCH") or "main")
        except Exception:
            pass
        tok = tok or str(__import__("os").environ.get("GITHUB_TOKEN") or "")
        repo = repo or str(__import__("os").environ.get("GITHUB_REPO") or "")
        if not tok or not repo or "/" not in repo:
            st.session_state["mn_push_err"] = "manca GITHUB_TOKEN o GITHUB_REPO nei Secrets"
            return
        path = "mn_giorni_utente.json"
        api = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "PorciniPredictor",
        }
        sha = None
        r = requests.get(api, headers=headers, params={"ref": branch}, timeout=20)
        if r.status_code == 200:
            sha = (r.json() or {}).get("sha")
        body = {
            "message": f"archivio piogge {datetime.now().date().isoformat()}",
            "content": base64.b64encode(
                json.dumps(store, ensure_ascii=False).encode("utf-8")
            ).decode("ascii"),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        p = requests.put(api, headers=headers, json=body, timeout=25)
        if p.status_code in (200, 201):
            st.session_state["mn_push_ts"] = time.time()
            st.session_state["mn_push_ok"] = True
            st.session_state["mn_push_err"] = ""
        else:
            st.session_state["mn_push_ok"] = False
            st.session_state["mn_push_err"] = f"GitHub HTTP {p.status_code}"
    except Exception as e:
        st.session_state["mn_push_ok"] = False
        st.session_state["mn_push_err"] = str(e)[:80]


def mn_giorno_pluviometro(token, code, giorno):
    """Un giorno. Successi in sessione e su file; i 429 non si cachano."""
    store = _carica_giorni_file()
    key = f"{code}|{giorno}"
    if key in store:
        return {"ok": True, "status": 200, "row": store[key]}
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "PorciniPredictor/1.0 (uso personale)",
    }
    r = requests.get(
        f"https://api.meteonetwork.it/v3/data-daily/{code}",
        headers=headers,
        params={"observation_date": giorno},
        timeout=15,
    )
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "row": None}
    js = r.json()
    row = js[0] if isinstance(js, list) and js else js
    if isinstance(row, dict):
        store[key] = row
        st.session_state["mn_giorni"] = store
        _salva_giorni_file()
        return {"ok": True, "status": 200, "row": row}
    return {"ok": False, "status": r.status_code, "row": None}


def mn_serie_giornaliera(token, code, days=30, nuovi_per_volta=4):
    """Fino a 30 giorni. Ogni Calcola scarica al massimo 4 giorni nuovi."""
    if not token or not code:
        return None, 0, days
    oggi = datetime.now().date()
    righe = []
    nuovi = 0
    store = _carica_giorni_file()
    for i in range(min(int(days), 30)):
        d = (oggi - timedelta(days=i)).isoformat()
        key = f"{code}|{d}"
        if key in store:
            righe.append(store[key])
            continue
        if nuovi >= nuovi_per_volta:
            continue
        pack = mn_giorno_pluviometro(token, code, d)
        if pack.get("status") == 429:
            break
        if pack.get("ok") and pack.get("row"):
            righe.append(pack["row"])
            store[key] = pack["row"]
        nuovi += 1
    st.session_state["mn_giorni"] = store
    _salva_giorni_file()
    return _mn_rows_to_df(righe), len(righe), days


@st.cache_data(ttl=1800)
def mn_dati_stazione(token, code, days=30):
    """Una o poche chiamate per stazione. Niente 30 GET: quello genera 429 e poi sparisce MN."""
    headers = {"Authorization": f"Bearer {token}"}
    oggi = datetime.now().date()
    start = (oggi - timedelta(days=min(days, 16))).isoformat()
    end = oggi.isoformat()

    for url, params in [
        (f"https://api.meteonetwork.it/v3/data-daily/{code}", {"start": start, "end": end}),
        (f"https://api.meteonetwork.it/v3/daily/{code}", {"from": start, "to": end}),
    ]:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if r.status_code != 200:
                continue
            js = r.json()
            if isinstance(js, dict):
                js = js.get("data") or js.get("values") or js.get("daily") or []
            if isinstance(js, list) and js:
                df = _mn_rows_to_df(js)
                if df is not None and len(df) >= 3:
                    return df
        except Exception:
            continue

    try:
        r = requests.get(
            f"https://api.meteonetwork.it/v3/data-realtime/{code}",
            headers=headers,
            timeout=20,
        )
        if r.status_code == 200:
            js = r.json()
            row = js[0] if isinstance(js, list) and js else js
            if isinstance(row, dict):
                return _mn_rows_to_df([row])
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400)
def catalogo_stazioni_ufficiali():
    """Stazioni Meteostat del Centro-Sud + elenco hardcoded (WMO/aeroporti)."""
    out = []
    seen = set()
    path = Path(__file__).resolve().parent / "stazioni_it.json"
    if path.exists():
        try:
            for s in json.loads(path.read_text()):
                sid = str(s.get("id"))
                if not sid:
                    continue
                seen.add(sid)
                out.append({
                    "id": sid,
                    "nome": s.get("nome") or sid,
                    "lat": float(s["lat"]),
                    "lon": float(s["lon"]),
                    "quota": s.get("quota"),
                    "daily_end": s.get("daily_end"),
                })
        except Exception:
            pass
    for s in STAZIONI:
        sid = str(s["id"])
        if sid in seen:
            continue
        out.append({
            "id": sid,
            "nome": s["nome"],
            "lat": s["lat"],
            "lon": s["lon"],
            "quota": None,
            "daily_end": None,
        })
    return out


def stazioni_ufficiali_vicine(lat, lon, quota=None, n=4, max_km=35):
    ranked = []
    for s in catalogo_stazioni_ufficiali():
        d = distanza_km(lat, lon, s["lat"], s["lon"])
        if d > max_km:
            continue
        dq = (quota - s["quota"]) if (quota is not None and s.get("quota") is not None) else None
        ranked.append((punteggio_vicinanza(d, dq, max_km), d, s))
    ranked.sort(key=lambda x: x[0])
    res = []
    for _, d, s in ranked[:n]:
        s2 = dict(s)
        s2["distanza_km"] = round(d, 1)
        res.append(s2)
    return res


def stazione_piu_vicina(lat, lon, quota=None):
    vicine = stazioni_ufficiali_vicine(lat, lon, quota=quota, n=1, max_km=80)
    if not vicine:
        return None, None
    return vicine[0], vicine[0]["distanza_km"]


@st.cache_data(ttl=3600)
def get_stazione_dati(station_id, days=30):
    year = datetime.now().year
    frames = []
    for y in (year - 1, year):
        url = f"https://data.meteostat.net/daily/{y}/{station_id}.csv.gz"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                continue
            raw = gzip.decompress(r.content)
            dfy = pd.read_csv(io.BytesIO(raw))
            frames.append(dfy)
        except Exception:
            continue
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    if "date" not in df.columns:
        return None
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    fine = datetime.now()
    inizio = fine - timedelta(days=days)
    df = df[(df["date"] >= inizio) & (df["date"] <= fine)].copy()
    if len(df) < 8:
        return None
    prcp = pd.to_numeric(df.get("prcp"), errors="coerce")
    # se la colonna pioggia è quasi tutta vuota la stazione non è utile per i porcini
    if prcp.notna().sum() < 8:
        return None
    # NON mettere 0 sui buchi: uno 0 finto abbassa i mm rispetto alla stazione vera
    out = pd.DataFrame({
        "date": df["date"],
        "precip": prcp,
        "t_max": pd.to_numeric(df.get("tmax"), errors="coerce"),
        "t_min": pd.to_numeric(df.get("tmin"), errors="coerce"),
        "t_mean": pd.to_numeric(df.get("tavg"), errors="coerce"),
    })
    return out


def riepilogo_vento(df, giorni=10):
    """Vento persistente secca il letto: fattore 1 = ok, verso 0 = nascite azzerate."""
    vuoto = {
        "vento_medio_10g": None,
        "vento_max_10g": None,
        "giorni_oltre_20": 0,
        "giorni_oltre_30": 0,
        "giorni_consecutivi_venti": 0,
        "fattore_vento": 1.0,
        "nota_vento": "Vento non disponibile",
        "picchi_vento": [],
        "picco_max_data": None,
        "picco_max_kmh": None,
    }
    if df is None or "vento_max" not in getattr(df, "columns", []):
        return vuoto
    coda = df.tail(giorni).copy()
    v = pd.to_numeric(coda["vento_max"], errors="coerce").fillna(0)
    if v.isna().all() or float(v.max()) == 0 and float(v.mean()) == 0:
        # potrebbe essere tutto zero vero, trattiamo comunque
        pass
    giorni_20 = int((v >= 20).sum())
    giorni_30 = int((v >= 30).sum())
    streak = 0
    for val in reversed(list(v)):
        if val >= 20:
            streak += 1
        else:
            break
    media = float(v.mean())
    vmax = float(v.max())
    # stress: persistenza + intensità (esponenziale come richiesto)
    stress = giorni_20 * 0.12 + giorni_30 * 0.32 + max(0, streak - 1) * 0.22
    if media >= 28:
        stress += 0.7
    elif media >= 22:
        stress += 0.35
    fattore = float(max(0.03, min(1.0, exp(-stress))))
    if giorni_30 >= 4 and streak >= 3:
        fattore = min(fattore, 0.12)
    if fattore >= 0.85:
        nota = "Vento debole, umidità del suolo tenuta"
    elif fattore >= 0.5:
        nota = "Vento fresco persistente: il letto si sta asciugando"
    elif fattore >= 0.2:
        nota = "Vento forte e ripetuto: nascite fortemente ridotte"
    else:
        nota = "Vento persistente >20–30 km/h: umidità quasi azzerata"
    picchi = []
    picco_data = None
    picco_kmh = None
    try:
        serie = df.copy()
        serie["date"] = pd.to_datetime(serie["date"], errors="coerce")
        serie["vento_max"] = pd.to_numeric(serie["vento_max"], errors="coerce")
        serie = serie.dropna(subset=["date", "vento_max"])
        taglio = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=30)
        serie = serie[serie["date"] >= taglio]
        forti = serie[serie["vento_max"] >= 20].sort_values("date")
        for _, rr in forti.iterrows():
            picchi.append(
                f"{pd.to_datetime(rr['date']).date()}: {float(rr['vento_max']):.1f} km/h"
            )
        if len(serie):
            top = serie.loc[serie["vento_max"].idxmax()]
            picco_data = pd.to_datetime(top["date"]).date().isoformat()
            picco_kmh = round(float(top["vento_max"]), 1)
    except Exception:
        pass
    return {
        "vento_medio_10g": round(media, 1),
        "vento_max_10g": round(vmax, 1),
        "giorni_oltre_20": giorni_20,
        "giorni_oltre_30": giorni_30,
        "giorni_consecutivi_venti": streak,
        "fattore_vento": round(fattore, 3),
        "nota_vento": nota,
        "picchi_vento": picchi,
        "picco_max_data": picco_data,
        "picco_max_kmh": picco_kmh,
    }


def _dir_cardinale(gradi):
    try:
        g = float(gradi) % 360
    except Exception:
        return None
    nomi = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return nomi[int((g + 22.5) // 45) % 8]


@st.cache_data(ttl=3600)
def get_vento_direzione_om(lat, lon):
    """Direzione prevalente 10 gg. L'archivio MN mensile non ha i gradi."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": round(float(lat), 3),
                "longitude": round(float(lon), 3),
                "past_days": 10,
                "forecast_days": 1,
                "daily": "wind_direction_10m_dominant",
                "timezone": "Europe/Rome",
            },
            timeout=12,
        )
        if r.status_code != 200:
            return None
        vals = (r.json().get("daily") or {}).get("wind_direction_10m_dominant") or []
        nums = [float(x) for x in vals if x is not None]
        if not nums:
            return None
        import math
        rad = [math.radians(x) for x in nums]
        x = sum(math.sin(a) for a in rad) / len(rad)
        y = sum(math.cos(a) for a in rad) / len(rad)
        ang = (math.degrees(math.atan2(x, y)) + 360) % 360
        return _dir_cardinale(ang)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_temperature_om(lat, lon, days=30):
    """Solo temperature, non la pioggia."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": round(float(lat), 3),
                "longitude": round(float(lon), 3),
                "past_days": min(int(days), 92),
                "forecast_days": 1,
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "Europe/Rome",
            },
            timeout=12,
        )
        if r.status_code != 200:
            return None
        d = r.json().get("daily") or {}
        if not d.get("time"):
            return None
        return pd.DataFrame({
            "date": pd.to_datetime(d["time"]).normalize(),
            "t_max": d.get("temperature_2m_max"),
            "t_min": d.get("temperature_2m_min"),
        })
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_umidita_media(lat, lon):
    """Umidità relativa media 10 giorni (Open-Meteo). MN pubblico spesso non la manda."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": round(float(lat), 3),
                "longitude": round(float(lon), 3),
                "past_days": 10,
                "forecast_days": 1,
                "daily": "relative_humidity_2m_mean",
                "timezone": "Europe/Rome",
            },
            timeout=12,
        )
        if r.status_code != 200:
            return None
        vals = (r.json().get("daily") or {}).get("relative_humidity_2m_mean") or []
        nums = [float(x) for x in vals if x is not None]
        if not nums:
            return None
        return round(sum(nums) / len(nums), 1)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_openmeteo_bundle(lat, lon, days=30):
    """Storico + previsione + suolo. Pioggia da ICON-2I (2 km) se disponibile."""
    oggi = pd.Timestamp(datetime.now().date())
    start = (datetime.now().date() - timedelta(days=days)).isoformat()
    end = datetime.now().date().isoformat()

    storico = None
    # storico ad alta risoluzione sul modello italiano
    try:
        r = requests.get(
            "https://historical-forecast-api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start,
                "end_date": end,
                "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,temperature_2m_mean,wind_speed_10m_max",
                "models": "italia_meteo_arpae_icon_2i",
                "timezone": "Europe/Rome",
            },
            timeout=25,
        )
        if r.status_code == 200:
            data = r.json()
            if "daily" in data:
                storico = pd.DataFrame({
                    "date": pd.to_datetime(data["daily"]["time"]),
                    "precip": data["daily"]["precipitation_sum"],
                    "t_max": data["daily"]["temperature_2m_max"],
                    "t_min": data["daily"]["temperature_2m_min"],
                    "t_mean": data["daily"]["temperature_2m_mean"],
                    "vento_max": data["daily"].get("wind_speed_10m_max") or 0,
                }).fillna(0)
    except Exception:
        storico = None

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "past_days": min(days, 92),
        "forecast_days": 7,
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,temperature_2m_mean,wind_speed_10m_max",
        "hourly": "soil_moisture_7_to_28cm",
        "timezone": "Europe/Rome",
        "models": "italia_meteo_arpae_icon_2i",
    }
    try:
        r = requests.get(url, params=params, timeout=25)
        if r.status_code != 200:
            params.pop("models", None)
            r = requests.get(url, params=params, timeout=25)
        r.raise_for_status()
        data = r.json()
    except Exception:
        data = {}

    daily = None
    if "daily" in data:
        daily = pd.DataFrame({
            "date": pd.to_datetime(data["daily"]["time"]),
            "precip": data["daily"]["precipitation_sum"],
            "t_max": data["daily"]["temperature_2m_max"],
            "t_min": data["daily"]["temperature_2m_min"],
            "t_mean": data["daily"]["temperature_2m_mean"],
            "vento_max": data["daily"].get("wind_speed_10m_max") or 0,
        }).fillna(0)

    if storico is None and daily is not None:
        storico = daily[daily["date"] <= oggi].tail(days)
    elif storico is not None and daily is not None and "vento_max" in daily.columns:
        # allinea il vento del modello anche se la pioggia viene da altrove
        if "vento_max" not in storico.columns:
            storico = storico.merge(daily[["date", "vento_max"]], on="date", how="left")
    forecast = daily[daily["date"] > oggi].head(7) if daily is not None else None

    soil = None
    if data.get("hourly") and data["hourly"].get("soil_moisture_7_to_28cm"):
        soil_vals = [v for v in data["hourly"]["soil_moisture_7_to_28cm"] if v is not None]
        if soil_vals:
            soil = round(sum(soil_vals[-72:]) / max(1, len(soil_vals[-72:])), 3)
    vento = riepilogo_vento(storico if storico is not None else daily)
    return storico, forecast, soil, vento


def get_openmeteo_data(lat, lon, days=30):
    storico, *_ = get_openmeteo_bundle(lat, lon, days)
    return storico


def _info_stazione(s, fonte):
    return {
        "fonte": fonte,
        "stazione": s.get("nome") or s.get("code") or "n/d",
        "distanza_km": s.get("distanza_km"),
        "quota_stazione": s.get("quota"),
        "codice": s.get("code") or s.get("id"),
        "pioggia_modello_30g": None,
        "pioggia_stazione_30g": None,
    }


def _tabella_bosco(df):
    if df is None or len(df) == 0:
        return ""
    cols = list(df.columns)

    def _esc(v):
        s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    th = "".join(f"<th>{_esc(c)}</th>" for c in cols)
    body = []
    for _, rr in df.iterrows():
        body.append("<tr>" + "".join(f"<td>{_esc(rr[c])}</td>" for c in cols) + "</tr>")
    return (
        '<div class="bmap-table"><table><thead><tr>'
        + th
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _wc_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://app.weathercloud.net/map",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json,text/javascript,*/*",
    })
    try:
        s.get("https://app.weathercloud.net/", timeout=20)
    except Exception:
        pass
    return s


def _wc_id(code):
    code = str(code).strip()
    if not code:
        return ""
    if code.isdigit():
        return code
    try:
        return str(int(code, 36))
    except Exception:
        return code


def _wc_catalogo_file():
    path = Path(__file__).resolve().parent / "weathercloud_centro.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=21600)
def wc_catalogo():
    """Stazioni WeatherCloud Centro-Sud. Live + file di riserva."""
    locale = _wc_catalogo_file()
    s = _wc_session()
    try:
        r = s.get("https://app.weathercloud.net/map/bgdevices", timeout=60)
        txt = r.text or ""
        js = r.json() if txt.lstrip()[:1] == "{" else None
        devs = (js or {}).get("devices") or []
    except Exception:
        devs = []
    if not devs:
        return locale
    out = []
    for d in devs:
        if not isinstance(d, (list, tuple)) or len(d) < 4:
            continue
        try:
            lat, lon = float(d[2]), float(d[3])
        except Exception:
            continue
        if not (39.8 <= lat <= 43.2 and 12.2 <= lon <= 16.3):
            continue
        code = str(d[0])
        out.append({
            "code": code,
            "id": _wc_id(code),
            "nome": str(d[1]),
            "lat": lat,
            "lon": lon,
            "online": d[4] == 2 if len(d) > 4 else True,
        })
    if len(out) < 50:
        return locale or out
    return out


@st.cache_data(ttl=3600)
def _wc_evolution(device_id, variable):
    s = _wc_session()
    did = _wc_id(device_id)
    try:
        r = s.post(
            "https://app.weathercloud.net/device/evolution",
            data={"device": did, "variable": str(variable), "period": "month"},
            timeout=25,
        )
        return ((r.json() or {}).get("data") or {}).get("values") or {}
    except Exception:
        return {}


@st.cache_data(ttl=90)
def wc_mese_mm(device_id):
    """Solo mm WC (801), per confrontare in fretta."""
    vals = _wc_evolution(device_id, "801")
    recs = []
    for ts, payload in (vals or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            stats = ((payload or {}).get("801") or {}).get("stats") or {}
            mm = stats.get("total")
            if mm is None:
                mm = stats.get("sum") or 0
            recs.append({"date": pd.Timestamp(dt), "precip": float(mm or 0)})
        except Exception:
            continue
    if not recs:
        return None
    return pd.DataFrame(recs).sort_values("date")


@st.cache_data(ttl=90)
def wc_mese_pioggia(device_id):
    """Mese WC: mm (801) + T (101) + vento raffica (541/521, m/s → km/h). Date = sito WC."""
    vals_r = _wc_evolution(device_id, "801")
    vals_t = _wc_evolution(device_id, "101")
    vals_v = _wc_evolution(device_id, "541")
    by_day = {}
    for ts, payload in (vals_r or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            stats = ((payload or {}).get("801") or {}).get("stats") or {}
            mm = stats.get("total")
            if mm is None:
                mm = stats.get("sum") or 0
            by_day[dt] = {"date": pd.Timestamp(dt), "precip": float(mm or 0)}
        except Exception:
            continue
    for ts, payload in (vals_t or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            stats = ((payload or {}).get("101") or {}).get("stats") or {}
            rec = by_day.setdefault(dt, {"date": pd.Timestamp(dt), "precip": 0.0})
            if stats.get("max") is not None:
                rec["t_max"] = float(stats["max"])
            if stats.get("min") is not None:
                rec["t_min"] = float(stats["min"])
            if stats.get("sum") is not None and stats.get("samples"):
                rec["t_med"] = round(float(stats["sum"]) / float(stats["samples"]), 1)
        except Exception:
            continue
    for ts, payload in (vals_v or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            rec = by_day.setdefault(dt, {"date": pd.Timestamp(dt), "precip": 0.0})
            payload = payload or {}
            raffica = ((payload.get("521") or {}).get("stats") or {}).get("max")
            medio = ((payload.get("541") or {}).get("stats") or {}).get("max")
            ms = raffica if raffica is not None else medio
            if ms is not None:
                rec["vento_max"] = round(float(ms) * 3.6, 1)
        except Exception:
            continue
    store = _carica_giorni_file()
    did = str(_wc_id(device_id))
    for dt, rec in list(by_day.items()):
        key = f"wc:{did}|{dt.isoformat()}"
        packed = {"date": dt.isoformat(), "precip": float(rec.get("precip") or 0)}
        for k in ("t_max", "t_min", "t_med", "vento_max"):
            if rec.get(k) is not None:
                packed[k] = rec[k]
        store[key] = packed
    oggi = datetime.now().date()
    inizio_api = min(by_day.keys()) if by_day else oggi
    for i in range(40):
        d = oggi - timedelta(days=i)
        key = f"wc:{did}|{d.isoformat()}"
        if d >= inizio_api or key not in store:
            continue
        old = store.get(key) or {}
        rec = {"date": pd.Timestamp(d), "precip": float(old.get("precip") or 0)}
        for k in ("t_max", "t_min", "t_med", "vento_max"):
            if old.get(k) is not None:
                rec[k] = float(old[k])
        by_day[d] = rec
    st.session_state["mn_giorni"] = store
    try:
        _salva_giorni_file()
    except Exception:
        pass
    if not by_day:
        return None
    df = pd.DataFrame(list(by_day.values()))
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    taglio = pd.Timestamp(oggi) - pd.Timedelta(days=30)
    df = df[df["date"] >= taglio]
    return df.sort_values("date")


def _mn_catalogo_file():
    p = Path(__file__).resolve().parent / "mn_centro.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=3600)
def mn_catalogo_pubblico():
    """Elenco dalla pagina pubblica /it/stations-list. Niente token."""
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    rows = []
    try:
        page = sess.get("https://www.meteonetwork.eu/it/stations-list", timeout=30)
        m = re.search(r'csrf-token" content="([^"]+)"', page.text or "")
        csrf = m.group(1) if m else ""
        r = sess.post(
            "https://www.meteonetwork.eu/it/get-elenco-stazioni-tabella",
            headers={
                "X-CSRF-TOKEN": csrf,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.meteonetwork.eu/it/stations-list",
                "Accept": "application/json",
            },
            timeout=90,
        )
        rows = (r.json() or {}).get("stations") or []
    except Exception:
        rows = []
    if not rows:
        return _mn_catalogo_file()
    out = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            continue
        if str(row[5] or "").upper() != "IT":
            continue
        try:
            lat, lon = float(row[1]), float(row[2])
        except Exception:
            continue
        if not (39.5 <= lat <= 43.5 and 12.0 <= lon <= 16.5):
            continue
        oggi = None
        try:
            if len(row) > 20 and row[20] not in (None, ""):
                oggi = float(row[20])
        except Exception:
            oggi = None
        mese = None
        try:
            if len(row) > 22 and row[22] not in (None, ""):
                mese = float(row[22])
        except Exception:
            mese = None
        nome = str(row[3] or row[4] or row[0])
        citta = str(row[4] or "")
        if citta and citta.lower() not in nome.lower():
            nome = f"{citta} - {nome}"
        out.append({
            "code": str(row[0]),
            "nome": nome,
            "lat": lat,
            "lon": lon,
            "oggi_mm": oggi,
            "mese_mm": mese,
        })
    if len(out) < 50:
        locale = _mn_catalogo_file()
        if locale:
            return locale
    return out


@st.cache_data(ttl=3600)
def fm_pdf_mese(slug, quale="precedente"):
    """PDF mese corrente/precedente del Semaforo Funghimagazine."""
    if not slug:
        return None
    v = datetime.now().strftime("%Y%m%d%H00")
    url = (
        f"https://funghimagazine.it/wp-content/uploads/pdf_stazioni/"
        f"storico_{quale}/{slug}.pdf?v={v}"
    )
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://funghimagazine.it/lazio-semaforo-dei-funghi/",
                "Accept": "application/pdf,*/*",
            },
            timeout=25,
        )
        if r.status_code != 200 or not (r.content or b"").startswith(b"%PDF"):
            return None
        from pypdf import PdfReader
        import io
        text = ""
        reader = PdfReader(io.BytesIO(r.content))
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    except Exception:
        return None
    records = []
    for m in re.finditer(
        r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]20\d{2})\s+(-?\d+[.,]?\d*)",
        text,
    ):
        ds, vs = m.group(1), m.group(2).replace(",", ".")
        try:
            mm = float(vs)
        except Exception:
            continue
        dt = None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(ds, fmt)
                break
            except Exception:
                continue
        if dt:
            records.append({"date": pd.Timestamp(dt.date()), "precip": mm})
    if not records:
        return None
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date")


FM_LOCALITA = {
    "Abruzzo": [
        "gran sasso", "campo imperatore", "majella", "popoli", "fara san martino",
        "atessa", "ofena", "ovindoli", "roccaraso", "sulmona", "pescasseroli",
        "scanno", "castel di sangro", "pacentro", "caramanico", "pietracamela",
        "prati di tivo", "blockhaus", "passolanciano",
        "vasto", "gissi", "casalbordino", "torino di sangro", "fossacesia",
        "lanciano", "carunchio", "carpineto", "pollutri", "pallano", "scerni",
    ],
    "Campania": [
        "matese", "piedimonte", "cusano", "irpinia", "cilento", "sarno",
        "calitri", "sapri", "amalfi", "montella", "bagnoli", "laceno",
        "serino", "roccamonfina", "teano", "avellino", "benevento",
        "picentini", "terminio", "alburni",
    ],
    "Molise": [
        "capracotta", "agnone", "matese", "montedimezzo", "collemeluccio",
        "pescopennataro", "frosolone", "guardiaregia", "isernia", "campobasso",
        "mainarde", "trivento", "roccavivara", "vinchiaturo",
    ],
    "Lazio": [
        "terminillo", "leonessa", "cimini", "soratte", "simbruini", "subiaco",
        "ernici", "fiuggi", "lepini", "aurunci", "ausoni", "rieti",
        "viterbo", "frosinone", "cassino", "sora", "alatri", "filettino",
    ],
    "Marche": [
        "sibillini", "ussita", "visso", "sarnano", "amandola", "montemonaco",
        "arquata", "acquasanta", "catria", "nerone", "carpegna", "camerino",
        "fabriano", "cingoli", "conero", "fiastra", "bolognola", "frontone",
    ],
    "Umbria": [
        "norcia", "castelluccio", "valnerina", "cascia", "cucco", "gubbio",
        "subasio", "colfiorito", "spoleto", "orvieto", "trasimeno", "amelia",
        "nocera umbra", "pietralunga", "cerreto", "preci", "terni",
    ],
}

CAPUT_FRIGORIS = {
    "valle castellana": "TE080",
    "rocca santa maria": "TE106",
    "ceppo": "TE106",
}

# stazioni CF Abruzzo con coordinate (descrizione.php + paesi)
CF_STAZIONI = [
    {"id": "AQ081", "nome": "Campo Imperatore Giardino Botanico", "lat": 42.4438, "lon": 13.5583},
    {"id": "AQ010", "nome": "Campo Felice", "lat": 42.2124, "lon": 13.4575},
    {"id": "AQ071", "nome": "Rocca di Cambio", "lat": 42.2367, "lon": 13.4890},
    {"id": "AQ059", "nome": "Ovindoli", "lat": 42.1390, "lon": 13.5230},
    {"id": "AQ024", "nome": "Rocca di Mezzo Rovere", "lat": 42.1634, "lon": 13.5180},
    {"id": "AQ023", "nome": "Fonteavignone", "lat": 42.2000, "lon": 13.5100},
    {"id": "AQ014", "nome": "Pescasseroli", "lat": 41.8080, "lon": 13.7890},
    {"id": "AQ012", "nome": "Rifugio Fioretti", "lat": 42.4550, "lon": 13.5550},
    {"id": "AQ021", "nome": "Piani di Pezza", "lat": 42.1750, "lon": 13.4600},
    {"id": "AQ020", "nome": "Altopiano delle Cinque Miglia", "lat": 41.8700, "lon": 14.0500},
    {"id": "AQ030", "nome": "Monte Genzana", "lat": 41.9510, "lon": 13.8840},
    {"id": "AQ035", "nome": "Scanno Pineta", "lat": 41.9040, "lon": 13.8790},
    {"id": "AQ124", "nome": "Villetta Barrea", "lat": 41.7760, "lon": 13.9230},
    {"id": "AQ015", "nome": "Rifugio Montecristo", "lat": 41.8600, "lon": 13.9800},
    {"id": "AQ077", "nome": "Capestrano", "lat": 42.2680, "lon": 13.7670},
    {"id": "TE080", "nome": "Valle Castellana", "lat": 42.7350, "lon": 13.4970},
    {"id": "TE106", "nome": "Il Ceppo", "lat": 42.6650, "lon": 13.4780},
    {"id": "TE013", "nome": "Rifugio Franchetti", "lat": 42.4700, "lon": 13.5650},
    {"id": "TE127", "nome": "Poggio Umbricchio", "lat": 42.5800, "lon": 13.5200},
    {"id": "CH003", "nome": "Guardiagrele", "lat": 42.1900, "lon": 14.2210},
    {"id": "PE111", "nome": "Farindola", "lat": 42.4430, "lon": 13.8220},
    {"id": "PE079", "nome": "Popoli", "lat": 42.1740, "lon": 13.8320},
    {"id": "PE078", "nome": "Bussi sul Tirino", "lat": 42.2130, "lon": 13.8250},
]


def cf_stazione_vicina(lat, lon, max_km=5.0):
    migliore = None
    for s in CF_STAZIONI:
        d = distanza_km(lat, lon, s["lat"], s["lon"])
        if d <= max_km and (migliore is None or d < migliore["distanza_km"]):
            migliore = {**s, "distanza_km": round(d, 1)}
    return migliore


@st.cache_data(ttl=1800)
def cf_scheda(station_id):
    """Pioggia giornaliera / mensile / annuale da caputfrigoris.it."""
    try:
        r = requests.get(
            f"https://www.caputfrigoris.it/station.php?id={station_id}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=25,
        )
        t = r.text or ""
    except Exception:
        return None
    idx = t.find("Pioggia")
    blocco = t[idx: idx + 900] if idx >= 0 else ""
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*mm", blocco, flags=re.I)
    oggi = mese = anno = None
    try:
        if len(nums) >= 1:
            oggi = float(nums[0])
        if len(nums) >= 2:
            mese = float(nums[1])
        if len(nums) >= 3:
            anno = float(nums[2])
    except Exception:
        return None
    nome = station_id
    m = re.search(r"<title>([^<]+)", t, flags=re.I)
    if m:
        nome = m.group(1).split("-")[0].replace("Stazione:", "").strip() or station_id
    return {"id": station_id, "nome": nome, "oggi_mm": oggi, "mese_mm": mese, "anno_mm": anno}


@st.cache_data(ttl=3600)
def mn_archivio_pubblico(code, mesi=2):
    """Giorni dalla pagina /archive della stazione. Niente token."""
    if not code:
        return None
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    try:
        scheda = sess.get(
            f"https://www.meteonetwork.eu/it/weather-station/{code}",
            timeout=25,
        )
        page = sess.get(scheda.url.rstrip("/") + "/archive", timeout=25)
        m = re.search(r'csrf-token" content="([^"]+)"', page.text or "")
        csrf = m.group(1) if m else ""
        referer = page.url
    except Exception:
        return None
    oggi = datetime.now().date()
    records = []
    for back in range(int(mesi)):
        d0 = (oggi.replace(day=1) - timedelta(days=32 * back)).replace(day=1)
        try:
            r = sess.post(
                "https://www.meteonetwork.eu/it/update-month-riepilogue",
                headers={
                    "X-CSRF-TOKEN": csrf,
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": referer,
                },
                data={"anno": d0.year, "mese": d0.month, "code": code},
                timeout=25,
            )
            js = r.json()
            rows = js.get("data") if isinstance(js, dict) else None
        except Exception:
            rows = None
        if not rows:
            continue
        for row in rows:
            try:
                g = int(str(row.get("giorno") or "0"))
                rain = float(row.get("rain") or 0)
                dt = datetime(d0.year, d0.month, g)
            except Exception:
                continue
            rec = {"date": pd.Timestamp(dt.date()), "precip": rain}
            for src, dst in (("tmax", "t_max"), ("tmin", "t_min"), ("tmed", "t_med"), ("wmax", "vento_max")):
                if row.get(src) not in (None, ""):
                    try:
                        rec[dst] = float(str(row[src]).replace(",", "."))
                    except Exception:
                        pass
            records.append(rec)
    store = _carica_giorni_file()
    for rec in records:
        d = pd.to_datetime(rec["date"]).date().isoformat()
        key = f"{code}|{d}"
        rain = float(rec.get("precip") or 0)
        old = store.get(key) or {}
        if not isinstance(old, dict):
            old = {"precip": old, "date": d}
        old_rain = None
        try:
            old_rain = float(old.get("precip") or 0)
        except Exception:
            old_rain = None
        if old_rain is not None and rain <= 0 and old_rain > 0:
            rec["precip"] = old_rain
        packed = {"precip": float(rec.get("precip") or 0), "date": d}
        for k in ("t_max", "t_min", "t_med", "vento_max"):
            if rec.get(k) is not None:
                packed[k] = rec[k]
            elif old.get(k) is not None:
                packed[k] = old[k]
                rec[k] = old[k]
        store[key] = packed
    oggi = datetime.now().date()
    have = {pd.to_datetime(r["date"]).date().isoformat() for r in records}
    for i in range(30):
        d = (oggi - timedelta(days=i)).isoformat()
        key = f"{code}|{d}"
        if d in have or key not in store:
            continue
        try:
            old = store[key] or {}
            rec = {
                "date": pd.Timestamp(d),
                "precip": float(old.get("precip") or 0),
            }
            for k in ("t_max", "t_min", "t_med", "vento_max"):
                if old.get(k) is not None:
                    rec[k] = float(old[k])
            records.append(rec)
        except Exception:
            pass
    st.session_state["mn_giorni"] = store
    _salva_giorni_file()
    if not records:
        return None
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date")


@st.cache_data(ttl=900)
def mn_interpolato(token, lat, lon):
    """Griglia MN 2.5 km (stesso dato delle mappe realtime). Serve token STANDARD."""
    if not token:
        return None
    try:
        r = requests.get(
            "https://api.meteonetwork.it/v3/interpolated-realtime",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "PorciniPredictor/1.0"},
            params={"lat": lat, "lon": lon},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        js = r.json()
        row = js[0] if isinstance(js, list) and js else js
        return row if isinstance(row, dict) else None
    except Exception:
        return None


@st.cache_data(ttl=900)
def wc_oggi(device_id):
    s = _wc_session()
    did = _wc_id(device_id)
    try:
        r = s.get(
            "https://app.weathercloud.net/device/values",
            params={"code": did},
            timeout=20,
        )
        js = r.json()
        if not isinstance(js, dict) or "rain" not in js and "temp" not in js:
            return None
        return js
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_weather_data(lat, lon, days=30, mn_token="", quota=None, max_km_stazione=35, mn_codici="", stazioni_mn=None, serie_mn=None, usa_wc=True, nome_zona="", regione=""):
    info = {
        "fonte": "ICON-2I 2km (modello sul bosco)",
        "stazione": "n/d",
        "distanza_km": None,
        "quota_stazione": None,
        "pioggia_modello_30g": None,
        "pioggia_stazione_30g": None,
    }
    forecast = None
    soil = None
    vento = riepilogo_vento(None)

    # niente Open-Meteo in calcolo: rallentava ogni zona e i mm/°C arrivano dalle stazioni
    storico_om, forecast, soil = None, None, None

    if storico_om is not None and "precip" in storico_om.columns:
        info["pioggia_modello_30g"] = round(float(storico_om["precip"].sum(skipna=True)), 1)

    def _mm(df):
        if df is None or "precip" not in df.columns:
            return None
        return round(float(df["precip"].sum(skipna=True)), 1)

    def _giorni_lista(df):
        """Giorni umidi + ultimi 8 giorni anche se a 0, così settembre si vede."""
        out = []
        if df is None or len(df) == 0 or "precip" not in df.columns:
            return out
        d = df.copy()
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        d["precip"] = pd.to_numeric(d["precip"], errors="coerce").fillna(0)
        oggi = pd.Timestamp(datetime.now().date())
        visti = set()
        for _, rr in d.sort_values("date").iterrows():
            dt = pd.to_datetime(rr["date"]).normalize()
            mm = float(rr["precip"] or 0)
            recenti = (oggi - dt).days <= 8
            if mm >= 0.2 or recenti:
                out.append(f"{dt.date()}: {mm:.1f} mm")
                visti.add(dt)
        for i in range(8):
            dt = oggi - pd.Timedelta(days=i)
            if dt not in visti:
                out.append(f"{dt.date()}: 0.0 mm")
        out.sort()
        return out

    # Caput Frigoris: nome zona oppure stazione entro 5 km
    nome_l = (nome_zona or "").lower()
    cf_id = None
    cf_meta = None
    for chiave, sid in CAPUT_FRIGORIS.items():
        if chiave in nome_l:
            cf_id = sid
            break
    if not cf_id:
        cf_meta = cf_stazione_vicina(lat, lon, max_km=5.0)
        if cf_meta:
            cf_id = cf_meta["id"]
    if cf_id:
        cf = cf_scheda(cf_id) or {"nome": cf_id, "oggi_mm": None, "mese_mm": None, "anno_mm": None}
        store = _carica_giorni_file()
        rows = []
        pref = f"{cf_id}|"
        for k, v in (store or {}).items():
            if not str(k).startswith(pref):
                continue
            try:
                rec = {
                    "date": pd.Timestamp(str((v or {}).get("date") or k.split("|", 1)[-1])),
                    "precip": float((v or {}).get("precip") or 0),
                }
                for kk in ("t_max", "t_min", "t_med", "vento_max"):
                    if v and v.get(kk) is not None:
                        rec[kk] = float(v[kk])
                rows.append(rec)
            except Exception:
                pass
        if cf.get("oggi_mm") is not None:
            rows.append({"date": pd.Timestamp(datetime.now().date()), "precip": float(cf.get("oggi_mm") or 0)})
        df_cf = None
        if rows:
            df_cf = pd.DataFrame(rows).drop_duplicates("date").sort_values("date")
            taglio = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=30)
            df_cf = df_cf[df_cf["date"] >= taglio]
        giorni = []
        if df_cf is not None:
            for _, rr in df_cf.iterrows():
                if float(rr.get("precip") or 0) >= 0.2:
                    giorni.append(f"{pd.to_datetime(rr['date']).date()}: {float(rr['precip']):.1f} mm")
        info = {
            "fonte": (
                f"Caput Frigoris {cf.get('nome')} ({cf_id})"
                + (f" · oggi {cf.get('oggi_mm')} mm" if cf.get("oggi_mm") is not None else "")
                + (f" · mese {cf.get('mese_mm')} mm" if cf.get("mese_mm") is not None else "")
                + " · agosto da archivio locale"
            ),
            "stazione": cf.get("nome") or cf_id,
            "distanza_km": (cf_meta or {}).get("distanza_km") or 0,
            "pioggia_stazione_30g": _mm(df_cf),
            "giorni_pluviometro": giorni or [
                f"oggi: {cf.get('oggi_mm')} mm",
                f"mese in corso: {cf.get('mese_mm')} mm",
            ],
        }
        if df_cf is not None and len(df_cf):
            return df_cf, info, forecast, soil, vento

    # MN solo se entro 5 km E senza troppi buchi; altrimenti WC (più giorni / più mm)
    RAGGIO_MN_BUONO = 5.0

    def _giorni_pieni(dfx):
        if dfx is None or len(dfx) == 0 or "precip" not in getattr(dfx, "columns", []):
            return 0
        try:
            dd = dfx.copy()
            dd["date"] = pd.to_datetime(dd["date"]).dt.normalize()
            taglio = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=30)
            dd = dd[dd["date"] >= taglio]
            return int(pd.to_numeric(dd["precip"], errors="coerce").notna().sum())
        except Exception:
            return 0

    def _affidabilita(dfx, online=True, dist=5.0):
        n = _giorni_pieni(dfx)
        if n < 8:
            return -1.0
        try:
            mm = float(pd.to_numeric(dfx["precip"], errors="coerce").sum())
        except Exception:
            mm = 0.0
        has_t = False
        has_v = False
        try:
            has_t = "t_max" in dfx.columns and pd.to_numeric(dfx["t_max"], errors="coerce").notna().sum() >= 5
            has_v = "vento_max" in dfx.columns and pd.to_numeric(dfx["vento_max"], errors="coerce").notna().sum() >= 5
        except Exception:
            pass
        score = n * 3.0 + min(mm, 250) * 0.6
        if has_t:
            score += 18
        if has_v:
            score += 10
        if online:
            score += 8
        score -= float(dist) * 1.5
        return score

    cat_mn_pre = mn_catalogo_pubblico()
    mn_min = 999.0
    mn_near = None
    if cat_mn_pre:
        for s in cat_mn_pre:
            dkm = distanza_km(lat, lon, s["lat"], s["lon"])
            if dkm < mn_min:
                mn_min = dkm
                mn_near = s
    n_mn = 0
    mm_mn = 0.0
    df_mn_peek = None
    if mn_near is not None and mn_min <= RAGGIO_MN_BUONO:
        df_mn_peek = mn_archivio_pubblico(mn_near.get("code"), 2)
        n_mn = _giorni_pieni(df_mn_peek)
        try:
            mm_mn = float(pd.to_numeric(df_mn_peek["precip"], errors="coerce").sum()) if df_mn_peek is not None else 0.0
        except Exception:
            mm_mn = 0.0
    wc_piu_pioggia = False
    if usa_wc and mn_min <= RAGGIO_MN_BUONO:
        try:
            cat_peek = wc_catalogo()
            candid = []
            for staz in cat_peek:
                dkm = distanza_km(lat, lon, staz["lat"], staz["lon"])
                if dkm <= RAGGIO_MN_BUONO:
                    candid.append((dkm, staz))
            candid.sort(key=lambda x: x[0])
            for dkm, staz in candid[:1]:
                df_c = wc_mese_mm(staz.get("id") or staz.get("code"))
                if df_c is None or "precip" not in df_c.columns:
                    continue
                mm_c = float(pd.to_numeric(df_c["precip"], errors="coerce").sum())
                n_c = _giorni_pieni(df_c)
                sc_c = _affidabilita(df_c, online=bool(staz.get("online", True)), dist=dkm)
                sc_m = _affidabilita(df_mn_peek, online=True, dist=mn_min)
                if sc_c > sc_m:
                    wc_piu_pioggia = True
                    break
        except Exception:
            wc_piu_pioggia = False
    ha_mn_vicina = mn_min <= RAGGIO_MN_BUONO and n_mn >= 20 and not wc_piu_pioggia
    _nz = (nome_zona or "").lower()
    d_gm = distanza_km(lat, lon, 41.350254, 14.365734)
    d_vt = distanza_km(lat, lon, 41.348467, 14.525056)
    forza_piedimonte = (
        "alife" not in _nz
        and (d_gm <= 5.0 or "piedimonte" in _nz or "castello del matese" in _nz)
    )
    forza_cusano = d_vt <= 5.0 or (("cusano" in _nz or "casano" in _nz) and ("mutri" in _nz or "mutria" in _nz))
    if forza_piedimonte and forza_cusano:
        if d_vt < d_gm:
            forza_piedimonte = False
        else:
            forza_cusano = False
    if usa_wc and (not ha_mn_vicina or forza_piedimonte or forza_cusano):
        cat = wc_catalogo()
        raggio_vicino = 5.0
        tutte_dist = []
        for staz in cat:
            dkm = distanza_km(lat, lon, staz["lat"], staz["lon"])
            if dkm <= float(max_km_stazione):
                s2 = dict(staz)
                s2["distanza_km"] = round(dkm, 1)
                tutte_dist.append(s2)
        tutte_dist.sort(key=lambda x: x["distanza_km"])
        vicine_vicine = [x for x in tutte_dist if x["distanza_km"] <= raggio_vicino]
        nome_l = (nome_zona or "").lower()
        if forza_piedimonte:
            gm = None
            for staz in cat:
                code = str(staz.get("code") or "").upper()
                nid = str(staz.get("id") or "")
                nn = (staz.get("nome") or "").lower()
                if code == "3XWWUH5" or nid == "8581011017" or "gian marco" in nn:
                    gm = dict(staz)
                    gm["distanza_km"] = round(distanza_km(lat, lon, staz["lat"], staz["lon"]), 1)
                    break
            if gm is None:
                gm = {
                    "code": "3XWWUH5",
                    "id": "8581011017",
                    "nome": "Gian Marco",
                    "lat": 41.350254,
                    "lon": 14.365734,
                    "online": True,
                    "distanza_km": round(distanza_km(lat, lon, 41.350254, 14.365734), 1),
                }
            vicine_vicine = [gm]
        if forza_cusano:
            vt = None
            for staz in cat:
                code = str(staz.get("code") or "").upper()
                nid = str(staz.get("id") or "")
                nn = (staz.get("nome") or "").lower()
                if code == "3EE8J9B" or nid == "7400786303" or "vitelli" in nn:
                    vt = dict(staz)
                    vt["distanza_km"] = round(distanza_km(lat, lon, staz["lat"], staz["lon"]), 1)
                    break
            if vt is None:
                vt = {
                    "code": "3EE8J9B",
                    "id": "7400786303",
                    "nome": "Giuseppe Vitelli",
                    "lat": 41.348467,
                    "lon": 14.525056,
                    "online": True,
                    "distanza_km": round(distanza_km(lat, lon, 41.348467, 14.525056), 1),
                }
            vicine_vicine = [vt]
        if any(k in nome_l for k in ("cusano", "mutri", "casano")) and not forza_cusano:
            preferite = [x for x in vicine_vicine if "vitelli" in (x.get("nome") or "").lower() or str(x.get("code") or "").upper() == "3EE8J9B"]
            altre = [x for x in vicine_vicine if x not in preferite]
            vicine_vicine = preferite + altre
        # WC fino a 10 km se MN è oltre 8 km dal bosco
        pool = vicine_vicine[:3]
        if pool:
            migliore = None
            df_wc = None
            for cand in pool:
                df_c = wc_mese_mm(cand.get("id") or cand["code"])
                mm_c = 0.0
                n_c = 0
                if df_c is not None and len(df_c) and "precip" in df_c.columns:
                    mm_c = float(df_c["precip"].sum(skipna=True))
                    n_c = _giorni_pieni(df_c)
                dist = float(cand.get("distanza_km") or 99)
                rank = (_affidabilita(df_c, online=bool(cand.get("online", True)), dist=dist), n_c, mm_c, -dist)
                if migliore is None or rank > migliore[0]:
                    migliore = (rank, cand, df_c, mm_c)
            s = migliore[1] if migliore else pool[0]
            df_wc = wc_mese_pioggia(s.get("id") or s.get("code")) if s else None
            if df_wc is None and migliore:
                df_wc = migliore[2]
            oggi = wc_oggi(s.get("id") or s["code"])
            if df_wc is not None and len(df_wc):
                df_mm = df_wc.copy()
                df_mm["date"] = pd.to_datetime(df_mm["date"]).dt.normalize()
                if oggi and oggi.get("rain") is not None:
                    try:
                        oggi_d = pd.Timestamp(datetime.now().date())
                        mask = df_mm["date"] == oggi_d
                        if mask.any():
                            df_mm.loc[mask, "precip"] = float(oggi["rain"])
                    except Exception:
                        pass
                giorni_txt = _giorni_lista(df_mm)
                n_pluvio = int(df_mm["precip"].notna().sum())
                if storico_om is not None:
                    serie = storico_om.copy()
                    serie["date"] = pd.to_datetime(serie["date"]).dt.normalize()
                    for _, row in df_mm.iterrows():
                        mask = serie["date"] == row["date"]
                        if mask.any():
                            serie.loc[mask, "precip"] = row["precip"]
                    df_out = serie
                else:
                    df_out = df_mm
                oggi_mm = oggi.get("rain") if oggi else None
                fonte = (
                    f"WeatherCloud {s.get('nome')} a {s.get('distanza_km')} km · più mm nel raggio 5 km"
                    + (f" · oggi {oggi_mm} mm" if oggi_mm is not None else "")
                    + f" · {n_pluvio} gg da pluviometro"
                )
                info = _info_stazione(s, fonte)
                info["giorni_pluviometro"] = giorni_txt
                info["pioggia_modello_30g"] = (
                    round(float(storico_om["precip"].sum(skipna=True)), 1) if storico_om is not None else None
                )
                info["pioggia_stazione_30g"] = _mm(df_mm)
                if "vento_max" in df_out.columns:
                    vento = riepilogo_vento(df_out)
                if oggi and oggi.get("wspdhi") is not None:
                    try:
                        vento = {
                            **(vento or {}),
                            "oggi_kmh": float(oggi.get("wspdhi") or oggi.get("wspd") or 0) * 3.6,
                        }
                    except Exception:
                        pass
                return df_out, info, forecast, soil, vento
            # stazione WC c'è ma il mese non è arrivato: uso comunque quella più vicina + modello
            if storico_om is not None:
                fonte = f"WeatherCloud {s.get('nome')} a {s.get('distanza_km')} km · mm mese non letti, uso modello sul punto stazione"
                info = _info_stazione(s, fonte)
                return storico_om, info, forecast, soil, vento

    # 1) MeteoNetwork da lista pubblica (stessa pagina /it/stations-list)
    cat_mn = None if (forza_piedimonte or forza_cusano) else mn_catalogo_pubblico()
    if cat_mn:
        vicine_pub = []
        nome_l0 = (nome_zona or "").lower()
        if any(k in nome_l0 for k in ("bojano", "boiano", "spinete")):
            vicine_pub.append({
                "code": "mls065",
                "nome": "Bojano - Loc.Massari",
                "lat": 41.486,
                "lon": 14.455,
                "distanza_km": round(distanza_km(lat, lon, 41.486, 14.455), 1),
            })
        if "amatrice" in nome_l0:
            vicine_pub.append({
                "code": "laz201",
                "nome": "Amatrice - BAGNOLO",
                "lat": 42.630707,
                "lon": 13.232802,
                "distanza_km": round(distanza_km(lat, lon, 42.630707, 13.232802), 1),
            })
            for staz in cat_mn:
                if str(staz.get("code") or "").lower() == "laz201":
                    continue
                nn = (staz.get("nome") or "").lower()
                if "bagnolo" in nn or "amatrice" in nn:
                    dkm = distanza_km(lat, lon, staz["lat"], staz["lon"])
                    if dkm <= 20:
                        s2 = dict(staz)
                        s2["distanza_km"] = round(dkm, 1)
                        vicine_pub.append(s2)
            vicine_pub.sort(key=lambda x: (0 if "laz201" == str(x.get("code") or "").lower() else 1, x["distanza_km"]))
        if not vicine_pub:
            for staz in cat_mn:
                dkm = distanza_km(lat, lon, staz["lat"], staz["lon"])
                if dkm <= RAGGIO_MN_BUONO:
                    s2 = dict(staz)
                    s2["distanza_km"] = round(dkm, 1)
                    vicine_pub.append(s2)
            vicine_pub.sort(key=lambda x: x["distanza_km"])
        if not vicine_pub and cat_mn:
            nome_l = (nome_zona or "").lower()
            chiavi = [w for w in re.split(r"[^a-zàèéìòù]+", nome_l) if len(w) >= 5]
            for s0 in cat_mn:
                nn = (s0.get("nome") or "").lower()
                dkm = distanza_km(lat, lon, s0["lat"], s0["lon"])
                if any(k in nn for k in chiavi) and dkm <= RAGGIO_MN_BUONO:
                    s0 = dict(s0)
                    s0["distanza_km"] = round(dkm, 1)
                    vicine_pub.append(s0)
                    break
            if not vicine_pub:
                extra = []
                for s0 in cat_mn:
                    dkm = distanza_km(lat, lon, s0["lat"], s0["lon"])
                    extra.append((dkm, s0))
                extra.sort(key=lambda x: x[0])
                if extra and extra[0][0] <= RAGGIO_MN_BUONO:
                    s0 = dict(extra[0][1])
                    s0["distanza_km"] = round(extra[0][0], 1)
                    vicine_pub.append(s0)
        if vicine_pub:
            s = vicine_pub[0]
            prefer = {str(x.get("code") or "").lower(): x for x in vicine_pub}
            nome_l = (nome_zona or "").lower()
            if "mls071" in prefer and (
                "capracotta" in nome_l
                or str(s.get("code") or "").lower() in {"mls052", "mls064"}
            ):
                s = prefer["mls071"]
            if any(k in nome_l for k in ("bojano", "boiano", "spinete")) and "mls065" in prefer:
                s = prefer["mls065"]
            mesi_arch = 3 if str(s.get("code") or "").lower() == "laz201" else 2
            df_mn = mn_archivio_pubblico(s["code"], mesi_arch)
            if df_mn is None and mn_token:
                df_mn = mn_dati_stazione(mn_token, s["code"], days)
            store = _carica_giorni_file()
            recs = []
            pref = str(s.get("code") or "").lower() + "|"
            for k, v in (store or {}).items():
                if not str(k).lower().startswith(pref):
                    continue
                try:
                    rec = {
                        "date": pd.Timestamp(str((v or {}).get("date") or k.split("|", 1)[-1])),
                        "precip": float((v or {}).get("precip") or 0),
                    }
                    for kk in ("t_max", "t_min", "t_med", "vento_max"):
                        if v and v.get(kk) is not None:
                            rec[kk] = float(v[kk])
                    recs.append(rec)
                except Exception:
                    pass
            if recs:
                df_store = pd.DataFrame(recs)
                if df_mn is None or not len(df_mn):
                    df_mn = df_store
                else:
                    df_mn = pd.concat([df_store, df_mn], ignore_index=True)
                df_mn["date"] = pd.to_datetime(df_mn["date"], errors="coerce")
                df_mn = df_mn.dropna(subset=["date"]).drop_duplicates("date", keep="last").sort_values("date")
            serie = None
            if df_mn is not None and len(df_mn):
                df_mn = df_mn.copy()
                df_mn["date"] = pd.to_datetime(df_mn["date"]).dt.normalize()
                taglio = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=30)
                df_mn30 = df_mn[df_mn["date"] >= taglio].copy()
                serie = df_mn30
                oggi_d = pd.Timestamp(datetime.now().date())
                if s.get("oggi_mm") is not None:
                    if (serie["date"] == oggi_d).any():
                        serie.loc[serie["date"] == oggi_d, "precip"] = s["oggi_mm"]
                    else:
                        extra = {"date": oggi_d, "precip": float(s["oggi_mm"])}
                        serie = pd.concat([serie, pd.DataFrame([extra])], ignore_index=True)
            n_gg = int(df_mn["precip"].notna().sum()) if df_mn is not None and len(df_mn) else 0
            fonte = (
                f"MeteoNetwork {s.get('nome')} ({s.get('code')}) a {s.get('distanza_km')} km"
                + (f" · oggi {s.get('oggi_mm')} mm" if s.get("oggi_mm") is not None else "")
                + (f" · {n_gg} gg archivio" if n_gg else " · lista pubblica")
            )
            info = _info_stazione(s, fonte)
            info["giorni_pluviometro"] = _giorni_lista(serie) if serie is not None else []
            if serie is not None and len(serie):
                info["pioggia_stazione_30g"] = _mm(serie)
                if "vento_max" in serie.columns:
                    vento = riepilogo_vento(serie)
            else:
                info["pioggia_stazione_30g"] = 0.0
                serie = pd.DataFrame({"date": [], "precip": []})
            return serie, info, forecast, soil, vento

    # 1b) MeteoNetwork token (codici manuali) se la lista pubblica non basta
    #    (evita 30 chiamate/giorno che fanno 429 e fanno sparire MN).
    if mn_token and not (forza_piedimonte or forza_cusano):
        stazioni = list(stazioni_mn or [])
        if not stazioni:
            stazioni = mn_stazioni_da_codici(mn_token, mn_codici)
        vicine_mn = mn_stazioni_vicine(lat, lon, stazioni, quota=quota, n=3, max_km=max_km_stazione)
        if vicine_mn:
            s = vicine_mn[0]
            df_mn = None
            if serie_mn and s.get("code") in (serie_mn or {}):
                df_mn = serie_mn.get(s["code"])
            if df_mn is None:
                df_mn = mn_dati_stazione(mn_token, s["code"], days)
            df_punto_staz = None
            try:
                df_punto_staz, _, _, _ = get_openmeteo_bundle(s["lat"], s["lon"], days)
            except Exception:
                df_punto_staz = None
            serie = df_punto_staz if df_punto_staz is not None else storico_om
            n_pluvio = 0
            if serie is not None and df_mn is not None and len(df_mn):
                serie = serie.copy()
                n_pluvio = int(df_mn["precip"].notna().sum()) if "precip" in df_mn.columns else len(df_mn)
                for _, row in df_mn.iterrows():
                    if pd.isna(row.get("date")):
                        continue
                    mask = pd.to_datetime(serie["date"]).dt.normalize() == pd.to_datetime(row["date"]).normalize()
                    if mask.any() and not pd.isna(row.get("precip")):
                        serie.loc[mask, "precip"] = row["precip"]
            if serie is not None:
                oggi_mm = None
                if df_mn is not None and len(df_mn) and "precip" in df_mn.columns:
                    oggi_mm = df_mn.iloc[-1]["precip"]
                fonte = (
                    f"MeteoNetwork {s.get('nome')} a {s.get('distanza_km')} km"
                    + (f" · oggi pluviometro {oggi_mm} mm" if oggi_mm is not None else "")
                    + (f" · {n_pluvio} gg da pluviometro" if n_pluvio else " · 30g modello sul punto stazione")
                )
                info = _info_stazione(s, fonte)
                giorni_txt = []
                if df_mn is not None and len(df_mn) and "precip" in df_mn.columns:
                    tmp = df_mn.dropna(subset=["date"]).sort_values("date")
                    for _, rr in tmp.iterrows():
                        giorni_txt.append(f"{pd.to_datetime(rr['date']).date()}: {float(rr['precip']):.1f} mm")
                info["giorni_pluviometro"] = giorni_txt
                info["pioggia_modello_30g"] = (
                    round(float(storico_om["precip"].sum(skipna=True)), 1) if storico_om is not None else None
                )
                info["pioggia_stazione_30g"] = _mm(serie)
                return serie, info, forecast, soil, vento

    # 1b) MeteoNetwork interpolato 2.5 km (mappe realtime) se WC è oltre 5 km
    if mn_token and storico_om is not None:
        inter = mn_interpolato(mn_token, lat, lon)
        if inter:
            serie = storico_om.copy()
            rain = inter.get("daily_rain") or inter.get("rain")
            try:
                if rain not in (None, ""):
                    oggi_d = pd.Timestamp(datetime.now().date())
                    serie["date"] = pd.to_datetime(serie["date"]).dt.normalize()
                    mask = serie["date"] == oggi_d
                    if mask.any():
                        serie.loc[mask, "precip"] = float(rain)
            except Exception:
                pass
            fonte_mn = "MeteoNetwork interpolato 2,5 km (mappe realtime)"
            if rain not in (None, ""):
                fonte_mn += f" · oggi {rain} mm"
            info = {
                "fonte": fonte_mn,
                "stazione": "griglia MN sul bosco",
                "distanza_km": 0,
                "quota_stazione": None,
                "pioggia_modello_30g": _mm(storico_om),
                "pioggia_stazione_30g": _mm(serie),
                "giorni_pluviometro": [f"{datetime.now().date()}: {rain} mm"] if rain not in (None, "") else [],
            }
            return serie, info, forecast, soil, vento

    # 2) ufficiale SOLO se è vicina al bosco (altrimenti i mm non c'entrano)
    limite_ufficiale = min(18, max_km_stazione)
    for s in stazioni_ufficiali_vicine(lat, lon, quota=quota, n=4, max_km=limite_ufficiale):
        dq = None
        if quota is not None and s.get("quota") is not None:
            dq = abs(quota - s["quota"])
        if dq is not None and dq > 400:
            continue
        df_st = get_stazione_dati(s["id"], days)
        if df_st is not None and df_st["precip"].notna().sum() >= 8:
            info = _info_stazione(s, "Stazione ufficiale vicina")
            info["pioggia_modello_30g"] = (
                round(float(storico_om["precip"].sum(skipna=True)), 1) if storico_om is not None else None
            )
            info["pioggia_stazione_30g"] = _mm(df_st)
            return df_st, info, forecast, soil, vento

    info["fonte"] = "Nessuna stazione MeteoNetwork/Caput Frigoris nel raggio"
    return None, info, forecast, soil, vento


def specie_porcini(tipo_bosco, quota=1000, t_max_media=20.0, mese=None):
    """4 specie da FunghiMagazine: albero + quota + mese + caldo."""
    if mese is None:
        mese = datetime.now().month
    tipo = (tipo_bosco or "").lower()
    q = float(quota or 1000)
    t = float(t_max_media or 20)

    # alberi: chi può uscire in quel bosco (articolo FM)
    base = {
        "faggio": ["estatino", "edulis", "pinicola"],
        "castagno": ["estatino", "edulis", "pinicola", "aereus"],
        "quercia": ["estatino", "aereus", "edulis"],
        "abete_bianco": ["pinicola", "edulis", "estatino"],
        "abete_rosso": ["pinicola", "edulis"],
    }
    possibili = list(base.get(tipo, ["estatino", "edulis"]))
    # Centro-Sud: aereus su quercia/castagno, non in faggeta
    if tipo == "quercia" and t < 18:
        if "pinicola" not in possibili:
            possibili.append("pinicola")

    # stagione
    if mese in (3, 4, 5):
        stagione = {"estatino": 3, "pinicola": 3, "aereus": 1, "edulis": 1}
    elif mese in (6, 7, 8):
        stagione = {"aereus": 3, "estatino": 3, "edulis": 1, "pinicola": 1}
    elif mese == 9:
        stagione = {"estatino": 3, "edulis": 2, "aereus": 2, "pinicola": 2}
    elif mese in (10, 11):
        stagione = {"edulis": 3, "pinicola": 3, "estatino": 1, "aereus": 1}
    else:
        stagione = {"edulis": 2, "pinicola": 2, "estatino": 0, "aereus": 0}

    # clima: estatino/aereus amano il caldo; edulis/pinicola il fresco
    clima = {"estatino": 0, "aereus": 0, "edulis": 0, "pinicola": 0}
    if t >= 26:
        clima["aereus"] += 2
        clima["estatino"] += 2
        clima["edulis"] -= 1
        clima["pinicola"] -= 2
    elif t >= 22:
        clima["estatino"] += 2
        clima["aereus"] += 1
    elif 16 <= t <= 22:
        clima["edulis"] += 2
        clima["pinicola"] += 1
        clima["estatino"] += 1
    else:
        clima["pinicola"] += 2
        clima["edulis"] += 1
        clima["aereus"] -= 2
        clima["estatino"] -= 1
    if q >= 1200 and mese in (6, 7, 8, 9):
        clima["estatino"] += 2
        clima["edulis"] += 1
        clima["pinicola"] += 1
    elif q >= 1400:
        clima["pinicola"] += 2
        clima["edulis"] += 1
        clima["aereus"] -= 1
    elif q <= 600:
        clima["aereus"] += 1
        if mese in (6, 7, 8):
            clima["estatino"] -= 1
        else:
            clima["estatino"] += 1
        clima["pinicola"] -= 1

    nomi = {
        "estatino": "Estatino (B. reticulatus)",
        "aereus": "Nero / bronzino (B. aereus)",
        "edulis": "Chiaro tardivo (B. edulis)",
        "pinicola": "Pinicola (B. pinophilus)",
    }
    out = []
    for sp in possibili:
        punti = stagione.get(sp, 0) + clima.get(sp, 0)
        if punti >= 4:
            stato = "probabile"
        elif punti >= 2:
            stato = "possibile"
        else:
            stato = "fuori stagione"
        out.append({"id": sp, "nome": nomi[sp], "stato": stato, "punti": punti})
    out.sort(key=lambda x: -x["punti"])
    return out


def trova_buttate(df, giorni_attesa, t_max_media=20.0, fattore_v=1.0):
    """Buttata secondo FunghiMagazine: nasce 12-15 gg dopo pioggia importante,
    dura in media 15 gg, 15-20 se condizioni buone, fino a ~30 se ideali
    (poco vento, temp non estreme, tanta acqua prima)."""
    if df is None or len(df) == 0 or "precip" not in df.columns:
        return []
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    d["precip"] = pd.to_numeric(d["precip"], errors="coerce").fillna(0)
    d = d.sort_values("date")
    eventi = []
    acc = 0.0
    start = None
    last = None
    for _, row in d.iterrows():
        mm = float(row["precip"])
        giorno = row["date"]
        if mm >= 2:
            if start is None:
                start = giorno
                acc = mm
            elif last is not None and (giorno - last).days <= 3:
                acc += mm
            else:
                if acc >= 20:
                    eventi.append((last or start, acc))
                start = giorno
                acc = mm
            last = giorno
        elif start is not None and last is not None and (giorno - last).days > 3:
            if acc >= 20:
                eventi.append((last, acc))
            start, acc, last = None, 0.0, None
    if start is not None and acc >= 20:
        eventi.append((last or start, acc))

    oggi = pd.Timestamp(datetime.now().date())
    # caldo torrido + vento: FM dice che inibiscono o chiudono la buttata
    if t_max_media >= 30:
        dur_clima = 0.55
    elif t_max_media >= 27:
        dur_clima = 0.72
    elif 16 <= t_max_media <= 26:
        dur_clima = 1.0
    else:
        dur_clima = 0.9
    if fattore_v < 0.4:
        dur_clima *= 0.55
    elif fattore_v < 0.7:
        dur_clima *= 0.75
    out = []
    for data_evt, mm in eventi:
        # base 15 gg; 20 se tanta acqua; fino a 30 se spugnata abbondante e clima ok
        if mm >= 60 and dur_clima >= 0.95:
            durata = 28
        elif mm >= 40 and dur_clima >= 0.85:
            durata = 20
        else:
            durata = 15
        durata = max(7, round(durata * dur_clima))
        inizio = pd.Timestamp(data_evt) + pd.Timedelta(days=giorni_attesa)
        fine = inizio + pd.Timedelta(days=durata)
        # senza pioggia recente il terreno si asciuga: buttata chiusa
        dopo = d[d["date"] >= pd.Timestamp(data_evt)]
        ultima_umida = None
        if len(dopo):
            umide = dopo[dopo["precip"] >= 5]
            if len(umide):
                ultima_umida = pd.to_datetime(umide["date"].max()).normalize()
        if ultima_umida is not None:
            asciutto = int((oggi - ultima_umida).days)
            if asciutto >= 10:
                fine = min(fine, ultima_umida + pd.Timedelta(days=10))
        attiva = bool(inizio.normalize() <= oggi <= fine.normalize())
        if ultima_umida is not None and (oggi - ultima_umida).days >= 10:
            attiva = False
        out.append({
            "pioggia_mm": round(float(mm), 1),
            "data_pioggia": pd.Timestamp(data_evt).date().isoformat(),
            "inizio": inizio.date().isoformat(),
            "fine": fine.date().isoformat(),
            "attiva": attiva,
            "giorni_alla_fine": int((fine.normalize() - oggi).days) if attiva else None,
        })
    return out


def finestra_uscita(giorni_dalla_pioggia, giorni_attesa, forecast):
    """Stima i prossimi giorni utili in base al ritardo dalla spugnata e alla previsione."""
    if giorni_dalla_pioggia is None or giorni_dalla_pioggia >= 99:
        return "Attendi una buona pioggia (≥30 mm cumulati)"

    inizio = giorni_attesa - 3
    fine = giorni_attesa + 5
    oggi_offset = giorni_dalla_pioggia

    if inizio <= oggi_offset <= fine:
        stato = "Finestra aperta adesso"
    elif oggi_offset < inizio:
        manca = inizio - oggi_offset
        stato = f"Ancora presto — prova tra {manca}–{manca + 4} giorni"
    else:
        stato = "Finestra in chiusura / già passata"

    pioggia_prevista = 0.0
    if forecast is not None and len(forecast):
        pioggia_prevista = float(forecast["precip"].sum())
        if pioggia_prevista >= 20:
            stato += f" · in arrivo ~{pioggia_prevista:.0f} mm (nuova spugnata)"
    return stato


def calcola_punteggio(df, tipo_bosco, regole, quota=1000, soil=None, forecast=None, vento=None):
    if df is None or len(df) < 5:
        return 0, "Dati insufficienti", {}

    precip_totale = float(df["precip"].sum())
    giorni_con_pioggia = int((df["precip"] > 1).sum())
    def _media(col, fallback):
        if df is None or col not in df.columns:
            return fallback, None
        v = float(pd.to_numeric(df[col], errors="coerce").mean())
        if pd.isna(v):
            return fallback, None
        return v, round(v, 1)

    t_max_media, t_max_view = _media("t_max", 20.0)
    t_min_media, t_min_view = _media("t_min", 12.0)
    _, t_med_view = _media("t_med", None)

    # ultimi 10 giorni pesano di più del mese intero
    coda = df.tail(10)
    precip_10g = float(coda["precip"].sum())

    pioggia_min = regole["pioggia_min"]
    pioggia_max = regole["pioggia_max"]

    # in quota le temperature ideali sono più basse
    if quota >= 1400:
        t_max_ok = (18, 24)
        t_min_ok = (8, 14)
    elif quota >= 1000:
        t_max_ok = (20, 26)
        t_min_ok = (10, 16)
    else:
        t_max_ok = (22, 28)
        t_min_ok = (12, 18)

    if t_max_media > 27:
        pioggia_min += 15
        pioggia_max += 20
    elif t_max_media > 25:
        pioggia_min += 8
        pioggia_max += 12

    if precip_totale < pioggia_min * 0.5:
        score_pioggia = 0
    elif precip_totale < pioggia_min:
        score_pioggia = 20 * (precip_totale / pioggia_min)
    elif precip_totale <= pioggia_max:
        score_pioggia = 50
        if giorni_con_pioggia >= 5:
            score_pioggia = 55
        if giorni_con_pioggia >= 8:
            score_pioggia = 60
    else:
        score_pioggia = max(10, 40 - (precip_totale - pioggia_max) * 0.5)

    if precip_10g >= 15:
        score_pioggia = min(65, score_pioggia + 5)

    score_temp = 0
    if t_max_ok[0] <= t_max_media <= t_max_ok[1]:
        score_temp += 25
    elif t_max_ok[0] - 3 <= t_max_media <= t_max_ok[1] + 3:
        score_temp += 15
    else:
        score_temp += 5

    if t_min_ok[0] <= t_min_media <= t_min_ok[1]:
        score_temp += 15
    elif t_min_ok[0] - 3 <= t_min_media <= t_min_ok[1] + 3:
        score_temp += 10
    else:
        score_temp += 3

    # FM: estivi 12-15 gg dopo l'ultima pioggia importante;
    # in faggeta (più fresca, pinophilus/edulis) un filo più lunga
    specie = specie_porcini(tipo_bosco, quota, t_max_media)
    top_sp = next((s for s in specie if s["stato"] != "fuori stagione"), specie[0] if specie else None)
    # FM: estatino/aereus più rapidi dopo i tepori; edulis/pinicola dopo piogge fresche
    if top_sp and top_sp["id"] in ("estatino", "aereus"):
        giorni_attesa = 12
    elif tipo_bosco in ("faggio", "abete_bianco", "abete_rosso"):
        giorni_attesa = 15
    elif tipo_bosco == "castagno":
        giorni_attesa = 13
    else:
        giorni_attesa = 12

    vento = vento or riepilogo_vento(df if df is not None and "vento_max" in df.columns else None)
    fattore_v = float(vento.get("fattore_vento") or 1.0)
    buttate = trova_buttate(df, giorni_attesa, t_max_media, fattore_v)
    attive = [b for b in buttate if b.get("attiva")]
    giorni_dalla_pioggia = 99
    if buttate:
        ultima = pd.to_datetime(buttate[-1]["data_pioggia"])
        giorni_dalla_pioggia = int((pd.Timestamp(datetime.now().date()) - ultima.normalize()).days)

    if len(attive) >= 2:
        score_tempo = 28
    elif attive:
        score_tempo = 22
    elif buttate:
        # c'è stata acqua ma la buttata è finita o non è ancora nata
        prossime = [b for b in buttate if pd.to_datetime(b["inizio"]) > pd.Timestamp(datetime.now().date())]
        score_tempo = 12 if prossime else 4
    else:
        score_tempo = 3

    score_suolo = 0
    if soil is not None:
        # valori volumetrici tipici 0.15–0.40 m3/m3
        if 0.22 <= soil <= 0.38:
            score_suolo = 10
        elif 0.18 <= soil <= 0.42:
            score_suolo = 5

    # il vento persistente brucia l'effetto della pioggia e del suolo
    umido = (score_pioggia + score_tempo + score_suolo) * fattore_v
    punteggio_totale = min(100, umido + score_temp * (0.45 + 0.55 * fattore_v))
    if attive:
        pezzi = [f"{b['pioggia_mm']} mm il {b['data_pioggia']} (fino al {b['fine']})" for b in attive]
        consiglio = "Buttata aperta: " + " · ".join(pezzi)
        if len(attive) >= 2:
            consiglio = "Buttate incrociate · " + consiglio
    elif buttate:
        ultime = buttate[-1]
        if pd.to_datetime(ultime["inizio"]) > pd.Timestamp(datetime.now().date()):
            consiglio = f"Buttata in arrivo dal {ultime['inizio']} (pioggia {ultime['pioggia_mm']} mm il {ultime['data_pioggia']})"
        else:
            consiglio = f"Buttata chiusa il {ultime['fine']} — serve una nuova spugnata"
    else:
        consiglio = finestra_uscita(giorni_dalla_pioggia, giorni_attesa, forecast)
    attese = [s for s in specie if s["stato"] in ("probabile", "possibile")]
    if attese:
        txt_sp = ", ".join(f"{s['nome']} ({s['stato']})" for s in attese[:3])
        consiglio = f"Specie: {txt_sp} · " + consiglio
    if fattore_v < 0.5:
        consiglio = vento.get("nota_vento", "Vento secco") + " · " + consiglio

    dettaglio = {
        "precip_totale_30g": round(precip_totale, 1),
        "precip_10g": round(precip_10g, 1),
        "giorni_con_pioggia": giorni_con_pioggia,
        "t_max_media": t_max_view if t_max_view is not None else "n/d",
        "t_min_media": t_min_view if t_min_view is not None else "n/d",
        "t_med_media": t_med_view if t_med_view is not None else "n/d",
        "giorni_dalla_buona_pioggia": giorni_dalla_pioggia if giorni_dalla_pioggia < 99 else "n/d",
        "giorni_attesa_consigliati": giorni_attesa,
        "umidita_suolo": soil if soil is not None else "n/d",
        "consiglio": consiglio,
        "vento_medio_10g": vento.get("vento_medio_10g"),
        "vento_max_10g": vento.get("vento_max_10g"),
        "giorni_vento_20": vento.get("giorni_oltre_20"),
        "giorni_vento_30": vento.get("giorni_oltre_30"),
        "giorni_vento_consecutivi": vento.get("giorni_consecutivi_venti"),
        "fattore_vento": vento.get("fattore_vento"),
        "nota_vento": vento.get("nota_vento"),
        "picchi_vento": vento.get("picchi_vento") or [],
        "picco_max_data": vento.get("picco_max_data"),
        "picco_max_kmh": vento.get("picco_max_kmh"),
        "buttate": buttate,
        "buttate_attive": len(attive),
        "specie": specie,
        "specie_testo": ", ".join(
            f"{s['nome']} ({s['stato']})" for s in specie if s["stato"] != "fuori stagione"
        ) or "nessuna in stagione",
    }

    # senza buttata aperta non è verde, anche con 60 mm a inizio mese
    if not attive:
        punteggio_totale = min(punteggio_totale, 48)
        dettaglio["consiglio"] = consiglio
    # Poca acqua nel mese: non può essere una buttata "ALTA"
    if precip_totale < 25:
        punteggio_totale = min(punteggio_totale, 42)
        consiglio = f"Poca pioggia in 30g ({precip_totale:.0f} mm) · " + consiglio
        dettaglio["consiglio"] = consiglio

    if punteggio_totale >= 70:
        livello = "🟢 ALTO - condizioni molto buone"
    elif punteggio_totale >= 50:
        livello = "🟡 MEDIO - condizioni discrete"
    elif punteggio_totale >= 30:
        livello = "🟠 BASSO - ancora presto o condizioni deboli"
    else:
        livello = "🔴 SCARSO - condizioni non favorevoli"

    return punteggio_totale, livello, dettaglio


def invia_email(destinatario, oggetto, corpo, smtp_user, smtp_pass):
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = destinatario
        msg["Subject"] = oggetto
        msg.attach(MIMEText(corpo, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True, "Email inviata con successo!"
    except Exception as e:
        return False, f"Errore invio email: {str(e)}"


def analizza_punto(p, regole, mn_token, max_km_stazione=35, mn_codici="", stazioni_mn=None, serie_mn=None, usa_wc=True):
    df, info_meteo, forecast, soil, vento = get_weather_data(
        p["lat"], p["lon"], days=30, mn_token=mn_token or "",
        quota=p.get("quota"), max_km_stazione=max_km_stazione,
        mn_codici=mn_codici, stazioni_mn=stazioni_mn, serie_mn=serie_mn,
        usa_wc=usa_wc, nome_zona=p.get("nome") or "", regione=p.get("regione") or "",
    )
    score, livello, det = calcola_punteggio(
        df, p["tipo"], regole, quota=p.get("quota", 1000),
        soil=soil, forecast=forecast, vento=vento,
    )
    return {**p, "score": score, "livello": livello, "dettaglio": det, "meteo": info_meteo}


def calcola_tutti(punti, regole, mn_token, max_km_stazione=35, max_workers=8, mn_codici="", stazioni_mn=None, serie_mn=None, usa_wc=True):
    risultati = []
    tot = max(1, len(punti))
    barra = st.progress(0, text=f"Calcolo 0/{tot} zone (0%)")
    fatti = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut = {
            ex.submit(analizza_punto, p, regole, mn_token, max_km_stazione, mn_codici, stazioni_mn, serie_mn, usa_wc): p
            for p in punti
        }
        for f in as_completed(fut):
            try:
                risultati.append(f.result())
            except Exception as e:
                p = fut[f]
                risultati.append({
                    **p,
                    "score": 0,
                    "livello": f"Errore: {e}",
                    "dettaglio": {},
                    "meteo": {"fonte": "errore", "stazione": "n/d", "distanza_km": None},
                })
            fatti += 1
            pct = int(fatti * 100 / tot)
            barra.progress(pct / 100, text=f"Calcolo {fatti}/{tot} zone ({pct}%)")
    barra.progress(1.0, text=f"Calcolo {tot}/{tot} zone (100%)")
    return sorted(risultati, key=lambda x: x["score"], reverse=True)


# ===================== UI =====================
st.markdown(
    """
    <div class="hero">
      <p class="kicker">Micelio · Appennino</p>
      <div class="hero-title">
        <span class="hero-fungo">🍄‍🟫</span>
        <h1>Boletus Map</h1>
        <span class="hero-fungo">🍄‍🟫</span>
      </div>
      <p class="lede">Mappa interattiva crescita Boletus<br>&amp;<br>Mappa Live piogge (dati presi direttamente dal sito della Protezione Civile)</p>
      <div class="chip-row">
        <span class="chip">Abruzzo</span>
        <span class="chip">Molise</span>
        <span class="chip">Lazio</span>
        <span class="chip">Campania</span>
        <span class="chip">Marche</span>
        <span class="chip">Umbria</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    usa_wc = True
    mn_email, mn_pass, collega_mn = "", "", False
    mn_token_manuale, mn_codici = "", ""

    st.markdown(
        """
        <div class="side-hero">
          <div class="side-hero-emoji">🍄‍🟫</div>
          <p class="kicker">Diario del bosco</p>
          <h3>Boletus Map</h3>
          <p class="side-quote">Nei boschi conquistò la sua misura. Laggiù, per la prima volta in vita sua, si sentiva consolato, come se fino a quel momento non avesse mai trovato alcuna consolazione. E ogni volta, sulla soglia del bosco, si sentiva indomabile, come prima di compiere un atto grandioso; come prima di un giorno grandioso.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.header("Filtri del bosco")
    st.markdown("**Regioni da calcolare**")
    c1, c2, c3 = st.columns(3)
    with c1:
        r_abr = st.checkbox("Abruzzo", value=False)
        r_mol = st.checkbox("Molise", value=True)
    with c2:
        r_laz = st.checkbox("Lazio", value=False)
        r_cam = st.checkbox("Campania", value=False)
    with c3:
        r_mar = st.checkbox("Marche", value=False)
        r_umb = st.checkbox("Umbria", value=False)
    regioni_sel = [n for n, on in (
        ("Abruzzo", r_abr), ("Molise", r_mol), ("Lazio", r_laz),
        ("Campania", r_cam), ("Marche", r_mar), ("Umbria", r_umb),
    ) if on]
    st.markdown("**Tipo di bosco**")
    t1, t2 = st.columns(2)
    with t1:
        t_fag = st.checkbox("Faggio", value=True)
        t_cas = st.checkbox("Castagno", value=True)
        t_que = st.checkbox("Quercia", value=True)
    with t2:
        t_ab = st.checkbox("Abete bianco", value=True)
        t_ar = st.checkbox("Abete rosso", value=True)
    tipi_sel = [k for k, on in (
        ("faggio", t_fag), ("castagno", t_cas), ("quercia", t_que),
        ("abete_bianco", t_ab), ("abete_rosso", t_ar),
    ) if on]
    quota_range = st.slider("Quota (m)", 0, 1800, (0, 1800), step=50)
    cerca = st.text_input("Cerca zona (nome)", value="", placeholder="es. matese, sangro…")
    q_cerca = (cerca or "").strip().lower()
    if q_cerca:
        suggeriti = []
        visti = set()
        for p in PUNTI:
            n = p["nome"]
            if q_cerca in n.lower() and n not in visti:
                visti.add(n)
                suggeriti.append(n)
            if len(suggeriti) >= 15:
                break
        if suggeriti:
            st.caption(f"{len(suggeriti)} zone")
            scelto = st.selectbox(
                "Suggerimenti",
                ["— continua a scrivere —"] + suggeriti,
                label_visibility="collapsed",
            )
            if scelto and not scelto.startswith("—"):
                cerca = scelto
        else:
            st.caption("Nessuna zona con queste lettere")

    st.markdown("---")
    pioggia_min = st.slider("Pioggia minima ideale (mm / 30gg)", 20, 80, 40)
    pioggia_max = st.slider("Pioggia massima ideale (mm / 30gg)", 60, 150, 100)
    max_km_stazione = 5.0
    _carica_giorni_file()
    if st.session_state.get("mn_push_ok"):
        st.caption("Archivio piogge su GitHub")
    elif st.session_state.get("mn_push_err"):
        st.caption(f"Archivio GitHub: {st.session_state.get('mn_push_err')}")
    st.markdown("---")
    if st.button("Esci", use_container_width=True):
        st.session_state["app_ok"] = False
        st.session_state["ruolo"] = "guest"
        st.rerun()
    calcola = st.button("🍄‍🟫 Calcola / aggiorna dati", type="primary", use_container_width=True)

regole = {"pioggia_min": pioggia_min, "pioggia_max": pioggia_max}
mn_token = ""
email_dest, smtp_user, smtp_pass = "", "", ""

punti_filtrati = [
    p for p in PUNTI
    if p["regione"] in regioni_sel
    and p["tipo"] in tipi_sel
    and quota_range[0] <= p["quota"] <= quota_range[1]
    and (cerca.lower() in p["nome"].lower() if cerca else True)
]

st.header("🍄‍🟫 Situazione attuale")
st.write(f"Zone selezionate: **{len(punti_filtrati)}** su {len(PUNTI)} totali")

if not punti_filtrati:
    st.warning("Seleziona almeno una regione e un tipo di bosco nella sidebar.")
    st.stop()

stazioni_mn = mn_stazioni_da_codici(mn_token, mn_codici) if (mn_token and mn_codici) else []
if mn_token and mn_codici:
    if stazioni_mn:
        st.sidebar.success("Stazioni MN lette: " + ", ".join(f"{s['nome']} ({s['code']})" for s in stazioni_mn))
        if st.session_state.get("mn_progresso"):
            st.sidebar.info("Pluviometro " + st.session_state["mn_progresso"] + ". Ripremi Calcola per aggiungere altri giorni (max 4 per volta).")
    else:
        st.sidebar.error(
            "Codici inseriti ma nessuna stazione letta. Aspetta se c'è stato un 429, "
            "poi un solo Calcola. Verifica i codici sulla scheda MN."
        )

if calcola or "risultati" not in st.session_state:
    serie_mn = {}
    if calcola and stazioni_mn:
        with st.spinner(f"Scarico fino a 4 giorni nuovi di pluviometro (obiettivo 30 gg)..."):
            report = []
            for s in stazioni_mn:
                df_s, n_ok, n_tot = mn_serie_giornaliera(mn_token, s["code"], 30, 4)
                serie_mn[s["code"]] = df_s
                report.append(f"{s['nome']}: {n_ok}/{n_tot} gg")
            st.session_state["mn_progresso"] = " · ".join(report)
    with st.spinner(f"Calcolo su {len(punti_filtrati)} zone..."):
        st.session_state["risultati"] = calcola_tutti(
            punti_filtrati, regole, mn_token,
            max_km_stazione=max_km_stazione,
            mn_codici=mn_codici,
            stazioni_mn=stazioni_mn,
            serie_mn=serie_mn,
            usa_wc=usa_wc,
        )
        _salva_giorni_file()
        st.session_state["filtro_usato"] = {
            "regioni": regioni_sel,
            "tipi": tipi_sel,
            "n": len(punti_filtrati),
        }
elif st.session_state.get("filtro_usato", {}).get("n") != len(punti_filtrati):
    st.info("I filtri sono cambiati. Premi **Calcola / aggiorna dati** per ricalcolare.")

risultati = st.session_state.get("risultati", [])
if not risultati:
    st.stop()

# filtra i risultati già calcolati per ricerca/quota se l'utente non ha ricalcolato
risultati_view = [
    r for r in risultati
    if r["regione"] in regioni_sel
    and r["tipo"] in tipi_sel
    and quota_range[0] <= r["quota"] <= quota_range[1]
    and (cerca.lower() in r["nome"].lower() if cerca else True)
]

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
n_alto = sum(1 for r in risultati_view if r["score"] >= 70)
n_medio = sum(1 for r in risultati_view if 50 <= r["score"] < 70)
best = risultati_view[0] if risultati_view else None
kpi1.metric("Zone analizzate", len(risultati_view))
kpi2.metric("🟢 Alto", n_alto)
kpi3.metric("🟡 Medio", n_medio)
kpi4.metric("Top zona", f"{best['score']:.0f}" if best else "—", best["nome"] if best else "")

col1, col2 = st.columns([1.4, 1])

with col1:
    if risultati_view:
        lat_c = sum(r["lat"] for r in risultati_view) / len(risultati_view)
        lon_c = sum(r["lon"] for r in risultati_view) / len(risultati_view)
        m = folium.Map(location=[lat_c, lon_c], zoom_start=8)
        for r in risultati_view:
            color = (
                "green" if r["score"] >= 70
                else "orange" if r["score"] >= 50
                else "red" if r["score"] >= 30
                else "gray"
            )
            d = r.get("dettaglio", {})
            meteo = r.get("meteo", {}) or {}
            tot_staz = meteo.get("pioggia_stazione_30g")
            giorni_all = meteo.get("giorni_pluviometro") or []
            giorni_pioggia = []
            for g in giorni_all:
                try:
                    mm = float(str(g).rsplit(":", 1)[-1].replace("mm", "").strip())
                except Exception:
                    mm = 0
                if mm >= 0.2:
                    giorni_pioggia.append(g)
            if not giorni_pioggia:
                giorni_html = "nessun giorno ≥ 0,2 mm nei dati scaricati"
            else:
                giorni_html = "<br>".join(giorni_pioggia)
            tot_txt = f"{tot_staz} mm" if tot_staz is not None else f"{d.get('precip_totale_30g', 'n/d')} mm"
            popup_html = f"""
            <div style="max-height:200px;overflow:auto;font-size:12px;line-height:1.35;max-width:240px;">
            <b>{r['nome']}</b><br>
            Regione: {r['regione']}<br>
            Tipo: {r['tipo']}<br>
            Quota ~{r['quota']} m<br>
            Specie: {d.get('specie_testo', 'n/d')}<br>
            <b>Punteggio: {r['score']:.0f}/100</b><br>
            {r['livello']}<br>
            {d.get('consiglio', '')}<br>
            <b>Pioggia ultimo mese: {tot_txt}</b><br>
            T max: {d.get('t_max_media', 'n/d')} °C · T med: {d.get('t_med_media', 'n/d')} °C · T min: {d.get('t_min_media', 'n/d')} °C<br>
            Vento 10gg: max {d.get('vento_max_10g', 'n/d')} km/h · {d.get('nota_vento', '')}<br>
            Picco: {d.get('picco_max_data') or 'n/d'} {('('+str(d.get('picco_max_kmh'))+' km/h)') if d.get('picco_max_kmh') is not None else ''}<br>
            Giorni vento ≥20: {('<br>' + '<br>'.join(d.get('picchi_vento') or [])) if d.get('picchi_vento') else ' nessuno'}<br>
            Fonte: {meteo.get('fonte', 'n/d')}<br>
            Stazione: {meteo.get('stazione', 'n/d')}<br>
            <b>Giorni di pioggia:</b><br>{giorni_html}
            </div>
            """
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=8 + r["score"] / 12,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                tooltip=f"{r['nome']} · {r['score']:.0f}",
                popup=folium.Popup(popup_html, max_width=260),
            ).add_to(m)
        with st.expander("Mappa delle zone", expanded=True):
            st_folium(m, width=700, height=520, returned_objects=[])
        with st.expander("Radar Protezione Civile", expanded=False):
            st.markdown("[Apri radar.protezionecivile.it](https://radar.protezionecivile.it/)")
            st.components.v1.iframe("https://radar.protezionecivile.it/", height=420)
        with st.expander("Mappe giornaliere MeteoNetwork", expanded=False):
            st.markdown("[Apri mappe giornaliere MeteoNetwork](https://www.meteonetwork.eu/it/mappe-realtime)")
            st.components.v1.html(
                """
                <div style="width:100%;height:820px;overflow:auto;-webkit-overflow-scrolling:touch;border-radius:16px;">
                  <iframe src="https://www.meteonetwork.eu/it/mappe-realtime"
                    style="width:100%;height:1800px;border:0;"
                    scrolling="yes"></iframe>
                </div>
                """,
                height=840,
            )
    else:
        st.info("Nessuna zona da mostrare. Controlla i filtri in sidebar.")

with col2:
    st.subheader("Classifica zone")
    for r in risultati_view:
        with st.expander(f"{r['score']:.0f} • {r['nome']} ({r['regione']})", expanded=r["score"] >= 70):
            st.markdown(f"**{r['livello']}**")
            st.write(f"Tipo bosco: **{r['tipo']}** | Quota ~{r['quota']} m")
            d = r["dettaglio"]
            st.write(f"Specie attese: **{d.get('specie_testo', 'n/d')}**")
            st.info(d.get("consiglio", ""))
            st.write(f"• Pioggia ultimi 30 giorni: **{d.get('precip_totale_30g')} mm** ({d.get('giorni_con_pioggia')} giorni con pioggia)")
            st.write(f"• Pioggia ultimi 10 giorni: **{d.get('precip_10g')} mm**")
            st.write(f"• Temperatura max media: **{d.get('t_max_media')} °C**")
            st.write(f"• Temperatura min media: **{d.get('t_min_media')} °C**")
            st.write(f"• Giorni dalla buona pioggia: **{d.get('giorni_dalla_buona_pioggia')}** (attesa: {d.get('giorni_attesa_consigliati')} gg)")
            st.write(f"• Umidità suolo (7–28 cm): **{d.get('umidita_suolo')}**")
            st.write(
                f"• Vento 10 gg: media **{d.get('vento_medio_10g')} km/h**, "
                f"max **{d.get('vento_max_10g')} km/h** "
                f"({d.get('giorni_vento_20')} gg ≥20, {d.get('giorni_vento_30')} gg ≥30, "
                f"streak {d.get('giorni_vento_consecutivi')})"
            )
            st.write(f"• Fattore vento (1=ok, ~0=letto secco): **{d.get('fattore_vento')}** — {d.get('nota_vento')}")
            if d.get("picco_max_data"):
                st.write(f"• Picco vento: **{d.get('picco_max_kmh')} km/h** il **{d.get('picco_max_data')}**")
            picchi = d.get("picchi_vento") or []
            if picchi:
                st.write("• Giorni con vento ≥20 km/h:")
                for p in picchi:
                    st.write(f"  – {p}")
            meteo = r.get("meteo", {})
            dist = meteo.get("distanza_km")
            dist_txt = f" ({dist} km)" if dist is not None else ""
            st.write(f"• Fonte usata per il punteggio: **{meteo.get('fonte', 'n/d')}**")
            giorni_p = meteo.get("giorni_pluviometro") or []
            if giorni_p:
                st.write("• Mm veri già scaricati:")
                for g in giorni_p:
                    st.write(f"  – {g}")
            else:
                st.write("• Mm veri già scaricati: nessuno (ripremi Calcola, senza svuotare la cache)")
            if meteo.get("pioggia_modello_30g") is not None or meteo.get("pioggia_stazione_30g") is not None:
                st.write(
                    f"• Confronto 30 gg — modello sul bosco: **{meteo.get('pioggia_modello_30g')} mm** · "
                    f"stazione più vicina: **{meteo.get('pioggia_stazione_30g')} mm**"
                )
            qst = meteo.get("quota_stazione")
            qst_txt = f", quota stazione {int(qst)} m" if qst not in (None, "") else ""
            st.write(f"• Stazione: **{meteo.get('stazione', 'n/d')}**{dist_txt}{qst_txt}")
            st.progress(min(100, int(r["score"])) / 100)

st.markdown("---")
st.subheader("Mm di oggi dalle stazioni")
oggi_txt = datetime.now().strftime("%Y-%m-%d")
live_rows = []
visti_staz = set()
for r in risultati_view:
    meteo = r.get("meteo") or {}
    staz = meteo.get("stazione") or "n/d"
    if staz in visti_staz:
        continue
    visti_staz.add(staz)
    mm_oggi = None
    fonte = str(meteo.get("fonte") or "")
    m = re.search(r"oggi[^0-9]*([0-9]+(?:[.,][0-9]+)?)\s*mm", fonte, flags=re.I)
    if m:
        try:
            mm_oggi = float(m.group(1).replace(",", "."))
        except Exception:
            mm_oggi = None
    if mm_oggi is None:
        for g in meteo.get("giorni_pluviometro") or []:
            gs = str(g)
            if oggi_txt in gs or datetime.now().strftime("%d/%m") in gs:
                try:
                    mm_oggi = float(gs.rsplit(":", 1)[-1].replace("mm", "").strip().replace(",", "."))
                except Exception:
                    pass
    live_rows.append({
        "zona": r["nome"],
        "stazione": staz,
        "mm_oggi": mm_oggi if mm_oggi is not None else "n/d",
    })
if live_rows:
    st.markdown(_tabella_bosco(pd.DataFrame(live_rows)), unsafe_allow_html=True)
st.caption("Fonte radar: Dipartimento della Protezione Civile — radar.protezionecivile.it")

st.markdown("---")
st.subheader("🍄‍🟫 Tabella e export")
if risultati_view:
    tab = pd.DataFrame([{
        "zona": r["nome"],
        "regione": r["regione"],
        "tipo": r["tipo"],
        "quota_m": r["quota"],
        "score": round(r["score"], 1),
        "livello": r["livello"],
        "consiglio": r["dettaglio"].get("consiglio"),
        "pioggia_30g_mm": r["dettaglio"].get("precip_totale_30g"),
        "pioggia_10g_mm": r["dettaglio"].get("precip_10g"),
        "t_max": r["dettaglio"].get("t_max_media"),
        "t_min": r["dettaglio"].get("t_min_media"),
        "giorni_da_pioggia": r["dettaglio"].get("giorni_dalla_buona_pioggia"),
        "suolo": r["dettaglio"].get("umidita_suolo"),
        "vento_medio_kmh": r["dettaglio"].get("vento_medio_10g"),
        "gg_vento_20": r["dettaglio"].get("giorni_vento_20"),
        "gg_vento_30": r["dettaglio"].get("giorni_vento_30"),
        "fattore_vento": r["dettaglio"].get("fattore_vento"),
        "nota_vento": r["dettaglio"].get("nota_vento"),
        "fonte": r.get("meteo", {}).get("fonte"),
        "stazione": r.get("meteo", {}).get("stazione"),
    } for r in risultati_view])
    tab = tab.astype(str)
    vis = tab[["zona", "regione", "tipo", "quota_m", "score", "livello", "pioggia_30g_mm", "stazione"]].copy()
    st.markdown(_tabella_bosco(vis), unsafe_allow_html=True)
    st.download_button(
        "Scarica CSV",
        tab.to_csv(index=False).encode("utf-8"),
        file_name=f"porcini_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption(
    "Fonte: MeteoNetwork pubblico (stazioni + archivio). "
    "Rispetta i regolamenti regionali su tesserini, quantitativi e specie protette."
)
