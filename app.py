import pyaudio
import wave
import speech_recognition as sr
from googletrans import Translator

# Parámetros de configuración de la grabación
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5
OUTPUT_FILENAME = "grabacion.wav"
MIC_INDEX = 2  # Índice del micrófono (cambiar según el dispositivo)

# Inicializar PyAudio
p = pyaudio.PyAudio()

# Mostrar los dispositivos disponibles
# print("Dispositivos disponibles:")
# for i in range(p.get_device_count()):
#     info = p.get_device_info_by_index(i)
#     print(f"Device {i}: {info['name']}")

# Abrir el flujo de audio usando el índice del micrófono
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=MIC_INDEX,  # Usar el micrófono o dispositivo de audio en el índice
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

# Guardar la grabación en un archivo WAV
wf = wave.open(OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print(f"Grabación guardada como {OUTPUT_FILENAME}")

# Convertir el archivo de audio a texto con SpeechRecognition
r = sr.Recognizer()

with sr.AudioFile(OUTPUT_FILENAME) as source:
    audio_data = r.record(source)
    print("Reconociendo el texto del audio...")
    try:
        texto = r.recognize_google(audio_data, language='es-ES')  # Español
        print(f"Texto transcrito: {texto}")
    except sr.UnknownValueError:
        print("No se pudo entender el audio.")
    except sr.RequestError:
        print("Error en el servicio de reconocimiento de voz.")

# Traducir el texto a otro idioma (por ejemplo, inglés)
translator = Translator()
translated_text = translator.translate(texto, src='es', dest='en')

print(f"Texto traducido: {translated_text.text}")
