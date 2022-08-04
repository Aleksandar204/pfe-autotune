import numpy as np
from scipy.signal import stft, resample,istft
from tqdm import tqdm

def copy(arg):
    return np.copy(arg)

def findClosest(val, list):
    m = abs(list[0]-val)
    ret = 0
    for i in range(len(list)):
        if abs(list[i] - val) < m:
            m =  abs(list[i] - val)
            ret = i
    return list[ret]

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

def calculatePitch(x,fs,winSize):
    bounds = [20,2000]
    xf = x.astype(np.float64)
    basePitch = []
    for i in tqdm(range(int(len(x) / winSize)-1)):
        basePitch.append(
            augmented_detect_pitch_CMNDF(
                xf,
                winSize,
                i * winSize,
                fs,
                bounds
            )
        )
    basePitch = np.array(basePitch) / 1.05
    return basePitch

def calculateNotes():
    base = 55
    notes = []
    for i in range(60):
        #print(base * (2 **(i/12)))
        notes.append(base * (2 **(i/12)))
    return notes

def changePitch(x,fs,origPitch,newPitch):
        f,t,Zxx = stft(x *0.7,fs,nperseg=4096,noverlap=3072)
        Zxxc = np.copy(Zxx)
        for i in range(Zxx.shape[1]):
            for j in range(Zxx.shape[0]):
                if int(j/getVal(i,Zxx.shape[0],t,x,fs,origPitch,newPitch)) < Zxx.shape[0]:
                    Zxxc[j][i] = Zxx[int(j/getVal(i,Zxx.shape[0],t,x,fs,origPitch,newPitch))][i]

        return resample(istft(Zxxc,fs,nperseg=4096,noverlap=3072)[1], len(x))

def getVal(sl,length,t,x,fs,origPitch,newPitch):
    value = 1
    tstart = t[sl]
    tuk = len(x)/fs
    perc = tstart/tuk
    i = int(perc*len(newPitch))
    if i >= len(newPitch):
        i = len(newPitch)-1
    value = newPitch[i].value()/origPitch[i]

    return value