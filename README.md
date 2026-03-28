# TLR to Discord

A Windows CLI tool that monitors a Postgres database for dispatch alerts, transcribes radio audio, and sends formatted notifications to Discord.

Built for Indiana law enforcement and fire dispatch systems using Trunk Recorder / Rdio Scanner.

## Output Format

Each alert is formatted as:

```
DELAWARE COUNTY | 5000 BLK N NEVADO RD (MT OLIVE CHURCH) | Vehicle Crash - Injury | ENGINE 92, RESCUE 93, EVAC 61, SQUAD 11 responding to an injury crash on Rural Fire Ground 1
```

- **County** — Detected from talkgroup, system label, or transcript
- **Address** — Abbreviated block format with landmark if available
- **Incident Type** — Classified using Indiana 10-codes and keyword detection
- **Summary** — Responding units, incident description, and channel

Alerts are sent to Discord as a plain text line plus a color-coded embed.

## Features

- Polls the `alerts` table every 60 seconds for new entries
- Uses existing transcripts from the database when available
- Falls back to a Whisper-compatible transcription API for untranscribed audio
- Parses Indiana 10-codes (10-0 through 10-100) and signal codes
- Deduplicates alerts (same call won't post twice)
- Suppresses pager tests and disregard tones
- Persists state across restarts via `state.json`

## Requirements

- Windows 10/11
- Python 3.10+
- PostgreSQL database (Rdio Scanner / Trunk Recorder schema)
- Discord webhook URL
- Whisper-compatible transcription API endpoint

## Installation

1. Clone the repo:

```
git clone https://github.com/officialbones/TLR-to-Discord.git
cd TLR-to-Discord
```

2. Install Python dependencies:

```
pip install -r requirements.txt
```

3. Copy the example config and fill in your values:

```
copy .env.example .env
```

4. Edit `.env` with your settings:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASS=your_db_password
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
TRANSCRIPTION_URL=https://your-whisper-api/v1/audio/transcriptions
```

All fields are required. The script will exit with an error if any are missing.

## Usage

```
python main.py
```

The script runs continuously, polling every 60 seconds. Press `Ctrl+C` to stop.

On first run it starts from the latest alert in the database so it won't reprocess old alerts.

## Configuration

All configuration is done through the `.env` file:

| Variable | Description |
|---|---|
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASS` | Database password |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL |
| `TRANSCRIPTION_URL` | Whisper-compatible API endpoint |
| `POLL_INTERVAL` | Polling interval in seconds (default: 60) |
| `STATE_FILE` | Path to state file (default: ./state.json) |

## Project Structure

```
├── main.py              # Entry point and polling loop
├── config.py            # Loads settings from .env
├── db.py                # PostgreSQL queries
├── transcribe.py        # Audio transcription via Whisper API
├── parser.py            # Transcript parsing and formatting
├── discord_notify.py    # Discord webhook integration
├── ten_codes.py         # Indiana 10-codes and signal codes
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
└── .gitignore           # Excludes .env and state.json
```

## License

MIT
