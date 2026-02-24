
"""
ui/design_system.py — Finalized Design System for Resume Screening UI v3.
CRITICAL: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER CONSENT.
This file contains the hardcoded "Gold Standard" UI/UX tokens, colors, and global CSS.
"""

import streamlit as st

# ── Color Palette (Enterprise v3 Gold Standard) ──────────────────────────────────
# Background & Surface
BG       = "#F0F2F7"
SURFACE  = "#FFFFFF"
BORDER   = "#E2E6F0"

# Primary Brand (Blue)
BLUE     = "#2F5BEA"
BLUE_DK  = "#1E46C7"
BLUE_LT  = "#EEF2FD"
BLUE_BD  = "#CCDAFC"

# Status Colors
GREEN    = "#0F7B55"
GREEN_LT = "#E8F7F2"
GREEN_BD = "#A7DCC9"

AMBER    = "#92610A"
AMBER_LT = "#FEF9EC"
AMBER_BD = "#E8CE87"

RED      = "#B22B2B"
RED_LT   = "#FDF0F0"
RED_BD   = "#F0BDBD"

# Text Colors
T1       = "#0E1726"
T2       = "#374151"
T3       = "#6B7280"
T4       = "#9CA3AF"

def inject_custom_css():
    """
    Injects the finalized Enterprise v3 CSS into the Streamlit app.
    Locks in font (Inter), spacing, animations, and component styling.
    """
    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

*{{box-sizing:border-box;}}

/* Global Background & Font */
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{{
  background:{BG}!important;
  font-family:'Inter',system-ui,sans-serif!important;
  color:{T2}!important;
}}

/* Container Spacing */
[data-testid="stMain"] .block-container{{
  padding:1.5rem 2.25rem!important;
  max-width:1500px!important;
}}

/* Remove Streamlit Default Header/Gap */
header[data-testid="stHeader"], [data-testid="stHeader"], [data-testid="stAppHeader"] {{
  display: none !important;
  height: 0px !important;
}}

/* Sidebar Polishing */
[data-testid="stSidebarContent"]{{padding-top:0px!important;}}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{{padding-top:0px!important;}}
[data-testid="stSidebar"] *{{font-family:'Inter',sans-serif!important;}}
[data-testid="stSidebar"] .stRadio>div{{gap:2px!important;}}

/* Styled Sidebar Navigation Buttons */
[data-testid="stSidebar"] .stRadio label{{
  font-size:.875rem!important;font-weight:500!important;
  color:{T2}!important;padding:9px 14px!important;
  border-radius:8px!important;border:1px solid transparent!important;
  transition:all .18s!important;cursor:pointer!important;width:100%!important;
}}
[data-testid="stSidebar"] .stRadio label:hover{{
  background:{BLUE_LT}!important;color:{BLUE}!important;border-color:{BLUE_BD}!important;
}}

/* Primary Buttons */
.stButton>button{{
  background:{BLUE}!important;color:#fff!important;
  border:none!important;border-radius:8px!important;
  font-weight:600!important;font-size:.8125rem!important;
  padding:.5rem 1.1rem!important;min-height:38px!important;
  white-space:nowrap!important;transition:all .18s!important;
  box-shadow:0 2px 10px rgba(47,91,234,.28)!important;
}}
.stButton>button:hover{{
  background:{BLUE_DK}!important;transform:translateY(-1px)!important;
  box-shadow:0 4px 18px rgba(47,91,234,.38)!important;
}}
.stButton>button:active{{transform:translateY(0)!important;}}

/* Download Buttons (Ghost style) */
[data-testid="stDownloadButton"]>button{{
  background:{SURFACE}!important;color:{BLUE}!important;
  border:1.5px solid {BLUE}!important;border-radius:8px!important;
  font-weight:600!important;font-size:.8125rem!important;
  padding:.5rem 1.1rem!important;min-height:38px!important;
  white-space:nowrap!important;transition:all .18s!important;
}}
[data-testid="stDownloadButton"]>button:hover{{background:{BLUE_LT}!important;}}

/* Inputs (Text, TextArea) */
.stTextInput input,.stTextArea textarea{{
  background:{SURFACE}!important;border:1.5px solid {BORDER}!important;
  border-radius:8px!important;color:{T1}!important;
  font-family:'Inter',sans-serif!important;font-size:.875rem!important;
  transition:border-color .18s,box-shadow .18s!important;
}}
.stTextInput input:focus,.stTextArea textarea:focus{{
  border-color:{BLUE}!important;box-shadow:0 0 0 3px rgba(47,91,234,.12)!important;
}}

/* Dashboard Cards (Expander, Cards) */
div[data-baseweb="select"]{{
  background:{SURFACE}!important;border:1.5px solid {BORDER}!important;
  border-radius:8px!important;
}}
div[data-baseweb="select"] *{{color:{T1}!important;}}

div[data-testid="stExpander"]{{
  background:{SURFACE}!important;border:1px solid {BORDER}!important;
  border-radius:8px!important;margin-bottom:8px!important;
  box-shadow:0 1px 8px rgba(0,0,0,.06)!important;
  transition:box-shadow .18s!important;
}}
div[data-testid="stExpander"]:hover{{box-shadow:0 4px 20px rgba(0,0,0,.10)!important;}}
div[data-testid="stExpander"] summary{{
  color:{T1}!important;font-weight:600!important;font-size:.875rem!important;
}}

/* File Uploader Customization */
[data-testid="stFileUploader"]{{
  background:{SURFACE}!important;border:2px dashed {BORDER}!important;
  border-radius:8px!important;
}}

/* Progress Bar Color */
.stProgress>div>div{{background:{BLUE}!important;}}

/* Dashboard Metrics */
[data-testid="stMetric"]{{
  background:{SURFACE}!important;border:1px solid {BORDER}!important;
  border-radius:8px!important;padding:1rem!important;
}}

/* Alert/Notify Styling */
.stAlert{{border-radius:8px!important;font-size:.875rem!important;}}

/* Horizontal Dividers */
hr{{border-color:{BORDER}!important;}}

/* Scrollbar Customization */
::-webkit-scrollbar{{width:5px;height:5px;}}
::-webkit-scrollbar-track{{background:{BG};}}
::-webkit-scrollbar-thumb{{background:#CBD2DC;border-radius:3px;}}

/* Hide Main Menu/Footer Completely */
#MainMenu,footer,header{{visibility:hidden!important;}}

/* Animations */
@keyframes fadeIn{{from{{opacity:0;}}to{{opacity:1;}}}}
.fade{{animation:fadeIn .3s ease both;}}
</style>
    """
    st.markdown(css, unsafe_allow_html=True)
