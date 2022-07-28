import sys
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication,QFileDialog,QMessageBox,QProgressDialog
from PySide2.QtCore import QFile

import numpy as np
from scipy.io.wavfile import read
from scipy.io.wavfile import write
from scipy.fft import *
from scipy.signal import stft, hanning
import sounddevice as sd

#Debug imports
import matplotlib.pyplot as plt

class MainWindow():
    fileName = ""
    playing = False
    stream = None
    fs = 0
    x = None

    baseFreqs = []

    # Class init
    def __init__(self):
        ui_file_name = "ui_files/mainwindow.ui"
        ui_file = QFile(ui_file_name)
        loader = QUiLoader()
        self.win = loader.load(ui_file)
        ui_file.close()
        self.win.pushButton.pressed.connect(self.play)
        self.win.menuFile.triggered.connect(self.menuFileEvent)
        self.win.menuHelp.triggered.connect(self.menuAboutEvent)

    # Qt Slots
    def menuAboutEvent(self):
        QMessageBox.about(None,"PFE Autotune","Napravio Aleksandar Rašković za vreme prolećne online PFE radionice")
    def menuFileEvent(self,args):
        val = args.text()
        if val == 'Open':
            self.openFile()
        if val == 'Export':
            self.exportFile()
        if val == 'Close':
            self.closeFile()
        elif val == 'Exit':
            QApplication.quit()


    # Audio functions connected to UI
    def play(self):
        self.playing = not self.playing
        if not self.playing:
            self.win.pushButton.setText("Play")
            sd.stop()
        else:
            self.win.pushButton.setText("Pause")
            
            sd.play(self.x,self.fs*2)
    
    def openFile(self):
        self.closeFile()
        
        self.fileName = QFileDialog.getOpenFileName(None,"Open Image", "./", "Audio Files (*.wav)")[0]
        self.fs,self.x = read(self.fileName)

        startpoint = 0
        window = int(self.fs/100)
        xf = rfftfreq(len(self.x[startpoint:startpoint+window]), 1/self.fs)
        self.baseFreqs = []

        cnt = 0
        while startpoint < len(self.x): #Racunanje fft fft-a za nalazenje base pitch-a
            sig = self.x[startpoint:startpoint+window]
            yf = rfft(sig)
            self.baseFreqs.append(self.calculatePitch(rfft(np.abs(yf))))
            cnt += 1
            startpoint += window

        self.changePitch(0,4096*500,2**(12.0/12))



    def closeFile(self):
        self.fileName = ""
        self.fs = 0
        self.x = None
        self.audiosamples = []
        self.playing = True
        self.play()

    def exportFile(self):
        write("output.wav",self.fs,self.x)

    def changePitch(self,startpoint,endpoint,val):
        signal = self.x[startpoint:endpoint]
        chunk = 4096
        overlap = 0.75
        hopin = int(chunk*(1-overlap))
        hopout = int(hopin*val)
        
        window = hanning(chunk)
        F = []
        for i in range(0,endpoint-chunk,hopin):
            F.append(rfft(window*signal[i:i+chunk]))

        cnt = 0
        signal = np.zeros(len(signal))
        for i in range(0,endpoint-chunk,hopout):
            signal[i:i+chunk] += window*irfft(F[cnt])
            cnt +=1

        self.x[startpoint:endpoint] = signal

    def calculatePitch(self,arr):
        return 0


# Main function
if __name__ == "__main__":
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.win.show()

    sys.exit(app.exec_())