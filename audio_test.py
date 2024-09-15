import pyaudio
import wave

# Parámetros de configuración de la grabación
FORMAT = pyaudio.paInt16  # Formato de los datos de audio
CHANNELS = 1              # Número de canales (1 para mono)
RATE = 44100              # Tasa de muestreo (en Hz)
CHUNK = 1024              # Tamaño de cada bloque de audio
RECORD_SECONDS = 5        # Duración de la grabación en segundos
OUTPUT_FILENAME = "grabacion.wav"  # Nombre del archivo de salida

# Inicializar PyAudio
p = pyaudio.PyAudio()

# Mostrar los dispositivos disponibles
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"Device {i}: {info['name']}")

# Abrir el flujo de audio
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=0,
                frames_per_buffer=CHUNK)

print("Grabando...")

frames = []

# Grabando por el tiempo especificado
for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("Grabación completa.")

# Detener y cerrar el flujo de audio
stream.stop_stream()
stream.close()
p.terminate()

# Guardar los datos grabados en un archivo WAV
wf = wave.open(OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print(f"Grabación guardada como {OUTPUT_FILENAME}")
