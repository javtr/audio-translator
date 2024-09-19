import sys
from PyQt5.QtWidgets import QApplication
from ui import AudioTranslatorApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AudioTranslatorApp()
    ex.show()
    sys.exit(app.exec_())
