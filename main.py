import sys
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication,QFileDialog,QMessageBox,QProgressDialog,QWidget,QVBoxLayout,QSlider
from PySide2.QtCore import QFile
import PySide2
import sounddevice as sd
import threading
import time
import math
import numpy as np
from scipy.io.wavfile import read
from scipy.io.wavfile import write
from scipy.fft import *
from scipy.signal import stft, resample, savgol_filter,windows,istft
import matplotlib.pyplot as plt
from tqdm import tqdm

def findClosest(val, list):
    m = abs(list[0]-val)
    ret = 0
    for i in range(len(list)):
        if abs(list[i] - val) < m:
            m =  abs(list[i] - val)
            ret = i
    return list[ret]

def complex_polarToCartesian(r, theta):
    return r * np.exp(theta*1j)

def complex_cartesianToPolar(x):
    return (np.abs(x), np.angle(x))


def autocorrel(f, W, t, lag):    
    return np.sum(
        f[t : t + W] *
        f[lag + t : lag + t + W]
    )

def df(f, W, t, lag):
    return autocorrel(f, W, t, 0)+ autocorrel(f, W, t + lag, 0)- (2 * autocorrel(f, W, t, lag))

def cmndf(f, W, t, lag_max):
    sum = 0
    vals = []
    for lag in range(0, lag_max):
        if lag == 0:
            vals.append(1)
            sum += 0
        else:
            sum += df(f, W, t, lag)
            vals.append(df(f, W, t, lag) / sum * lag)
    return vals

def augmented_detect_pitch_CMNDF(f, W, t, sample_rate, bounds, thresh=0.1):
    CMNDF_vals = cmndf(f, W, t, bounds[-1])[bounds[0]:]
    sample = None
    for i, val in enumerate(CMNDF_vals):
        if val < thresh:
            sample = i + bounds[0]
            break
    if sample is None:
        sample = np.argmin(CMNDF_vals) + bounds[0]
    return sample_rate / (sample + 1)


class MainWindow():
    fileName = ""
    playing = False
    stream = None
    fs = 0
    x = None

    basePitch = []
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
        self.win.pushButton_2.pressed.connect(self.snapNotes)
        self.win.pushButton_3.pressed.connect(self.calcPlay)
        self.sliderBars = []
        self.notes = []
        base = 55
        for i in range(60):
            #print(base * (2 **(i/12)))
            self.notes.append(base * (2 **(i/12)))

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
            self.playing = False
            QApplication.quit()

    def snapNotes(self):
        for i in range(len(self.sliderBars)):
            self.sliderBars[i].setValue(findClosest(self.sliderBars[i].value(), self.notes))
        
    def calcPlay(self):
        self.changePitch()

    # Audio functions connected to UI
    def play(self):
        self.playing = not self.playing
        if not self.playing:
            self.win.pushButton.setText("Play")
            sd.stop()
        else:
            self.x = np.copy(self.orig)
            self.win.pushButton.setText("Pause")
            # print(len(self.basePitch),len(self.sliderBars))
            t = threading.Thread(target=self.moveHorizontalSlider)
            t.start()
            sd.play(self.x,self.fs)

    def moveHorizontalSlider(self):
        sl = 0
        while(self.playing):
            self.win.horizontalSlider.setValue(sl)
            time.sleep(self.winSize / self.fs)
            sl +=1

    def openFile(self):
        self.closeFile()
        
        self.fileName = QFileDialog.getOpenFileName(None,"Open Image", "./", "Audio Files (*.wav)")[0]
        self.fs,self.x = read(self.fileName)
        self.orig = np.copy(self.x)

        self.winSize = 8820
        bounds = [20,2000]

        for i in range(int(len(self.x) / self.winSize)-1):
            self.sliderBars.append(QSlider())
            self.sliderBars[i].setOrientation(PySide2.QtCore.Qt.Orientation.Vertical)
            self.sliderBars[i].setMinimum(0)
            self.sliderBars[i].setMaximum(500)
            self.win.horizontalLayout.addWidget(self.sliderBars[i])
        self.win.horizontalSlider.setMaximum(int(len(self.x) / self.winSize)-1)

        self.xf = self.x.astype(np.float64)
        for i in tqdm(range(int(len(self.x) / self.winSize)-1)):
            self.basePitch.append(
                augmented_detect_pitch_CMNDF(
                    self.xf,
                    self.winSize,
                    i * self.winSize,
                    self.fs,
                    bounds
                )
            )
        self.basePitch = np.array(self.basePitch) / 1.05
        for i in range(int(len(self.x) / self.winSize)-1):
            self.sliderBars[i].setValue(self.basePitch[i])

        # plt.plot(range(len(self.basePitch)),self.basePitch)
        # plt.show()

        

        # self.basePitch = []
        # self.xf = self.x.astype(np.float64)
        # for i in tqdm(range(len(self.xf) // (winSize + 2))):
        #     self.basePitch.append(
        #         augmented_detect_pitch_CMNDF(
        #             self.xf,
        #             winSize,
        #             i * winSize,
        #             self.fs,
        #             bounds
        #         )
        #     )
        # self.basePitch = np.array(self.basePitch) / 1.05
        # plt.plot(range(len(self.basePitch)),self.basePitch)
        # plt.show()

        

    def closeFile(self):
        self.fileName = ""
        self.fs = 0
        self.x = None
        self.audiosamples = []
        self.playing = True
        self.play()
        self.basePitch = []

    def exportFile(self):
        write("output.wav",self.fs,self.x)

    def changePitch(self):
        f,t,Zxx = stft(self.x *0.5,self.fs,nperseg=4096,noverlap=3072)
        Zxxc = np.copy(Zxx)
        for i in range(Zxx.shape[1]):
            for j in range(Zxx.shape[0]):
                if int(j/self.getVal(i,Zxx.shape[0],t)) < Zxx.shape[0]:
                    Zxxc[j][i] = Zxx[int(j/self.getVal(i,Zxx.shape[0],t))][i]

        self.x[0:] = resample(istft(Zxxc,self.fs,nperseg=4096,noverlap=3072)[1], len(self.x))
        
    def getVal(self,sl,length,t):
        value = 1
        tstart = t[sl]
        tuk = len(self.x)/self.fs
        perc = tstart/tuk
        i = int(perc*len(self.sliderBars))
        if i >= len(self.sliderBars):
            i = len(self.sliderBars)-1
        value = self.sliderBars[i].value()/self.basePitch[i]

        # print(value)
        return value


# Main function
if __name__ == "__main__":
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.win.show()

    sys.exit(app.exec_())