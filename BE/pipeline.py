"""Cloud Run entry point for one complete JobPull batch.

The scraper and analyzer remain independently runnable, but this command gives
Cloud Scheduler one safe target: scrape first, then analyze the newly stored
jobs. Use ``--skip-analysis`` when the Gemini key/quota is not enabled yet.
"""
import argparse
import sys

import config
from analyze import main as analyze_main
from run import main as scrape_main


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-analysis", action="store_true")
    parser.add_argument("sources", nargs="*", help="linkedin, indeed, and/or naukri")
    args = parser.parse_args(argv)

    scrape_main(args.sources)

    if args.skip_analysis:
        print("[pipeline] analysis skipped by request")
    elif not config.GEMINI_API_KEY:
        print("[pipeline] GEMINI_API_KEY is not set; analysis skipped")
    else:
        analyze_main([])


if __name__ == "__main__":
    main(sys.argv[1:])
