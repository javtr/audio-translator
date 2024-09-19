import sys
import soundcard as sc
import numpy as np
import whisper
from googletrans import Translator
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QGridLayout, QTextEdit, QComboBox, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import queue

class AudioRecorderThread(QThread):
    finished = pyqtSignal()

    def __init__(self, speaker, message_queue, input_language, output_language, model_name):
        super().__init__()
        self.speaker = speaker
        self.is_recording = False
        self.message_queue = message_queue
        self.whisper_model = whisper.load_model(model_name)
        self.input_language = input_language
        self.output_language = output_language
        self.translator = Translator()

    def run(self):
        SAMPLE_RATE = 16000  # Whisper prefers 16kHz
        CHUNK_DURATION = 2  # Duration of each chunk in seconds

        self.is_recording = True
        all_data = []

        with sc.get_microphone(id=self.speaker.id, include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            while self.is_recording:
                data = mic.record(numframes=SAMPLE_RATE * CHUNK_DURATION)
                all_data.append(data)

        if all_data:
            self.process_audio(np.concatenate(all_data))

        self.finished.emit()

    def process_audio(self, data):
        try:
            audio_data = data.flatten().astype(np.float32)
            result = self.whisper_model.transcribe(audio_data, language=self.input_language)
            
            texto_original = result["text"]

            if texto_original.strip():
                if self.output_language != self.input_language:
                    self.message_queue.put("-----------------------------------")
                    translated_text = self.translator.translate(texto_original, src=self.input_language, dest=self.output_language).text
                    self.message_queue.put(f"{translated_text}")
                else:
                    self.message_queue.put("-----------------------------------")
                    self.message_queue.put(f"{texto_original}")

        except Exception as e:
            self.message_queue.put(f"Error: {str(e)}")

    def stop(self):
        self.is_recording = False

class AudioTranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.is_recording = False
        self.message_queue = queue.Queue()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_messages)
        self.timer.start(100)

    def initUI(self):
        layout = QVBoxLayout()

        grid_layout = QGridLayout()

        # Combobox para seleccionar el dispositivo de audio
        self.deviceCombo = QComboBox()
        self.speakers = sc.all_speakers()
        for speaker in self.speakers:
            self.deviceCombo.addItem(speaker.name)
        grid_layout.addWidget(QLabel("Dispositivo:"), 0, 0)
        grid_layout.addWidget(self.deviceCombo, 0, 1)

        # Combobox para seleccionar el idioma de entrada
        self.inputLanguageCombo = QComboBox()
        self.inputLanguageCombo.addItem("Español", "es")
        self.inputLanguageCombo.addItem("Inglés", "en")
        self.inputLanguageCombo.addItem("Portugués", "pt")
        grid_layout.addWidget(QLabel("Audio entrada:"), 1, 0)
        grid_layout.addWidget(self.inputLanguageCombo, 1, 1)

        # Combobox para seleccionar el idioma de salida
        self.outputLanguageCombo = QComboBox()
        self.outputLanguageCombo.addItem("Español", "es")
        self.outputLanguageCombo.addItem("Inglés", "en")
        self.outputLanguageCombo.addItem("Portugués", "pt")
        grid_layout.addWidget(QLabel("Salida texto:"), 0, 2)
        grid_layout.addWidget(self.outputLanguageCombo, 0, 3)

        # Combobox para seleccionar el modelo de Whisper
        self.modelCombo = QComboBox()
        self.modelCombo.addItem("tiny")
        self.modelCombo.addItem("base")
        self.modelCombo.addItem("small")
        self.modelCombo.addItem("medium")
        self.modelCombo.addItem("large")
        grid_layout.addWidget(QLabel("Modelo IA:"), 1, 2)
        grid_layout.addWidget(self.modelCombo, 1, 3)
        

        layout.addLayout(grid_layout)

        # Botón de grabación
        self.recordButton = QPushButton('Iniciar Grabación')
        self.recordButton.clicked.connect(self.toggleRecording)
        layout.addWidget(self.recordButton)

        self.recordButton.setStyleSheet("""
        background-color: #00C7B7;
        color: black;
        """)

        # Text area para mostrar los resultados
        self.resultText = QTextEdit()
        self.resultText.setReadOnly(True)
        layout.addWidget(self.resultText)

        self.setLayout(layout)
        self.setWindowTitle('Grabador y Traductor de Audio Multilingüe')
        self.setGeometry(30, 50, 700, 800)

        # Tema oscuro
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
        self.recordButton.setText('Grabando...')
        self.recordButton.setStyleSheet("""
            background-color: #FB6A75;
            color: black;
        """)

        selected_speaker = self.speakers[self.deviceCombo.currentIndex()]
        input_language = self.inputLanguageCombo.currentData()
        output_language = self.outputLanguageCombo.currentData()
        model_name = self.modelCombo.currentText()
        self.thread = AudioRecorderThread(selected_speaker, self.message_queue, input_language, output_language, model_name)
        self.thread.finished.connect(self.onRecordingFinished)
        self.thread.start()

    def stopRecording(self):
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.stop()
            self.recordButton.setEnabled(False)
            self.recordButton.setText('Procesando...')
            self.recordButton.setStyleSheet("""
                background-color: #F6D852;
                color: black;
            """)
        else:
            self.onRecordingFinished()

    def check_messages(self):
        while not self.message_queue.empty():
            message = self.message_queue.get()
            self.resultText.append(message)

    def onRecordingFinished(self):
        self.is_recording = False
        self.recordButton.setText('Iniciar Grabación')
        self.recordButton.setStyleSheet("""
            background-color: #00C7B7;
            color: black;
        """)
        self.recordButton.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AudioTranslatorApp()
    ex.show()
    sys.exit(app.exec_())
