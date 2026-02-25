import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from app.services.skill_extractor import get_skill_extractor  # type: ignore

def test_non_tech_skills():
    extractor = get_skill_extractor()
    
    test_cases = [
        ("Project Management Professional with PMP and Agile Scrum experience.", ["Project Management", "Agile", "Scrum"]),
        ("Managed stakeholders and assessed risks in a Kanban environment.", ["Stakeholder Management", "Risk Management", "Kanban"]),
        ("Expert in financial analysis, budgeting, and KPI tracking.", ["Financial Analysis", "Budget Management", "KPI Tracking"]),
        ("Talent acquisition leader with background in HRIS and succession planning.", ["Talent Acquisition", "HRIS", "Succession Planning"]),
        ("Highly developed emotional intelligence and conflict resolution skills.", ["Emotional Intelligence", "Conflict Resolution"])
    ]
    
    print("--- Running Non-Tech Skill Extraction Test ---")
    all_passed = True
    for text, expected in test_cases:
        extracted = extractor.extract_from_text(text)
        # Check if all expected skills are in the extracted list
        missing = [s for s in expected if s not in extracted]
        if missing:
            print(f"FAILED: '{text}'")
            print(f"  Expected: {expected}")
            print(f"  Extracted: {extracted}")
            print(f"  Missing: {missing}")
            all_passed = False
        else:
            print(f"PASSED: '{text}'")
            print(f"  Extracted: {extracted}")
            
    if all_passed:
        print("\nSUCCESS: All non-tech domains are correctly supported by the SkillExtractor!")
    else:
        print("\nFAILURE: Some skills were not correctly identified.")

if __name__ == "__main__":
    test_non_tech_skills()
