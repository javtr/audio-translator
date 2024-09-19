import sys
import soundcard as sc
import numpy as np
import whisper
from googletrans import Translator
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QComboBox, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import queue
import threading

class AudioRecorderThread(QThread):
    finished = pyqtSignal()

    def __init__(self, speaker, audio_queue):
        super().__init__()
        self.speaker = speaker
        self.is_recording = False
        self.audio_queue = audio_queue

    def run(self):
        SAMPLE_RATE = 16000  # Whisper prefiere 16kHz
        CHUNK_DURATION = 15  # Procesar cada 5 segundos de audio

        self.is_recording = True

        with sc.get_microphone(id=self.speaker.id, include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            while self.is_recording:
                data = mic.record(numframes=SAMPLE_RATE * CHUNK_DURATION)
                self.audio_queue.put(data.flatten().astype(np.float32))  # Enviar fragmento de audio al buffer

        self.finished.emit()

    def stop(self):
        self.is_recording = False

class AudioProcessorThread(QThread):
    def __init__(self, audio_queue, message_queue, input_language, output_language):
        super().__init__()
        self.audio_queue = audio_queue
        self.message_queue = message_queue
        self.whisper_model = whisper.load_model("base").to("cuda")
        self.input_language = input_language
        self.output_language = output_language
        self.translator = Translator()
        self.is_processing = True

    def run(self):
        while self.is_processing:
            if not self.audio_queue.empty():
                audio_data = self.audio_queue.get()
                self.process_audio(audio_data)

    def process_audio(self, audio_data):
        try:
            self.message_queue.put("Procesando fragmento de audio...")

            # Usar Whisper para transcripción
            result = self.whisper_model.transcribe(
                audio_data, 
                language=self.input_language
            )
            texto_original = result["text"]

            if texto_original.strip():
                self.message_queue.put(f"Texto original ({self.input_language}): {texto_original}")

                if self.output_language != self.input_language:
                    self.message_queue.put(f"Traduciendo de {self.input_language} a {self.output_language}...")
                    translated_text = self.translator.translate(texto_original, src=self.input_language, dest=self.output_language).text
                    self.message_queue.put(f"Texto traducido ({self.output_language}): {translated_text}")
                else:
                    self.message_queue.put("No se requiere traducción.")
        except Exception as e:
            self.message_queue.put(f"Error: {str(e)}")

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

        # Iniciar el hilo de grabación de audio
        self.audio_thread = AudioRecorderThread(selected_speaker, self.audio_queue)
        self.audio_thread.start()

        # Iniciar el hilo de procesamiento de audio
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

    def onRecordingFinished(self):
        self.is_recording = False
        self.recordButton.setText('Iniciar Grabación')
        self.recordButton.setEnabled(True)
        self.resultText.append("Grabación finalizada.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AudioTranslatorApp()
    ex.show()
    sys.exit(app.exec_())
