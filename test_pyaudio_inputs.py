"""Print real audio input devices with PyAudio using safe key access."""
import pyaudio
p = pyaudio.PyAudio()
print("Host APIs:", p.get_host_api_count())
for i in range(p.get_host_api_count()):
    info = p.get_host_api_info_by_index(i)
    print("API", i, info.get('name'))
print("Devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(i, info.get('name'), "inputs=", info.get('maxInputChannels'), "outputs=", info.get('maxOutputChannels'))
p.terminate()