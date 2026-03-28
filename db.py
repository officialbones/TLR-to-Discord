"""Database operations for the alert monitor."""

import logging
import psycopg2
import psycopg2.extras
from config import DATABASE_URL

logger = logging.getLogger(__name__)

_conn = None


def get_connection():
    """Return a persistent connection, reconnecting if closed."""
    global _conn
    if _conn is None or _conn.closed:
        logger.info("Connecting to database...")
        _conn = psycopg2.connect(DATABASE_URL)
        _conn.autocommit = False
        logger.info("Database connected.")
    return _conn


def fetch_new_alerts(last_alert_id: int) -> list[dict]:
    """
    Fetch new alerts with joined call, talkgroup, and system info.
    Returns list of dicts sorted by alertId ASC.
    """
    conn = get_connection()
    query = """
        SELECT
            a."alertId",
            a."callId",
            a."systemId",
            a."talkgroupId",
            a."alertType",
            a."toneDetected",
            a."toneSetId",
            a."keywordsMatched",
            a."transcriptSnippet",
            a."createdAt",
            c."transcript",
            c."transcriptionStatus",
            c."audioFilename",
            c."audioMime",
            c."alertSummary",
            c."timestamp" AS "callTimestamp",
            t."label" AS "talkgroupLabel",
            t."name" AS "talkgroupName",
            s."label" AS "systemLabel"
        FROM "alerts" a
        JOIN "calls" c ON a."callId" = c."callId"
        LEFT JOIN "talkgroups" t ON a."talkgroupId" = t."talkgroupId"
        LEFT JOIN "systems" s ON a."systemId" = s."systemId"
        WHERE a."alertId" > %s
        ORDER BY a."alertId" ASC
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (last_alert_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        conn.rollback()
        raise


def fetch_call_audio(call_id: int) -> tuple[bytes, str, str]:
    """Return (audio_bytes, filename, mime_type) from calls table."""
    conn = get_connection()
    query = """
        SELECT "audio", "audioFilename", "audioMime"
        FROM "calls"
        WHERE "callId" = %s
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (call_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"No call found with callId={call_id}")
            audio = bytes(row["audio"])
            return audio, row["audioFilename"], row["audioMime"]
    except Exception as e:
        logger.error(f"Error fetching audio for callId={call_id}: {e}")
        conn.rollback()
        raise


def update_call_transcript(call_id: int, transcript: str):
    """Update the transcript and status on a call."""
    conn = get_connection()
    query = """
        UPDATE "calls"
        SET "transcript" = %s, "transcriptionStatus" = 'completed'
        WHERE "callId" = %s
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (transcript, call_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating transcript for callId={call_id}: {e}")
        conn.rollback()
        raise


def update_call_alert_summary(call_id: int, summary: str):
    """Update the alertSummary on a call."""
    conn = get_connection()
    query = """
        UPDATE "calls"
        SET "alertSummary" = %s
        WHERE "callId" = %s
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (summary, call_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating alert summary for callId={call_id}: {e}")
        conn.rollback()
        raise


def get_max_alert_id() -> int:
    """Get the current max alertId, or 0 if table is empty."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COALESCE(MAX("alertId"), 0) FROM "alerts"')
            result = cur.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting max alertId: {e}")
        conn.rollback()
        return 0
