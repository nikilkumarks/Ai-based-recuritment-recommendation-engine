"""Synthetic NLP fixtures. Plumbing tests only — not real-world accuracy evidence."""

from __future__ import annotations

ANNOTATED_RESUME = """
Ada Lovelace
ada@example.com | +91 98765 43210
https://www.linkedin.com/in/ada-lovelace
https://github.com/ada
https://ada.dev

Summary
Backend engineer focused on retrieval systems and ranking APIs.

Experience
Senior Engineer at Example Corp
Jan 2023 - Present
Built ranking APIs with Python and FastAPI.

Software Engineer | Acme Labs | 2020 - 2022
Worked on retrieval systems.

Education
B.Tech Computer Science, National Institute of Technology
2016 - 2020

Projects
Campus Recommendation Engine
https://github.com/example/recs
Built a matching prototype using Python, Next.js, and CI/CD.

Certifications
AWS Cloud Practitioner, Amazon Web Services, Jan 2024

Skills
Python, TensorFlow, C++, Node.js, Next.js, CI/CD, ML, Machine Learning
""".strip()

FALSE_POSITIVE_TEXT = "This project improved performance by 30%."

ANNOTATED_JD = """
Senior Backend Engineer
Location: Bengaluru
Employment: Full-time
We need 4 years of experience and a Bachelor of Technology.

Requirements
Must have Python, FastAPI, PostgreSQL, and CI/CD.
Preferred
Nice to have TensorFlow and Next.js.
""".strip()
