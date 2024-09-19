import whisper
import numpy as np
from googletrans import Translator
from PyQt5.QtCore import QThread
import time
import queue
import logging

class AudioProcessorThread(QThread):
    def __init__(self, audio_queue, message_queue, input_language, output_language):
        super().__init__()
        self.audio_queue = audio_queue
        self.message_queue = message_queue
        self.whisper_model = whisper.load_model("tiny")
        self.input_language = input_language
        self.output_language = output_language
        self.translator = Translator()
        self.is_processing = True
        self.last_processed_time = 0

    def run(self):
        while self.is_processing:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                self.process_audio(audio_data)
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error en el hilo de procesamiento: {str(e)}")
                self.message_queue.put(f"Error en el hilo de procesamiento: {str(e)}")

    def process_audio(self, audio_data):
        try:
            current_time = time.time()
            if current_time - self.last_processed_time < 1:
                return
            self.last_processed_time = current_time

            # self.message_queue.put("Procesando fragmento de audio...")
            # logging.info("Iniciando transcripción con Whisper")

            audio_data = np.clip(audio_data, -1, 1)
            result = self.whisper_model.transcribe(
                audio_data, 
                language=self.input_language,
                fp16=False
            )
            texto_original = result["text"]

            logging.info(f"Transcripción completada: {texto_original}")

            if texto_original.strip():
                self.message_queue.put(f"Texto original ({self.input_language}): {texto_original}")

                if self.output_language != self.input_language:
                    logging.info(f"Traduciendo de {self.input_language} a {self.output_language}")
                    # self.message_queue.put(f"Traduciendo de {self.input_language} a {self.output_language}...")
                    translated_text = self.translator.translate(texto_original, src=self.input_language, dest=self.output_language).text
                    self.message_queue.put(f"Texto traducido ({self.output_language}): {translated_text}")
                    logging.info(f"Traducción completada: {translated_text}")
                else:
                    self.message_queue.put("No se requiere traducción.")
            else:
                logging.warning("No se detectó texto en el fragmento de audio")
                self.message_queue.put("No se detectó texto en este fragmento de audio.")
        except Exception as e:
            logging.error(f"Error en el procesamiento de audio: {str(e)}")
            self.message_queue.put(f"Error en el procesamiento de audio: {str(e)}")

    def stop(self):
        self.is_processing = False
