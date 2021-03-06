# -*- coding: utf-8 -*-
"""
Created on Tue May  4 22:47:39 2021

@author: MYOUNG-WOO

MOKE microscope v1.0.2

Bug fix: Conversion from 16 bit to 8 bit for Video recording
"""

from pyueye import ueye
import numpy as np
import cv2
import sys
from skimage.util import img_as_ubyte
from skimage import exposure, io
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtGui import *
from PyQt5 import uic, QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QCoreApplication
import pyvisa
import time

form_class = uic.loadUiType("MOKE_microscope.ui")[0]

class WindowClass(QMainWindow, form_class) :
    def __init__(self) :
        super().__init__()
        self.setupUi(self)

##############################################################################
        
       # Button connection ###################################################
        self.Movie_Button.clicked.connect(self.Movie)
        self.Contrast_Button.clicked.connect(self.Contrast_Enhancement)
        self.Diff_Button.clicked.connect(self.Differential_Image)
        self.SetBG_Button.clicked.connect(self.Set_Background)
        self.SetFPS_Button.clicked.connect(self.Set_FPS)
        self.SetExp_Button.clicked.connect(self.Set_Exp)
        self.SetCurr_Button.clicked.connect(self.Set_Curr)
        self.Save_Button.clicked.connect(self.Save)
        self.Rec_Button.clicked.connect(self.Rec)
        self.Exit_Button.clicked.connect(self.Exit)
       
       # Initial switch setting ##############################################
        self.Movie_Switch = -1
        self.Contrast_Switch = -1
        self.Diff_Switch = -1
        self.SetBG_Switch = -1
        self.KepcoInit_Switch = -1
        self.Rec_Switch = -1
        
        self.time_avg = 1
        self.Img_Sum = 100
       
       # Indicator ###########################################################
        if self.Movie_Switch == 1:
            self.Movie_Text_Browser.setText("On")
            self.Movie_Text_Browser.setAlignment(QtCore.Qt.AlignCenter);
        elif self.Movie_Switch == -1:
            self.Movie_Text_Browser.setText("Off")
            self.Movie_Text_Browser.setAlignment(QtCore.Qt.AlignCenter);
            
        if self.Contrast_Switch == 1:
            self.Contrast_Text_Browser.setPlainText("On")
            self.Contrast_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        elif self.Contrast_Switch == -1:
            self.Contrast_Text_Browser.setPlainText("Off")
            self.Contrast_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
            
        if self.Diff_Switch == 1:
            self.Diff_Text_Browser.setPlainText("On")
            self.Diff_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        elif self.Contrast_Switch == -1:
            self.Diff_Text_Browser.setPlainText("Off")
            self.Diff_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
            
        if self.Rec_Switch == 1:
            self.Rec_Text_Browser.setPlainText("Rec On")
            self.Rec_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        elif self.Rec_Switch == -1:
            self.Rec_Text_Browser.setPlainText("Rec Off")
            self.Rec_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
            
       
       # Camera Initialization ###############################################
        self.Camera_Initialization()
       
       # Set dummy background image (Black image) ############################
        self.bg_raw = ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)
        self.bg = np.reshape(self.bg_raw, (self.height, self.width, 1)).astype(np.float64)
        self.FinalImage = self.bg
        
        self.bg_resize = cv2.resize(self.bg,(0,0), fx=0.5, fy=0.5)
        self.bg_resize = QtGui.QImage(self.bg_resize, self.bg_resize.shape[1], self.bg_resize.shape[0], QtGui.QImage.Format_Indexed8)
        self.Movie_Frame.setPixmap(QtGui.QPixmap.fromImage(self.bg_resize))
        
        self.value = ueye.c_double(0)
        self.value_to_return = ueye.c_double()
        self.nRet = ueye.is_SetAutoParameter(self.hcam, ueye.IS_SET_ENABLE_AUTO_SHUTTER, self.value, self.value_to_return)
        
        self.value = ueye.c_double(0)
        self.value_to_return = ueye.c_double()
        #self.nRet = ueye.is_SetAutoParameter(self.hcam, ueye.IS_SET_ENABLE_AUTO_GAIN, self.value, self.value_to_return)
        
        self.SetFPS_lineEdit.setText(str("%.2f" % self.IDS_FPS).zfill(5))
        self.SetFPS_lineEdit.setAlignment(QtCore.Qt.AlignRight)
        
        self.SetExp_lineEdit.setText(str("%.2f" % self.IDS_exposure).zfill(5))
        self.SetExp_lineEdit.setAlignment(QtCore.Qt.AlignRight)

    
    def Camera_Initialization(self):
        self.hcam = ueye.HIDS(0)
        self.ret = ueye.is_InitCamera(self.hcam, None)
        self.ret = ueye.is_SetColorMode(self.hcam, ueye.IS_CM_MONO12)
        self.IDS_FPS = float(50)
        self.newrate = ueye.DOUBLE(self.IDS_FPS)
        self.rate = ueye.DOUBLE(self.IDS_FPS)
        self.IDS_exposure = float(20)
        
        self.width = 2056
        self.height = 1542
        self.rect_aoi = ueye.IS_RECT()
        self.rect_aoi.s32X = ueye.int(0)
        self.rect_aoi.s32Y = ueye.int(0)
        self.rect_aoi.s32Width = ueye.int(self.width)
        self.rect_aoi.s32Height = ueye.int(self.height)
        ueye.is_AOI(self.hcam, ueye.IS_AOI_IMAGE_SET_AOI, self.rect_aoi, ueye.sizeof(self.rect_aoi))
        
        self.mem_ptr = ueye.c_mem_p()
        self.mem_id = ueye.int()
        self.bitspixel = 16
        self.ret = ueye.is_AllocImageMem(self.hcam, self.width, self.height, self.bitspixel, self.mem_ptr, self.mem_id)
        
        self.ret = ueye.is_SetImageMem(self.hcam, self.mem_ptr, self.mem_id)
        self.ret = ueye.is_CaptureVideo(self.hcam, ueye.IS_DONT_WAIT)
        #self.lineinc = self.width * int((self.bitspixel + 7) / 8)
        self.lineinc = self.width * int(self.bitspixel / 8)
        
        self.nRet = ueye.is_SetFrameRate(self.hcam, self.rate, self.newrate)
        self.expms = ueye.DOUBLE(self.IDS_exposure)
        self.nRet = ueye.is_Exposure(self.hcam, ueye.IS_EXPOSURE_CMD_SET_EXPOSURE, self.expms, ueye.sizeof(self.expms))
        
        self.pixelclock = ueye.c_uint(197)
        self.nRet = ueye.is_PixelClock(self.hcam, ueye.IS_PIXELCLOCK_CMD_SET, self.pixelclock, 4)
        #pixelclock = ueye.c_uint()
        #ueye.is_PixelClock(hcam, ueye.IS_PIXELCLOCK_CMD_GET, pixelclock, 4)
        
        self.nRet = ueye.is_SetHardwareGain(self.hcam, 100, ueye.IS_IGNORE_PARAMETER, ueye.IS_IGNORE_PARAMETER, ueye.IS_IGNORE_PARAMETER)
        #gg = ueye.c_uint()
        #ueye.is_SetHWGainFactor(hcam, ueye.IS_GET_MASTER_GAIN_FACTOR, gg)
        self.nRet = ueye.is_SetHardwareGamma(self.hcam, ueye.IS_SET_HW_GAMMA_ON)
        
    def Movie(self):
        self.Movie_Switch = -1*self.Movie_Switch
        if self.Movie_Switch == 1:
            self.Movie_Text_Browser.setText("On")
            self.Movie_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        elif self.Movie_Switch == -1:
            self.Movie_Text_Browser.setText("Off")
            self.Movie_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)        
        
        while(self.Movie_Switch == 1):
            self.fps = ueye.c_double()
            self.nRet = ueye.is_GetFramesPerSecond(self.hcam, self.fps)
            self.FPS_Text_Browser.setText(str("%.2f" % self.fps).zfill(5))
            self.FPS_Text_Browser.setAlignment(QtCore.Qt.AlignRight)
            
            self.exposure = ueye.c_double()
            self.nRet = ueye.is_Exposure(self.hcam, ueye.IS_EXPOSURE_CMD_GET_EXPOSURE, self.exposure, 8)
            self.Exp_Text_Browser.setText(str("%.2f" % self.exposure).zfill(5))
            self.Exp_Text_Browser.setAlignment(QtCore.Qt.AlignRight)
            
            
            #kk = 0
            #while(kk <= self.Img_Sum):
            #    kk = kk+1    
            #    
            #    if kk == 1:
            #        self.img_raw = (ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)).astype(np.float64)
            #    else:
            #        self.img_raw0 = (ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)).astype(np.float64)
            #        self.img_raw = self.img_raw*(kk-1)/kk+self.img_raw0/kk
            #        del self.img_raw0
            #    
            #    time.sleep(1/self.fps)
            
            self.img_raw = ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)
            
            if self.Diff_Switch == -1:
                self.img = np.reshape(self.img_raw, (self.height, self.width, 1)).astype(np.uint16)
            elif self.Diff_Switch == 1:
                self.img0 = (np.reshape(self.img_raw, (self.height, self.width, 1))).astype(np.float64)
                self.img = np.round((self.img0-self.bg+4095)/2).astype(np.uint16)
            
            if self.Contrast_Switch == 1:
                self.img = np.reshape(self.img, (self.height, self.width))
               
               # Contrast stretching
                self.pL, self.pH = np.percentile(self.img, (2, 98))
                self.img = exposure.rescale_intensity(self.img, in_range=(self.pL, self.pH), out_range=(0, 4095))
               
               # Equalization
                #self.img = img_as_ubyte(exposure.equalize_hist(self.img))
               
               # Adaptive Equalization 
                #self.img = img_as_ubyte(exposure.equalize_adapthist(self.img, clip_limit=0.5))
                
                self.img = np.reshape(self.img, (self.height, self.width, 1))


            self.FinalImage = self.img
            
            if self.Rec_Switch == 1:
                if 'vid' in locals():
                    vid = np.append(vid, self.FinalImage, axis=2)
                    if vid.shape[2] > 10000:
                        vid = np.delete(vid, 0, axis=2)
                    self.Time_1 = time.time()
                    self.Time = np.append(self.Time, self.Time_1-self.Time_0)
                    self.Time_0 = self.Time_1
                    
                else:
                    vid = np.zeros([self.height, self.width])
                    vid = self.FinalImage
                    self.Time_0 = time.time()
                    self.Time = 0
            
            if 'vid' in locals() and self.Rec_Switch == -1:
                # selecting file path
                filePath, _ = QFileDialog.getSaveFileName(self, "Save Video", "", "avi(*.avi);;All Files(*.*) ")
                
                # if file path is blank return back
                if filePath == "":
                    del vid
                    del self.Time
                    #return
                
                else:
                    self.fps = np.round(1/np.median(self.Time))
                    
                    out = cv2.VideoWriter(filePath, cv2.VideoWriter_fourcc(*'DIVX'), self.fps, (self.width, self.height), isColor=False)
                    for i in range(0, vid.shape[2]):
                        img = (np.round(vid[:, :, i]/4095*255)-1).astype(np.uint8)
                        out.write(img)
                    
                    out.release()
                    del vid
                    del self.Time               
                
            
            self.img_resize = cv2.resize(self.FinalImage,(0,0), fx=0.5, fy=0.5)
            self.img_resize = (self.img_resize/4095*255).astype(np.uint8)
            #self.img_resize = QtGui.QImage(self.img_resize, self.img_resize.shape[1], self.img_resize.shape[0], QtGui.QImage.Format_Indexed8)
            self.img_resize = QtGui.QImage(self.img_resize, self.img_resize.shape[1], self.img_resize.shape[0], QtGui.QImage.Format_Indexed8)
            
            self.Movie_Frame.setPixmap(QtGui.QPixmap.fromImage(self.img_resize))
           
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        
    def Contrast_Enhancement(self):
        self.Contrast_Switch = -1*self.Contrast_Switch
        if self.Contrast_Switch == 1:
            self.Contrast_Text_Browser.setPlainText("On")
            self.Contrast_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        elif self.Contrast_Switch == -1:
            self.Contrast_Text_Browser.setPlainText("Off")
            self.Contrast_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)

    
    def Differential_Image(self):
        self.Diff_Switch = -1*self.Diff_Switch
        if self.Diff_Switch == 1:
            self.Diff_Text_Browser.setPlainText("On")
            self.Diff_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        elif self.Diff_Switch == -1:
            self.Diff_Text_Browser.setPlainText("Off")
            self.Diff_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)

    
    def Set_Background(self):
        #self.bg_raw = ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=False)
        #time.sleep(0.5)
        #self.bg = np.reshape(self.bg_raw, (self.height, self.width, 1)).astype(np.float64)
        
        kk = 0        
        while(kk <= self.Img_Sum):
            kk = kk+1    
            
            if kk == 1:
                self.bg = (ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)).astype(np.float64)
            else:
                self.bg0 = (ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)).astype(np.float64)
                self.bg = self.bg*(kk-1)/kk+self.bg0/kk
                del self.bg0
            
            time.sleep(1/self.fps)
            
        self.bg = np.reshape(self.bg, (self.height, self.width, 1)).astype(np.float64)
        
        
    def Set_FPS(self):
        if self.Movie_Switch == 1:
            self.rate = ueye.DOUBLE(float(self.SetFPS_lineEdit.text()))
            self.newrate = ueye.DOUBLE(float(self.SetFPS_lineEdit.text()))
            self.nRet = ueye.is_SetFrameRate(self.hcam, self.rate, self.newrate)

        
    def Set_Exp(self):
        if self.Movie_Switch == 1:
            self.exposure = ueye.DOUBLE(float(self.SetExp_lineEdit.text()))
            self.expms = ueye.DOUBLE(self.exposure)
            self.nRet = ueye.is_Exposure(self.hcam, ueye.IS_EXPOSURE_CMD_SET_EXPOSURE, self.expms, ueye.sizeof(self.expms))

    
    def Set_Curr(self):
        if self.KepcoInit_Switch == -1:            
            self.kepco_gpib = int(1)
            self.rm = pyvisa.ResourceManager()
        
            self.kepco_inst = self.rm.open_resource('GPIB0::{gpib_add}::INSTR'.format(gpib_add=self.kepco_gpib), read_termination='\n', write_termination='\n')
            
            self.kepco_inst.write("*rst; status:preset; *cls")
            self.kepco_inst.write("CURR:RANG 1")
            self.kepco_inst.write("VOLT:RANG 1")
            
            self.kepco_inst.write("CURR 0")
            self.kepco_inst.write("VOLT 20")
                        
            self.kepco_inst.write("FUNC:MODE CURR")
            
            self.KepcoInit_Switch = 1
        
        if self.KepcoInit_Switch == 1:
            self.kepco_current = float(self.SetCurr_lineEdit.text())
            
            if abs(self.kepco_current) <= 10:
                self.kepco_inst.write("CURR {curr}".format(curr=self.kepco_current))
                self.kepco_inst.write("OUTP ON")        


    def Save(self):          
        # selecting file path
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
  
        # if file path is blank return back
        if filePath == "":
            return
          
        # saving canvas at desired path
        # self.SaveImage.save("a.png")
        
        kk = 0        
        while(kk <= self.Img_Sum):
            kk = kk+1    
            
            if kk == 1:
                self.img_raw = (ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)).astype(np.float64)
            else:
                self.img_raw0 = (ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)).astype(np.float64)
                self.img_raw = self.img_raw*(kk-1)/kk+self.img_raw0/kk
                del self.img_raw0
            
            time.sleep(1/self.fps)
        
        self.img_raw = ueye.get_data(self.mem_ptr, self.width, self.height, self.bitspixel, self.lineinc, copy=True)
        
        if self.Diff_Switch == -1:
            self.img = np.reshape(self.img_raw, (self.height, self.width, 1)).astype(np.uint16)
        elif self.Diff_Switch == 1:
            self.img0 = (np.reshape(self.img_raw, (self.height, self.width, 1))).astype(np.float64)
            self.img = np.round((self.img0-self.bg+4095)/2).astype(np.uint16)
        
        if self.Contrast_Switch == 1:
            self.img = np.reshape(self.img, (self.height, self.width))
           
           # Contrast stretching
            #self.pL, self.pH = np.percentile(self.img, (2, 98))
            #self.img = exposure.rescale_intensity(self.img, in_range=(self.pL, self.pH), out_range=(0, 4095))
           
           # Equalization
            self.img = img_as_ubyte(exposure.equalize_hist(self.img))
           
           # Adaptive Equalization 
            #self.img = img_as_ubyte(exposure.equalize_adapthist(self.img, clip_limit=0.5))
            
            self.img = np.reshape(self.img, (self.height, self.width, 1))


        self.FinalImage = self.img
        
        io.imsave(filePath, self.FinalImage)
        
        
    def Rec(self): 
        self.Rec_Switch = -1*self.Rec_Switch
        if self.Rec_Switch == 1:
            self.Rec_Text_Browser.setText("Rec On")
            self.Rec_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        elif self.Rec_Switch == -1:
            self.Rec_Text_Browser.setText("Rec Off")
            self.Rec_Text_Browser.setAlignment(QtCore.Qt.AlignCenter)
        
    
    def Exit(self):
        if self.KepcoInit_Switch == 1:
            self.kepco_inst.write("CURR {curr}".format(curr=0))
            self.kepco_inst.write("OUTP OFF")
                
        self.Movie_Switch = -1
        #time.sleep(1)
        #cv2.destroyAllWindows()
        ueye.is_FreeImageMem(self.hcam, self.mem_ptr, self.mem_id)      
        self.ret = ueye.is_ExitCamera(self.hcam)
        self.close()
            
##############################################################################

if __name__ == "__main__" :
    app = QApplication(sys.argv) 
    myWindow = WindowClass() 
    myWindow.show()
    app.exec_()