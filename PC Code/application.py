import serial
import time
import struct
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

timestamps = [0] # Initialize with 0
values = [[0] for _ in range(6)] # Initialize with 0
file = open("data.csv", "w")
file2 = open("detection_times.csv", "w")

samples_range = 5 * 100 # 5 seconds * assumed 100 Hz sample rate for visualizing only some seconds of data

# Exponential Moving Average
window_size = 10
processed_values = [[0] for _ in range(6)] # Initialize with 0
N = 10 # Num Windows to average
alpha = 2/(N+1)

# Peak Detection
peak_window_size = 250
peak_time_margin = 0.0 
peak_threshold = 0.3
curl_timeout = 3.5
detect_times = []

value_range = [[-1.5, 1.5], [-1.5, 1.5], [-1.5, 1.5], [-100, 100], [-100, 100], [-100, 100]]

start_found = False
end_found = False

def cap_and_scale(value, value_range):
    if value > value_range[1]:
        return 1
    elif value < value_range[0]:
        return -1
    else:
        return value/value_range[1] 
    
def cap(value, value_range):
    if value > value_range[1]:
        return value_range[1]
    elif value < value_range[0]:
        return value_range[0]
    else:
        return value
    
def peak_detection(data, time, peaks, peak_window_size=250, peak_threshold=0.3, data_threshold = 0.1):
    window_times = time[-1*peak_window_size:]
    window_vals = data[-1*peak_window_size:]
    peak_window_max = max(window_vals)
    peak_window_max_idx = window_vals.index(peak_window_max)
    peak_time = window_times[peak_window_max_idx]
    if (peak_window_max > window_vals[0] + peak_threshold) and (peak_window_max > window_vals[-1] + peak_threshold): # If the peak value is greater than first value and lower than last value
        if data[peak_window_max_idx] > data_threshold: # Filter for small movements
            return peak_time

def segmenter(data, time, start, end, target_samples = 100):
    start_idx = time.index(start)
    end_idx = time.index(end)
    segment = data[start_idx:end_idx+1]
    return

def read_serial():
    ser = serial.Serial('COM11', 921600)
    time.sleep(2)
    timeout_enable = False
    while True:
        if ser.in_waiting > 0:
            raw_data = ser.read(28)
            unpacked_data = struct.unpack('fffffff', raw_data)

            timestamps.append(unpacked_data[0])
            for i in range(6):
                if i < 3:
                    processed_values[i].append(cap(alpha*unpacked_data[1+i] + (1-alpha)*processed_values[i][-1], value_range[i])) # Exponential Moving Average
                else:
                    processed_values[i].append(cap_and_scale(alpha*unpacked_data[1+i] + (1-alpha)*processed_values[i][-1], value_range[i]))

                values[i].append(unpacked_data[1+i])

            peak_time = peak_detection(processed_values[5], timestamps, peaks=detect_times, peak_threshold=0.02)
            if (peak_time not in detect_times) and (peak_time != None):
                detect_times.append(peak_time)
                timeout_enable = True
                print("Detection")
            
            # if len(detect_times) != 0:
            #     if timestamps[-1] > detect_times[-1] + curl_timeout and timeout_enable:
            #         detect_times.append(timestamps[-1])
            #         timeout_enable = False
            #         print("Detection - ")

            file.write("{:.5f};".format(timestamps[-1]))
            for i in range(6):
                file.write("{:.5f}".format(processed_values[i][-1]))
                if i < 5:
                    file.write(';')
            file.write('\n')

serial_thread = threading.Thread(target=read_serial)
serial_thread.daemon = True 
serial_thread.start()

# Initialize plot
fig, axs = plt.subplots(6, 1, sharex=True)
colors = ['r', 'g', 'b', 'c', 'm', 'y']
lines = [axs[i].plot([], [], color=colors[i])[0] for i in range(6)]

def init():
    axs[0].set_ylabel('acc_x')
    axs[1].set_ylabel('acc_y')
    axs[2].set_ylabel('acc_z')
    axs[3].set_ylabel('gyro_x')
    axs[4].set_ylabel('gyro_y')
    axs[5].set_ylabel('gyro_z')
    axs[-1].set_xlabel('Timestamp')
    return lines

def update(frame):
    data_to_plot = processed_values
    if timestamps:
        for i, line in enumerate(lines):
            if len(values[i]) > 0:
                line.set_data(timestamps[max(0, len(timestamps)-samples_range):-1], data_to_plot[i][max(0, len(timestamps)-samples_range):-1])
                axs[i].relim()
                axs[i].autoscale_view()
    return lines

ani = FuncAnimation(fig, update, frames=range(1000), init_func=init, blit=False, interval=5)

plt.show()

for i in detect_times:
    file2.write("{:.5f};".format(i))

file.close()
file2.close()