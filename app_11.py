import sys
import soundcard as sc
import numpy as np
import whisper
from googletrans import Translator
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QComboBox, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import queue

class AudioRecorderThread(QThread):
    finished = pyqtSignal()

    def __init__(self, speaker, message_queue, input_language, output_language):
        super().__init__()
        self.speaker = speaker
        self.is_recording = False
        self.message_queue = message_queue
        self.whisper_model = whisper.load_model("medium").cpu()
        self.input_language = input_language
        self.output_language = output_language

    def run(self):
        SAMPLE_RATE = 16000  # Whisper prefers 16kHz
        CHUNK_DURATION = 2  # Duration of each chunk in seconds

        self.is_recording = True
        all_data = []

        with sc.get_microphone(id=self.speaker.id, include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            while self.is_recording:
                data = mic.record(numframes=SAMPLE_RATE * CHUNK_DURATION)
                all_data.append(data)

        # Process all audio when finished
        if all_data:
            self.process_audio(np.concatenate(all_data))

        self.finished.emit()

    def process_audio(self, data):
        self.message_queue.put("Procesando audio...")

        try:
            self.message_queue.put(f"Reconociendo voz en {self.input_language} con Whisper...")
            
            # Ensure data is in the correct format for Whisper
            audio_data = data.flatten().astype(np.float32)
            
            # Use Whisper for speech recognition
            result = self.whisper_model.transcribe(audio_data, language=self.input_language)
            texto_original = result["text"]

            if texto_original.strip():
                translator = Translator()
                self.message_queue.put(f"Traduciendo texto de {self.input_language} a {self.output_language}...")
                translated_text = translator.translate(texto_original, src=self.input_language, dest=self.output_language)

                self.message_queue.put(f"Texto original ({self.input_language}): {texto_original}")
                self.message_queue.put(f"Texto traducido ({self.output_language}): {translated_text.text}")

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

        self.deviceCombo = QComboBox()
        self.speakers = sc.all_speakers()
        for speaker in self.speakers:
            self.deviceCombo.addItem(speaker.name)
        layout.addWidget(QLabel("Seleccione el dispositivo de audio:"))
        layout.addWidget(self.deviceCombo)

        # Add input language selection
        self.inputLanguageLabel = QLabel("Seleccione el idioma de entrada:")
        layout.addWidget(self.inputLanguageLabel)
        self.inputLanguageCombo = QComboBox()
        self.inputLanguageCombo.addItem("Español", "es")
        self.inputLanguageCombo.addItem("Inglés", "en")
        self.inputLanguageCombo.addItem("Portugués", "pt")
        layout.addWidget(self.inputLanguageCombo)

        # Add output language selection
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

        # Aplicando tema oscuro
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
        self.thread = AudioRecorderThread(selected_speaker, self.message_queue, input_language, output_language)
        self.thread.finished.connect(self.onRecordingFinished)
        self.thread.start()

    def stopRecording(self):
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.stop()
            self.recordButton.setEnabled(False)
            self.resultText.append("Finalizando grabación...")
        else:
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