"""
ui/app.py — AI Resume Screening System · Premium Streamlit UI
Dark enterprise theme · Glassmorphism cards · Inline-safe CSS
"""

# pyre-ignore[21]
import streamlit as st
# pyre-ignore[21]
import plotly.graph_objects as go
# pyre-ignore[21]
import requests

API_BASE = "http://127.0.0.1:8000"

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  :root {
    --bg-base:   #0b0f1a;
    --bg-card:   #111827;
    --bg-card2:  #1a2235;
    --border:    #1e2d45;
    --accent:    #3b82f6;
    --accent2:   #6366f1;
    --green:     #10b981;
    --amber:     #f59e0b;
    --red:       #ef4444;
    --text-pri:  #f1f5f9;
    --text-sec:  #94a3b8;
    --text-mute: #475569;
  }
  html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: var(--bg-base) !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    color: var(--text-pri) !important;
  }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1525 0%, #111827 100%) !important;
    border-right: 1px solid var(--border) !important;
  }
  [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
  [data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {
    color: var(--text-pri) !important;
    font-weight: 700 !important;
  }
  [data-testid="stSidebar"] .stRadio > div { gap: 4px !important; }
  [data-testid="stSidebar"] .stRadio label {
    font-size: 0.9rem !important;
    padding: 8px 12px !important;
    border-radius: 8px !important;
    border: 1px solid transparent !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
  }
  [data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(59,130,246,0.1) !important;
    border-color: rgba(59,130,246,0.3) !important;
  }
  [data-testid="stMain"] .block-container {
    padding: 2rem 2.5rem !important;
    max-width: 1400px !important;
  }
  .stButton > button {
    background: linear-gradient(135deg, #2563eb, #4f46e5) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1.4rem !important;
    letter-spacing: 0.01em !important;
    transition: opacity 0.2s, transform 0.1s !important;
    box-shadow: 0 4px 12px rgba(59,130,246,0.3) !important;
  }
  .stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
  }
  .stButton > button:active { transform: translateY(0) !important; }
  .stTextInput input, .stTextArea textarea, .stSelectbox select, div[data-baseweb="select"] {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-pri) !important;
  }
  div[data-baseweb="select"] * { color: var(--text-pri) !important; }
  div[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
  }
  div[data-testid="stExpander"] summary {
     color: var(--text-pri) !important;
     font-weight: 500 !important;
  }
  [data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 1rem !important;
  }
  [data-testid="stMetricLabel"] { color: var(--text-sec) !important; }
  [data-testid="stMetricValue"] { color: var(--text-pri) !important; }
  .stAlert { border-radius: 8px !important; }
  hr { border-color: var(--border) !important; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg-base); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  [data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 10px !important;
  }
  .stProgress > div > div { background: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs):
    try:
        r = getattr(requests, method)(f"{API_BASE}{path}", timeout=60, **kwargs)
        if r.status_code < 300:
            return r.json(), None
        return None, r.json().get("detail", f"HTTP {r.status_code}")
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API — run: `uvicorn app.api.main:app --reload`"
    except Exception as e:
        return None, str(e)


def score_color(score: float) -> str:
    if score >= 0.70: return "#10b981"
    if score >= 0.45: return "#f59e0b"
    return "#ef4444"


def score_label(score: float) -> str:
    if score >= 0.70: return "Strong Match"
    if score >= 0.45: return "Moderate Match"
    return "Weak Match"


def score_emoji(score: float) -> str:
    if score >= 0.70: return "🟢"
    if score >= 0.45: return "🟡"
    return "🔴"


def page_header(icon: str, title: str, subtitle: str):
    st.markdown(f"""
<div style="
  background: linear-gradient(135deg, #0f2240 0%, #1a1040 50%, #0a1628 100%);
  border: 1px solid #1e3a5f;
  border-left: 4px solid #3b82f6;
  border-radius: 12px;
  padding: 1.6rem 2rem;
  margin-bottom: 2rem;
  position: relative;
  overflow: hidden;
">
  <div style="
    position: absolute; right: -20px; top: -20px;
    width: 120px; height: 120px;
    background: radial-gradient(circle, rgba(59,130,246,0.15), transparent 70%);
    border-radius: 50%;
  "></div>
  <div style="font-size: 2rem; margin-bottom: 0.3rem;">{icon}</div>
  <h1 style="color:#f1f5f9; margin:0; font-size:1.7rem; font-weight:800;
             letter-spacing:-0.02em;">{title}</h1>
  <p style="color:#64748b; margin:0.3rem 0 0; font-size:0.9rem;">{subtitle}</p>
</div>
""", unsafe_allow_html=True)


def metric_card(value: str, label: str, color: str = "#3b82f6", icon: str = ""):
    st.markdown(f"""
<div style="
  background: linear-gradient(135deg, #111827, #1a2235);
  border: 1px solid #1e2d45;
  border-top: 3px solid {color};
  border-radius: 12px;
  padding: 1.2rem 1.5rem;
  text-align: center;
">
  <div style="font-size:1.8rem; margin-bottom:4px;">{icon}</div>
  <div style="font-size:2.2rem; font-weight:800; color:{color};
              line-height:1;">{value}</div>
  <div style="font-size:0.75rem; color:#64748b; text-transform:uppercase;
              letter-spacing:0.08em; margin-top:6px; font-weight:500;">{label}</div>
</div>
""", unsafe_allow_html=True)


def score_bar_html(score: float, label: str) -> str:
    pct = int(score * 100)
    color = score_color(score)
    return f"""<div style="margin-bottom:2px;">
<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
<span style="font-size:0.75rem; color:#94a3b8; font-weight:500;">{label}</span>
<span style="font-size:0.75rem; color:{color}; font-weight:700;">{pct}%</span>
</div>
<div style="background:#1e2d45; border-radius:6px; height:7px; overflow:hidden;">
<div style="background:linear-gradient(90deg,{color},{color}aa);
width:{pct}%; height:7px; border-radius:6px;
transition:width 0.6s ease;"></div>
</div>
</div>"""


def candidate_card(c: dict, show_bars: bool = True) -> str:
    rank      = c["rank"]
    name      = c.get("candidate_name", "—")
    total     = c["total_score"]
    bd        = c.get("score_breakdown", {})
    color     = score_color(total)
    lbl       = score_label(total)
    pct       = int(total * 100)
    rank_bg   = {1: "#f59e0b", 2: "#94a3b8", 3: "#cd7f32"}.get(rank, "#334155")

    bars = ""
    if show_bars:
        for key, lbl2 in [("skill_match","Skill"), ("experience_alignment","Experience"),
                          ("role_relevance","Role Fit")]:
            v = bd.get(key, 0)
            p = int(v * 100)
            c2 = score_color(v)
            bars += f"""<div style="margin-bottom:6px;">
<div style="display:flex;justify-content:space-between;margin-bottom:3px;">
<span style="font-size:0.72rem;color:#64748b;font-weight:500;">{lbl2}</span>
<span style="font-size:0.72rem;color:{c2};font-weight:700;">{p}%</span>
</div>
<div style="background:#0f172a;border-radius:4px;height:5px;overflow:hidden;">
<div style="background:linear-gradient(90deg,{c2},{c2}88);
width:{p}%;height:5px;border-radius:4px;"></div>
</div>
</div>"""

    return f"""<div style="
  background: linear-gradient(135deg, #111827 0%, #1a2235 100%);
  border: 1px solid #1e2d45;
  border-left: 4px solid {color};
  border-radius: 12px;
  padding: 1.2rem 1.5rem;
  margin-bottom: 10px;
  display: flex;
  align-items: flex-start;
  gap: 1.2rem;
  transition: transform 0.2s;
" onmouseover="this.style.transform='translateY(-2px)'"
   onmouseout="this.style.transform='translateY(0)'">
  <div style="
    background: {rank_bg};
    color: #fff;
    font-size: 0.85rem;
    font-weight: 800;
    min-width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  ">#{rank}</div>
  <div style="flex:1; min-width:0;">
    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:8px;">
      <span style="font-size:1rem; font-weight:700; color:#f1f5f9;">{name}</span>
      <span style="
        background: rgba(59,130,246,0.12);
        color: {color};
        border: 1px solid {color}44;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 20px;
        letter-spacing:0.03em;
      ">{score_emoji(total)} {lbl}</span>
      <span style="margin-left:auto; font-size:1.4rem; font-weight:800;
                   color:{color};">{pct}%</span>
    </div>
    {bars}
  </div>
</div>"""


def skill_tag(skill: str, matched: bool) -> str:
    if matched:
        bg, color, border = "rgba(16,185,129,0.1)", "#10b981", "rgba(16,185,129,0.3)"
        prefix = "✓"
    else:
        bg, color, border = "rgba(239,68,68,0.1)", "#ef4444", "rgba(239,68,68,0.3)"
        prefix = "✗"
    return (f'<span style="background:{bg};color:{color};border:1px solid {border};'
            f'padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;'
            f'display:inline-block;margin:3px;">{prefix} {skill}</span>')


def section_title(text: str):
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:1.5rem 0 1rem;">
  <div style="height:3px;width:24px;background:linear-gradient(90deg,#3b82f6,#6366f1);
              border-radius:2px;"></div>
  <span style="font-size:0.85rem;font-weight:700;color:#94a3b8;
               text-transform:uppercase;letter-spacing:0.1em;">{text}</span>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding: 1rem 0 1.5rem; text-align:center;">
<div style="font-size:2.5rem; margin-bottom:8px;">🎯</div>
<div style="font-size:1rem; font-weight:800; color:#f1f5f9;
            letter-spacing:-0.01em;">AI Resume Screener</div>
<div style="font-size:0.72rem; color:#475569; margin-top:4px;">
  Explainable · Bias-Aware · Local AI
</div>
</div>
""", unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["📥  Input", "📊  Results", "🔍  Explanations",
         "⚖️  Bias Insights", "💬  Feedback"],
        label_visibility="collapsed",
    )

    # pyre-ignore
    st.markdown("<div style='margin:1.5rem 0;border-top:1px solid #1e2d45;'></div>", unsafe_allow_html=True)

    health, _ = api("get", "/health")
    if health:
        st.markdown("""
<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);
            border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:8px;">
<div style="width:8px;height:8px;background:#10b981;border-radius:50%;
            box-shadow:0 0 6px #10b981;"></div>
<span style="color:#10b981;font-size:0.8rem;font-weight:600;">API Connected</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
            border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:8px;">
<div style="width:8px;height:8px;background:#ef4444;border-radius:50%;"></div>
<span style="color:#ef4444;font-size:0.8rem;font-weight:600;">API Offline</span>
</div>
<div style="font-size:0.72rem;color:#475569;margin-top:8px;line-height:1.5;">
Run: <code style="background:#1e2d45;padding:2px 6px;border-radius:4px;
color:#94a3b8;">uvicorn app.api.main:app --reload</code>
</div>
""", unsafe_allow_html=True)

    # Quick stats
    # pyre-ignore
    st.markdown("<div style='margin:1.2rem 0;border-top:1px solid #1e2d45;'></div>", unsafe_allow_html=True)
    resumes_data, _ = api("get", "/resumes/")
    jobs_data_s, _  = api("get", "/jobs/")
    n_r = resumes_data["total"] if resumes_data else 0
    n_j = jobs_data_s["total"] if jobs_data_s else 0
    st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
<div style="background:#111827;border:1px solid #1e2d45;border-radius:8px;
            padding:10px;text-align:center;">
<div style="font-size:1.4rem;font-weight:800;color:#3b82f6;">{n_r}</div>
<div style="font-size:0.68rem;color:#475569;text-transform:uppercase;
            letter-spacing:0.06em;margin-top:2px;">Resumes</div>
</div>
<div style="background:#111827;border:1px solid #1e2d45;border-radius:8px;
            padding:10px;text-align:center;">
<div style="font-size:1.4rem;font-weight:800;color:#6366f1;">{n_j}</div>
<div style="font-size:0.68rem;color:#475569;text-transform:uppercase;
            letter-spacing:0.06em;margin-top:2px;">Jobs</div>
</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — INPUT
# ─────────────────────────────────────────────────────────────────────────────
if page == "📥  Input":
    page_header("📥", "Data Input", "Upload resumes and create job descriptions to begin screening")

    col_r, col_j = st.columns([1, 1], gap="large")

    # ── Resume Upload ──────────────────────────────────────────────────────
    with col_r:
        st.markdown("""
<div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;
            padding:1.5rem;margin-bottom:1rem;">
<div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin-bottom:4px;">
  📄 Upload Resumes
</div>
<div style="font-size:0.8rem;color:#64748b;">
  Supports PDF, DOCX, and TXT formats
</div>
</div>
""", unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Drop resume files here",
            type=["pdf", "docx", "doc", "txt"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files:
            if st.button("⬆️  Upload All Resumes", use_container_width=True):
                ok: int = 0
                fail: int = 0
                prog = st.progress(0)
                status_box = st.empty()
                for i, f in enumerate(uploaded_files):
                    # pyre-ignore
                    status_box.markdown(
                        f'<div style="font-size:0.8rem;color:#94a3b8;">Processing {f.name}…</div>',
                        unsafe_allow_html=True
                    )
                    data, err = api("post", "/resumes/upload",
                        files={"file": (f.name, f.getvalue(),
                                        f.type or "application/octet-stream")})
                    if data:
                        # pyre-ignore
                        ok = ok + 1
                    else:
                        # pyre-ignore
                        fail = fail + 1
                        st.warning(f"❌ {f.name}: {err}")
                    prog.progress((i + 1) / len(uploaded_files))
                status_box.empty()
                if ok:
                    st.success(f"✅ {ok} resume(s) uploaded successfully!")
                if fail:
                    st.error(f"{fail} upload(s) failed.")

        section_title("Or paste resume text")
        with st.expander("✏️  Paste plain-text resume"):
            paste_name = st.text_input("Candidate Name", placeholder="e.g. Priya Sharma")
            paste_text = st.text_area("Resume Text",
                placeholder="Paste the full resume text here…", height=200)
            if st.button("Submit Text Resume", use_container_width=True):
                if paste_name and paste_text:
                    data, err = api("post", "/resumes/upload-text",
                        data={"name": paste_name, "raw_text": paste_text})
                    if data:
                        st.success(
                            f"✅ **{data['candidate_name']}** added — "
                            f"{data['skills_extracted']} skills · "
                            f"{data['total_years_experience']:.1f} YoE"
                        )
                    else:
                        st.error(err)
                else:
                    st.warning("Please enter both a name and resume text.")

    # ── Job Description ────────────────────────────────────────────────────
    with col_j:
        st.markdown("""
<div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;
            padding:1.5rem;margin-bottom:1rem;">
<div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin-bottom:4px;">
  🏢 Job Description
</div>
<div style="font-size:0.8rem;color:#64748b;">
  Include required skills, preferred skills, and experience expectations
</div>
</div>
""", unsafe_allow_html=True)

        jd_title = st.text_input("Job Title", placeholder="e.g. Senior ML Engineer")
        jd_text  = st.text_area("Job Description",
            placeholder=(
                "Required Skills:\n- Python\n- Machine Learning\n\n"
                "Nice to Have:\n- Docker\n- AWS\n\n"
                "Requirements:\nMinimum 5 years of experience."
            ), height=310)
        if st.button("➕  Add Job Description", use_container_width=True):
            if jd_title and jd_text and len(jd_text) >= 50:
                data, err = api("post", "/jobs/",
                    json={"title": jd_title, "description": jd_text})
                if data:
                    req = data.get("required_skills", [])
                    pref = data.get("preferred_skills", [])
                    st.success(f"✅ **{data['title']}** created (ID: {data['job_id']})")
                    st.markdown(f"""
<div style="background:#0f172a;border:1px solid #1e2d45;border-radius:8px;
            padding:1rem;margin-top:0.5rem;">
<div style="font-size:0.8rem;color:#64748b;margin-bottom:6px;
            font-weight:600;text-transform:uppercase;letter-spacing:.05em;">
Parsed Skills
</div>
<div style="margin-bottom:6px;">
<span style="font-size:0.72rem;color:#10b981;font-weight:600;">
Required ({len(req)}):
</span>
<span style="font-size:0.75rem;color:#94a3b8;"> {', '.join(req[:8]) or '—'}</span>
</div>
<div>
<span style="font-size:0.72rem;color:#f59e0b;font-weight:600;">
Preferred ({len(pref)}):
</span>
<span style="font-size:0.75rem;color:#94a3b8;"> {', '.join(pref[:8]) or '—'}</span>
</div>
</div>
""", unsafe_allow_html=True)
                else:
                    st.error(err)
            else:
                st.warning("Title required — description needs at least 50 characters.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — RESULTS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📊  Results":
    page_header("📊", "Ranked Candidates",
                "Multi-factor AI scoring — Skill Match · Experience Alignment · Role Relevance")

    jobs_data, err = api("get", "/jobs/")
    if err: st.error(err); st.stop()
    # pyre-ignore
    if not jobs_data["jobs"]:
        # pyre-ignore
        st.info("No jobs yet — go to **Input** and add a job description first.")
        # pyre-ignore
        st.stop()

    # pyre-ignore
    job_opts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs_data["jobs"]}

    ctrl_l, ctrl_r = st.columns([2, 1])
    with ctrl_l:
        selected = st.selectbox("Select Job", list(job_opts.keys()),
                                label_visibility="collapsed")
    job_id = job_opts[selected]
    with ctrl_r:
        run_btn = st.button("🚀  Run Ranking", use_container_width=True)

    if run_btn:
        with st.spinner("Computing skill, experience & semantic scores…"):
            data, err = api("post", f"/rank/{job_id}")
        if err: st.error(err); st.stop()
        # pyre-ignore
        st.session_state[f"rank_{job_id}"] = data

    if f"rank_{job_id}" not in st.session_state:
        saved, _ = api("get", f"/rank/{job_id}/results")
        # pyre-ignore
        if saved: st.session_state[f"rank_{job_id}"] = saved

    results = st.session_state.get(f"rank_{job_id}")
    if not results:
        st.markdown("""
<div style="background:#111827;border:1px dashed #1e2d45;border-radius:12px;
            padding:3rem;text-align:center;">
<div style="font-size:2.5rem;margin-bottom:12px;">🚀</div>
<div style="color:#64748b;font-size:0.9rem;">
Click <strong style="color:#f1f5f9;">Run Ranking</strong> to rank candidates
</div>
</div>
""", unsafe_allow_html=True)
        st.stop()

    candidates = results["ranked_candidates"]
    weights    = results.get("weights_used", {})

    # Summary row
    top_score = candidates[0]["total_score"] if candidates else 0
    # pyre-ignore
    st.html("<div style='height:12px'></div>")
    m1, m2, m3, m4 = st.columns(4)
    with m1: metric_card(str(len(candidates)), "Candidates Ranked", "#3b82f6", "👥")
    with m2: metric_card(f"{int(top_score*100)}%", "Top Score", "#10b981", "🏆")
    with m3: metric_card(f"{int(weights.get('skill_match',0.4)*100)}%",
                         "Skill Weight", "#6366f1", "⚡")
    with m4:
        strong = sum(1 for c in candidates if c["total_score"] >= 0.70)
        metric_card(str(strong), "Strong Matches", "#f59e0b", "✨")

    section_title(f"Ranked Results — {results.get('job_title','')}")

    for c in candidates:
        # pyre-ignore
        html = candidate_card(c, show_bars=True)
        st.markdown(html, unsafe_allow_html=True)

    # pyre-ignore
    st.markdown(
        f'<div style="font-size:0.72rem;color:#334155;margin-top:12px;">'
        f'Generated: {results.get("generated_at","—")[:19].replace("T"," ")} UTC'
        f'</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — EXPLANATIONS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔍  Explanations":
    page_header("🔍", "Candidate Explanations",
                "Human-readable reasoning for every ranking decision")

    jobs_data, _ = api("get", "/jobs/")
    if not jobs_data or not jobs_data["jobs"]:
        st.info("Add a job and run ranking first."); st.stop()

    # pyre-ignore
    job_opts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs_data["jobs"]}
    sel = st.selectbox("Select Job", list(job_opts.keys()), label_visibility="collapsed")
    job_id = job_opts[sel]

    results, err = api("get", f"/rank/{job_id}/results")
    if err or not results:
        st.info("No rankings yet — run ranking on the Results page first."); st.stop()

    # pyre-ignore
    candidates = results["ranked_candidates"]
    section_title(f"{len(candidates)} candidates · expand for details")

    for c in candidates:
        rank    = c["rank"]
        name    = c.get("candidate_name", "—")
        total   = c["total_score"]
        bd      = c.get("score_breakdown", {})
        matched = c.get("matched_skills", [])
        missing = c.get("missing_skills", [])
        # pyre-ignore
        expl    = c.get("explanation", "No explanation available.")
        color   = score_color(total)
        lbl     = score_label(total)

        with st.expander(f"#{rank}  {name}  ·  {score_emoji(total)} {lbl}  ·  {int(total*100)}%"):
            col_scores, col_skills = st.columns([1, 1.4], gap="large")

            with col_scores:
                # pyre-ignore
                st.markdown("""
<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;
            text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;">
  Score Breakdown
</div>
""", unsafe_allow_html=True)
                for metric, lbl2 in [
                    ("total", "Overall Score"),
                    ("skill_match", "Skill Match"),
                    ("experience_alignment", "Experience"),
                    ("role_relevance", "Role Relevance"),
                ]:
                    v = bd.get(metric, total if metric == "total" else 0)
                    st.markdown(score_bar_html(v, lbl2), unsafe_allow_html=True)

            with col_skills:
                if matched:
                    st.markdown("""
<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;
            text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">
  ✅ Matched Skills
</div>
""", unsafe_allow_html=True)
                    tags = " ".join(skill_tag(s, True) for s in matched)
                    # pyre-ignore
                    st.markdown(f'<div style="line-height:2;">{tags}</div>', unsafe_allow_html=True)

                if missing:
                    st.markdown("""
<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;
            text-transform:uppercase;letter-spacing:.08em;
            margin-top:12px;margin-bottom:8px;">
  ❌ Missing Skills
</div>
""", unsafe_allow_html=True)
                    tags = " ".join(skill_tag(s, False) for s in missing)
                    # pyre-ignore
                    st.markdown(f'<div style="line-height:2;">{tags}</div>', unsafe_allow_html=True)

            st.markdown("""
<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;
            text-transform:uppercase;letter-spacing:.08em;
            margin-top:16px;margin-bottom:8px;">
  💬 AI Explanation
</div>
""", unsafe_allow_html=True)
            st.markdown(f"""
<div style="
  background:#0a1628;
  border:1px solid #1e2d45;
  border-left:4px solid #3b82f6;
  border-radius:8px;
  padding:1rem 1.2rem;
  font-size:0.875rem;
  color:#cbd5e1;
  line-height:1.7;
">{expl}</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 — BIAS INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⚖️  Bias Insights":
    page_header("⚖️", "Bias & Fairness Insights",
                "Statistical signals that may indicate unfair ranking patterns")

    jobs_data, _ = api("get", "/jobs/")
    if not jobs_data or not jobs_data["jobs"]:
        st.info("Add a job and run ranking first."); st.stop()

    # pyre-ignore
    job_opts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs_data["jobs"]}
    sel = st.selectbox("Select Job", list(job_opts.keys()), label_visibility="collapsed")
    job_id = job_opts[sel]

    if st.button("🔍  Analyze Bias", use_container_width=False):
        with st.spinner("Running statistical analysis…"):
            report, err = api("get", f"/bias/{job_id}")
        if err: st.error(err); st.stop()
        st.session_state[f"bias_{job_id}"] = report

    report = st.session_state.get(f"bias_{job_id}")
    if not report:
        st.markdown("""
<div style="background:#111827;border:1px dashed #1e2d45;border-radius:12px;
            padding:3rem;text-align:center;">
<div style="font-size:2.5rem;margin-bottom:12px;">⚖️</div>
<div style="color:#64748b;font-size:0.9rem;">
Click <strong style="color:#f1f5f9;">Analyze Bias</strong> to check for fairness signals
</div>
</div>
""", unsafe_allow_html=True)
        st.stop()

    # ── Metric cards ──────────────────────────────────────────────────────
    section_title("Fairness Metrics")
    b1, b2, b3 = st.columns(3)
    skew = report.get("experience_skew_score", 0)
    kw   = report.get("keyword_overfit_score", 0)
    n_s  = len(report.get("bias_signals", []))

    def bias_color(v, lo=0.45, hi=0.7):
        return "#ef4444" if v >= hi else "#f59e0b" if v >= lo else "#10b981"

    with b1: metric_card(f"{skew:.2f}", "Experience Skew", bias_color(skew), "📈")
    with b2: metric_card(f"{kw:.2f}",   "Keyword Overfit", bias_color(kw, 0.5, 0.75), "🔑")
    with b3: metric_card(str(n_s), "Bias Signals", bias_color(n_s, 1, 2), "🚩")

    # ── Factor dominance chart ────────────────────────────────────────────
    fd = report.get("factor_dominance", [])
    if fd:
        section_title("Factor Dominance")
        try:
            # pyre-ignore[21]
            import plotly.graph_objects as go
            factors  = [f["factor_name"].replace("_", " ").title() for f in fd]
            contribs = [f["average_contribution"] for f in fd]
            fig = go.Figure(go.Bar(
                x=factors, y=contribs,
                marker={"color": ["#3b82f6", "#10b981", "#f59e0b"], "line": {"color": "rgba(0,0,0,0)", "width": 0}},
                text=[f"{v:.3f}" for v in contribs],
                textposition="outside",
                textfont={"color": "#94a3b8", "size": 12},
            ))
            fig.update_layout(
                paper_bgcolor="#0b0f1a",
                plot_bgcolor="#111827",
                font={"color": "#94a3b8", "family": "Inter"},
                yaxis={"gridcolor": "#1e2d45", "color": "#475569", "zeroline": False},
                xaxis={"color": "#94a3b8"},
                margin={"t": 30, "b": 20, "l": 20, "r": 20},
                showlegend=False,
                height=260,
                bargap=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.info("plotly not installed — run: pip install plotly")

    # ── Bias signals ──────────────────────────────────────────────────────
    section_title("Bias Signals Detected")
    signals = report.get("bias_signals", [])
    if not signals:
        st.markdown("""
<div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);
            border-radius:10px;padding:1.2rem 1.5rem;display:flex;
            align-items:center;gap:12px;">
<div style="font-size:1.5rem;">✅</div>
<div>
<div style="color:#10b981;font-weight:600;font-size:0.9rem;">No Bias Signals Detected</div>
<div style="color:#475569;font-size:0.8rem;margin-top:2px;">
  No statistically significant bias patterns found in this ranking.
</div>
</div>
</div>
""", unsafe_allow_html=True)
    else:
        sev_color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"}
        for sig in signals:
            sev  = sig.get("severity", "low")
            col  = sev_color.get(sev, "#94a3b8")
            st.markdown(f"""
<div style="background:#111827;border:1px solid {col}33;
            border-left:4px solid {col};border-radius:10px;
            padding:1rem 1.2rem;margin-bottom:8px;">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
<span style="background:{col}22;color:{col};border:1px solid {col}44;
             font-size:0.7rem;font-weight:700;padding:2px 8px;
             border-radius:20px;text-transform:uppercase;
             letter-spacing:.05em;">{sev}</span>
<span style="color:#f1f5f9;font-weight:600;font-size:0.9rem;">
  {sig.get("signal_type","").replace("_"," ").title()}
</span>
</div>
<div style="color:#94a3b8;font-size:0.85rem;line-height:1.6;">
{sig.get("description","")}
</div>
</div>
""", unsafe_allow_html=True)

    # ── Disclaimer ───────────────────────────────────────────────────────
    section_title("Ethical Disclaimer")
    st.markdown(f"""
<div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.2);
            border-radius:10px;padding:1.2rem 1.5rem;">
<div style="color:#f59e0b;font-size:0.8rem;line-height:1.7;">
⚠️ {report.get("ethical_disclaimer","")}
</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 — FEEDBACK
# ─────────────────────────────────────────────────────────────────────────────
elif page == "💬  Feedback":
    page_header("💬", "Recruiter Feedback",
                "Accept or reject candidates — drives adaptive weight learning")

    jobs_data, _ = api("get", "/jobs/")
    if not jobs_data or not jobs_data["jobs"]:
        st.info("Add a job and run ranking first."); st.stop()

    # pyre-ignore
    job_opts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs_data["jobs"]}
    sel = st.selectbox("Select Job", list(job_opts.keys()), label_visibility="collapsed")
    job_id = job_opts[sel]

    results, err = api("get", f"/rank/{job_id}/results")
    if err or not results:
        st.info("Run ranking first."); st.stop()

    # pyre-ignore
    candidates = results["ranked_candidates"]

    # Stats row
    stats, _ = api("get", "/feedback/stats")
    if stats:
        section_title("Feedback Statistics")
        s1, s2, s3, s4 = st.columns(4)
        total_fb = stats.get("total_feedback", 0)
        acc      = stats.get("accept_count", 0)
        rej      = stats.get("reject_count", 0)
        acc_rate = f"{int(acc/total_fb*100)}%" if total_fb else "—"
        with s1: metric_card(str(total_fb), "Total Feedback", "#3b82f6", "📊")
        with s2: metric_card(str(acc), "Accepted", "#10b981", "✅")
        with s3: metric_card(str(rej), "Rejected", "#ef4444", "❌")
        with s4: metric_card(acc_rate, "Accept Rate", "#6366f1", "📈")

    section_title("Submit Feedback")

    for c in candidates:
        rid   = c.get("ranking_id")
        if not rid: continue
        name  = c.get("candidate_name", "—")
        rank  = c["rank"]
        total = c["total_score"]
        color = score_color(total)

        st.markdown(f"""
<div style="background:#111827;border:1px solid #1e2d45;border-radius:10px;
            padding:1rem 1.4rem;margin-bottom:4px;display:flex;
            align-items:center;gap:12px;">
<div style="background:#1e2d45;color:#94a3b8;font-size:0.75rem;
              font-weight:700;min-width:32px;height:32px;border-radius:50%;
              display:flex;align-items:center;justify-content:center;">
    #{rank}
</div>
<div style="flex:1;">
    <span style="color:#f1f5f9;font-weight:600;font-size:0.9rem;">{name}</span>
</div>
<div style="color:{color};font-size:0.85rem;font-weight:700;">
    {int(total*100)}%
</div>
</div>
""", unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns([1, 2, 1])
        with fc1:
            decision = st.radio("", ["accept", "reject"],
                                key=f"d_{rid}", horizontal=True,
                                label_visibility="collapsed")
        with fc2:
            notes = st.text_input("", key=f"n_{rid}",
                                  placeholder="Optional notes…",
                                  label_visibility="collapsed")
        with fc3:
            if st.button("Submit", key=f"s_{rid}", use_container_width=True):
                resp, err = api("post", "/feedback/",
                    json={"ranking_id": rid, "decision": decision, "notes": notes})
                if resp:
                    msg = f"✅ **{name}** — {decision}"
                    if resp.get("weight_adjustment_triggered"):
                        msg += f"  🔄 Weights updated!"
                    st.success(msg)
                else:
                    st.error(err)

        # pyre-ignore
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
