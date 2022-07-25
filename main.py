import sys
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide2.QtCore import QFile

import numpy as np
from scipy.io.wavfile import read
from scipy.io.wavfile import write
import sounddevice as sd


class MainWindow():
    fileName = ""
    playing = False
    stream = None
    fs = 0
    x = None

    def __init__(self):
        ui_file_name = "ui_files/mainwindow.ui"
        ui_file = QFile(ui_file_name)
        loader = QUiLoader()
        self.win = loader.load(ui_file)
        ui_file.close()
        self.win.pushButton.pressed.connect(self.play)
        self.win.menuFile.triggered.connect(self.menuFileEvent)
        self.win.menuHelp.triggered.connect(self.menuAboutEvent)
        self.win.show()

    def menuAboutEvent(self):
        QMessageBox.about(None,"PFE Autotune","Napravio Aleksandar Rašković za vreme prolećne online PFE radionice")
    def menuFileEvent(self,args):
        val = args.text()
        if val == 'Open':
            self.fileName = QFileDialog.getOpenFileName(None,"Open Image", "./", "Audio Files (*.wav)")[0]
            self.fs,self.x = read(self.fileName)
        if val == 'Export':
            write("output.wav",self.fs,self.x)
        if val == 'Close':
            self.fileName = ""
            self.fs = 0
            self.x = None
        elif val == 'Exit':
            QApplication.quit()

    def play(self):
        self.playing = not self.playing
        if not self.playing:
            self.win.pushButton.setText("Play")
            sd.stop()
        else:
            self.win.pushButton.setText("Pause")
            sd.play(self.x, self.fs)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.win.show()

    sys.exit(app.exec_())