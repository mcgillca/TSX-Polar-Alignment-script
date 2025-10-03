#!/usr/bin/env -S python3 -u
#
# Line above uses -S allow python to be run with an argument
# python -u prevents buffering of output, allowing you to immediatly see
# the output of the command if e.g. re-directed to a file.
#
# To run this program type:
#
# PAUI.py or python3 PAUI.py
#
# The programme will attempt to take two images at the same DEC but rotated 
# through a fixed angle to determine polar alignment.
#
# Changelog
# V 1.0  - Initial release
# V 1.1  - Tidied up interface. Added scrollbar and clear button.
# V 1.2  - Added the abilty to define a filter to be used with plate solving.
#          Now removes the image and SRC files by default.
#          Binning and filter wheel positions are restored after the run
# V 1.3  - Now does not change subframe state. Allows large cameras to set limited
#          area for plate solve to speed this up.
#
# 03 October 2025

import socket
import time
import sys
import signal
import http.client, urllib.request, urllib.parse, urllib.error
import datetime
import os.path
import random, math
from pathlib import Path

# Imports for UI
import tkinter as tk
from tkinter import messagebox
import threading
from queue import Queue
import platform

# Parameters for controlling take picture
CAM_DURATION = 4.0    # Number of seconds for picture
CAM_BINNING  = 4      # Binning of image
CAM_SCALE    = 6.872  # Arcsec/pixel of binned image - used for platesolve
CAM_FILTER   = ""     # Set if you want to specify a filter for platesolve
# 2.31 for Nerpio, 6.872 for Weybridge, 1.7 for DSS images

# Parameters for controlling where to take images
PA_DEC       = 60.0   # Which declination to take images?
HAI1         = 1.0   # HA for Image 1
HAI2         = 5.0   # HA for Image 2

######################### TESTING ######################################
# Parameters for testing - ensure are are false for a real run
verbose    = False # Flag to say how much data to print out
simulating = False  # Flag to indicate that using simulated images from DSS
testdata   = False # Flag to indicate using test data from Mathematica
keepfiles  = False # Keep the image and source files rather than delete them  

######################### CODE #########################################
# Set up CAM scale if using DSS images
if simulating:
    CAM_SCALE = 1.7
    CAM_BINNING = 1

# Create an event to signal the thread to stop
stop_event = threading.Event()

# Create flag to indicate whether process is running
async_running = False

# Create flag to indicate whether user has confirmed they have disabled
# Tpoint pointing correction
tpoint_pointing_disabled = False

# Now define actions when buttons are pressed and code runs

def start_action():
    # stop_event and async_running are global flags which
    # control whether the PA process should stop and whether it is running
    # thread is a global variable so can stop if needed
    # queue is a global variable so subroutines can send data to the display    

    global stop_event, async_running, thread, queue, tpoint_pointing_disabled

    # Make user confirm they have disabled Tpoint before continuing
    if not tpoint_pointing_disabled:
        result = messagebox.askquestion("Pointing", "Have you disabled Tpoint pointing corrections?")
        if result == "no":
            text_display.config(state=tk.NORMAL)
            text_display.insert(tk.END, logtime()+"Disable pointing corrections before continuing\n")
            text_display.see(tk.END)  # Scroll to the end
            text_display.config(state=tk.DISABLED)
            return
        else:
            tpoint_pointing_disabled = True

    text_display.config(state=tk.NORMAL)
    text_display.insert(tk.END, logtime()+"Starting Polar Alignement Routine\n")
    text_display.see(tk.END)  # Scroll to the end
    text_display.config(state=tk.DISABLED)

    # It should not be possible to press the start button
    # if the PA process is running, but just in case,
    # make sure that only create a new thread when it is not already running
    
    if not async_running:
        # Create a Queue to communicate between threads
        queue = Queue()
        
        # Create a new stop event. This will clear the event if
        # the thread has been previously stopped.
        stop_event = threading.Event()
        
        # Start a new thread to run the asynchronous code
        # Allows the UI to continue whilst running the PA process
        thread = threading.Thread(target=PolarAlign, args=(queue,))
        thread.start()
        
        # set async_running to show the PA process is running
        async_running = True
        
        # Disable start button
        start_button.config(state='disabled')
        stop_button.config(state='normal')
        
        # Schedule the check_queue function to run periodically
        root.after(100, lambda: check_queue(queue))
        
# When stop is clicked, sets the stop_event flag which will
# cause the PA routine to stop when it is safe to do so
# (after lastest image has been completed).
def stop_action():
    # Add your stop action logic here
    text_display.config(state=tk.NORMAL)
    text_display.insert(tk.END, logtime()+"Completing current task.\n")
    text_display.see(tk.END)  # Scroll to the end
    text_display.config(state=tk.DISABLED)
    stop_event.set()
    stop_button.config(state='disabled')        

# Delete all text from the start (line 1, character 0) to the end
def clear_action():
    text_display.config(state=tk.NORMAL)
    text_display.delete('1.0', tk.END)  
    text_display.config(state=tk.DISABLED)
    
# Creates Start, Stop and Clear buttons, a display area for messages and a
# visual indication of required adjustments to achieve Polar Alignment

# Create the main window
root = tk.Tk()
root.title("Polar Alignment")

# Add Icon to main window - but only if Linux
if platform.system() == "Linux":
    p1 = tk.PhotoImage(file = "/usr/share/pixmaps/PAIcon.png")
    # Icon set for program window
    root.iconphoto(False, p1) 

# Create arrow display frame
arrow_frame = tk.Frame(root)
arrow_frame.pack(pady=10)

# Create left display area
left_display = tk.Frame(arrow_frame, width=200, height=200)
left_display.pack(side=tk.LEFT,padx=50, pady=10)

# Add up or down arrow with text below in the left display area
alt_arrow_label = tk.Label(left_display, text="↑", font=("Helvetica", 60))
alt_arrow_label.pack()

alt_text_label = tk.Label(left_display, text="Waiting", font=("Helvetica", 25))
alt_text_label.pack()

# Add icon - but only for Linux
if platform.system() == "Linux":
    # Create mid display area
    mid_display = tk.Frame(arrow_frame, width=100, height=100)
    mid_display.pack(side=tk.LEFT,padx=10, pady=10)

    # Load and embed a logo
    logo_image = tk.PhotoImage(file="/usr/share/pixmaps/PAIcon.png")
    logo_label = tk.Label(mid_display, image=logo_image)
    logo_label.pack()

# Create right display area
right_display = tk.Frame(arrow_frame, width=200, height=200)
right_display.pack(side=tk.LEFT,padx=50, pady=10)

# Add clockwise or anticlockwise symbols with text below
az_rotate_label = tk.Label(right_display, text="⟲", font=("Helvetica", 60))
az_rotate_label.pack()

az_text_label = tk.Label(right_display, text="Waiting", font=("Helvetica", 25))
az_text_label.pack()

# Create text display area
display_frame = tk.Frame(root)
display_frame.pack(side=tk.TOP, padx=10)
text_display = tk.Text(display_frame, height=5, width=80, state=tk.DISABLED)
text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,pady=10, padx = 10)

# Create a Scrollbar
def on_scroll(*args):
    text_display.yview(*args)
    
scrollbar = tk.Scrollbar(display_frame, orient="vertical", command=on_scroll)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Configure the Text widget to use the scrollbar
text_display.config(yscrollcommand=scrollbar.set)

# Create button frame
button_frame = tk.Frame(root)
button_frame.pack(side = tk.TOP, pady=10)

# Create buttons below the display area
start_button = tk.Button(button_frame, text="Start", command=start_action)
start_button.pack(side=tk.LEFT, padx=10)

stop_button = tk.Button(button_frame, text="Stop", command=stop_action)
stop_button.config(state='disabled')
stop_button.pack(side=tk.LEFT, padx=10)

clear_button = tk.Button(button_frame, text="Clear", command=clear_action)
clear_button.pack(side=tk.LEFT, padx=10)

# Routine to create colours for the text
def colour_scale(val):
    if abs(val) > 1:
        return 'red'
    if abs(val) > 0.17:
        return 'yellow'
    return 'green'

# This routine is called every 0.1 seconds. Checks to see if it has
# received any messages from the PA routine. There are several
# types of message:
#    Starting with |: contains the latest calculated adjustment factors
#    Startign with <: a warning message. No new data but routine will continue
#    Starting with !: an error message. The routine will stop
#    Other:         : contains an informational message

def check_queue(queue):
    # Check if the queue has any messages
    while not queue.empty():
        message = queue.get()

        # Update the other displays if needed
        # PA routine has sent the most recent PA adjustment factors
        # These will be separated by a '|'
        if message[0] == '|':
            vals = message.split('|')
            alt_text_label.config(text = DegFormat(abs(float(vals[1]))), \
                                fg = colour_scale(float(vals[1])))
            az_text_label.config(text = DegFormat(abs(float(vals[2]))), \
                                fg = colour_scale(float(vals[2])))
            
            # Use sign of alt adjustment value to change up or down arrow
            if float(vals[1]) > 0:
                alt_arrow_label.config(text="↓", \
                                       fg = colour_scale(float(vals[1])))
            else:
                alt_arrow_label.config(text="↑",\
                                       fg = colour_scale(float(vals[1])))

            # Use sign of az adjustment value to change rotation state
            if float(vals[2]) > 0:
                az_rotate_label.config(text="⟲", \
                                       fg = colour_scale(float(vals[2])))
            else:
                az_rotate_label.config(text="⟳", \
                                       fg = colour_scale(float(vals[2])))

        # Warning message
        elif message[0] == '<': 
            alt_text_label.config(text = "Waiting")
            az_text_label.config(text = "Waiting")
            end_text = message.find(">")
            subtext = message[1:end_text]+"\n"
            text_display.config(state=tk.NORMAL)
            text_display.insert(tk.END, subtext)
            
            text_display.see(tk.END)  # Scroll to the end
            text_display.config(state=tk.DISABLED)

        # Error message. PA routine has responsibilty for
        # resetting flags and ending
        elif message[0] == '!': 
            alt_text_label.config(text = "Error")
            az_text_label.config(text = "Error")
            subtext = message[1:]+"\n"
            text_display.config(state=tk.NORMAL)
            text_display.insert(tk.END, subtext, ("red",))
            text_display.tag_config("red", foreground="red")
            text_display.see(tk.END)  # Scroll to the end
            text_display.config(state=tk.DISABLED)

        # An informational message.
        else:
            # Update the text display area
            text_display.config(state=tk.NORMAL)
            text_display.insert(tk.END, message+'\n')
            text_display.see(tk.END)  # Scroll to the end
            text_display.config(state=tk.DISABLED)
            
    # Schedule the check_queue function to run again after a delay
    root.after(100, lambda: check_queue(queue))

# Handle what happens when the main window is closed
# In the application closing event handler
#(e.g., when the main window is closed):

# First set up global variable to indicate when main window is closed
# Used to prevent other routines trying to change the state of the window
# If they do, this will cause the script to hang.
WindowClosed = False

def on_closing():
    global WindowClosed
    # Set WindowClosed to be true - indicates to PA routines
    # that they should NOT try and change the UI.
    WindowClosed = True
    # If the PA routine is running, close gently.
    if async_running:
        # Set the stop event to signal the thread to stop
        stop_event.set()
        # Wait for the PA thread to finish 
        thread.join()

    # When done, close the window    
    root.destroy()

# Bind the closing event handler to the main window closing event
root.protocol("WM_DELETE_WINDOW", on_closing)
        
# Utility code to be used by the PA routines

# Has the stop event been set? If so, resets buttons and returns true.
# The PA routine then has the accoutability to tidy up and stop running
def end_async_code_check():
    # Checks whether stop event is set
    # Resets buttons and returns true if set.
    if stop_event.is_set():
        async_running = False
        # Don't change UI state if main window was closed by user
        if not WindowClosed:
            start_button.config(state='normal')
            stop_button.config(state='disabled')
    return stop_event.is_set()

# Tidies up when async_code is done. Resets the flags and restores the state
# of the buttons. Accountability of the PA routine since UI routine can't know
# when the imaging stops
def finish_async_code():
    global async_running
    async_running = False
    # Don't try and change windows state if main window was closed by user
    if not WindowClosed:
        start_button.config(state='normal')
        stop_button.config(state='disabled')       

# Test code for trying the UI.
test_messages = ["Just starting", "|-12.3|14.7|", "<Plate solved failed. Wait.>", "|2.3|0.7|", "|0.1|-0.7|", "!Error: Stopping.","|-12.3|-14.7|"]

# Test routine for trying the UI
def async_code(queue):
    # Simulate asynchronous code that generates messages
    for i in range(0, 6):
        if end_async_code_check():
            finish_async_code()
            break
        tot= 0.0
        time.sleep(1)  # Simulating a time-consuming task
        message = f"{test_messages[i]}\n"

        # Put the message in the queue
        queue.put(message)
        if message[0] == '!':
            finish_async_code()
            break

    # Finished. Allow to be restarted 
    finish_async_code()

# Code from here down is used to interact with The Sky X.
# The next routine is used to send the data to TSX. Stolen with pride from Anat.
# Variant of TSXSend that puts a try/catch statement in to catch errors
def TSXSendTry(message):
    TCP_IP = '127.0.0.1'
    TCP_PORT = 3040
    BUFFER_SIZE = 1024
    tryMessage = " \
    /* Java Script */\
    try { \
   " + message + " \
    } \
    catch (e) { \
       out = e; \
    } \
    "
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Catch if can't open TCP port.
    try:
        s.connect((TCP_IP, TCP_PORT))
    except:
        queue.put("!"+logtime()+"Could not connect to TSX. Is TSX runnng?")
        queue.put("!"+logtime()+"Have you enabled the TSX TCP server?")
        finish_async_code()
        sys.exit()
        
 
    s.sendall(tryMessage.encode())
    data = s.recv(BUFFER_SIZE)
    s.close()
    if verbose: print(data)
    data2 = data.decode().split("|")
    return data2

# Routines for connecting equipment
def connectscope():
    MESSAGE = " \
    /* Java Script */\
    sky6RASCOMTele.Connect();\
    "
    data = TSXSendTry(MESSAGE)
    if data[0] != "undefined":
        queue.put("!"+logtime() + "Could not connect scope: "+ data[0])
        finish_async_code()
        sys.exit()
    else:
        queue.put(logtime() + "Scope Connected")
        return 0

def connectfilterwheel():
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCamera.filterWheelConnect();\
    "
    data = TSXSendTry(MESSAGE)
    if data[0] != "0":
        queue.put("!"+logtime() + "Could not connect filterwheel: "+ data[0])
        finish_async_code()
        sys.exit()
    else:
        queue.put(logtime() + "Filterwheel connected")
        return 0

# Variable to hold position of initial filter
def setfilter(filter):
    global initfilter
    # First get current filter name and store to reset later
    initfilter= int(TSXSendTry("ccdsoftCamera.FilterIndexZeroBased")[0])

    # Find how many filter slots there are
    lastslot = int(TSXSendTry("ccdsoftCamera.lNumberFilters")[0])

    # Now look for filter name
    ifilter = 0
    while ifilter < lastslot:
        filName = TSXSendTry("ccdsoftCamera.szFilterName(" + \
                             str(ifilter) + ")")[0]
        if filName == filter: # Found filter requested
            respond = TSXSendTry("ccdsoftCamera.FilterIndexZeroBased = " + \
                                 str(ifilter) + ";")
            if int(respond[0]) == ifilter:
                queue.put(logtime() + "Selected filter: " + filter)
                return 0
            else:
                queue.put("!"+logtime() + "Could not set filter: "+ filter + \
                          "Err code:"+ data[0])
                finish_async_code()
                sys.exit()
                
        ifilter += 1

    queue.put("!"+logtime() + "Could not find filter: "+ filter)
    finish_async_code()
    sys.exit()
    
def connectcamera():
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCamera.Connect();\
    "
    data = TSXSendTry(MESSAGE)
    if data[0] != "0":
        queue.put("!"+logtime() + "Could not connect camera: "+ data[0])
        finish_async_code()
        sys.exit()
    else:
        queue.put(logtime() + "Camera connected")
        return 0

def unpark( ):
    MESSAGE = " \
    /* Java Script */\
    sky6RASCOMTele.Connect();\
    sky6RASCOMTele.Unpark();\
    "
    return TSXSendTry(MESSAGE)

def GetImageBin():
    MESSAGE = " \
    /* Java Script */\
    out = ccdsoftCamera.BinX;\
    "
    bin = int(TSXSendTry(MESSAGE)[0])
    return bin

def SetImageBin(bin):
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCamera.BinX = " + str(bin) + " ;\
    ccdsoftCamera.BinY = " + str(bin) + " ;\
    "
    return TSXSendTry(MESSAGE)

def takeimagebin( exp, bin ):
    TCP_IP = '127.0.0.1'
    TCP_PORT = 3040
    BUFFER_SIZE = 1024
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCamera.Connect();\
    ccdsoftCamera.Asynchronous = false; \
    ccdsoftCamera.ExposureTime = " + str(exp) + ";  \
    ccdsoftCamera.AutoSaveOn = true;\
    ccdsoftCamera.ImageReduction = 0;   \
    ccdsoftCamera.Frame = 1;\
    ccdsoftCamera.Delay = 0;\
    ccdsoftCamera.BinX = " + str(bin) + " ;\
    ccdsoftCamera.BinY = " + str(bin) + " ;\
    ccdsoftCamera.TakeImage();\
    "
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(MESSAGE.encode())
    s.settimeout(exp+60)
    try:
        data = s.recv(BUFFER_SIZE)
    except socket.error:
        data = "Timeout"
        print(logtime() + "Timeout from camera.")
    s.close()
    return

# Next routine gets the actual HA of the image
def ImageLinkLastImage(scale):
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCameraImage.AttachToActiveImager();\
    ImageLink.pathToFITS = ccdsoftCameraImage.Path;\
    ImageLink.scale = " + str(scale) + ";\
    ImageLink.unknownScale = 0;\
    ImageLink.execute();\
    "
    data = TSXSendTry(MESSAGE)
    if data[0] != "undefined":
        print(logtime()+ data[0])
        return 1
    return 0
    
# Next routine gets the actual HA of the image
def GetImageHAandLST():
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCameraImage.AttachToActiveImager();\
    ha = ccdsoftCameraImage.FITSKeyword(\"TELEHA\");\
    lst = ccdsoftCameraImage.FITSKeyword(\"LST\");\
    out = ha + '|' + lst;\
    "
    data = TSXSendTry(MESSAGE)
    spdataha  = data[0].split()
    hadata    = abs(float(spdataha[0])) + float(spdataha[1])/60.0 + \
                float(spdataha[2])/3600.0
    ha = math.copysign(hadata, float(spdataha[0]))
    spdatalst = data[1].split()
    lstdata   = abs(float(spdatalst[0])) + float(spdatalst[1])/60.0 + \
                float(spdatalst[2])/3600.0
    lst = math.copysign(lstdata, float(spdatalst[0]))
    return ha, lst

def takeimage( exp ):
    TCP_IP = '127.0.0.1'
    TCP_PORT = 3040
    BUFFER_SIZE = 1024
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCamera.Connect();\
    ccdsoftCamera.Asynchronous = false; \
    ccdsoftCamera.ExposureTime = " + str(exp) + ";  \
    ccdsoftCamera.AutoSaveOn = true;\
    ccdsoftCamera.ImageReduction = 0;   \
    ccdsoftCamera.Frame = 1;\
    ccdsoftCamera.Delay = 0;\
    ccdsoftCamera.Subframe = false;\
    ccdsoftCamera.BinX = 1;\
    ccdsoftCamera.BinY = 1;\
    ccdsoftCamera.TakeImage();\
    "
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(MESSAGE.encode())
    s.settimeout(exp+60)
    try:
        data = s.recv(BUFFER_SIZE)
    except socket.error:
        data = "Timeout"
        print(logtime() + "Timeout from camera.")
    s.close()
    return

# Function to attempt flats:
def SlewToRaAndDec(Ra, Dec, Targetname):
    MESSAGE = " \
    /* Java Script */\
    sky6RASCOMTele.SlewToRaDec(" + str(Ra) + ", " + str(Dec) + ",\"" \
    + Targetname+"\");\
    "
    data = TSXSendTry(MESSAGE)# Function to attempt flats:
    
def GetImageLinkResults():
    MESSAGE = " \
    /* Java Script */\
    err = ImageLinkResults.errorCode; \
    ra = ImageLinkResults.imageCenterRAJ2000; \
    dec = ImageLinkResults.imageCenterDecJ2000;\
    sky6Utils.Precess2000ToNow(ra, dec);\
    file = ccdsoftCamera.LastImageFileName;\
    out = err+ '|' + sky6Utils.dOut0 + '|' + sky6Utils.dOut1 + '|' + file;\
    "
    data = TSXSendTry(MESSAGE)
    if not keepfiles: # Remove file and src file
        fitsfilename = data[3]
        srcfilename = fitsfilename.replace(".fit", ".SRC")
        Path.unlink(fitsfilename, missing_ok = True)
        Path.unlink(srcfilename, missing_ok = True)
    return int(data[0]), float(data[1]), float(data[2])
    
# Next utility functions to calculate sin and cos in degrees
def sind(ang):
    return math.sin(ang*math.pi/180.0)

def cosd(ang):
    return math.cos(ang*math.pi/180.0)

def acosd(cosval):
    return math.acos(cosval)*180.0/math.pi

# A utility function to return LST for rise and set
def LSTRise(alt, lat, dec, ra):
    cosh = (sind(alt)-sind(lat)*sind(dec))/cosd(lat)/cosd(dec)
    if cosh > 1:
        return 1000.0
    if cosh < -1:
        return -1000.0

    # Can work out H
    H = acosd(cosh)/15.0
    return -H+ra

def LSTSet(alt, lat, dec, ra):
    cosh = (sind(alt)-sind(lat)*sind(dec))/cosd(lat)/cosd(dec)
    if cosh > 1:
        return -1000.0
    if cosh < -1:
        return 1000.0

    # Can work out H
    H = acosd(cosh)/15.0
    return H+ra

# A function to keep time within range of 12 to 36 hours
# so times from mid-day through midnight to the following mid-day
# are in sequence.
# Special cases:
# If range is > 100, then never rises
# If range is < 100, then never sets
def range24(t):
    # Deal wilth special cases
    if t > 100: return 1000.0
    if t < -100.0: return -1000.0
    
    i = math.floor(t/24)
    t -= i * 24
    if t < 12: t +=24 
    return t

# Formats decimal time nicely
def formatdectime(t):
    if t > 24: t-= 24.0
    h = math.floor(t)
    m = math.floor((t-h)*60)
    return '%02d:%02d' % (h, m)

# A utility function to return latitude, longitude, current LST and UT.
def LatLongLstUT():
    MESSAGE = " \
    /* Java Script */\
    var Out=\"\";\
    var dLat;\
    var dLon;\
    var dLST;\
    var UT;\
    var sk6DocProp_Latitude = 0;\
    var sk6DocProp_Longitude = 1;\
    var sk6DocProp_JulianDateNow=9;\
    sky6StarChart.DocumentProperty(sk6DocProp_Latitude);\
    dLat = sky6StarChart.DocPropOut;\
    sky6StarChart.DocumentProperty(sk6DocProp_Longitude);\
    dLon = sky6StarChart.DocPropOut;\
    sky6Utils.ComputeLocalSiderealTime();\
    dLST = sky6Utils.dOut0;\
    sky6Utils.ComputeUniversalTime();\
    dUT = sky6Utils.dOut0;\
    Out += String(dLat) + \"|\";\
    Out += String(dLon) + \"|\";\
    Out += String(dLST) + \"|\";\
    Out += String(dUT);\
    "
    data = TSXSendTry(MESSAGE)
    return float(data[0]), float(data[1]), float(data[2]),\
        float(data[3])

# Utility routines
# Nicely formats time for a logoutput
def logtime():
    return time.strftime("[%d-%m-%Y %H:%M:%S] ")

# Next takes a string which is decimal time and turns it into a time
def format_time(dectimestring):
    dectime = float(dectimestring)
    hour = int(dectime);
    min = int((dectime - hour)*60)
    sec = int((dectime - hour)*3600-min*60+0.5)
    tstring = '%02d:%02d:%02d' % (hour, min, sec)
    return tstring

# Utility routine that calculates a decimal time from a time structure
def decimaltime(ts):
    d = ts.tm_hour+ts.tm_min/60.0+ts.tm_sec/3600.0
    return d

# Calculate Alt Az from HA DEC
def AltAzfromHADEC(HA, Dec):
    
    MESSAGE = " \
    /* Java Script */\
    sky6Utils.ComputeLocalSiderealTime();\
    Ra = sky6Utils.dOut0 - (" + str(HA)+");\
    sky6Utils.ConvertRADecToAzAlt(Ra, " + str(Dec) + ");\
    out = sky6Utils.dOut1 + '|' + sky6Utils.dOut0;\
    "
    data = TSXSendTry(MESSAGE)
    return float(data[0]), float(data[1])

# Calculate Alt Az from HA DEC
def AltAzfromHADECLat(HA, Dec, lat):
    # Convert to radians
    HAr  = HA  * math.pi/12.0
    Decr = Dec * math.pi/180.0
    latr = lat * math.pi/180.0
    Altr = math.asin(math.sin(Decr)*math.sin(latr) + math.cos(Decr) * \
                     math.cos(latr)*math.cos(HAr))
    Azr = math.atan2(-math.cos(Decr)*math.cos(latr)*math.sin(HAr),\
                     math.sin(Decr)-math.sin(latr)*math.sin(Altr))
    
    Alt = Altr * 180.0/math.pi
    Az  = Azr * 180.0/math.pi

    return(Alt, Az)

def HADECfromAltAz(Alt, Az):
    MESSAGE = " \
    /* Java Script */\
    sky6Utils.ConvertAzAltToRADec(" + str(Az) +"," + str(Alt) + ");\
    Ra = sky6Utils.dOut0;\
    Dec = sky6Utils.dOut1;\
    sky6Utils.ComputeHourAngle(Ra);\
    Ha = sky6Utils.dOut0;\
    out = Ha + '|' + Dec;\
    "
    data = TSXSendTry(MESSAGE)
    return float(data[0]), float(data[1])

# Routine to dry and work out rotation that will take (Alt1, Az1) to (Alt2, Az2)

# Routine to look for brute force best solution of rotation
def BruteRotationSearch(Alt, Az, AltTarget, AzTarget):
    # Set resolution of first search to 2 arcmin
    res1 = 6/60
    # Set resolution of search to 5 arsec
    res2 = 10/3600
    
    V = VfromAltAz(Alt, Az)
    VTarget = VfromAltAz(AltTarget, AzTarget)

    # Fix to a standard range - 10 degrees altitude, 25 degrees azimuth
    trange = 10
    prange = 25

    (tsoln, psoln) = RotationSearch(V, VTarget, 0, trange, res1, 0, \
                                    prange, res1)
    # Now refine it further
    (tsoln, psoln) = RotationSearch(V, VTarget, tsoln, res1*2, res2, \
                                    psoln, res1*2, res2)
    return (tsoln, psoln)
    
def RotationSearch(V, VTarget, tmid, trange, tinc, pmid, prange, pinc):
    # Initialise best solution
    tsoln = tmid
    psoln = pmid
    solmax = VDot(VTarget, VAltAzRotate(V, tsoln, psoln))

    # Double loop to test best solution
    t = tmid-trange
    while t < tmid + trange:
        p = pmid - prange
        while p < pmid + prange:
            sol = VDot(VTarget, VAltAzRotate(V, t, p))
            if sol > solmax:
                solmax = sol
                tsoln = t
                psoln = p
            p += pinc
        t += tinc

    return (tsoln, psoln)

        
# Routine to rotate Alt, Az by Theta and Phi
def RotateAltAz(Alt, Az, theta, phi):
    # First turn into a vector
    V = VfromAltAz(Alt, Az)
    # Then rotate by theta, phi
    V1 = VAltAzRotate(V, theta, phi)
    # Then return new AltAz location
    return VecToAltAz(V1)

# Next a series of funtions to help with vectors
def VfromAltAz(Alt, Az):
    # Calculates a 3D unit vector in the direction of Alt Az
    # First convert to radians
    V=[0,0,0]
    Altr = Alt * math.pi / 180.0
    Azr  = Az * math.pi / 180.0

    # Now can calculate the vector
    V[0] = math.cos(Altr) * math.sin(Azr)
    V[1] = math.cos(Altr) * math.cos(Azr)
    V[2] = math.sin(Altr)
    return V

def VecToAltAz(V):
    # Calculates the alt/az postion from a unit vector, V
    # Will return Az in the range of -180 to 180.
    Alt = math.asin(V[2]) * 180/math.pi
    Az = math.atan2(V[0], V[1]) * 180/math.pi

    return Alt, Az

def VAltAzRotate(V, theta, phi):
    # Rotates V firsty by phi degrees counter clockwise around Z axis
    # then by theta degrees clockwise around X axis. This convention
    # should rotate the telescope axis back to the pole given the alt,az
    # offset of the axis from the pole as input.

    # First convert to radians
    thetar = theta * math.pi / 180.0
    phir = phi * math.pi / 180.0

    # Now rotate around Z axis
    V1=[0.0,0.0,0.0]
    V1[0] = math.cos(phir) * V[0] - math.sin(phir) * V[1]
    V1[1] = math.sin(phir) * V[0] + math.cos(phir) * V[1]
    V1[2] = V[2]

    # Finally around the X axis
    V2=[0.0,0.0,0.0]
    V2[0] = V1[0]
    V2[1] = math.cos(thetar) * V1[1] + math.sin(thetar) * V1[2]
    V2[2] = -math.sin(thetar) * V1[1] + math.cos(thetar) * V1[2]

    return V2
    
def VSub(V1, V2):
    # Calculates V1-V2 and returns
    V = [V1[0] - V2[0], V1[1] - V2[1], V1[2] - V2[2]]
    return V

def VDot(V1, V2):
    # Calculates dot product of two vectors
    return V1[0]*V2[0]+V1[1]*V2[1]+V1[2]*V2[2]

def UVec(V):
    # returns unit vector in same direction as V
    norm = math.sqrt(VDot(V,V))
    UV = [element / norm for element in V]
    return UV
    
def VCross(V1, V2):
    # Calculates cross product of two vectors
    V = [0,0,0]
    V[0] = V1[1]*V2[2]-V1[2]*V2[1]
    V[1] = V1[2]*V2[0]-V1[0]*V2[2]
    V[2] = V1[0]*V2[1]-V1[1]*V2[0]
    return V
    
def VGCC(SZ,CZ,SA,CA,phi):
    # Returns a vector on the great circle defined by SZ, CZ, SA, CA at position Phi
    # If equation for great circle in y-z plane is [0, sin(phi), cos(phi)]
    # Then equation for rotated great circle is
    # [ -SZ CA cos(phi) - SA sin(phi), -SZ SA cos(phi) + CA sin(phi), CZ cos(phi)]
    return [ -SZ*CA*math.cos(phi) - SA*math.sin(phi),
        -SZ*SA*math.cos(phi) + CA*math.sin(phi), CZ*math.cos(phi)]

def Cosang(SZ,CZ,SA,CA,phi, V1, V2):
    # Calculates the angle between the two image locations and the potential polar axis
    # First calculate the postion of the potential polar axis
    gcc = VGCC(SZ,CZ,SA,CA,phi)
    a1 = UVec(VCross(gcc, V1))
    a2 = UVec(VCross(gcc, V2))
    return VDot(a1,a2)
    
# Next routine solves for the polar axis given data from the two images
def PASolve(RA1, DEC1, LST1, THA1, RA2, DEC2, LST2, THA2):
    # Inputs for the routine are:
    # RA1, DEC1 - the platsolved RA and DEC in JNow.
    # LST1      - the local siderial time as recorded in the first image
    # THA1      - the hour angle as reported from the telescope
    # The inputs labeled '2' are the same but for the second image
    
    # Other variables:
    # HA1       - the hour angle in radians for the first image from RA1 and LST1.
    # HA2       - the hour angle in radians for the second image from RA1 and LST1.
    # D1        - Dec in radians for first image
    # D2        - Dec in radians for second image
    # V1        - Vector in direction of image 1
    # V2        - Vector in direction of image 2
    # DV        - Difference between V2 and V2
    # ADV       - norm of DV
    # DVA       - unit vector of DV (DV divided by ADV).
    # SZ        - Sin of angle between the horizon and DVA
    # CZ        - Cos of angle between the horizon and DVA
    # AZD       - azimuthal direction of DVA measured from the x-axis
    # SA        - Sin of AZD
    # CA        - Cos of AZD
    
    # First determine hour angles in radians for the two images
    HA1 = (LST1 - RA1)/24.0*2*math.pi
    HA2 = (LST2 - RA2)/24.0*2*math.pi
    
    # Now the DEC in radians for the two images
    D1 = DEC1 * math.pi/180.0
    D2 = DEC2 * math.pi/180.0
    
    # Now work out vectors for the positions of image 1 and 2.
    # Using co-ordinate system aligned with North and South Celestial Poles.
    # Z axis pointing to North, Y aligned with Meridian, and X perpendicular to both
    # pointing to Horizon
    
    V1 = [math.cos(D1) * math.sin(HA1), math.cos(D1) * math.cos(HA1), math.sin(D1)]
    V2 = [math.cos(D2) * math.sin(HA2), math.cos(D2) * math.cos(HA2), math.sin(D2)]
    
    # Now calculate the differnce between the two vectors, then the unit vector in that direction
    DV = VSub(V2,V1)
    DVA = UVec(DV)
    
    # Now want to create equation for great circle perpendicular to DVA
    # This will contain the pole since must be equidistant from each image since a pure rotation
    # around the RA telescope axis
    # Can do this by rotating the unit circle in the y-z plane.
    # First rotate around the y axis so that the height of the transformed x-axis matches the
    # z value of DVA.
    # Second rotation is around z to align transformed x-axis with DVA.
    SZ = DVA[2]
    CZ = math.sqrt(1-SZ*SZ)
    AZD = math.atan2(DVA[1], DVA[0])
    SA = math.sin(AZD)
    CA = math.cos(AZD)
    
    # If equation for great circle in y-z plane is [0, sin(phi), cos(phi)]
    # Then equation for rotated great circle is
    # [ -SZ CA cos(phi) - SA sin(phi), -SZ SA cos(phi) + CA sin(phi), CA cos(phi)]
    # This is encoded in the function Cosang
    
    # Calculate the cos of the angle between the telescope HA positons
    CosHASep = math.cos((THA1 - THA2)*math.pi/12.0)
    
    # Solution shoudl be somewhere near the pole - solve using numerical NR soln
    Phi = 0.0
    EPS = 0.0001
    EPSSOLN = 0.0000001
    DC = Cosang(SZ,CZ,SA,CA,Phi, V1, V2) - CosHASep
    while abs(DC) > EPSSOLN:
        DCPlus = Cosang(SZ,CZ,SA,CA,Phi+EPS, V1, V2) - CosHASep
        DCMinus = Cosang(SZ,CZ,SA,CA,Phi-EPS, V1, V2) - CosHASep
        DCGradient = (DCPlus-DCMinus)/EPS/2.0
        Phi -= DC/DCGradient
        DC = Cosang(SZ,CZ,SA,CA,Phi, V1, V2) - CosHASep
    
    # Calculate vector for polar axis
    PA =VGCC(SZ,CZ,SA,CA,Phi)
    
    # Now calculate RA and DEC
    PADEC = math.asin(PA[2])*180/math.pi
    PAHA = math.atan2(PA[0], PA[1])*12/math.pi
    
    if verbose: print("Phi:", Phi*180.0/math.pi)

    return PAHA, PADEC

# Next function formats the degrees as degrees, minutes and arcsec
def DegFormat(angle):
    degree_sign= '\N{DEGREE SIGN}'
    # Cope with 
    if angle >= 0:
        angsign = ""
    else:
        angsign = "-"
        angle = -angle

    # The plus 0.5/3600 is to cope with rounding to 1 arc second
    deg = int(angle+0.5/3600)
    angle -= deg
    angle *= 60
    # The plus 0.5/60 is to cope with rounding to 1 arc second
    minutes = int(angle+0.5/60)
    angle -= minutes
    angle *= 60
    seconds = int(angle+0.5)
    out = angsign+str(deg) + degree_sign + " " + str(minutes) + "' " + str(seconds) + '"'
    return out

# Next function formats hour angles as hours, minutes and arcsec

def HourFormat(angle):
    # Cope with positive an negative angles
    if angle > 0:
        strsign = ""
    else:
        angle = -angle
        strsign = "-"
        
    deg = int(angle+0.5/3600) # Copes with rouding to nearest second
    angle -= deg
    angle *= 60
    minutes = int(angle+0.5/60) # Copes with rouding to nearest second
    angle -= minutes
    angle *= 60
    seconds = int(angle+0.5)
    out = strsign + str(deg) + "h " + str(minutes) + "' " + str(seconds) + '"'
    return out

def GetTestImageLinkResults(path):
    MESSAGE = " \
    /* Java Script */\
    ccdsoftCameraImage.Path = \"" + path + "\";\
    ccdsoftCameraImage.Open();\
    ha = ccdsoftCameraImage.FITSKeyword(\"TELEHA\");\
    lst = ccdsoftCameraImage.FITSKeyword(\"LST\");\
    psra = ccdsoftCameraImage.FITSKeyword(\"CRVAL1\");\
    psdec = ccdsoftCameraImage.FITSKeyword(\"CRVAL2\");\
    ccdsoftCameraImage.Close();\
    out = ha + '|' + lst + '|' + psra + '|' + psdec;\
    "
    data = TSXSendTry(MESSAGE)
    spdataha  = data[0].split()
    hadata    = abs(float(spdataha[0])) + float(spdataha[1])/60.0 + \
                float(spdataha[2])/3600.0
    ha = math.copysign(hadata, float(spdataha[0]))
    spdatalst = data[1].split()
    lstdata   = abs(float(spdatalst[0])) + float(spdatalst[1])/60.0 + \
                float(spdatalst[2])/3600.0
    lst = math.copysign(lstdata, float(spdatalst[0]))
    return ha, lst, float(data[2]), float(data[3])

def GetTestDat(tha, lst ,ra, dec, i):
    return (tha[i], lst[i], ra[i], dec[i])

# Resets image bin and filter state
def RestoreCameraState():
    global initfilter
    SetImageBin(initbin)
    queue.put(logtime()+"Reset camera bin state")
    if CAM_FILTER != "":
        TSXSendTry("ccdsoftCamera.FilterIndexZeroBased = " + \
                                 str(initfilter) + ";")
        queue.put(logtime()+"Reset filter wheel position")
        
def PolarAlign(queue):
    global initbin
    # Store current bin state
    initbin = GetImageBin()
    
    # if using test data from Mathematica, read in from file
    if testdata:
        lstdat = []
        thadat = []
        radat = []
        decdat = []
        npoints = 0
        
        for line in open("test.data"):
            listWords = line.split("\t")
            if listWords[0] != "\n":
                lstdat.append(float(listWords[0]))
                thadat.append(float(listWords[1]))
                radat.append(float(listWords[2]))
                decdat.append(float(listWords[3]))
                npoints += 1

    else:
        # Start up - connect to all devices - exit if there is an error
        if connectscope():
            queue.put("!Ensure Scope Connected Properly")
            finish_async_code()
            return
        if connectcamera():
            queue.put("!Ensure Camera Connected Properly")
            finish_async_code()
            return
        if CAM_FILTER != "":
            if connectfilterwheel():
                queue.put("!Ensure FilterWheel Connected Properly")
                finish_async_code()
                return
            if setfilter(CAM_FILTER):
                queue.put("!Could not set filter - check filter name")
                finish_async_code()
                return
                
            
        
    # Now slew to first target point
    # First Get Long, Lat, LST and UT (only need LST) to convert to RA
    lat, longitude, LST, UT =  LatLongLstUT()
    
    RA1 = LST - HAI1
    
    if end_async_code_check():
        queue.put(logtime() + "Stopped polar aligment routine.")
        # Restore initial camera state
        RestoreCameraState()
        finish_async_code()
        
        return

    else:
        if not testdata:
            queue.put(logtime() + "Slewing to first polar alignment point")
            # Ensure mount is unparked
            unpark()
            SlewToRaAndDec(RA1, PA_DEC, "PA 1")        
        
    if end_async_code_check():
        queue.put(logtime() + "Completed Slewing")
        # Restore initial camera state
        RestoreCameraState()
        finish_async_code()

        return
    else:
        if not testdata:
            queue.put(logtime() + "Taking first image")
            takeimagebin(CAM_DURATION, CAM_BINNING)
        
    #iha1, ilst1, ira1, idec1 = GetTestImageLinkResults("/home/stellarmate/TheSkyXImages/February 24 2024/PA_1_4x4_4.000secs_-10.00C_00001422.fit")
    if testdata:
        iha1, ilst1, ira1, idec1 = GetTestDat(thadat, lstdat, radat, decdat, 0)
    else:
        if simulating: # DSS images do not containt HA and LST data
            iha1 = HAI1
            ilst1 = LST
        else:
            iha1, ilst1 = GetImageHAandLST()
    
        queue.put(logtime() + "Image HA: " + HourFormat(iha1) + " LST: " + HourFormat(ilst1))

    
        ierr = ImageLinkLastImage(CAM_SCALE)
        ierrsolve, ira1, idec1 = GetImageLinkResults()
        if (ierr > 0 or ierrsolve > 0):
            queue.put("!"+logtime()+"Exiting. Could not image link image")
            # Restore initial camera state
            RestoreCameraState()
            finish_async_code()
            return
        
        queue.put(logtime() + "Solved image RA: " + HourFormat(ira1) + \
              " and Dec: " + DegFormat(idec1))
    
    # Repeat for second point
    lat, longitude, LST, UT =  LatLongLstUT()
    RA2 = LST - HAI2

    if end_async_code_check():
        queue.put(logtime() + "Completed taking first image")
        # Restore initial camera state
        RestoreCameraState()
        finish_async_code()
        return
    
    else:
        if not testdata:
            queue.put(logtime() + "Slewing to second polar alignment point")
            SlewToRaAndDec(RA2, PA_DEC, "PA 2")

    if end_async_code_check():
        queue.put(logtime() + "Completed slewing to second alignment point")
        # Restore initial camera state
        RestoreCameraState()
        finish_async_code()
        return
    
    else:
        if not testdata:
            queue.put(logtime() + "Taking second image")
            takeimagebin(CAM_DURATION, CAM_BINNING)

    if testdata:
        iha2, ilst2, ira2, idec2 = GetTestDat(thadat, lstdat, radat, decdat, 1)
    else:
        if simulating: # DSS images don't contain HA and LST data 
            iha2 = HAI2
            ilst2 = LST
        else:
            iha2, ilst2 = GetImageHAandLST()

        queue.put(logtime() + "Image HA: " + HourFormat(iha2) + \
                  " LST: " + HourFormat(ilst2))
        ierr = ImageLinkLastImage(CAM_SCALE)
        ierrsolve, ira2, idec2 = GetImageLinkResults()
        
        if (ierr > 0 or ierrsolve > 0):
            queue.put("!"+logtime()+"Exiting. Could not image link image")
            # Restore initial camera state
            RestoreCameraState()
            finish_async_code()
            return
        
        queue.put(logtime() + "Solved image RA: " + HourFormat(ira2), \
                      " and Dec: " + DegFormat(idec2))
    
    # Set up variables for polar alignment solution
    D1 = idec1
    RA1 = ira1
    LST1 = ilst1
    THA1 = iha1
    D2 = idec2
    RA2 = ira2
    LST2 = ilst2
    THA2 = iha2
    
    # Test out polar alignment solution
    #D1 = 60.0
    #RA1 = 0.0
    #LST1 = 0.0
    #THA1 = 0.0
    #D2= 61.848
    #LST2 = 0.0
    #RA2 = 21.3226
    #THA2 = 3.0
    
    PAHA, PADEC = PASolve(RA1, D1, LST1, THA1, RA2, D2, LST2, THA2)
    #PAAlt, PAAz = AltAzfromHADEC(PAHA, PADEC)
    PAAlt, PAAz = AltAzfromHADECLat(PAHA, PADEC, lat)
    
    # Calculate difference from 360 if > 180.
    if PAAz > 180.0:
        PAAz = PAAz - 360.0
        
    queue.put(logtime()+"PA Alt: "+ DegFormat(PAAlt) +  " PAAz: "+ DegFormat(PAAz))
    queue.put(logtime()+ "Alt change: " + DegFormat(PAAlt-lat) + \
              " Az Change: " + DegFormat(PAAz))
    
    # Now work out alt az of last image so can compare against new images
    I2HA = ilst2 - ira2
    I2Alt, I2Az = AltAzfromHADECLat(I2HA, idec2, lat)

    # Work out target Alt Az when successful PA
    TargetAlt, TargetAz = RotateAltAz(I2Alt, I2Az, PAAlt-lat, PAAz)
    
    if TargetAz > 180.0:
        TargetAz = TargetAz - 360.0
        
    # Work out target HA, Dec when successful PA
    TargetHA, TargetDec = HADECfromAltAz(TargetAlt, TargetAz)

    theta, phi = BruteRotationSearch(I2Alt, I2Az, TargetAlt, TargetAz)
    # Adjust theta, phi depending on the hemisphere:
    # Code below mutiplies by -1 if southern hemisphere, 1 if Northern
    theta = theta * math.copysign(1, lat)
    phi   = phi   * math.copysign(1, lat)
    
    queue.put("|"+str(theta)+"|"+str(phi)+"|")
    if phi > 0:
        queue.put(logtime()+"Azimuthal: Rotate counter clockwise by " + \
                  DegFormat(abs(phi)))
    else:
        queue.put(logtime()+"Azimuthal: Rotate clockwise by " + \
                  DegFormat(abs(phi)))
        
    if theta > 0:
        queue.put(logtime()+"Altitude: lower axis by " + \
              DegFormat(abs(theta)))
    else:
        queue.put(logtime()+ "Altitude: raise axis by " +  \
              DegFormat(abs(theta)))
        
    n = 1
    while (not end_async_code_check()) and \
          (True if not testdata else n < npoints-1):
        n += 1
        queue.put(logtime() + "Taking image")
        #imagepath = "/home/stellarmate/TheSkyXImages/February 24 2024/PA_2_4x4_4.000secs_-10.00C_0000" + str(1422+n) +".fit"
        #iha, ilst, ira, idec = GetTestImageLinkResults(imagepath)
        if testdata:
            iha, ilst, ira, idec = GetTestDat(thadat, lstdat, radat, decdat, n)
            ierr = 0
            ierrsolve = 0
            time.sleep(2)
        else:
            takeimagebin(CAM_DURATION, CAM_BINNING)

            if simulating: # DSS images don't contin HA and LST data 
                lat, longitude, LST, UT =  LatLongLstUT()
                iha = HAI2
                ilst = LST
            else:
                iha, ilst = GetImageHAandLST()

            ierr = ImageLinkLastImage(CAM_SCALE)
            ierrsolve, ira, idec = GetImageLinkResults()
            
        if (ierr ==0 and ierrsolve == 0):
            # Calculate true iha from solved RA and Dec
            iha = ilst-ira
            # Calculate Alt and Az from Ha and Dec
            ialt, iaz = AltAzfromHADECLat(iha, idec, lat)
            if iaz > 180:
                iaz =iaz - 360
                if verbose :
                    print("New Alt", DegFormat(ialt), "New Az", DegFormat(iaz))
                
            # Now work out where Target postion would have rotated to
            iha2 = ilst - ilst2 + TargetHA

            TargetAlt, TargetAz = AltAzfromHADECLat(iha2, TargetDec, lat)

            if TargetAz > 180:
                TargetAz = TargetAz - 360.0

            if verbose:
                print("TargetAlt", DegFormat(TargetAlt), "TargetAz", DegFormat(TargetAz))
                print("ImageAlt", DegFormat(ialt), "ImageAz", DegFormat(iaz))

            theta, phi = BruteRotationSearch(ialt, iaz, TargetAlt, TargetAz)
            # Adjust theta, phi depending on the hemisphere:
            # Code below mutiplies by -1 if southern hemisphere, 1 if Northern
            theta = theta * math.copysign(1, lat)
            phi   = phi   * math.copysign(1, lat)

            if simulating: # Test of interface
                # Gradually increase theta and phi
                theta = (theta+n*0.1)*(-1)**n
                phi = (phi+n*0.1)*(-1)**n
            
            queue.put("|"+str(theta)+"|"+str(phi)+"|")
            if phi > 0:
                queue.put(logtime()+"Azimuth: Rotate mount counter clockwise by " + \
                      DegFormat(abs(phi)))
            else:
                queue.put(logtime()+"Azimuth: Rotate mount clockwise by " + DegFormat(abs(phi)))
                
            if theta > 0:
                queue.put(logtime()+"Altitude: lower mount by " + \
                      DegFormat(abs(theta)))
            else:
                queue.put(logtime()+ "Altitude: raise mount by " + \
                      DegFormat(abs(theta)))
        else:            
            queue.put("<"+logtime()+"Could not plate solve image>")


    queue.put(logtime()+"Completed Polar Alignment")
    # Restore initial camera state
    RestoreCameraState()
    finish_async_code()

    return

def interrupt_handler(signum, frame):
    print(f'Handling signal {signum} ({signal.Signals(signum).name}).')

    global LOOPING
    LOOPING = False
    print("Will quit after next image.")

#if __name__ == "__main__":
#    signal.signal(signal.SIGINT, interrupt_handler)
#    MainRoutine()

# Start the Tkinter event loop
root.mainloop()
