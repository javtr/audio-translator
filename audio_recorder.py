import soundcard as sc
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
import logging

class AudioRecorderThread(QThread):
    finished = pyqtSignal()

    def __init__(self, audio_queue, selected_mic):
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
                    data = data.astype(np.float32).flatten()
                    self.audio_queue.put(data)
        except Exception as e:
            logging.error(f"Error en la grabación de audio: {str(e)}")
        finally:
            logging.info("Grabación finalizada.")
            self.finished.emit()

    def stop(self):
        self.is_recording = False
