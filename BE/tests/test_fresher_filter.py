"""
Pure unit test for the IT-FRESHER title filter — no network, no DB. Run:
    python tests/test_fresher_filter.py

Demonstrates that the fresher profile ACCEPTS entry-level IT roles (fresher /
intern / trainee / junior / associate, across dev, data, QA, support, HR) and
REJECTS senior titles and non-IT / blue-collar roles.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from title_filter import evaluate_fresher

SHOULD_ACCEPT = [
    "Software Developer - Fresher",
    "Graduate Engineer Trainee",
    "Trainee Software Engineer",
    "Junior Python Developer",
    "Associate Software Engineer",
    "Data Analyst - Fresher",
    "QA Trainee",
    "Entry Level Web Developer",
    "Internship - Backend Development",
    "HR Intern",
    "Technical Support Executive (Fresher)",
    "Management Trainee - IT",
    "Campus Hire - Software Engineer",
    "Associate Consultant - Fresher",
    "GET - Graduate Engineer Trainee",
    "Junior Data Analyst",
    "Trainee - Information Technology",
]

SHOULD_REJECT = [
    "Senior Software Engineer",
    "Lead Data Scientist",
    "Engineering Manager",
    "Principal Developer",
    "Staff Nurse",
    "Delivery Driver",
    "Mechanical Engineer",
    "Senior HR Manager",
    "Experienced Java Developer",
    "Field Sales Executive",
    "Data Scientist",            # plain mid title, no entry signal
    "Python Developer",          # plain mid title, no entry signal
    "Security Guard",
    "Junior Clinical Scientist", # entry signal but NOT an IT role
    "Trainee Accountant",        # entry signal but NOT an IT role
    "Nursing Trainee",           # non-IT reject
    "",
]


def run():
    passed = failed = 0
    print("--- SHOULD ACCEPT (fresher / entry-level IT) ---")
    for t in SHOULD_ACCEPT:
        ok, reason = evaluate_fresher(t)
        mark = "PASS" if ok else "FAIL"
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        print(f"  [{mark}] {t!r:48s} -> accepted={ok} {reason}")

    print("--- SHOULD REJECT (senior / non-IT / no entry signal) ---")
    for t in SHOULD_REJECT:
        ok, reason = evaluate_fresher(t)
        mark = "PASS" if not ok else "FAIL"
        passed, failed = (passed + 1, failed) if not ok else (passed, failed + 1)
        print(f"  [{mark}] {t!r:48s} -> accepted={ok} {reason}")

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
