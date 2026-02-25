"""ui/app.py — Resume Screening · Polished Enterprise UI v3 (FINAL)"""
# CRITICAL: DO NOT MODIFY THE UI DESIGN WITHOUT EXPLICIT USER CONSENT.
# The UI/UX tokens and CSS are locked in ui/design_system.py.

# pyre-ignore[21]
import streamlit as st  # type: ignore
import plotly.graph_objects as go  # type: ignore
import requests  # type: ignore

# Import locked Design System
try:
    from design_system import (  # type: ignore
        inject_custom_css, BG, SURFACE, BORDER, BLUE, BLUE_DK, BLUE_LT, BLUE_BD,
        GREEN, GREEN_LT, GREEN_BD, AMBER, AMBER_LT, AMBER_BD, RED, RED_LT, RED_BD,
        T1, T2, T3, T4
    )
except ImportError:
    from ui.design_system import (  # type: ignore
        inject_custom_css, BG, SURFACE, BORDER, BLUE, BLUE_DK, BLUE_LT, BLUE_BD,
        GREEN, GREEN_LT, GREEN_BD, AMBER, AMBER_LT, AMBER_BD, RED, RED_LT, RED_BD,
        T1, T2, T3, T4
    )

def scolor(s):
    if s >= .70: return GREEN, GREEN_LT, GREEN_BD
    if s >= .45: return AMBER, AMBER_LT, AMBER_BD
    return RED, RED_LT, RED_BD

def slabel(s):
    if s >= .70: return "Strong"
    if s >= .45: return "Moderate"
    return "Weak"

@st.cache_data(ttl=10)
def fetch_stats():
    """Cached fetch of basic counts to speed up sidebar reruns."""
    rd, _ = api("get", "/resumes/")
    jd_s, _ = api("get", "/jobs/")
    return (rd["total"] if rd else 0), (jd_s["total"] if jd_s else 0)

@st.cache_data(ttl=60)
def check_health():
    """Cached health check."""
    health, _ = api("get", "/health")
    return bool(health)

@st.cache_data(ttl=30)
def fetch_jobs():
    """Cached jobs list."""
    res, err = api("get", "/jobs/")
    return res.get("jobs", []) if res else [], err

@st.cache_data(ttl=30)
def fetch_ranking_results(job_id):
    """Cached ranking results."""
    res, err = api("get", f"/rank/{job_id}/results")
    return res, err

# Lock in the Design System
inject_custom_css()

API_BASE = "http://127.0.0.1:8000"


# ── Helpers ───────────────────────────────────────────────────────────────────
def api(method, path, **kw):
    try:
        r = getattr(requests, method)(f"{API_BASE}{path}", timeout=60, **kw)
        if r.status_code == 204 or not r.content:
            return ({}, None) if r.status_code < 300 else (None, f"HTTP {r.status_code}")
        try:
            if not r.content: return ({}, None)
            data = r.json()
            if r.status_code < 300: return data, None
            return None, data.get("detail", f"Error {r.status_code}: {r.text[:200]}")
        except:
            msg = f"Error {r.status_code}"
            if r.text: msg += f": {r.text[:200]}"
            return None, msg
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API — check if server is running."
    except Exception as e:
        return None, f"Request error: {str(e)}"


def sec(txt):
    st.markdown(f'<div style="font-size:.7rem;font-weight:700;color:{T3};text-transform:uppercase;letter-spacing:.09em;padding-bottom:.5rem;border-bottom:1px solid {BORDER};margin:1.4rem 0 .85rem;">{txt}</div>', unsafe_allow_html=True)

def pg(title, sub=""):
    st.markdown(f'<div style="margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid {BORDER};"><h1 style="font-size:1.5rem;font-weight:800;color:{T1};letter-spacing:-.02em;margin-bottom:3px;">{title}</h1><p style="font-size:.8125rem;color:{T3};">{sub}</p></div>', unsafe_allow_html=True)

def stat_box(val, lbl, c=BLUE):
    st.markdown(f'<div style="background:{SURFACE};border:1px solid {BORDER};border-top:3px solid {c};border-radius:8px;padding:.9rem 1.1rem;text-align:center;box-shadow:0 1px 8px rgba(0,0,0,.06);"><div style="font-size:1.6rem;font-weight:800;color:{c};line-height:1;">{val}</div><div style="font-size:.68rem;font-weight:600;color:{T3};text-transform:uppercase;letter-spacing:.08em;margin-top:5px;">{lbl}</div></div>', unsafe_allow_html=True)

def pbar(pct, col):
    """Clean, single-line progress bar to prevent Streamlit rendering bugs."""
    return f'<div style="background:{BORDER};border-radius:99px;height:4px;overflow:hidden;margin-top:6px;width:100%;border:0.5px solid {BORDER};"><div style="background:{col};width:{pct}%;height:100%;border-radius:99px;"></div></div>'

def skill_chip(s, fg, bg, bd):
    return f'<span style="background:{bg};color:{fg};border:1px solid {bd};font-size:.72rem;font-weight:500;padding:2px 9px;border-radius:20px;display:inline-block;margin:2px;">{s}</span>'

def badge(lbl, fg, bg, bd):
    """Modern status badge with soft tones and precise typography."""
    return f'<span style="background:{bg}; color:{fg}; border:1px solid {bd}; font-size:0.65rem; font-weight:700; padding:4px 12px; border-radius:100px; text-transform:uppercase; letter-spacing:0.04em; box-shadow: 0 1px 2px rgba(0,0,0,0.04); white-space:nowrap;">{lbl}</span>'

def info_card(content):
    st.markdown(f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:1.25rem 1.5rem;box-shadow:0 1px 8px rgba(0,0,0,.06);">{content}</div>', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div style="padding:0.5rem 1rem 1rem;border-bottom:1px solid {BORDER};margin-bottom:.75rem;"><div style="font-size:1.0625rem;font-weight:800;color:{T1};letter-spacing:-.02em;">Resume Screening</div><div style="font-size:.72rem;color:{T4};margin-top:3px;font-weight:500;">AI-Assisted Candidate Review</div></div>', unsafe_allow_html=True)

    page = st.radio("nav", ["Input","Results","Explanations","Fairness Audit","Feedback"], label_visibility="collapsed")

    st.markdown(f'<div style="margin:1rem 0;border-top:1px solid {BORDER};"></div>', unsafe_allow_html=True)

    is_online = check_health()
    if is_online:
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:{GREEN_LT};border:1px solid {GREEN_BD};border-radius:8px;"><div style="width:7px;height:7px;background:{GREEN};border-radius:50%;flex-shrink:0;"></div><span style="font-size:.8rem;font-weight:600;color:{GREEN};">API Connected</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:{RED_LT};border:1px solid {RED_BD};border-radius:8px;"><div style="width:7px;height:7px;background:{RED};border-radius:50%;flex-shrink:0;"></div><span style="font-size:.8rem;font-weight:600;color:{RED};">API Offline</span></div>', unsafe_allow_html=True)

    st.markdown(f'<div style="margin:.75rem 0;border-top:1px solid {BORDER};"></div>', unsafe_allow_html=True)

    nr, nj = fetch_stats()

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
        resumes_list = rl.get("resumes", []) if isinstance(rl, dict) else []
        if isinstance(resumes_list, list):
            for r in resumes_list:
                with st.expander(r["name"]):
                    st.markdown(f'<div style="font-size:.8rem;color:{T3};margin-bottom:10px;"><b style="color:{T2};">File:</b> {r["file_name"]}<br><b style="color:{T2};">Added:</b> {r["created_at"][:16].replace("T"," ")}</div>', unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    with b1:
                        show_text = st.toggle("View Text", key=f"vtog_{r['id']}")
                    with b2:
                        if st.button("Download PDF", key=f"d_{r['id']}", use_container_width=True):  # type: ignore
                            import requests as _r  # type: ignore
                            with st.spinner("Generating…"):
                                pr = _r.get(f"{API_BASE}/resumes/{r['id']}/pdf", timeout=30)
                            if pr.status_code == 200:
                                st.download_button("Save PDF", pr.content, f"{r['name'].replace(' ','_')}.pdf", "application/pdf", key=f"ds_{r['id']}", use_container_width=True)
                            else: st.error("PDF failed.")
                    
                    if show_text:
                        det, _ = api("get", f"/resumes/{r['id']}")
                        if det:
                            txt = det.get("raw_text", "")
                            st.markdown(f"""
                                <div style="background:{BG}; border: 1px solid {BORDER}; border-radius: 8px; padding: 1.25rem; margin-top: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid {BORDER}; padding-bottom: 8px;">
                                        <span style="font-size: 0.65rem; font-weight: 800; color: {T3}; text-transform: uppercase; letter-spacing: 0.1em;">Document Explorer</span>
                                        <span style="font-size: 0.65rem; color: {T4};">{len(txt)} chars</span>
                                    </div>
                                    <div style="font-size: 0.82rem; color: {T2}; line-height: 1.7; max-height: 350px; overflow-y: auto; white-space: pre-wrap; font-family: 'Inter', system-ui, sans-serif;">{txt}</div>
                                </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                    if st.button("Delete Resume", key=f"del_r_{r['id']}", use_container_width=True):
                        d, e = api("delete", f"/resumes/{r['id']}")
                        if e: st.error(e)
                        else:
                            st.cache_data.clear()
                            st.success("Resume deleted.")
                            st.rerun()
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

        sec("Stored Job Descriptions")
        jl, _ = fetch_jobs()
        if jl:
            for j in jl:
                with st.expander(f"{j['title']} (ID: {j['id']})"):
                    st.markdown(f'<div style="font-size:.8rem;color:{T3};margin-bottom:10px;"><b style="color:{T2};">Added:</b> {j["created_at"][:16].replace("T"," ")}<br><b style="color:{T2};">Exp. Required:</b> {j["min_years_experience"]} yrs</div>', unsafe_allow_html=True)
                    if st.button("Delete Job Role", key=f"del_j_{j['id']}", use_container_width=True):
                        d, e = api("delete", f"/jobs/{j['id']}")
                        if e: st.error(e)
                        else:
                            st.cache_data.clear() # Clear all caches to refresh lists
                            st.success("Job deleted.")
                            st.rerun()
        else:
            st.caption("No jobs defined yet.")


# ── PAGE 2: RESULTS ───────────────────────────────────────────────────────────
elif page == "Results":
    pg("Ranked Candidates", "Assistive scoring only — final decisions remain with the recruiter.")

    jobs, err = api("get", "/jobs/")
    if err: st.error(err); st.stop()
    if not jobs["jobs"]:  # type: ignore
        st.info("No jobs found — add a job description first."); st.stop()

    jopts = {f"{j['title']}  (ID: {j['id']})": j["id"] for j in jobs["jobs"]}  # type: ignore
    c1, c2, c3 = st.columns([2,1.2,1])
    with c1: sel = st.selectbox("Job", list(jopts.keys()), label_visibility="collapsed")
    job_id = jopts[sel]
    with c2: sprio = st.toggle("Skills Priority", help="Dampen experience penalties to prioritize candidate potential and skills.")
    with c3:
        if st.button("Run Scoring", use_container_width=True):
            with st.spinner("Computing scores…"):
                d, e = api("post", f"/rank/{job_id}?skills_priority={str(sprio).lower()}")
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

    # Table header - High density, professional metadata row
    h0,h1,h2,h3,h4,h5,h6 = st.columns([.5, 2.5, .8, .8, .8, .8, .9])
    header_style = f"font-size:0.68rem; font-weight:800; color:{T4}; text-transform:uppercase; letter-spacing:0.12em; padding-bottom:12px; border-bottom:1px solid {BORDER};"
    h0.markdown(f'<div style="{header_style}">#</div>', unsafe_allow_html=True)
    h1.markdown(f'<div style="{header_style}">Candidate</div>', unsafe_allow_html=True)
    h2.markdown(f'<div style="{header_style}">Overall</div>', unsafe_allow_html=True)
    h3.markdown(f'<div style="{header_style}">Skillset</div>', unsafe_allow_html=True)
    h4.markdown(f'<div style="{header_style}">Exp.</div>', unsafe_allow_html=True)
    h5.markdown(f'<div style="{header_style}">Role Fit</div>', unsafe_allow_html=True)
    h6.markdown(f'<div style="{header_style}">Status</div>', unsafe_allow_html=True)

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
        row_bg = BLUE_LT if is_picked else SURFACE
        
        # Professional row look with refined padding
        rs = f"background:{row_bg}; padding:16px 6px; border-bottom:1px solid {BORDER}; min-height:70px;"
        
        r0,r1,r2,r3,r4,r5,r6 = st.columns([.5, 2.5, .8, .8, .8, .8, .9])
        
        # Rank
        r0.markdown(f'<div style="{rs} font-size:0.85rem; font-weight:700; color:{T4}; display:flex; align-items:center;">#{rank}</div>', unsafe_allow_html=True)
        
        # Name + Boost tag
        boost_tag = f'<span title="Talent Boost" style="background:{AMBER_LT}; border:1px solid {AMBER_BD}; color:{AMBER}; font-size:0.6rem; padding:2px 8px; border-radius:4px; margin-left:10px; font-weight:700;">BOOST ⭐</span>' if bd.get("boost_applied") else ""
        r1.markdown(f'<div style="{rs} font-size:0.95rem; font-weight:600; color:{T1}; display:flex; align-items:center;">{name}{boost_tag}</div>', unsafe_allow_html=True)
        
        # Score
        r2.markdown(f'<div style="{rs} font-size:1.05rem; font-weight:800; color:{fg}; display:flex; align-items:center;">{pct}<small style="font-size:0.65rem; margin-left:1px; opacity:0.8;">%</small></div>', unsafe_allow_html=True)
        
        # Metrics
        for col, val in zip([r3,r4,r5], [sk,ex,rf]):
            col.markdown(f'<div style="{rs}"><div style="font-size:0.75rem; font-weight:600; color:{T2};">{int(val*100)}%</div>{pbar(int(val*100), fg)}</div>', unsafe_allow_html=True)
            
        # Status Badge
        r6.markdown(f'<div style="{rs} display:flex; align-items:center; justify-content:flex-start;">{badge(lbl,fg,bg2,bd2)}</div>', unsafe_allow_html=True)

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
            fg,bg2,bd2 = scolor(cn["total_score"])
            bdd = cn.get("score_breakdown",{})
            mat = cn.get("matched_skills",[])
            mis = cn.get("missing_skills",[])
            expl = cn.get("explanation","")
            
            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
            dp1, dp2 = st.columns([1, 1], gap="large")

            with dp1:
                # Optimized single-block Score Card
                rows_html = "".join([
                    f'<div style="margin-bottom:12px;">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
                    f'<span style="font-size:.78rem;color:{T3};">{label}</span>'
                    f'<span style="font-size:.78rem;font-weight:700;color:{scolor(v)[0]};">{int(v*100)}%</span>'
                    f'</div>{pbar(int(v*100), scolor(v)[0])}</div>'
                    for k, label in [("skill_match","Skill Match"),("experience_alignment","Experience"),("role_relevance","Role Fit")]
                    if (v := bdd.get(k,0)) or True
                ])
                
                st.markdown(f"""
                <div style="background:{SURFACE};border:1px solid {BORDER};border-top:4px solid {fg};border-radius:12px;padding:1.5rem;box-shadow:0 10px 30px rgba(0,0,0,.08);">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.25rem;">
                    <div>
                      <div style="font-size:1.1rem;font-weight:800;color:{T1};letter-spacing:-.01em;">{cn.get("candidate_name","—")}</div>
                      <div style="font-size:.78rem;color:{T3};margin-top:3px;font-weight:500;">Rank #{cn["rank"]} · <span style="color:{fg};font-weight:700;">{slabel(cn["total_score"])} Match</span></div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:1.85rem;font-weight:800;color:{fg};line-height:1;">{int(cn["total_score"]*100)}%</div>
                      <div style="font-size:.65rem;color:{T4};text-transform:uppercase;font-weight:700;margin-top:4px;">Total Score</div>
                    </div>
                  </div>
                  {rows_html}
                </div>
                """, unsafe_allow_html=True)

            with dp2:
                if mat or mis or expl:
                    # Optimized single-block Insights Card
                    mat_html = f'<div style="font-size:.7rem;font-weight:800;color:{GREEN};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Matched Skills</div><div style="line-height:2.4;margin-bottom:16px;">' + "".join(skill_chip(s,GREEN,GREEN_LT,GREEN_BD) for s in mat) + '</div>' if mat else ""
                    gap_html = f'<div style="font-size:.7rem;font-weight:800;color:{RED};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Skill Gaps</div><div style="line-height:2.4;margin-bottom:16px;">' + "".join(skill_chip(s,RED,RED_LT,RED_BD) for s in mis) + '</div>' if mis else ""
                    expl_html = f'<div style="font-size:.7rem;font-weight:800;color:{T3};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Model Rationale</div><div style="background:{BG};border:1px solid {BORDER};border-left:4px solid {BLUE};border-radius:8px;padding:12px 14px;font-size:.825rem;color:{T2};line-height:1.7;">{expl}</div>' if expl else ""
                    
                    st.markdown(f"""
                    <div style="background:{SURFACE};border:1px solid {BORDER};border-radius:12px;padding:1.5rem;box-shadow:0 10px 30px rgba(0,0,0,.08);">
                      {mat_html}
                      {gap_html}
                      {expl_html}
                    </div>
                    """, unsafe_allow_html=True)


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

    for i, c in enumerate(cands):
        rank=c["rank"]
        name=c.get("candidate_name","—")
        tot=c["total_score"]
        hp_badge = " ⭐ " if c.get("high_potential") else ""
        bdd=c.get("score_breakdown",{})
        mat=c.get("matched_skills",[])
        mis=c.get("missing_skills",[])
        expl=c.get("explanation","")
        fg,bg2,bd2=scolor(tot)
        
        with st.expander(f"#{rank}  {name} {hp_badge} —  {int(tot*100)}%  ({slabel(tot)})"):
            # Header Info
            st.markdown(f"""
                <div style="margin-bottom: 20px; border-bottom: 1px solid {BORDER}; padding-bottom: 15px;">
                    <span style="font-size: 0.65rem; font-weight: 800; color:{T4}; text-transform: uppercase; letter-spacing: 0.1em;">Candidate Insight Report</span>
                </div>
            """, unsafe_allow_html=True)
            
            sc, sk = st.columns([1, 1.3], gap="large")
            with sc:
                st.markdown(f'<div style="font-size: 0.7rem; font-weight: 700; color: {T3}; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 15px;">Score Breakdown</div>', unsafe_allow_html=True)
                for mk, ml in [("total", "Overall Alignment"), ("skill_match", "Technical Fit"), ("experience_alignment", "Experience Fit"), ("role_relevance", "Mission Fit")]:
                    v = bdd.get(mk, tot if mk == "total" else 0)
                    p = int(v * 100)
                    cf, _, _ = scolor(v)
                    st.markdown(f"""
                        <div style="margin-bottom: 14px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 0.78rem; color: {T2}; font-weight: 500;">{ml}</span>
                                <span style="font-size: 0.82rem; font-weight: 800; color: {cf};">{p}%</span>
                            </div>
                            {pbar(p, cf)}
                        </div>
                    """, unsafe_allow_html=True)
            
            with sk:
                if mat:
                    chips = " ".join(skill_chip(s, GREEN, GREEN_LT, GREEN_BD) for s in mat)
                    st.markdown(f'<div style="font-size: 0.7rem; font-weight: 700; color: {GREEN}; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;">Technical Strengths</div><div style="line-height: 2.3;">{chips}</div>', unsafe_allow_html=True)
                if mis:
                    chips = " ".join(skill_chip(s, RED, RED_LT, RED_BD) for s in mis)
                    st.markdown(f'<div style="font-size: 0.7rem; font-weight: 700; color: {RED}; text-transform: uppercase; letter-spacing: 0.08em; margin: 18px 0 8px;">Strategic Gaps</div><div style="line-height: 2.3;">{chips}</div>', unsafe_allow_html=True)
            
            # Model Rationale Card
            st.markdown(f"""
                <div style="background: {BG}; border: 1px solid {BORDER}; border-left: 4px solid {BLUE}; border-radius: 8px; padding: 1.25rem; margin: 24px 0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
                    <div style="font-size: 0.65rem; font-weight: 800; color: {T3}; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 10px;">Model Rationale (Assistive)</div>
                    <div style="font-size: 0.85rem; color: {T1}; line-height: 1.75; font-family: 'Inter', sans-serif;">{expl}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Integrated Document Explorer
            show_text = st.toggle("Document Explorer", key=f"etog_{c['resume_id']}_{rank}")
            if show_text:
                rd2, _ = api("get", f"/resumes/{c['resume_id']}")
                if rd2:
                    txt = rd2.get("raw_text", "")
                    st.markdown(f"""
                        <div style="background:{SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; padding: 1.25rem; margin-top: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid {BORDER}; padding-bottom: 8px;">
                                <span style="font-size: 0.62rem; font-weight: 800; color: {T3}; text-transform: uppercase; letter-spacing: 0.1em;">Resume Source Transcript</span>
                                <span style="font-size: 0.62rem; color: {T4};">{len(txt)} chars</span>
                            </div>
                            <div style="font-size: 0.8rem; color: {T2}; line-height: 1.7; max-height: 350px; overflow-y: auto; white-space: pre-wrap; font-family: 'Inter', system-ui, sans-serif;">{txt}</div>
                        </div>
                    """, unsafe_allow_html=True)


# ── PAGE 4: FAIRNESS AUDIT ────────────────────────────────────────────────────
elif page == "Fairness Audit":
    pg("Fairness Audit", "Statistical signals in scoring patterns. Review before finalising decisions.")
    st.markdown(f'<div style="background:{AMBER_LT};border:1px solid {AMBER_BD};border-radius:8px;padding:10px 14px;margin-bottom:1rem;font-size:.8rem;color:{AMBER};line-height:1.6;"><b>Note:</b> This page audits <b>Scoring Fairness</b> (how the AI ranks). To record your <b>Decisions</b> (Progress/Decline), use the <b>Feedback</b> page.</div>', unsafe_allow_html=True)

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
    with fa1: st.metric("Experience Skew", f"{skew:.2f}", help="Spearman correlation (0 to 1). High values mean rankings match years of experience perfectly.")
    with fa2: st.metric("Keyword Overfit", f"{kw:.2f}", help="Spearman correlation (0 to 1). High values mean rankings match keyword counts perfectly.")
    with fa3: st.metric("Signals Flagged", str(ns), help="Number of potential bias markers detected for human review.")

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
        st.markdown(f"""
        <div style="background:{GREEN_LT};border:1px solid {GREEN_BD};border-radius:12px;padding:1.5rem;box-shadow:0 4px 15px rgba(15,123,85,.05);">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem;">
            <div style="background:{GREEN};color:#fff;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:900;">✓</div>
            <div style="font-size:1rem;font-weight:700;color:{GREEN};">Fairness Verification Passed</div>
          </div>
          <p style="font-size:.825rem;color:{T2};line-height:1.6;margin-bottom:1rem;">The audit has completed. No statistically significant bias markers were found in this ranking cycle. The score distribution aligns with job-relevant requirements.</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div style="display:flex;align-items:center;gap:8px;font-size:.78rem;color:{T3};"><span style="color:{GREEN};">●</span> Gender-Neutral Language check</div>
            <div style="display:flex;align-items:center;gap:8px;font-size:.78rem;color:{T3};"><span style="color:{GREEN};">●</span> Age-Bias Trigger check</div>
            <div style="display:flex;align-items:center;gap:8px;font-size:.78rem;color:{T3};"><span style="color:{GREEN};">●</span> Keyword Over-Optimization check</div>
            <div style="display:flex;align-items:center;gap:8px;font-size:.78rem;color:{T3};"><span style="color:{GREEN};">●</span> Geographic Proxy check</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for sg in sigs:
            sev=sg.get("severity","low"); fg2,bg2,bd3=scm.get(sev,scm["low"])
            affected = sg.get("affected_candidates", [])
            affected_html = ""
            if affected:
                names = ", ".join([a["name"] for a in affected])
                affected_html = f'<div style="margin-top:8px;font-size:.75rem;font-weight:700;color:{fg2};">Influential Candidates: <span style="font-weight:400;color:{T2};">{names}</span></div>'
            
            st.markdown(f'<div style="background:{SURFACE};border:1px solid {bd3};border-left:4px solid {fg2};border-radius:8px;padding:.9rem 1.1rem;margin-bottom:8px;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;"><span style="background:{bg2};color:{fg2};font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:20px;text-transform:uppercase;">{sev}</span><span style="color:{T1};font-weight:600;font-size:.875rem;">{sg.get("signal_type","").replace("_"," ").title()}</span></div><div style="font-size:.8125rem;color:{T2};line-height:1.65;">{sg.get("description","")}</div>{affected_html}</div>', unsafe_allow_html=True)

    sec("Ethical Disclaimer")
    st.markdown(f'<div style="background:{BG};border:1px solid {BORDER};border-radius:8px;padding:1rem 1.25rem;font-size:.8125rem;color:{T2};line-height:1.7;">{rep.get("ethical_disclaimer","")}</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown(f"""
        <div style="margin-top:2rem;padding:1.5rem;background:{BLUE_LT};border:1px solid {BLUE_BD};border-radius:12px;">
          <div style="font-size:1rem;font-weight:700;color:{BLUE};margin-bottom:.5rem;">🛡️ Candidate Advocacy & Professionalism</div>
          <p style="font-size:.825rem;color:{T2};line-height:1.6;">
            <b>The "YoE Blind Spot":</b> Candidates often forget to explicitly state their total years of experience, or use varied date formats. 
            If a top candidate is ranked lower than expected, check if they have a <b>Skill Match</b> > 0.80. This usually indicates a 
            strong profile despite detected tenure gaps.
          </p>
          <p style="font-size:.825rem;color:{T2};line-height:1.6;margin-top:.5rem;">
            <b>Talent Boost:</b> The system automatically applies a 40% penalty-dampening boost (⭐) to candidates who show exceptional 
            role relevance and skills, even if their experience count is low. This ensures we don't miss "Fast Track" talent.
          </p>
        </div>
        """, unsafe_allow_html=True)


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

    # Fetch feedback stats for this specific job
    stats, _ = api("get", f"/feedback/stats?job_id={jopts[sel]}")
    if stats and res is not None:
        job_title = str(res.get("job_title", ""))
        sec(f"Feedback Summary — {job_title}")
        tf=stats.get("total_feedback",0); ac=stats.get("accept_count",0); rj=stats.get("reject_count",0)
        fs1,fs2,fs3,fs4=st.columns(4)
        with fs1: stat_box(tf,"Total Submitted")
        with fs2: stat_box(ac,"Progressed",GREEN)
        with fs3: stat_box(rj,"Declined",RED)
        with fs4: stat_box(f"{int(ac/tf*100)}%" if tf else "—","Progress Rate")
    
    # Fetch all feedback for this job to map current decisions
    fb_res, _ = api("get", f"/feedback/job/{jopts[sel]}")
    fb_map = {}
    if isinstance(fb_res, dict) and "feedback" in fb_res:
        for f in fb_res["feedback"]:
            if f["ranking_id"] not in fb_map:
                fb_map[f["ranking_id"]] = f["decision"]

    sec("Review Queue")
    for c in cands:
        rid=c.get("ranking_id")
        if not rid: continue
        name=c.get("candidate_name","—"); rank=c["rank"]; tot=c["total_score"]
        fg,bg2,bd2=scolor(tot)
        prev = fb_map.get(rid)
        status_badge = ""
        if prev == "accept":
            status_badge = f' {badge("PROGRESSED", GREEN, GREEN_LT, GREEN_BD)}'
        elif prev == "reject":
            status_badge = f' {badge("DECLINED", RED, RED_LT, RED_BD)}'
        else:
            status_badge = f' {badge("PENDING", T4, SURFACE, BORDER)}'

        html = f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:.85rem 1.25rem;margin-bottom:4px;display:flex;align-items:center;gap:12px;box-shadow:0 1px 6px rgba(0,0,0,.05);"><div style="font-size:.8rem;font-weight:700;color:{T3};min-width:28px;text-align:center;">#{rank}</div><div style="flex:1;font-size:.9rem;font-weight:600;color:{T1};">{name}</div><div style="font-size:.85rem;font-weight:800;color:{fg};margin-right:8px;">{int(tot*100)}%</div>{status_badge} {str(badge(slabel(tot),fg,bg2,bd2))}</div>'
        st.markdown(html, unsafe_allow_html=True)
        fc1,fc2,fc3=st.columns([1,2,1])
        with fc1:
            prev = fb_map.get(rid)
            idx = 0 if prev == "accept" else 1 if prev == "reject" else 0
            dec=st.radio("",["Progress","Decline"],index=idx,key=f"d_{rid}",horizontal=True,label_visibility="collapsed")
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
