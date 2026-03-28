"""Alert Monitor: Polls Postgres alerts table and sends formatted dispatches to Discord."""

import json
import logging
import time
import sys

from config import POLL_INTERVAL, STATE_FILE
import db
from transcribe import get_or_create_transcript
from parser import parse_alert
from discord_notify import build_embed, send_to_discord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("alert-monitor")


def load_state() -> int:
    """Load last_alert_id from state file. Returns 0 if not found."""
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_alert_id", 0)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return 0


def save_state(last_alert_id: int):
    """Persist last_alert_id to state file."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"last_alert_id": last_alert_id}, f)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def process_alert(alert: dict) -> bool:
    """
    Full pipeline for one alert:
    1. Get or create transcript
    2. Parse into structured format (may return None for suppressed alerts)
    3. Send Discord plain text + embed
    4. Update DB with alert summary
    """
    alert_id = alert["alertId"]
    call_id = alert["callId"]
    logger.info(f"Processing alert #{alert_id} (callId={call_id})")

    # Step 1: Get transcript
    transcript = get_or_create_transcript(alert)
    if not transcript:
        logger.warning(f"No transcript available for alert #{alert_id}")

    # Step 2: Parse transcript
    parsed = parse_alert(alert, transcript)
    if parsed is None:
        logger.info(f"Alert #{alert_id} suppressed (pager test / disregard)")
        return False

    logger.info(
        f"Alert #{alert_id}: {parsed['county']} | {parsed['address']} | "
        f"{parsed['incident_type']}"
    )

    # Step 3: Send to Discord — plain text line + rich embed
    payload = build_embed(alert, parsed)
    # Add the plain text summary line above the embed
    payload["content"] = parsed["formatted"]
    discord_ok = send_to_discord(payload)
    if not discord_ok:
        logger.warning(f"Discord notification failed for alert #{alert_id}")

    # Step 4: Update DB
    try:
        db.update_call_alert_summary(call_id, parsed["formatted"])
    except Exception as e:
        logger.error(f"Failed to update alert summary for callId={call_id}: {e}")

    return True


def main():
    logger.info("=" * 60)
    logger.info("Alert Monitor starting...")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")
    logger.info("=" * 60)

    # Load last processed alert ID
    last_alert_id = load_state()

    # If no state, start from current max to avoid processing old alerts
    if last_alert_id == 0:
        try:
            last_alert_id = db.get_max_alert_id()
            save_state(last_alert_id)
            logger.info(f"No previous state found. Starting from alertId={last_alert_id}")
        except Exception as e:
            logger.error(f"Failed to get max alertId: {e}")
            logger.info("Starting from alertId=0 (will process all alerts)")

    logger.info(f"Watching for alerts with alertId > {last_alert_id}")

    # Track processed callIds to deduplicate within a session
    # (multiple alerts can fire for the same call — tone + keyword)
    processed_call_ids = set()

    while True:
        try:
            alerts = db.fetch_new_alerts(last_alert_id)

            if alerts:
                logger.info(f"Found {len(alerts)} new alert(s)")

            for alert in alerts:
                call_id = alert["callId"]

                # Deduplicate: skip if we already sent a Discord message for this callId
                if call_id in processed_call_ids:
                    logger.info(
                        f"Skipping alert #{alert['alertId']} — "
                        f"callId={call_id} already processed"
                    )
                    last_alert_id = alert["alertId"]
                    save_state(last_alert_id)
                    continue

                try:
                    sent = process_alert(alert)
                    if sent:
                        processed_call_ids.add(call_id)
                except Exception as e:
                    logger.error(
                        f"Failed to process alert #{alert['alertId']}: {e}",
                        exc_info=True,
                    )

                # Always advance past this alert
                last_alert_id = alert["alertId"]
                save_state(last_alert_id)

            # Prevent the dedup set from growing forever —
            # keep only the last 500 call IDs
            if len(processed_call_ids) > 500:
                excess = len(processed_call_ids) - 500
                for _ in range(excess):
                    processed_call_ids.pop()

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}", exc_info=True)

        try:
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break


if __name__ == "__main__":
    main()
