import sys
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication,QFileDialog,QMessageBox,QProgressDialog
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
    audiosamples = []

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
            self.progressbar = QProgressDialog("Joining audio samples...", "ok", 0, len(self.audiosamples))
            self.progressbar.setMinimumDuration(500)
            self.progressbar.setWindowTitle("Joining audio samples...")
            self.joinSamples()
            
            sd.play(self.x,self.fs)
            self.progressbar.hide()
            self.progressbar.reset()
    
    def openFile(self):
        self.closeFile()
        self.playing = True
        self.play()
        self.fileName = QFileDialog.getOpenFileName(None,"Open Image", "./", "Audio Files (*.wav)")[0]
        self.fs,self.x = read(self.fileName)
        cnt = 0
        temp = []
        for i in range(len(self.x)):
            temp.append(self.x[i])
            if(cnt == 9999):
                temp = np.array(temp)
                cnt = 0
                self.audiosamples.append(temp)
                temp = []
            cnt += 1
        if len(self.x) % 10000 != 0:
            temp = np.array(temp)
            cnt = 0
            self.audiosamples.append(temp)
            temp = []

    def closeFile(self):
        self.fileName = ""
        self.fs = 0
        self.x = None
        self.audiosamples = []

    def exportFile(self):
        write("output.wav",self.fs,self.x)


    # Helper audio functions
    def joinSamples(self):
        xt = self.x # Ove dve linije koda su obazevne da bi kvalitet audia bio bolji od youtube earrape-a
        xt = xt[len(xt):] # xt je temporary promenljiva koju postavim na originalan audio, pa je onda ispraznim i popunim promenjenim audio sampleovima
        for i in range(len(self.audiosamples)):
            self.progressbar.setValue(i)
            xt = np.concatenate((xt,self.audiosamples[i]),axis=None)
        print(np.array_equal(self.x,xt))
        self.x = xt

# Main function
if __name__ == "__main__":
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.win.show()

    sys.exit(app.exec_())