import sys
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide2.QtCore import QFile, QIODevice

import numpy as np
from scipy.io import wavfile
import scipy.fft as fft
import scipy.signal as signal

fileName = ""
fs,x = (0,np.zeros(1))

def menuFileEvent(args):
    val = args.text()
    if val == 'Open':
        global fileName
        global window
        fileName = QFileDialog.getOpenFileName(None,"Open Image", "./", "Audio Files (*.wav)")[0]
        global fs,x 
        fs,x = wavfile.read(fileName)
        
    if val == 'Close':
        fileName = ""
    elif val == 'Exit':
        QApplication.quit()

def menuAboutEvent():
    QMessageBox.about(None,"PFE Autotune","Napravio Aleksandar Rašković za vreme prolećne online radionice")

def play():
    print(fs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    

    global window
    ui_file_name = "ui_files/mainwindow.ui"
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)
    loader = QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()
    if not window:
        print(loader.errorString())
        sys.exit(-1)
    window.pushButton.pressed.connect(play)
    window.menuFile.triggered.connect(menuFileEvent)
    window.menuHelp.triggered.connect(menuAboutEvent)
    window.show()
    
    sys.exit(app.exec_())