# Jarvis Voice Assistant

A full-featured voice assistant for your PC — Jarvis. Understands **Hinglish** and **English**, runs in voice-only or with a system tray and type-to-chat GUI.

---

## Features

- **Voice input** — Google Speech Recognition; human-like listening (tolerant of pauses, works with earbuds)
- **Optional enhanced audio** — Far-field, noise suppression, AGC, VAD (run with `--enhanced`)
- **Smart Brain personality** — Calm, respectful, context-aware Jarvis who thinks before replying and talks in polite “Sir” tone (Hindi + English mix)
- **Apps** — Open/close applications by name (Chrome, Excel, Teams, etc.)
- **Web** — Open websites (Gmail, YouTube, Zmail, RID, TradingView, etc.) and close specific tabs (“close rid tab”, “close youtube tab”)
- **Microsoft Teams** — “Ping chandra.nahata” → focus Teams, open search (Ctrl+E), type the user, open chat
- **Outlook** — Search mail by person, unread summary, folder check
- **Reminders** — Set, list, and delete reminders (“mere liye koi reminder hai?”, “7 baje yaad dilana meeting”)
- **Active window** — “Abhi kya open hai?” → tells you which app/window is in focus
- **Todo** — Add tasks, list, mark complete
- **Info** — Time, date, weather, news, battery, system usage, internet speed
- **Media** — Volume, play favourite song, YouTube search
- **Other** — Jokes, calculator, screenshots, WiFi password, stock price, maps, help
- **IQ quiz** — Short, fun IQ-style quiz with score + estimated IQ range
- **AI fallback** — Unrecognized commands get a sensible reply
- **Auto-learning** — Learns from your usage; ML intent model trains from `intents.json`

---

## Requirements

- **Python 3.8+**
- **Windows** (uses `win32gui`, `pywin32` for window/process control)
- Microphone (and optionally speakers/earbuds)

---

## Installation

```bash
# Clone or download the project, then:
cd Jarvis_20-12-25
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Optional (enhanced audio):**  
`pip install scipy webrtcvad`

**Optional (NLP):**  
`python -m spacy download en_core_web_sm`

---

## Usage

| Command | Description |
|--------|-------------|
| `python main.py` | **Default.** System tray + Type-to-Jarvis GUI + voice |
| `python main.py --voice-only` or `-v` | Voice-only mode (no GUI) |
| `python main.py --enhanced` | Professional audio (far-field, noise suppression) |
| `python main.py --debug` or `-d` | Enable debug output |

---

## Example commands (Hinglish / English)

- **Apps:** “Chrome kholo”, “open Excel”, “close rid tab”
- **Teams:** “ping chandra.nahata”, “teams john chat”
- **Reminders:** “mere liye koi reminder hai?”, “7 baje yaad dilana meeting”
- **Focus:** “abhi kya open hai?”, “which window is focused”
- **Mail:** “Rahul ka mail dikhao”, “unread mail”
- **Todo:** “todo dikhao”, “add task buy milk”
- **Info:** “kitne baje”, “aaj ki tarikh”, “battery”, “news”
- **IQ quiz:** “take iq test”, “iq quiz khelo”, “mera iq batao”

---

## Project structure

```
Jarvis_20-12-25/
├── main.py                 # Default entry point (tray + Type-to-Jarvis GUI + voice)
│
├── core/
│   ├── async_listener.py       # Voice input (human-like pauses, earbuds-friendly)
│   ├── enhanced_listener.py    # Optional: far-field, noise suppression, VAD
│   ├── speaker_async.py        # Text-to-speech
│   ├── translator.py           # Hindi ↔ English
│   ├── intent_detector.py      # Orchestrates rules + patterns + ML
│   ├── intent_rules.py         # Rule-based intents (high priority)
│   ├── intent_patterns.py      # Pattern-based intents
│   ├── intent_ml.py            # ML intent model
│   ├── context_manager.py      # Memory, active window, entities
│   ├── context_resolver.py     # Pronouns, “isko close karo”, etc.
│   ├── command_router.py       # Routes intents to skills
│   ├── application_control.py  # Open/close apps (static + dynamic index)
│   ├── app_launcher.py         # Fuzzy app launch from index
│   ├── window_manager.py      # Focus/restore window
│   ├── ai_fallback.py          # Fallback replies, knowledge
│   └── nlp.py                  # Entities (spaCy)
│
├── skills/
│   ├── teams_control.py        # Teams: ping user, open chat (Ctrl+E)
│   ├── chrome_control.py       # Close tab by site (rid, youtube, etc.)
│   ├── web_launcher.py         # Open URLs (WEBSITES / URLS)
│   ├── reminder.py             # Set, list, delete reminders
│   ├── outlook.py              # Mail search, inbox, folders
│   ├── todo.py                 # Tasks
│   ├── info.py                 # Time, date, weather, news, battery
│   ├── volume_control.py       # Volume up/down, mute
│   ├── play_favourite.py       # Favourite song
│   ├── youtube.py              # YouTube search
│   ├── system_control.py       # Lock, shutdown, restart, etc.
│   ├── iq_quiz.py              # Short IQ-style quiz (score + estimated IQ range)
│   └── ...                     # calculator, jokes, screenshot, wifi, etc.
│
├── desktop_overlay/
│   ├── tray.py                 # System tray icon and menu
│   └── type_to_jarvis.py       # GUI: type commands to Jarvis
│
├── config/
│   ├── settings.py              # listen_timeout, language, API keys placeholders
│   └── prompts.py
│
├── data/
│   ├── intents.json             # Intent phrases (ML training)
│   ├── responses.json           # Spoken responses
│   ├── reminders.json           # Reminder storage
│   └── app_index.json            # Installed apps (built by app_indexer)
│
├── requirements.txt
└── README.md
```

---

## Configuration

Edit **`config/settings.py`**:

- `listen_timeout` — Seconds to wait for a voice command (default `7`)
- `language` — Default language
- `weather_api_key` — OpenWeatherMap key for weather
- `city` — Default city for weather
- `rss_feed_url` — For news headlines

---

## License

Use and modify as needed for your project.
