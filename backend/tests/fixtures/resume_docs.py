"""In-memory PDF/DOCX fixtures. These only prove text survives extraction."""

from __future__ import annotations

import io

from docx import Document
from fpdf import FPDF


def pdf_with_lines(lines: list[str]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in lines:
        pdf.multi_cell(w=pdf.epw, h=8, text=line)
    return bytes(pdf.output())


def normal_pdf() -> bytes:
    return pdf_with_lines(
        [
            "Ada Lovelace",
            "Software engineer with eight years of experience.",
            "Built ranking systems and APIs.",
        ]
    )


def sectioned_pdf() -> bytes:
    return pdf_with_lines(
        [
            "Summary",
            "Backend engineer focused on retrieval systems.",
            "Experience",
            "Senior engineer at Example Corp.",
            "Education",
            "B.S. Computer Science",
            "Projects",
            "Built a campus recommendation prototype.",
            "Skills",
            "Python, SQL, Docker",
            "Certifications",
            "AWS Cloud Practitioner",
        ]
    )


def pdf_containing(term: str) -> bytes:
    return pdf_with_lines(
        [
            "Candidate resume",
            f"Technical skills include {term} among other tools.",
            "Experience includes production services.",
        ]
    )


def blank_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    return bytes(pdf.output())


def malformed_pdf() -> bytes:
    return b"%PDF-1.4\nthis is not a valid pdf body\n%%EOF"


def encrypted_pdf() -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(normal_pdf()))
    writer = PdfWriter()
    writer.append(reader)
    writer.encrypt("secret-password")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def normal_docx() -> bytes:
    document = Document()
    document.add_heading("Ada Lovelace", level=0)
    document.add_paragraph("Software engineer with eight years of experience.")
    document.add_paragraph("Built ranking systems and APIs.")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def heading_docx() -> bytes:
    document = Document()
    document.add_heading("Summary", level=1)
    document.add_paragraph("Backend engineer focused on retrieval systems.")
    document.add_heading("Experience", level=1)
    document.add_paragraph("Senior engineer at Example Corp.")
    document.add_heading("Education", level=1)
    document.add_paragraph("B.S. Computer Science")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Skill"
    table.cell(0, 1).text = "Level"
    table.cell(1, 0).text = "Python"
    table.cell(1, 1).text = "Advanced"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def malformed_docx() -> bytes:
    return b"PK\x03\x04not-a-real-office-document"
