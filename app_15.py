import sys
import soundcard as sc
import numpy as np
import whisper
from googletrans import Translator
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QComboBox, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import queue
import time
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class AudioRecorderThread(QThread):
    finished = pyqtSignal()

    def __init__(self, audio_queue,selected_mic):
        super().__init__()

        self.is_recording = False
        self.audio_queue = audio_queue
        self.selected_mic = selected_mic

    def run(self):
        SAMPLE_RATE = 16000
        CHUNK_DURATION = 10

        self.is_recording = True

        try:
            with sc.get_microphone(id=self.selected_mic.id, include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
                logging.info("Grabación iniciada.")
                while self.is_recording:
                    data = mic.record(numframes=SAMPLE_RATE * CHUNK_DURATION)
                    # Convertir a float32 y asegurarse de que sea un array de una dimensión
                    data = data.astype(np.float32).flatten()
                    self.audio_queue.put(data)
        except Exception as e:
            logging.error(f"Error en la grabación de audio: {str(e)}")
        finally:
            logging.info("Grabación finalizada.")
            self.finished.emit()

    def stop(self):
        self.is_recording = False

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

            self.message_queue.put("Procesando fragmento de audio...")
            logging.info("Iniciando transcripción con Whisper")

            # Asegurarse de que audio_data es float32 y está en el rango correcto
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
                    self.message_queue.put(f"Traduciendo de {self.input_language} a {self.output_language}...")
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

class AudioTranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.is_recording = False
        self.message_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_messages)
        self.timer.start(100)

    def initUI(self):
        layout = QVBoxLayout()

        self.deviceCombo = QComboBox()
        self.speakers = sc.all_speakers()
        for speaker in self.speakers:
            self.deviceCombo.addItem(speaker.name)
        layout.addWidget(QLabel("Seleccione el dispositivo de audio:"))
        layout.addWidget(self.deviceCombo)

        # Añadir selección de idioma de entrada
        self.inputLanguageLabel = QLabel("Seleccione el idioma de entrada:")
        layout.addWidget(self.inputLanguageLabel)
        self.inputLanguageCombo = QComboBox()
        self.inputLanguageCombo.addItem("Español", "es")
        self.inputLanguageCombo.addItem("Inglés", "en")
        self.inputLanguageCombo.addItem("Portugués", "pt")
        layout.addWidget(self.inputLanguageCombo)

        # Añadir selección de idioma de salida
        self.outputLanguageLabel = QLabel("Seleccione el idioma de salida:")
        layout.addWidget(self.outputLanguageLabel)
        self.outputLanguageCombo = QComboBox()
        self.outputLanguageCombo.addItem("Español", "es")
        self.outputLanguageCombo.addItem("Inglés", "en")
        self.outputLanguageCombo.addItem("Portugués", "pt")
        layout.addWidget(self.outputLanguageCombo)

        self.recordButton = QPushButton('Iniciar Grabación')
        self.recordButton.clicked.connect(self.toggleRecording)
        layout.addWidget(self.recordButton)

        self.resultText = QTextEdit()
        self.resultText.setReadOnly(True)
        layout.addWidget(self.resultText)

        self.setLayout(layout)
        self.setWindowTitle('Grabador y Traductor de Audio Multilingüe')
        self.setGeometry(30, 50, 700, 800)

        # Aplicar tema oscuro
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-size: 18px;
            }
            QPushButton {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #565656;
                padding: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #4b4f51;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #565656;
                font-size: 18px;
            }
            QComboBox {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #565656;
                font-size: 14px;
            }
        """)

    def toggleRecording(self):
        if not self.is_recording:
            self.startRecording()
        else:
            self.stopRecording()

    def startRecording(self):
        self.is_recording = True
        self.recordButton.setText('Detener Grabación')
        self.resultText.clear()
        self.resultText.append("Grabando...")

        selected_speaker = self.speakers[self.deviceCombo.currentIndex()]

        input_language = self.inputLanguageCombo.currentData()
        output_language = self.outputLanguageCombo.currentData()

        self.audio_thread = AudioRecorderThread(self.audio_queue,selected_speaker)
        self.audio_thread.start()

        self.processor_thread = AudioProcessorThread(self.audio_queue, self.message_queue, input_language, output_language)
        self.processor_thread.start()

    def stopRecording(self):
        if hasattr(self, 'audio_thread') and self.audio_thread.isRunning():
            self.audio_thread.stop()
            self.recordButton.setEnabled(False)
            self.resultText.append("Finalizando grabación...")

        if hasattr(self, 'processor_thread'):
            self.processor_thread.stop()

        self.onRecordingFinished()

    def check_messages(self):
        while not self.message_queue.empty():
            message = self.message_queue.get()
            self.resultText.append(message)
            logging.info(f"Mensaje en la interfaz: {message}")

    def onRecordingFinished(self):
        self.is_recording = False
        self.recordButton.setText('Iniciar Grabación')
        self.recordButton.setEnabled(True)
        self.resultText.append("Grabación finalizada.")
        logging.info("Grabación finalizada")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AudioTranslatorApp()
    ex.show()
    sys.exit(app.exec_())