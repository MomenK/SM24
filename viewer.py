import asyncio

import numpy as np

import time

from datetime import datetime

from bleak import BleakClient

from asyncqt import QEventLoop, asyncSlot

import pyqtgraph as pg

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from PyQt5.QtWidgets import QComboBox, QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel




devices = {

  "address": ["CC:78:AB:89:5A:8B", "CC:78:AB:89:58:FB","CC:78:AB:89:5A:DB","CC:78:AB:89:5A:D7"],

  "names":  ['SM24_big_1', 'SM24_big_2', 'SM24_small_1', 'SM24_small_2'],

  "type":  ['1', '1', '2', '2'],

  "gainValues" :[['1', '2', '5', '10','20', '50', '100', '200'],['1', '2', '5', '10','20', '50', '100', '200'],

  ['1', '2', '4', '8','16', '32', '64', '128'],['1', '2', '4', '8','16', '32', '64', '128']],

}


services = {

    "UUID": ["f000beea-0451-4000-B000-000000000000","f000beeb-0451-4000-B000-000000000000"],

    "UUID_gain": ["f000befa-0451-4000-B000-000000000000","f000befb-0451-4000-B000-000000000000"],

}


class Window(QWidget):

    def __init__(self, loop=None, parent=None):

        super().__init__(parent)

        self._loop = loop

        self.samplesPerSecond = 5

        self.shortPeriod = 5* 60 * self.samplesPerSecond

        self.longPeriod =  120* 60 * self.samplesPerSecond

        self.currentMode = False  #sets current of voltage mode app

        self._time_now =  datetime.now()

        self.gain = 0 # can take values from 0 to 7 

        self.write = True

        self.updateCounter = 0

        self.channel = 0  # Should go from 0 to 3 for each sensor channel

        # self._client = 0


        

        self.layout = QVBoxLayout()

    

        # First Row *********************************************************

        layout1 = QHBoxLayout()

        layout1.addWidget(QLabel("Select The Device:"))


        self.deviceList = QComboBox()

        self.deviceList.addItems(devices["names"])

        self.deviceList.activated.connect(self.deviceListCB)

        layout1.addWidget(self.deviceList)


        self.pushButton = QPushButton('Connect')

        self.connect = 0

        self.pushButton.clicked.connect(self.connectToggle)

        layout1.addWidget(self.pushButton)


        self.layout.addLayout(layout1)

        self.connectText = QLabel("Choose the device and press connect")

        self.layout.addWidget(self.connectText)

        

        # Second Row *********************************************************

        styles = {'color':'b', 'font-size':'20px'}

        self.graphPlot = pg.GraphicsLayoutWidget()

        self.graphPlot.setBackground('w')

        plot = self.graphPlot.addPlot()

        self._data = np.zeros(self.shortPeriod)

        self.time = np.arange(self.shortPeriod)[::-1]/self.samplesPerSecond/60   # Control sampling rate here

        pen = pg.mkPen(color=(68, 200, 73), width=5, style=QtCore.Qt.SolidLine)

        self._curve = plot.plot(-self.time, self.data,pen=pen)

        plot.showGrid(x=True, y=True)

        plot.setLabel('left', "Concentration", **styles)

        plot.setLabel('bottom', "Time (mins)", **styles)

        plot.setYRange(0, 1, padding=0.15)


        # ********************************** Regions *********************************************************************************************************************

        ranges = [[-3, -0.5,],  [-0.5,0],  [0,1],  [1,1.5],  [  1.5,3]]

        colours = [(255,0,0,50), (255,200,0,50),  (0,255,0,50), (255,200,0,50), (255,0,0,50)]

        

        for i in range(len(ranges)):

            plot.addItem(pg.LinearRegionItem( ranges[i], movable = False, orientation='horizontal',brush=colours[i]), pen = (255,0,255,255))


        self.layout.addWidget(self.graphPlot)

        


        self.graphPlotLong = pg.GraphicsLayoutWidget()

        self.graphPlotLong.setBackground('w')

        plotLong = self.graphPlotLong.addPlot()

        self._dataLong = np.zeros(self.longPeriod)

        self.timeLong = np.arange(self.longPeriod)[::-1]/self.samplesPerSecond/60

        # pen = pg.mkPen(color=(56, 197, 244), width=5, style=QtCore.Qt.SolidLine)

        pen = pg.mkPen(color=(250, 100, 10), width=5, style=QtCore.Qt.SolidLine)

        self._curveLong = plotLong.plot(-self.timeLong,self.dataLong, pen=pen)

        plotLong.showGrid(x=True, y=True)

        plotLong.setLabel('left', "Concentration", **styles)

        plotLong.setLabel('bottom', "Time (mins)", **styles)

        lr = pg.LinearRegionItem([-max(self.time),0], movable = False)

        lr.setZValue(-10)

        plotLong.addItem(lr)

        plotLong.setYRange(0, 1, padding=0.15)

        for i in range(len(ranges)):

            plotLong.addItem(pg.LinearRegionItem( ranges[i], movable = False, orientation='horizontal',brush=colours[i]), pen = (255,0,255,255))

        self.layout.addWidget(self.graphPlotLong)


        #  Data logging ******************************************************************************

        name = str(self._time_now).replace(" ","_").replace(".","_").replace("-","").replace(":","")

        # name = 'test'

        self.file = open(name + '.csv',"w")

        if (self.currentMode == True):

            self.file.write("time,current(nA),channel,gain\n")

            # plot.setLabel('left', "Current (nA)")

            # plot.setLabel('left', "Concentration")

        else:

            self.file.write("time,voltage(V),channel,gain\n")

            # plot.setLabel('left', "Voltage", units='V')

            # plot.setLabel('left', "Voltage (V)")

            

        # plot.setLabel('bottom', "Samples")

        

        


        # Third Row *********************************************************

        layout1 = QHBoxLayout()

        self.gainText = QLabel("Set gain")

        layout1.addWidget(self.gainText)

        self.gainList = QComboBox()

        self.gainList.addItems(['1', '2', '5', '10','20', '50', '100', '200'])

        self.gainList.setEnabled(False)

        self.gainList.activated.connect(self.gainListCB)

        layout1.addWidget(self.gainList)

        layout1.addWidget(QLabel("x10M"))

        self.layout.addLayout(layout1)


        # Fourth Row *********************************************************

        # layout1 = QHBoxLayout()

        # self.channelText = QLabel("Current channel is")

        # layout1.addWidget(self.channelText)

        # layout1.addWidget(QPushButton('Change Channel'))

        # self.layout.addLayout(layout1)


        self.setLayout(self.layout)




    # def create_client(self):

    #     self._client = BleakClient(address, loop=self._loop)

    #     return self._client

    

    async def stop(self):

        if self.connect == True:

            await self.client.disconnect()

        # self.file.close()

            

    @property

    def client(self):

        return self._client

    @property

    def data(self):

        return self._data

    @property

    def dataLong(self):

        return self._dataLong

    @property

    def curve(self):

        return self._curve

    @property

    def curveLong(self):

        return self._curveLong




# This function, allows the user to select the device, connects to it and starts streaming

    async def start(self):

        while(not self.connect):

                await asyncio.sleep(1)


        if self.connect == True:

            self.connectText.setText("Connecting to the device ")

            self.pushButton.setEnabled(False)

            self.deviceList.setEnabled(False)

            self.gainList.setEnabled(True)

            

            while True:

                try:

                    # self.create_client()

                    self._client = BleakClient(devices["address"][self.deviceList.currentIndex()], loop=self._loop)

                    await self.client.connect()

                except:

                    self.connectText.setText("Device not found, trying again ... ")

                    await asyncio.sleep(5)

                else:

                    self.connectText.setText("Connected ")

                    self.file.write(self.deviceList.currentText() + '\n')

                    self.start_read()

                    break

            


    async def read(self):

        

        QtCore.QTimer.singleShot(int(1000/self.samplesPerSecond), self.start_read)

        if self.write == True:   

            # while True: 

            try:

                # print(services["UUID_gain"][self.channel])

                await self.client.write_gatt_char(services["UUID_gain"][self.channel], bytearray([self.gain]), response=True)

                respone = await self.client.read_gatt_char(services["UUID_gain"][self.channel])

                response = int.from_bytes(respone, "big")

                print( f'Sent {self.gain:x}, Response {response:x}' )

                if self.gain == response:

                    self.write = False

                    # break

            except:

                self.connectText.setText("System Error - restart ")

                    

        # Just read

        else:

            try:

                data = await self.client.read_gatt_char(services["UUID"][self.channel])

            except:

                # self.connectText.setText("System Error - restart ")

                print("System Error - restart ")

            else:  

                sensor_data = self.rawToVolts(data) 

                self.update_plot(sensor_data)

                self.file.write(f"{self._time_now},{sensor_data},{1},{self.gain}\n")




    def start_read(self):

        t_time = self._time_now

        self._time_now =  datetime.now()

        delta_time = ( self._time_now - t_time).total_seconds()

        self.connectText.setText(f"Connected. Sampling rate is: {round(1/delta_time)} samples/second ")

        # self.connectText.setText(f"Connected. ")

        asyncio.ensure_future(self.read(), loop=self._loop)




#  Figure stuff

    def update_plot(self, concentration):


        self.dataLong[:-1] = self.dataLong[1:]

        self.dataLong[-1] = concentration

        downScale = 5

        if self.updateCounter == downScale:

            self.curveLong.setData(-self.timeLong[::downScale],np.mean(self.dataLong.reshape(-1, downScale), axis=1))

            self.updateCounter = 1

            # print('hello')

            # print(self.updateCounter)

        else:

            self.updateCounter += 1

            # print(self.updateCounter)

  


        self.curve.setData(-self.time,self.dataLong[-int(self.shortPeriod):])








        # One quick fix

        # if self.updateCounter >= 20:

        #     self.updateCounter = 0

        #     self.curveLong.setData(-self.timeLong,self.dataLong)

        #     # self.curveLong.set_ydata(-self.timeLong,self.dataLong)

        # else:

        #     self.updateCounter += 1

  

        # self.data[:-1] = self.data[1:]

        # self.data[-1] = concentration

        # self.curve.setData(-self.time,self.data)


    

    def rawToVolts(self, data):

        gainVal = devices["gainValues"][self.deviceList.currentIndex()][self.gain]

        if (self.currentMode == True):

            # from Volts to nano Amp

            R = 10*1e6 * int(gainVal) * 1e-9

        else:

            R = 1      

        

                # R = 10*1e6 * self.gain int([self.gain])


        if devices["type"][self.deviceList.currentIndex()] == '1' :

            data1 = data.copy()

            data[0]= data1[3]

            data[1]= data1[2]

            data[2]= data1[1]

            data[3]= data1[0]

            return ((int.from_bytes(data, byteorder='big', signed=False)*33/43 * 1e-6) - 1.65 ) / R

        else:

            data1 = data.copy()

            data[0]= data1[3]

            data[1]= data1[2]

            data[2]= data1[1]

            data[3]= data1[0]

            data = data[1:4]

            # print("Raw data= " + str(data))

            # print(''.join('{:02x}'.format(x) for x in data))

            # print(int.from_bytes(data, byteorder='big', signed=True)* (2.4/1)/(2**24) )

            # divide over R to convert to current

            return int.from_bytes(data, byteorder='big', signed=True)* (2.4/1)/(2**24) / R


    def connectToggle(self):

        self.connect = 1

    

    def gainListCB(self):

        self.gain = self.gainList.currentIndex()

        # print("......")

        # print(self.gainList.currentIndex(),self.gainList.currentText(), self.gain, devices["gainValues"][self.deviceList.currentIndex()][self.gain])

        self.write = True


    def deviceListCB(self):

        self.gainList.clear()

        self.gainList.addItems(devices["gainValues"][self.deviceList.currentIndex()])

        # self.gain = devices["gainValues"][self.deviceList.currentIndex()][self.gainList.currentIndex()]

        self.gain = self.gainList.currentIndex()

        # print("......")

        # print(self.gainList.currentIndex(),self.gainList.currentText(), self.gain, devices["gainValues"][self.deviceList.currentIndex()][self.gain])

        self.write = True


  

    def closeEvent(self, event):

        self.connect = False

        self.file.close()

        super().closeEvent(event)

        asyncio.ensure_future(self.stop(), loop=self._loop)




def main(args):

    app = QtWidgets.QApplication(args)

    loop = QEventLoop(app)

    asyncio.set_event_loop(loop)

    window = Window()

    window.setWindowTitle("SM24 Visualiser")

    window.show()  

    with loop:

        asyncio.ensure_future(window.start(), loop=loop)

        loop.run_forever()




if __name__ == "__main__":

    import sys


    main(sys.argv)
