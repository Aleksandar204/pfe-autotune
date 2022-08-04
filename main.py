import sys
import threading
import time

from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication,QFileDialog,QMessageBox,QProgressDialog,QWidget,QVBoxLayout,QSlider
from PySide2.QtCore import QFile,QCoreApplication,Qt

import sounddevice as sd
from scipy.io.wavfile import read,write

import pitch

class MainWindow():
    fileName = ""
    playing = False
    fs = 0
    x = None
    notes = []

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
        self.win.horizontalSlider.hide()
        self.sliderBars = []
        self.notes = pitch.calculateNotes()
        
    
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
        if self.fileName == "":
            msgBox = QMessageBox()
            msgBox.setText("No file opened!")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.exec_()
            return
        for i in range(len(self.sliderBars)):
            self.sliderBars[i].setValue(pitch.findClosest(self.sliderBars[i].value(), self.notes))
        
    def calcPlay(self):
        if self.fileName == "":
            msgBox = QMessageBox()
            msgBox.setText("No file opened!")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.exec_()
            return
        self.x = pitch.copy(self.orig)
        self.x[0:] = pitch.changePitch(self.x,self.fs,self.basePitch,self.sliderBars)

    def closeEvent(self):
        self.playing = False

    # Audio functions connected to UI
    def play(self):
        
        if self.playing:
            self.playing = not self.playing
            self.win.pushButton.setText("Play")
            sd.stop()
        else:
            if self.fileName == "":
                msgBox = QMessageBox()
                msgBox.setText("No file opened!")
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.exec_()
                return
            self.playing = not self.playing
            self.win.pushButton.setText("Pause")
            # print(len(self.basePitch),len(self.sliderBars))
            t = threading.Thread(target=self.moveHorizontalSlider)
            t.start()
            sd.play(self.x,self.fs)

    def moveHorizontalSlider(self):
        sl = 0
        while(self.playing):
            if sl == self.win.horizontalSlider.maximum():
                self.play()
            self.win.horizontalSlider.setValue(sl)
            time.sleep(self.winSize / self.fs)
            sl +=1

    def openFile(self):
        self.closeFile()
        
        self.fileName = QFileDialog.getOpenFileName(None,"Open Image", "./", "Audio Files (*.wav)")[0]
        if self.fileName == "":
            msgBox = QMessageBox()
            msgBox.setText("Canceled file open.")
            msgBox.setIcon(QMessageBox.Information)
            msgBox.exec_()
            return
        self.fs,self.x = read(self.fileName)
        self.orig = pitch.copy(self.x)
        self.win.horizontalSlider.show()
        self.winSize = 8820
        self.basePitch = pitch.calculatePitch(self.x, self.fs, self.winSize)

        for i in range(int(len(self.x) / self.winSize)-1):
            self.sliderBars.append(QSlider())
            self.sliderBars[i].setOrientation(Qt.Orientation.Vertical)
            self.sliderBars[i].setMinimum(20)
            self.sliderBars[i].setMaximum(500)
            self.win.horizontalLayout.addWidget(self.sliderBars[i])
        self.win.horizontalSlider.setMaximum(int(len(self.x) / self.winSize)-1)

        
        for i in range(int(len(self.x) / self.winSize)-1):
            self.sliderBars[i].setValue(self.basePitch[i])

    def closeFile(self):
        self.fileName = ""
        self.fs = 0
        self.x = None
        self.playing = True
        self.play()
        self.basePitch = []
        self.win.horizontalSlider.hide()
        for i in reversed(range(1,self.win.horizontalLayout.count())):
            self.win.horizontalLayout.itemAt(i).widget().setParent(None)
        self.sliderBars = []

    def exportFile(self):
        write("output.wav",self.fs,self.x)


# Main function
if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.win.show()
    app.aboutToQuit.connect(mw.closeEvent)
    sys.exit(app.exec_())