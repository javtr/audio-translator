import soundcard as sc
import numpy as np
import wave
import speech_recognition as sr
from googletrans import Translator

# Parámetros de configuración de la grabación
SAMPLE_RATE = 44100
RECORD_SECONDS = 5
OUTPUT_FILENAME = "grabacion_sistema_mono.wav"

print("Dispositivos de salida disponibles:")
speakers = sc.all_speakers()
for i, speaker in enumerate(speakers):
    print(f"{i}: {speaker.name}")

# Seleccionar los parlantes (puedes cambiar el índice si es necesario)
selected_speaker = speakers[2]
print(f"Grabando audio del sistema desde {selected_speaker.name}...")
print("Grabando...")

# Grabar audio (forzando mono)
with sc.get_microphone(id=selected_speaker.id, include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
    data = mic.record(numframes=SAMPLE_RATE * RECORD_SECONDS)

print("Grabación completa.")

# Convertir el numpy array a bytes
byte_data = (data * 32767).astype(np.int16).tobytes()

# Guardar la grabación en un archivo WAV
with wave.open(OUTPUT_FILENAME, 'wb') as wf:
    wf.setnchannels(1)  # Mono
    wf.setsampwidth(2)  # 2 bytes por muestra
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(byte_data)

print(f"Grabación guardada como {OUTPUT_FILENAME}")

# Convertir el archivo de audio a texto con SpeechRecognition
r = sr.Recognizer()

with sr.AudioFile(OUTPUT_FILENAME) as source:
    audio_data = r.record(source)
    print("Reconociendo el texto del audio...")
    try:
        texto = r.recognize_google(audio_data, language='es-ES')  # Español
        print(f"Texto transcrito: {texto}")
       
        # Traducir el texto a otro idioma (por ejemplo, inglés)
        translator = Translator()
        translated_text = translator.translate(texto, src='es', dest='en')
        print(f"Texto traducido: {translated_text.text}")
    except sr.UnknownValueError:
        print("No se pudo entender el audio. Asegúrate de que haya sonido durante la grabación.")
    except sr.RequestError:
        print("Error en el servicio de reconocimiento de voz.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {str(e)}")