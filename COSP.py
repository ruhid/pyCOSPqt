import sys
import os
import mne
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, QTimer, QModelIndex, QItemSelectionModel
from PyQt5.QtWidgets import QDialog, QApplication, QTableWidgetItem, QFileDialog, QMainWindow, QMessageBox, QLabel, \
    QGraphicsColorizeEffect, QAbstractItemView, QHeaderView
from ui import Ui_MainWindow  # Importing the auto-generated ui.py

def TKO(array):
    windows=np.lib.stride_tricks.sliding_window_view(array, 3, axis=1)
    TKO_data = windows.T[1].T ** 2 - windows.T[0].T * windows.T[2].T
    return TKO_data

def find_longest_epoch(signal):

    # Find indices where the signal changes
    change_indices = np.where(np.diff(signal) != 0)[0] + 1
    #print(change_indices)

    # If the signal starts with 0, prepend a 0 to change_indices
    if signal[0] == 0:
        change_indices = np.insert(change_indices, 0, 0)

    # If the signal ends with 0, append the length of the array to change_indices
    if signal[-1] == 0:
        change_indices = np.append(change_indices, signal.size)

    # Reshape the array for easy indexing
    change_indices = change_indices.reshape(-1, 2)

    # Find the longest zero epoch
    longest_epoch = max(change_indices, key=lambda x: x[1] - x[0])
    print(f"The longest epoch with only zeros is from index {longest_epoch[0]} to {longest_epoch[1] - 1}.")
    return longest_epoch



class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Create PlotWidgets
        self.pg=pg

        # Add PlotWidgets to Layout
        self.plot_widget1 = self.ui.graphicsView1.addPlot(row=0, col=0)
        self.plot_widget2 = self.ui.graphicsView2.addPlot(row=0, col=0)

        # Detect mouse movements
        self.ui.graphicsView1.scene().sigMouseMoved.connect(self.mouse_moved_1)
        self.ui.graphicsView2.scene().sigMouseMoved.connect(self.mouse_moved_2)

        # Detect x press
        self.x_key_held=False

        # Connect buttons
        self.ui.pushButtonBackward.clicked.connect(self.backward)
        self.ui.pushButtonForward.clicked.connect(self.forward)
        self.ui.pushButtonLoadEdf.clicked.connect(self.load_edf)
        self.ui.pushButtonApplyFilter.clicked.connect(self.filter)
        self.ui.pushButtonAD.clicked.connect(self.cosp_finder_moving_std)

        # Initialize
        self.current_trace_index = 0
        self.show()

    def load_edf(self):
        file_name, _ = QFileDialog.getOpenFileName(None, "Open EDF File", "", "EDF files (*.edf)")
        if file_name:
            self.raw = mne.io.read_raw_edf(file_name, preload=True)
            self.data, self.times = self.raw[:, :]
            self.sample_rate = self.raw.info['sfreq']
            self.nyquist=int(self.sample_rate/2)-1
            self.ui.spinBoxHigh.setMaximum(int(self.sample_rate/2)-1)
            self.ui.labelStatus.setText(f"{file_name} loaded, sample rate : {self.sample_rate}")
            self.stimulus_artefact_finder()
            self.filter()
            print(self.stimulus_times)

    def stimulus_artefact_finder(self):
        raw_filtered = self.raw.copy().filter(l_freq=self.nyquist//2,
                                                   h_freq=self.nyquist)
        data_filtered, times_filtered = raw_filtered[:, :]
        self.stimulus_times=times_filtered[data_filtered.argmax(axis=1)]


    def filter(self):
        self.raw_filtered = self.raw.copy().filter(l_freq=self.ui.spinBoxLow.value(),
                                                   h_freq=self.ui.spinBoxHigh.value())
        self.data_filtered, self.times_filtered = self.raw_filtered[:, :]

        if self.ui.checkBoxTKO.isChecked():
            self.data_filtered=TKO(self.data_filtered)

        if self.ui.checkBoxRect.isChecked():
            self.data_filtered=np.abs(self.data_filtered)

        self.plot_trace(self.current_trace_index)


    def plot_trace(self, index):
        print(index)
        if not index:
            index=self.current_trace_index
        self.current_trace_index = index
        self.plot_widget1.clear()
        self.plot_widget1.plot(self.times, self.data[self.current_trace_index, :])
        self.plot_widget2.clear()
        length_of_y=self.data_filtered[self.current_trace_index, :].shape[-1]
        self.plot_widget2.plot(self.times_filtered[:length_of_y], self.data_filtered[self.current_trace_index, :])
        if self.ui.checkBoxDetectStimulus.isChecked():
            self.plot_detected_stimulus_vline()
            self.ui.doubleSpinBoxDetectionStartPoint.setValue(round(self.stimulus_times[self.current_trace_index],3))

    def plot_detected_stimulus_vline(self):
        x=self.stimulus_times[self.current_trace_index]
        y_min=min(self.data_filtered[self.current_trace_index])
        y_max=max(self.data_filtered[self.current_trace_index])
        x_line = np.array([x, x])
        y_line = np.array([y_min,y_max])
        text = pg.TextItem(text="stimulus ", anchor=(1, 0), color=(255, 0, 0))
        text.setPos(x, y_max)
        self.plot_widget2.plot(x_line, y_line, pen='r')
        self.plot_widget2.addItem(text)


    def cosp_finder_moving_std(self):
        index=self.current_trace_index
        data=self.data_filtered[self.current_trace_index]
        sample_rate=self.sample_rate
        times=self.times_filtered
        stimulus_index=self.stimulus_times[self.current_trace_index]
        window=self.ui.doubleSpinBoxWindowSize.value()

        data_10ms_moving_SD = np.lib.stride_tricks.sliding_window_view(data, int(sample_rate*window)).std(axis=1)
        length = data_10ms_moving_SD.shape[0]
        prestimulus = int(0.09 * sample_rate)
        prestimulus_std = data[:prestimulus].std()
        data_n_copy = data_10ms_moving_SD.copy()

        #detection start and end point
        detection_start_point=int(self.ui.doubleSpinBoxDetectionStartPoint.value()*self.sample_rate)
        detection_end_point=int(self.ui.doubleSpinBoxDetectionEndPoint.value()*self.sample_rate)
        data_n_copy[data_n_copy < prestimulus_std] = 0
        data_n_copy[data_n_copy >= prestimulus_std] = 1

        # plot detected muscle contractions
        self.plot_widget2.plot(times[prestimulus:length],
                               data_n_copy[prestimulus:]*self.data_filtered[self.current_trace_index, :].max(),
                               pen=pg.mkPen(color=(255, 165, 0,50),width=2))

        self.plot_widget1.plot(times[prestimulus:length],
                               data_n_copy[prestimulus:] * self.data[self.current_trace_index, :].max(),
                               pen=pg.mkPen(color=(255, 165, 0, 50), width=2))

        # plot detected largest non contractile time epoch
        largest_time_index=find_longest_epoch(data_n_copy[detection_start_point:detection_end_point])+detection_start_point
        x=times[largest_time_index[0]:largest_time_index[1]]
        y=np.ones_like(x)*self.data_filtered[self.current_trace_index, :].max()

        self.plot_widget2.plot(x,y,
                               pen=pg.mkPen(color=(0, 255, 0, 50), width=10))
        self.plot_widget1.plot(x,
                               np.ones_like(x)*self.data[self.current_trace_index, :].max(),
                               pen=pg.mkPen(color=(0, 255, 0, 50), width=10))

        pcos=round(times[largest_time_index[1]]-times[largest_time_index[0]],3)
        pcos_offset=round(times[largest_time_index[1]]-stimulus_index,3)
        self.show_pcos(times[largest_time_index[1]],
                       f"PCOS is: {pcos}s offset is :{pcos_offset}")

    def show_pcos(self, x, text):

        cosp_data = pg.TextItem(text=text, anchor=(1, 0), color=(0, 200, 0))
        cosp_data.setPos(x, self.data[self.current_trace_index,:].max())
        self.plot_widget1.addItem(cosp_data)

        text_filtered = pg.TextItem(text=text, anchor=(1, 0), color=(0, 200, 0))
        text_filtered.setPos(x, self.data[self.current_trace_index,:].max())
        self.plot_widget2.addItem(text_filtered)




    def remove_plot(self):
        self.ui.graphicsView2.removeItem(self.plot_widget3)


    def backward(self):
        if self.current_trace_index > 0:
            self.current_trace_index -= 1
            self.plot_trace(self.current_trace_index)

    def forward(self):
        if self.current_trace_index < self.data.shape[0] - 1:
            self.current_trace_index += 1
            self.plot_trace(self.current_trace_index)

    def mouse_moved_1(self, pos):
        mouse_point = self.plot_widget1.vb.mapSceneToView(pos)
        self.mouse_x = mouse_point.x()
        self.mouse_y= mouse_point.y()
        self.ui.labelStatus.setText(f"Mouse coordinates: x={self.mouse_x} y={self.mouse_y}")

    def mouse_moved_2(self, pos):
        mouse_point = self.plot_widget2.vb.mapSceneToView(pos)
        self.mouse_x = mouse_point.x()
        self.mouse_y= mouse_point.y()
        if self.x_key_held:
            self.ui.labelStatus.setText(f"Mouse coordinates: x={self.mouse_x} y={self.mouse_y}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_X:
            if not self.x_key_held :
                self.first_x=self.mouse_x
            self.x_key_held = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_X:
            self.x_key_held = False
            self.last_x=self.mouse_x
            self.plot_measure_epoch()


    def plot_measure_epoch(self):

        y=self.data[self.current_trace_index,:]

        if self.ui.checkBoxFromZero.isChecked():
            x1=0
        else:
            x1=self.first_x
        x2=self.last_x
        y1 = np.array([np.min(y), np.max(y)])
        y2 = np.array([np.min(y), np.max(y)])

        try:
            self.plot_widget1.removeItem(self.curve1)
            self.plot_widget1.removeItem(self.curve2)
            self.plot_widget1.removeItem(self.fill)
        except Exception as e:
            print("no plt item  ",e)
            pass
        pen=pg.mkPen(color=(0, 0, 255, 50),
                     width=2)
        self.curve1 = self.plot_widget1.plot([x1, x1], y1, pen=pen)
        self.curve2 = self.plot_widget1.plot([x2, x2], y2, pen=pen)

        # Create FillBetweenItem
        self.fill = pg.FillBetweenItem(self.curve1, self.curve2, brush=(0, 0, 255, 50))  # RGBA

        # Add fill to plot
        self.plot_widget1.addItem(self.fill)





if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
