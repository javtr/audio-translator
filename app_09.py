import sys
import soundcard as sc
import numpy as np
import whisper
from googletrans import Translator
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import queue

class AudioRecorderThread(QThread):
    def __init__(self, speaker, message_queue):
        super().__init__()
        self.speaker = speaker
        self.is_recording = False
        self.message_queue = message_queue
        self.whisper_model = whisper.load_model("base").cpu()

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

    def process_audio(self, data):
        self.message_queue.put("Procesando audio...")

        try:
            self.message_queue.put("Reconociendo voz con Whisper...")
            
            # Ensure data is in the correct format for Whisper
            audio_data = data.flatten().astype(np.float32)
            
            # Use Whisper for speech recognition
            result = self.whisper_model.transcribe(audio_data, language="es")
            texto = result["text"]

            if texto.strip():
                translator = Translator()
                self.message_queue.put("Traduciendo texto...")
                translated_text = translator.translate(texto, src='es', dest='es')

                self.message_queue.put(f"Texto original: {texto}")
                self.message_queue.put(f"Texto traducido: {translated_text.text}")

        except Exception as e:
            self.message_queue.put(f"Error: {str(e)}")

    def stop(self):
        self.is_recording = False


class AudioTranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.is_recording = False
        self.message_queue = queue.Queue()  # Crear la cola de mensajes

        # Usar un temporizador para verificar la cola
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_messages)
        self.timer.start(100)  # Verificar la cola cada 100 ms

    def initUI(self):
        layout = QVBoxLayout()

        self.deviceCombo = QComboBox()
        self.speakers = sc.all_speakers()
        for speaker in self.speakers:
            self.deviceCombo.addItem(speaker.name)
        layout.addWidget(self.deviceCombo)

        self.recordButton = QPushButton('Iniciar Grabación')
        self.recordButton.clicked.connect(self.toggleRecording)
        layout.addWidget(self.recordButton)

        self.resultText = QTextEdit()
        self.resultText.setReadOnly(True)
        layout.addWidget(self.resultText)

        self.setLayout(layout)
        self.setWindowTitle('Grabador y Traductor de Audio Continuo')
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
        self.thread = AudioRecorderThread(selected_speaker, self.message_queue)
        self.thread.start()

    def stopRecording(self):
        if hasattr(self, 'thread'):
            self.thread.stop()
        self.recordButton.setEnabled(False)
        self.resultText.append("Finalizando grabación...")

    def check_messages(self):
        # Verificar si hay mensajes en la cola y mostrarlos en la interfaz
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
