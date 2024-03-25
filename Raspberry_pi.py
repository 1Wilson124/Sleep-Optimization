import tkinter as tk
from tkinter import ttk
import datetime
import threading
import os, sys
import subprocess
#import winsound  # For Windows sound notifications
import time
from PIL import Image, ImageTk
import pygame
import Adafruit_DHT
import RPi.GPIO as GPIO
# Set GPIO mode
GPIO.setmode(GPIO.BCM)

# Define pins connected to ULN2003A
IN1 = 25
IN2 = 8
IN3 = 7
IN4 = 1

# Set GPIO pins as outputs
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)

# Define the stepper motor sequence
sequence = [[1,0,0,1],
            [1,0,0,0],
            [1,1,0,0],
            [0,1,0,0],
            [0,1,1,0],
            [0,0,1,0],
            [0,0,1,1],
            [0,0,0,1]]

# Define GPIO pins for buttons
button_pins = [21, 3, 4, 14, 15, 18, 17]

GPIO.setmode(GPIO.BCM)
for pin in button_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Define the output pin for the light
led_pin=20
GPIO.setup(led_pin, GPIO.OUT)
    
# Define GPIO to ADC mapping
MQ135_DO_PIN = 2

# Set up sensor type and GPIO pin
sensor = Adafruit_DHT.DHT11
pin = 22 # GPIO pin 4 (physical pin 7)

alarm_time=[0,0]

def step_forward(delay, steps, reverse):
    for i in range(steps):
        if reverse:
            for step in sequence:
                GPIO.output(IN1, step[0])
                GPIO.output(IN2, step[1])
                GPIO.output(IN3, step[2])
                GPIO.output(IN4, step[3])
                time.sleep(delay)
        else:
            for step in reversed(sequence):
                GPIO.output(IN1, step[0])
                GPIO.output(IN2, step[1])
                GPIO.output(IN3, step[2])
                GPIO.output(IN4, step[3])
                time.sleep(delay)
                
class AlarmClock:
    def __init__(self, master):
        self.images = {
            "Switch-on": ImageTk.PhotoImage(Image.open("/home/pi/Downloads/rpi/rpi/img/Switch-on.png")),
            "Switch-off": ImageTk.PhotoImage(Image.open("/home/pi/Downloads/rpi/rpi/img/Switch-off.png")),

            "AQ": ImageTk.PhotoImage(Image.open("/home/pi/Downloads/rpi/rpi/img/AQ.png")),
            "Temperature": ImageTk.PhotoImage(Image.open("/home/pi/Downloads/rpi/rpi/img/Temperature.png")),
            "Humidity": ImageTk.PhotoImage(Image.open("/home/pi/Downloads/rpi/rpi/img/Humidity.png")),

            "Light-on": ImageTk.PhotoImage(Image.open("/home/pi/Downloads/rpi/rpi/img/Light-on.png")),
            "Light-off": ImageTk.PhotoImage(Image.open("/home/pi/Downloads/rpi/rpi/img/Light-off.png")),
        }

        self._init_start(master)
        self._init_conditions()
        self._init_middle_widgets()
        self._init_alarm()
        self.thread=threading.Thread(target=self.statistics)
        self.thread.daemon = True
        self.thread.start()


    def _init_start(self, master):
        self.master = master
        master.title("Alarm Clock")

        # self.turn_off = ttk.Button(master, image=self.images["Switch-on"], command=self.turning)
        # self.turn_off.pack()

        self.title1 = ttk.Label(master, text="Notifications: Open your windows")
        self.title1.pack(pady=10)

    def _init_conditions(self):

        self.hour = 0
        self.minute = 0
        self.rotate = 0
        self.conditions = ttk.Frame(self.master)
        self.conditions.pack()

        self.air = ttk.Label(self.conditions, image=self.images["AQ"])
        self.air.grid(row=1, column=1, padx=5, pady=5)

        self.air_value = ttk.Label(self.conditions, text="60%")
        self.air_value.grid(row=1, column=2, padx=5, pady=5)

        self.temperature = ttk.Label(self.conditions, image=self.images["Temperature"])
        self.temperature.grid(row=1, column=3, padx=5, pady=5)

        self.temperature_value = ttk.Label(self.conditions, text="80°C")
        self.temperature_value.grid(row=1, column=4, padx=5, pady=5)

        self.humidity = ttk.Label(self.conditions, image=self.images["Humidity"])
        self.humidity.grid(row=1, column=5, padx=5, pady=5)

        self.humidity_value = ttk.Label(self.conditions, text="100%")
        self.humidity_value.grid(row=1, column=6, padx=5, pady=5)


    def _init_middle_widgets(self):
        self.middle_widgets = ttk.Frame(self.master)
        self.middle_widgets.pack()

        self.clock_label = ttk.Label(self.middle_widgets, font=('calibri', 100, 'bold'))
        self.clock_label.grid(row=0, column=1, padx=10, pady=5)
        self.update_clock()




    def _init_alarm(self):
        self.alarm_time = tk.StringVar()

        self.alarm_label = tk.Label(self.master, textvariable=self.alarm_time)
        self.alarm_label.pack()
        self.alarm_time.set("Alarm Time: 00:00")

        self.button_frame = ttk.Frame(self.master)
        self.button_frame.pack(padx=5, pady=5)

        # self.blind_label = ttk.Label(self.button_frame, text="Blinds")
        # self.blind_label.grid(row=0, column=0)

        # self.light_label = ttk.Label(self.button_frame, text="Light")
        # self.light_label.grid(row=0, column=7)

        self.light = ttk.Button(self.button_frame, image=self.images["Light-on"], command=self.lighting)
        self.light.grid(row=1, column=0)

        self.blinds = ttk.Button(self.button_frame, image=self.images["Switch-on"], command=self.blinding)
        self.blinds.grid(row=1, column=7)

        self.hour_button = tk.Button(self.button_frame, text="Hr", command=self.increment_hour)
        self.hour_button.grid(row=1, column=1)

        self.minute_button = tk.Button(self.button_frame, text="Mn", command=self.increment_minute)
        self.minute_button.grid(row=1, column=2)

        self.set_button = tk.Button(self.button_frame, text="Set", command=self.set_alarm)
        self.set_button.grid(row=1, column=3)

        self.stop_button = tk.Button(self.button_frame, text="Stop", command=self.stop_alarm, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=4)

        self.sleep = tk.Button(self.button_frame, text="Sound", command=self.sleep_sounds)
        self.sleep.grid(row=1, column=5)

        self.alarm_active = False
        self.update_time()
        #self.master.after(7000, self.statistics)
        self.master.after(7000, self.run_while)
    def turning(self):
        print("turning off")
    
    def lighting(self):
        print("lighting")
        if GPIO.input(led_pin)==0:
            GPIO.output(led_pin, GPIO.HIGH)
        else:
            GPIO.output(led_pin, GPIO.LOW)
        time.sleep(0.5)
    def blinding(self):
        print("blinding")
        # Rotate the motor
        delay = 0.001
        num_steps = 1024  # Adjust this according to your motor's requirements
        if self.rotate==0:
            self.rotate=1
            step_forward(delay, num_steps, 1)
        else:
            self.rotate=0
            step_forward(delay, num_steps, 0)
        time.sleep(0.5)
    def sleep_sounds(self):
        audio_process=subprocess.Popen(["omxplayer", "-o", "alsa", "/home/pi/Downloads/rpi/rpi/sleep_sound.mp3"]) 

    def read_mq135(self):
        # Set MQ135 digital output pin as input
        GPIO.setup(MQ135_DO_PIN, GPIO.IN)
        # Read MQ135 output
        value = GPIO.input(MQ135_DO_PIN)
        return value

    def update_clock(self):
        now = time.strftime('%H:%M:%S')
        self.clock_label.config(text=now)
        self.clock_label.after(1000, self.update_clock)
    
    def run_while(self):
        functions=["self.lighting()", "self.increment_hour()", "self.increment_minute()", "self.set_alarm()", "self.stop_alarm()", "self.sleep_sounds()", "self.blinding()"]
        for pin in button_pins:
            if not GPIO.input(pin):
                exec(functions[button_pins.index(pin)])
                # Your custom action when a button is pressed
                time.sleep(0.5)  # Debouncing delay
        self.master.after(10, self.run_while)

    def statistics(self):
        while True:
            humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
            if humidity is not None and temperature is not None:
                self.temperature_value.config(text = '{0:0.1f}°C'.format(temperature,humidity))
                self.humidity_value.config(text = '{1:0.1f}%'.format(temperature,humidity))

            else:
                print('Failed to read data from sensor!')
            air_quality = self.read_mq135()
            if air_quality==0:
                air_quality="Bad"
                self.title1.config(text="Notifications: Open your windows")
            else:
                air_quality="Good"
                self.title1.config(text="Notifications: All Good!")
            self.air_value.config(text=air_quality)
            time.sleep(5)

    def set_alarm(self):
        try:
            alarm_time = self.alarm_time.get()[-5:]
            print(alarm_time)
            alarm_time = datetime.datetime.strptime(alarm_time, "%H:%M")
            current_time = datetime.datetime.now().time()

            # Convert both times to seconds for easier comparison
            alarm_seconds = alarm_time.hour * 3600 + alarm_time.minute * 60
            current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second

            if alarm_seconds < current_seconds:
                alarm_seconds += 24 * 3600  # If alarm is set for the next day
            self.time_diff = alarm_seconds - current_seconds

            self.master.after(self.time_diff * 1000, self.activate_alarm)
            self.alarm_active = True
            self.set_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        except ValueError:
            pass

    def activate_alarm(self):
        # For Windows sound notifications
        #winsound.Beep(1000, 1000)  # Beep for 1 second

        # we need to use this
        # For cross-platform sound notifications using pygame
        audio_process=subprocess.Popen(["omxplayer", "-o", "alsa", "/home/pi/Downloads/rpi/rpi/alarm_sound.mp3"])

    def stop_alarm(self):
        if self.alarm_active:
            # For Windows sound notifications
            #winsound.PlaySound(None, winsound.SND_PURGE)
            # btw we will have to use the way below

            # For cross-platform sound notifications using pygame
            os.system("killall omxplayer.bin") 

            self.alarm_active = False
            self.set_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def update_time(self):
        time_str = f"Alarm Time: {self.hour:02d}:{self.minute:02d}"
        self.alarm_time.set(time_str)
        self.master.after(1000, self.update_time)

    def increment_hour(self):
        self.hour = (self.hour + 1) % 24
        self.update_time()

    def increment_minute(self):
        self.minute = (self.minute + 1) % 60
        self.update_time()

def set_light_theme(root): #styling goes here
    settings = {
        "TButton": {
            "configure": {
                "background": "#ffffff",
                "foreground": "#000000"
            }
        },
        "TLabel": {
            "configure": {
                "background": "#ffffff",
                "foreground": "#000000"
            }
        },
        "TFrame": {
            "configure": {
                "background": "#ffffff",
                "foreground": "#000000"
            }
        },
    }

    root.configure(background="#ffffff")
    #root.attributes('-fullscreen', True)
    style = ttk.Style()
    style.theme_create("PI", parent="alt", settings=settings)
    style.theme_use("PI")

root = tk.Tk()
root.geometry("480x272")

set_light_theme(root)

my_clock = AlarmClock(root)
# Full screen
# root.wm_attributes('-fullscreen', 'True')
root.mainloop()