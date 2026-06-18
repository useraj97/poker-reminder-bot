"""
Send ONE PokerBros reminder, fired by GitHub Actions.

The workflow triggers this a few minutes before the target time. This script:
  - figures out the exact target time in US Eastern (handles EST/EDT automatically),
  - sleeps until that exact moment, then sends,
  - and ignores the "wrong" cron line that only matches the other DST offset,
    so the message is sent exactly once per day at the right time.

Usage:
  python send_reminder.py --target 19:58 --which first
  python send_reminder.py --target 20:05 --which second

Env vars required:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Optional:
  TABLE_NAME (default "Call Now, Cry Later")
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

ET = ZoneInfo("America/New_York")
TABLE_NAME = os.environ.get("TABLE_NAME", "Call Now, Cry Later").strip()

# How early the workflow is allowed to fire (we sleep until target).
MAX_LEAD_MIN = 20
# How late we'll still send if the run was delayed; beyond this we skip.
MAX_LATE_MIN = 30


def message(which: str) -> str:
    if which == "first":
        return (
            f"⏰ 7:58 PM — Time to open the PokerBros table!\n"
            f"Start it now from the template: “{TABLE_NAME}” 🃏\n"
            f"We go live at 8:00."
        )
    return (
        f"🚨 8:05 PM — Is the “{TABLE_NAME}” table up yet?\n"
        f"If not, fire it up now so everyone can sit down. 🎰"
    )


def send(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    chat_id = os.environ["TELEGRAM_CHAT_ID"].strip()
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    resp.raise_for_status()
    if not resp.json().get("ok"):
        raise RuntimeError(f"Telegram error: {resp.text}")
    print(f"Sent: {text.splitlines()[0]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="ET time HH:MM, e.g. 19:58")
    ap.add_argument("--which", required=True, choices=["first", "second"])
    args = ap.parse_args()

    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        sys.exit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secret.")

    hh, mm = (int(x) for x in args.target.split(":"))
    now = datetime.now(ET)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    lead = (target - now).total_seconds() / 60  # minutes until target (negative if past)
    print(f"Now ET: {now:%Y-%m-%d %H:%M}. Target: {target:%H:%M}. Lead: {lead:.1f} min.")

    if lead > MAX_LEAD_MIN:
        print("Too early — this is the non-matching DST schedule. Skipping.")
        return
    if lead < -MAX_LATE_MIN:
        print("Too late — run was delayed beyond window. Skipping.")
        return

    if lead > 0:
        print(f"Sleeping {lead:.1f} min until exact target time...")
        time.sleep(lead * 60)

    send(message(args.which))


if __name__ == "__main__":
    main()
