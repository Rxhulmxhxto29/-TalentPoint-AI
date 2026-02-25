"""
app/services/report_service.py — PDF report generation for resumes and rankings.
Uses fpdf2 to create professional, cleanly formatted PDF documents.
"""

import logging
from datetime import datetime
from typing import Any, List, Dict
from fpdf import FPDF # type: ignore

logger = logging.getLogger(__name__)

class PDFReport(FPDF):
    def header(self):
        # Logo placeholder or icon
        self.set_font("helvetica", "B", 12)
        self.set_text_color(37, 99, 235) # Blue accent
        self.cell(0, 10, "AI Resume Screener | Enterprise Report", border=0, align="L")
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 116, 139) # Secondary text
        self.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", border=0, align="R")
        self.ln(12)
        self.line(10, 22, 200, 22) # Header line

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()} | AI-Aided Recruitment Insights", align="C")

class ReportService:
    def _sanitize_text(self, text: str) -> str:
        """Replace common non-latin-1 characters with safe equivalents to avoid '?' in PDFs."""
        if not text: return ""
        replacements = {
            "\u2022": "-",     # bullet
            "\u2013": "-",     # en dash
            "\u2014": "-",     # em dash
            "\u201c": '"',     # smart open quote
            "\u201d": '"',     # smart close quote
            "\u2018": "'",     # smart open single quote
            "\u2019": "'",     # smart close single quote
            "\u2026": "...",   # ellipsis
            "\u2122": "(TM)",  # trademark
            "\u00ae": "(R)",   # registered
            "\u00a9": "(C)",   # copyright
            "\t": "    ",     # tabs to spaces
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Final fallback for characters still outside latin-1
        return text.encode("latin-1", "replace").decode("latin-1")

    def generate_resume_pdf(self, candidate_name: str, raw_text: str) -> bytes:
        """Create a clean PDF version of the resume text."""
        try:
            pdf = PDFReport()
            pdf.add_page()
            
            # Title
            pdf.set_font("helvetica", "B", 20)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 15, self._sanitize_text(candidate_name), ln=True)
            
            pdf.ln(5)
            
            # Body
            pdf.set_font("helvetica", size=10)
            pdf.set_text_color(51, 65, 85)
            safe_text = self._sanitize_text(raw_text)
            pdf.multi_cell(0, 6, safe_text)
            
            return pdf.output()
        except Exception as e:
            logger.error(f"Failed to generate resume PDF: {e}")
            raise

    def generate_ranking_report(
        self, 
        job_title: str, 
        candidates: List[Dict[str, Any]], 
        weights: Dict[str, float]
    ) -> bytes:
        """Create a professional ranking report summary."""
        try:
            pdf = PDFReport()
            pdf.add_page()
            
            # Job Title
            pdf.set_font("helvetica", "B", 18)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 12, f"Ranking Report: {self._sanitize_text(job_title)}", ln=True)
            
            pdf.ln(5)
            
            # Summary Section
            pdf.set_font("helvetica", "B", 12)
            pdf.set_fill_color(248, 250, 252)
            pdf.cell(0, 10, " 1. Configuration Summary", ln=True, fill=True)
            pdf.ln(2)
            
            pdf.set_font("helvetica", size=10)
            pdf.set_text_color(71, 85, 105)
            pdf.cell(40, 7, f"Total Ranked:")
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 7, f"{len(candidates)} candidates", ln=True)
            
            pdf.set_font("helvetica", size=10)
            pdf.cell(40, 7, f"Scoring Weights:")
            w_str = ", ".join([f"{k.replace('_',' ').title()}: {int(v*100)}%" for k,v in weights.items()])
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 7, w_str, ln=True)
            
            pdf.ln(10)
            
            # Ranking Table Header
            pdf.set_font("helvetica", "B", 11)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(37, 99, 235)
            pdf.cell(15, 10, "Rank", border=1, align="C", fill=True)
            pdf.cell(75, 10, "Candidate Name", border=1, align="L", fill=True)
            pdf.cell(30, 10, "Score", border=1, align="C", fill=True)
            pdf.cell(70, 10, "Match Level", border=1, align="C", fill=True)
            pdf.ln()
            
            # Ranking Table Rows
            pdf.set_text_color(30, 41, 59)
            pdf.set_font("helvetica", size=10)
            for c in candidates[:20]: # type: ignore # Show top 20 in the table
                score_pct = f"{int(c['total_score'] * 100)}%"
                
                # Determine match label
                if c['total_score'] >= 0.70: label = "Strong Match"
                elif c['total_score'] >= 0.45: label = "Moderate Match"
                else: label = "Weak Match"
                
                pdf.cell(15, 8, str(c['rank']), border=1, align="C")
                pdf.cell(75, 8, self._sanitize_text(c.get('candidate_name', '—')), border=1, align="L")
                pdf.cell(30, 8, score_pct, border=1, align="C")
                pdf.cell(70, 8, label, border=1, align="C")
                pdf.ln()
                
            # Candidate Details Page
            if candidates:
                pdf.add_page()
                pdf.set_font("helvetica", "B", 12)
                pdf.set_fill_color(248, 250, 252)
                pdf.cell(0, 10, " 2. Top Candidate Insights", ln=True, fill=True)
                pdf.ln(5)
                
                for c in candidates[:5]: # type: ignore # Detailed view for top 5
                    pdf.set_font("helvetica", "B", 11)
                    pdf.set_text_color(15, 23, 42)
                    pdf.cell(0, 8, f"#{c['rank']} {self._sanitize_text(c.get('candidate_name', '—'))} ({int(c['total_score']*100)}%)", ln=True)
                    
                    pdf.set_font("helvetica", size=9)
                    pdf.set_text_color(71, 85, 105)
                    expl = self._sanitize_text(c.get('explanation', ''))
                    pdf.multi_cell(0, 5, f"AI Feedback: {expl}")
                    
                    # Skills match summary
                    matched_list = c.get('matched_skills', [])
                    if matched_list:
                        matched = self._sanitize_text(", ".join(matched_list))
                        pdf.set_font("helvetica", "B", 9)
                        pdf.set_text_color(5, 150, 105)
                        pdf.ln(1) # Small gap
                        pdf.multi_cell(0, 5, f"Matched Skills: {matched}")
                    
                    pdf.ln(2)
                    last_y = pdf.get_y()
                    if last_y > 270: # Avoid line at the very bottom
                        pdf.add_page()
                    else:
                        pdf.line(10, last_y, 200, last_y)
                        pdf.ln(5)
            
            return pdf.output()
        except Exception as e:
            logger.error(f"Failed to generate ranking report: {e}")
            raise

# Singleton instance
report_service = ReportService()
