"""Simple voice verification test that confirms SpeechRecognition capture and recognition are working before adding UI integration complexity."""
import time
import speech_recognition as sr

print("1) Import: OK")
r = sr.Recognizer()
print("2) Recognizer: OK")
mic = sr.Microphone()
print("3) Microphone: OK")
with mic as source:
    print("4) Calibrating...")
    r.adjust_for_ambient_noise(source, duration=1)
    print("5) Speak now, then wait...")
    try:
        audio = r.listen(source, timeout=12, phrase_time_limit=12)
        print("6) Audio captured")
    except Exception as e:
        print("Listen error:", e)
        raise SystemExit(1)
print("7) Recognizing...")
try:
    text = r.recognize_google(audio, language="en-US")
    print("8) Recognized:", text)
except sr.UnknownValueError:
    print("8) Could not understand audio")
except Exception as e:
    print("8) Recognition error:", e)