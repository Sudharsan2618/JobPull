"""
Pure unit test for the title filter — no network, no DB. Run:
    python tests/test_title_filter.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from title_filter import evaluate_title

SHOULD_ACCEPT = [
    "Gen AI Engineer",
    "Generative AI Engineer",
    "AI Engineer",
    "Senior AI Engineer",
    "Python Developer",
    "Python Developer - Backend",
    "Machine Learning Engineer",
    "ML Engineer",
    "Artificial Intelligence Engineer",
    "AI/ML Engineer",
    "LLM Engineer",
    "NLP Engineer",
]

SHOULD_REJECT = [
    "Sales Executive",
    "HR Manager",
    "Python Trainer",
    "AI Sales Specialist",
    "Recruiter",
    "Business Development Manager",
    "Accountant",
    "Customer Support Engineer",
    "",
]


def run():
    passed = failed = 0
    print("--- SHOULD ACCEPT ---")
    for t in SHOULD_ACCEPT:
        ok, reason = evaluate_title(t)
        mark = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{mark}] {t!r:45s} -> accepted={ok} {reason}")

    print("--- SHOULD REJECT ---")
    for t in SHOULD_REJECT:
        ok, reason = evaluate_title(t)
        mark = "PASS" if not ok else "FAIL"
        if not ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{mark}] {t!r:45s} -> accepted={ok} {reason}")

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
