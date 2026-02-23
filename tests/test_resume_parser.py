"""
tests/test_resume_parser.py — Tests for resume_parser service.
"""

import pytest  # type: ignore
from app.services.resume_parser import (  # type: ignore
    parse_resume_text,
    _split_into_sections,
    _extract_candidate_name,
    _compute_duration_years,
    _parse_experience_section,
)


class TestSectionSplitting:
    def test_skills_section_identified(self):
        text = "John Doe\n\nSkills:\nPython, SQL\n\nExperience:\nDev at ACME 2020-2022"
        lines = text.splitlines()
        sections = _split_into_sections(lines)
        assert "python" in " ".join(sections["skills"]).lower() or \
               "sql" in " ".join(sections["skills"]).lower()

    def test_education_section_identified(self):
        text = "Jane\n\nEducation:\nB.Tech CS | IIT | 2020\n\nExperience:\nEngineer 2020"
        lines = text.splitlines()
        sections = _split_into_sections(lines)
        assert any("iit" in l.lower() for l in sections["education"])


class TestNameExtraction:
    def test_extracts_two_word_name(self):
        header_lines = ["Priya Sharma", "priya@email.com"]
        name = _extract_candidate_name(header_lines, "priya_sharma.txt")
        assert "Priya" in name and "Sharma" in name

    def test_fallback_to_filename(self):
        header_lines = ["some random text that isnt a name 1234"]
        name = _extract_candidate_name(header_lines, "john_doe.txt")
        # Filename fallback
        assert "John" in name or "john" in name.lower()

    def test_three_word_name(self):
        header_lines = ["Rahul Kumar Singh"]
        name = _extract_candidate_name(header_lines, "resume.txt")
        assert "Rahul" in name


class TestDurationComputation:
    def test_year_range(self):
        duration = _compute_duration_years("2018", "2022")
        assert duration == 4.0

    def test_present_end(self):
        import datetime
        duration = _compute_duration_years("2020", "Present")
        assert duration >= 2.0  # At least 2 years since 2020

    def test_zero_duration_edge_case(self):
        duration = _compute_duration_years("2023", "2023")
        assert duration == 0.0


class TestFullParsing:
    def test_senior_resume_name(self, parsed_senior_resume):
        assert "Priya" in parsed_senior_resume["name"] or \
               "Sharma" in parsed_senior_resume["name"]

    def test_raw_skills_extracted(self, parsed_senior_resume):
        skills = parsed_senior_resume["skills"]
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_yoe_positive(self, parsed_senior_resume):
        yoe = parsed_senior_resume["total_years_experience"]
        assert yoe > 0.0, "Senior resume should have >0 years experience"

    def test_junior_yoe_less_than_senior(self, parsed_senior_resume, parsed_junior_resume):
        senior_yoe = parsed_senior_resume["total_years_experience"]
        junior_yoe = parsed_junior_resume["total_years_experience"]
        assert junior_yoe < senior_yoe, "Junior should have less YoE than senior"

    def test_all_required_keys_present(self, parsed_senior_resume):
        required_keys = {"name", "skills", "experience_entries",
                         "total_years_experience", "education", "summary", "raw_text"}
        assert required_keys.issubset(parsed_senior_resume.keys())

    def test_raw_text_preserved(self, parsed_senior_resume):
        assert len(parsed_senior_resume["raw_text"]) > 50
