"""Local mock data sources used by the Student Support Assistant.

In a production system these would be replaced by calls to a real FAQ
content store and a student information system. Keeping them isolated in
one module makes that swap a one-file change.
"""

from __future__ import annotations

from student_support_assistance.models import FAQEntry, StudentRecord

#: The FAQ knowledge base, searched by :mod:`knowledge_base`.
KNOWLEDGE_BASE: tuple[FAQEntry, ...] = (
    FAQEntry(
        question="When is course registration?",
        answer=(
            "Course registration for the upcoming semester opens four weeks "
            "before the term starts and closes one week after classes begin. "
            "Check the academic calendar on the student portal for exact dates."
        ),
        tags=("registration", "deadline", "calendar", "semester"),
    ),
    FAQEntry(
        question="How do I pay my tuition?",
        answer=(
            "Tuition can be paid online through the student portal using a "
            "credit card or bank transfer, or in person at the Bursar's "
            "Office. Payment plans are available for students who qualify."
        ),
        tags=("tuition", "payment", "bursar", "fees"),
    ),
    FAQEntry(
        question="What is the deadline to pay tuition?",
        answer=(
            "Tuition is due no later than the second Friday of each "
            "semester. A late fee applies to balances paid after that date."
        ),
        tags=("tuition", "deadline", "payment", "late fee"),
    ),
    FAQEntry(
        question="How do I apply for admission?",
        answer=(
            "Admissions applications are submitted online through the "
            "admissions portal. You will need transcripts, a personal "
            "statement, and two letters of recommendation."
        ),
        tags=("admissions", "application", "transcripts"),
    ),
    FAQEntry(
        question="What are the admission requirements?",
        answer=(
            "Undergraduate admission requires a high school diploma or "
            "equivalent, a minimum GPA of 2.5, and satisfactory scores on "
            "an accepted standardized test."
        ),
        tags=("admissions", "requirements", "gpa"),
    ),
    FAQEntry(
        question="Where is the campus located?",
        answer=(
            "The main campus is located at 123 University Avenue. Shuttle "
            "buses run between the campus and the downtown transit center "
            "every 20 minutes on weekdays."
        ),
        tags=("campus", "location", "directions", "shuttle"),
    ),
    FAQEntry(
        question="What are the campus office hours?",
        answer=(
            "Administrative offices, including the Registrar and Bursar, "
            "are open Monday through Friday from 9 a.m. to 5 p.m."
        ),
        tags=("campus", "office hours", "registrar", "bursar"),
    ),
    FAQEntry(
        question="How do I check my graduation requirements?",
        answer=(
            "Log in to the student portal and open the 'Degree Audit' tab "
            "to see remaining requirements toward graduation. You can also "
            "request a review from your academic advisor."
        ),
        tags=("graduation", "degree audit", "requirements"),
    ),
    FAQEntry(
        question="When can I apply to graduate?",
        answer=(
            "Graduation applications open at the start of your final "
            "semester and must be submitted at least eight weeks before "
            "commencement."
        ),
        tags=("graduation", "application", "deadline", "commencement"),
    ),
    FAQEntry(
        question="How do I drop or withdraw from a course?",
        answer=(
            "Courses can be dropped from the student portal before the "
            "add/drop deadline without academic penalty. Withdrawing after "
            "that date results in a 'W' grade on your transcript."
        ),
        tags=("registration", "withdraw", "drop", "transcript"),
    ),
    FAQEntry(
        question="How do I apply for financial aid?",
        answer=(
            "Financial aid applications are submitted through the Financial "
            "Aid Office using the annual aid application. Awards are based "
            "on demonstrated need and available funding."
        ),
        tags=("financial aid", "application", "funding"),
    ),
    FAQEntry(
        question="What payment methods are accepted for tuition?",
        answer=(
            "The Bursar's Office accepts credit card, debit card, bank "
            "transfer, and certified check payments for tuition and fees."
        ),
        tags=("payment", "tuition", "bursar", "methods"),
    ),
)

#: Mock student information system records, keyed by student ID.
STUDENT_RECORDS: dict[str, StudentRecord] = {
    "S1001": StudentRecord(
        student_id="S1001",
        status="Enrolled",
        courses=("Python Programming", "Data Structures"),
    ),
    "S1002": StudentRecord(
        student_id="S1002",
        status="Enrolled",
        courses=("Calculus II", "Introduction to Psychology", "English Composition"),
    ),
    "S1003": StudentRecord(
        student_id="S1003",
        status="On Leave",
        courses=(),
    ),
    "S1004": StudentRecord(
        student_id="S1004",
        status="Graduated",
        courses=("Capstone Project",),
    ),
    "S1005": StudentRecord(
        student_id="S1005",
        status="Enrolled",
        courses=("Organic Chemistry", "Statistics"),
    ),
}
