# TLR to Discord

A Windows CLI tool that monitors a Postgres database for dispatch alerts, transcribes radio audio, and sends formatted notifications to Discord.

Built for Indiana law enforcement and fire dispatch systems using Trunk Recorder / Rdio Scanner.

## Output Format

Each alert is formatted as:

```
DELAWARE COUNTY | 5000 BLK N NEVADO RD (MT OLIVE CHURCH) | Vehicle Crash - Injury | ENGINE 92, RESCUE 93, EVAC 61, and SQUAD 11 responding to an injury crash at Mount Olive Church.
```

- **County** — Detected from talkgroup, system label, or transcript
- **Address** — Abbreviated block format with landmark if available
- **Incident Type** — Classified using Indiana 10-codes and keyword detection
- **Summary** — AI-generated summary of the dispatch (powered by Ollama + Llama 3.2)

Alerts are sent to Discord as a plain text line plus a color-coded embed.

## Features

- Polls the `alerts` table every 60 seconds for new entries
- Uses existing transcripts from the database when available
- Falls back to a Whisper-compatible transcription API for untranscribed audio
- AI-powered summarization via Ollama (Llama 3.2 3B recommended)
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
- Ollama instance with a model for summarization

## Ollama Setup (Summarization)

The script uses an Ollama instance to generate clean summaries from raw radio transcripts. This is a **separate service** from your Whisper transcription endpoint.

1. Install Ollama on your GPU server: https://ollama.com

2. Pull the recommended model:

```
ollama pull llama3.2:3b
```

3. Start the Ollama server:

```
ollama serve
```

Ollama runs on port `11434` by default and provides an OpenAI-compatible API at `/v1/chat/completions`.

4. Expose it via Cloudflare tunnel, ngrok, or direct IP so your Windows machine can reach it:

```
cloudflared tunnel --url http://localhost:11434
```

5. Add the URL to your `.env`:

```
LLM_URL=https://your-ollama-tunnel-url/v1/chat/completions
LLM_MODEL=llama3.2:3b
```

**Why Llama 3.2 3B?** It's small enough to run fast on modest GPUs, but smart enough to clean up messy radio transcripts into readable summaries. You don't need a 70B model for 1-2 sentence summaries.

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
TRANSCRIPTION_URL=https://your-whisper-url/v1/audio/transcriptions
LLM_URL=https://your-ollama-url/v1/chat/completions
LLM_MODEL=llama3.2:3b
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
| `LLM_URL` | Ollama API endpoint for summarization |
| `LLM_MODEL` | Ollama model name (default: llama3.2:3b) |
| `POLL_INTERVAL` | Polling interval in seconds (default: 60) |
| `STATE_FILE` | Path to state file (default: ./state.json) |

## Project Structure

```
├── main.py              # Entry point and polling loop
├── config.py            # Loads settings from .env
├── db.py                # PostgreSQL queries
├── transcribe.py        # Audio transcription via Whisper API
├── parser.py            # Transcript parsing, classification, and AI summarization
├── discord_notify.py    # Discord webhook integration
├── ten_codes.py         # Indiana 10-codes and signal codes
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
└── .gitignore           # Excludes .env and state.json
```

## License

MIT
