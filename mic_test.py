import speech_recognition as sr

r = sr.Recognizer()
names = sr.Microphone.list_microphone_names()

print("=== MICS ===")
for i, n in enumerate(names):
    print(i, n)

print("\n=== TEST OPEN ===")
ok = []
for i in range(len(names)):
    try:
        m = sr.Microphone(device_index=i)
        with m as source:
            r.adjust_for_ambient_noise(source, duration=0.2)
        print(f"OK: {i} -> {names[i]}")
        ok.append(i)
    except Exception as e:
        pass

print("\nWorking indexes:", ok)
