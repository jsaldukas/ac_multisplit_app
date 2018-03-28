#############################################################
# Multisplit App v0.1
# 
# Created by Justinas Saldukas, jsaldukas@gmail.com
#############################################################

appName = "multisplit"
logPrefix = appName + ": "
appFolder = "apps/python/" + appName

import ac
import acsys
import math
import csv
import datetime
import sys
import traceback
import os, os.path

ac.log(logPrefix + "Started, version v0.1")

appWindow = 0
label1 = 0
resetBtn = 0
newSplitBtn = 0
multisplitapp = 0
splitsRenderer = 0

class SplitsRenderer:
    def __init__(self, startx, starty, lapCount, splitCount):
        self.laps = []
        self.splits = []
        self.lastLap = None
        self.labels = []
        
        lineHeight = 20
        lapHeaderWidth = 100
        splitWidth = 50
        splitHeight = 60
        
        global appWindow
        for lapIdx in range(0, lapCount):
            labelId = ac.addLabel(appWindow, "")
            ac.setPosition(labelId, startx, starty + lapIdx * splitHeight)
            
            self.labels.append([labelId])
            for splitIdx in range(0, splitCount):
                labelId = ac.addLabel(appWindow, "")
                ac.setPosition(labelId, startx + lapHeaderWidth + splitIdx * splitWidth, starty + lapIdx * splitHeight)
                self.labels[-1].append(labelId)
                
    def __clear_labels(self):
        for idList in self.labels:
            for id in idList:
                ac.setText(id, "")
    def updateLaps(self, lapsData):
        self.__clear_labels()
        
        for i, lapData in enumerate(lapsData):
            if i >= len(self.labels):
                break
            
            lapLabels = self.labels[i]
            
            time = lapData["time"]
            lap = lapData["lap"]
            
            lapHeaderText = "#{:2d} {:02d}:{:02d}.{:03d}".format(lap, int(time / 60000), int(time / 1000 % 60), int(time % 1000))
            ac.setText(lapLabels[0], lapHeaderText)
            
            for j, splitData in enumerate(lapData["splits"]):
                if j >= len(lapLabels) - 1:
                    break
                
                time = splitData["time"]
                splitText = "<{:3d}\r\n{:02d}.{:02d}\r\n {:3d}>".format(int(splitData["enter_speed"]), int(time/1000), int(time%1000/10), int(splitData["exit_speed"]))
                ac.setText(lapLabels[j+1], splitText)

class Multisplit:
    def __init__(self, track, track_config):
        global appFolder
        self.trackfile = appFolder + "/" + track + '_' + track_config + '.track_splits'
        self.splitConfig = []
        self.currentSplitIndex = 0
        self.currentSplitData = None
        self.lastSplitData = None
        self.lastCarUpdate = None
        self.laps = []
        self.currentLap = None
        self.splitsHistory = []
        self.reset()
        self.__load()
        
    def __load(self):
        self.splitConfig = []
        self.currentSplitIndex = 0
        if os.path.isfile(self.trackfile):
            with open(self.trackfile, 'r') as f:
                for line in f:
                    self.splitConfig.append(float(line))
                 
    def __save(self):
        with open(self.trackfile, 'w') as f:
            for split in self.splitConfig:
                f.write(str(split) + "\n")
    
    def resetSplitConfig(self, npos):
        self.splitConfig = [0]
        self.currentSplitIndex = 0
        self.__save()
    
    def newSplit(self):
        npos = 0
        if self.lastCarUpdate:
            npos = self.lastCarUpdate["npos"]
        
        if npos in self.splitConfig:
            return
        
        index = 0
        for i, split_npos in enumerate(self.splitConfig):
            if npos < split_npos:
                index = i
                break
                
        self.splitConfig.insert(index, npos)
        
        self.__save()
        
    def reset(self):
        self.currentSplitIndex = 0
        self.currentSplitData = {
            "time": 0,
            "enter_speed": 0,
            "exit_speed": 0
        }
        self.lastSplitData = None
        self.lastCarUpdate = None
        self.currentLap = None
        self.laps = []
    
    def carUpdate(self, npos, speed, lap_time, last_lap_time, lap_count):
        global logPrefix
        updated = False
        
        if self.lastCarUpdate and len(self.splitConfig) > 0:
            nextSplitIndex = self.currentSplitIndex + 1
            if nextSplitIndex >= len(self.splitConfig):
                nextSplitIndex = 0
            
            traversingStart = self.lastCarUpdate and self.lastCarUpdate["npos"] > npos and (self.lastCarUpdate["npos"] - npos) > 0.2
            traversingToNextSplit = ((not traversingStart and self.lastCarUpdate["npos"] <= self.splitConfig[nextSplitIndex] and npos > self.splitConfig[nextSplitIndex]) or
                                    (traversingStart and self.splitConfig[nextSplitIndex] == 0))
            
            delta_lap_time = lap_time - self.lastCarUpdate["lap_time"]
            if traversingStart:
                ac.console(logPrefix + "traversingStart")
                delta_lap_time = last_lap_time - self.lastCarUpdate["lap_time"] + lap_time
            
            self.currentSplitData["time"] += delta_lap_time
            
            if traversingToNextSplit:
                ac.console(logPrefix + "traversingToNextSplit")
                self.currentSplitData["exit_speed"] = speed
                self.currentSplitData["idx"] = self.currentSplitIndex
                self.lastSplitData = self.currentSplitData
                self.currentSplitData = {
                    "time": 0,
                    "enter_speed": speed,
                    "exit_speed": 0,
                    "lap": lap_count
                }
                self.currentSplitIndex = nextSplitIndex
                
                if not self.currentLap:
                    self.currentLap = {
                        "lap": lap_count,
                        "time": 0,
                        "splits": []
                    }
                    self.laps.insert(0, self.currentLap)
                
                self.currentLap["splits"].append(self.lastSplitData)
                
                if self.currentLap["lap"] != lap_count:
                    self.currentLap["time"] = last_lap_time
                    self.currentLap = {
                        "lap": lap_count,
                        "time": 0,
                        "splits": []
                    }
                    self.laps.insert(0, self.currentLap)
                    
                    if len(self.laps) > 20:
                        del self.laps[-1]
                
                updated = True
        
        self.lastCarUpdate = {
            "npos": npos,
            "lap_time": lap_time
        }
        
        return updated
    def __format_time(self, ms):
        return "{:02d}.{:03d}".format(int(ms / 1000), int(ms % 1000))
        
    def __format_speed(self, speed):
        return "{:>3d} kmh".format(int(speed))
        
    def getInfoText(self):
        text = ''
        if self.lastSplitData:
            #ac.console(logPrefix + "getInfoText lastSplitTime=" + str(self.lastSplitData["time"]) + "||" + type(self.lastSplitData["time"]).__name__)
            #text += str(self.lastSplitData["time"])
            text += "Current pos: " + str(self.lastCarUpdate["npos"])
            text += (("Last split[{:2d}:  {}\r\n"
                     "Entry speed: {}\r\n"
                     "Exit speed:  {}\r\n").format(
                        self.lastSplitData["idx"] + 1, 
                        self.__format_time(self.lastSplitData["time"]),
                        self.__format_speed(self.lastSplitData["enter_speed"]),
                        self.__format_speed(self.lastSplitData["exit_speed"])))
        
        text += "[" + str(self.currentSplitIndex) + "] " + '|'.join(str(x) for x in self.splitConfig) + "\r\n"
        return text

def printExceptionInfo(contextName=''):
    global logPrefix
    ac.console(logPrefix + "Exception[{}]: {}".format(contextName, traceback.format_exc(1)))
    ac.log(logPrefix + "Exception[{}]: {}".format(contextName, traceback.format_exc()))
    
def onActivate(*args):
    global logPrefix, multisplitapp
    ac.console(logPrefix + "onActivate()")
    try:
        trackName = ac.getTrackName(0)
        trackConfig = ac.getTrackConfiguration(0)
        
        multisplitapp = Multisplit(trackName, trackConfig)
        #ac.setText(label1, multisplitapp.getInfoText())
        
    except:
        printExceptionInfo("onActivate")
    
def onDismiss(*args):
    global logPrefix, multisplitapp
    ac.console(logPrefix + "onDismiss()")
    try:
        if multisplitapp:
            multisplitapp = None
    except:
        printExceptionInfo("onDismiss")

def onNewSplitClicked(*args):
    global logPrefix, multisplitapp
    ac.console(logPrefix + "onNewSplitClicked()")
    try:
        if multisplitapp:
            multisplitapp.newSplit()
    except:
        printExceptionInfo("onNewSplitClicked")

def onResetClicked(*args):
    global logPrefix, multisplitapp
    ac.console(logPrefix + "onResetClicked()")
    try:
        if multisplitapp:
            multisplitapp.reset()
    except:
        printExceptionInfo("onResetClicked")
        

def onRender(delta_t):
    global label1, appWindow, multisplitapp, splitsRenderer
    
    #ac.setBackgroundOpacity(appWindow, 0)
    
    speedKmh = ac.getCarState(0, acsys.CS.SpeedKMH)
    lapTimeMs = ac.getCarState(0, acsys.CS.LapTime)
    lastLapTimeMs = ac.getCarState(0, acsys.CS.LastLap)
    trackPosition = ac.getCarState(0, acsys.CS.NormalizedSplinePosition)
    lapCount = ac.getCarState(0, acsys.CS.LapCount)
    
    if multisplitapp:
        try:
            #ac.setText(label1, multisplitapp.getInfoText())
            updated = multisplitapp.carUpdate(trackPosition, speedKmh, lapTimeMs, lastLapTimeMs, lapCount)
            
            if updated:
                splitsRenderer.updateLaps(multisplitapp.laps)
                #ac.setText(label1, multisplitapp.getInfoText())
        except:
            printExceptionInfo("onRender:call frame()")
            
# This function gets called by AC when the Plugin is initialised
# The function has to return a string with the plugin name
def acMain(ac_version):
    global appWindow, label1, logPrefix, appName, splitsRenderer
    ac.console(logPrefix + "acMain")
    try:
        appWindow = ac.newApp(appName)
        ac.setTitle(appWindow, "")
        ac.setSize(appWindow, 300, 300)
        ac.drawBorder(appWindow, 0)
        ac.setBackgroundOpacity(appWindow, 0.3)
        
        resetBtn = ac.addButton(appWindow, "R")
        ac.setPosition(resetBtn, 5, 30)
        ac.setSize(resetBtn, 30, 30)
        ac.addOnClickedListener(resetBtn, onResetClicked)
        
        newSplitBtn = ac.addButton(appWindow, "N")
        ac.setPosition(newSplitBtn, 40, 30)
        ac.setSize(newSplitBtn, 30, 30)
        ac.addOnClickedListener(newSplitBtn, onNewSplitClicked)
        
        #label1 = ac.addLabel(appWindow, "____")
        #ac.setPosition(label1, 0, 70)
        
        splitsRenderer = SplitsRenderer(2, 62, 10, 10)
        
        ac.addRenderCallback(appWindow, onRender)
        ac.addOnAppActivatedListener(appWindow, onActivate)
        ac.addOnAppDismissedListener(appWindow, onDismiss)
        
        ac.console(logPrefix + "Initialized")
    except:
        printExceptionInfo("acMain")
    
    return appName
