import queue
import soundcard as sc
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QTextEdit, QComboBox, QLabel
from PyQt5.QtCore import QTimer
from audio_recorder import AudioRecorderThread
from audio_processor import AudioProcessorThread
import logging

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

        self.inputLanguageCombo = QComboBox()
        self.inputLanguageCombo.addItem("Español", "es")
        self.inputLanguageCombo.addItem("Inglés", "en")
        self.inputLanguageCombo.addItem("Portugués", "pt")
        layout.addWidget(QLabel("Seleccione el idioma de entrada:"))
        layout.addWidget(self.inputLanguageCombo)

        self.outputLanguageCombo = QComboBox()
        self.outputLanguageCombo.addItem("Español", "es")
        self.outputLanguageCombo.addItem("Inglés", "en")
        self.outputLanguageCombo.addItem("Portugués", "pt")
        layout.addWidget(QLabel("Seleccione el idioma de salida:"))
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

        self.audio_thread = AudioRecorderThread(self.audio_queue, selected_speaker)
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
