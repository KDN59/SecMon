#!/usr/bin/python3
# -*- coding: utf-8 -*-

# python3 ~/Documents/Python/SecMon/SecMon.py &
# ps -ef | grep SecMon.py | awk '{print $2}' | xargs kill -9

import RPi.GPIO as GPIO
import time
import os
from tkinter import *
from subprocess import call
import cv2
import numpy as np
from PIL import Image, ImageTk
import requests
import sqlite3

#--- RPi app for monitoring events from 4 sensors and saving in SQL DB ---
#--- by default all permissions is False ---
# app use pins states to setup pirs & prowl msg & prz chnaged DB
# BCM  7 -> events1 -> pir1
# BCM  6 -> events1 -> ?
# BCM 13 -> events1 -> ?
# BCM 19 -> events1 -> ?
# BCM 26 -> msg
# BCM  0 -> prz chnaged DB

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
# define RPi pins for PIR sensors ---
event1_pin = 7
event2_pin = 23
event3_pin = 17
event4_pin = 27
# define pin for permission of events ---
pr_events1 = 5
pr_events2 = 6
pr_events3 = 13
pr_events4 = 19
# define permission for message via PROWL ---
pr_pin_msg = 26
# define prz of changed DB ---
pr_db = 0
# setup pins for events as inputs ---
GPIO.setup(event1_pin, GPIO.IN)
GPIO.setup(event2_pin, GPIO.IN)
GPIO.setup(event3_pin, GPIO.IN)
GPIO.setup(event4_pin, GPIO.IN)
# setup pins for permission events & msg & pr_db as inputs as false ---
GPIO.setup(pr_events1, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(pr_events2, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(pr_events3, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(pr_events4, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(pr_pin_msg, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(pr_db, GPIO.IN, GPIO.PUD_DOWN)
# define relation pin & zone ---
eventsToZone = {event1_pin : 'Entrance',
                event2_pin : 'Hall',
                event3_pin : 'BedRoom',
                event4_pin : 'Pool'}
# define relation pr_events & events_pin ---
pinToEvents = {'5': 7, '6': 23, '17': 13, '27': 19}
      
def start_motion(pin):
    global start_time, zone
    call('espeak "Atention! Motion detected." 2>/dev/null', shell=True)
    # display root window ---
    root.deiconify()
    root.update()
    # define start time & zone of events ---
    zone = eventsToZone[pin]
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    print("Alarm Start " + start_time + " " + zone)
            
    get_frame()
    # send prowl message ---
    if GPIO.input(pr_pin_msg):
        sendMsgProwl("KALKAN SECURITY", msg + zone + ' area !', 0)

    stop_motion()

def stop_motion():
    # check every second status PIR_PIN (if 0 -> exit)
    if not GPIO.input(event1_pin):
        # hide root window ---
        root.withdraw()
        # define stop time of events 
        stop_time = time.strftime("%X")
        # connect to DB
        conn=sqlite3.connect(path_DB)
        # create table events_log if not exists
        if os.path.getsize(path_DB) < 100:
           cursor = conn.cursor()
           cursor.execute('CREATE TABLE events_log (start TIME,stop TIME,zone TEXT,type TEXT)')
           conn.commit()
        # write in DB        
        conn.execute('INSERT INTO events_log (start, stop, zone, type) VALUES(?,?,?,?)',
                     (start_time, stop_time, zone, 'MD'))
        conn.commit()
        # limited records in DB (only last 10)
        cursor = conn.execute("SELECT * from events_log ORDER BY start DESC Limit 10")
        res = cursor.fetchall()
        if len(res) >= 10:
          conn.execute("DELETE from events_log WHERE start < :Id", {"Id": res[9][0]})
          conn.commit()
        # close table
        conn.close()
        # setup pr_db is ready (True)
        GPIO.setup(pr_db, GPIO.IN, GPIO.PUD_UP)
        return
    root.after(1000, stop_motion)

def beep(t, f):
    os.system('play --no-show-progress --null --channels 1 synth %s sine %f' % (t, f))

def get_frame():
    global bs, stream
    if stream is None:
        try:
            stream = requests.get(url_cam, stream=True, timeout=5)
        except Exception:
            print('Error connection to IP Cammera !')
            return
    bs = b''
    while GPIO.input(event1_pin):
      try:
        bs = bs + stream.raw.read(1024)
        a = bs.find(b'\xff\xd8')
        if a != -1:
            b = bs.find(b'\xff\xd9', a)
        if (a != -1) and (b != -1):
            jpg = bs[a:b + 2]
            bs = bs[b + 2:]
            cv_img = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
            img = ImageTk.PhotoImage(image=pil_img)
            # show image in window
            w.configure(image=img, compound=TOP, text=msg + zone + ' area !',
                            font=(None, 14), width=640, height=500)
            w._image_cache = img
            root.update()
      except Exception:
          print('Streaming error !')
          stream = None
          break

def eventsPermission(pr_events):
    if(GPIO.input(pr_events)):
      if pr_events == pr_events1:	
         GPIO.add_event_detect(event1_pin, GPIO.RISING, callback=start_motion)
    else:
      GPIO.remove_event_detect(pinToEvents[str(pr_events)])

def sendMsgProwl(application, description, priority):
    data = {
        'apikey': "46318fb3526d9f98b40974c3c249af32eb871cec",
        'application': application,
        'description': description,
        'priority': priority,  # In the range -2..2
    }
    requests.post('https://api.prowlapp.com/publicapi/add', data=data)

stream = None
url_cam = 'http://192.168.0.22/live'
path_DB = '/home/kdn59/Documents/Python/SecMon/SecMonDB.db'

root = Tk()
root.title('Security Monitor v1.0')
x = root.winfo_screenwidth() / 2 - 320
y = root.winfo_screenheight() / 2 - 240
root.geometry("+%d+%d" % (x, y))

beep(.2, 1000)

msg = 'Detected motion in '
w = Label(root, text = msg,
          fg = "red",
          bg = "cyan",
          font = "Helvetica 25 bold ")
w.pack(expand=True)
# hide main window
root.withdraw()
# call eventsPermission for any changing pr_events
GPIO.add_event_detect(pr_events1, GPIO.BOTH, callback=eventsPermission)
GPIO.add_event_detect(pr_events2, GPIO.BOTH, callback=eventsPermission)
GPIO.add_event_detect(pr_events3, GPIO.BOTH, callback=eventsPermission)
GPIO.add_event_detect(pr_events4, GPIO.BOTH, callback=eventsPermission)

mainloop()
