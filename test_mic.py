import speech_recognition as sr

print("Available microphones:")
mic_list = sr.Microphone.list_microphone_names()
for i, name in enumerate(mic_list):
    print(f"Device {i}: {name}")

print("\nTesting which microphone works...")
working_index = None

for i, name in enumerate(mic_list):
    try:
        with sr.Microphone(device_index=i) as source:
            print(f"[SUCCESS] Device {i} ('{name}') initialized successfully!")
            working_index = i
            break
    except Exception as e:
        print(f"[FAILED] Device {i} ('{name}'): {e}")

if working_index is not None:
    print(f"\nResult: We can fix jarvis.py by setting device_index={working_index}")
else:
    print("\nResult: All microphones failed. The issue is likely Windows Privacy Settings or missing hardware.")
