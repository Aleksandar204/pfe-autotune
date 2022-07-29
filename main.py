import sys
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication,QFileDialog,QMessageBox,QProgressDialog,QWidget,QVBoxLayout
from PySide2.QtCore import QFile
import sounddevice as sd

import numpy as np
from scipy.io.wavfile import read
from scipy.io.wavfile import write
from scipy.fft import *
from scipy.signal import stft, resample, savgol_filter,windows
import matplotlib.pyplot as plt

def complex_polarToCartesian(r, theta):
    return r * np.exp(theta*1j)

def complex_cartesianToPolar(x):
    return (np.abs(x), np.angle(x))

class PhaseVocoder(object): #Preuzeto od https://github.com/cwoodall/
    def __init__(self, ihop, ohop):
        self.input_hop = int(ihop)
        self.output_hop = int(ohop)
        self.last_phase = 0
        self.phase_accumulator = 0

    def sendFrame(self, frame):
        omega_bins = 2*np.pi*np.arange(len(frame))/len(frame)
        magnitude, phase = complex_cartesianToPolar(frame)

        delta_phase = phase - self.last_phase
        self.last_phase = phase

        delta_phase_unwrapped =  delta_phase - self.input_hop * omega_bins
        delta_phase_rewrapped = np.mod(delta_phase_unwrapped + np.pi, 2*np.pi) - np.pi
        
        true_freq = omega_bins + delta_phase_rewrapped/self.input_hop
        
        self.phase_accumulator += self.output_hop * true_freq
        
        return complex_polarToCartesian(magnitude, self.phase_accumulator)

    def sendFrames(self, frames):
        for frame in frames:
            yield self.sendFrame(frame)

class MainWindow():
    fileName = ""
    playing = False
    stream = None
    fs = 0
    x = None

    basePitch = []
    vocoder = PhaseVocoder(0,0)
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
            
            sd.play(self.x,self.fs)
    
    def openFile(self):
        self.closeFile()
        
        self.fileName = QFileDialog.getOpenFileName(None,"Open Image", "./", "Audio Files (*.wav)")[0]
        self.fs,self.x = read(self.fileName)
        winSize = 4410

        for i in range(0,len(self.x), winSize):
            self.basePitch.append(self.calculatePitch(i,i+winSize))

        plt.plot(range(len(self.basePitch)),self.basePitch)
        plt.show()
        
        self.changePitch(0, 4410*100, 2**(8/12))

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
        chunk = 4410
        overlap = 0.9
        hopin = int(chunk*(1-overlap))
        hopout = int(hopin*val)
        
        window = windows.hann(chunk)
        F = []
        for i in range(0,(endpoint-startpoint)-chunk,hopin):
            F.append(fft(window*signal[i:i+chunk])/np.sqrt(((float(chunk)/float(hopin))/2.0)))

        self.vocoder.input_hop = int(hopin)
        self.vocoder.output_hop = int(hopout)
        adjusted = F
        adjusted = [frame for frame in self.vocoder.sendFrames(F)]
        F = adjusted
        cnt = 0
        signal = np.zeros(len(F)*hopout)
        for i in range(0,len(signal)-chunk,hopout):
            signal[i:i+chunk] += window*np.real(window*ifft(F[cnt]))
            cnt +=1
        #print(len(signal))
        resampled = resample(signal, endpoint-startpoint)
        self.x[startpoint:endpoint] = resampled

    def calculatePitch(self,startpoint,endpoint):
        window = windows.hann(len(self.x[startpoint:endpoint]))
        f = rfft(self.x[startpoint:endpoint])
        xf = rfftfreq(len(f),1/(self.fs/2))

        for i in range(50):
            f[i] = 0+0j
        return (np.argmax(np.abs(f)))

        # plt.plot(xf,np.abs(ff))
        # plt.ylim(top=10e6)
        # plt.show()
        # plt.figure()

# Main function
if __name__ == "__main__":
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.win.show()

    sys.exit(app.exec_())