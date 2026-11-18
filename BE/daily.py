"""
Daily entrypoint — run the career-page pipeline once and send the digest.

  py -3.13 daily.py                 # last 7 days, LLM relevance, Telegram digest
  py -3.13 daily.py --days 3        # tighter window
  py -3.13 daily.py --no-llm        # keyword relevance only (no Gemini calls)
  py -3.13 daily.py --no-notify     # skip Telegram

Run it from the in-app scheduler (default) OR wire it to Windows Task Scheduler
if you prefer it to fire even when the console isn't running.
"""
import sys

from app.services import pipeline, notify


def main(argv):
    days = 7
    use_llm = "--no-llm" not in argv
    notify_on = "--no-notify" not in argv
    if "--days" in argv:
        try:
            days = int(argv[argv.index("--days") + 1])
        except Exception:
            pass

    print(f"[daily] running career pipeline · window={days}d · llm={use_llm} · notify={notify_on}")
    run_doc, matched = pipeline.run(max_age_days=days, use_llm=use_llm, send_digest=notify_on)
    print(f"[daily] discovered={run_doc['discovered']} new={run_doc['new']} matched={run_doc['matched']}")
    for co, s in run_doc["byCompany"].items():
        print(f"   {co}: new={s.get('new')} matched={s.get('matched')} {s.get('note','')}")
    if run_doc["errors"]:
        print("   errors:", run_doc["errors"])
    if notify_on and not notify.configured():
        print("[daily] Telegram not configured — set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env to get pushes.")
    return run_doc


if __name__ == "__main__":
    main(sys.argv[1:])
