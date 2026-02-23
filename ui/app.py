"""ui/app.py — Resume Screening · Polished Enterprise UI v3"""
# pyre-ignore[21]
import streamlit as st
# pyre-ignore[21]
import plotly.graph_objects as go
# pyre-ignore[21]
import requests

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Resume Screening", layout="wide",
                   initial_sidebar_state="expanded")

# ── Palette (hardcoded for inline use) ───────────────────────────────────────
BG       = "#F0F2F7"
SURFACE  = "#FFFFFF"
BORDER   = "#E2E6F0"
BLUE     = "#2F5BEA"
BLUE_DK  = "#1E46C7"
BLUE_LT  = "#EEF2FD"
BLUE_BD  = "#CCDAFC"
GREEN    = "#0F7B55"
GREEN_LT = "#E8F7F2"
GREEN_BD = "#A7DCC9"
AMBER    = "#92610A"
AMBER_LT = "#FEF9EC"
AMBER_BD = "#E8CE87"
RED      = "#B22B2B"
RED_LT   = "#FDF0F0"
RED_BD   = "#F0BDBD"
T1       = "#0E1726"
T2       = "#374151"
T3       = "#6B7280"
T4       = "#9CA3AF"

def scolor(s):
    if s >= .70: return GREEN, GREEN_LT, GREEN_BD
    if s >= .45: return AMBER, AMBER_LT, AMBER_BD
    return RED, RED_LT, RED_BD

def slabel(s):
    if s >= .70: return "Strong"
    if s >= .45: return "Moderate"
    return "Weak"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{{box-sizing:border-box;}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{{
  background:{BG}!important;
  font-family:'Inter',system-ui,sans-serif!important;
  color:{T2}!important;
}}
[data-testid="stMain"] .block-container{{
  padding:1.75rem 2.25rem!important;max-width:1500px!important;
}}
[data-testid="stSidebar"]{{
  background:{SURFACE}!important;
  border-right:1px solid {BORDER}!important;
  box-shadow:2px 0 20px rgba(0,0,0,.05)!important;
}}
[data-testid="stSidebar"] *{{font-family:'Inter',sans-serif!important;}}
[data-testid="stSidebar"] .stRadio>div{{gap:2px!important;}}
[data-testid="stSidebar"] .stRadio label{{
  font-size:.875rem!important;font-weight:500!important;
  color:{T2}!important;padding:9px 14px!important;
  border-radius:8px!important;border:1px solid transparent!important;
  transition:all .18s!important;cursor:pointer!important;width:100%!important;
}}
[data-testid="stSidebar"] .stRadio label:hover{{
  background:{BLUE_LT}!important;color:{BLUE}!important;border-color:{BLUE_BD}!important;
}}
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
[data-testid="stDownloadButton"]>button{{
  background:{SURFACE}!important;color:{BLUE}!important;
  border:1.5px solid {BLUE}!important;border-radius:8px!important;
  font-weight:600!important;font-size:.8125rem!important;
  padding:.5rem 1.1rem!important;min-height:38px!important;
  white-space:nowrap!important;transition:all .18s!important;
}}
[data-testid="stDownloadButton"]>button:hover{{background:{BLUE_LT}!important;}}
.stTextInput input,.stTextArea textarea{{
  background:{SURFACE}!important;border:1.5px solid {BORDER}!important;
  border-radius:8px!important;color:{T1}!important;
  font-family:'Inter',sans-serif!important;font-size:.875rem!important;
  transition:border-color .18s,box-shadow .18s!important;
}}
.stTextInput input:focus,.stTextArea textarea:focus{{
  border-color:{BLUE}!important;box-shadow:0 0 0 3px rgba(47,91,234,.12)!important;
}}
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
[data-testid="stFileUploader"]{{
  background:{SURFACE}!important;border:2px dashed {BORDER}!important;
  border-radius:8px!important;
}}
.stProgress>div>div{{background:{BLUE}!important;}}
[data-testid="stMetric"]{{
  background:{SURFACE}!important;border:1px solid {BORDER}!important;
  border-radius:8px!important;padding:1rem!important;
}}
.stAlert{{border-radius:8px!important;font-size:.875rem!important;}}
hr{{border-color:{BORDER}!important;}}
::-webkit-scrollbar{{width:5px;height:5px;}}
::-webkit-scrollbar-track{{background:{BG};}}
::-webkit-scrollbar-thumb{{background:#CBD2DC;border-radius:3px;}}
#MainMenu,footer,header{{visibility:hidden!important;}}
@keyframes fadeIn{{from{{opacity:0;}}to{{opacity:1;}}}}
.fade{{animation:fadeIn .3s ease both;}}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def api(method, path, **kw):
    try:
        r = getattr(requests, method)(f"{API_BASE}{path}", timeout=60, **kw)
        return (r.json(), None) if r.status_code < 300 else (None, r.json().get("detail", f"HTTP {r.status_code}"))
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API."
    except Exception as e:
        return None, str(e)

def sec(txt):
    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{T3};text-transform:uppercase;letter-spacing:.09em;padding-bottom:.5rem;border-bottom:1px solid {BORDER};margin:1.4rem 0 .85rem;">{txt}</div>', unsafe_allow_html=True)

def pg(title, sub=""):
    st.markdown(f'<div style="margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid {BORDER};"><h1 style="font-size:1.5rem;font-weight:800;color:{T1};letter-spacing:-.02em;margin-bottom:3px;">{title}</h1><p style="font-size:.8125rem;color:{T3};">{sub}</p></div>', unsafe_allow_html=True)

def stat_box(val, lbl, c=BLUE):
    st.markdown(f'<div style="background:{SURFACE};border:1px solid {BORDER};border-top:3px solid {c};border-radius:8px;padding:.9rem 1.1rem;text-align:center;box-shadow:0 1px 8px rgba(0,0,0,.06);"><div style="font-size:1.6rem;font-weight:800;color:{c};line-height:1;">{val}</div><div style="font-size:.68rem;font-weight:600;color:{T3};text-transform:uppercase;letter-spacing:.08em;margin-top:5px;">{lbl}</div></div>', unsafe_allow_html=True)

def pbar(pct, col):
    return f'<div style="background:#E4E8F2;border-radius:4px;height:5px;overflow:hidden;margin-top:4px;"><div style="background:{col};width:{pct}%;height:5px;border-radius:4px;"></div></div>'

def skill_chip(s, fg, bg, bd):
    return f'<span style="background:{bg};color:{fg};border:1px solid {bd};font-size:.72rem;font-weight:500;padding:2px 9px;border-radius:20px;display:inline-block;margin:2px;">{s}</span>'

def badge(lbl, fg, bg, bd):
    return f'<span style="background:{bg};color:{fg};border:1px solid {bd};font-size:.68rem;font-weight:700;padding:3px 10px;border-radius:20px;white-space:nowrap;">{lbl}</span>'

def info_card(content):
    st.markdown(f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:1.25rem 1.5rem;box-shadow:0 1px 8px rgba(0,0,0,.06);">{content}</div>', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div style="padding:1.5rem 1rem 1.25rem;border-bottom:1px solid {BORDER};margin-bottom:.75rem;"><div style="font-size:1.0625rem;font-weight:800;color:{T1};letter-spacing:-.02em;">Resume Screening</div><div style="font-size:.72rem;color:{T4};margin-top:3px;font-weight:500;">AI-Assisted Candidate Review</div></div>', unsafe_allow_html=True)

    page = st.radio("nav", ["Input","Results","Explanations","Fairness Audit","Feedback"], label_visibility="collapsed")

    st.markdown(f'<div style="margin:1rem 0;border-top:1px solid {BORDER};"></div>', unsafe_allow_html=True)

    health, _ = api("get", "/health")
    if health:
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:{GREEN_LT};border:1px solid {GREEN_BD};border-radius:8px;"><div style="width:7px;height:7px;background:{GREEN};border-radius:50%;flex-shrink:0;"></div><span style="font-size:.8rem;font-weight:600;color:{GREEN};">API Connected</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:{RED_LT};border:1px solid {RED_BD};border-radius:8px;"><div style="width:7px;height:7px;background:{RED};border-radius:50%;flex-shrink:0;"></div><span style="font-size:.8rem;font-weight:600;color:{RED};">API Offline</span></div>', unsafe_allow_html=True)

    st.markdown(f'<div style="margin:.75rem 0;border-top:1px solid {BORDER};"></div>', unsafe_allow_html=True)

    rd, _ = api("get", "/resumes/")
    jd_s, _ = api("get", "/jobs/")
    nr = rd["total"] if rd else 0
    nj = jd_s["total"] if jd_s else 0

    # Two stat pills — inline, no transforms/absolute positioning
    st.markdown(f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:.75rem;"><div style="background:{BLUE_LT};border:1px solid {BLUE_BD};border-radius:8px;padding:12px;text-align:center;"><div style="font-size:1.4rem;font-weight:800;color:{BLUE};">{nr}</div><div style="font-size:.65rem;color:{T3};text-transform:uppercase;letter-spacing:.07em;margin-top:3px;">Resumes</div></div><div style="background:{BLUE_LT};border:1px solid {BLUE_BD};border-radius:8px;padding:12px;text-align:center;"><div style="font-size:1.4rem;font-weight:800;color:{BLUE};">{nj}</div><div style="font-size:.65rem;color:{T3};text-transform:uppercase;letter-spacing:.07em;margin-top:3px;">Jobs</div></div></div><div style="font-size:.7rem;color:{T4};line-height:1.6;padding:0 2px;border-top:1px solid {BORDER};padding-top:.75rem;">Final decisions rest with the recruiter. Scores are assistive only.</div>', unsafe_allow_html=True)


# ── PAGE 1: INPUT ─────────────────────────────────────────────────────────────
if page == "Input":
    pg("Data Input", "Upload candidate resumes and define the job description.")
    col_r, col_j = st.columns([1,1], gap="large")

    with col_r:
        info_card(f'<div style="font-size:.9375rem;font-weight:700;color:{T1};margin-bottom:2px;">Resume Upload</div><div style="font-size:.8rem;color:{T3};">PDF, DOCX, or TXT · Multiple files supported</div>')
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        uploaded = st.file_uploader("Drop files here", type=["pdf","docx","doc","txt"],
                        accept_multiple_files=True, label_visibility="collapsed")
        ok: int = 0
        fail: int = 0
        if uploaded:
            if st.button("Upload Resumes", use_container_width=True):
                prog = st.progress(0); status = st.empty()
                for i, f in enumerate(uploaded):
                    status.caption(f"Processing {f.name}…")
                    d, e = api("post", "/resumes/upload",
                        files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")})
                    if d: ok = ok + 1   # type: ignore
                    else:
                        fail = fail + 1  # type: ignore
                        st.warning(f"{f.name}: {e}")
                    prog.progress((i+1)/len(uploaded))
                status.empty()
                if ok: st.success(f"{ok} resume(s) uploaded.")
                if fail: st.error(f"{fail} failed.")

        sec("Paste plain-text resume")
        with st.expander("Enter resume manually"):
            pn = st.text_input("Candidate name", placeholder="Full name")
            pt = st.text_area("Resume text", placeholder="Paste full resume content here…", height=180)
            if st.button("Submit Resume", use_container_width=True):
                if pn and pt:
                    d, e = api("post", "/resumes/upload-text", data={"name": pn, "raw_text": pt})
                    if d: st.success(f"{d['candidate_name']} — {d['skills_extracted']} skills · {d['total_years_experience']:.1f} yrs")
                    else: st.error(e)
                else: st.warning("Name and text required.")

        sec("Stored Resumes")
        rl, _ = api("get", "/resumes/")
        if rl and rl["resumes"]:
            for r in rl["resumes"][:10]:
                with st.expander(r["name"]):
                    st.markdown(f'<div style="font-size:.8rem;color:{T3};margin-bottom:10px;"><b style="color:{T2};">File:</b> {r["file_name"]}<br><b style="color:{T2};">Added:</b> {r["created_at"][:16].replace("T"," ")}</div>', unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("View Text", key=f"v_{r['id']}", use_container_width=True):  # type: ignore
                            det, _ = api("get", f"/resumes/{r['id']}")  # type: ignore
                            if det: st.markdown(f'<pre style="background:{BG};border:1px solid {BORDER};border-radius:8px;padding:12px;font-size:.78rem;color:{T2};max-height:220px;overflow-y:auto;white-space:pre-wrap;margin-top:8px;">{det.get("raw_text","")}</pre>', unsafe_allow_html=True)
                    with b2:
                        if st.button("Download PDF", key=f"d_{r['id']}", use_container_width=True):  # type: ignore
                            import requests as _r  # type: ignore
                            with st.spinner("Generating…"):
                                pr = _r.get(f"{API_BASE}/resumes/{r['id']}/pdf", timeout=30)
                            if pr.status_code == 200:
                                st.download_button("Save PDF", pr.content, f"{r['name'].replace(' ','_')}.pdf", "application/pdf", key=f"ds_{r['id']}", use_container_width=True)
                            else: st.error("PDF failed.")
        else:
            st.caption("No resumes uploaded yet.")

    with col_j:
        info_card(f'<div style="font-size:.9375rem;font-weight:700;color:{T1};margin-bottom:2px;">Job Description</div><div style="font-size:.8rem;color:{T3};">Required skills, qualifications, and experience expectations.</div>')
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        jt = st.text_input("Job title", placeholder="e.g. Senior Software Engineer")
        jx = st.text_area("Job description", placeholder="Required:\n- Python, FastAPI\n- 5+ years\n\nPreferred:\n- Docker, AWS", height=300)
        if st.button("Save Job Description", use_container_width=True):
            if jt and jx and len(jx) >= 50:
                d, e = api("post", "/jobs/", json={"title": jt, "description": jx})
                if d:
                    req = d.get("required_skills", [])
                    pref = d.get("preferred_skills", [])
                    st.success(f"Saved: {d['title']} (ID {d['job_id']})")
                    st.markdown(f'<div style="background:{BG};border:1px solid {BORDER};border-radius:8px;padding:.9rem 1rem;margin-top:.5rem;"><div style="font-size:.7rem;font-weight:700;color:{T3};text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px;">Parsed Skills</div><div style="margin-bottom:4px;"><span style="font-size:.75rem;color:{GREEN};font-weight:600;">Required ({len(req)}):</span> <span style="font-size:.78rem;color:{T2};">{", ".join(req[:10]) or "—"}</span></div><div><span style="font-size:.75rem;color:{AMBER};font-weight:600;">Preferred ({len(pref)}):</span> <span style="font-size:.78rem;color:{T2};">{", ".join(pref[:10]) or "—"}</span></div></div>', unsafe_allow_html=True)
                else: st.error(e)
            else: st.warning("Title required; description needs 50+ characters.")


# ── PAGE 2: RESULTS ───────────────────────────────────────────────────────────
elif page == "Results":
    pg("Ranked Candidates", "Assistive scoring only — final decisions remain with the recruiter.")

    jobs, err = api("get", "/jobs/")
    if err: st.error(err); st.stop()
    if not jobs["jobs"]:  # type: ignore
        st.info("No jobs found — add a job description first."); st.stop()

    jopts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs["jobs"]}  # type: ignore
    c1, c2 = st.columns([3,1])
    with c1: sel = st.selectbox("Job", list(jopts.keys()), label_visibility="collapsed")
    job_id = jopts[sel]
    with c2:
        if st.button("Run Scoring", use_container_width=True):
            with st.spinner("Computing scores…"):
                d, e = api("post", f"/rank/{job_id}")
            if e: st.error(e); st.stop()
            st.session_state[f"rank_{job_id}"] = d

    if f"rank_{job_id}" not in st.session_state:
        sv, _ = api("get", f"/rank/{job_id}/results")
        if sv: st.session_state[f"rank_{job_id}"] = sv

    res = st.session_state.get(f"rank_{job_id}")
    if not res:
        info_card(f'<div style="text-align:center;padding:2.5rem 0;font-size:.9rem;color:{T3};">Select a job and click <b style="color:{T1};">Run Scoring</b> to rank candidates.</div>')
        st.stop()

    cands   = res["ranked_candidates"]
    weights = res.get("weights_used", {})
    top     = cands[0]["total_score"] if cands else 0
    strong  = sum(1 for c in cands if c["total_score"] >= .70)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    m1,m2,m3,m4 = st.columns(4)
    with m1: stat_box(len(cands), "Candidates Scored")
    with m2: stat_box(f"{int(top*100)}%", "Highest Score", GREEN)
    with m3: stat_box(strong, "Strong Matches", BLUE)
    with m4: stat_box(f"{int(weights.get('skill_match',.4)*100)}%", "Skill Weight")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Candidate picker for detail view (no per-row button) ──────────────────
    cand_names = ["— Select candidate to view details —"] + [c.get("candidate_name","—") for c in cands]
    pc1, pc2 = st.columns([2,3])
    with pc1:
        picked = st.selectbox("View candidate details", cand_names, label_visibility="visible")

    sec(f"Ranking — {res.get('job_title','')}")

    # Table header
    h0,h1,h2,h3,h4,h5,h6 = st.columns([.5, 2.5, .8, .8, .8, .8, .9])
    for col, txt in zip([h0,h1,h2,h3,h4,h5,h6], ["#","Candidate","Overall","Skill","Exp.","Role Fit","Status"]):
        col.markdown(f'<div style="font-size:.68rem;font-weight:700;color:{T3};text-transform:uppercase;letter-spacing:.08em;padding-bottom:6px;border-bottom:2px solid {BORDER};">{txt}</div>', unsafe_allow_html=True)

    for i, c in enumerate(cands):
        rank  = c["rank"]
        name  = c.get("candidate_name","—")
        tot   = c["total_score"]
        bd    = c.get("score_breakdown",{})
        sk    = bd.get("skill_match",0)
        ex    = bd.get("experience_alignment",0)
        rf    = bd.get("role_relevance",0)
        pct   = int(tot*100)
        fg,bg2,bd2 = scolor(tot)
        lbl   = slabel(tot)
        is_picked = (picked == name)
        row_bg = BLUE_LT if is_picked else (SURFACE if i%2==0 else "#F8F9FC")

        rs = f"background:{row_bg};padding:10px 4px;border-bottom:1px solid {BORDER};"
        r0,r1,r2,r3,r4,r5,r6 = st.columns([.5, 2.5, .8, .8, .8, .8, .9])
        r0.markdown(f'<div style="{rs}font-size:.85rem;font-weight:700;color:{T3};">#{rank}</div>', unsafe_allow_html=True)
        r1.markdown(f'<div style="{rs}font-size:.875rem;font-weight:600;color:{T1};">{name}</div>', unsafe_allow_html=True)
        r2.markdown(f'<div style="{rs}font-size:.9rem;font-weight:800;color:{fg};">{pct}%</div>', unsafe_allow_html=True)
        r3.markdown(f'<div style="{rs}font-size:.78rem;color:{T2};">{int(sk*100)}%{pbar(int(sk*100),fg)}</div>', unsafe_allow_html=True)
        r4.markdown(f'<div style="{rs}font-size:.78rem;color:{T2};">{int(ex*100)}%{pbar(int(ex*100),fg)}</div>', unsafe_allow_html=True)
        r5.markdown(f'<div style="{rs}font-size:.78rem;color:{T2};">{int(rf*100)}%{pbar(int(rf*100),fg)}</div>', unsafe_allow_html=True)
        r6.markdown(f'<div style="{rs}">{badge(lbl,fg,bg2,bd2)}</div>', unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:.72rem;color:{T4};margin-top:10px;">Generated: {res.get("generated_at","")[:19].replace("T"," ")} UTC</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    dc, _ = st.columns([1,2])
    with dc:
        if st.button("Download Report (PDF)", use_container_width=True, key="dl_rpt"):
            import requests as _r  # type: ignore
            with st.spinner("Generating…"):
                rp = _r.get(f"{API_BASE}/rank/{job_id}/report.pdf", timeout=30)
            if rp.status_code == 200:
                safe = res.get("job_title","report").replace(" ","_").lower()
                st.download_button("Save Report", rp.content, f"ranking_{safe}.pdf", "application/pdf", use_container_width=True, key="sv_rpt")
            else: st.error("Report generation failed.")

    # ── Detail panel ──────────────────────────────────────────────────────────
    if picked != "— Select candidate to view details —":
        cn = next((c for c in cands if c.get("candidate_name") == picked), None)
        if cn:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            fg,bg2,bd2 = scolor(cn["total_score"])
            bdd = cn.get("score_breakdown",{})
            mat = cn.get("matched_skills",[])
            mis = cn.get("missing_skills",[])
            expl = cn.get("explanation","")
            dp1, dp2 = st.columns([1, 1], gap="large")

            with dp1:
                st.markdown(f'<div style="background:{SURFACE};border:1px solid {BORDER};border-top:3px solid {fg};border-radius:8px;padding:1.25rem;box-shadow:0 4px 20px rgba(0,0,0,.09);"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;"><div><div style="font-size:1rem;font-weight:700;color:{T1};">{cn.get("candidate_name","—")}</div><div style="font-size:.75rem;color:{T3};margin-top:2px;">Rank #{cn["rank"]} · {slabel(cn["total_score"])}</div></div><div style="font-size:1.75rem;font-weight:800;color:{fg};">{int(cn["total_score"]*100)}%</div></div>', unsafe_allow_html=True)
                for mk,ml in [("skill_match","Skill Match"),("experience_alignment","Experience"),("role_relevance","Role Fit")]:
                    v=bdd.get(mk,0); p=int(v*100); cf,_,_=scolor(v)
                    st.markdown(f'<div style="margin-bottom:10px;"><div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="font-size:.78rem;color:{T3};">{ml}</span><span style="font-size:.78rem;font-weight:700;color:{cf};">{p}%</span></div>{pbar(p,cf)}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with dp2:
                st.markdown(f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:1.25rem;box-shadow:0 4px 20px rgba(0,0,0,.09);">', unsafe_allow_html=True)
                if mat:
                    chips = " ".join(skill_chip(s,GREEN,GREEN_LT,GREEN_BD) for s in mat)
                    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{GREEN};text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;">Matched Skills</div><div style="line-height:2.2;">{chips}</div>', unsafe_allow_html=True)
                if mis:
                    chips = " ".join(skill_chip(s,RED,RED_LT,RED_BD) for s in mis)
                    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{RED};text-transform:uppercase;letter-spacing:.07em;margin:12px 0 6px;">Skill Gaps</div><div style="line-height:2.2;">{chips}</div>', unsafe_allow_html=True)
                if expl:
                    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{T3};text-transform:uppercase;letter-spacing:.07em;margin:12px 0 6px;">Model Reasoning (Assistive)</div><div style="background:{BG};border:1px solid {BORDER};border-left:3px solid {BLUE};border-radius:4px;padding:10px 12px;font-size:.8rem;color:{T2};line-height:1.75;">{expl}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)


# ── PAGE 3: EXPLANATIONS ──────────────────────────────────────────────────────
elif page == "Explanations":
    pg("Candidate Explanations", "Scoring rationale for each candidate. Model reasoning is assistive only.")
    jobs, _ = api("get", "/jobs/")
    if not jobs or not jobs["jobs"]: st.info("Add a job and run scoring first."); st.stop()
    jopts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs["jobs"]}  # type: ignore
    sel = st.selectbox("Job", list(jopts.keys()), label_visibility="collapsed")
    res, err = api("get", f"/rank/{jopts[sel]}/results")
    if err or not res: st.info("Run scoring first."); st.stop()
    cands = res["ranked_candidates"]  # type: ignore
    sec(f"{len(cands)} candidates")

    for c in cands:
        rank=c["rank"]; name=c.get("candidate_name","—"); tot=c["total_score"]
        bdd=c.get("score_breakdown",{}); mat=c.get("matched_skills",[]); mis=c.get("missing_skills",[])
        expl=c.get("explanation",""); fg,bg2,bd2=scolor(tot)
        with st.expander(f"#{rank}  {name}  —  {int(tot*100)}%  ({slabel(tot)})"):
            sc, sk = st.columns([1,1.3], gap="large")
            with sc:
                st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{T3};text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px;">Score Breakdown</div>', unsafe_allow_html=True)
                for mk,ml in [("total","Overall"),("skill_match","Skill Match"),("experience_alignment","Experience"),("role_relevance","Role Fit")]:
                    v=bdd.get(mk, tot if mk=="total" else 0); p=int(v*100); cf,_,_=scolor(v)
                    st.markdown(f'<div style="margin-bottom:10px;"><div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="font-size:.78rem;color:{T3};">{ml}</span><span style="font-size:.78rem;font-weight:700;color:{cf};">{p}%</span></div>{pbar(p,cf)}</div>', unsafe_allow_html=True)
            with sk:
                if mat:
                    chips=" ".join(skill_chip(s,GREEN,GREEN_LT,GREEN_BD) for s in mat)
                    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{GREEN};text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;">Matched</div><div style="line-height:2.2;">{chips}</div>', unsafe_allow_html=True)
                if mis:
                    chips=" ".join(skill_chip(s,RED,RED_LT,RED_BD) for s in mis)
                    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{RED};text-transform:uppercase;letter-spacing:.07em;margin:10px 0 6px;">Gaps</div><div style="line-height:2.2;">{chips}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{T3};text-transform:uppercase;letter-spacing:.07em;margin:14px 0 6px;">Model Reasoning (Assistive)</div><div style="background:{BG};border:1px solid {BORDER};border-left:3px solid {BLUE};border-radius:4px;padding:10px 12px;font-size:.8125rem;color:{T2};line-height:1.75;">{expl}</div>', unsafe_allow_html=True)
            if st.button("Load Resume Text", key=f"rt_{c['resume_id']}_{rank}"):  # type: ignore
                rd2, _ = api("get", f"/resumes/{c['resume_id']}")  # type: ignore
                if rd2: st.markdown(f'<pre style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:12px;font-size:.78rem;color:{T2};max-height:300px;overflow-y:auto;white-space:pre-wrap;">{rd2.get("raw_text","")}</pre>', unsafe_allow_html=True)


# ── PAGE 4: FAIRNESS AUDIT ────────────────────────────────────────────────────
elif page == "Fairness Audit":
    pg("Fairness Audit", "Statistical signals in scoring patterns. Review before finalising decisions.")
    st.markdown(f'<div style="background:{AMBER_LT};border:1px solid {AMBER_BD};border-radius:8px;padding:10px 14px;margin-bottom:1rem;font-size:.8rem;color:{AMBER};line-height:1.6;"><b>Note:</b> Statistical indicators only — not confirmation of bias. Apply professional judgement.</div>', unsafe_allow_html=True)

    jobs, _ = api("get", "/jobs/")
    if not jobs or not jobs["jobs"]: st.info("Add a job and run scoring first."); st.stop()
    jopts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs["jobs"]}  # type: ignore
    sel = st.selectbox("Job", list(jopts.keys()), label_visibility="collapsed")
    jid = jopts[sel]
    if st.button("Run Fairness Analysis"):
        with st.spinner("Analysing…"):
            r, e = api("get", f"/bias/{jid}")
        if e: st.error(e); st.stop()
        st.session_state[f"bias_{jid}"] = r

    rep = st.session_state.get(f"bias_{jid}")
    if not rep:
        info_card(f'<div style="text-align:center;padding:2rem 0;font-size:.9rem;color:{T3};">Select a job and click <b style="color:{T1};">Run Fairness Analysis</b>.</div>')
        st.stop()

    skew=rep.get("experience_skew_score",0); kw=rep.get("keyword_overfit_score",0); ns=len(rep.get("bias_signals",[]))
    def bc(v,lo=.45,hi=.7): return RED if v>=hi else AMBER if v>=lo else GREEN
    fa1,fa2,fa3=st.columns(3)
    with fa1: stat_box(f"{skew:.2f}","Experience Skew",bc(skew))
    with fa2: stat_box(f"{kw:.2f}","Keyword Overfit",bc(kw,.5,.75))
    with fa3: stat_box(str(ns),"Signals Flagged",bc(ns,1,2))

    fd=rep.get("factor_dominance",[])
    if fd:
        sec("Factor Contribution")
        fig=go.Figure(go.Bar(
            x=[f["factor_name"].replace("_"," ").title() for f in fd],
            y=[f["average_contribution"] for f in fd],
            marker={"color":[BLUE,GREEN,AMBER],"line":{"width":0}},
            text=[f"{f['average_contribution']:.3f}" for f in fd],
            textposition="outside",textfont={"color":T3,"size":11},
        ))
        fig.update_layout(paper_bgcolor=BG,plot_bgcolor=SURFACE,
            font={"color":T3,"family":"Inter"},
            yaxis={"gridcolor":BORDER,"zeroline":False},
            margin={"t":24,"b":8,"l":8,"r":8},showlegend=False,height=220,bargap=.45)
        st.plotly_chart(fig,use_container_width=True)

    sec("Flagged Signals")
    sigs=rep.get("bias_signals",[])
    scm={"high":(RED,RED_LT,RED_BD),"medium":(AMBER,AMBER_LT,AMBER_BD),"low":(GREEN,GREEN_LT,GREEN_BD)}
    if not sigs:
        st.markdown(f'<div style="background:{GREEN_LT};border:1px solid {GREEN_BD};border-radius:8px;padding:1rem 1.25rem;font-size:.875rem;color:{GREEN};font-weight:600;">No signals detected.</div>', unsafe_allow_html=True)
    else:
        for sg in sigs:
            sev=sg.get("severity","low"); fg2,bg2,bd3=scm.get(sev,scm["low"])
            st.markdown(f'<div style="background:{SURFACE};border:1px solid {bd3};border-left:4px solid {fg2};border-radius:8px;padding:.9rem 1.1rem;margin-bottom:8px;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;"><span style="background:{bg2};color:{fg2};font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:20px;text-transform:uppercase;">{sev}</span><span style="color:{T1};font-weight:600;font-size:.875rem;">{sg.get("signal_type","").replace("_"," ").title()}</span></div><div style="font-size:.8125rem;color:{T2};line-height:1.65;">{sg.get("description","")}</div></div>', unsafe_allow_html=True)

    sec("Ethical Disclaimer")
    st.markdown(f'<div style="background:{BG};border:1px solid {BORDER};border-radius:8px;padding:1rem 1.25rem;font-size:.8125rem;color:{T2};line-height:1.7;">{rep.get("ethical_disclaimer","")}</div>', unsafe_allow_html=True)


# ── PAGE 5: FEEDBACK ──────────────────────────────────────────────────────────
elif page == "Feedback":
    pg("Recruiter Feedback", "Record your decision on each candidate. Feedback is optional and calibrates future scoring.")
    jobs, _ = api("get", "/jobs/")
    if not jobs or not jobs["jobs"]: st.info("Add a job and run scoring first."); st.stop()
    jopts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs["jobs"]}  # type: ignore
    sel = st.selectbox("Job", list(jopts.keys()), label_visibility="collapsed")
    res, err = api("get", f"/rank/{jopts[sel]}/results")
    if err or not res: st.info("Run scoring first."); st.stop()
    cands = res["ranked_candidates"]  # type: ignore

    stats, _ = api("get", "/feedback/stats")
    if stats:
        sec("Feedback Summary")
        tf=stats.get("total_feedback",0); ac=stats.get("accept_count",0); rj=stats.get("reject_count",0)
        fs1,fs2,fs3,fs4=st.columns(4)
        with fs1: stat_box(tf,"Total Submitted")
        with fs2: stat_box(ac,"Progressed",GREEN)
        with fs3: stat_box(rj,"Declined",RED)
        with fs4: stat_box(f"{int(ac/tf*100)}%" if tf else "—","Progress Rate")

    sec("Review Queue")
    for c in cands:
        rid=c.get("ranking_id")
        if not rid: continue
        name=c.get("candidate_name","—"); rank=c["rank"]; tot=c["total_score"]
        fg,bg2,bd2=scolor(tot)
        st.markdown(f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:.85rem 1.25rem;margin-bottom:4px;display:flex;align-items:center;gap:12px;box-shadow:0 1px 6px rgba(0,0,0,.05);"><div style="font-size:.8rem;font-weight:700;color:{T3};min-width:28px;text-align:center;">#{rank}</div><div style="flex:1;font-size:.9rem;font-weight:600;color:{T1};">{name}</div><div style="font-size:.85rem;font-weight:800;color:{fg};margin-right:8px;">{int(tot*100)}%</div>{badge(slabel(tot),fg,bg2,bd2)}</div>', unsafe_allow_html=True)
        fc1,fc2,fc3=st.columns([1,2,1])
        with fc1:
            dec=st.radio("",["Progress","Decline"],key=f"d_{rid}",horizontal=True,label_visibility="collapsed")
        with fc2:
            notes=st.text_input("",key=f"n_{rid}",placeholder="Optional notes…",label_visibility="collapsed")
        with fc3:
            if st.button("Submit",key=f"s_{rid}",use_container_width=True):
                resp,ferr=api("post","/feedback/",json={"ranking_id":rid,"decision":"accept" if dec=="Progress" else "reject","notes":notes})
                if resp:
                    msg=f"{name}: {dec}d"
                    if resp.get("weight_adjustment_triggered"): msg+=" — weights updated"
                    st.success(msg)
                else: st.error(ferr)
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
