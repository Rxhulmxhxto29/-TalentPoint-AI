import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from app.services.resume_parser import _compute_duration_years, _parse_experience_section  # type: ignore
from app.services.jd_parser import _extract_experience_requirements  # type: ignore

def test_experience_parsing():
    print("--- Running Experience Parsing Tests ---")
    
    # 1. Resume Duration Tests (Mon YYYY - Mon YYYY)
    test_cases_duration = [
        ("Jan 2020", "Jun 2020", 0.42),
        ("Jan 2020", "Present", None), # Should be > 4 years as of 2024
        ("2021", "2023", 2.0)
    ]
    
    print("\n[Duration Tests]")
    for s, e, exp in test_cases_duration:
        dur = _compute_duration_years(s, e)
        print(f"  {s} to {e} -> {dur} yrs (Expected approx: {exp})")

    # 2. Explicit Resume Statements
    test_cases_explicit = [
        (["I have 6 months of experience in Python."], 0.5),
        (["Experienced professional with 2 years and 3 months of work."], 2.0) # Existing logic takes max
    ]
    
    print("\n[Explicit Statement Tests]")
    for lines, exp in test_cases_explicit:
        _, total = _parse_experience_section(lines)
        print(f"  '{lines[0]}' -> {total} yrs (Expected: {exp})")

    # 3. JD Requirements
    test_cases_jd = [
        ("Looking for someone with 6 months of experience.", 0.5),
        ("Minimum 18 months experience required.", 1.5),
        ("3-5 years of experience.", 3.0)
    ]
    
    print("\n[JD Requirement Tests]")
    for text, exp_min in test_cases_jd:
        vmin, vmax = _extract_experience_requirements(text)
        print(f"  '{text}' -> Min: {vmin}, Max: {vmax} (Expected Min: {exp_min})")

if __name__ == "__main__":
    test_experience_parsing()
