"""Minimal standalone voice test to isolate mic/recognition issues."""
import time
import speech_recognition as sr

print("SpeechRecognition imported ok")
r = sr.Recognizer()
print("Recognizer created")

try:
    mic = sr.Microphone()
    print("Microphone object created")
except Exception as e:
    print("Microphone init failed:", e)
    raise SystemExit(1)

with mic as source:
    print("Adjusting for ambient noise...")
    r.adjust_for_ambient_noise(source, duration=1)
    print("Speak now...")
    try:
        audio = r.listen(source, timeout=10, phrase_time_limit=8)
        print("Audio captured")
    except Exception as e:
        print("Listen failed:", e)
        raise SystemExit(1)

print("Recognizing...")
try:
    text = r.recognize_google(audio, language="en-US")
    print("Recognized:", text)
except sr.UnknownValueError:
    print("Could not understand audio")
except sr.RequestError as e:
    print("Google recognition error:", e)
except Exception as e:
    print("Recognition unexpected error:", e)