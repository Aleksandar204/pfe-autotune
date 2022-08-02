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
from tqdm import tqdm

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

class PhaseVocoder(object): # Preuzeto od https://github.com/cwoodall/
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
        winSize = 8820
        bounds = [20,2000]

        self.xf = self.x.astype(np.float64)
        for i in tqdm(range(len(self.xf) // (winSize + 2))):
            self.basePitch.append(
                augmented_detect_pitch_CMNDF(
                    self.xf,
                    winSize,
                    i * winSize,
                    self.fs,
                    bounds
                )
            )
        self.basePitch = np.array(self.basePitch) / 1.05
        plt.plot(range(len(self.basePitch)),self.basePitch)
        plt.show()

        for i in range(2,10,2):
            self.changePitch(i*4410*10,(i+2)*4410*10,2**(i/12)
        self.basePitch = []
        self.xf = self.x.astype(np.float64)
        for i in tqdm(range(len(self.xf) // (winSize + 2))):
            self.basePitch.append(
                augmented_detect_pitch_CMNDF(
                    self.xf,
                    winSize,
                    i * winSize,
                    self.fs,
                    bounds
                )
            )
        self.basePitch = np.array(self.basePitch) / 1.05
        plt.plot(range(len(self.basePitch)),self.basePitch)
        plt.show()

        

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

    def changePitch(self,startpoint,endpoint,val):
        padding = 1000
        # print((startpoint,endpoint))
        signal = self.x[startpoint-padding:endpoint+padding]
        chunk = 4410
        overlap = 0.9
        hopin = int(chunk*(1-overlap))
        hopout = int(hopin*val)
        
        window = windows.hann(chunk)
        F = []
        for i in range(0,len(signal)-chunk,hopin):
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
        resampled = resample(signal, endpoint-startpoint+2*padding)
        self.x[startpoint:endpoint] = resampled[padding:len(resampled) - padding]
# Main function
if __name__ == "__main__":
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.win.show()

    sys.exit(app.exec_())