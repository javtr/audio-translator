import sys
import soundcard as sc
import numpy as np
import wave
import speech_recognition as sr
from googletrans import Translator
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal
import time

class AudioRecorderThread(QThread):
    update = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, speaker):
        super().__init__()
        self.speaker = speaker
        self.is_recording = False

    def run(self):
        SAMPLE_RATE = 44100
        CHUNK_DURATION = 5  # Duración de cada fragmento en segundos
        OUTPUT_FILENAME = "grabacion_sistema_mono.wav"

        self.is_recording = True
        all_data = []

        with sc.get_microphone(id=self.speaker.id, include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            while self.is_recording:
                data = mic.record(numframes=SAMPLE_RATE * CHUNK_DURATION)
                all_data.append(data)
                
                # Procesar el fragmento actual
                self.process_audio(np.concatenate(all_data), SAMPLE_RATE, OUTPUT_FILENAME)

        # Procesar toda la grabación al finalizar
        if all_data:
            self.process_audio(np.concatenate(all_data), SAMPLE_RATE, OUTPUT_FILENAME)
        
        self.finished.emit()

    def process_audio(self, data, SAMPLE_RATE, OUTPUT_FILENAME):
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
                self.update.emit(texto, translated_text.text)
            except Exception as e:
                self.update.emit(str(e), "")

    def stop(self):
        self.is_recording = False

class AudioTranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.is_recording = False

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
        self.setGeometry(300, 300, 400, 300)

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
        self.thread = AudioRecorderThread(selected_speaker)
        self.thread.update.connect(self.onUpdate)
        self.thread.finished.connect(self.onRecordingFinished)
        self.thread.start()

    def stopRecording(self):
        if hasattr(self, 'thread'):
            self.thread.stop()
        self.recordButton.setEnabled(False)
        self.resultText.append("Finalizando grabación...")

    def onUpdate(self, original, translated):
        self.resultText.append(f"Texto original: {original}")
        self.resultText.append(f"Texto traducido: {translated}")
        self.resultText.append("------------------------")

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