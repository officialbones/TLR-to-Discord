"""Discord webhook notification for dispatch alerts."""

import logging
import time
from datetime import datetime, timezone
import requests
from config import DISCORD_WEBHOOK_URL

logger = logging.getLogger(__name__)

# Embed colors by incident category
COLOR_FIRE = 0xFF4500       # Red-orange
COLOR_EMS = 0x3498DB        # Blue
COLOR_LAW = 0xF1C40F        # Yellow
COLOR_HAZMAT = 0xE67E22     # Orange
COLOR_PURSUIT = 0x9B59B6    # Purple
COLOR_DEFAULT = 0x95A5A6    # Grey

FIRE_KEYWORDS = ["fire", "smoke", "burn", "flame", "hazmat", "gas leak", "carbon monoxide", "explosion"]
EMS_KEYWORDS = ["ems", "medical", "cardiac", "ambulance", "overdose", "unresponsive", "breathing", "choking", "seizure", "stroke", "fall", "injury", "chest pain"]
LAW_KEYWORDS = ["shooting", "shots", "stabbing", "assault", "robbery", "burglary", "theft", "stolen", "domestic", "disturbance", "pursuit", "trespass", "suspicious", "alarm", "bomb", "missing"]
PURSUIT_KEYWORDS = ["pursuit", "chase"]
HAZMAT_KEYWORDS = ["hazmat", "haz-mat", "hazardous"]


def _color_for_type(incident_type: str) -> int:
    """Return embed color based on incident type."""
    it_lower = incident_type.lower()

    if any(kw in it_lower for kw in PURSUIT_KEYWORDS):
        return COLOR_PURSUIT
    if any(kw in it_lower for kw in HAZMAT_KEYWORDS):
        return COLOR_HAZMAT
    if any(kw in it_lower for kw in FIRE_KEYWORDS):
        return COLOR_FIRE
    if any(kw in it_lower for kw in EMS_KEYWORDS):
        return COLOR_EMS
    if any(kw in it_lower for kw in LAW_KEYWORDS):
        return COLOR_LAW
    return COLOR_DEFAULT


def _unix_to_iso(ts) -> str:
    """Convert unix timestamp (seconds or milliseconds) to ISO 8601."""
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    ts = int(ts)
    # Handle millisecond timestamps
    if ts > 1e12:
        ts = ts // 1000
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def build_embed(alert: dict, parsed: dict) -> dict:
    """Build a Discord webhook payload with a rich embed."""
    color = _color_for_type(parsed["incident_type"])

    embed = {
        "title": f"{parsed['incident_type']}",
        "color": color,
        "fields": [
            {"name": "County", "value": parsed["county"], "inline": True},
            {"name": "Address", "value": parsed["address"], "inline": True},
            {"name": "Incident Type", "value": parsed["incident_type"], "inline": True},
        ],
        "description": parsed["summary"][:4096],
        "timestamp": _unix_to_iso(alert.get("createdAt")),
        "footer": {"text": f"Alert #{alert.get('alertId', '?')}"},
    }

    # Add talkgroup/system info if available
    tg = alert.get("talkgroupLabel") or alert.get("talkgroupName") or ""
    sys_label = alert.get("systemLabel") or ""
    if tg:
        embed["fields"].append({"name": "Talkgroup", "value": tg, "inline": True})
    if sys_label:
        embed["fields"].append({"name": "System", "value": sys_label, "inline": True})

    # Add alert type if available
    alert_type = alert.get("alertType", "")
    if alert_type:
        embed["fields"].append({"name": "Alert Type", "value": alert_type, "inline": True})

    return {"embeds": [embed]}


def send_to_discord(payload: dict) -> bool:
    """
    Send payload to Discord webhook.
    Handles rate limiting with retry.
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("No Discord webhook URL configured, skipping notification")
        return False

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=30,
        )

        if response.status_code == 204:
            logger.info("Discord notification sent successfully")
            return True

        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 5)
            logger.warning(f"Discord rate limited, retrying after {retry_after}s")
            time.sleep(retry_after)
            response = requests.post(
                DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=30,
            )
            if response.status_code == 204:
                logger.info("Discord notification sent after rate limit retry")
                return True

        logger.error(
            f"Discord webhook failed: {response.status_code} {response.text[:200]}"
        )
        return False

    except Exception as e:
        logger.error(f"Discord webhook error: {e}")
        return False
