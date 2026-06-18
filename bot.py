"""
PokerBros table reminder bot.

Sends two scheduled reminders to a Telegram group every day (US Eastern time):
  - 7:58 PM  -> heads-up to open the table
  - 8:05 PM  -> reminder that the table should be live

Configuration is via environment variables:
  TELEGRAM_BOT_TOKEN   token from @BotFather (required)
  TELEGRAM_CHAT_ID     numeric ID of the group chat (required)
  TABLE_NAME           table template name (default: "Call Now, Cry Later")
  RUN_DAYS            optional cron day-of-week filter, e.g. "mon-fri" or "fri,sat,sun"
                       (default: every day)
"""

import logging
import os
import sys

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("pokerbot")

TIMEZONE = "America/New_York"  # US Eastern (handles EST/EDT automatically)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
TABLE_NAME = os.environ.get("TABLE_NAME", "Call Now, Cry Later").strip()
RUN_DAYS = os.environ.get("RUN_DAYS", "*").strip() or "*"


def send_message(text: str) -> None:
    """Send a message to the configured group chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text},
            timeout=30,
        )
        if resp.ok and resp.json().get("ok"):
            log.info("Sent reminder: %s", text.splitlines()[0])
        else:
            log.error("Telegram API error: %s", resp.text)
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to send message: %s", exc)


def first_reminder() -> None:
    send_message(
        f"⏰ 7:58 PM — Time to open the PokerBros table!\n"
        f"Start it now from the template: “{TABLE_NAME}” 🃏\n"
        f"We go live at 8:00."
    )


def second_reminder() -> None:
    send_message(
        f"🚨 8:05 PM — Is the “{TABLE_NAME}” table up yet?\n"
        f"If not, fire it up now so everyone can sit down. 🎰"
    )


def main() -> None:
    if not BOT_TOKEN or not CHAT_ID:
        log.error(
            "Missing config. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
            "environment variables."
        )
        sys.exit(1)

    sched = BlockingScheduler(timezone=TIMEZONE)
    sched.add_job(
        first_reminder, "cron", hour=19, minute=58,
        day_of_week=RUN_DAYS, id="reminder_758",
    )
    sched.add_job(
        second_reminder, "cron", hour=20, minute=5,
        day_of_week=RUN_DAYS, id="reminder_805",
    )

    log.info(
        "Bot started. Reminders at 7:58 PM and 8:05 PM %s (days: %s) for table '%s'.",
        TIMEZONE, RUN_DAYS, TABLE_NAME,
    )
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped.")


if __name__ == "__main__":
    main()
