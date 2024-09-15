import sys
import soundcard as sc
import numpy as np
import wave
import speech_recognition as sr
from googletrans import Translator
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal

class AudioRecorderThread(QThread):
    finished = pyqtSignal(str, str)

    def __init__(self, speaker):
        super().__init__()
        self.speaker = speaker

    def run(self):
        SAMPLE_RATE = 44100
        RECORD_SECONDS = 10
        OUTPUT_FILENAME = "grabacion_sistema_mono.wav"

        with sc.get_microphone(id=self.speaker.id, include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            data = mic.record(numframes=SAMPLE_RATE * RECORD_SECONDS)

        byte_data = (data * 32767).astype(np.int16).tobytes()

        with wave.open(OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(byte_data)

        r = sr.Recognizer()
        with sr.AudioFile(OUTPUT_FILENAME) as source:
            audio_data = r.record(source)
            try:
                texto = r.recognize_google(audio_data, language='es-ES')
                translator = Translator()
                translated_text = translator.translate(texto, src='es', dest='en')
                self.finished.emit(texto, translated_text.text)
            except Exception as e:
                self.finished.emit(str(e), "")

class AudioTranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.deviceCombo = QComboBox()
        self.speakers = sc.all_speakers()
        for speaker in self.speakers:
            self.deviceCombo.addItem(speaker.name)
        layout.addWidget(self.deviceCombo)

        self.recordButton = QPushButton('Grabar y Traducir')
        self.recordButton.clicked.connect(self.recordAndTranslate)
        layout.addWidget(self.recordButton)

        self.resultText = QTextEdit()
        self.resultText.setReadOnly(True)
        layout.addWidget(self.resultText)

        self.setLayout(layout)
        self.setWindowTitle('Grabador y Traductor de Audio')
        self.setGeometry(300, 300, 400, 300)

    def recordAndTranslate(self):
        self.recordButton.setEnabled(False)
        self.resultText.clear()
        self.resultText.append("Grabando...")
        
        selected_speaker = self.speakers[self.deviceCombo.currentIndex()]
        self.thread = AudioRecorderThread(selected_speaker)
        self.thread.finished.connect(self.onRecordingFinished)
        self.thread.start()

    def onRecordingFinished(self, original, translated):
        self.resultText.clear()
        self.resultText.append(f"Texto original: {original}")
        self.resultText.append(f"Texto traducido: {translated}")
        self.recordButton.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AudioTranslatorApp()
    ex.show()
    sys.exit(app.exec_())