import tkinter as tk
import time
import tempfile
import threading
from tkinter import ttk
from tkinter import*
from tkinter import messagebox
from PIL import ImageTk, Image
import serial
import serial.tools.list_ports
from serial import SerialException
from tkinter import messagebox
import os
import sys
import subprocess
import numpy as np
import json
from datetime import datetime
from glob import glob
import pygetwindow as gw
from PIL import ImageGrab
import sys
import os
from tkinter import Tk
import re
import requests

from datetime import datetime
import socket
import webbrowser

FIREBASE_API_KEY =   "AIzaSyBJU0eISC9PZQbUNY-vS8DK1hRwDMeFVDk"
FIREBASE_PROJECT_ID = "spifcalibrationdata"

firebase_id_token = None
firebase_refresh_token = None
firebase_uid = None

def firebase_anonymous_login():
    global firebase_id_token
    global firebase_refresh_token
    global firebase_uid
    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signUp?key={FIREBASE_API_KEY}"
    )
    payload = {
        "returnSecureToken": True
    }
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )
        if response.status_code != 200:
            print("Firebase authentication failed:")
            print(response.text)
            return False
        data = response.json()
        firebase_id_token = data["idToken"]
        firebase_refresh_token = data["refreshToken"]
        firebase_uid = data["localId"]
        print("Firebase authentication successful")
        print("Anonymous UID:", firebase_uid)
        return True
    except requests.RequestException as e:
        print("Firebase connection error:", e)
        return False
    
    if firebase_anonymous_login():
        print("Firebase ready")
    else:
        print("Firebase login failed")

def firestore_url(document_path=""):
    return (
        "https://firestore.googleapis.com/v1/"
        f"projects/{FIREBASE_PROJECT_ID}/"
        f"databases/(default)/documents/{document_path}"
    )


def firestore_headers():
    if not firebase_id_token:
        raise RuntimeError("Firebase authentication token is missing.")

    return {
        "Authorization": f"Bearer {firebase_id_token}",
        "Content-Type": "application/json"
    }


def firestore_encode_fields(data):
    fields = {}

    for key, value in data.items():

        if isinstance(value, bool):
            fields[key] = {
                "booleanValue": value
            }

        elif isinstance(value, int):
            fields[key] = {
                "integerValue": str(value)
            }

        elif isinstance(value, float):
            fields[key] = {
                "doubleValue": value
            }

        elif isinstance(value, str):
            fields[key] = {
                "stringValue": value
            }

        elif value is None:
            fields[key] = {
                "nullValue": None
            }

    return fields


def firestore_decode_fields(fields):
    result = {}

    for key, value in fields.items():

        if "stringValue" in value:
            result[key] = value["stringValue"]

        elif "integerValue" in value:
            result[key] = int(value["integerValue"])

        elif "doubleValue" in value:
            result[key] = float(value["doubleValue"])

        elif "booleanValue" in value:
            result[key] = value["booleanValue"]

        elif "nullValue" in value:
            result[key] = None

    return result


def firestore_set_document(document_path, data):

    url = firestore_url(document_path)

    payload = {
        "fields": firestore_encode_fields(data)
    }

    response = requests.patch(
        url,
        headers=firestore_headers(),
        json=payload,
        timeout=15
    )

    if response.status_code not in (200, 201):
        print("Firestore write failed:")
        print(response.status_code)
        print(response.text)
        return False

    return True


def firestore_get_document(document_path):

    url = firestore_url(document_path)

    response = requests.get(
        url,
        headers=firestore_headers(),
        timeout=15
    )

    if response.status_code == 404:
        return None

    if response.status_code != 200:
        print("Firestore read failed:")
        print(response.status_code)
        print(response.text)
        return None

    document = response.json()

    return firestore_decode_fields(
        document.get("fields", {})
    )


def firestore_list_documents(collection_path):
    url = firestore_url(collection_path)
    response = requests.get(
        url,
        headers=firestore_headers(),
        timeout=15
    )
    if response.status_code != 200:
        print("Firestore list failed:")
        print(response.status_code)
        print(response.text)
        return []
    return response.json().get("documents", [])

class RootGui:
    @staticmethod
    def resource_path(relative_path):
        """ Get the absolute path, works with PyInstaller """
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def __init__(self):
        """ Initializing the root GUI"""
        self.root = Tk()

        icon_path = self.resource_path("liftlg.ico")
        try:
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Tkinter icon failed: {e}")

        self.root.title("SPIF Calibration Tool")
        window_width = 950
        window_height = 860
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        # connect close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
             
    def on_closing(self):
        top = tk.Toplevel(self.root)
        top.title("Reminder")
        screen_width = top.winfo_screenwidth()
        screen_height = top.winfo_screenheight()    
        width = 250
        height = 100
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.grab_set()
        msg = tk.Label(
            top,
            text="Please save your data before closing.",
            font=("Helvetica", 10)
        )
        msg.pack(pady=10)

        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=10)

        def stay():
            top.destroy()

        def exit_anyway():
            top.destroy()
            self.root.destroy()

        tk.Button(btn_frame, text="Save First", width=12, command=stay)\
            .grid(row=0, column=0, padx=10)

        tk.Button(btn_frame, text="Exit Anyway", width=12, command=exit_anyway)\
            .grid(row=0, column=1, padx=10)


class ComGui():
    print("Creating the widgets to display and send data from/to Arduino ")

    """
    Class to create all the widgets

    """
    rootFolder = "C:/Users/eduar/OneDrive/Documents/CalibrationData"
    def open_resource(self, event=None):
        webbrowser.open("https://anjan-276.github.io/SPIFCalibrationSOP/")
    def __init__(self, root, serial):
        self.root = root
        self.root.grid_rowconfigure(998, weight=1)
        self.serial = serial
        self.suspension_type = StringVar()
        self.suspension_type.set("0.0")
        self.selected_value1 = StringVar()
        self.mode_operand = StringVar()
        self.mode_operand.set("0.0")
        self.displayVar = StringVar()
        self.displayVar.set(" ")
        self.set_pressure = StringVar()
        self.set_pressure.set("0.0")


        self.lift_slope = 0
        self.lift_intercept = 0
        self.tandem_slope = 0
        self.tandem_intercept = 0
        self.lower_slope = 0
        self.lower_intercept = 0

        self.mLift = 0
        self.bLift = 0
        self.mMTP = 0
        self.bMTP = 0

        self.mGVWU = 0
        self.bGVWU = 0
        self.mGVWD = 0
        self.bGVWD = 0
        self.bool = BooleanVar()
        self.bool.set(True)
        
        self.VIN = StringVar()
        self.percent = 0.5

        self.schedule_type = LabelFrame(self.root, text = "", width = 10)
        self.schedule_type.grid(row = 0, column = 0, padx = 30, pady = 10, sticky ="wn", ipadx = 10, ipady = 3)

        self.suspValue = ["Suspension", "Walking Beam", "Air Ride", "TufTrac"]
        self.valueDrop = ttk.Combobox(
            self.schedule_type,
            values=self.suspValue,
            font=('Helvetica',10,'bold'),
            width=15
        )
        self.valueDrop.current(0)
        
        self.valueDrop.grid(row = 1, column = 0, padx = 5, pady = 5, ipadx = 5, ipady = 5)
        self.valueDrop.bind("<<ComboboxSelected>>", self.Suspension)
        self.scheValue = [ "Schedule", "Schedule 21", "Schedule 23"]
        self.valueDrop1 = ttk.Combobox(
            self.schedule_type,
            values=self.scheValue,
            font=('Helvetica',10,'bold'),
            width=15
        )
        self.valueDrop1.current(0)
        self.valueDrop1.grid(row = 0, column = 0, padx = 5, pady = 5, ipadx = 15, ipady = 5)
        print(f"Schedule from Value Drop 1: {self.valueDrop1.get()} ")
        self.selected_value1.set(self.valueDrop1.get())
        print(f"selected value 1: {self.selected_value1.get()}")
        self.valueDrop1.bind("<<ComboboxSelected>>", self.Schedule)
        Label(self.schedule_type, text="VIN:").grid(row=3, column=0, sticky=W)
        self.VIN = Entry(self.schedule_type, textvariable=self.VIN, width=20)
        self.VIN.grid(row=3, column=0, padx = 30, pady = 10, ipadx = 20)

        
        self.frToLift = DoubleVar()
        self.liftToFrTan = DoubleVar()
        self.tanSpacing = DoubleVar()

        self.lengthFr = LabelFrame(
            self.root,
            text="Length (Meters)",
            width=10,
            highlightthickness=3,
            font=('Helvetica', 10, 'bold')
        )
        self.lengthFr.grid(row=0, column=1, sticky = "wn", ipadx=10, ipady=3)
        Label(self.lengthFr, text="Front-Lift:").grid(row=0, column=0, sticky=E)
        self.frToLiftEntry = Entry(self.lengthFr, textvariable=self.frToLift, width=10)
        self.frToLiftEntry.grid(row=0, column=1, padx=1, pady=2)
        Label(self.lengthFr, text="Lift to Front Tandem:").grid(row=1, column=0, sticky=E)
        self.liftToFrTanEntry = Entry(self.lengthFr, textvariable=self.liftToFrTan, width=10)
        self.liftToFrTanEntry.grid(row=1, column=1, padx=1, pady=2)

        Label(self.lengthFr, text="Tandem Spacing:").grid(row=2, column=0, sticky=E)
        self.tanSpacingEntry = Entry(self.lengthFr, textvariable=self.tanSpacing, width=10)
        self.tanSpacingEntry.grid(row=2, column=1, padx=1, pady=2)
        self.scheBt = Button(
            self.lengthFr,
            text="Send",
            foreground='green',
            font=('Helvetica', 8, 'bold'),
            command=self.run_spif
        )   
        self.scheBt.grid(row=3, column=1, sticky="e", padx=5, pady=3)

        
        # ADD THIS: parent container for stacking
        self.right_panel = Frame(self.root)
        self.right_panel.grid(row=0, column=2, sticky="wn", padx=10)
        
        # RIGHT PANEL
        # =========================
        self.right_panel = Frame(self.root)
        self.right_panel.grid(row=0, column=2, sticky="wn", padx=10)
        self.modes_select = LabelFrame(
            self.right_panel,
            text="Operation Modes",
            font=('Helvetica', 10, 'bold')
        )
        self.modes_select.pack(fill="x", pady=5)
        self.modes_select.grid_columnconfigure(0, weight=1)

        self.mode_btn_frame = Frame(self.modes_select)
        self.mode_btn_frame.grid(row=0, column=0, sticky="ew")

        # Force horizontal expansion
        self.mode_btn_frame.grid_columnconfigure((0,1,2), weight=1)

        Button(self.mode_btn_frame, text="↑",
            font=('Helvetica', 10, 'bold'),
            command=lambda: self.operationMode("up")
        ).grid(row=0, column=0, padx=5, sticky="ew")

        Button(self.mode_btn_frame, text="↓",
            font=('Helvetica', 10, 'bold'),
            command=lambda: self.operationMode("down")
        ).grid(row=0, column=1, padx=5, sticky="ew")

        Button(self.mode_btn_frame, text="auto",
            font=('Helvetica', 10, 'bold'),
            command=lambda: self.operationMode("auto")
        ).grid(row=0, column=2, padx=5, sticky="ew")

        Label(self.modes_select, textvariable=self.displayVar)\
            .grid(row=1, column=0, pady=5, sticky="ew")

        # =========================
        # PRESSURE BLOCK
        # =========================
        self.press_select = LabelFrame(
            self.right_panel,
            text="Set Pressure",
            font=('Helvetica', 10, 'bold')
        )
        self.press_select.pack(fill="x", pady=5)

        self.press_select.grid_columnconfigure(0, weight=1)

        self.press_frame = Frame(self.press_select)
        self.press_frame.grid(row=0, column=0, sticky="ew")

        self.press_frame.grid_columnconfigure((0,1,2), weight=1)

        Label(self.press_frame, text="Pressure:").grid(row=0, column=0)

        self.pressEntry = Entry(
            self.press_frame,
            textvariable=self.set_pressure,
            width=10
        )
        self.pressEntry.grid(row=0, column=1, padx=5, sticky="ew")

        Button(
            self.press_frame,
            text="Send",
            foreground='green',
            font=('Helvetica', 8, 'bold'),
            command=lambda: self.Pressure(self.set_pressure.get())
        ).grid(row=0, column=2, padx=5, sticky="ew")
        self.readingFr = LabelFrame(self.root, text = "Sensor Readings", width = 10, highlightthicknes = 3, font = ('Helvetica', 10, 'bold'))
        self.readingFr.grid(row = 1, column = 0, padx = 30, pady = 10, ipadx = 20, ipady = 10)
        suspLb = Label(self.readingFr, text = "Suspension Type:").grid(row = 0, column = 0, sticky = E)
        axleLb = Label(self.readingFr, text = "Axle Position:", justify = "left", anchor = E).grid(row = 1, column = 0, sticky = E)
        pressurelb = Label(self.readingFr, text = "Set Pressure:").grid(row = 2, column = 0, sticky = E)
        ridebaglb = Label(self.readingFr, text = "Ride Bag Pressure (RBP):").grid(row = 3, column = 0, sticky = E)
        speedlb = Label(self.readingFr, text = "Speed:").grid(row = 4, column = 0, sticky = E)
        directionlb = Label(self.readingFr, text = "Direction:").grid(row = 5, column = 0, sticky = E)
        reverselb = Label(self.readingFr, text = "Reverse:").grid(row = 6, column = 0, sticky = E)
        fourWaylb = Label(self.readingFr, text = "4-WAY:").grid(row = 7, column = 0, sticky = E)
        tandemSensorlb = Label(self.readingFr, text = "Tandem Sensor:").grid(row = 8, column = 0, sticky = E)
        btStatelb = Label(self.readingFr, text = "Button State:").grid(row = 9, column = 0, sticky = E)
        weightlb = Label(self.readingFr, text = "Truck Total Weight:").grid(row = 10, column = 0, sticky = E)
        lowerlb = Label(self.readingFr, text = "Lower:").grid(row = 11, column = 0, sticky = E)
        liftlb = Label(self.readingFr, text = "Lift:").grid(row = 12, column = 0, sticky = E)
        MTPlb = Label(self.readingFr, text = "MTP:").grid(row = 13, column = 0, sticky = E)

        self.suspTypeLb = StringVar()
        self.posLb = StringVar()
        self.setLb = StringVar()
        self.bagpressLb = StringVar()
        self.speedLb = StringVar()
        self.dircLb = StringVar()
        self.revrsLb = StringVar()
        self.fourLb = StringVar()
        self.tandemLb = StringVar()
        self.btStateLb = StringVar()
        self.weightLb = StringVar()
        self.lowerLb = StringVar() 
        self.liftLb = StringVar()
        self.MTPLb = StringVar()
        self.frontWeight = StringVar()
        self.schedule21_23 = StringVar()
        self.liftWeight = StringVar()
        self.tandemWeight = StringVar()
        self.totalWeight = StringVar()
        self.scheduleInfo = StringVar()
        
        lab1 = Label(self.readingFr, textvariable = self.suspTypeLb, width = 12, font = ('Helvetica', 10, 'bold')).grid(row = 0, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.posLb, font = ('Helvetica', 10, 'bold')).grid(row = 1, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.setLb, font = ('Helvetica', 10, 'bold')).grid(row = 2, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.bagpressLb, font = ('Helvetica', 10, 'bold')).grid(row = 3, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.speedLb, font = ('Helvetica', 10, 'bold')).grid(row = 4, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.dircLb, font = ('Helvetica', 10, 'bold')).grid(row = 5, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.revrsLb, font = ('Helvetica', 10, 'bold')).grid(row = 6, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.fourLb, font = ('Helvetica', 10, 'bold')).grid(row = 7, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.tandemLb, font = ('Helvetica', 10, 'bold')).grid(row = 8, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.btStateLb, font = ('Helvetica', 10, 'bold')).grid(row = 9, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.weightLb, font = ('Helvetica', 10, 'bold')).grid(row = 10, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.lowerLb, font = ('Helvetica', 10, 'bold')).grid(row = 11, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.liftLb, font = ('Helvetica', 10, 'bold')).grid(row = 12, column = 1)
        lab1 = Label(self.readingFr, textvariable = self.MTPLb, font = ('Helvetica', 10, 'bold')).grid(row = 13, column = 1)

        self.emptyFr = LabelFrame(self.root, text = "Empty Weight(KG)", width = 10, highlightthicknes = 3, font = ('Helvetica', 10, 'bold'))
        self.emptyFr.grid(row = 1, column = 1, sticky ="wn", padx = 10, pady = 10, ipadx = 10, ipady = 10)
        self.eUPlb = Label(self.emptyFr, text = "Lift Axle Up", font = ('Helvetica', 8, 'bold')).grid(row = 0, column = 1)
        self.lb1 = Label(self.emptyFr, text = "Front:").grid(row = 1, column = 0, sticky = E)
        self.lb1 = Label(self.emptyFr, text = "Lift:").grid(row = 2, column = 0, sticky = E)
        self.lb1 = Label(self.emptyFr, text = "Front Tandem:").grid(row = 3, column = 0, sticky = E)
        self.lb1 = Label(self.emptyFr, text = "Rear Tandem:").grid(row = 4, column = 0, sticky = E)
        self.lb1 = Label(self.emptyFr, text = "Tandem Sensor:").grid(row = 5, column = 0, sticky = E)
        self.lb1 = Label(self.emptyFr, text = "Pressure(RBP):").grid(row = 6, column = 0, sticky = E)
        self.lb1 = Label(self.emptyFr, text = "GVW:").grid(row = 8, column = 0, sticky = E)

        self.frontEUP = IntVar()
        self.liftEUP = IntVar()
        self.frontTandemEUP = IntVar()
        self.rearREUP = IntVar()
        self.tandemSensorEUP = DoubleVar()
        self.GVWEUP = IntVar()
        self.gvw1 = IntVar()
        

        self.fronte = Entry(self.emptyFr, textvariable = self.frontEUP, width = 10).grid(row = 1, column = 1, padx = 5, pady = 5)
        self.frontTandeme = Entry(self.emptyFr, textvariable = self.frontTandemEUP, width = 10).grid(row = 3, column =1, pady = 5)
        self.rearRe = Entry(self.emptyFr, textvariable = self.rearREUP, width = 10).grid(row = 4, column = 1, padx = 5, pady = 5)
        self.tandemSensore = Entry(self.emptyFr, textvariable = self.tandemSensorEUP, width = 10).grid(row = 5, column = 1, padx = 5, pady = 5)
        self.btEup = Button(self.emptyFr, text = "Calc", foreground = 'green', font = ('Helvetica', 8, 'bold'), command = self.GVW_1).grid(row = 7, column = 1, padx = 5, pady = 5)
        self.gvw11 = Label(self.emptyFr, textvariable = self.gvw1).grid(row = 8, column = 1)
        


        self.eDNlb = Label(self.emptyFr, text = "Lift Axle Down", font = ('Helvetica', 8, 'bold')).grid(row = 0, column = 2)
        self.frontEDW = IntVar()
        self.liftEDW = IntVar()
        self.frontTandemEDW = IntVar()
        self.rearREDW = IntVar()
        self.tandemSensorEDW = DoubleVar()
        self.pressureEDW = DoubleVar()
        self.GVWEDW = IntVar()
        self.gvw2 = IntVar()
        self.frToGVWE = IntVar()
        self.frToGVWL = IntVar()
        self.GVWDiffE = IntVar()
        self.GVWDiffL = IntVar()
        self.liftToTanDiffE = IntVar()
        self.liftToTanDiffL = IntVar()

        self.fronte = Entry(self.emptyFr, textvariable = self.frontEDW, width = 10).grid(row = 1, column = 2, padx = 5, pady = 5)
        self.lifte = Entry(self.emptyFr, textvariable = self.liftEDW, width = 10).grid(row = 2, column = 2, padx = 5, pady = 5)
        self.frontTandeme = Entry(self.emptyFr, textvariable = self.frontTandemEDW, width = 10).grid(row = 3, column =2, pady = 5)
        self.rearRe = Entry(self.emptyFr, textvariable = self.rearREDW, width = 10).grid(row = 4, column = 2, padx = 5, pady = 5)
        self.tandemSensore = Entry(self.emptyFr, textvariable = self.tandemSensorEDW, width = 10).grid(row = 5, column = 2, padx = 5, pady = 5)
        self.presse = Entry(self.emptyFr, textvariable = self.pressureEDW, width = 10).grid(row = 6, column = 2, padx = 5, pady = 5)
        self.btEdw = Button(self.emptyFr, text = "Calc", foreground = 'green', font = ('Helvetica', 8, 'bold'), command = self.GVW_2).grid(row = 7, column = 2, padx = 5, pady = 5)
        self.gvw22 = Label(self.emptyFr, textvariable = self.gvw2).grid(row = 8, column = 2)
        
        self.frToGVWE.set(0)
        self.GVWDiffE.set(0)
        self.liftToTanDiffE.set(0)
        
        
        self.loadedFr = LabelFrame(self.root, text = "Loaded Weight(KG)", width = 10, highlightthicknes = 3, font = ('Helvetica', 10, 'bold'))
        self.loadedFr.grid(row = 1, column = 2, sticky ="wn", padx = 10, pady = 10, ipadx = 10, ipady = 10)
        self.lUPlb = Label(self.loadedFr, text = "Lift Axle Up", font = ('Helvetica', 8, 'bold')).grid(row = 0, column = 1)
        self.lb1 = Label(self.loadedFr, text = "Front:").grid(row = 1, column = 0, sticky = E)
        self.lb1 = Label(self.loadedFr, text = "Lift:").grid(row = 2, column = 0, sticky = E)
        self.lb1 = Label(self.loadedFr, text = "Front Tandem:").grid(row = 3, column = 0, sticky = E)
        self.lb1 = Label(self.loadedFr, text = "Rear Tandem:").grid(row = 4, column = 0, sticky = E)
        self.lb1 = Label(self.loadedFr, text = "Tandem Sensor:").grid(row = 5, column = 0, sticky = E)
        self.lb1 = Label(self.loadedFr, text = "Pressure(RBP):").grid(row = 6, column = 0, sticky = E)
        self.lb1 = Label(self.loadedFr, text = "GVW:").grid(row = 8, column = 0, sticky = E)
        
        self.frToGVWL.set(0)
        self.GVWDiffL.set(0)
        self.liftToTanDiffL.set(0)
        
        self.frontLUP = IntVar()
        self.liftLUP = IntVar()
        self.frontTandemLUP = IntVar()
        self.rearRLUP = IntVar()
        self.tandemSensorLUP = DoubleVar()
        self.GVWLUP = IntVar()
        self.gvw3 = IntVar()


        self.fronte = Entry(self.loadedFr, textvariable = self.frontLUP, width = 10).grid(row = 1, column = 1, padx = 5, pady = 5)
        self.frontTandeme = Entry(self.loadedFr, textvariable = self.frontTandemLUP, width = 10).grid(row = 3, column =1, pady = 5)
        self.rearRe = Entry(self.loadedFr, textvariable = self.rearRLUP, width = 10).grid(row = 4, column = 1, padx = 5, pady = 5)
        self.tandemSensore = Entry(self.loadedFr, textvariable = self.tandemSensorLUP, width = 10).grid(row = 5, column = 1, padx = 5, pady = 5)
        self.btLup = Button(self.loadedFr, text = "Calc", foreground = 'green', font = ('Helvetica', 8, 'bold'), command = self.GVW_3).grid(row = 7, column = 1, padx = 5, pady = 5)
        self.gvw33 = Label(self.loadedFr, textvariable = self.gvw3).grid(row = 8, column = 1)
        self.frToGVWL.set(0)
        self.lDNlb = Label(self.loadedFr, text = "Lift Axle Down", font = ('Helvetica', 8, 'bold')).grid(row = 0, column = 2)
        self.frontLDW = IntVar()
        self.liftLDW = IntVar()
        self.frontTandemLDW = IntVar()
        self.rearRLDW = IntVar()
        self.tandemSensorLDW = DoubleVar()
        self.pressureLDW = DoubleVar()
        self.GVWLDW = IntVar()
        self.gvw4 = IntVar()
        self.suspensionType = StringVar()


        self.fronte = Entry(self.loadedFr, textvariable = self.frontLDW, width = 10).grid(row = 1, column = 2, padx = 5, pady = 5)
        self.lifte = Entry(self.loadedFr, textvariable = self.liftLDW, width = 10).grid(row = 2, column = 2, padx = 5, pady = 5)
        self.frontTandeme = Entry(self.loadedFr, textvariable = self.frontTandemLDW, width = 10).grid(row = 3, column =2, pady = 5)
        self.rearRe = Entry(self.loadedFr, textvariable = self.rearRLDW, width = 10).grid(row = 4, column = 2, padx = 5, pady = 5)
        self.tandemSensore = Entry(self.loadedFr, textvariable = self.tandemSensorLDW, width = 10).grid(row = 5, column = 2, padx = 5, pady = 5)
        self.presse = Entry(self.loadedFr, textvariable = self.pressureLDW, width = 10).grid(row = 6, column = 2, padx = 5, pady = 5)
        self.btLdw = Button(self.loadedFr, text = "Calc", foreground = 'green', font = ('Helvetica', 8, 'bold'), command = self.GVW_4).grid(row = 7, column = 2, padx = 5, pady = 5)
        self.gvw44 = Label(self.loadedFr, textvariable = self.gvw4).grid(row = 8, column = 2)


        self.calc = LabelFrame(self.root, text = "Compute", width = 10, highlightthicknes = 3, font = ('Helvetica', 10, 'bold'))
        self.calc.grid(row = 2, column = 1, sticky = "wn", padx = 10, pady = 10, ipadx = 10, ipady = 10)
        self.label1 = Label(self.calc, text = "LOWER:").grid(row = 0, column = 0, sticky = E)
        self.label2 = Label(self.calc, text = "LIFT:").grid(row = 1, column = 0, sticky = E)
        self.label3 = Label(self.calc, text = "MTP:").grid(row = 2, column = 0, sticky = E)
        self.calc5bt = Button(self.calc, text = "Calculate", foreground = 'green', font = ('Helvetica', 8, 'bold'), command = self.calc5).grid(row = 3, column = 0, sticky = "w", padx = 5, pady = 5)
        self.lowerVar = DoubleVar()
        self.liftVar = DoubleVar()
        self.MTPVar = DoubleVar()
        lab2 = Label(self.calc, textvariable = self.lowerVar).grid(row = 0, column = 1)
        lab2 = Label(self.calc, textvariable = self.liftVar).grid(row = 1, column = 1)
        lab2 = Label(self.calc, textvariable = self.MTPVar).grid(row = 2, column = 1)

        self.pointbt = Button(self.calc, text = "Send", foreground = 'green', font = ('Helvetica', 8, 'bold'), command = lambda: self.sendPoint(self.lowerVar.get(), self.liftVar.get(), self.MTPVar.get())).grid(row = 3, column = 1, sticky = "w", padx = 5, pady = 5)

        self.estFrWtEm = IntVar()
        self.estLiftWtEm = IntVar()
        self.estFrTanWtEm = IntVar()
        self.estRearTanWtEm = IntVar()
        self.estAvgTanWtEm = IntVar()
        self.estFrWtLd = IntVar()
        self.estLiftWtLd = IntVar()
        self.estFrTanWtLd = IntVar()
        self.estRearTanWtLd = IntVar()
        self.estAvgTanWtLd = IntVar()
        self.estPercentEm = IntVar()
        self.estPercentLd = IntVar()
        self.estValFr = LabelFrame(self.root, text = "Estimated Values(KG)", width = 10, highlightthicknes = 3, font = ('Helvetica', 10, 'bold'))
        self.estValFr.grid(row = 2, column = 0, sticky = 'wn', padx = 30, pady = 10, ipadx = 20, ipady = 10)
        self.emptyLb = Label(self.estValFr, text = "Empty", font = ('Helvetica', 8, 'bold')).grid(row = 0, column = 1, padx=10)
        self.loadedLb = Label(self.estValFr, text = "Loaded", font = ('Helvetica', 8, 'bold')).grid(row = 0, column = 2, padx = 10)
        self.label1 = Label(self.estValFr, text = "Front:").grid(row = 1, column = 0, sticky = E, padx = 5)
        label1 = Label(self.estValFr, textvariable = self.estFrWtEm).grid(row = 1, column = 1)
        label1 = Label(self.estValFr, textvariable = self.estFrWtLd).grid(row = 1, column = 2)
        self.label2 = Label(self.estValFr, text = "Lift:").grid(row = 2, column = 0, sticky = E, padx = 5)
        label1 = Label(self.estValFr, textvariable = self.estLiftWtEm).grid(row = 2, column = 1)
        label1 = Label(self.estValFr, textvariable = self.estLiftWtLd).grid(row = 2, column = 2)
        self.label3 = Label(self.estValFr, text = "Front Tandem:").grid(row = 3, column = 0, sticky = E, padx = 5)
        label1 = Label(self.estValFr, textvariable = self.estFrTanWtEm).grid(row = 3, column = 1)
        label1 = Label(self.estValFr, textvariable = self.estFrTanWtLd).grid(row = 3, column = 2)
        self.label3 = Label(self.estValFr, text = "Rear Tandem:").grid(row = 4, column = 0, sticky = E, padx = 5)
        label1 = Label(self.estValFr, textvariable = self.estRearTanWtEm).grid(row = 4, column = 1)
        label1 = Label(self.estValFr, textvariable = self.estRearTanWtLd).grid(row = 4, column = 2)
        self.label3 = Label(self.estValFr, text = "Front to GVW:").grid(row = 5, column = 0, sticky = E, padx = 5)
        label1 = Label(self.estValFr, textvariable = self.estPercentEm).grid(row = 5, column = 1)
        label1 = Label(self.estValFr, textvariable = self.estPercentLd).grid(row = 5, column = 2)
        
        self.menuFr = LabelFrame(self.root, text = "Menu", width = 10, highlightthicknes = 3, font = ('Helvetica', 10, 'bold'))
        self.menuFr.grid(row = 2, column = 2, sticky ="wn", padx = 10, pady = 10, ipadx = 10, ipady = 3)
        self.connect_bt = Button(self.menuFr, text = "Connect", command = self.openPort, width = 7, state = DISABLED, fg = 'black', font = ('Helvetica', 10, 'bold'))
        self.connect_bt.grid(row = 0, column = 0, padx = 15, pady = 15, ipadx = 1, ipady = 1)
        self.saveBt = Button(self.menuFr, text = "Save", command = self.saveOnClick, width = 7, fg = 'black', font = ('Helvetica', 10, 'bold'))
        self.saveBt.grid(row = 1, column = 0, padx = 15, pady = 15, ipadx = 1, ipady = 1)
        self.retrieveBt = Button(self.menuFr, text = "Retrieve", command = self.retrieveOnClick, width = 7, fg = 'black', font = ('Helvetica', 10, 'bold'))
        self.retrieveBt.grid(row = 1, column = 1, padx = 15, pady = 15, ipadx = 1, ipady = 1)
        self.helpBt = Button(self.menuFr, text = "Help", command = self.helpOnClick, width = 7, fg = 'black', font = ('Helvetica', 10, 'bold'))
        self.helpBt.grid(row = 0, column = 1, padx = 15, pady = 15, ipadx = 1, ipady = 1)
        self.summFr = LabelFrame(self.root, text="Summary", width=50, highlightthickness=3, font=('Helvetica', 10, 'bold'))
        self.summFr.grid_forget()  # hidden initially   
        
        self.resource = Label(
            self.root,
            text="More Information Here",
            fg="blue",
            cursor="hand2"
        )

        self.resource.bind("<Button-1>", self.open_resource)

        self.resource.place(
            relx=0.5,
            rely=0.98,
            anchor="s"
        )

    def summary(self):
        self.frToGVWSummE = StringVar()
        self.liftToTanSummE = StringVar()
        self.frToGVWSummL = StringVar()
        self.liftToTanSummL = StringVar()
        self.GVWDiffSummE = StringVar()
        self.GVWDiffSummL = StringVar()
        # ---------------- EMPTY / LOAD LOGIC ----------------
        if self.spifResult == 1:
            if self.frToGVWE.get() >= 19:
                self.frToGVWSummE.set("Good")
            else:
                self.frToGVWSummE.set("Redo calibration. Target ≥23% front axle weight.")

            if self.frToGVWL.get() >= 19:
                self.frToGVWSummL.set("Good")
            else:
                self.frToGVWSummL.set("Redo calibration. Target ≥23% front axle weight.")
        elif self.spifResult == 2:
            if self.frToGVWE.get() >= 23:
                self.frToGVWSummE.set("Good")
            else:
                self.frToGVWSummE.set("Redo calibration. Target ≥23% front axle weight.")
            if self.frToGVWL.get() >= 23:
                self.frToGVWSummL.set("Good")
            else:
                self.frToGVWSummL.set("Redo calibration. Target ≥23% front axle weight.")
        # ---------------- LIFT / TANDEM CHECK (EMPTY) ----------------
        if self.liftToTanDiffE.get() > 500:
            if self.spifResult == 1:
                if self.frToGVWE.get() > 21:
                    self.liftToTanSummE.set("Needs improvement. Reduce front axle load.")
                else:
                    self.liftToTanSummE.set("OK. As good as it gets.")
            elif self.spifResult == 2:
                if self.frToGVWE.get() > 25:
                    self.liftToTanSummE.set("Needs improvement. Reduce front axle load.")
                else:
                    self.liftToTanSummE.set("OK. As good as it gets.")
        else:
            self.liftToTanSummE.set("Good")
        # ---------------- LIFT / TANDEM CHECK (LOADED) ----------------
        if self.liftToTanDiffL.get() > 500:
            if self.spifResult == 1:
                if self.frToGVWL.get() > 21:
                    self.liftToTanSummL.set("Needs improvement. Reduce front axle load.")
                else:
                    self.liftToTanSummL.set("OK. As good as it gets.")
            elif self.spifResult == 2:
                if self.frToGVWL.get() > 25:
                    self.liftToTanSummL.set("Needs improvement. Reduce front axle load.")
                else:
                    self.liftToTanSummL.set("OK. As good as it gets.")
        else:
            self.liftToTanSummL.set("Good")
        if(self.GVWDiffE.get() > 200):
            self.GVWDiffSummE.set("Weight diff high. Reweigh to within 200 KG.")
        else:
            self.GVWDiffSummE.set("Good")
        if(self.GVWDiffL.get() > 200):
            self.GVWDiffSummL.set("Weight diff high. Reweigh to within 200 KG.")
        else:
            self.GVWDiffSummL.set("Good")
        # ---------------- CREATE SUMMARY UI ----------------
        self.summFr = LabelFrame(self.root, text="Summary", width=10, highlightthickness=3, font=('Helvetica', 10, 'bold'))
        self.summFr.grid(row=4, column=0, sticky=W, columnspan=4, padx=20, pady=0)
        # EMPTY
        Label(self.summFr, text="Empty", font=('Helvetica', 8, 'bold')).grid(row=0, column=1, sticky=W, padx=5)
        Label(self.summFr, text="Front to GVW %:", font=('Helvetica', 8, 'bold')).grid(row=1, column=0, sticky=W, padx=5)
        Label(self.summFr, text="Weight Equalization:", font=('Helvetica', 8, 'bold')).grid(row=2, column=0, sticky=W, padx=5)
        Label(self.summFr, text=f"{self.frToGVWE.get()}% → {self.frToGVWSummE.get()}").grid(row=1, column=1, sticky=W, padx=5)
        Label(self.summFr, text=f"{self.liftToTanDiffE.get()} KG → {self.liftToTanSummE.get()}").grid(row=2, column=1, sticky=W, padx=5)
        # LOADED
        Label(self.summFr, text="Loaded", font=('Helvetica', 8, 'bold')).grid(row=0, column=3, sticky=W, padx=5)
        Label(self.summFr, text=f"{self.frToGVWL.get()}% → {self.frToGVWSummL.get()}").grid(row=1, column=3, sticky=W, padx=5)
        Label(self.summFr, text=f"{self.liftToTanDiffL.get()} KG → {self.liftToTanSummL.get()}").grid(row=2, column=3, sticky=W, padx=5)
        #GVW
        Label(self.summFr, text="GVW Difference.:", font=('Helvetica', 8, 'bold')).grid(row=3, column=0, sticky=W, padx=5)
        Label(self.summFr, text=f"{self.GVWDiffE.get()} KG → {self.GVWDiffSummE.get()}").grid(row=3, column=1, sticky=W, padx=5)
        Label(self.summFr, text=f"{self.GVWDiffL.get()} KG → {self.GVWDiffSummL.get()}").grid(row=3, column=3, sticky=W, padx=5)
       
        
    root_gui = RootGui   
    def getVersion(self, filename):
        """
        Extract version number from SOP filename.
        Example:
        SOPForTruckCalibration2.0.0.pdf -> (2,0,0)
        """

        match = re.search(r'(\d+\.\d+\.\d+)', filename)

        if match:
            return tuple(map(int, match.group(1).split(".")))

        return (0, 0, 0)


    def helpOnClick(self):
        assets_path = self.root_gui.resource_path("assets")
        local_pdf = None

        if os.path.exists(assets_path):
            for file in os.listdir(assets_path):
                if file.startswith("SOPForTruckCalibration") and file.endswith(".pdf"):
                    if local_pdf is None or self.getVersion(file) > self.getVersion(local_pdf):
                        local_pdf = file

        local_pdf_path = os.path.join(assets_path, local_pdf) if local_pdf else None

        try:
            github_page = "https://anjan-276.github.io/SPIFCalibrationSOP/"
            html = requests.get(github_page + "index.html", timeout=5).text

            pdf_files = re.findall(r'href="(SOPForTruckCalibration[\d\.]+\.pdf)"', html)

            if pdf_files:
                latest_pdf = pdf_files[0]
                online_version = self.getVersion(latest_pdf)
                local_version = self.getVersion(local_pdf) if local_pdf else (0, 0, 0)

                if online_version > local_version:
                    pdf_url = github_page + latest_pdf
                    pdf_path = os.path.join(assets_path, latest_pdf)

                    response = requests.get(pdf_url, timeout=30)
                    response.raise_for_status()

                    with open(pdf_path, "wb") as f:
                        f.write(response.content)

                    if local_pdf_path and os.path.exists(local_pdf_path):
                        os.remove(local_pdf_path)

                    local_pdf_path = pdf_path

        except Exception as e:
            print("Could not check for SOP updates:", e)

        if local_pdf_path and os.path.exists(local_pdf_path):
            os.startfile(local_pdf_path)
        else:
            messagebox.showerror("Help", "No SOP document available.")
            
    def run_spif(self):
        self.spifResult = self.SPIFChecker(
        self.frToLift.get(),
        self.liftToFrTan.get(),
        self.tanSpacing.get()
    )
        self.valueDrop1.current(self.spifResult)
        
    def weightCalc(self, frToLift, liftToFrTan,tanSpacing,front, rear, GVWt, state):
        self.run_spif()
        percent = 0.5
        lowPercentLimit = 0
        if( self.spifResult == 1):
            lowPercentLimit = 0.19
        elif(self.spifResult == 2):
            lowPercentLimit = 0.23
        totalMoment = (
            front * (frToLift + liftToFrTan) +
            rear * (frToLift + liftToFrTan + tanSpacing)
        )
        A = np.array([
            [frToLift, frToLift + liftToFrTan, frToLift + liftToFrTan + tanSpacing],
            [1, 1, 1],
            [2, -1, -1] 
        ], dtype = float)

        try:
            B = np.array([totalMoment, GVWt * (1 - percent), 0], dtype = float)
            sol = np.linalg.solve(A, B)

            while np.any(sol < 0) and percent > lowPercentLimit:
                percent -= 0.02
                B = np.array([totalMoment, GVWt * (1 - percent), 0])
                sol = np.linalg.solve(A, B)

        except np.linalg.LinAlgError:
            print("Matrix error — check geometry inputs")
            return
        if(state == "empty"):
            self.estLiftWtEm.set(round(sol[0])) 
            self.estFrWtEm.set(round(GVWt*percent))
            self.estFrTanWtEm.set(round((sol[1] + sol[2]) / 2))
            self.estRearTanWtEm.set(round((sol[1] + sol[2]) / 2))
            self.estPercentEm.set(f"{round(percent*100)}%")
        if(state == "loaded"):
            self.estLiftWtLd.set(round(sol[0])) 
            self.estFrWtLd.set(round(GVWt*percent))
            self.estFrTanWtLd.set(round((sol[1] + sol[2]) / 2))
            self.estRearTanWtLd.set(round((sol[1] + sol[2]) / 2))
            self.estPercentLd.set(f"{round(percent*100)}%")        
        
    def onClickFxnEm(self):
        self.weightCalc(self.frToLift.get(),
                        self.liftToFrTan.get(),
                        self.tanSpacing.get(),
                        self.frontTandemEUP.get(),
                        self.rearREUP.get(),
                        self.GVWEUP,
                        "empty"
                        )
    def onClickFxnLd(self):
        self.weightCalc(self.frToLift.get(),
                        self.liftToFrTan.get(),
                        self.tanSpacing.get(),
                        self.frontTandemLUP.get(),
                        self.rearRLUP.get(),
                        self.GVWLUP,
                        "loaded")
        
    import socket

    def hasInternet(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
        
    def saveData(self):
        if not self.hasInternet():
            print("No internet connection")
            return 50
        timestamp = datetime.now().strftime("%Y-%m-%d||%H:%M:%S")
        # Collect data
        try:
            data = {
                "VIN": self.VIN.get(),
                "frToLift": self.frToLift.get(),
                "liftToFrTan": self.liftToFrTan.get(),
                "tanSpacing": self.tanSpacing.get(),
                "emFrWtUp": self.frontEUP.get(),
                "emFrTanWtUp": self.frontTandemEUP.get(),
                "emRearTanWtUp": self.rearREUP.get(),
                "emTanSenUp": self.tandemSensorEUP.get(),
                "emFrWtDw": self.frontEDW.get(),
                "emFrTanWtDw": self.frontTandemEDW.get(),
                "emRearTanWtDw": self.rearREDW.get(),
                "emTanSenDw": self.tandemSensorEDW.get(),
                "emLiftWt": self.liftEDW.get(),
                "emRBP": self.pressureEDW.get(),
                "ldFrWtUp": self.frontLUP.get(),
                "ldFrTanWtUp": self.frontTandemLUP.get(),
                "ldRearTanWtUp": self.rearRLUP.get(),
                "ldTanSenUp": self.tandemSensorLUP.get(),
                "ldFrWtDw": self.frontLDW.get(),
                "ldFrTanWtDw": self.frontTandemLDW.get(),
                "ldRearTanWtDw": self.rearRLDW.get(),
                "ldTanSenDw": self.tandemSensorLDW.get(),
                "ldLiftWt": self.liftLDW.get(),
                "ldRBP": self.pressureLDW.get(),
                "suspType": self.suspension_type.get(),
                "scheType": self.scheValue[self.SPIFChecker(
                    self.frToLift.get(),
                    self.liftToFrTan.get(),
                    self.tanSpacing.get()
                )]
            }
        except Exception:
            print("One or more fields are blank or invalid.")
            return 20
        vin = data["VIN"]
        # VIN must existhelp
        if not vin or vin.strip() == "":
            print("VIN is required. Data not saved.")
            return 10

        # ❗ Check ALL other fields
        invalid_fields = []

        for key, value in data.items():
            if key == "VIN":
                continue

            # Check numeric fields
            if isinstance(value, (int, float)):
                if value == 0:
                    invalid_fields.append(key)

            # Check string fields (if any)
            elif isinstance(value, str):
                if value.strip() == "":
                    invalid_fields.append(key)

            # Catch anything unexpected
            else:
                invalid_fields.append(key)

        if invalid_fields:
            print("Data incomplete. The following fields are missing/invalid:")
            print(invalid_fields)
            print("JSON not saved.")
            return 20
        try:
            firestore_set_document("trucks",
            document(vin),
            collection("calibrations"),
            document(timestamp),
            set(data))
            print(f"Calibration uploaded successfully for VIN {vin}")
            return 30

        except Exception as e:
            print("Firestore upload failed:", e)
            return 40
        # Replace with your window title
 
    
    def retrieveData(self):
        if not self.hasInternet():
            print("No internet connection")
            return 50
        vin = self.VIN.get().strip()
        if not vin:
            print("VIN is required")
            return 10
        try:
            docs = (
                firestore_get_document("trucks",
                document(vin),
                collection("calibrations"),
                stream())
            )
            latest_doc = None
            latest_time = None

            for doc in docs:
                try:
                    doc_time = datetime.strptime(
                        doc.id,
                        "%Y-%m-%d||%H:%M:%S"
                    )

                    if latest_time is None or doc_time > latest_time:
                        latest_time = doc_time
                        latest_doc = doc

                except Exception as e:
                    print("Invalid timestamp:", doc.id, e)

            if latest_doc is None:
                print("No calibration data found")
                return 20

            data = latest_doc.to_dict()

            print("Loading calibration:", latest_doc.id)

            self.VIN.delete(0, END)
            self.VIN.insert(0, data.get("VIN", ""))

            self.frToLift.set(data.get("frToLift", 0.0))
            self.liftToFrTan.set(data.get("liftToFrTan", 0.0))
            self.tanSpacing.set(data.get("tanSpacing", 0.0))

            self.frontEUP.set(data.get("emFrWtUp", 0.0))
            self.frontTandemEUP.set(data.get("emFrTanWtUp", 0.0))
            self.rearREUP.set(data.get("emRearTanWtUp", 0.0))
            self.tandemSensorEUP.set(data.get("emTanSenUp", 0.0))

            self.frontEDW.set(data.get("emFrWtDw", 0.0))
            self.frontTandemEDW.set(data.get("emFrTanWtDw", 0.0))
            self.rearREDW.set(data.get("emRearTanWtDw", 0.0))
            self.tandemSensorEDW.set(data.get("emTanSenDw", 0.0))
            self.liftEDW.set(data.get("emLiftWt", 0.0))
            self.pressureEDW.set(data.get("emRBP", 0.0))

            self.frontLUP.set(data.get("ldFrWtUp", 0.0))
            self.frontTandemLUP.set(data.get("ldFrTanWtUp", 0.0))
            self.rearRLUP.set(data.get("ldRearTanWtUp", 0.0))
            self.tandemSensorLUP.set(data.get("ldTanSenUp", 0.0))

            self.frontLDW.set(data.get("ldFrWtDw", 0.0))
            self.frontTandemLDW.set(data.get("ldFrTanWtDw", 0.0))
            self.rearRLDW.set(data.get("ldRearTanWtDw", 0.0))
            self.tandemSensorLDW.set(data.get("ldTanSenDw", 0.0))

            self.liftLDW.set(data.get("ldLiftWt", 0.0))
            self.pressureLDW.set(data.get("ldRBP", 0.0))

            self.suspensionType.set("")
            self.suspensionType.set(data.get("suspType", ""))
            self.valueDrop.current(self.suspValue.index(self.suspensionType.get()))
            self.suspension_type.set(data.get("suspType", ""))
            
            self.scheduleInfo.set("")
            self.scheduleInfo.set(data.get("scheType", ""))
            self.valueDrop1.current(self.scheValue.index(self.scheduleInfo.get()))
            print(f"Loaded latest calibration: {latest_doc.id}")
            return 30

        except Exception as e:
            print("Firestore retrieve error:", e)
            return 40

    def saveOnClick(self):
        if (self.saveData()==30):
            InfoMsg = f"Data Saved to Cloud"
            messagebox.showinfo(" ", InfoMsg)
        elif(self.saveData() == 20):
            InfoMsg = f"Incomplete Data"
            messagebox.showinfo(" ", InfoMsg)
        elif(self.saveData() == 10):
            InfoMsg = f"VIN does not exist"
            messagebox.showinfo(" ", InfoMsg)
        elif(self.saveData() == 40):
            InfoMsg = f"Error encountered"
            messagebox.showinfo(" ", InfoMsg)
        elif(self.saveData() == 50):
             messagebox.showwarning(
                "Internet Connection",
                "No internet connection available."
            )
            
    def retrieveOnClick(self):
        result = self.retrieveData()

        if result == 30:
            messagebox.showinfo(" ", "Data retrieved successfully")

        elif result == 20:
            messagebox.showinfo(" ", "No data available")

        elif result == 10:
            messagebox.showinfo(" ", "VIN does not exist")

        elif result == 40:
            messagebox.showinfo(" ", "Error encountered")

        elif result == 50:
            messagebox.showwarning(
                "Internet Connection",
                "No internet connection available."
            )
             
    def openPort(self):
        print("user trying to connect")
        self.serial.getComPorts()

    def enable_bt(self):
        if self.bool.get() == True:
            self.connect_bt.config(state = DISABLED)
        else:
            self.connect_bt.config(state = NORMAL)
        print("enable the button to connect")





    def Suspension(self, event):
        print("The user selected a new option from Menu")
        self.selected_value = event.widget.get()

        if self.selected_value == "Suspension":
            self.serial.sendSusp("0")
            self.suspension_type.set("Suspension")
        elif self.selected_value == "Walking Beam":
            self.serial.sendSusp("1")
            self.suspension_type.set("Walking Beam")
        elif self.selected_value == "Air Ride":
            self.serial.sendSusp("2")
            self.suspension_type.set("Air Ride")
        elif self.selected_value == "TufTrac":
            self.serial.sendSusp("3")
            self.suspension_type.set("TufTrac")


    def Schedule(self, event):
        print("The user selected a new option from Menu")
        self.selected_value1 = event.widget.get()
        print(f"Schedule from Value Drop: {self.selected_value1}")
        self.serial.sendSchedule(str(self.spifResult))

    def operationMode(self, modes):
        self.modesOp = modes

        if self.modesOp == "up":
            self.serial.sendMode(str(15))
            self.displayVar.set("UP")
            print("Axle is UP")

        elif self.modesOp == "down":
            self.serial.sendMode(str(25))
            self.displayVar.set("DOWN")
            print("Axle is DOWN")


        elif self.modesOp == "auto":
            self.serial.sendMode(str(85))
            self.displayVar.set("AUTO")
            print("AUTOMATIC operation")



    def Pressure(self, pressure_val):

        self.press = str(pressure_val)
        print(self.press)
        self.serial.sendPressure(self.press)

    def GVW_1(self):
        self.GVWEUP = self.frontEUP.get() + self.frontTandemEUP.get() + self.rearREUP.get()
        self.gvw1.set(self.GVWEUP)
        print("Function to Calculate GVWtEm 1")
        self.onClickFxnEm()

    def GVW_2(self):
        self.GVW_1()
        self.GVWEDW = self.frontEDW.get() + self.liftEDW.get() + self.frontTandemEDW.get() + self.rearREDW.get()
        self.gvw2.set(self.GVWEDW)
        self.frToGVWE.set(round((self.frontEDW.get()/self.GVWEDW)*100))
        self.GVWDiffE.set(abs(self.GVWEUP-self.GVWEDW))
        self.liftToTanDiffE.set(round(((self.frontTandemEDW.get()+self.rearREDW.get())/2-self.liftEDW.get())))
        print("Function to Calculate GVWtEm 2")

    def GVW_3(self):
        self.GVWLUP = self.frontLUP.get() + self.frontTandemLUP.get() + self.rearRLUP.get()
        self.gvw3.set(self.GVWLUP)
        print("Function to Calculate GVWtEm 3")
        self.onClickFxnLd()

    def GVW_4(self):
        self.GVW_3()
        self.GVWLDW = self.frontLDW.get() + self.liftLDW.get() + self.frontTandemLDW.get() + self.rearRLDW.get()
        self.gvw4.set(self.GVWLDW)
        self.frToGVWL.set(round((self.frontLDW.get()/self.GVWLDW)*100))
        self.GVWDiffL.set(abs(self.GVWLUP-self.GVWLDW))
        self.liftToTanDiffL.set(round(((self.frontTandemLDW.get()+self.rearRLDW.get())/2-self.liftLDW.get())))
        print("Function to Calculate GVWtEm 4")
        
    def SPIFChecker(self, frontToLift, liftToFrontTandem, tandemSpacing):
        spif21 = False
        spif23 = False
        if(tandemSpacing >= 1.3 and tandemSpacing <= 1.6 and liftToFrontTandem >= 2.3 and liftToFrontTandem <= 2.8 and frontToLift > 3):
            spif21 = True
        if(liftToFrontTandem >= 2.51 and liftToFrontTandem <= 2.8 and tandemSpacing >= 1.2 and tandemSpacing <= 1.88):
            if(((frontToLift + liftToFrontTandem + tandemSpacing/2) > 6.4 and tandemSpacing >= 1.2 and tandemSpacing <= 1.8) or ((frontToLift + liftToFrontTandem + tandemSpacing/2) > 6.85 and tandemSpacing > 1.8 and tandemSpacing <= 1.88)):
                spif23 = True
        if(spif21 == True and spif23 == True):
            print("SPIF23")
            return 2
        if(spif21 == True and spif23 == False):
            print("SPIF21")
            return 1
        if(spif23 == True and spif21 == False) :
            print("SPIF23")
            return 2
        if(spif21 == False and spif23 == False):
            print("None")
            return 0
            
    def calc5(self):
        self.run_spif()
        # =========================
        # SAFE DIVISION HELPER
        # =========================
        def safe_div(num, den, name=""):
            if den == 0:
                print(f"Warning: Division by zero in {name}")
                return 0
            return num / den

        # =========================
        # Lower Point
        # =========================
        self.lower_slope = round(
            safe_div(
                self.frontLUP.get() - self.frontEUP.get(),
                self.tandemSensorLUP.get() - self.tandemSensorEUP.get(),
                "lower_slope"
            ),
            2
        )

        self.lower_intercept = round(
            self.frontEUP.get() - self.lower_slope * self.tandemSensorEUP.get(),
            2
        )

        self.lowerVar.set(round(
            safe_div(9000 - self.lower_intercept, self.lower_slope, "lowerVar"),
            1
        ))

        # =========================
        # Lift Point
        # =========================
        self.mLift = round(
            safe_div(
                self.liftLDW.get() - self.liftEDW.get(),
                self.pressureLDW.get() - self.pressureEDW.get(),
                "mLift"
            ),
            2
        )

        self.bLift = round(
            self.liftEDW.get() - self.mLift * self.pressureEDW.get(),
            2
        )

        if self.spifResult == 2:
            self.liftVar.set(round(safe_div(4000 - self.bLift, self.mLift, "liftVar"), 1))

        elif self.spifResult == 1:
            self.liftVar.set(round(safe_div(3000 - self.bLift, self.mLift, "liftVar"), 1))

        # =========================
        # Lift Point with Strain
        # =========================
        self.lift_slope = round(
            safe_div(
                self.liftLDW.get() - self.liftEDW.get(),
                self.tandemSensorLDW.get() - self.tandemSensorEDW.get(),
                "lift_slope"
            ),
            2
        )

        self.lift_intercept = round(
            self.liftEDW.get() - self.lift_slope * self.tandemSensorEDW.get(),
            2
        )

        # =========================
        # Max Tandem Point
        # =========================
        self.mMTP = round(
            safe_div(
                self.gvw4.get() - self.gvw2.get(),
                self.pressureLDW.get() - self.pressureEDW.get(),
                "mMTP"
            ),
            2
        )

        self.bMTP = round(
            self.gvw2.get() - self.mMTP * self.pressureEDW.get(),
            2
        )

        if self.spifResult == 2:
            self.MTPVar.set(round(safe_div(36000 - self.bMTP, self.mMTP, "MTPVar"), 1))

        elif self.spifResult == 1:
            self.MTPVar.set(round(safe_div(33000 - self.bMTP, self.mMTP, "MTPVar"), 1))

        # =========================
        # Tandem slope
        # =========================
        self.tandem_slope = round(
            safe_div(
                (self.frontTandemLDW.get() + self.rearRLDW.get()) -
                (self.frontTandemEDW.get() + self.rearREDW.get()),
                self.tandemSensorLDW.get() - self.tandemSensorEDW.get(),
                "tandem_slope"
            ),
            2
        )

        self.tandem_intercept = round(
            (self.frontTandemEDW.get() + self.rearREDW.get()) -
            self.tandem_slope * self.tandemSensorEDW.get(),
            2
        )

        # =========================
        # GVW UP
        # =========================
        self.mGVWU = round(
            safe_div(
                self.gvw3.get() - self.gvw1.get(),
                self.tandemSensorLUP.get() - self.tandemSensorEUP.get(),
                "mGVWU"
            ),
            2
        )

        self.bGVWU = round(
            self.gvw1.get() - self.mGVWU * self.tandemSensorEUP.get(),
            2
        )

        # =========================
        # GVW DOWN
        # =========================
        self.mGVWD = round(
            safe_div(
                self.gvw4.get() - self.gvw2.get(),
                self.tandemSensorLDW.get() - self.tandemSensorEDW.get(),
                "mGVWD"
            ),
            2
        )

        self.bGVWD = round(
            self.gvw2.get() - self.mGVWD * self.tandemSensorEDW.get(),
            2
        )

        # =========================
        # DEBUG PRINTS
        # =========================
        print("Function to Calculate the set points")
        print(self.lower_slope)
        print(self.lower_intercept)
        print(self.mLift)
        print(self.bLift)
        print(self.lift_slope)
        print(self.lift_intercept)
        print(self.mMTP)
        print(self.bMTP)
        print(self.tandem_slope)
        print(self.tandem_intercept)
        print(self.mGVWU)
        print(self.bGVWU)
        print(self.mGVWD)
        print(self.bGVWD)

        # =========================
        # VALIDATION
        # =========================
        if (self.liftVar.get() == 0 and
            self.lowerVar.get() == 0 and
            self.MTPVar.get() == 0):
            messagebox.showinfo(" ", "Populate empty and loaded weights before calculating points")
        elif(self.MTPVar.get() == 0 and self.liftVar.get() == 0):
            messagebox.showinfo(" ", "Does not qualify for SPIF21 or SPIF22. Measure axle spread again.")
        elif(self.MTPVar.get() == 0 ):
            messagebox.showinfo(" ", "Calculate GVW before calculating points")
        if (self.liftVar.get() < 0 or
            self.lowerVar.get() < 0 or
            self.MTPVar.get() < 0):
            messagebox.showinfo(" ", "Error. Partial GVW provided")
        if(self.liftVar.get() > 0 and
            self.lowerVar.get() > 0 and
            self.MTPVar.get() > 0):    
            self.summary()
        
    def sendPoint(self, pnt1, pnt2, pnt3):
        pt1 = str(self.lower_slope)
        pt2 = str(self.lower_intercept)
        pt3 = str(self.mLift)
        pt4 = str(self.bLift)
        pt5 = str(self.lift_slope)
        pt6 = str(self.lift_intercept)
        pt7 = str(self.mMTP)
        pt8 = str(self.bMTP)
        pt9 = str(self.tandem_slope) 
        pt10 = str(self.tandem_intercept)
        pt11 = str(self.mGVWU)
        pt12 = str(self.bGVWU)
        pt13 = str(self.mGVWD)
        pt14 = str(self.bGVWD)
        print("Function to send the points to Arduino")
        self.serial.setPoints(str(pnt1), str(pnt2), str(pnt3), pt1, pt2, pt3, pt4, pt5, pt6, pt7, pt8, pt9, pt10, pt11, pt12, pt13, pt14)

    
class SerialGui():

    def __init__(self, root):
        self.root = root.root
        self.com_gui = None
        self.serial = serial.Serial()
        self.retry = False
        self.root.after(5000, self.getComPorts)
        self.suspension = StringVar()
        self.suspension.set("0.0")
        self.schedule_var = StringVar()
        self.schedule_var.set("1")
        self.pressureValue = StringVar()
        self.pressureValue.set("0.0")
        self.modeValue = StringVar()
        self.modeValue.set("0.0")
        self.presval = StringVar()
        self.presval.set("0.0")

    def getComPorts(self):
        """
        Scan Arduino ports
        """
        self.ports =serial.tools.list_ports.comports()
        self.commPort = 'None'
        self.numConnection = len(self.ports)

        for i in range(0, self.numConnection):
            port = self.ports[i]
            strPort = str(port)
            print(port)
            if 'Arduino' in strPort or 'UART' in strPort or 'Port' in strPort or 'USB' in strPort or 'Serial' in strPort:
                splitPort = strPort.split(' ')
                self.commPort = (splitPort[0])

        if self.commPort != 'None':
            print(self.commPort)
            InfoMsg = f"Device Found on {self.commPort}"
            messagebox.showinfo(" ", InfoMsg)
            self.serialConnet()

        else:
            ErrorMsg = f'Device not Found. Reconnect the Module'
            reply = messagebox.askretrycancel(" ", ErrorMsg)
            print(reply)

            if reply == True:
                self.root.after(5000, self.getComPorts)
                print("User forgot to connect the Arduino")

            else:
                self.com_gui.bool.set(False)
                self.com_gui.enable_bt()
                print("User does not want to connect")



    def sendSusp(self, menuOption):
        self.suspension.set(menuOption)
        print(f"Susp:{self.suspension.get()}")
        if self.serial.is_open:
            self.serial.write(self.suspension.get().encode())
            self.serial.write(",".encode())

        else:
            print("Serial port not open")



    def sendSchedule(self, menuOption1):
        self.schedule_var.set(menuOption1)
        print(f"Sche:{self.schedule_var.get()}")

        if self.serial.is_open:
            self.serial.write(self.schedule_var.get().encode())
            self.serial.write(",".encode())

        else:
            print("Serial port not open")



    def sendMode(self, mode):
        self.modeValue.set(mode)
        print(f"Suspension selected: {self.suspension.get()}")
        print(f"the user selected the operation mode: {mode}")
        if self.serial.is_open:
            self.serial.write(self.suspension.get().encode())
            self.serial.write(",".encode())
            self.serial.write(self.modeValue.get().encode())
            self.serial.write(",".encode())




    def sendPressure(self, pre1):
        self.value = pre1
        print(self.value)
        self.pressureValue.set(pre1)
        print("Testing new function...")
        print(f"Suspension: {self.suspension.get()}, Operand: {self.modeValue.get}")
        self.presval.set(pre1)
        if self.serial.is_open:
            self.serial.write(self.suspension.get().encode())
            self.serial.write(",".encode())
            self.serial.write(self.modeValue.get().encode())
            self.serial.write(",".encode())
            self.serial.write(self.pressureValue.get().encode())
            self.serial.write(",".encode())


    def setPoints(self, pnt1, pnt2, pnt3, pt1, pt2, pt3, pt4, pt5, pt6, pt7, pt8, pt9, pt10, pt11, pt12, pt13, pt14):
        # Create a list of the data to be sent
        pointstosend = [pnt1, pnt2, pnt3, self.suspension.get(), self.modeValue.get(), self.pressureValue.get(), pt1, pt2, pt3, pt4, pt5, pt6, pt7, pt8, pt9, pt10, pt11, pt12, pt13, pt14, self.schedule_var.get(), pt7, pt8, pt5, pt6, pnt1, pnt2, "4"]
        #, self.suspension.get(), self.modeValue.get(), self.pressureValue.get(), pt1, pt2, pt3, pt4, pt5, pt6, pt7, pt8, pt9, pt10, pt11, pt12, pt13, pt14, self.schedule_var.get(), pt7, pt8, pt5, pt6, pnt1, pnt2, "4"]
        # Print the data that will be sent
        print("Points entered:", ", ".join([str(val) for val in pointstosend]))
        self.serial.write(self.suspension.get().encode())
        self.serial.write(",".encode())
        self.serial.write(self.modeValue.get().encode())
        self.serial.write(",".encode())
        self.serial.write(self.pressureValue.get().encode())
        self.serial.write(",".encode())
        self.serial.write(pt1.encode())
        self.serial.write(",".encode())
        self.serial.write(pt2.encode())
        self.serial.write(",".encode())
        self.serial.write(pt3.encode())
        self.serial.write(",".encode())
        self.serial.write(pt4.encode())
        self.serial.write(",".encode())
        self.serial.write(pt13.encode())
        self.serial.write(",".encode())
        self.serial.write(pt14.encode())
        self.serial.write(",".encode())
        self.serial.write(pt9.encode())
        self.serial.write(",".encode())
        self.serial.write(pt10.encode())
        self.serial.write(",".encode())
        self.serial.write(pt11.encode())
        self.serial.write(",".encode())
        self.serial.write(pt12.encode())
        self.serial.write(",".encode())
        self.serial.write(self.schedule_var.get().encode())
        self.serial.write(";".encode())
        self.serial.write(pt7.encode())
        self.serial.write(",".encode())
        self.serial.write(pt8.encode())
        self.serial.write(",".encode())
        self.serial.write(pt5.encode())
        self.serial.write(",".encode())
        self.serial.write(pt6.encode())
        self.serial.write(",".encode())
        self.serial.write(pnt1.encode())
        self.serial.write(",".encode())
        self.serial.write(pnt2.encode())
        self.serial.write(",".encode())
        self.serial.write(pnt3.encode())
        self.serial.write(",".encode())



    def serialOpen(self):
        """
        Setup the serial communication
        """

        try:
            print("Trying to open the door: 1")
            self.serial.is_open

        except:
            print("Trying to open the door: 2")
            PORT = self.commPort
            BAUD = 9600
            self.serial.port = PORT
            self.serial.baudrate = BAUD
            self.serial.timeout = 0.1
            self.serial.open()
            self.serial.status = True

        try:
            print("Trying to open the door: 3")
            if self.serial.is_open:
                print("Trying to open the door: 4")
                self.serial.status = True

            else:
                print("Trying to open the door: 5")
                PORT = self.commPort
                BAUD = 9600
                self.serial.port = PORT
                self.serial.baudrate = BAUD
                self.serial.timeout = 0.1
                self.serial.open()
                self.serial.status = True

        except:
            print("Trying to open the door: 6")
            self.serial.status = False


    def serialClose(self):
        """
        Close Serial Communication
        """

        try:
            self.serial.is_open
            self.serial.close()
            self.serial.status = False

        except:
            self.serial.status = False


    def serialConnet(self):
        """
        Method used connect
        """

        self.portfound = self.commPort
        if self.portfound != 'None':

            self.serialOpen()
            if self.serial.status:

                InfoMsg = f"Successful connection using {self.portfound}"
                messagebox.showinfo(" ", InfoMsg)
                self.com_gui.bool.set(True)
                self.com_gui.enable_bt()

                self.root.after(5000, self.readData())


            else:
                """
                ERROR Handling 

                """

                ErrorMsg = f"Failure Opening {self.commPort}. (Port Busy)"
                reply = messagebox.showerror(" ", ErrorMsg)
                print(reply)
                if reply == "ok":
                    self.com_gui.bool.set(False)
                    self.com_gui.enable_bt()
                    print("Selected Port is Busy")


        else:

            InfoMsg = f"Device Not Found. Reconnect the Module"
            messagebox.showwarning(" ", InfoMsg)
            self.root.after(10000, self.getComPorts())

    def readData(self):

        """
        Read data from Arduino
        """

        if self.serial.is_open:
            try:
                print("tried it")
                if self.serial.in_waiting > 0:

                    global data1
                    data1 = ["0"]*20
                    data = self.serial.readline().decode(encoding = 'latin1')
                    DATA = data.split(',')
                    for i in range(len(DATA) - 1):
                        data1[i] = DATA[i]
                    print(data1)
                    data2 = data1[0]
                    data3 = data1[1] 
                    data4 = data1[2]
                    data5 = data1[3]
                    data6 = data1[4]
                    data7 = data1[5]
                    data8 = data1[6]
                    data9 = data1[7]
                    data10 = data1[8]
                    data11 = data1[9]
                    data12 = data1[10]
                    data13 = data1[11]
                    data14 = data1[12]
                    data15 = data1[13]
                    data16 = data1[14]
                    data17 = data1[15]
                    data18 = data1[16]
                    data19 = data1[17]
                    

                    self.com_gui.suspTypeLb.set(data2)
                    self.com_gui.posLb.set(data3)  
                    self.com_gui.setLb.set(data4)
                    self.com_gui.bagpressLb.set(data5)
                    self.com_gui.speedLb.set(data6)
                    self.com_gui.dircLb.set(data7)
                    self.com_gui.revrsLb.set(data8)
                    self.com_gui.fourLb.set(data9)
                    self.com_gui.tandemLb.set(data10)
                    self.com_gui.btStateLb.set(data11)
                    self.com_gui.weightLb.set(data12)
                    self.com_gui.lowerLb.set(data13)
                    self.com_gui.liftLb.set(data14)
                    self.com_gui.MTPLb.set(data15)
                    self.com_gui.frontWeight.set(data15)
                    self.com_gui.schedule21_23.set(data16)
                self.root.after(100, self.readData)


            except:

                ErrorMsg = f"Failure to establish connection using {self.commPort}"
                print("I am causing error!")
                messagebox.showerror(" ", ErrorMsg)
                self.serialClose()
                self.root.after(5000, self.getComPorts())


        else:
            self.serialConnet()
            self.root.after(5000, self.readData)

    from tkinter import messagebox

if __name__ == "__main__":
    root_gui = RootGui()
    mySerial = SerialGui(root_gui)
    com_Gui = ComGui(root_gui.root, mySerial)
    mySerial.com_gui = com_Gui
    root_gui.root.mainloop()
    
    