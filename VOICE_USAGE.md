# Voice Control for AMAZON AI

## Overview
AMAZON AI sasa inaweza kufanya automation tasks kwa kutumia sauti (voice). Unaweza kuongea na AI, na itakusikiliza, kutoa command, na kufanya kazi kama ulivyoandikia.

## Features
- **Voice Input**: Semta kwa kutumia microphone, AI itasikiliza na kutambua command yako.
- **Voice Output**: AI itajibu kwa sauti (text-to-speech) baada ya kumaliza kazi.
- **Full Automation**: Kila kitu unayoweza kuandika (create file, open app, move folder, etc.) kinaweza kutolewa kwa sauti.

## Requirements
- Python 3.8+
- Libraries:
  - `SpeechRecognition` (for voice input)
  - `pyttsx3` (for voice output)
  - `pyaudio` (required by SpeechRecognition for microphone access)

Install dependencies:
```bash
pip install SpeechRecognition pyttsx3 pyaudio
```

## How to Use

### Starting Voice Mode
1. Fungua AMAZON AI application (`python ui/main.py`).
2. Bofya kitufe cha **🎤 Microphone** kwenye header (juu kulia).
3. Itasikiliza moja kwa moja. Semta command yako kwa sauti.
4. Baada ya kusikiliza, AI itajibu kwa sauti na kutekeleza.

### Example Voice Commands
- "Open Chrome"
- "Create file notes.txt"
- "Move folder projects to documents"
- "Search web python tutorial"
- "List processes"
- "Close notepad"

### Stopping Voice
- Bofya tena kitufe cha 🎤 kusimamisha kusikiliza.
- Itasitisha sauti pia.

## Configuration

### Enable/Disable Voice
```python
from voice import get_voice_engine
engine = get_voice_engine()
engine.set_voice_enabled(True)  # Enable voice output
engine.set_voice_enabled(False)  # Disable voice output
```

### Adjust Voice Properties
```python
engine.tts_engine.setProperty("rate", 160)   # Speed (words per minute)
engine.tts_engine.setProperty("volume", 0.9) # Volume (0.0 to 1.0)
```

## Supported Languages
- Speech recognition: English (default), Swahili (experimental)
- Text-to-speech: English (system default)

## Offline Swahili (No Internet)

AMAZON AI sasa inaweza kutumia STT ya offline kwa Kiswahili kupitia Whisper local.

1. Install package:
```bash
pip install openai-whisper
```

2. Hakikisha `ffmpeg` ipo kwenye system (Whisper inaitumia kusoma audio).

3. Weka language ya voice kuwa Swahili (`sw` au `sw-TZ`).

Mfumo utatumia backend ya `whisper` kwa offline recognition, kisha fallback zingine kama zipo.

## Troubleshooting
- **Microphone not working**: Ensure `pyaudio` is installed and microphone is connected.
- **Voice not speaking**: Check if `pyttsx3` is installed and system has TTS voices.
- **Low accuracy**: Speak clearly, reduce background noise.

## Notes
- Voice mode is **off by default**; activate via the microphone button.
- Commands are processed through the same NLU/automation pipeline as typed text.
- For long responses, only key parts are spoken to avoid excessive speech.