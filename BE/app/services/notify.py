"""
Telegram notifications — the proactive daily digest + instant new-match alerts.

Setup (one time):
  1. In Telegram, message @BotFather -> /newbot -> copy the token.
  2. Message your new bot once (say "hi"), then open
     https://api.telegram.org/bot<token>/getUpdates to read your chat id.
  3. Put both in JobPull/.env:
        TELEGRAM_BOT_TOKEN=123456:ABC...
        TELEGRAM_CHAT_ID=987654321

If either is missing, send() is a safe no-op that reports 'not configured' — the
pipeline still runs and stores jobs; you just won't get a push until it's set.
"""
import os

try:
    import requests
except ImportError:
    requests = None

import config

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", getattr(config, "TELEGRAM_BOT_TOKEN", ""))
_CHAT = os.getenv("TELEGRAM_CHAT_ID", getattr(config, "TELEGRAM_CHAT_ID", ""))


def configured() -> bool:
    return bool(_TOKEN and _CHAT)


def send(text: str) -> dict:
    if not configured():
        return {"ok": False, "status": "not configured (set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)"}
    if requests is None:
        return {"ok": False, "status": "requests not installed"}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
            json={"chat_id": _CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=20)
        return {"ok": r.status_code == 200, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "status": f"{type(e).__name__}: {e}"}


def digest(matched: list, when: str = "today") -> dict:
    """Send a formatted digest of matched jobs. `matched` = list of job dicts."""
    if not matched:
        return send(f"🛰️ <b>JobPull</b> — no new matches {when}. All quiet in Chennai/Bengaluru.")
    lines = [f"🛰️ <b>JobPull</b> — {len(matched)} new match{'es' if len(matched) != 1 else ''} {when}", ""]
    for j in matched[:20]:
        title = j.get("title", "")
        co = j.get("company", "")
        loc = (j.get("location") or "").split(",")[0]
        url = j.get("apply_url") or j.get("job_url") or ""
        why = ""
        rel = j.get("relevance") or {}
        if rel.get("reason"):
            why = f"\n   <i>{rel['reason']}</i>"
        lines.append(f"• <b>{title}</b> — {co} · {loc}\n   <a href=\"{url}\">apply</a>{why}")
    if len(matched) > 20:
        lines.append(f"\n…and {len(matched) - 20} more in the console.")
    return send("\n".join(lines))
