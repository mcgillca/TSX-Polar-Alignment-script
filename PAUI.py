#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "pyside6",
#     "pyobjc-framework-Cocoa; sys_platform == 'darwin'",
# ]
# ///
from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QCheckBox, QTextEdit, QSizePolicy,
    QStyledItemDelegate, QLineEdit, QHeaderView, QFileDialog, QMessageBox,
    QSizePolicy, QStyle, QAbstractItemDelegate, QAbstractItemView, QGridLayout,
    QDialog, QGroupBox, QSpinBox, QDoubleSpinBox, QComboBox, QScrollArea, QFrame,
    QScrollBar, QTabWidget, QSplitter, QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QObject, QSize, QTimer, QThread, QSettings
from PySide6.QtCore import QRegularExpression, QCoreApplication, QProcess
from PySide6.QtGui import QColor, QBrush, QFont, QValidator, QGuiApplication, QPainter
from PySide6.QtGui import QIntValidator, QDoubleValidator, QRegularExpressionValidator, QFontMetrics
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QToolTip

import sys
import os
import re
import sqlite3
import json
import math
import random
import signal
import socket
import subprocess
import csv
import time
import tempfile
import shutil
import threading
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from types import MappingProxyType
from typing import Callable, Any, Optional, Dict, List, Tuple, Union
import http.client
import urllib.request
import urllib.parse
import urllib.error
import os.path
import platform

###############################################################################
# CONFIG
###############################################################################



import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Default values for settings
# (Only used until edited in the Settings tab; thereafter the saved values are
# read at the start of each run, even in batch mode.)
# ─────────────────────────────────────────────────────────────────────────────

# Parameter to control start and end of imaging
SUNIMAGING = -12      # How far Sun below horizon to image
                      # -6: Civil, -12: Nautical, -18: Astronomical

SUNFLATS = 6          # How far Sun above horizon to start Dusk flats or stop Dawn flats.

# Parameters for controlling guiding
AG_exp_min    = 3.0   # Minimum autoguider exposure length (seconds)
AG_exp_max    = 30.0  # Maximum autoguider exposure length (seconds)
AG_gain       = 0.5   # Guide camera gain (e⁻/ADU)
AG_read_noise = 6.64  # Guide camera read noise in e⁻ at 1×1 binning
AG_target_snr = 30.0  # Target SNR for guide star selection
AG_exp_current = AG_exp_min  # Last calculated optimal exposure (set by AGFindStarSEP)
AG_dither = 5.0       # Maximum dither radius in guider pixels
AG_ERR_MAX = 1.0      # Guiding settling distance in guider pixels
AG_WATCHDOG = True    # Whether to run the autoguider watchdog daemon
AG_SEP_HOT_PIXEL = True  # Run SEP internal hot pixel detection
AG_SEP_HP_RADIUS = 2.0   # Ignore HP detections within this radius of a star (px)

# Parameters for controlling flats
QDuskFlats  = False   # Whether or not to take dusk flats
QDawnFlats  = False   # Whether or not to take dawn flats
FL_Min = 0.1          # Minimum exposure time for flats
FL_Max = 12.0         # Maximum exposure time for flats
FL_ADU = 25000        # Desired ADU Target
FL_ADU_MIN = 20000    # Minimum acceptable
FL_ADU_MAX = 30000    # Maximum acceptable
NFLATS = 2            # Number of flats

# How long to wait when it's cloudy
SLEEP = 300           # Pause before trying again in seconds.

# Focus parameters
# The routine checks the magnitude of the star found by @Focus2 — if too dim,
# @Focus2 likely tried to focus on a hot pixel and the result is ignored.
# ATFOC_MAG_LIM sets the maximum (dimmest) magnitude acceptable.
#
# FOC_TEMP_CHANGE: retrigger focus when temperature changes by this many degrees.
#   Set to zero to disable.
# FOC_TIME_CHANGE: retrigger focus every N minutes. Set to zero to disable.
# BACKLASH: if > 0, move the focuser inward by this amount before the final
#   approach, to compensate for backlash.
ATFOC_MAG_LIM     = 1    # Minimum magnitude to accept @Focus results
ATFOC_F2_TOL      = 10.0 # Tolerance (focuser steps): AtFocus2Robust accepts if
                         # |Lorentzian - @F2| <= this. Set to 0 to skip the check.
ATFOC_F2_MAX_RUNS = 3    # Maximum number of @Focus2 attempts in AtFocus2Robust.
ATFOC_MIN_SNR     = 0.0  # Minimum SNR for first @F2 frame star. Set to 0 to disable.
FOC_STAR_SNR_MIN  = 25.0 # Threshold used to colour the SNR column in FocusLogWindow.
                         # Also used as the rejection threshold for the first @F2 frame
                         # star SNR check. Set to 0 to disable.
FOC_CAMERA_GAIN       = 1.0  # Main camera gain (e⁻/ADU) — used for SNR calculation
FOC_TEMP_CHANGE = 1    # Change of temperature required to trigger refocusing
FOC_TIME_CHANGE = 0    # How often to trigger refocusing (in minutes)?
FOC_FWHM_CHANGE = 0    # % FWHM rise above baseline to trigger refocusing (0 = off)
FOC_FWHM_ROUND  = 80   # Minimum star roundness (%) for a sub to be trusted
BACKLASH        = 0    # If > 0, move inward this amount before going to final
                       # focus position to compensate for backlash

# Variables for filter wheel — only used if a filter wheel is detected
FocusFilter   = 'L'     # Filter to use for focusing
CLS_REDUCTION = 1       # Camera frame reduction for CLS: 1=full, 2=half, 4=quarter
DawnFilters = "LRGBHSO" # Filter order for dawn flats (highest → lowest bandwidth)

# TheSkyX Application Support Files (ASF) folder — where TheSkyX keeps its own
# settings (ImagingSystem.ini, Custom Horizon.hrz, etc). Normally the per-OS
# default below; TSX_ASF_DIRECTORY becomes a normal user setting once Settings
# has loaded once (see keywords_from_settings() in main_window.py), so a
# relocated/networked ASF folder (TheSkyX supports this via its own
# startup.ini/UserDataRoot mechanism) can be configured like any other path.

def tsx_user_data_root() -> Path:
    """Return TheSkyX's default per-OS Application Support Files folder.

    On Windows the user-data root is in Documents (not AppData); the edition
    folder may include "64" depending on the installation.
    """
    if sys.platform == "win32":
        base = Path.home() / "Documents" / "Software Bisque"
        for edition in ("TheSkyX Professional Edition 64",
                        "TheSkyX Professional Edition"):
            p = base / edition
            if p.exists():
                return p
        return base / "TheSkyX Professional Edition"
    # macOS and Linux both use ~/Library/Application Support
    return (Path.home() / "Library" / "Application Support" /
            "Software Bisque" / "TheSkyX Professional Edition")


def asf_directory() -> Path:
    """Return the current TheSkyX ASF folder (the TSX_ASF_DIRECTORY setting)."""
    return Path(TSX_ASF_DIRECTORY) if TSX_ASF_DIRECTORY else tsx_user_data_root()


TSX_ASF_DIRECTORY = str(tsx_user_data_root())

# Custom horizon file (TheSkyX .hrz format), inside the ASF folder above.
HRZ_PATH = str(asf_directory() / "Custom Horizon.hrz")

# Directories for log files and target files.
# If left blank both will be set to ~/Documents.
LOG_DIRECTORY    = ""
TARGET_DIRECTORY = ""

# Directories for image and flat files.
# If left blank will use the existing TSX image directory for both.
FLAT_DIRECTORY  = ""
IMAGE_DIRECTORY = ""

# TheSkyX AutoSave filename format string (colon-prefixed codes).
# :t=target, :f=filter, :b=binning, :i=image type, :c=temp, :e=exposure,
# trailing : = auto-appended sequence number.
# Not a user setting — read live from ImagingSystem.ini by
# keywords_from_settings() in main_window.py; this is just the pre-startup
# placeholder.
AUTOSAVE_FORMAT = ""

# Sky survey preview / camera FOV settings
FOV_WIDTH      = 1.5       # Camera field-of-view width in degrees
FOV_HEIGHT     = 1.0       # Camera field-of-view height in degrees
FOV_ANGLE      = 0.0       # Camera position angle (degrees, North through East)
FOV_FLIP_X     = False     # Mirror camera image
preview_survey = "DSS2 Red"  # "DSS2 Red" (SkyView) or "DSS2 Colour" (HiPS2FITS)

# File to send mail or other comms if selected
MAIL_FILE = ""

# ── Polar alignment tool ─────────────────────────────────────────────────────
# Used only by the standalone Polar Alignment app (polar_ui / polar_align).
# In PAUI.py these were module constants the user had to edit by hand;
# PA_CAM_SCALE in particular is per-site (6.764 at Weybridge, 2.31 at Nerpio).
PA_CAM_DURATION = 4.0    # Exposure for each plate-solve image (seconds)
PA_CAM_BINNING  = 4      # Binning for those images
PA_CAM_SCALE    = 6.764  # Arcsec/pixel at that binning — used for plate solving
PA_CAM_FILTER   = ""     # Filter to use; blank leaves the wheel alone
PA_CAM_SUBFRAME = 4      # 1 = full frame, 2 = centre half, 4 = centre quarter
PA_DEC          = 60.0   # Declination to image at
PA_HA1          = 1.0    # Hour angle of the first image
PA_HA2          = 5.0    # Hour angle of the second image
PA_KEEP_FILES   = False  # Keep the FITS and .SRC files rather than deleting
PA_COMPARE_REFRACTION = False  # Log local vs TheSkyX Alt/Az to size refraction

# File to report whether weather is safe for imaging
WEATHER_FILE = ""

# ─────────────────────────────────────────────────────────────────────────────
# Do not edit below this line
# ─────────────────────────────────────────────────────────────────────────────

VERSION = "TheSkyX Scheduler V4.4"

# Product name with the version stripped off.  The main window title uses this
# so that manual screenshots survive a point release; the full VERSION string
# is written to the log at startup and at the head of every session instead.
# Derived rather than hard-coded so bump_version.py only has to rewrite VERSION.
APP_NAME = VERSION.rsplit(" V", 1)[0] if " V" in VERSION else VERSION

# Bare version number, e.g. "4.4" — lets the Target Planner label itself with
# its own product name rather than borrowing the Scheduler's.
VERSION_NUM = VERSION.rsplit(" V", 1)[1] if " V" in VERSION else ""

# The Polar Alignment tool numbers itself, because it is published from its
# own public repo to people who have never seen the scheduler: shipping a
# first release as "v4.4" would invite them to look for versions 1 to 4.3.
# Its releases also have nothing to do with the scheduler's — a fix here need
# not move that number, and a scheduler release need not move this one.
# bump_version.py rewrites the two separately.
POLAR_VERSION = "2.0"

# Resolve blank directories to ~/Documents
_home_docs = str(Path.home() / "Documents")
if LOG_DIRECTORY    == "": LOG_DIRECTORY    = _home_docs
if TARGET_DIRECTORY == "": TARGET_DIRECTORY = _home_docs
if FLAT_DIRECTORY   == "": FLAT_DIRECTORY   = _home_docs
if IMAGE_DIRECTORY  == "": IMAGE_DIRECTORY  = _home_docs

# Global variable to hold file names — used for the log file
TARGET_FILE_NAME = ""
LOG_FILE_NAME    = ""

# Verbosity
verbose = False  # Flag to say how much data to print out

# Global variables for testing.  The `testing` flag is set automatically if
# the simulated mount is detected.
testing = False  # Flag to pretend sun has set. Set to False for real use.
SUN     = -3    # Value of altitude for testing

# Set automatically to True if using a simulator camera / focuser respectively
testflat = False  # Flag to test simulated flats
testfoc  = False  # Flag to assume focusing successful

# Dusk flat order is the reverse of the dawn order
DuskFilters = DawnFilters[::-1]

# Focus state
QFocuser          = False  # Do we have a focuser connected?
LastFocusPosition = 0      # Last known focuser position
LastFocusTemp     = 0.0    # Last known focus temperature
LastFocusTime     = 0.0    # Time of last focus

# Manual refocus request — set by the Focus panel button, consumed by the
# imaging loop after the current sub completes.  atfocus3_active mirrors the
# imaging loop's per-target QAtFocus3 so the button can disable itself for
# targets whose filter sequence embeds an @Focus3 run.
refocus_requested = False
atfocus3_active   = False

# Filter wheel state
QFilterWheel = False  # Do we have a filter wheel?
QFilterError = False  # Is there an error with the filter names?
NFilters     = 0      # Number of filters
FilterDict   = {}     # dict: first-letter → zero-based index
FilterNames  = []     # list of filter name strings

# Dome state
QDome = False  # Do we have a dome?

# Constants for testing whether an object can be imaged
EARLY = -1   # Too early for this object
IMAGE =  0   # Object is in the right altitude range to image
LATE  =  1   # Too late for this altitude range

# Whether to repeat imaging the next day (GUI mode only)
REPEAT = False

# Image stats accumulator
ImageStats = []

# Weather status
Weather_Status     = ""     # Gated: flips to "SAFE" only after ObservatoryOpenDelay elapses
Weather_Status_Raw = ""     # Immediate per-poll reading ("SAFE"/"UNSAFE"/"UNKNOWN")
Weather_Comment  = ""     # Free-text description (e.g. "rain")
Weather_Pressure = 0.0    # If provided, pressure will be updated in TheSky
Weather_Warning  = False  # If True, will flash the LED

ObservatoryOpenDelay = 300.0  # Seconds to hold after Safe before config.Weather_Status flips

# Weather impact tracking (reset at the start of each imaging run)
weather_lost_s        = 0.0    # Total seconds lost waiting for weather to clear
weather_events        = 0      # Number of separate weather interruptions
weather_in_bad_period = False  # True while a weather episode is still active
guider_restarts       = 0      # Watchdog restarts after "Autoguider stopped unexpectedly"
session_start_t       = 0.0    # time.time() recorded at the start of the imaging run
session_night_date    = ''     # YYYY-MM-DD label for log/DB file names; set by image_loop
imaging_complete      = False  # True once all imaging targets are done (dawn flats may follow)
altitude_wait_info    = None   # dict(tgt_id, coords, alt, time, rise) while waiting for altitude

# Is TheSkyX connected?
QTSXConnected = False

# Settings keyword lists (populated by SettingsManager)
keyword     = []
keyvalue    = []
description = []
validation  = []
section     = []

# True when running as the standalone Target Planner (no TheSkyX)
standalone = False

# UI timing state
tdusk = 0.0   # Stored dusk time
tdawn = 0.0   # Stored dawn time
tflat = 0.0   # Stored time when taking dusk flats can start
lat   = 0.0   # Stored latitude
lon   = None  # Stored longitude (degrees, east positive); None until set at startup
tnow  = 0.0   # Stored initial time  (only tnow - LST difference is used)
LST   = 0.0   # Stored LST when first invoked

# Per-target status arrays (one element per row in the target table)
values_OK  = [[False, False, False, False, False, False, False, False, False]]
start_time = [0.0]
end_time   = [-1000000.0]
ra_dec        = [{0.0, 0.0}]
ra_dec_j2000  = {}          # target_name -> (ra_hours_j2000, dec_deg_j2000)

# ─────────────────────────────────────────────────────────────────────────────
# Callback slot: set by imaging_loop at startup to avoid a circular import.
# tsx_comms calls  config.emergency_park_fn()  instead of EmergencyPark()
# directly.
# ─────────────────────────────────────────────────────────────────────────────
emergency_park_fn = None      # Callable[[], None] | None

# Set by MainWindow at startup.  Call this from any thread to initiate a
# graceful emergency shutdown: cancels the imaging runner, then quits once
# the worker thread has actually stopped (no arbitrary delay, no QThread
# destroy-while-running warning).
emergency_shutdown_fn = None  # Callable[[], None] | None

# settings.py calls  config.keywords_from_settings_fn()  instead of
# keywords_from_settings() directly (defined in main_window.py).
keywords_from_settings_fn = None   # Callable[[], None] | None

# Callable[(key: str, value) -> None] | None
# Allows ui_widgets to persist a single setting without importing main_window.
save_setting_fn = None

# The MainWindow instance — set in main.py after construction so that
# ui_widgets.py can call window.enable_start() without a circular import.
window = None   # MainWindow | None

# The active StopToken for the current imaging run — set by the image_job
# wrapper so that psuedo_sleep() can check it for cooperative cancellation.
stop_token = None  # StopToken | None

# Stop event for the autoguider watchdog thread — set by AGstart() in
# autoguiding.py, cleared and signalled by AGstop() in device_control.py.
ag_watchdog_stop = None   # threading.Event | None

# The QThread running the watchdog — stored so AGstop() can wait() for it.
ag_watchdog_thread = None  # _AGWatchdogThread | None

# Accumulated per-image SEP stats; each entry is a dict keyed by STAT_COLS.
image_stats_list: list = []

# Per-session focus run history; each entry is a FocusRunRecord from focusing.py.
focus_run_history: list = []

# Plate scale in arcsec/pixel derived from the last FITS header; None = unknown.
plate_scale: float | None = None

# GuidingRMSDaemon instance — set by MainWindow, read by imaging.py to update
# plate scale without a circular import.
guiding_rms_daemon = None  # GuidingRMSDaemon | None

# Index into image_stats_list marking the start of the current imaging session.
# Set to len(image_stats_list) each time Start is pressed so the Summary
# "This Session" tab only counts subs taken in the current run.
session_start_index: int = 0

# Snapshot of the target table taken when Start is pressed: list of 9-element
# string lists, one per row.  None until the first imaging session begins.
# Used by SummaryDialog so that mid-session table edits don't corrupt the view.
session_table_snapshot: list | None = None

# Cache of TSX property-0 names resolved by NameLookupThread.
# Maps casefold(table_name) → tsx_name so SummaryDialog._build_alias_map
# can resolve aliases without making a live TSX call (which blocks during CLS).
tsx_name_cache: dict[str, str] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Focus panel settings and runtime state
# ─────────────────────────────────────────────────────────────────────────────
focus_interval_min: float   = 0.0    # mirrors FOC_TIME_CHANGE for panel time bar
focus_temp_delta: float     = 0.0    # mirrors FOC_TEMP_CHANGE for panel gauge

# Current focuser temperature (kept fresh by FocuserTempDaemon)
focuser_temp_current: float = 0.0
focuser_temp_daemon = None   # set to FocuserTempDaemon instance at startup

# Simulated @Focus2 playback
use_simulated_focus: bool   = False
simulated_focus_dir: str    = ""     # set at launch from os.path.dirname(main_window.__file__)
_sim_focus_idx: int         = 0      # index of next simulated file to consume

# Module self-references: config.X == X, utils.X == X, etc.
import sys as _sys
config          = _sys.modules[__name__]
utils           = _sys.modules[__name__]
theme           = _sys.modules[__name__]
session_history = _sys.modules[__name__]

###############################################################################
# UTILS
###############################################################################



import os
import ssl
import subprocess
import sys
import time
import urllib.request


# ─────────────────────────────────────────────────────────────────────────────
# Network helper
# ─────────────────────────────────────────────────────────────────────────────

def ssl_urlopen(req, timeout: int = 30):
    """
    Open *req* (URL string or Request object) with SSL verification, falling
    back to an unverified context if the cert chain cannot be validated.
    This handles macOS/Windows installs where Python's bundled CA store is
    absent or stale.  Returns the response object as a context manager.
    """
    import urllib.error
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except Exception as exc:
        reason = getattr(exc, 'reason', exc)
        if isinstance(reason, ssl.SSLError) or isinstance(exc, ssl.SSLError):
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Legacy async-mode shims
#
# Legacy batch-mode symbols — queue.put() calls have been replaced with output(),
# so only the stop-check wrappers are still needed.
# ─────────────────────────────────────────────────────────────────────────────
async_running = False           # always False; legacy guard variable

def end_async_code_check() -> bool:
    """Return True if the current imaging job has been asked to stop."""
    tok = config.stop_token
    return tok is not None and tok.stop_requested()

def finish_async_code() -> None:
    """Legacy no-op — clean-up was handled by the old async framework."""
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Message-status constants
# ─────────────────────────────────────────────────────────────────────────────
OK      = 0
WARNING = 1
ERROR   = 2

# ─────────────────────────────────────────────────────────────────────────────
# Module-level logger reference.
# Set by main_window.py after the AppLogger instance is created:
#   import src.utils as utils
#   utils._log_sink = my_app_logger
# Named _log_sink (not logger) so it does not collide with the ui_widgets
# module-level `logger = _LoggerProxy()` name when everything is merged into
# a single-file build.
# ─────────────────────────────────────────────────────────────────────────────
_log_sink = None   # AppLogger | None


# ─────────────────────────────────────────────────────────────────────────────
# is_float — pure helper, no dependencies
# ─────────────────────────────────────────────────────────────────────────────
def is_float(string) -> bool:
    """Return True if *string* can be converted to a float."""
    try:
        float(string)
        return True
    except (ValueError, TypeError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# logtime
# ─────────────────────────────────────────────────────────────────────────────
def logtime() -> str:
    """Return a formatted timestamp string for log messages."""
    return time.strftime("[%d-%m-%Y %H:%M:%S] ")


# ─────────────────────────────────────────────────────────────────────────────
# output + log capture
# ─────────────────────────────────────────────────────────────────────────────

# When set to a list, output() appends every message to it in addition to
# normal logging.  start_capture()/stop_capture() manage this buffer.
_capture_buffer: list | None = None


def start_capture() -> None:
    """Begin capturing all output() calls into an internal buffer."""
    global _capture_buffer
    _capture_buffer = []


def stop_capture() -> list:
    """Stop capturing and return captured lines (clears the buffer)."""
    global _capture_buffer
    lines = _capture_buffer or []
    _capture_buffer = None
    return lines


def peek_capture() -> list | None:
    """Return a snapshot of the current capture buffer, or None if not capturing."""
    return list(_capture_buffer) if _capture_buffer is not None else None


def resume_capture(existing: list) -> None:
    """Attach an existing list as the capture buffer so subsequent output() calls append to it."""
    global _capture_buffer
    _capture_buffer = existing


def output(message: str, status: int = OK) -> None:
    """
    Log *message* to the GUI logger and/or to the log file.

    status  — OK (0), WARNING (1) or ERROR (2).  WARNING is shown in orange
              (amber), ERROR in red.

    Warning/error lines stay visible when the message area is filtered, and
    the text is left unmodified so the timestamp-stripping done by the status
    updater and the activity-log classifier still matches.
    """
    if _capture_buffer is not None:
        _capture_buffer.append(message)

    GUI = True
    if GUI:
        if status == WARNING:
            messagetoprint = message
            color = "orange"
        elif status == ERROR:
            messagetoprint = message
            color = "red"
        else:
            messagetoprint = message
            color = "black"

        if _log_sink is not None:
            _log_sink.log(messagetoprint, color)
    else:
        print(message)

    # If a log file is configured, append to it
    if config.LOG_FILE_NAME != "":
        with open(config.LOG_FILE_NAME, "a") as fh:
            fh.write(message + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# subprocess_clean_env
# ─────────────────────────────────────────────────────────────────────────────
def subprocess_clean_env() -> dict:
    """Return a copy of os.environ with uv/virtualenv variables stripped out.

    When tsxscheduler.py is launched via ``uv run``, the child process inherits
    uv's virtualenv: VIRTUAL_ENV is set, the venv's bin/ directory is prepended
    to PATH, and PYTHONPATH may be set.  External scripts (weather, mail) need
    the *system* Python site-packages, not the uv venv.  Pass the dict returned
    by this function as the ``env=`` argument to subprocess.run / subprocess.Popen.
    """
    env = os.environ.copy()
    venv = env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    if venv:
        bin_dir = os.path.join(venv, "bin")
        path_parts = env.get("PATH", "").split(os.pathsep)
        env["PATH"] = os.pathsep.join(p for p in path_parts if p != bin_dir)
    return env


# ─────────────────────────────────────────────────────────────────────────────
# send_mail_message
# ─────────────────────────────────────────────────────────────────────────────
def send_mail_message(subject: str, body: str) -> None:
    """Invoke the configured mail script with *subject* and *body*."""
    if config.MAIL_FILE == "":
        return

    command = [str(config.MAIL_FILE), subject, body]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True,
                       env=subprocess_clean_env())
        output(logtime() + "Email '" + subject + "' sent.")
    except subprocess.CalledProcessError as e:
        output(f"{logtime()}Mail command failed with return code: {e.returncode}", ERROR)
        output(f"{logtime()}Mail command failed with output: {e.stdout[:-1]}", True)


# ─────────────────────────────────────────────────────────────────────────────
# psuedo_sleep
# ─────────────────────────────────────────────────────────────────────────────
def psuedo_sleep(sleep: float, phrase: str = "Stopped sleeping") -> None:
    """
    Sleep for *sleep* seconds, waking every 0.1 s to check for a stop signal.

    Checks config.stop_token (set by the image_job wrapper) for cooperative
    cancellation via the StopToken mechanism.

    NOTE: end_async_code_check(), finish_async_code(), and queue are legacy
    symbols from the old batch-mode threading design.  They are not defined
    anywhere in the current codebase; those code paths are dead.  They are
    preserved here unchanged so behaviour is identical to dev.py at runtime.
    """
    tstart = time.time()
    while (time.time() - tstart) < sleep:
        if end_async_code_check():   # noqa: F821  (intentionally undefined)
            output(logtime() + phrase)   # noqa: F821
            finish_async_code()             # noqa: F821
            sys.exit()
        tok = config.stop_token
        if tok is not None:
            if tok.stop_requested():
                output(logtime() + phrase)
                sys.exit()
            tok.pulse()   # heartbeat so watchdog does not fire during long sleeps
        time.sleep(0.1)


def night_date_str() -> str:
    """Return the observing-night date for log/DB file naming.

    Uses config.session_night_date when set by image_loop (preferred, since it
    accounts for whether we started before or after SUNFLATS).  Falls back to
    the noon-to-noon (-12 h) convention when called outside an imaging session.
    """
    nd = getattr(config, 'session_night_date', '')
    if nd:
        return nd
    return time.strftime('%Y-%m-%d', time.localtime(time.time() - 43200))


def set_log_file_name(target: str) -> None:
    """Set config.LOG_FILE_NAME based on the current target file or target name.

    If a target CSV file has been opened or saved (config.TARGET_FILE_NAME is
    set), the log file takes its stem: e.g. M106_Pelican.csv → M106_Pelican.log.
    Otherwise falls back to <target>_YYYY-MM-DD.log (where target is the name
    of the first imaging target on the list).
    """
    import os
    if config.LOG_DIRECTORY:
        daystr = night_date_str()
        if config.TARGET_FILE_NAME:
            filename = config.TARGET_FILE_NAME + "_" + daystr + ".log"
        else:
            filename = target.replace(" ", "_") + "_" + daystr + ".log"
        config.LOG_FILE_NAME = os.path.join(config.LOG_DIRECTORY, filename)


def unset_log_file_name() -> None:
    """Clear config.LOG_FILE_NAME (disables per-target log file)."""
    config.LOG_FILE_NAME = ""


# ─────────────────────────────────────────────────────────────────────────────
# format_time / decimaltime
# ─────────────────────────────────────────────────────────────────────────────
def format_time(dectimestring: str) -> str:
    """Convert a decimal-hours string to an HH:MM:SS string."""
    dectime = float(dectimestring)
    hour = int(dectime + 0.5 / 3600)
    min_ = int((dectime - hour + 0.5 / 3600) * 60)
    sec  = int((dectime - hour + 0.5 / 3600) * 3600 - min_ * 60)
    return "%02d:%02d:%02d" % (hour, min_, sec)


def decimaltime(ts) -> float:
    """Convert a time.struct_time to decimal hours."""
    return ts.tm_hour + ts.tm_min / 60.0 + ts.tm_sec / 3600.0


# ─────────────────────────────────────────────────────────────────────────────
# ensure_focus  (macOS / Qt focus workaround)
# ─────────────────────────────────────────────────────────────────────────────
def ensure_focus(widget) -> None:
    """
    Ensure *widget* and its application regain focus before showing a dialog
    or tooltip.  Works around macOS Qt focus issues when another Qt app is open.
    Safe on all platforms.
    """
    if widget is None:
        return

    win = widget.window().windowHandle() if widget.window() else None
    if win is not None:
        win.requestActivate()

    if sys.platform == "darwin":
        try:
            import ctypes
            objc = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/AppKit.framework/AppKit"
            )
            objc.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass

###############################################################################
# THEME
###############################################################################




def is_dark() -> bool:
    """Return True if the current colour scheme is dark.

    Primary:  Qt styleHints().colorScheme() — works on macOS and Windows.
    Fallback: window background luminance — reliable on Linux/Fusion/Raspberry Pi
              where colorScheme() returns Unknown.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return False
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return True
    if scheme == Qt.ColorScheme.Light:
        return False
    # Fallback: measure window background luminance
    from PySide6.QtGui import QPalette
    bg = app.palette().color(QPalette.ColorRole.Window)
    luminance = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
    return luminance < 128


# ─── Log panel (QTextEdit text_display) ─────────────────────────────────────
#
# Log messages use explicit colour name strings ("black", "red", "orange",
# "green") that assume a white backdrop.  On a dark background "black" becomes
# invisible; the others are vivid enough to survive either theme but benefit
# from slightly adjusted shades in dark mode for better contrast.

def log_panel_bg() -> str:
    """Background colour for the log QTextEdit."""
    return "#1e1e1e" if is_dark() else "#ffffff"


def log_color(name: str) -> str:
    """Map a log-level colour name to a theme-appropriate value.

    "black" (the implicit default) is replaced by a visible default-text colour.
    Red / orange / green get slightly adjusted shades in dark mode.
    Anything else passes through unchanged.
    """
    dark_map: dict[str, str] = {
        "black":  "#d4d4d4",   # default info text — light grey on dark
        "red":    "#f47878",   # error — softer red on dark
        "orange": "#ffb347",   # warning — warm amber on dark
        "green":  "#73c073",   # success — muted green on dark
    }
    light_map: dict[str, str] = {
        "black":  "#000000",
        "red":    "#cc0000",
        "orange": "#b35900",
        "green":  "#006600",
    }
    m = dark_map if is_dark() else light_map
    return m.get(name, name)   # pass unknown colours through unchanged


# ─── Entry-table cell states (CustomTableWidget / scheduler) ─────────────────
#
# Three semantic states, each mapped to a light and a dark variant.
# "white" / plain-white cells are "neutral" (no validation result yet).

_CELL_MAP_LIGHT: dict[str, str] = {
    "white":       "#ffffff",
    "lightgreen":  "#90ee90",   # valid    — light green
    "#ffcccc":     "#ffcccc",   # invalid  — light pink
    "#90ee90":     "#90ee90",   # valid    — light green (hex alias)
    "#fff3cd":     "#fff3cd",   # warning  — light amber
    "orange":      "#ff8c00",   # nsubs=0  — orange
}
_CELL_MAP_DARK: dict[str, str] = {
    "white":       "#3a3a3a",   # neutral  — dark grey
    "lightgreen":  "#1f4d2b",   # valid    — deep muted green
    "#ffcccc":     "#5c2a2a",   # invalid  — deep muted red
    "#90ee90":     "#1f4d2b",   # valid    — deep muted green (hex alias)
    "#fff3cd":     "#4a3f1f",   # warning  — deep muted amber
    "orange":      "#5c3800",   # nsubs=0  — deep muted orange
}

_CELL_FG_LIGHT: dict[str, str] = {
    "white":       "#000000",
    "lightgreen":  "#000000",
    "#90ee90":     "#000000",
    "#ffcccc":     "#000000",
    "#fff3cd":     "#856404",   # dark amber text on light amber
    "orange":      "#000000",
}
_CELL_FG_DARK: dict[str, str] = {
    "white":       "#e8e8e8",
    "lightgreen":  "#86efac",   # light green text on dark green
    "#90ee90":     "#86efac",
    "#ffcccc":     "#fca5a5",   # light red text on dark red
    "#fff3cd":     "#fde68a",   # light amber text on dark amber
    "orange":      "#fed7aa",   # light peach text on dark orange
}


def cell_fg(bg_color: str) -> str:
    """Foreground (text) colour to pair with a given semantic background colour.

    Pass the same semantic string you passed to cell_bg() / set_cell_color().
    Falls back to cell_text() for unknown strings.
    """
    m = _CELL_FG_DARK if is_dark() else _CELL_FG_LIGHT
    return m.get(bg_color, cell_text())


# ─── Monitor tab panel states ─────────────────────────────────────────────────
#
# Each state returns (bg, border, badge_col, hero_col).
# "quality" is one of: "good" | "marginal" | "poor" | "neutral"

_MONITOR_LIGHT: dict[str, tuple[str, str, str, str]] = {
    "good":     ("#f0faf4", "#a8d5b8", "#1f9d57", "#1f9d57"),
    "marginal": ("#fdf8f0", "#f5d98a", "#d97706", "#d97706"),
    "poor":     ("#fef2f2", "#f5a8a8", "#d1453b", "#d1453b"),
    "neutral":  ("#f8f9fb", "#e2e6ec", "",        "#1e2329"),
}
_MONITOR_DARK: dict[str, tuple[str, str, str, str]] = {
    "good":     ("#1a2d1f", "#2a5c38", "#34d374", "#34d374"),
    "marginal": ("#2d2510", "#7a6020", "#f59e0b", "#f59e0b"),
    "poor":     ("#2d1515", "#7a2828", "#f87171", "#f87171"),
    "neutral":  ("#242424", "#3a3a3a", "",        "#9aa0a8"),
}


def monitor_panel_state(quality: str) -> tuple[str, str, str, str]:
    """Return (bg, border, badge_col, hero_col) for a Monitor panel quality state.

    quality: "good" | "marginal" | "poor" | "neutral"
    """
    m = _MONITOR_DARK if is_dark() else _MONITOR_LIGHT
    return m.get(quality, m["neutral"])


def monitor_guiding_band() -> str:
    """Fill colour for the 'good' threshold band in the guiding RMS graph."""
    return "#1a3d22" if is_dark() else "#e8f5ec"


def monitor_run_badge_bg() -> str:
    """Background for the 'Run N of N' badge in the focus panel header."""
    return "#3a3d42" if is_dark() else "#eef0f3"


def monitor_label_col() -> str:
    """Secondary label text colour (FWHM, Stars, etc.) for Monitor panels."""
    return "#9aa0a8" if is_dark() else "#6b7280"


def monitor_value_col() -> str:
    """Default (non-quality) value text colour for Monitor panels."""
    return "#d0d4da" if is_dark() else "#1e2329"


def cell_bg(color: str) -> str:
    """Translate a semantic cell-background request to the current theme's colour.

    Pass through any colour string not in the known semantic map unchanged.
    """
    m = _CELL_MAP_DARK if is_dark() else _CELL_MAP_LIGHT
    return m.get(color, color)


def cell_normal_bg() -> str:
    """The 'no validation result' cell background for the current theme."""
    return _CELL_MAP_DARK["white"] if is_dark() else _CELL_MAP_LIGHT["white"]


def cell_text() -> str:
    """Text colour for cells that are manually painted (validation states)."""
    return "#e8e8e8" if is_dark() else "#000000"


# ─── Results table (SuggestTargetsDialog) ───────────────────────────────────
#
# The _C_* module-level constants in suggest_targets.py should be initialised
# by calling these functions once at import time.

def results_row_bg() -> str:
    """Normal (even) row background."""
    return "#262626" if is_dark() else "#ffffff"


def results_alt_bg() -> str:
    """Alternating (odd) row background."""
    return "#2e2e2e" if is_dark() else "#f0f4fa"


def results_header_bg() -> str:
    """Category-header row background."""
    return "#1c3a5c" if is_dark() else "#dce8f8"


def results_header_text() -> str:
    """Category-header / label text colour."""
    return "#7eb8ee" if is_dark() else "#1a4a8a"


def results_text() -> str:
    """Normal data-row text colour."""
    return "#e0e0e0" if is_dark() else "#1a1a1a"


# ─── Settings-dialog input fields ────────────────────────────────────────────

def input_bg() -> str:
    return "#3a3a3a" if is_dark() else "#ffffff"


def input_text() -> str:
    return "#e0e0e0" if is_dark() else "#000000"


def input_border() -> str:
    return "#666666" if is_dark() else "#3a3a3a"


def jump_bar_selected_bg() -> str:
    return "#505050" if is_dark() else "#d0d0d0"


def input_error_bg() -> str:
    return "#5c2a2a" if is_dark() else "#ffcccc"


def input_error_border() -> str:
    return "#cc4444" if is_dark() else "#cc0000"


# ─── CustomTableWidget grid lines ────────────────────────────────────────────

def table_grid_col() -> str:
    """Gridline colour for CustomTableWidget body cells.

    Light value chosen to match the QHeaderView section-separator colour so
    the body grid is visually consistent with the header dividers.
    """
    return "#555555" if is_dark() else "#c0c0c0"

###############################################################################
# ICONS
###############################################################################


import base64
from PySide6.QtGui import QIcon, QPixmap

_TSXS_B64 = (
    "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"
)

_TSXIMAGEINFO_B64 = (
    "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"
)

_TSXSETTINGS_B64 = (
    "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"
    "QW0jTHYAAAAASUVORK5CYII="
)

_TSXS_TARGETS_B64 = (
    "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"
    "TkSuQmCC"
)

# The Polar Alignment tool's icon, carried over from the original PAUI.py
# so the rewritten tool is recognisable as the same thing.
_PAUI_B64 = (
    "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"
)


def _make_icon(b64: str) -> QIcon:
    px = QPixmap()
    px.loadFromData(base64.b64decode(b64))
    return QIcon(px)

def app_icon()         -> QIcon: return _make_icon(_TSXS_B64)
def imageinfo_icon()-> QIcon: return _make_icon(_TSXIMAGEINFO_B64)
def settings_icon() -> QIcon: return _make_icon(_TSXSETTINGS_B64)
def targets_app_icon() -> QIcon: return _make_icon(_TSXS_TARGETS_B64)
def polar_app_icon()   -> QIcon: return _make_icon(_PAUI_B64)

###############################################################################
# TSX_COMMS
###############################################################################



import os
import platform
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Globals local to this module
# ─────────────────────────────────────────────────────────────────────────────
TSXSendLock = threading.Lock()
asynctoken  = None   # Holds the stop-token when an async job is running


# ─────────────────────────────────────────────────────────────────────────────
# Core socket communication
# ─────────────────────────────────────────────────────────────────────────────
def TSXSendTry(message: str, timeout: float = 120) -> list[str]:
    """
    Send *message* (JavaScript) to TheSkyX via TCP and return the response
    split on '|'.

    *timeout* is the socket timeout in seconds (default 120).  Pass a larger
    value for commands that legitimately take a long time (e.g. CLS slews).

    Uses a threading lock so that multiple threads cannot send simultaneously.
    On failure, attempts to restart TheSkyX and then exits.
    """
    TCP_IP   = '127.0.0.1'
    TCP_PORT = 3040
    BUFFER_SIZE = 50000

    tryMessage = (
        " /* Java Script */ try { "
        + message
        + " } catch (e) { out = e; } "
    )

    try:
        if config.verbose:
            output(
                logtime()
                + f"Thread {threading.current_thread().name} "
                + "waiting to acquire lock"
            )

        with TSXSendLock:
            if config.verbose:
                output(
                    logtime()
                    + f"Thread {threading.current_thread().name} "
                    + "acquired lock for message.)"
                )
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((TCP_IP, TCP_PORT))
            s.sendall(tryMessage.encode())
            data = s.recv(BUFFER_SIZE)
            s.close()

        if config.verbose:
            output(str(data))

        return data.decode().split("|")

    except socket.timeout:
        output(logtime() + f"TSX stopped responding (timeout after {timeout}s).", ERROR)
        output(logtime() + "Attempting restart and emergency park.")
        send_mail_message("TSX Timed Out", f"TSX stopped responding after {timeout}s. Attempting restart.")
        (process, status) = restartTheSkyX()
        # Note: restartTheSkyX() currently calls sys.exit() so the lines below
        # are only reached if that behaviour changes in the future.
        if status == 0:
            send_mail_message("TSX Timed Out but...", "Successfully restarted imaging.")
        else:
            send_mail_message("TSX Timed Out", "Could Not Restart TSX.")
            _finish_async()
            sys.exit()

    except Exception:
        output(logtime() + "Could not connect to TSX.", ERROR)
        output(logtime() + "Trying to restart....")
        send_mail_message("TSX Died. Trying to restart.", "Trying to restart.")
        (process, status) = restartTheSkyX()
        # Note: restartTheSkyX() currently calls sys.exit() so the lines below
        # are only reached if that behaviour changes in the future.
        if status == 0:
            send_mail_message("TSX Died but...", "Successfully restarted imaging.")
        else:
            send_mail_message("TSX Died", "Could Not Restart TSX.")
            _finish_async()
            sys.exit()


# ─────────────────────────────────────────────────────────────────────────────
# Process management helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_tsx_pids() -> list[int]:
    """Return PIDs of all running TheSkyX processes (cross-platform)."""
    try:
        if sys.platform == "win32":
            pids: list[int] = []
            for exe in ("TheSkyX.exe", "TheSkyX64.exe"):
                out = subprocess.check_output(
                    ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"],
                    universal_newlines=True, stderr=subprocess.DEVNULL,
                )
                for line in out.splitlines():
                    parts = line.strip().strip('"').split('","')
                    if len(parts) >= 2:
                        try:
                            pids.append(int(parts[1]))
                        except ValueError:
                            pass
            return pids
        else:
            out = subprocess.check_output(
                ["pgrep", "-f", "TheSkyX"], universal_newlines=True
            )
            return [int(pid) for pid in out.splitlines()]
    except subprocess.CalledProcessError:
        return []


# Keep old name as an alias so any external callers still work.
def find_process_by_name_unix(process_name: str) -> list[int]:
    return find_tsx_pids()


def kill_process_by_pid(pid: int) -> int:
    """Kill process *pid*.  Returns 0 on success, 1 on error."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                output(logtime() + f"Process with PID {pid} has been terminated.")
                return 0
            output(logtime() + f"Failed to terminate PID {pid}: {result.stderr.strip()}")
            return 1
        else:
            os.kill(pid, signal.SIGKILL)
            output(logtime() + f"Process with PID {pid} has been terminated.")
            return 0
    except ProcessLookupError:
        output(logtime() + f"No process with PID {pid} found.")
        return 1
    except PermissionError:
        output(logtime() + f"Permission denied to terminate process with PID {pid}.")
        return 1
    except Exception as e:
        output(logtime() + f"Error terminating process with PID {pid}: {e}")
        return 1


def KillTheSkyX() -> None:
    """Kill all running TheSkyX processes (cross-platform)."""
    pids = find_tsx_pids()
    if pids:
        output(logtime() + "TSX still running though cannot talk to it. Killing processes first.")
        for pid in pids:
            if kill_process_by_pid(pid):
                output(logtime() + "Could not kill TheSkyX. Exiting.", ERROR)
                _finish_async()
                sys.exit()
        time.sleep(5)

    pids = find_tsx_pids()
    if pids:
        output(logtime() + "TSX still running despite killing it. Exiting.", ERROR)
        _finish_async()
        sys.exit()


def restartTheSkyX():
    """Kill and restart TheSkyX, reconnect devices, then exit the current thread."""
    KillTheSkyX()

    install_file = config.asf_directory() / "TheSkyXInstallPath.txt"
    try:
        install_dir = install_file.read_text(encoding="utf-8").splitlines()[0].strip()
    except Exception as e:
        send_mail_message("Cannot Restart TSX",
                          f"Could not read install path from {install_file}: {e}")
        return (None, 1)

    system = platform.system()
    if system == "Linux":
        # X11 display argument required on headless Linux
        args = [install_dir + "/TheSkyX", "-display", ":0"]
    elif system == "Darwin":
        args = [install_dir + "/MacOS/TheSkyX"]
    elif sys.platform == "win32":
        tsx64 = Path(install_dir) / "TheSkyX64.exe"
        tsx32 = Path(install_dir) / "TheSkyX.exe"
        args = [str(tsx64 if tsx64.exists() else tsx32)]
    else:
        send_mail_message("Cannot Restart TSX",
                          f"Unsupported platform: {system}")
        return (None, 1)

    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        output(logtime() + "TSXStartup Errors: File not found.")
        return (None, 1)
    except PermissionError:
        output(logtime() + "TSXStartup Errors: Permissions invalid.")
        return (None, 1)
    except OSError as e:
        output(logtime() + f"TSXStartup Errors: OS error: {e}")
        return (None, 1)
    except ValueError as e:
        output(logtime() + f"TSXStartup Errors: Invalid input: {e}")
        return (process, 1)

    output(logtime() + "TSX restarted. Waiting for 10 seconds to allow TSX to restart fully.")
    time.sleep(10)

    # Call EmergencyPark via the callback registered in config to avoid
    # a circular import with imaging_loop.
    if config.emergency_park_fn is not None:
        output(logtime() + "TSX restarted. Triggering emergency park.")
        config.emergency_park_fn()
    else:
        # emergency_park_fn was already cleared — TSX failed while a park was
        # already in progress.  The mount may not be parked.
        output(logtime() + "TSX failed during emergency park — mount may not be parked.", ERROR)
        send_mail_message(
            "TSX Failed During Emergency Park",
            "TSX stopped responding while attempting to park the mount.\n\n"
            "The mount may NOT be parked. Please check equipment immediately.",
        )

    sys.exit()

    # The code below is unreachable while sys.exit() is called above, but is
    # kept in case the restart strategy changes in the future.
    _dc = device_control
    if _dc.connectscope():    return (process, 1)
    if _dc.connectcamera():   return (process, 1)
    if _dc.connectfocuser():  return (process, 1)
    if _dc.connectautoguider(): return (process, 1)
    if config.QFilterWheel:
        _fw = filter_wheel
        if _fw.connectFW():   return (process, 1)
    if config.QDome:
        if _dc.connectDome(): return (process, 1)

    output(logtime() + "All devices connected. Trying to continue imaging.")
    return (process, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Simulator / test-flag detection
# ─────────────────────────────────────────────────────────────────────────────
def setTestFlags() -> None:
    """
    Query TheSkyX for selected hardware and set the global test flags in
    config accordingly.
    """
    camera = TSXSendTry("SelectedHardware.cameraModel")[0]
    config.testflat = (camera == "Camera Simulator")

    focuser = TSXSendTry("SelectedHardware.focuserModel")[0]
    if focuser == "<No Focuser Selected>":
        config.QFocuser = False
        config.testfoc  = True
        output(logtime() + "No focuser selected.")
    elif focuser == "Focuser Simulator":
        config.QFocuser = True
        config.testfoc  = True
    else:
        config.QFocuser = True
        config.testfoc  = False

    dome = TSXSendTry("SelectedHardware.domeModel")[0]
    if dome == "<No Dome Selected>":
        config.QDome = False
        output(logtime() + "No dome selected.")
    else:
        config.QDome = True


def simulatedMount() -> bool:
    """
    Return True if a mount simulator is selected, and set config.SUN
    to an appropriate test value.
    """
    mount = TSXSendTry("SelectedHardware.mountModel")[0]
    if mount == "Telescope Mount Simulator":
        if config.QDuskFlats:
            config.SUN = -2
        else:
            config.SUN = config.SUNIMAGING - 1.0
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────
def _finish_async() -> None:
    """
    Call finish_async_code() if an asynctoken is active.
    finish_async_code is a legacy symbol (not currently defined); this wrapper
    silently does nothing if it cannot be resolved.
    """
    try:
        finish_async_code()   # noqa: F821
    except NameError:
        pass

###############################################################################
# COORDINATES
###############################################################################



import csv
import math
import sys
import time



# ─────────────────────────────────────────────────────────────────────────────
# Trig helpers (degrees)
# ─────────────────────────────────────────────────────────────────────────────

def sind(ang: float) -> float:  return math.sin(ang * math.pi / 180.0)
def cosd(ang: float) -> float:  return math.cos(ang * math.pi / 180.0)
def acosd(cosval: float) -> float: return math.acos(cosval) * 180.0 / math.pi
def asind(sinval: float) -> float: return math.asin(sinval) * 180.0 / math.pi

def angular_sep_deg(ra1_h: float, dec1_deg: float, ra2_h: float, dec2_deg: float) -> float:
    """Great-circle separation between two RA(hours)/Dec(deg) points, in degrees."""
    ra1, ra2 = ra1_h * 15.0, ra2_h * 15.0
    cos_sep = (sind(dec1_deg) * sind(dec2_deg)
               + cosd(dec1_deg) * cosd(dec2_deg) * cosd(ra1 - ra2))
    return acosd(max(-1.0, min(1.0, cos_sep)))


# ─────────────────────────────────────────────────────────────────────────────
# Sun altitude and twilight times
# ─────────────────────────────────────────────────────────────────────────────

def sun_setting() -> bool:
    """Return True if the Sun is west of the meridian (setting), False if rising.

    Uses the same hour-angle sign convention as RADecLSTtoAlt: sind(H) > 0
    means the object is west of the meridian (hour angle positive → setting).
    """
    ra, dec = radec("Sun")
    _, _, lst, _ = LatLongLstUT()
    _, setting = RADecLSTtoAlt(ra, dec, lst)
    return setting


def sun_alt() -> float:
    """Return current Sun altitude in degrees (or config.SUN when testing)."""
    MESSAGE = (
        " /* Java Script */ "
        'sky6StarChart.Find("Sun"); '
        "sky6ObjectInformation.Property(59); "
        "sky6ObjectInformation.ObjInfoPropOut; "
    )
    data = TSXSendTry(MESSAGE)
    try:
        solar_alt = float(data[0])
    except ValueError:
        raise RuntimeError(
            f"TheSkyX comms error in sun_alt() — unexpected response: {data[0]!r}"
        )
    return config.SUN if config.testing else solar_alt


def nautical_twilight() -> str:
    MESSAGE = (
        " /* Java Script */ "
        'sky6StarChart.Find("Sun"); '
        "sky6ObjectInformation.Property(170); "
        "sky6ObjectInformation.ObjInfoPropOut; "
    )
    data = TSXSendTry(MESSAGE)
    try:
        return format_time(data[0])
    except ValueError:
        output(logtime() + f"TheSkyX comms error in nautical_twilight() — unexpected response: {data[0]!r}", ERROR)
        return "--:--:--"


def civil_twilight() -> str:
    MESSAGE = (
        " /* Java Script */ "
        'sky6StarChart.Find("Sun"); '
        "sky6ObjectInformation.Property(167); "
        "sky6ObjectInformation.ObjInfoPropOut; "
    )
    data = TSXSendTry(MESSAGE)
    try:
        return format_time(data[0])
    except ValueError:
        output(logtime() + f"TheSkyX comms error in civil_twilight() — unexpected response: {data[0]!r}", ERROR)
        return "--:--:--"


def sunset() -> str:
    MESSAGE = (
        " /* Java Script */ "
        'sky6StarChart.Find("Sun"); '
        "sky6ObjectInformation.Property(69); "
        "sky6ObjectInformation.ObjInfoPropOut; "
    )
    data = TSXSendTry(MESSAGE)
    try:
        return format_time(data[0])
    except ValueError:
        output(logtime() + f"TheSkyX comms error in sunset() — unexpected response: {data[0]!r}", ERROR)
        return "--:--:--"


# ─────────────────────────────────────────────────────────────────────────────
# Target lookup
# ─────────────────────────────────────────────────────────────────────────────

def get_tsx_name0(target: str) -> str:
    """Return TSX property 0 (the primary name used in filenames) for *target*.

    This is the name TheSkyX uses when auto-saving images, so it can differ
    from the name the user typed (e.g. "IC 5067" vs "Pelican Nebula").
    Returns an empty string if the target is not found or TSX is unavailable.
    """
    MESSAGE = (
        f'sky6StarChart.Find("{target}"); '
        'sky6ObjectInformation.Property(0); '
        'sky6ObjectInformation.ObjInfoPropOut; '
    )
    try:
        data = TSXSendTry(MESSAGE)
        return data[0].strip() if data else ""
    except Exception:
        return ""


def find(target: str) -> int:
    """Return 0 if *target* is found in TheSkyX, 1 if not found."""
    MESSAGE = (
        ' /* Java Script */ '
        'out = "0"; '
        'try { sky6StarChart.Find("' + target + '"); } '
        'catch (repErr) { out = "1"; } '
        'out; '
    )
    data = TSXSendTry(MESSAGE)
    return 1 if data[0] == "1" else 0


def altaz(target: str) -> tuple[float, float]:
    """Return (altitude, azimuth) of *target* in degrees."""
    MESSAGE = (
        " /* Java Script */ "
        "var alt; var azm; "
        'sky6StarChart.Find("' + target + '"); '
        "sky6ObjectInformation.Property(59); "
        "alt = sky6ObjectInformation.ObjInfoPropOut; "
        "sky6ObjectInformation.Property(58); "
        "azm = sky6ObjectInformation.ObjInfoPropOut; "
        'out = alt + "|" + azm '
    )
    data = TSXSendTry(MESSAGE)
    try:
        return float(data[0]), float(data[1])
    except ValueError:
        raise RuntimeError(
            f"TheSkyX comms error in altaz({target!r}) — unexpected response: {data!r}"
        )


def radec(target: str) -> tuple[float, float]:
    """Return (RA hours, Dec degrees) of *target* in the current epoch."""
    MESSAGE = (
        " /* Java Script */ "
        "var ra; var dec; "
        'sky6StarChart.Find("' + target + '"); '
        "sky6ObjectInformation.Property(54); "
        "ra = sky6ObjectInformation.ObjInfoPropOut; "
        "sky6ObjectInformation.Property(55); "
        "dec = sky6ObjectInformation.ObjInfoPropOut; "
        'out = ra + "|" + dec '
    )
    data = TSXSendTry(MESSAGE)
    try:
        return float(data[0]), float(data[1])
    except ValueError:
        raise RuntimeError(
            f"TheSkyX comms error in radec({target!r}) — unexpected response: {data!r}"
        )


def radec_j2000(target: str) -> tuple[float, float]:
    """Return (RA hours, Dec degrees) of *target* in J2000 / ICRS epoch.

    Use this when querying external services (SkyView, etc.) that expect J2000
    rather than the current apparent coordinates returned by radec().
    """
    MESSAGE = (
        " /* Java Script */ "
        "var ra; var dec; "
        'sky6StarChart.Find("' + target + '"); '
        "sky6ObjectInformation.Property(56); "
        "ra = sky6ObjectInformation.ObjInfoPropOut; "
        "sky6ObjectInformation.Property(57); "
        "dec = sky6ObjectInformation.ObjInfoPropOut; "
        'out = ra + "|" + dec '
    )
    data = TSXSendTry(MESSAGE)
    try:
        return float(data[0]), float(data[1])
    except ValueError:
        raise RuntimeError(
            f"TheSkyX comms error in radec_j2000({target!r}) — unexpected response: {data!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Location and sidereal time
# ─────────────────────────────────────────────────────────────────────────────

def LatLongLstUT() -> tuple[float, float, float, float]:
    """Return (latitude, longitude, LST, UT) from TheSkyX."""
    MESSAGE = (
        " /* Java Script */ "
        'var Out=""; '
        "var sk6DocProp_Latitude = 0; "
        "var sk6DocProp_Longitude = 1; "
        "var sk6DocProp_JulianDateNow = 9; "
        "sky6StarChart.DocumentProperty(sk6DocProp_Latitude); "
        "dLat = sky6StarChart.DocPropOut; "
        "sky6StarChart.DocumentProperty(sk6DocProp_Longitude); "
        "dLon = sky6StarChart.DocPropOut; "
        "sky6Utils.ComputeLocalSiderealTime(); "
        "dLST = sky6Utils.dOut0; "
        "sky6Utils.ComputeUniversalTime(); "
        "dUT = sky6Utils.dOut0; "
        'Out += String(dLat) + "|"; '
        'Out += String(dLon) + "|"; '
        'Out += String(dLST) + "|"; '
        "Out += String(dUT); "
    )
    data = TSXSendTry(MESSAGE)
    try:
        return float(data[0]), float(data[1]), float(data[2]), float(data[3])
    except ValueError:
        raise RuntimeError(
            f"TheSkyX comms error in LatLongLstUT() — unexpected response: {data!r}"
        )


def TSXChartTime() -> float:
    """Return the current chart time from TheSkyX as decimal hours."""
    MESSAGE = (
        " /* Java Script */ "
        "sky6StarChart.DocumentProperty(9); "
        "chartJD = sky6StarChart.DocPropOut; "
        "sky6Utils.ConvertJulianDateToCalender(chartJD); "
        "year   = sky6Utils.dOut0; "
        "month  = sky6Utils.dOut1; "
        "day    = sky6Utils.dOut2; "
        "hour   = sky6Utils.dOut3; "
        "minute = sky6Utils.dOut4; "
        "second = sky6Utils.dOut5; "
        "out = hour + '|' + minute + '|' + second + '|'; "
    )
    data = TSXSendTry(MESSAGE)
    try:
        h = float(data[0])
        m = float(data[1])
        s = float(data[2])
    except ValueError:
        output(logtime() + f"TheSkyX comms error in TSXChartTime() — unexpected response: {data!r}", ERROR)
        return 0.0
    return h + m / 60 + s / 3600


# ─────────────────────────────────────────────────────────────────────────────
# Rise / set LST calculations
# ─────────────────────────────────────────────────────────────────────────────

def LSTRise(alt: float, lat: float, dec: float, ra: float) -> float:
    cosh = (sind(alt) - sind(lat) * sind(dec)) / cosd(lat) / cosd(dec)
    if cosh >  1: return  1000.0
    if cosh < -1: return -1000.0
    H = acosd(cosh) / 15.0
    return -H + ra


def LSTSet(alt: float, lat: float, dec: float, ra: float) -> float:
    cosh = (sind(alt) - sind(lat) * sind(dec)) / cosd(lat) / cosd(dec)
    if cosh >  1: return -1000.0
    if cosh < -1: return  1000.0
    H = acosd(cosh) / 15.0
    return H + ra


def RADecLSTtoAlt(ra: float, dec: float, lst: float) -> tuple[float, bool]:
    """Return (altitude, setting) for the given RA/Dec at *lst*."""
    H = (lst - ra) * 15.0
    sinalt = sind(dec) * sind(config.lat) + cosd(dec) * cosd(config.lat) * cosd(H)
    alt = asind(sinalt)
    setting = sind(H) > 0
    return alt, setting


# ─────────────────────────────────────────────────────────────────────────────
# Time / coordinate normalisation and formatting
# ─────────────────────────────────────────────────────────────────────────────

def range24(t: float) -> float:
    """
    Map decimal hours into the range 12–36 (spanning midday → midnight →
    following midday) so that rise/set sequences are monotonically increasing.

    Returns ±1000 for circumpolar / never-rises special cases.
    """
    if t >  100: return  1000.0
    if t < -100: return -1000.0
    i = math.floor(t / 24)
    t -= i * 24
    if t < 12:
        t += 24
    return t


def formatdecdec(dec: float) -> str:
    d = math.floor(dec + 0.5 / 3600)
    m = math.floor((dec - d + 0.5 / 3600) * 60)
    s = math.floor((dec - d + 0.05 / 3600) * 3600 - m * 60)
    return '%02d\N{DEGREE SIGN} %02d\' %02d"' % (d, m, s)


def formatdecra(ra: float) -> str:
    h = math.floor(ra + 0.5 / 3600)
    m = math.floor((ra - h + 0.5 / 3600) * 60)
    s = math.floor((ra - h + 0.5 / 3600) * 3600 - m * 60)
    return '%02dh %02dm %02ds' % (h, m, s)


def formatdectime(t: float) -> str:
    if t > 24:
        t -= 24.0
    h = math.floor(t + 0.5 / 60)
    m = math.floor((t - h + 0.5 / 60) * 60)
    return '%02d:%02d' % (h, m)


# ─────────────────────────────────────────────────────────────────────────────
# Target file reader / scheduler
# ─────────────────────────────────────────────────────────────────────────────

def readtargets(targetfilename: str):
    """
    Read a CSV target file and compute an approximate imaging schedule.

    Returns: (target, exposure, filters, start_alt, end_alt) lists.
    Also updates config.tdusk and config.tdawn.
    """
    target    = []
    exposure  = []
    filters   = []
    start_alt = []
    end_alt   = []
    start_t   = []
    end_t     = []

    # Ensure TheSkyX clock is in sync with the system clock
    TSXSendTry('TheSkyXAction.execute("TIMESKIP_USECOMPUTERCLOCK")')
    lat, longitude, LST, UT = LatLongLstUT()
    tnow = decimaltime(time.localtime())

    with open(targetfilename, "r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)   # skip header
        for row in reader:
            if row[0].startswith("#"):
                continue

            if find(row[0]) == 1:
                sys.exit("Exiting. Target %s not found" % row[0])

            target.append(_preferred_name(row[0]))
            exposure.append(float(row[1]))
            filters.append(row[2].strip())

            if row[3][0] == 'r':
                start_alt.append(float(row[3][1:]))
            elif row[3][0] == 's':
                start_alt.append(-float(row[3][1:]))
            else:
                sys.exit("Exiting. Starting Altitude '%s' must begin with (r)ising or (s)etting." % row[3])

            if row[4][0] == 'r':
                end_alt.append(float(row[4][1:]))
            elif row[4][0] == 's':
                end_alt.append(-float(row[4][1:]))
            else:
                sys.exit("Exiting. Ending Altitude '%s' must begin with (r)ising or (s)etting." % row[4])

            start_t.append(0.0)
            end_t.append(24.0)

    for i in range(len(target)):
        ra, dec = radec(target[i])
        if start_alt[i] >= 0:
            start_t[i] = range24(LSTRise(start_alt[i], lat, dec, ra) - LST + tnow)
        else:
            start_t[i] = range24(LSTSet(-start_alt[i], lat, dec, ra) - LST + tnow)

        if end_alt[i] >= 0:
            end_t[i] = range24(LSTRise(end_alt[i], lat, dec, ra) - LST + tnow)
        else:
            end_t[i] = range24(LSTSet(-end_alt[i], lat, dec, ra) - LST + tnow)

        if start_t[i] > 100.0:
            sys.exit("Exiting. Target %s never reaches altitude of %3.1f." % (target[i], start_alt[i]))
        if end_t[i] < -100.0:
            sys.exit("Exiting. Target %s always below setting altitude of %3.1f." % (target[i], end_alt[i]))
        if end_t[i] > 100.0 and i != len(target) - 1:
            output("Warning. Target %s never sets below altitude of %3.1f." % (target[i], end_alt[i]))
            output("Remaining targets will not get imaged.")

    ra, dec = radec("Sun")
    tsunset   = range24(LSTSet(0.0,   lat, dec, ra) - LST + tnow)
    tcivils   = range24(LSTSet(-6.0,  lat, dec, ra) - LST + tnow)
    tnauticals = range24(LSTSet(-12,  lat, dec, ra) - LST + tnow)
    tsunrise  = range24(LSTRise(0.0,  lat, dec, ra) - LST + tnow)
    tcivilr   = range24(LSTRise(-6.0, lat, dec, ra) - LST + tnow)
    tnauticalr = range24(LSTRise(-12.0, lat, dec, ra) - LST + tnow)
    config.tdusk = range24(LSTRise(config.SUNIMAGING, lat, dec, ra) - LST + tnow)
    config.tdawn = range24(LSTRise(config.SUNIMAGING, lat, dec, ra) - LST + tnow)

    if 0 < tnow < tsunrise - 24:
        tnow = range24(tnow)

    output(" ")
    output("Summary of Imaging Programme")
    output("============================")
    if tnow < tsunset:
        output("Wait for sunset at %s." % formatdectime(tsunset))
    if tnow < tcivils and config.QDuskFlats:
        output("Take dusk flats")
    if tnow < config.tdusk:
        output("Wait for imaging dusk at %s." % formatdectime(config.tdusk))
        tlast = config.tdusk
    else:
        tlast = tnow

    for i in range(len(target)):
        if tlast < start_t[i]:
            output("Wait for target %s to rise to %3.1f at %s." % (
                target[i], start_alt[i], formatdectime(start_t[i])
            ))
            tstart = start_t[i]
        else:
            tstart = tlast
        tend = tnauticalr if tnauticalr < end_t[i] else end_t[i]
        if tnow < tend:
            nsubs = (tend - tstart) * 3600 / (exposure[i] + 6 * config.AG_exp_min + 15)
            output("Take ~ %d subs of target %s length %3.1fs filters %s finishing %s." % (
                nsubs, target[i], exposure[i], filters[i], formatdectime(tend)
            ))
            tlast = tend
        else:
            output("Target %s not imaged. Last target image until dawn." % target[i])

    output("Imaging ends at %s." % formatdectime(config.tdawn))
    output("Wait for civil twilight at %s." % formatdectime(tcivilr))
    if config.QDawnFlats:
        output("Take dawn flats.")
    output("Finish")
    output(" ")

    return target, exposure, filters, start_alt, end_alt

###############################################################################
# FILTER_WHEEL
###############################################################################





# ─────────────────────────────────────────────────────────────────────────────
# Low-level filter queries
# ─────────────────────────────────────────────────────────────────────────────

def numberFilters() -> int:
    data = TSXSendTry(" /* Java Script */ ccdsoftCamera.lNumberFilters; ")
    try:
        return int(data[0])
    except ValueError:
        raise RuntimeError(
            f"TheSkyX comms error in numberFilters() — unexpected response: {data[0]!r}"
        )


def getFilterName(ifilt: int) -> str:
    data = TSXSendTry(
        " /* Java Script */ ccdsoftCamera.szFilterName(" + str(ifilt) + "); "
    )
    return data[0]


def SetFilter(name: str) -> None:
    """Set the active filter by its first-letter key (e.g. 'L', 'R').

    FilterIndexZeroBased is a TSX property setter — it echoes back whatever
    value was assigned regardless of validity, and the wheel does not physically
    move until the next TakeImage() call.  No meaningful error return exists.
    """
    MESSAGE = (
        "ccdsoftCamera.FilterIndexZeroBased = "
        + str(config.FilterDict[name])
        + "; "
    )
    TSXSendTry(MESSAGE)


# ─────────────────────────────────────────────────────────────────────────────
# Full connection + validation
# ─────────────────────────────────────────────────────────────────────────────

def connectFW() -> int:
    """
    Connect the filter wheel and validate all filter names against the current
    settings.  Populates config.QFilterWheel, config.NFilters,
    config.FilterDict, and config.FilterNames.

    Returns 0 on success, 1 on any error.
    """
    # Check whether a filter wheel has been selected at all
    if (TSXSendTry("SelectedHardware.filterWheelModel"))[0] == \
            "<No Filter Wheel Selected>":
        output(logtime() + "No filter wheel selected")
        config.QFilterWheel = False
        return 0

    # Attempt connection
    data = TSXSendTry(" /* Java Script */ ccdsoftCamera.filterWheelConnect(); ")
    if data[0] != "0":
        output(logtime() + "Could not connect filterwheel: " + data[0], ERROR)
        return 1

    output(logtime() + "Filter Wheel connected")
    try:
        config.NFilters = numberFilters()
    except RuntimeError as e:
        output(logtime() + f"Could not query filter count: {e}", ERROR)
        return 1

    # The filter-wheel simulator has 125 positions; cap it at 7
    if TSXSendTry("SelectedHardware.filterWheelModel")[0] == "Filter Wheel Simulator":
        config.NFilters = 7

    # Reset dictionaries in case this is a reconnect
    config.FilterDict.clear()
    config.FilterNames.clear()

    # Validate each filter name
    for ifilt in range(config.NFilters):
        fname = getFilterName(ifilt)

        # 'F' is reserved — @Focus3 uses it as a sequence trigger
        if fname[0] == 'F':
            output(logtime() + "Filter %s at position %d starts with 'F'." % (fname, ifilt), WARNING)
            output(logtime() + "F is used to request an @Focus3 refocus in sequences.", WARNING)
            output(logtime() + "Filter names cannot start with 'F'.", WARNING)
            output(logtime() + "Exit and update filter names in TheSky.", ERROR)
            return 1

        # First-letter must be unique
        if fname[0] in config.FilterDict:
            output(
                logtime()
                + "Filter %d initial %s duplicate with initial of filter %d"
                % (ifilt, fname[0], config.FilterDict[fname[0]]),
                WARNING,
            )
            output(logtime() + "Exit and update filter names in TheSky.", ERROR)
            return 1

        config.FilterDict[fname[0]] = ifilt
        config.FilterNames.append(fname)

    # Validate that the configured focus/dawn filters are present
    config.QFilterError = False

    if config.FocusFilter not in config.FilterDict:
        output(
            logtime() + "FocusFilter %s not in list of filternames" % config.FocusFilter,
            WARNING,
        )
        output(logtime() + "Update filter to use for focus to continue.", ERROR)
        config.QFilterError = True

    for f in config.DawnFilters:
        if f not in config.FilterDict:
            output(
                logtime() + "Filter %s in DawnFilters not in list of filternames" % f,
                WARNING,
            )
            output(logtime() + "Update filters in dawn filter order to continue.", ERROR)
            config.QFilterError = True

    config.QFilterWheel = True
    return 0

###############################################################################
# HORIZON
###############################################################################


import math
from pathlib import Path



_SIDEREAL_RATE = 24.0 / 23.9345   # LST hours per solar hour
_STEP_H        = 2.0 / 60.0        # 2-minute step size in decimal hours


def load_horizon(path: str = "") -> list[float] | None:
    """
    Load a TheSkyX .hrz file and return a list of horizon altitude limits.

    File format:
        Line 1  : N  — number of equally-spaced azimuth points
        Lines 2+: one altitude (degrees) per line for azimuths
                  360/N°,  2×360/N°,  ...,  360°

    Any number of points is supported; the step size is inferred as 360/N.
    Returns a list of N floats, or None if the file is missing or unreadable.
    """
    p = Path(path) if path else (config.asf_directory() / "Custom Horizon.hrz")
    if not p.exists():
        return None
    try:
        lines = [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]
        n = int(lines[0])
        return [float(lines[i + 1]) for i in range(n)]
    except Exception:
        return None


def _horizon_limit(alts: list[float], az_deg: float) -> float:
    """
    Return the linearly interpolated horizon altitude at az_deg.

    Works for any number of equally-spaced samples N, where sample i
    corresponds to azimuth (i+1)×(360/N)°.
    """
    n    = len(alts)
    step = 360.0 / n
    az   = az_deg % 360                    # map to [0, 360)
    fi   = az / step - 1.0                 # fractional 0-based index
    i0   = int(math.floor(fi)) % n
    i1   = (i0 + 1) % n
    frac = fi - math.floor(fi)
    return alts[i0] * (1.0 - frac) + alts[i1] * frac


def _altaz(ra: float, dec: float, lat: float, lst: float) -> tuple[float, float]:
    """
    Return (altitude, azimuth) in degrees for a target at RA (hours) / Dec
    (degrees) observed from latitude lat (degrees) at LST (decimal hours).
    Azimuth is measured North through East, 0–360°.
    """
    def sind(x): return math.sin(math.radians(x))
    def cosd(x): return math.cos(math.radians(x))

    H      = (lst - ra) * 15.0                          # hour angle, degrees
    sinalt = sind(dec) * sind(lat) + cosd(dec) * cosd(lat) * cosd(H)
    sinalt = max(-1.0, min(1.0, sinalt))
    alt    = math.degrees(math.asin(sinalt))

    cosalt = math.cos(math.radians(alt))
    if cosalt < 1e-10:                                   # at zenith
        return alt, 0.0

    sinaz = -cosd(dec) * sind(H) / cosalt
    cosaz = (sind(dec) - sinalt * sind(lat)) / (cosalt * cosd(lat))
    az    = math.degrees(math.atan2(sinaz, cosaz)) % 360
    return alt, az


def blocked_minutes(
    ra: float,
    dec: float,
    alts: list[float],
    t_start: float,
    t_end: float,
) -> float:
    """
    Return the number of minutes within [t_start, t_end] (decimal hours,
    same convention as config.tnow) during which the target is below the
    custom horizon.

    Uses the same 2-minute step size as visibility_windows.
    """
    lat  = config.lat
    lst0 = config.LST
    t0   = config.tnow

    blocked = 0
    t = t_start
    while t <= t_end:
        elapsed = t - t0
        lst     = (lst0 + elapsed * _SIDEREAL_RATE) % 24.0
        alt, az = _altaz(ra, dec, lat, lst)
        if alt <= _horizon_limit(alts, az):
            blocked += 1
        t += _STEP_H

    return blocked * _STEP_H * 60.0


def visibility_windows(
    ra:  float,
    dec: float,
    alts: list[float],
    min_window_minutes: float = 5.0,
) -> list[tuple[float, float]]:
    """
    Compute windows during which the target (RA hours, Dec degrees) is above
    the custom horizon for the next 24 hours.

    Uses config.lat, config.LST and config.tnow for the observer location and
    current time.  Steps through time in 2-minute increments.

    min_window_minutes filters out brief appearances shorter than this
    duration (e.g. the target grazing the top of a notch in the horizon).

    Returns a list of (t_start, t_end) tuples in local decimal hours using
    the same convention as the rest of the codebase — times may exceed 24
    for post-midnight windows; formatdectime() handles this correctly.
    """
    lat     = config.lat
    lst0    = config.LST
    t0      = config.tnow
    n_steps = int(24.0 / _STEP_H) + 1

    windows:  list[tuple[float, float]] = []
    in_window = False
    t_start   = 0.0

    for i in range(n_steps):
        t   = t0 + i * _STEP_H
        lst = (lst0 + i * _STEP_H * _SIDEREAL_RATE) % 24.0
        alt, az = _altaz(ra, dec, lat, lst)

        if alt > _horizon_limit(alts, az):
            if not in_window:
                in_window = True
                t_start   = t
        else:
            if in_window:
                in_window = False
                if (t - t_start) * 60.0 >= min_window_minutes:
                    windows.append((t_start, t))

    # Close any window still open at the end of the 24-hour sweep
    if in_window:
        t_end = t0 + 24.0
        if (t_end - t_start) * 60.0 >= min_window_minutes:
            windows.append((t_start, t_end))

    return windows

###############################################################################
# POLAR_MATH
###############################################################################



import math
from typing import Callable, Optional

Vec3 = list[float]

# Newton-Raphson controls for PASolve.  EPS is the finite-difference step for
# the numerical gradient, EPSSOLN the convergence threshold on cos(angle).
# Root finding for PASolve.  The equation Cosang(phi) == cos(HA separation)
# has FOUR roots in [0, 2*pi) — two genuinely different axes, each paired with
# its antipode.  The original code ran a single Newton-Raphson from phi = 0,
# which lands on the right root only while the misalignment is small; past
# about 15 degrees of altitude error it falls into a neighbouring basin and
# reports an axis tens of degrees from the pole.  So scan for every root, then
# choose between them (see _select_axis).
_SCAN_STEPS     = 720        # 0.5 degree steps — fine enough to bracket all four
_BISECT_ITER    = 80         # runs to machine precision; a bracket cannot diverge
_ROOT_TOL       = 1.0e-9     # |Cosang - target| accepted as a genuine root
# A root whose rotation reproduces image 2 from image 1 is exact to float
# noise; its antipodal twin is out by the better part of a degree at least.
_ROTATION_TOL   = 1.0e-4     # degrees

# Beyond this much misalignment the "nearest the pole" tie-break can prefer a
# rival root that happens to sit closer to the pole than the mount's true axis,
# and the answer is then wrong rather than merely imprecise.  Measured over
# random geometries with images between declination 30 and 70: exact in 3500
# out of 3500 cases below 15 degrees, 1.6% wrong by 20-25 degrees, 6% by 30.
#
# This is a conservative floor across that band, kept for the tests.  Where
# the declination is known, measurable_misalignment_deg gives the real limit:
# it rises steeply away from the pole, to some 40 degrees at declination 40.
PA_RELIABLE_DEG = 15.0

# The two images must actually be somewhere different.  Command a declination
# of 90 and the mount points at its own axis, where changing the hour angle
# moves it not at all: both images land on the same spot, and the pair carries
# no geometry to solve.  Left unchecked that is not an error but something
# worse -- coincident images return the SOUTHERN pole, and images an arcsecond
# apart return exactly +90, both perfectly plausible and both meaningless.
_MIN_IMAGE_SEP_DEG = 0.1

# BruteRotationSearch window and refinement steps, in degrees.  The window is
# deliberately larger than any mount should need: running off the edge silently
# corrupts both axes (see BruteRotationSearch), so the cost of a wide window is
# a little arithmetic and the cost of a narrow one is a wrong answer.
_SEARCH_ALT_DEG = 30.0
_SEARCH_AZ_DEG  = 60.0
_SEARCH_COARSE  = 0.5
_SEARCH_MEDIUM  = 0.05
_SEARCH_FINE    = 10 / 3600


# ── Vector helpers ───────────────────────────────────────────────────────────

def VfromAltAz(Alt: float, Az: float) -> Vec3:
    """Unit vector in the direction of Alt/Az (degrees)."""
    Altr = Alt * math.pi / 180.0
    Azr  = Az * math.pi / 180.0
    return [math.cos(Altr) * math.sin(Azr),
            math.cos(Altr) * math.cos(Azr),
            math.sin(Altr)]


def VecToAltAz(V: Vec3) -> tuple[float, float]:
    """Alt/Az (degrees) from a unit vector.  Az is returned in -180..180."""
    Alt = math.asin(V[2]) * 180 / math.pi
    Az  = math.atan2(V[0], V[1]) * 180 / math.pi
    return Alt, Az


def VAltAzRotate(V: Vec3, theta: float, phi: float) -> Vec3:
    """Rotate V by phi counter-clockwise about Z, then theta clockwise about X.

    This convention takes the telescope axis back to the pole given the
    axis's Alt/Az offset from it.
    """
    thetar = theta * math.pi / 180.0
    phir   = phi * math.pi / 180.0

    V1 = [math.cos(phir) * V[0] - math.sin(phir) * V[1],
          math.sin(phir) * V[0] + math.cos(phir) * V[1],
          V[2]]
    return [V1[0],
            math.cos(thetar) * V1[1] + math.sin(thetar) * V1[2],
            -math.sin(thetar) * V1[1] + math.cos(thetar) * V1[2]]


def VSub(V1: Vec3, V2: Vec3) -> Vec3:
    return [V1[0] - V2[0], V1[1] - V2[1], V1[2] - V2[2]]


def VDot(V1: Vec3, V2: Vec3) -> float:
    return V1[0] * V2[0] + V1[1] * V2[1] + V1[2] * V2[2]


def UVec(V: Vec3) -> Vec3:
    """Unit vector in the same direction as V."""
    norm = math.sqrt(VDot(V, V))
    return [element / norm for element in V]


def VCross(V1: Vec3, V2: Vec3) -> Vec3:
    return [V1[1] * V2[2] - V1[2] * V2[1],
            V1[2] * V2[0] - V1[0] * V2[2],
            V1[0] * V2[1] - V1[1] * V2[0]]


def VGCC(SZ: float, CZ: float, SA: float, CA: float, phi: float) -> Vec3:
    """Point at parameter *phi* on the great circle defined by SZ/CZ/SA/CA.

    The unit circle in the y-z plane, [0, sin(phi), cos(phi)], rotated first
    about y so the transformed x-axis matches the height of DVA, then about z
    to align it with DVA.
    """
    return [-SZ * CA * math.cos(phi) - SA * math.sin(phi),
            -SZ * SA * math.cos(phi) + CA * math.sin(phi),
            CZ * math.cos(phi)]


def Cosang(SZ: float, CZ: float, SA: float, CA: float, phi: float,
           V1: Vec3, V2: Vec3) -> float:
    """Cos of the angle subtended at the candidate polar axis by V1 and V2."""
    gcc = VGCC(SZ, CZ, SA, CA, phi)
    a1  = UVec(VCross(gcc, V1))
    a2  = UVec(VCross(gcc, V2))
    return VDot(a1, a2)


# ── Alt/Az conversion and rotation search ───────────────────────────────────

def AltAzfromHADECLat(HA: float, Dec: float, lat: float) -> tuple[float, float]:
    """Alt/Az from hour angle (hours), declination and latitude (degrees).

    The self-contained counterpart to the TheSkyX round-trip used elsewhere;
    needed here so the rotation search does not have to talk to the mount.
    """
    HAr  = HA * math.pi / 12.0
    Decr = Dec * math.pi / 180.0
    latr = lat * math.pi / 180.0
    Altr = math.asin(math.sin(Decr) * math.sin(latr)
                     + math.cos(Decr) * math.cos(latr) * math.cos(HAr))
    Azr  = math.atan2(-math.cos(Decr) * math.cos(latr) * math.sin(HAr),
                      math.sin(Decr) - math.sin(latr) * math.sin(Altr))
    return Altr * 180.0 / math.pi, Azr * 180.0 / math.pi


def RotateAltAz(Alt: float, Az: float,
                theta: float, phi: float) -> tuple[float, float]:
    """Alt/Az after rotating by theta and phi."""
    return VecToAltAz(VAltAzRotate(VfromAltAz(Alt, Az), theta, phi))


def RotationSearch(V: Vec3, VTarget: Vec3,
                   tmid: float, trange: float, tinc: float,
                   pmid: float, prange: float, pinc: float) -> tuple[float, float]:
    """Grid search for the (theta, phi) rotation carrying V onto VTarget."""
    tsoln  = tmid
    psoln  = pmid
    solmax = VDot(VTarget, VAltAzRotate(V, tsoln, psoln))

    t = tmid - trange
    while t < tmid + trange:
        p = pmid - prange
        while p < pmid + prange:
            sol = VDot(VTarget, VAltAzRotate(V, t, p))
            if sol > solmax:
                solmax = sol
                tsoln  = t
                psoln  = p
            p += pinc
        t += tinc
    return tsoln, psoln


def BruteRotationSearch(Alt: float, Az: float,
                        AltTarget: float, AzTarget: float
                        ) -> tuple[float, float, bool]:
    """Find the mount rotation carrying Alt/Az onto AltTarget/AzTarget.

    Returns (theta, phi, saturated) in degrees, theta in altitude and phi in
    azimuth.  *saturated* is True when the best fit sits on the edge of the
    search window, meaning the real rotation is larger than the window and
    both figures should be read as "at least this much, in this direction".

    The window matters more than it looks.  The two axes are not independent:
    when one of them hits the edge the search buys back some of the shortfall
    by overstating the other, so a single capped axis corrupts *both* readings.
    At the original 10/25 degree window a true -14 altitude error reported
    -10.2 altitude and +8.05 azimuth, with the azimuth wrong by a factor of
    over two.  Hence the wider window here, and hence reporting the cap.

    The grid is refined in stages rather than swept at final resolution: the
    objective is a dot product with one broad maximum, so a coarse pass locates
    it safely and the fine passes need only cover a few grid cells.
    """
    V       = VfromAltAz(Alt, Az)
    VTarget = VfromAltAz(AltTarget, AzTarget)

    trange, prange = _SEARCH_ALT_DEG, _SEARCH_AZ_DEG

    # (half-width in altitude, half-width in azimuth, step) per pass.
    tsoln = psoln = 0.0
    schedule = ((trange, prange, _SEARCH_COARSE),
                (_SEARCH_COARSE * 2, _SEARCH_COARSE * 2, _SEARCH_MEDIUM),
                (_SEARCH_MEDIUM * 2, _SEARCH_MEDIUM * 2, _SEARCH_FINE))
    for th, ph, step in schedule:
        tsoln, psoln = RotationSearch(V, VTarget, tsoln, th, step,
                                      psoln, ph, step)

    saturated = (abs(tsoln) >= trange - _SEARCH_COARSE
                 or abs(psoln) >= prange - _SEARCH_COARSE)
    return tsoln, psoln, saturated


def _Rodrigues(V: Vec3, P: Vec3, ang: float) -> Vec3:
    """Rotate *V* about unit axis *P* by *ang* radians."""
    c, s = math.cos(ang), math.sin(ang)
    cross = [P[1] * V[2] - P[2] * V[1],
             P[2] * V[0] - P[0] * V[2],
             P[0] * V[1] - P[1] * V[0]]
    dot = VDot(P, V)
    return [V[i] * c + cross[i] * s + P[i] * dot * (1 - c) for i in range(3)]


def _PhiRoots(SZ: float, CZ: float, SA: float, CA: float,
              V1: Vec3, V2: Vec3, CosHASep: float) -> list[float]:
    """Every phi in [0, 2*pi) where the subtended angle matches the mount's.

    Scans for sign changes, bisects each bracket, then keeps only those that
    settle on an actual zero.  Cosang is a dot product of unit vectors, so it
    is bounded but not continuous: it flips sign where the candidate axis meets
    V1 or V2.  Bisecting such a jump converges on a point where the function is
    nowhere near zero, so verifying the residual rejects it without needing to
    guess at a step-size threshold.
    """
    def f(phi: float) -> float | None:
        try:
            return Cosang(SZ, CZ, SA, CA, phi, V1, V2) - CosHASep
        except (ValueError, ZeroDivisionError):
            return None          # candidate axis is degenerate at this phi

    roots: list[float] = []
    prev: tuple[float, float] | None = None
    for i in range(_SCAN_STEPS + 1):
        phi = 2 * math.pi * i / _SCAN_STEPS
        val = f(phi)
        if val is None:
            prev = None
            continue
        if prev is not None and (val < 0) != (prev[1] < 0):
            lo, hi = prev[0], phi
            f_lo = prev[1]
            for _ in range(_BISECT_ITER):
                mid = (lo + hi) / 2.0
                f_mid = f(mid)
                if f_mid is None:
                    break
                if (f_mid < 0) == (f_lo < 0):
                    lo, f_lo = mid, f_mid
                else:
                    hi = mid
            root = (lo + hi) / 2.0
            f_root = f(root)
            if f_root is not None and abs(f_root) <= _ROOT_TOL:
                roots.append(root)
        prev = (phi, val)
    return roots


def _SelectAxis(roots: list[float], SZ: float, CZ: float, SA: float, CA: float,
                V1: Vec3, V2: Vec3, HASep: float) -> Vec3:
    """Pick the polar axis from the candidate roots.

    Two tests, in order:

    1.  Handedness.  The mount turned by the reported hour-angle separation
        about its axis, so rotating image 1 about a true axis by that angle
        must land on image 2.  An antipodal twin turns the other way and
        misses, which removes one root from each pair.

    2.  Distance from the pole.  Of the two distinct axes left, the mount's is
        the one near the celestial pole — we are aligning a telescope, not
        solving for an arbitrary rotation.  Taking the nearest pole rather
        than assuming the northern one keeps this correct below the equator.

    Test 2 is a prior, not a deduction, and it fails once the mount is so far
    out that the rival root lands nearer the pole than the truth — see
    PA_RELIABLE_DEG.  Both survivors fit the two images exactly, so nothing in
    the data can separate them; only the expectation of being roughly polar
    aligned can.
    """
    best: Vec3 | None = None
    best_sep = -1.0
    for phi in roots:
        PA = VGCC(SZ, CZ, SA, CA, phi)
        landed = _Rodrigues(V1, PA, -HASep)
        resid = math.degrees(math.acos(max(-1.0, min(1.0, VDot(landed, V2)))))
        if resid > _ROTATION_TOL:
            continue
        pole_sep = abs(PA[2])        # larger = closer to a pole
        if pole_sep > best_sep:
            best, best_sep = PA, pole_sep
    if best is None:
        raise ArithmeticError(
            "Polar axis solve found no consistent solution \u2014 the two "
            "images need a clear separation in hour angle, but not close to "
            "12 hours, where a half turn leaves the axis undetermined."
        )
    return best


def PASolve(RA1: float, DEC1: float, LST1: float, THA1: float,
            RA2: float, DEC2: float, LST2: float, THA2: float) -> tuple[float, float]:
    """Recover the polar axis from two plate-solved images.

    RA/DEC are the plate-solved JNow coordinates, LST the local sidereal time
    recorded with each image, and THA the hour angle reported by the mount.
    Returns (hour angle, declination) of the polar axis, in hours and degrees.

    The two image directions lie on a circle about the true polar axis, so the
    axis sits on the great circle perpendicular to their difference vector.
    Walking that circle, the angle the two images subtend at the candidate axis
    matches the mount's reported hour-angle separation at four places;
    _SelectAxis decides which of those is the mount's axis.

    Raises ArithmeticError on degenerate input (typically too small a
    separation in hour angle).
    """
    # Hour angles and declinations in radians.
    HA1 = (LST1 - RA1) / 24.0 * 2 * math.pi
    HA2 = (LST2 - RA2) / 24.0 * 2 * math.pi
    D1  = DEC1 * math.pi / 180.0
    D2  = DEC2 * math.pi / 180.0

    # Image directions, Z to the pole, Y on the meridian.
    V1 = [math.cos(D1) * math.sin(HA1), math.cos(D1) * math.cos(HA1), math.sin(D1)]
    V2 = [math.cos(D2) * math.sin(HA2), math.cos(D2) * math.cos(HA2), math.sin(D2)]

    sep = math.degrees(math.acos(max(-1.0, min(1.0, VDot(V1, V2)))))
    if sep < _MIN_IMAGE_SEP_DEG:
        raise ArithmeticError(
            f"The two images are only {sep * 60:.1f} arcmin apart on the sky, "
            "which is too little to solve from.  This usually means a "
            "declination so close to the pole that the hour angle barely "
            "moves the telescope."
        )

    # The pole is equidistant from both images (pure rotation about the mount
    # axis), so it lies on the great circle perpendicular to V2 - V1.
    DVA = UVec(VSub(V2, V1))
    SZ  = DVA[2]
    CZ  = math.sqrt(1 - SZ * SZ)
    AZD = math.atan2(DVA[1], DVA[0])
    SA  = math.sin(AZD)
    CA  = math.cos(AZD)

    HASep    = (THA2 - THA1) * math.pi / 12.0
    CosHASep = math.cos(HASep)

    roots = _PhiRoots(SZ, CZ, SA, CA, V1, V2, CosHASep)
    PA    = _SelectAxis(roots, SZ, CZ, SA, CA, V1, V2, HASep)

    PADEC = math.asin(PA[2]) * 180 / math.pi
    PAHA  = math.atan2(PA[0], PA[1]) * 12 / math.pi
    return PAHA, PADEC


# ── Screening a chosen pair of alignment points ─────────────────────────────

# Both adjustments tilt the polar axis, and how well their separate effects
# can be told apart is set by the star's NORTHWARD component, cos(alt)*cos(az).
# That vanishes on the whole vertical circle through due east and west, and
# anywhere on it the two bolts push the star along the SAME LINE: measured,
# the angle between their pushes is 0 degrees due east and 180 due west at any
# altitude, against 90 degrees due north.  Only the combined effect can then be
# seen, and splitting it between the two bolts is guesswork.
#
# The ends of that circle are special, and they are the same case on different
# axes -- a star on a bolt's own rotation axis does not move when that bolt
# turns.  Overhead the star sits on the azimuth bolt's axis, so that bolt
# barely moves it (measured 0.002, against 1.0 for the altitude bolt).  On the
# eastern or western horizon it sits on the altitude bolt's axis instead, and
# that is the weak one (0.34 at altitude 20, against 0.94).  Note that the
# weak bolt is not what does the damage: due east at altitude 70 both bolts
# are strong, 0.94 and 0.34, and the pair is degenerate all the same because
# the pushes are parallel.
#
# Measured against BruteRotationSearch over the whole sky, the error in the
# reported correction is about 0.7 / |cos(alt) cos(az)| times the error in the
# image position, to within a factor of about 1.5.
_CORR_AMP_K    = 0.7
_CORR_AMP_WARN = 5.0     # a 10" solve becomes a ~1' error in the correction
# Past this the two corrections are so nearly parallel that quoting a figure
# would imply a precision the answer does not have -- and at the zenith
# exactly, the amplification is infinite.
_CORR_AMP_HOPELESS = 200.0
# Taking the same two points in the other order costs nothing, so it is worth
# saying when it would help this much.  Set high so that the suggestion only
# appears when the gain is real: the pair is not faulty, merely back to front.
_SWAP_GAIN = 2.0
# A round nominal figure for how well an image's position is known, used to
# turn the amplification factors below into arcminutes the user can judge.  It
# is a stand-in, not a measurement: the plate solve itself usually does better
# than this, but flexure between the two points, differential refraction and
# seeing all add to it, and those do not shrink with the number of stars
# matched.  ImageLink reports ImageLinkResults.solutionRMS if a measured
# figure is ever wanted, though its units are not obvious from the property
# alone.  The screening thresholds are ratios, so they do not depend on this.
_NOMINAL_SOLVE_ARCSEC = 10.0

_MIN_ALT_DEG   = 20.0    # refraction and seeing below this
# Clearance above a custom horizon below which a point is worth a warning.
# Trees and rooftops are not sharp edges: seeing degrades, and the horizon
# itself is only sampled every degree or so.
_MIN_CLEARANCE_DEG = 5.0
_MIN_HA_SEP_H  = 2.0     # see screen_geometry
_GOOD_HA_SEP_H = 4.0     # what the advice steers towards
# Near the celestial equator the two candidate axes sit at nearly equal
# distances from the pole, so choosing the nearer stops being reliable.
# Measured, with 10" of image error and four hours of separation: declination
# 0 gives a median 16' error and picks the wrong root 79% of the time, dec 2
# gives 3.9' and 41%, dec 5 gives 1.6' and none, dec 10 gives 0.86', against
# 0.26' at dec 60.  The floor sits above the point where wrong roots stop, so
# that the warning covers the merely-poor as well as the broken.
_MIN_DEC_DEG   = 15.0
# The other end of the same axis: so close to the pole that the misalignment
# being measured is comparable with the whole distance from the images to the
# pole.  The declination setting stops at 80, so this is a backstop for
# callers that do not go through the dialog rather than something a user can
# reach.  See measurable_misalignment_deg.
_MIN_REACH_DEG = 5.0
# Exactly 12 hours apart is a half turn, where every axis on the bisecting
# circle fits both images equally well and the solve has nothing to choose
# between them.  Only reachable with hour angles of opposite sign, so the
# meridian-flip warning always fires alongside this.
_HALF_TURN_TOL_H = 0.5


def correction_amplification(alt: float, az: float) -> float:
    """How much an error in the image position is magnified in the correction."""
    vy = abs(math.cos(math.radians(alt)) * math.cos(math.radians(az)))
    return float("inf") if vy < 1e-9 else _CORR_AMP_K / vy


def axis_precision_arcmin(sep_hours: float,
                          solve_arcsec: float = _NOMINAL_SOLVE_ARCSEC) -> float:
    """Roughly how well the polar axis can be found, in arcminutes.

    The solve gets its leverage from the hour-angle separation, and the error
    falls off as one over it.  Declination barely enters: measured with 10" of
    image error, the axis came back to 0.33' at declination 30 and 0.24' at
    declination 80, both at four hours apart, so one figure in hours covers
    the whole usable sky.  Calibrated on the same runs -- 10 arcsec and four
    hours give about a quarter of an arcminute.
    """
    if sep_hours <= 0:
        return float("inf")
    return 1.05 * (solve_arcsec / _NOMINAL_SOLVE_ARCSEC) / sep_hours


def measurable_misalignment_deg(dec: float) -> float:
    """The largest misalignment this declination can still resolve, in degrees.

    Past this the nearest-the-pole choice between the two surviving roots
    starts picking the wrong one, and the answer is then wrong by roughly a
    half turn rather than merely imprecise.

    It is set by how far the images themselves are from the pole, not by the
    arc between them: measured as the first misalignment producing any wrong
    root, declination 40 held to 40 degrees, 60 to 30, 70 to 20, 80 to 10 --
    near enough 90 - |dec| at separations of one to four hours, and somewhat
    less at eight.  Since the declination setting stops at 80 this never falls
    below about 10 degrees, which is far more than any mount that has been
    roughly set up, so nothing is said about it unless it is reached.
    """
    return max(0.0, 90.0 - abs(dec))


def _lift_advice(ha: float, dec: float, lat: float,
                 horizon: Optional[Callable[[float], float]]) -> str:
    """How to raise a point that is too low, and by how much.

    Worked out rather than asserted, because the obvious rule is wrong away
    from the meridian.  At transit the highest declination is the one nearest
    the latitude, but five hours west of it a point at declination 60 sits
    lower than one at 70, so advising "nearer your latitude" would send the
    user the wrong way.  Trying both directions and quoting the gain also
    handles a custom horizon, where the skyline itself changes with azimuth.
    """
    def clearance(d: float, h: float) -> float:
        alt, az = AltAzfromHADECLat(h, d, lat)
        return alt - (horizon(az % 360.0) if horizon is not None else 0.0)

    base = clearance(dec, ha)
    moves: list[str] = []

    if abs(ha) > 0.5:
        gain = clearance(dec, ha - math.copysign(1.0, ha)) - base
        if gain > 0.5:
            moves.append(f"bring the hour angle an hour nearer the meridian "
                         f"({gain:+.1f}\N{DEGREE SIGN})")

    for step in (5.0, -5.0):
        if abs(dec + step) > 85.0:
            continue
        gain = clearance(dec + step, ha) - base
        if gain > 0.5:
            moves.append(f"{'raise' if step > 0 else 'lower'} the declination "
                         f"by 5\N{DEGREE SIGN} ({gain:+.1f}\N{DEGREE SIGN})")
            break

    if not moves:
        return "Neither a smaller hour angle nor a shift in declination lifts "\
               "it; this part of the sky is not usable."
    return "To lift it, " + ", or ".join(moves) + "."


def _arc_str(arcmin: float) -> str:
    """Format an angle the way the eye reads it: seconds when small."""
    if arcmin < 2.0:
        return f"{arcmin * 60:.0f}\""
    if arcmin < 60.0:
        return f"{arcmin:.1f}'"
    return f"{arcmin / 60.0:.1f}\N{DEGREE SIGN}"


def screen_geometry(lat: float, dec: float, ha1: float, ha2: float,
                    solve_arcsec: float = _NOMINAL_SOLVE_ARCSEC,
                    horizon: Optional[Callable[[float], float]] = None
                    ) -> list[tuple[str, str]]:
    """Judge a chosen pair of alignment points.

    Returns (level, message) pairs.  When the pair is sound that is a single
    ("good", ...) line saying what it will achieve; otherwise it is one line
    per fault, each saying how to fix it, at level "error" for something that
    cannot work at all and "warn" for something that will spoil the result.

    Five things matter, and only five.  Both points must be visible; the two
    hour angles must be on the same side of the meridian, or the mount flips
    between the images and takes its flexure with it; they must be far enough
    apart to give the solve some leverage; the second point must not be
    overhead or due east or west, where the two corrections stop being
    separable; and the declination must not be near the celestial equator,
    where the choice between the two candidate axes stops being reliable.
    """
    faults: list[tuple[str, str]] = []
    sep = abs(ha2 - ha1)

    alt1, az1 = AltAzfromHADECLat(ha1, dec, lat)
    alt2, az2 = AltAzfromHADECLat(ha2, dec, lat)
    az1 %= 360.0
    az2 %= 360.0

    amp  = correction_amplification(alt2, az2)
    axis = axis_precision_arcmin(sep, solve_arcsec)

    # 1.  Visible.  Against the real skyline where one is available, not the
    #     ideal one: a point 30 degrees up is still useless behind a tree.
    for label, alt, az in (("first", alt1, az1), ("second", alt2, az2)):
        limit = horizon(az) if horizon is not None else 0.0
        clearance = alt - limit
        fix = _lift_advice(ha1 if label == "first" else ha2, dec, lat, horizon)
        if clearance < 0:
            against = (f"your {limit:.0f}\N{DEGREE SIGN} skyline at azimuth "
                       f"{az:.0f}\N{DEGREE SIGN}" if limit > 0 else
                       "the horizon")
            faults.append(("error",
                f"The {label} point is below {against} "
                f"(altitude {alt:.0f}\N{DEGREE SIGN}).  {fix}"))
        elif horizon is not None and clearance < _MIN_CLEARANCE_DEG:
            faults.append(("warn",
                f"The {label} point clears your skyline by only "
                f"{clearance:.1f}\N{DEGREE SIGN} (altitude {alt:.0f}"
                f"\N{DEGREE SIGN} against {limit:.0f}\N{DEGREE SIGN} at "
                f"azimuth {az:.0f}\N{DEGREE SIGN}).  {fix}"))
        elif alt < _MIN_ALT_DEG:
            faults.append(("warn",
                f"The {label} point is only {alt:.0f}\N{DEGREE SIGN} up, "
                f"where refraction and poor seeing will spoil the solve.  "
                f"{fix}"))

    # 2.  Same side of the pier.  Nothing in the solve allows for a flip, and
    #     the change in flexure across one dwarfs anything the geometry wins.
    if ha1 * ha2 < 0:
        faults.append(("warn",
            f"Hour angles {ha1:+.1f} h and {ha2:+.1f} h straddle the "
            "meridian, so the mount will flip between the two images and its "
            "flexure with it, which the solve reads as misalignment.  Use "
            "two hour angles of the same sign."))
    if abs(sep - 12.0) < _HALF_TURN_TOL_H:
        faults.append(("error",
            f"{sep:.1f} h apart is a half turn, where every axis on the "
            "bisecting circle fits both images equally well and the polar "
            "axis cannot be found at all.  Bring the hour angles to the same "
            "side of the meridian."))

    # 3.  Far enough apart, which is purely a matter of hour angle.
    elif sep < _MIN_HA_SEP_H:
        against = axis_precision_arcmin(_GOOD_HA_SEP_H, solve_arcsec)
        faults.append(("warn",
            f"Only {sep:.1f} h apart: {solve_arcsec:.0f}\" of error would put "
            f"the polar axis about {_arc_str(axis)} out, against "
            f"{_arc_str(against)} at {_GOOD_HA_SEP_H:.0f} h.  Separate the "
            "hour angles by three to five hours, on the same side of the "
            "meridian."))

    # 4.  The second point clear of the zenith and of due east and west.  Only
    #     the second is screened: the first reaches PASolve as an equatorial
    #     direction and nothing else, while the correction is always computed
    #     where the mount stands while it is adjusted, which is the second.
    #     Measured with the first point exactly overhead, the axis came back
    #     to 0.12' -- better than a well-placed pair.
    if alt2 >= 0 and amp > _CORR_AMP_WARN:
        if math.cos(math.radians(alt2)) < abs(math.cos(math.radians(az2))):
            why = (f"nearly overhead (altitude {alt2:.0f}\N{DEGREE SIGN}), so "
                   "the azimuth adjustment barely moves it")
            fix = (f"Move the declination away from your latitude "
                   f"({lat:.0f}\N{DEGREE SIGN}), or the hour angle away from "
                   "the meridian.")
        else:
            why = (f"close to due east or west (azimuth {az2:.0f}"
                   "\N{DEGREE SIGN}), where both bolts push it along the "
                   "same line")
            fix = "Use a declination nearer the pole."
        if amp > _CORR_AMP_HOPELESS:
            effect = ("That leaves the altitude and azimuth adjustments all "
                      "but indistinguishable, so the correction reported "
                      "would be meaningless.")
        else:
            effect = (f"That multiplies the image error by about {amp:.0f}, "
                      f"so {solve_arcsec:.0f}\" becomes roughly "
                      f"{_arc_str(amp * solve_arcsec / 60.0)} of uncertainty "
                      "in the corrections you adjust to.")
        faults.append(("warn", f"The second point is {why}.  {effect}  {fix}"))

    # 4b. Which of the two points is visited second.  The pair is sound either
    #     way round -- the axis precision depends only on the separation --
    #     but the correction is read where the mount ends up, so ending low
    #     can be worth several times ending high.  Measured at declination 60
    #     from this site: -1 h then -5 h leaves the correction uncertain by
    #     16", the same two hour angles the other way round by 43".
    elif alt1 >= 0 and alt2 >= 0:
        swapped = correction_amplification(alt1, az1)
        if amp > _SWAP_GAIN * swapped:
            faults.append(("warn",
                f"The mount finishes at altitude {alt2:.0f}\N{DEGREE SIGN}, "
                "where the altitude and azimuth adjustments are harder to "
                f"tell apart (\N{MULTIPLICATION SIGN}{amp:.1f}).  Taking the "
                f"same two points the other way round \u2014 {ha2:+.1f} h "
                f"first, then {ha1:+.1f} h \u2014 would end lower and cut the "
                f"uncertainty in the corrections from "
                f"{_arc_str(amp * solve_arcsec / 60.0)} to "
                f"{_arc_str(swapped * solve_arcsec / 60.0)}.  Work away from "
                "the meridian, not towards it."))

    # 5.  Clear of the celestial equator -- and of the pole at the far end.
    reach = measurable_misalignment_deg(dec)
    if reach < _MIN_REACH_DEG:
        faults.append(("warn",
            f"Declination {dec:+.1f}\N{DEGREE SIGN} is only {reach:.1f}"
            "\N{DEGREE SIGN} from the pole, and this method cannot measure a "
            "misalignment larger than that.  Use a declination further from "
            "the pole."))
    # 5.  Clear of the celestial equator.
    if abs(dec) < _MIN_DEC_DEG:
        faults.append(("warn",
            f"Declination {dec:+.0f}\N{DEGREE SIGN} is too near the celestial "
            "equator, where the solve cannot reliably tell the true axis from "
            f"its mirror image.  Use a declination beyond "
            f"{_MIN_DEC_DEG:.0f}\N{DEGREE SIGN}, and preferably well beyond."))

    if faults:
        return faults

    return [("good",
        f"Points good.  {sep:.1f} h apart at declination {dec:+.0f}"
        f"\N{DEGREE SIGN}: {solve_arcsec:.0f}\" of plate-solve error or "
        f"flexure would put the polar axis about {_arc_str(axis)} out.")]


# ── Display formatting ──────────────────────────────────────────────────────

def DegFormat(angle: float) -> str:
    """Format degrees as  12° 34' 56"  (rounded to the nearest arcsecond)."""
    degree_sign = '\N{DEGREE SIGN}'
    angsign = ""
    if angle < 0:
        angsign = "-"
        angle = -angle

    # The half-unit offsets carry the rounding up through each field.
    deg = int(angle + 0.5 / 3600)
    angle -= deg
    angle *= 60
    minutes = int(angle + 0.5 / 60)
    angle -= minutes
    angle *= 60
    seconds = int(angle + 0.5)
    return f"{angsign}{deg}{degree_sign} {minutes}' {seconds}\""


def HourFormat(angle: float) -> str:
    """Format an hour angle as  3h 45' 12"  (rounded to the nearest second)."""
    strsign = ""
    if angle <= 0:
        angle = -angle
        strsign = "-"

    deg = int(angle + 0.5 / 3600)
    angle -= deg
    angle *= 60
    minutes = int(angle + 0.5 / 60)
    angle -= minutes
    angle *= 60
    seconds = int(angle + 0.5)
    return f"{strsign}{deg}h {minutes}' {seconds}\""

###############################################################################
# POLAR_ALIGN
###############################################################################



import math
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


# TheSkyX's TCP listener.  takeimage uses a raw socket rather than TSXSendTry
# because the exposure can outlast the shared helper's timeout.
_TSX_HOST = '127.0.0.1'
_TSX_PORT = 3040
_TSX_BUFFER = 1024


class PolarAlignError(RuntimeError):
    """Raised when the procedure cannot continue (comms, solve or hardware).

    *code* is TheSkyX's numeric error code where one was given, so callers can
    tell apart failures that mean different things — chiefly 651, too few
    stars, which during the adjustment loop means the mount is moving rather
    than anything being wrong.
    """

    def __init__(self, message: str, code: str = ""):
        super().__init__(message)
        self.code = code


# TheSkyX error codes worth naming, either because its own wording runs to a
# paragraph or because we can be more specific about what it means here.
TOO_FEW_STARS = "651"

_FRIENDLY_ERRORS = {
    TOO_FEW_STARS: "not enough stars in the image",
    "655": "no astrometric solution found",
    "206": "TheSkyX could not carry out the command",
    "250": "TheSkyX could not find the object",
    "709": "the image file no longer exists",
    "219": "TheSkyX is still busy with an earlier command",
    "303": "TheSkyX did not recognise the command",
}

_ERROR_CODE = re.compile(r"Error\s*=\s*(\d+)")


def _tidy_error(text: str) -> tuple[str, str]:
    """Reduce TheSkyX's error text to one line, plus its code.

    Two things get stripped.  The JavaScript exception class ("TypeError:")
    is an artefact of how the script is run and says nothing about what went
    wrong.  And several failures are followed by a paragraph of advice aimed
    at somebody sitting in front of TheSkyX — three ways to adjust Source
    Extraction, say — which is noise in a log that scrolls past during a run.
    """
    raw  = (text or "").strip()
    match = _ERROR_CODE.search(raw)
    code  = match.group(1) if match else ""

    friendly = _FRIENDLY_ERRORS.get(code)
    if friendly:
        head = friendly
    else:
        head = raw.splitlines()[0] if raw else ""
        head = re.sub(r"^\s*\w*(?:Error|Exception)\s*:\s*", "", head)
        head = head.split("Possible solutions")[0].strip().rstrip(".").strip()
        head = _ERROR_CODE.sub("", head)
        # Removing the code can leave "NG (reason. )" behind.
        head = re.sub(r"\(\s*\)", "", head)
        head = re.sub(r"\s+", " ", head).strip(" .")
        head = re.sub(r"\s+\)", ")", head).replace("( ", "(")

    if not head:
        head = "TheSkyX reported a failure"
    return (f"{head} (error {code})" if code else head), code


@dataclass
class CameraState:
    """Camera settings captured at start so they can be put back afterwards."""
    binning:    int = 1
    subframe:   int = 0
    left:       int = 0
    right:      int = 0
    top:        int = 0
    bottom:     int = 0
    filter_idx: Optional[int] = None


# ── Checked TheSkyX calls ───────────────────────────────────────────────────

def _tsx_status(js: str) -> str:
    """Run *js* and return "ok", or whatever TheSkyX complained about.

    TSXSendTry already wraps the script in try/catch and assigns any exception
    to `out`, so appending `out = 'ok'` makes success tell itself apart: any
    other reply came from the catch, or from TheSkyX declining to run the
    script at all.  Without a sentinel there is nothing to test, because a
    script that assigns nothing returns the value of its last expression,
    which is often a plausible-looking number.
    """
    try:
        data = TSXSendTry(js + " out = 'ok';")
    except Exception as exc:          # socket trouble, restart attempts, …
        return f"no reply from TheSkyX ({exc})"
    if not data:
        return "TheSkyX sent no reply"

    status = data[0].strip()
    if status == "ok":
        return "ok"

    # TheSkyX puts its own error after the script's output, and sometimes says
    # nothing useful in the output itself \u2014 a refused command can come back
    # as a bare "NG" with the reason only in the trailer.
    trailer = data[-1].strip() if len(data) > 1 else ""
    if trailer.startswith("No error"):
        trailer = ""
    if status and trailer:
        return f"{status} ({trailer})"
    return status or trailer or "TheSkyX sent no reply"


def _tsx_explain(status: str) -> str:
    """Turn TheSkyX's terser refusals into something actionable."""
    if ("Another script" in status or "still in progress" in status
            or "Error = 219" in status):
        return (f"{_tidy_error(status)[0]}  TheSkyX is busy with another "
                "script \u2014 close any running script or Tool, and check "
                "nothing else is driving it.")
    return _tidy_error(status)[0]


def _tsx_check(js: str, what: str) -> None:
    """Run *js*, raising PolarAlignError if TheSkyX did not accept it."""
    status = _tsx_status(js)
    if status != "ok":
        raise PolarAlignError(f"{what} failed: {_tsx_explain(status)}")


def _tsx_best_effort(js: str, what: str) -> None:
    """Run *js*, warning rather than raising if it is refused.

    For steps whose failure is survivable, or benign: unparking a mount that
    was never parked is reported as a failure by some drivers.
    """
    status = _tsx_status(js)
    if status != "ok":
        output(logtime() + f"{what} did not succeed: {_tsx_explain(status)}",
               WARNING)


# ── Device helpers ──────────────────────────────────────────────────────────

# The Filter Wheel Simulator reports 125 positions; connectFW() in
# filter_wheel.py caps it at 7 and so do we, or reading the names becomes 125
# round trips to TheSkyX.
_SIMULATOR_FILTERS = 7


def tsx_available(timeout: float = 2.0) -> bool:
    """Is TheSkyX listening and answering?

    A plain socket on purpose.  TSXSendTry treats a failed connection as
    TheSkyX having died mid-run: it emails, tries to restart it, and exits the
    process.  That is right during a run and quite wrong at startup, where not
    having TheSkyX open yet is ordinary.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((_TSX_HOST, _TSX_PORT))
            sock.send(b" /* Java Script */ out = 'ok';")
            return sock.recv(_TSX_BUFFER).decode(errors="replace").startswith("ok")
        finally:
            sock.close()
    except OSError:
        return False


def filter_count() -> int:
    """How many filters the wheel has, with the simulator capped."""
    slots = numberFilters()
    model = TSXSendTry("SelectedHardware.filterWheelModel")[0].strip()
    if model == "Filter Wheel Simulator":
        return min(slots, _SIMULATOR_FILTERS)
    return slots


def filter_names() -> list[str]:
    """The names of the filters in the wheel, or [] if there is no wheel.

    Uses filter_wheel's primitives, but not connectFW()'s validation: that
    rejects names beginning with "F" and names sharing a first letter, which
    are rules about @Focus3 sequence letters.  A wheel that breaks them is
    still perfectly usable for picking a plate-solving filter, so refusing it
    here would only hide filters this tool could use.
    """
    if TSXSendTry("ccdsoftCamera.filterWheelConnect();")[0].strip() != "0":
        return []
    names = []
    for idx in range(filter_count()):
        name = getFilterName(idx).strip()
        if name:
            names.append(name)
    return names


def connect_filterwheel() -> None:
    if TSXSendTry("ccdsoftCamera.filterWheelConnect();")[0] != "0":
        raise PolarAlignError("Could not connect the filter wheel.")


def select_filter(name: str) -> int:
    """Select *name* and return the filter index that was in use before."""
    previous = int(TSXSendTry("ccdsoftCamera.FilterIndexZeroBased")[0])
    for idx in range(filter_count()):
        if TSXSendTry(f"ccdsoftCamera.szFilterName({idx})")[0] == name:
            got = TSXSendTry(f"ccdsoftCamera.FilterIndexZeroBased = {idx};")
            if int(got[0]) != idx:
                raise PolarAlignError(f"Could not select filter {name!r}.")
            return previous
    raise PolarAlignError(f"Filter {name!r} not found in the wheel.")


def get_binning() -> int:
    return int(TSXSendTry("out = ccdsoftCamera.BinX;")[0])


def connect_camera() -> None:
    """Connect the camera, and confirm it really is connected.

    Some ccdsoftCamera properties are plain software settings that answer
    happily with no camera attached (SubframeLeft and friends), while others
    genuinely query the device and throw "no connection to the device,
    Error = 200" until it is connected.  Reading the second kind too early
    used to surface as an unrelated parse failure further down, so connect up
    front and check a device-backed property before relying on either kind.
    """
    data = TSXSendTry(
        "ccdsoftCamera.Connect();"
        "out = String(ccdsoftCamera.WidthInPixels);"
    )
    try:
        int(data[0])
    except (ValueError, IndexError):
        raise PolarAlignError(
            "Could not connect the camera in TheSkyX \u2014 check it is "
            "attached and switched on."
        )


def set_binning(binning: int) -> None:
    _tsx_check(f"ccdsoftCamera.BinX = {binning}; ccdsoftCamera.BinY = {binning};",
               f"Setting binning to {binning}x{binning}")


def get_subframe() -> tuple[int, int, int, int, int]:
    """Return (enabled, left, right, top, bottom)."""
    data = TSXSendTry(
        "l = ccdsoftCamera.SubframeLeft;"
        "r = ccdsoftCamera.SubframeRight;"
        "t = ccdsoftCamera.SubframeTop;"
        "b = ccdsoftCamera.SubframeBottom;"
        "f = ccdsoftCamera.Subframe;"
        "out = String(f) + '|' + String(l) + '|' + String(r) + '|'"
        "      + String(t) + '|' + String(b);"
    )
    return tuple(int(v) for v in data[:5])   # type: ignore[return-value]


def restore_subframe(state: CameraState) -> None:
    _tsx_check(
        f"ccdsoftCamera.SubframeLeft = {state.left};"
        f"ccdsoftCamera.SubframeRight = {state.right};"
        f"ccdsoftCamera.SubframeTop = {state.top};"
        f"ccdsoftCamera.SubframeBottom = {state.bottom};"
        f"ccdsoftCamera.Subframe = {state.subframe};",
        "Restoring the subframe")


def set_subframe(reduction: int) -> None:
    """Crop to the centre 1/2 or 1/4 of the frame to speed up plate solving.

    reduction == 1 disables the subframe.  Binning is forced to 1 first
    because TheSkyX specifies subframe corners in unbinned pixels.
    """
    if reduction == 1:
        _tsx_check("ccdsoftCamera.Subframe = 0;", "Clearing the subframe")
        return

    set_binning(1)
    data = TSXSendTry(
        "w = ccdsoftCamera.WidthInPixels;"
        "h = ccdsoftCamera.HeightInPixels;"
        "out = '|' + String(w) + '|' + String(h) + '|';"
    )
    try:
        w, h = int(data[1]), int(data[2])
    except (ValueError, IndexError):
        raise PolarAlignError(
            f"Could not read the camera frame size from TheSkyX: {data!r}"
        )

    if reduction == 2:
        left, right, top, bottom = w // 4, 3 * w // 4, h // 4, 3 * h // 4
    else:
        left, right = int(3 * w / 8), int(5 * w / 8)
        top, bottom = int(3 * h / 8), int(5 * h / 8)

    _tsx_check(
        f"ccdsoftCamera.SubframeLeft = {left};"
        f"ccdsoftCamera.SubframeRight = {right};"
        f"ccdsoftCamera.SubframeTop = {top};"
        f"ccdsoftCamera.SubframeBottom = {bottom};"
        "ccdsoftCamera.Subframe = 1;",
        "Setting the subframe")


def _last_image_path() -> str:
    """The file TheSkyX last saved an image to, or "" if it cannot say."""
    try:
        return TSXSendTry("out = String(ccdsoftCamera.LastImageFileName);")[0].strip()
    except Exception:
        return ""


def take_image(exposure: float, binning: int, reduction: int) -> str:
    """Take one autosaved light frame; return the file it was saved to.

    The path is returned, rather than leaving callers to ask TheSkyX for
    "the current image", because TheSkyX will happily keep handing out the
    last image it knows about.  Combined with plate_solve_results deleting
    each frame once solved, a skipped exposure would otherwise be solved
    again from a stale file, or from one that no longer exists.

    The script carries the /* Java Script */ marker and its reply is checked.
    Without the marker TheSkyX answers "Unknown command. Error = 303." and
    takes no image at all; because the reply used to be discarded, that
    failed instantly and silently and the run carried on with a stale frame.
    """
    set_subframe(reduction)
    previous = _last_image_path()

    message = (
        " /* Java Script */ try { "
        "ccdsoftCamera.Connect();"
        "ccdsoftCamera.Asynchronous = false;"
        f"ccdsoftCamera.ExposureTime = {exposure};"
        "ccdsoftCamera.AutoSaveOn = true;"
        "ccdsoftCamera.ImageReduction = 0;"
        "ccdsoftCamera.Frame = 1;"
        "ccdsoftCamera.Delay = 0;"
        f"ccdsoftCamera.BinX = {binning};"
        f"ccdsoftCamera.BinY = {binning};"
        "ccdsoftCamera.TakeImage();"
        "out = 'ok';"
        " } catch (e) { out = 'ERROR: ' + e; } "
    )

    # Raw socket: the exposure plus download can exceed TSXSendTry's timeout.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((_TSX_HOST, _TSX_PORT))
        sock.send(message.encode())
        sock.settimeout(exposure + 60)
        try:
            reply = sock.recv(_TSX_BUFFER).decode(errors="replace")
        except socket.error:
            raise PolarAlignError("Timed out waiting for the camera.")
    finally:
        sock.close()

    status = reply.split("|")[0].strip()
    if status != "ok":
        raise PolarAlignError(
            f"Could not take an image: {status or 'TheSkyX sent no reply'}"
        )

    path = _last_image_path()
    if not path:
        raise PolarAlignError(
            "TheSkyX did not report a saved image file \u2014 check that "
            "autosave is working."
        )
    if path == previous:
        raise PolarAlignError(
            "TheSkyX reported the same image file as last time "
            f"({Path(path).name}) \u2014 no new exposure appears to have been "
            "saved."
        )
    return path


def _sexagesimal(text: str, keyword: str = "") -> float:
    """Parse TheSkyX's 'DD MM SS.S' FITS keyword form into decimal hours.

    Raises PolarAlignError naming the keyword if the value is not in that
    form — a missing FITS keyword otherwise surfaces as a bare IndexError
    from the middle of the run, with nothing to say which field was bad.
    """
    parts = text.split()
    if len(parts) < 3:
        raise PolarAlignError(
            f"Unexpected value for FITS keyword {keyword or '?'}: {text!r} "
            f"(expected 'DD MM SS.S')."
        )
    try:
        value = (abs(float(parts[0]))
                 + float(parts[1]) / 60.0
                 + float(parts[2]) / 3600.0)
        return math.copysign(value, float(parts[0]))
    except ValueError as exc:
        raise PolarAlignError(
            f"Could not parse FITS keyword {keyword or '?'}: {text!r}"
        ) from exc


def using_dss_images() -> bool:
    """True when the camera simulator is serving Digitized Sky Survey images."""
    try:
        data = TSXSendTry("out = String(ccdsoftCamera.ImageUseDigitizedSkySurvey);")
        return data[0].strip() == "1"
    except Exception:
        return False


def mount_ha_and_lst() -> tuple[float, float]:
    """Hour angle and LST from the mount and site, rather than an image.

    Used when the image carries no usable header (see image_ha_and_lst).
    Both are read in a single call so they refer to the same instant.
    """
    data = TSXSendTry(
        "sky6RASCOMTele.Connect();"
        "sky6RASCOMTele.GetRaDec();"
        "sky6Utils.ComputeHourAngle(sky6RASCOMTele.dRa);"
        "ha = sky6Utils.dOut0;"
        "sky6Utils.ComputeLocalSiderealTime();"
        "out = String(ha) + '|' + String(sky6Utils.dOut0);"
    )
    try:
        return float(data[0]), float(data[1])
    except (ValueError, IndexError):
        raise PolarAlignError(
            f"Could not read hour angle and LST from the mount: {data!r}"
        )


def image_ha_and_lst() -> tuple[float, float]:
    """Hour angle and LST recorded in the last image's FITS header.

    Falls back to the mount when the camera is serving Digitized Sky Survey
    images.  Those are the original survey plates with a few keywords
    overlaid, so the header describes the 1950s plate and not this
    observation: no TELEHA or LST, a DATE-OBS from decades ago (and not
    always even well formed), and SITELAT/SITELONG for Palomar.  Nothing in
    the file can stand in, so the values have to come from TheSkyX.

    The fallback is deliberately limited to the DSS case.  On real hardware a
    missing or malformed TELEHA means something is wrong that is worth
    stopping for, rather than quietly substituting a different measurement.
    """
    data = TSXSendTry(
        "ccdsoftCameraImage.AttachToActiveImager();"
        'ha = ccdsoftCameraImage.FITSKeyword("TELEHA");'
        'lst = ccdsoftCameraImage.FITSKeyword("LST");'
        "out = ha + '|' + lst;"
    )
    try:
        return _sexagesimal(data[0], "TELEHA"), _sexagesimal(data[1], "LST")
    except PolarAlignError:
        if not using_dss_images():
            raise
        ha, lst = mount_ha_and_lst()
        output(logtime() + (
            "Image has no TELEHA/LST (Digitized Sky Survey image) \u2014 using "
            f"the mount's hour angle {HourFormat(ha)} and LST {HourFormat(lst)} "
            "instead."), WARNING)
        return ha, lst


# A blind solve landing this close to the configured scale means the setting
# was fine and the first failure was transient — worth not nagging about.
_SCALE_AGREEMENT = 0.02          # relative


class SolveScale:
    """The image scale to plate solve at, refined by what ImageLink measures.

    Starts at the configured setting, which is easy to get wrong — most often
    by entering it for a different binning, since the setting is arcsec per
    pixel AT THE BINNING IN USE.  When a blind search succeeds it reports the
    scale it actually found, and that is used for the rest of the run: a known
    scale solves in a fraction of the time a search takes, so a wrong setting
    costs one slow solve rather than one per image.
    """

    def __init__(self, configured: float) -> None:
        self.configured = configured
        self.value      = configured
        self.learned    = False
        # Set once any image has solved at self.value.  From then on a failure
        # is about the sky or the mount, never the scale, so there is nothing
        # for a search to discover.
        self.confirmed  = False

    def confirm(self) -> None:
        self.confirmed = True

    def learn(self, found: float) -> None:
        """Adopt the scale ImageLink measured, reporting it the first time."""
        if found <= 0:
            return
        first          = not self.learned
        self.value     = found
        self.learned   = True
        self.confirmed = True
        if not first:
            return
        off_by = abs(found - self.configured) / self.configured
        if off_by > _SCALE_AGREEMENT:
            output(logtime() + (
                f"The image is {found:.3f}\"/px, not the "
                f"{self.configured:.3f}\"/px configured.  Using the measured "
                f"scale for the rest of this run; set the image scale to "
                f"{found:.3f} for the binning you are using to avoid the "
                "slower search next time."), WARNING)
        else:
            output(logtime() + (
                f"Scale search confirmed {found:.3f}\"/px, close to the "
                "configured value — the earlier failure looks transient."))


def _image_link(scale: float, blind: bool, path: str) -> None:
    """One ImageLink run.  Raises PolarAlignError if it did not solve.

    Asks ImageLinkResults whether it succeeded rather than inferring it from
    the call's return value: execute() throws on failure, so the old test
    against "undefined" reported TheSkyX's exception text as though it were a
    result, and said nothing when the solve merely came back unsuccessful.
    """
    if path:
        # Name the file outright: "the active image" is whatever TheSkyX still
        # has open, which is not necessarily the one just exposed.
        source = 'ImageLink.pathToFITS = "{}";'.format(
            path.replace("\\", "\\\\").replace('"', '\\"'))
    else:
        source = ("ccdsoftCameraImage.AttachToActiveImager();"
                  "ImageLink.pathToFITS = ccdsoftCameraImage.Path;")
    data = TSXSendTry(
        source
        + f"ImageLink.scale = {scale};"
        f"ImageLink.unknownScale = {1 if blind else 0};"
        "ImageLink.execute();"
        "out = String(ImageLinkResults.succeeded);"
    )
    if data[0].strip() != "1":
        message, code = _tidy_error(data[0].strip() or "no reason given")
        raise PolarAlignError(f"Plate solve failed: {message}", code)


def _measured_scale() -> float:
    """The scale ImageLink reports for the image it just solved, or 0."""
    try:
        return float(TSXSendTry(
            "out = String(ImageLinkResults.imageScale);")[0].strip())
    except (ValueError, IndexError):
        return 0.0


def plate_solve(scale: SolveScale, path: str = "",
                allow_search: bool = True) -> None:
    """Solve the image, searching for the scale if it is not yet established.

    There is no retry at the same scale.  ImageLink is deterministic about
    the scale it is handed, so a second attempt with the same number fails the
    same way; and the blind search is strictly more capable, covering the
    configured scale along with everything else.  It is only slower, so try
    the known scale first and remember what a search finds (see SolveScale).

    The search happens only while the scale is still in doubt.  Once an image
    has solved, the scale is a known good number and a later failure is about
    the sky or the mount — an image trailed by the mount being adjusted has
    too few stars to solve at any scale, so searching would only make each
    failure slower.  *allow_search* says the same thing outright for the
    adjustment loop, where a search is never the right answer.
    """
    try:
        _image_link(scale.value, False, path)
        scale.confirm()
        return
    except PolarAlignError as exc:
        # Too few stars is about the image, not the scale: no scale will solve
        # a frame that has nothing to match against, so searching every one of
        # them would only make each failure slower.
        if (scale.confirmed or not allow_search
                or exc.code == TOO_FEW_STARS):
            raise
        output(logtime() + f"{exc}  Searching for the image scale instead.",
               WARNING)

    _image_link(scale.value, True, path)      # raises if this fails too
    scale.learn(_measured_scale())


def plate_solve_results(keep_files: bool, path: str = "") -> tuple[float, float]:
    """RA/Dec of the solved image centre, precessed to now.

    Deletes the image and its .SRC companion unless *keep_files*.
    """
    data = TSXSendTry(
        "err = ImageLinkResults.errorCode;"
        "ra = ImageLinkResults.imageCenterRAJ2000;"
        "dec = ImageLinkResults.imageCenterDecJ2000;"
        "sky6Utils.Precess2000ToNow(ra, dec);"
        "file = ccdsoftCamera.LastImageFileName;"
        "out = err + '|' + sky6Utils.dOut0 + '|' + sky6Utils.dOut1 + '|' + file;"
    )
    if int(data[0]) != 0:
        raise PolarAlignError(f"ImageLink reported error code {data[0]}.")
    if not keep_files:
        fits_name = path or data[3]
        Path.unlink(Path(fits_name), missing_ok=True)
        Path.unlink(Path(fits_name.replace(".fit", ".SRC")), missing_ok=True)
    return float(data[1]), float(data[2])


# How far the mount may report itself from where it was sent before the slew
# is treated as having failed.  Generous: this is checking that the mount went
# roughly where it was told, not its pointing accuracy.
_SLEW_TOLERANCE_DEG = 1.0


def slew_to(ra: float, dec: float, name: str) -> None:
    """Slew to *ra*/*dec*, and confirm the mount reports it got there.

    A slew that quietly does not happen is the worst failure this tool has,
    because nothing downstream looks wrong: images are taken, they solve, and
    the polar axis is computed from two frames that are not where the maths
    assumes.  So read the position back rather than trusting the command.
    """
    data = TSXSendTry(
        f'sky6RASCOMTele.SlewToRaDec({ra}, {dec}, "{name}");'
        "sky6RASCOMTele.GetRaDec();"
        "out = String(sky6RASCOMTele.dRa) + '|' + String(sky6RASCOMTele.dDec);"
    )
    try:
        got_ra, got_dec = float(data[0]), float(data[1])
    except (ValueError, IndexError):
        detail = (data[0].strip() if data else "") or "TheSkyX sent no reply"
        raise PolarAlignError(f"Slew to {name} failed: {_tsx_explain(detail)}")

    # Separation on the sky, with RA wrapped into +/- 12h and converged at
    # high declination.
    d_ra = (got_ra - ra + 12.0) % 24.0 - 12.0
    sep  = math.hypot(d_ra * 15.0 * math.cos(math.radians(dec)), got_dec - dec)
    if sep > _SLEW_TOLERANCE_DEG:
        raise PolarAlignError(
            f"Slew to {name} ended {sep:.2f}\N{DEGREE SIGN} from the requested "
            f"position (asked for RA {HourFormat(ra)} Dec {DegFormat(dec)}, "
            f"mount reports RA {HourFormat(got_ra)} Dec {DegFormat(got_dec)})."
        )


def unpark() -> None:
    # Best effort on purpose: a mount that was never parked reports Unpark as
    # a failure, and that must not end the run.
    _tsx_best_effort("sky6RASCOMTele.Connect(); sky6RASCOMTele.Unpark();",
                     "Unparking the mount")


def altaz_from_tsx(ha: float, dec: float) -> tuple[float, float]:
    """Alt/Az from TheSkyX, which applies refraction.

    Only used to quantify the refraction difference against the local
    calculation — see compare_refraction in run_polar_align.
    """
    data = TSXSendTry(
        "sky6Utils.ComputeLocalSiderealTime();"
        f"Ra = sky6Utils.dOut0 - ({ha});"
        f"sky6Utils.ConvertRADecToAzAlt(Ra, {dec});"
        "out = sky6Utils.dOut1 + '|' + sky6Utils.dOut0;"
    )
    return float(data[0]), float(data[1])


# ── Workflow ────────────────────────────────────────────────────────────────

def capture_camera_state() -> CameraState:
    """Record the camera settings the run is about to change."""
    enabled, left, right, top, bottom = get_subframe()
    return CameraState(
        binning=get_binning(), subframe=enabled,
        left=left, right=right, top=top, bottom=bottom,
        filter_idx=None,
    )


def restore_camera_state(state: CameraState) -> None:
    """Put back binning, subframe and filter, and say what was put back.

    Never raises: this runs from a finally, so a failure here must not bury
    whatever ended the run.

    Reported rather than done silently.  The run changes the camera under the
    user's feet -- binning to 4x4, usually a centre crop, sometimes a
    different filter -- and the next thing they do is likely to be an
    exposure that matters.  Saying what was restored turns "I hope it put
    that back" into something they can read off the log, and the line appears
    however the run ended, including after Stop or an error.
    """
    def said_binning() -> str:
        return f"binning {state.binning}x{state.binning}"

    def said_subframe() -> str:
        if not state.subframe:
            return "full frame"
        return (f"subframe {state.left}\u2013{state.right} by "
                f"{state.top}\u2013{state.bottom}")

    def said_filter() -> str:
        try:
            name = getFilterName(state.filter_idx).strip()
        except Exception:                      # noqa: BLE001
            name = ""
        return f"filter {name or state.filter_idx}"

    restored: list[str] = []
    for what, action, said in (
        ("binning",  lambda: set_binning(state.binning),   said_binning),
        ("subframe", lambda: restore_subframe(state),      said_subframe),
        ("filter",   lambda: _tsx_check(
            f"ccdsoftCamera.FilterIndexZeroBased = {state.filter_idx};",
            "Restoring the filter"),                       said_filter),
    ):
        if what == "filter" and state.filter_idx is None:
            continue                           # the run never touched it
        try:
            action()
            restored.append(said())
        except Exception as exc:
            output(logtime() + f"Could not restore camera {what}: {exc}",
                   WARNING)

    if restored:
        output(logtime() + "Camera settings restored: "
                         + ", ".join(restored) + ".")


def _measure(exposure: float, binning: int, reduction: int,
             scale: SolveScale, keep_files: bool,
             allow_search: bool = True) -> tuple[float, float, float, float]:
    """Take one image, solve it, and return (ha, lst, ra, dec).

    ha/lst come from the FITS header; ra/dec from the plate solve.
    """
    path = take_image(exposure, binning, reduction)
    ha, lst = image_ha_and_lst()
    output(logtime() + f"Image HA: {HourFormat(ha)}  LST: {HourFormat(lst)}")
    plate_solve(scale, path, allow_search)
    ra, dec = plate_solve_results(keep_files, path)
    output(logtime() + f"Solved RA: {HourFormat(ra)}  Dec: {DegFormat(dec)}")
    return ha, lst, ra, dec


# How many times to retake an image whose solve failed, before giving up on
# the measurements the run cannot start without.  These retries are for things
# that clear on their own — cloud, a passing aircraft, a nudged mount.  A wrong
# scale is not one of them, and is already dealt with inside plate_solve by
# searching for the scale rather than by trying again.
_SOLVE_ATTEMPTS = 3


def _measure_with_retry(what: str, token, exposure: float, binning: int,
                        reduction: int, scale: SolveScale, keep_files: bool
                        ) -> Optional[tuple[float, float, float, float]]:
    """_measure, retaking the image when the solve fails.

    Returns None if the run was stopped part way.  The two measurements that
    establish the polar axis have nowhere to fall back to — without both,
    there is no axis — so a failure here retries rather than ending the
    session, which the monitoring loop further down already does.
    """
    for attempt in range(1, _SOLVE_ATTEMPTS + 1):
        try:
            return _measure(exposure, binning, reduction, scale, keep_files)
        except PolarAlignError as exc:
            if token.checkpoint():
                return None
            # Too few stars is not something another exposure five seconds
            # later will fix — the sky is too light, or the camera is out of
            # focus.  The caller waits for darkness instead, which is a far
            # better answer than spending three exposures proving the point.
            if exc.code == TOO_FEW_STARS:
                raise
            if attempt == _SOLVE_ATTEMPTS:
                raise PolarAlignError(
                    f"Could not plate solve the {what} after "
                    f"{_SOLVE_ATTEMPTS} attempts: {exc}",
                    exc.code,
                ) from exc
            output(logtime() + (
                f"Could not plate solve the {what} (attempt {attempt} of "
                f"{_SOLVE_ATTEMPTS}): {exc}  Retaking the image."), WARNING)
    return None


# How long to leave between test exposures while waiting for the sky to
# darken.  The sky changes over tens of minutes, so there is nothing to gain
# from hammering the camera.
_DARK_RETRY_SECONDS = 60.0


def wait_for_stars(token, exposure: float, binning: int, reduction: int,
                   scale: SolveScale, keep_files: bool) -> bool:
    """Take test images until one solves, or the user stops.

    Returns True once the sky is usable.  Deliberately does not slew: this is
    only asking whether there are stars to be had yet, and the run starts
    again properly once there are.
    """
    output(logtime() + (
        "Waiting for the sky to darken.  Taking a test image every "
        f"{_DARK_RETRY_SECONDS:.0f} seconds; press Stop to give up."), WARNING)

    attempt = 0
    while not token.checkpoint():
        attempt += 1
        try:
            path = take_image(exposure, binning, reduction)
            plate_solve(scale, path)
            plate_solve_results(keep_files, path)
        except PolarAlignError as exc:
            if exc.code != TOO_FEW_STARS:
                raise
            output(logtime() + (
                f"Test image {attempt}: still too few stars to solve."))
            if token.sleep(_DARK_RETRY_SECONDS):
                return False
            continue
        output(logtime() + (
            f"Test image {attempt} solved — the sky is dark enough.  "
            "Starting the alignment again from the first point."))
        return True
    return False


def run_polar_align(
    token,
    *,
    exposure: float,
    binning: int,
    scale: float,
    subframe: int,
    filter_name: str = "",
    pa_dec: float = 60.0,
    ha1: float = 1.0,
    ha2: float = 5.0,
    keep_files: bool = False,
    compare_refraction: bool = False,
    on_adjustment: Optional[Callable[[float, float], None]] = None,
    on_stale: Optional[Callable[[str], None]] = None,
) -> None:
    """Run the polar-alignment procedure until stopped.

    *token* is a StopToken; the procedure checks it between every slow step.
    *on_adjustment* receives (theta, phi) in degrees after each solve — the
    altitude and azimuth corrections still needed — for the UI's gauges.
    *on_stale* receives a short reason when an image in the adjustment loop
    does not solve, so the gauges can show that what they display is from an
    earlier image rather than silently going stale.

    An image with too few stars to solve is taken to mean the sky has not
    darkened yet: the run takes test images once a minute until one solves,
    then begins the pair again.  Stop ends the wait.

    When *compare_refraction* is set, each Alt/Az is also computed via
    TheSkyX (which applies refraction) and the difference logged, so the
    size of the correction can be measured on-site rather than assumed.
    """
    connect_camera()
    # One tracker for the whole run: what a scale search discovers on the
    # first image is worth keeping for every image after it.
    solve_scale = SolveScale(scale)
    if using_dss_images():
        # Say so before anything depends on it.  It also bears on how much the
        # result means: a survey image is fetched for wherever the mount says
        # it is pointing, so it cannot show a pointing error the mount does
        # not already know about.
        output(logtime() + (
            "Camera is serving Digitized Sky Survey images.  Hour angle and "
            "LST will come from the mount, and the alignment figures will "
            "only be as real as the mount simulator makes them."), WARNING)
    state = capture_camera_state()
    try:
        if filter_name:
            connect_filterwheel()
            state.filter_idx = select_filter(filter_name)
            output(logtime() + f"Selected filter: {filter_name}")

        # Latitude is read from the mount once and reused: the Alt/Az maths
        # is local, so TheSkyX is asked for the site, not for every
        # conversion.  LST is re-read before each slew, since it advances.
        lat, _lon, lst, _ut = LatLongLstUT()

        def altaz(ha: float, dec: float, what: str) -> tuple[float, float]:
            """Local Alt/Az, optionally compared against TheSkyX's."""
            alt, az = AltAzfromHADECLat(ha, dec, lat)
            if compare_refraction:
                try:
                    t_alt, _t_az = altaz_from_tsx(ha, dec)
                    output(logtime() + (
                        f"Refraction check ({what}): local alt {alt:.4f} vs "
                        f"TheSkyX {t_alt:.4f} — difference "
                        f"{(t_alt - alt) * 3600:+.1f} arcsec"))
                except Exception as exc:
                    output(logtime() + f"Refraction check failed: {exc}", WARNING)
            return alt, az

        # Screen the chosen points before moving anything: some combinations
        # of declination and hour angle cannot give a good answer however
        # well the night goes, and it is better to say so now than after two
        # exposures.
        for level, note in screen_geometry(lat, pa_dec, ha1, ha2):
            output(logtime() + note,
                   ERROR if level == "error" else
                   WARNING if level == "warn" else OK)

        def wait_then_restart(which: str) -> bool:
            """Sit out the twilight, then say whether to start again."""
            output(logtime() + (
                f"The {which} had too few stars to plate solve \u2014 the sky "
                "is probably still too light."), WARNING)
            return wait_for_stars(token, exposure, binning, subframe,
                                  solve_scale, keep_files)

        # ── The two images the solve is built from ───────────────────────
        # Both points sit inside one loop because waiting for darkness has to
        # start the pair again, not resume it.  Tracking carries the mount's
        # hour angle forward while we wait, and although the solve itself
        # would survive that (the measured LST and hour angle move together),
        # the separation between the two points would quietly shrink — and
        # with it the precision of the whole result.  The second point is the
        # one that usually fails, having been reached a few minutes earlier
        # in the twilight than the first.
        while True:
            if token.checkpoint():
                return

            # ── First point ──────────────────────────────────────────────
            output(logtime() + "Slewing to the first polar alignment point")
            unpark()
            slew_to(lst - ha1, pa_dec, "PA 1")
            if token.checkpoint():
                return

            output(logtime() + "Taking the first image")
            try:
                first = _measure_with_retry("first image", token,
                                            exposure, binning, subframe,
                                            solve_scale, keep_files)
            except PolarAlignError as exc:
                if exc.code != TOO_FEW_STARS:
                    raise
                if not wait_then_restart("first image"):
                    return
                lat, _lon, lst, _ut = LatLongLstUT()   # time has moved on
                continue
            if first is None or token.checkpoint():
                return

            # ── Second point ─────────────────────────────────────────────
            lat, _lon, lst, _ut = LatLongLstUT()
            output(logtime() + "Slewing to the second polar alignment point")
            slew_to(lst - ha2, pa_dec, "PA 2")
            if token.checkpoint():
                return

            output(logtime() + "Taking the second image")
            try:
                second = _measure_with_retry("second image", token,
                                             exposure, binning, subframe,
                                             solve_scale, keep_files)
            except PolarAlignError as exc:
                if exc.code != TOO_FEW_STARS:
                    raise
                if not wait_then_restart("second image"):
                    return
                lat, _lon, lst, _ut = LatLongLstUT()
                continue
            if second is None or token.checkpoint():
                return
            break

        iha1, ilst1, ira1, idec1 = first
        iha2, ilst2, ira2, idec2 = second

        # ── Solve for the polar axis ─────────────────────────────────────
        pa_ha, pa_dec_solved = PASolve(ira1, idec1, ilst1, iha1,
                                       ira2, idec2, ilst2, iha2)
        # The solve picks whichever candidate axis lies nearest a pole, and
        # has no idea which hemisphere the site is in.  Fed a degenerate pair
        # it will cheerfully return the far pole, which looks entirely
        # plausible to the distance-from-the-pole check further down.
        if (pa_dec_solved > 0) != (lat > 0):
            raise PolarAlignError(
                f"The solve put the polar axis at declination "
                f"{pa_dec_solved:+.1f}\N{DEGREE SIGN}, the opposite hemisphere "
                f"to this site (latitude {lat:+.1f}\N{DEGREE SIGN}).  The two "
                "images cannot have been far enough apart to tell the axis "
                "from its mirror image \u2014 check the declination and hour "
                "angles."
            )

        pa_alt, pa_az = altaz(pa_ha, pa_dec_solved, "polar axis")
        if pa_az > 180.0:
            pa_az -= 360.0

        output(logtime() + f"Polar axis Alt: {DegFormat(pa_alt)}  "
                           f"Az: {DegFormat(pa_az)}")
        output(logtime() + f"Alt error: {DegFormat(pa_alt - lat)}  "
                           f"Az error: {DegFormat(pa_az)}")

        # Two axes fit the pair of images equally well and we pick the one
        # nearer the pole; that choice is only sound while the mount is
        # roughly aligned to begin with.  How far it holds is set by how far
        # the images themselves are from the pole -- see
        # measurable_misalignment_deg -- so a declination near the equator
        # tolerates far more than one close in.  Past that the solve can
        # return the rival axis, which looks perfectly plausible but is wrong,
        # so say so rather than let it drive the loop unremarked.
        pole_sep = 90.0 - abs(pa_dec_solved)
        limit = measurable_misalignment_deg(pa_dec)
        if pole_sep > limit:
            output(logtime() + f"Warning: the polar axis solves to "
                               f"{DegFormat(pole_sep)} from the pole, beyond "
                               f"the {limit:.0f}\N{DEGREE SIGN} that images at "
                               f"declination {pa_dec:+.0f}\N{DEGREE SIGN} can "
                               "measure.  Correct roughly by hand, then run "
                               "again.", WARNING)

        # Where the second image would sit once the mount is aligned.
        i2_alt, i2_az = altaz(ilst2 - ira2, idec2, "image 2")
        target_alt, target_az = RotateAltAz(i2_alt, i2_az, pa_alt - lat, pa_az)
        if target_az > 180.0:
            target_az -= 360.0
        target_ha, target_dec = _hadec_from_altaz(target_alt, target_az)

        _report_adjustment(i2_alt, i2_az, target_alt, target_az, lat,
                           on_adjustment)

        # ── Iterate: image, solve, report the remaining correction ───────
        consecutive_failures = 0
        while not token.checkpoint():
            output(logtime() + "Taking image")
            try:
                iha, ilst, ira, idec = _measure(
                    exposure, binning, subframe, solve_scale, keep_files,
                    allow_search=False)
            except PolarAlignError as exc:
                # Expected, not exceptional: once the first two images have
                # been taken the user is at the mount turning bolts, and an
                # image taken mid-adjustment trails and will not solve.
                consecutive_failures += 1
                moving = exc.code == TOO_FEW_STARS

                if on_stale is not None:
                    on_stale("mount moving?" if moving else "no solve")

                # Say it once.  Repeating the same line for every image would
                # bury the reading the user is actually working from.
                if consecutive_failures == 1:
                    if moving:
                        output(logtime() + (
                            "Image did not solve — too few stars, which "
                            "usually means the mount was moving.  The reading "
                            "below is from the last image that solved."),
                            WARNING)
                    else:
                        output(logtime() + f"Could not plate solve image: {exc}",
                               WARNING)
                elif consecutive_failures == _SOLVE_ATTEMPTS and not moving:
                    output(logtime() + (
                        f"{consecutive_failures} solves have failed in a row, "
                        "at the known scale and by searching for it.  Check "
                        "the sky, focus and tracking.  Imaging will keep "
                        "retrying until you press Stop."), WARNING)
                continue
            if consecutive_failures:
                output(logtime() + (
                    f"Solving again after {consecutive_failures} "
                    f"image{'s' if consecutive_failures > 1 else ''}."))
                consecutive_failures = 0

            ialt, iaz = altaz(ilst - ira, idec, "image")
            if iaz > 180.0:
                iaz -= 360.0

            # The target drifts with the sky, so advance it to this image's LST.
            t_alt, t_az = AltAzfromHADECLat(ilst - ilst2 + target_ha,
                                            target_dec, lat)
            if t_az > 180.0:
                t_az -= 360.0

            _report_adjustment(ialt, iaz, t_alt, t_az, lat, on_adjustment)

        output(logtime() + "Completed polar alignment")

    finally:
        restore_camera_state(state)


def _hadec_from_altaz(alt: float, az: float) -> tuple[float, float]:
    """Hour angle and declination from Alt/Az, via TheSkyX."""
    data = TSXSendTry(
        f"sky6Utils.ConvertAzAltToRADec({az}, {alt});"
        "Ra = sky6Utils.dOut0;"
        "Dec = sky6Utils.dOut1;"
        "sky6Utils.ComputeHourAngle(Ra);"
        "out = sky6Utils.dOut0 + '|' + Dec;"
    )
    return float(data[0]), float(data[1])


def _report_adjustment(alt: float, az: float, target_alt: float, target_az: float,
                       lat: float,
                       on_adjustment: Optional[Callable[[float, float], None]]) -> None:
    """Work out and report the mount adjustment still needed."""
    theta, phi, saturated = BruteRotationSearch(alt, az, target_alt, target_az)
    # Both senses reverse in the southern hemisphere.
    theta *= math.copysign(1, lat)
    phi   *= math.copysign(1, lat)

    if on_adjustment is not None:
        on_adjustment(theta, phi)

    direction = "counter clockwise" if phi > 0 else "clockwise"
    at_least = "by at least " if saturated else "by "
    output(logtime() + f"Azimuth: rotate mount {direction} {at_least}{DegFormat(abs(phi))}")
    vertical = "lower" if theta > 0 else "raise"
    output(logtime() + f"Altitude: {vertical} mount {at_least}{DegFormat(abs(theta))}")
    if saturated:
        # Past the search window the two axes trade off against each other, so
        # neither number is trustworthy — only their direction is.
        output(logtime() + "Warning: the mount is further out than the search "
                           "covers.  Adjust in the directions shown, then take "
                           "a fresh pair of images.")

###############################################################################
# SETTINGS
###############################################################################



import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QScrollArea, QScrollBar, QFrame, QDialog, QGroupBox, QGridLayout,
    QSizePolicy, QMessageBox, QFileDialog, QStyle, QStyleFactory, QTextEdit,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QProcess, QProcessEnvironment, QPoint
from PySide6.QtGui import QColor, QFontMetrics, QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression


######################################################
# Class for loading, writing and editing settings
# ---------------- Schema ----------------

# Types of editor for settings
EditorType = str  # "text" | "spin" | "doublespin" | "combo"

# Basic data storage per setting
@dataclass
class SettingSpec:
    key: str
    label: str
    default: Union[str, int, float, bool] = ""
    group: str = "General"
    tooltip: str = ""
    editor: EditorType = "text"             # "text", "spin", "doublespin", "combo"
    validator: Optional[str] = None         # "int"|"float"|"float_range"|"regex"|"path_file"|"path_dir"|"custom"|None
    validator_args: Dict[str, Any] = None
    options: Optional[List[str]] = None     # for combo
    required: bool = False
    visible: bool = True
    visible_if: Optional[Callable[[Dict[str, Any]], bool]] = None
    suffix: str = ""                        # displayed after the value in spin/doublespin editors


# ---------------- Core Widget ----------------

class SettingsWidget(QWidget):
    settingsSaved = Signal(dict)
    canceled = Signal()
    def __init__(self, schema: List[SettingSpec], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._schema = {s.key: s for s in schema}
        self._order = [s.key for s in schema]
        self._error_area: Optional[QTextEdit] = None
        self._groups: Dict[str, Tuple[QGroupBox, List[str]]] = {}

        self._editors: Dict[str, QWidget] = {}
        self._row_widgets: Dict[str, QWidget] = {}
        self._labels: List[QLabel] = []
        self._did_initial_size = False  # one-time sizing guard

        # Prevent checks on initial values until all values are loaded
        self._booting = True
        QTimer.singleShot(0, self._finish_boot)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ----- Scrollable area -----
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        groups: List[str] = []
        for k in self._order:
            g = self._schema[k].group
            if g not in groups:
                groups.append(g)

        self._build_jump_bar(groups)

        for group in groups:
            gb = QGroupBox(group)
            grid = QGridLayout(gb)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(6)
            grid.setColumnStretch(0, 0)  # labels fixed
            grid.setColumnStretch(1, 1)  # editors stretch
            row = 0
            keys_in_group: List[str] = []  # <— collect keys

            for key in [k for k in self._order if self._schema[k].group == group]:
                spec = self._schema[key]
                keys_in_group.append(key)   # <— track
                row_container = QWidget()
                row_layout = QGridLayout(row_container)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setHorizontalSpacing(12)
                row_layout.setVerticalSpacing(0)

                if spec.required:
                    label = QLabel(f"{spec.label} <span style='color:#FF6A00;'>*</span>")
                    label.setTextFormat(Qt.RichText)
                else:
                    label = QLabel(spec.label)
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                self._labels.append(label)

                editor_widget = self._create_editor(spec)
                editor_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                editor_widget.setMinimumWidth(440)
                if spec.tooltip:
                    label.setToolTip(spec.tooltip)

                row_layout.addWidget(label,         0, 0, 1, 1)
                row_layout.addWidget(editor_widget, 0, 1, 1, 1)

                self._row_widgets[key] = row_container
                row_container.setVisible(spec.visible)

                grid.addWidget(row_container, row, 0, 1, 2)
                row += 1

            content_layout.addWidget(gb)
            self._groups[group] = (gb, keys_in_group)
        content_layout.addStretch(1)

        # QScrollArea with NO horizontal scrollbar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(content)
        self._scroll = scroll
        scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)
        body.addWidget(self._jump_bar, stretch=0)
        body.addWidget(scroll, stretch=1)
        root.addLayout(body)

        # Error / message area
        self._error_area = QTextEdit()
        self._error_area.setReadOnly(True)
        self._error_area.setFixedHeight(100)
        self._error_area.setPlaceholderText("Messages will appear here…")
        _bg    = theme.input_bg()
        _fg    = theme.input_text()
        _bdr   = theme.input_border()
        _ebg   = theme.input_error_bg()
        _ebdr  = theme.input_error_border()
        self._error_area.setStyleSheet(f"""
        QTextEdit {{
            background: {_bg};
            color: {_fg};
            border: 1px solid {_bdr};
            border-radius: 6px;
            padding: 6px;
        }}
        """)
        self.setStyleSheet(self.styleSheet() + f"""
        /* Base look */
        QLineEdit {{
            padding: 6px;
            border-radius: 6px;
            border: 1px solid {_bdr};
            background: {_bg};
            color: {_fg};
        }}

        /* Error state (required/invalid) */
        QLineEdit[error="true"] {{
            border: 2px solid {_ebdr};
            background: {_ebg};
            color: {_fg};
        }}
        QSpinBox, QDoubleSpinBox, QComboBox {{
            padding: 6px;
            border-radius: 6px;
            border: 1px solid {_bdr};
            background: {_bg};
            color: {_fg};
        }}

        QSpinBox[error="true"], QDoubleSpinBox[error="true"], QComboBox[error="true"] {{
            border: 2px solid {_ebdr};
            background: {_ebg};
            color: {_fg};
        }}
        """)
        self._error_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._error_messages: Dict[str, str] = {}
        #self._error_area.setStyleSheet("QTextEdit { background: #111; color: #eee; border-radius: 8px; padding: 8px; }")
        root.addWidget(self._error_area)

        # Footer
        footer = QHBoxLayout()
        self._defaults_btn = QPushButton("Restore defaults")
        self._defaults_btn.setAutoDefault(False)
        self._defaults_btn.setDefault(False)
        self._defaults_btn.clicked.connect(self._restore_defaults_clicked)
        footer.addWidget(self._defaults_btn)
        footer.addStretch(1)
        self._save_btn = QPushButton("Save Settings")
        self._cancel_btn = QPushButton("Cancel")
        self._save_btn.clicked.connect(self._save_clicked)
        self._cancel_btn.clicked.connect(self._cancel_clicked)
        footer.addWidget(self._save_btn)
        footer.addWidget(self._cancel_btn)
        root.addLayout(footer)

        # Make all labels same width
        self._normalize_label_widths()

        # ✅ Measure real content width and apply a comfortable initial size
        # self._apply_initial_width() Initial width is supplied on first show

        # Visibility auto-updates
        self._install_visibility_triggers()
        # Apply global spinbox stylesheet once
        # self.setStyleSheet(self.styleSheet() + SPINBOX_CSS)
        # Ensure focus starts on the first editor after show
        QTimer.singleShot(0, self._focus_first_editor)

        # Disables return pushing opening any buttons!
        for btn in self.findChildren(QPushButton):
            btn.setDefault(False)
            btn.setAutoDefault(False)

        # Only show groups if at least one item is visible
        self._refresh_group_visibility()

    def showEvent(self, e):
        super().showEvent(e)
        if not self._did_initial_size:
            self._apply_initial_width(initial=True)

    # Once all values are loaded, then can check the ranges.
    def _finish_boot(self):
        self._booting = False
        # optionally recompute visibility/ranges once everything is ready
        self.refresh_visibility()

    def _focus_first_editor(self):
        # focus first visible editor (LineEdit / Spin / DoubleSpin / Combo)
        for key in self._order:
            row = self._row_widgets.get(key)
            if not row or not row.isVisible():
                continue
            w = self._editors.get(key)
            if isinstance(w, (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox)):
                w.setFocus(Qt.OtherFocusReason)
                return

    # --------- Public API ----------
    def values(self) -> Dict[str, Union[str, int, float, bool]]:
        out: Dict[str, Union[str, int, float, bool]] = {}
        for k in self._order:
            w = self._editors.get(k)
            if w is None:
                continue
            if isinstance(w, QLineEdit):
                out[k] = w.text().strip()
            elif isinstance(w, QSpinBox):
                out[k] = int(w.value())
            elif isinstance(w, QDoubleSpinBox):
                out[k] = float(w.value())
            elif isinstance(w, QComboBox):
                out[k] = w.currentText()
            elif isinstance(w, QCheckBox):
                out[k] = bool(w.isChecked())
        return out

    def set_values(self, values: Dict[str, Any]) -> None:
        self._booting = True # Turn off validators whilst we are setting values programatically
        try:
            for k, v in values.items():
                if k not in self._editors:
                    continue
                w = self._editors[k]
                if isinstance(w, QLineEdit):
                    w.setText("" if v is None else str(v))
                elif isinstance(w, QSpinBox):
                    try: w.setValue(int(v))
                    except: pass
                elif isinstance(w, QDoubleSpinBox):
                    try: w.setValue(float(v))
                    except: pass
                elif isinstance(w, QComboBox):
                    i = w.findText(str(v))
                    if i >= 0: w.setCurrentIndex(i)
                elif isinstance(w, QCheckBox):
                    w.setChecked(bool(v))
        finally:
            self._booting = False # Turn on validators again

        self.refresh_visibility()

    def refresh_visibility(self) -> None:
        vals = self.values()
        changed = False
        for k, spec in self._schema.items():
            if spec.visible_if is not None:
                try:
                    show = bool(spec.visible_if(vals))
                except Exception:
                    show = False
                row = self._row_widgets.get(k)
                if row and row.isHidden() == show:
                    row.setVisible(show)
                    changed = True

        # Hide empty groups
        self._refresh_group_visibility()

        if changed:
            self._apply_initial_width(initial=False)


    # Allows you to set the combo options after the schema is established.
    def set_combo_options(
    self,
    key: str,
    options: List[str],
    *,
    keep_value: bool = True,
    select: Optional[str] = None
        ) -> None:
        """
        Replace the option list of a combo editor at runtime.

        keep_value=True  -> try to keep the current selection if it still exists
        select="..."     -> if provided and present in options, select this value instead
                            (takes precedence over keep_value)
        If neither applies, selects the first option (if any).

        Also updates the schema's .options for consistency.
        """
        w = self._editors.get(key)
        if not isinstance(w, QComboBox):
            raise KeyError(f"'{key}' is not a combo editor (found {type(w).__name__}).")

        prev = w.currentText()
        w.blockSignals(True)
        try:
            w.clear()
            w.addItems([str(o) for o in options])

            # Choose selection
            target = None
            if select is not None and select in options:
                target = select
            elif keep_value and prev in options:
                target = prev

            if target is not None:
                idx = w.findText(target)
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif w.count() > 0:
                w.setCurrentIndex(0)
        finally:
            w.blockSignals(False)

        # keep schema in sync (so future loads/validations know the new list)
        spec = self._schema.get(key)
        if spec is not None:
            spec.options = list(options)

        # refresh any visibility rules that might depend on combo value
        self._on_any_value_change()

    # --------- Internals ----------
    def _refresh_group_visibility(self) -> None:
        """Show a group box only if at least one of its rows is (itself) set visible."""
        for group, (gb, keys) in self._groups.items():
            any_visible = False
            for k in keys:
                row = self._row_widgets.get(k)
                if row and not row.isHidden():
                    any_visible = True
                    break
            gb.setVisible(any_visible)
            gb.updateGeometry()
            items = self._jump_bar.findItems(group, Qt.MatchExactly)
            if items:
                item = items[0]
                item.setFlags(
                    item.flags() | Qt.ItemIsEnabled if any_visible
                    else item.flags() & ~Qt.ItemIsEnabled
                )
                col = theme.cell_text() if any_visible else theme.monitor_label_col()
                item.setForeground(QColor(col))

    def _build_jump_bar(self, groups: List[str]) -> None:
        self._jump_bar = QListWidget()
        self._jump_bar.setFixedWidth(148)
        self._jump_bar.setSpacing(1)
        self._jump_bar.setFrameShape(QFrame.NoFrame)
        self._jump_bar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._jump_bar.setFocusPolicy(Qt.NoFocus)
        self._jump_bar.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                padding: 2px 0;
            }}
            QListWidget::item {{
                padding: 5px 8px;
                border-radius: 5px;
                font-size: 12px;
                color: {theme.cell_text()};
            }}
            QListWidget::item:selected {{
                background: {theme.jump_bar_selected_bg()};
                color: {theme.cell_text()};
            }}
            QListWidget::item:hover:!selected {{
                background: {theme.input_bg()};
            }}
        """)
        for group in groups:
            item = QListWidgetItem(group)
            item.setData(Qt.UserRole, group)
            self._jump_bar.addItem(item)
        self._jump_bar.currentRowChanged.connect(self._on_jump_bar_clicked)

    def _on_jump_bar_clicked(self, row: int) -> None:
        if row < 0:
            return
        item = self._jump_bar.item(row)
        if item is None:
            return
        group_name = item.data(Qt.UserRole)
        gb, _ = self._groups.get(group_name, (None, None))
        if gb is None or not gb.isVisible():
            return
        content = self._scroll.widget()
        y = gb.mapTo(content, QPoint(0, 0)).y()
        self._scroll.verticalScrollBar().setValue(y)

    def _on_scroll_changed(self, value: int) -> None:
        content = self._scroll.widget()
        best_group = None
        best_y = -1
        for group, (gb, _) in self._groups.items():
            if not gb.isVisible():
                continue
            y = gb.mapTo(content, QPoint(0, 0)).y() - value
            if y <= 20 and y > best_y:
                best_y = y
                best_group = group
        if best_group is None:
            return
        items = self._jump_bar.findItems(best_group, Qt.MatchExactly)
        if items:
            self._jump_bar.blockSignals(True)
            self._jump_bar.setCurrentItem(items[0])
            self._jump_bar.blockSignals(False)

    def _inline_test_script_clicked(self):
        btn: QPushButton = self.sender()
        key = btn.property("target_key")
        if not key:
            return

        edit = self._editors.get(key)
        if not isinstance(edit, QLineEdit):
            return

        path = edit.text().strip()
        if not path:
            self._append_error(f'No file selected for "{self._schema[key].label}".')
            return
        if not os.path.isfile(path):
            self._append_error(f"File not found: {path}")
            return

        # If the spec supplies a custom test_handler, use it instead of executing the file.
        handler = (self._schema[key].validator_args or {}).get("test_handler")
        if callable(handler):
            ok, msg = handler(path)
            if ok:
                self._error_area.append(f"<span style='color:green'>{msg}</span>")
            else:
                self._append_error(msg)
            return

        # POSIX executability check (optional on macOS/Linux)
        if os.name != "nt" and not os.access(path, os.X_OK):
            self._append_error(f"File is not executable: {path}")
            return

        self._error_area.append(f"<b>Testing:</b> {path}")

        proc = QProcess(self)
        proc.setProgram(path)

        # Optional: pass arguments / timeout from schema
        args = (self._schema[key].validator_args or {}).get("test_args", [])
        proc.setArguments([str(a) for a in args])

        timeout_ms = int((self._schema[key].validator_args or {}).get("timeout_ms", 5000))

        def handle_finished(code, status):
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            err = bytes(proc.readAllStandardError()).decode("utf-8", "replace")
            if status == QProcess.CrashExit:
                self._append_error("Script crashed.")
            elif code != 0:
                self._append_error(f"Script exited with code {code}.")
            if out.strip():
                self._error_area.append(f"<pre>{out}</pre>")
            if err.strip():
                self._append_error(err)
            proc.deleteLater()

        proc.finished.connect(handle_finished)

        # Timeout guard
        timer = QTimer(proc)
        timer.setSingleShot(True)

        def kill_on_timeout():
            if proc.state() != QProcess.NotRunning:
                proc.kill()
                self._append_error("Script timed out and was terminated.")

        timer.timeout.connect(kill_on_timeout)

        qenv = QProcessEnvironment()
        for k, v in subprocess_clean_env().items():
            qenv.insert(k, v)
        proc.setProcessEnvironment(qenv)

        proc.start()
        timer.start(timeout_ms)

    def _normalize_label_widths(self):
        if not self._labels:
            return
        fm = QFontMetrics(self._labels[0].font())
        max_px = 0
        for lbl in self._labels:
            txt = lbl.text().replace("<span style='color:#FF6A00;'>*</span>", "*")
            w = fm.horizontalAdvance(txt) + 8
            max_px = max(max_px, w)
        for lbl in self._labels:
            lbl.setFixedWidth(max_px)

    def _compute_recommended_width(self) -> int:
        label_w = max((lbl.width() for lbl in self._labels), default=140)

        widest_editor = 480
        for row in self._row_widgets.values():
            if row.isHidden():
                continue
            widest_editor = max(widest_editor, row.sizeHint().width() - label_w)

        style = self.style()
        inter_col_gap  = 12
        side_margins   = 2 * 10
        group_padding  = 24
        # Prefer QStyle.PixelMetric enums; fall back to measuring a temp scrollbar if needed
        try:
            scroll_extent = style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent, None, self)
        except Exception:
            sb = QScrollBar(Qt.Vertical)
            scroll_extent = sb.sizeHint().width() or 16
            sb.deleteLater()
        try:
            frame_extra = 2 * style.pixelMetric(QStyle.PixelMetric.PM_DefaultFrameWidth, None, self)
        except Exception:
            frame_extra = 4

        jump_bar_w = 148 + 8  # jump bar fixed width + body spacing
        total = label_w + inter_col_gap + widest_editor + side_margins + group_padding + scroll_extent + frame_extra + jump_bar_w
        return total + 40

    # NEW: apply width (initial + after visibility changes)
    def _apply_initial_width(self, initial: bool = False):
        recommended = self._compute_recommended_width()
        # keep (or raise) the minimum width so no horizontal scrollbars appear
        if recommended > self.minimumWidth():
            self.setMinimumWidth(recommended)
        if initial and not self._did_initial_size:
            self.resize(max(self.width(), recommended), max(self.height(), 600))
            self._did_initial_size = True
        else:
            # don't force a resize during edits; just refresh geometry
            self.updateGeometry()

    def _create_editor(self, spec: SettingSpec) -> QWidget:
        tip = spec.tooltip or ""

        if spec.editor == "spin":
            w = QSpinBox()
            args = spec.validator_args or {}
            w.setRange(int(args.get("min", -2_147_483_648)), int(args.get("max", 2_147_483_647)))
            w.setSingleStep(int(args.get("step", 1)))
            w.setValue(int(spec.default) if str(spec.default).strip() != "" else 0)
            if spec.suffix:
                w.setSuffix(f" {spec.suffix.strip()}")
            if tip: w.setToolTip(tip)
            self._editors[spec.key] = w
            self._apply_dynamic_range(spec, w)
            w.valueChanged.connect(self._on_any_value_change)
            return w

        if spec.editor == "doublespin":
            w = QDoubleSpinBox()
            args = spec.validator_args or {}
            w.setRange(float(args.get("min", -1e12)), float(args.get("max", 1e12)))
            w.setDecimals(int(args.get("decimals", 3)))
            w.setSingleStep(float(args.get("step", 0.1)))
            w.setValue(float(spec.default) if str(spec.default).strip() != "" else 0.0)
            if spec.suffix:
                w.setSuffix(f" {spec.suffix.strip()}")
            if tip: w.setToolTip(tip)
            self._editors[spec.key] = w
            self._apply_dynamic_range(spec, w)
            w.valueChanged.connect(self._on_any_value_change)
            return w

        if spec.editor == "combo":
            w = QComboBox()
            opts = spec.options or []
            w.addItems([str(o) for o in opts])
            def_val = str(spec.default)
            idx = w.findText(def_val) if def_val else -1
            w.setCurrentIndex(idx if idx >= 0 else 0)
            if tip: w.setToolTip(tip)
            w.setFocusPolicy(Qt.TabFocus)   # <-- prevents "auto-focus on show"
            # optional: make the control look calmer when focused
            w.setStyleSheet("QComboBox { padding: 4px; }") # + COMBO_CSS)

            self._editors[spec.key] = w
            w.currentTextChanged.connect(self._on_any_value_change)
            return w

        if spec.editor == "bool":
            w = QCheckBox()
            w.setChecked(bool(spec.default))
            if tip: w.setToolTip(tip)
            self._editors[spec.key] = w
            # Trigger visibility updates when toggled
            w.stateChanged.connect(self._on_any_value_change)
            return w

        if spec.editor == "action":
            # Stateless action button — no value is stored.
            # validator_args["button_label"]  → button text (default "Action")
            # validator_args["action_handler"] → callable(); called on click
            args    = spec.validator_args or {}
            label   = args.get("button_label", "Action")
            handler = args.get("action_handler")
            btn = QPushButton(label)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            if tip: btn.setToolTip(tip)
            if callable(handler):
                btn.clicked.connect(handler)
            # Wrap in a container so width alignment matches other editors
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(0)
            h.addWidget(btn)
            h.addStretch()
            # NOT added to self._editors — no value to read/write
            return container

        # default: QLineEdit
        edit = QLineEdit()
        edit.setText(str(spec.default) if spec.default is not None else "")
        if tip: edit.setToolTip(tip)
        edit.setProperty("setting_key", spec.key)
        edit.editingFinished.connect(self._validate_one_from_sender)
        edit.textChanged.connect(self._on_any_value_change)
        #edit.setStyleSheet("QLineEdit { padding: 6px; border-radius: 6px; }")
        self._attach_qt_validator(edit, spec)

        if spec.validator in ("path_file", "path_dir"):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            h.addWidget(edit, 1)

            browse = QPushButton("Browse…")
            browse.setAutoDefault(False)
            browse.setDefault(False)
            browse.setProperty("target_key", spec.key)
            browse.clicked.connect(self._inline_browse_clicked)
            h.addWidget(browse, 0)

            if spec.validator == "path_file":
                _test_label = (spec.validator_args or {}).get("button_label", "Test…")
                testbtn = QPushButton(_test_label)
                testbtn.setAutoDefault(False)
                testbtn.setDefault(False)
                testbtn.setProperty("target_key", spec.key)
                testbtn.clicked.connect(self._inline_test_script_clicked)
                h.addWidget(testbtn, 0)

            self._editors[spec.key] = edit
            return row

        self._editors[spec.key] = edit
        return edit

    def _attach_qt_validator(self, editor: QLineEdit, spec: SettingSpec) -> None:
        vtype = spec.validator
        args = spec.validator_args or {}
        if vtype == "int":
            editor.setValidator(QIntValidator(int(args.get("min", -2_147_483_648)),
                                              int(args.get("max",  2_147_483_647)), editor))
        elif vtype in ("float", "float_range"):
            dv = QDoubleValidator(float(args.get("min", -1e12)), float(args.get("max", 1e12)),
                                  int(args.get("decimals", 6)), editor)
            dv.setNotation(QDoubleValidator.StandardNotation)
            editor.setValidator(dv)
        elif vtype == "regex":
            rx = QRegularExpression(args.get("pattern", r".*"))
            editor.setValidator(QRegularExpressionValidator(rx, editor))
        # path/custom checked on commit/save

    def _validate_one_from_sender(self) -> None:
        editor = self.sender()
        if isinstance(editor, QLineEdit):
            key = editor.property("setting_key")
            if key:
                self._validate_one(key)

    def _validate_one(self, key: str) -> bool:
        """Validate a single field by schema key (works for all editor types)."""
        spec = self._schema[key]
        if key not in self._editors:
            # Action buttons and other stateless widgets have no value to validate.
            return True
        w = self._editors[key]

        if getattr(self, "_booting", False):
            # don't validate during boot; treat as OK to avoid startup noise
            return True

        # Get a canonical string/numeric value from the editor
        if isinstance(w, QLineEdit):
            value_str = w.text().strip()
            value_num = None
        elif isinstance(w, QSpinBox):
            value_num = int(w.value())
            value_str = str(value_num)
        elif isinstance(w, QDoubleSpinBox):
            value_num = float(w.value())
            value_str = str(value_num)
        elif isinstance(w, QComboBox):
            value_str = w.currentText().strip()
            value_num = None
        elif isinstance(w, QCheckBox):
            value_str = "true" if w.isChecked() else "false"
            value_num = None
        else:
            # Unknown/unsupported widget: consider it OK
            return True

        ok = True
        msg = ""
        vtype = spec.validator
        args = spec.validator_args or {}

        def fail(message: str):
            nonlocal ok, msg
            ok, msg = False, message

        # Required check (applies to text/combo; spinboxes always have some value)
        if spec.required and isinstance(w, (QLineEdit, QComboBox)) and not value_str:
            fail(f'"{spec.label}" is required.')
        else:
            # Additional checks for text only (Qt validators already constrain spin/double ranges)
            if isinstance(w, QLineEdit):
                if vtype == "float_range" and value_str:
                    try:
                        val = float(value_str)
                        lo = float(args.get("min", -1e12))
                        hi = float(args.get("max",  1e12))
                        if not (lo <= val <= hi):
                            fail(f'"{spec.label}" must be between {lo} and {hi}.')
                    except ValueError:
                        fail(f'"{spec.label}" must be a number.')
                elif vtype == "path_file" and value_str:
                    must_exist = bool(args.get("must_exist", False))
                    if must_exist and not os.path.isfile(value_str):
                        fail(f'File for "{spec.label}" does not exist.')
                elif vtype == "path_dir" and value_str:
                    must_exist = bool(args.get("must_exist", False))
                    if must_exist and not os.path.isdir(value_str):
                        fail(f'Directory for "{spec.label}" does not exist.')

            # Custom validator (works for any editor type)
            if ok and vtype == "custom":
                func: Optional[Callable[[str], Tuple[bool, str]]] = args.get("callable")
                if func:
                    try:
                        ok, msg = func(value_str)
                    except Exception as e:
                        ok, msg = False, f'Validator error for "{spec.label}": {e}'

        # Visual feedback via dynamic property (handled by QSS above)
        w.setProperty("error", not ok)
        w.style().unpolish(w)
        w.style().polish(w)
        w.update()

        self._set_error(key, msg if not ok else "")
        return ok
    def _current_numeric_value(self, w):
        if isinstance(w, QSpinBox):
            return int(w.value())
        if isinstance(w, QDoubleSpinBox):
            return float(w.value())
        if isinstance(w, QLineEdit):
            t = w.text().strip()
            try: return float(t) if "." in t else int(t)
            except Exception: return None
        if isinstance(w, QComboBox):
            t = w.currentText().strip()
            try: return float(t) if "." in t else int(t)
            except Exception: return None
        if isinstance(w, QCheckBox):
            return int(w.isChecked())
        return None

    def _apply_dynamic_range(self, spec: SettingSpec, w: QWidget) -> None:
        if spec.editor not in ("spin", "doublespin"):
            return

        args = spec.validator_args or {}
        min_from = args.get("min_from")
        max_from = args.get("max_from")
        step_from = args.get("step_from")

        def update_range():
            # start with static fallbacks from args (if provided)
            minv = args.get("min", w.minimum() if hasattr(w, "minimum") else None)
            maxv = args.get("max", w.maximum() if hasattr(w, "maximum") else None)
            step = args.get("step", None)

            # pull live values from source editors if declared
            if min_from and (src := self._editors.get(min_from)):
                mv = self._current_numeric_value(src)
                if mv is not None: minv = mv
            if max_from and (src := self._editors.get(max_from)):
                mv = self._current_numeric_value(src)
                if mv is not None: maxv = mv
            if step_from and (src := self._editors.get(step_from)):
                sv = self._current_numeric_value(src)
                if sv is not None: step = sv

            # guard against inverted ranges
            if minv is not None and maxv is not None and float(minv) > float(maxv):
                # swap or clamp; here we clamp max to min
                maxv = minv

            # apply
            if isinstance(w, QSpinBox):
                if minv is not None and maxv is not None:
                    w.setRange(int(minv), int(maxv))
                if step is not None:
                    w.setSingleStep(int(step))
            elif isinstance(w, QDoubleSpinBox):
                if minv is not None and maxv is not None:
                    w.setRange(float(minv), float(maxv))
                if step is not None:
                    w.setSingleStep(float(step))

        # connect dependencies
        def connect_source(dep_key):
            if not dep_key or dep_key not in self._editors: return
            src = self._editors[dep_key]
            if isinstance(src, (QSpinBox, QDoubleSpinBox)):
                src.valueChanged.connect(update_range)
            elif isinstance(src, QLineEdit):
                src.textChanged.connect(lambda *_: update_range())
            elif isinstance(src, QComboBox):
                src.currentTextChanged.connect(lambda *_: update_range())
            elif isinstance(src, QCheckBox):
                src.stateChanged.connect(lambda *_: update_range())

        connect_source(min_from)
        connect_source(max_from)
        connect_source(step_from)

        # prime once the widget is built
        QTimer.singleShot(0, update_range)

    def _set_error(self, key: str, text: str) -> None:
        """Set or clear the error message for a specific field key."""
        if getattr(self, "_booting", False):
            return
        if text:
            self._error_messages[key] = text
        else:
            self._error_messages.pop(key, None)
        self._render_errors()

    def _render_errors(self) -> None:
        self._error_area.clear()
        for msg in self._error_messages.values():
            self._error_area.append(
                f"<span style='color:#ff8080'>• {msg}</span>"
            )

    def _restore_defaults_clicked(self):
        from PySide6.QtWidgets import QMessageBox
        result = QMessageBox.question(
            self,
            "Restore defaults",
            "Reset all settings to their default values?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            defaults = {k: s.default for k, s in self._schema.items()}
            self.set_values(defaults)
            self._error_area.clear()
            self._error_messages.clear()

    def _append_error(self, text: str):
        """Legacy: append a transient message with no associated key."""
        if getattr(self, "_booting", False):
            return

        if text:
            self._error_area.append(f"<span style='color:#ff8080'>• {text}</span>")

    def _inline_browse_clicked(self):
        btn: QPushButton = self.sender()
        key = btn.property("target_key")
        if not key: return
        spec = self._schema.get(key)
        if not spec: return
        edit = self._editors.get(key)
        if not isinstance(edit, QLineEdit): return
        current = edit.text().strip()
        start_dir = os.path.dirname(current) if current and os.path.exists(os.path.dirname(current)) else ""
        if spec.validator == "path_file":
            path, _ = QFileDialog.getOpenFileName(self, f"Choose file for {spec.label}", start_dir)
        elif spec.validator == "path_dir":
            path = QFileDialog.getExistingDirectory(self, f"Choose directory for {spec.label}", start_dir)
        else:
            path, _ = QFileDialog.getOpenFileName(self, f"Choose path for {spec.label}", start_dir)
        if path:
            edit.setText(path)
            self._validate_one(key)

    def _save_clicked(self):
        self._error_area.clear()
        self._error_messages.clear()
        ok_all = True
        for key in self._order:
            row = self._row_widgets.get(key)
            if row and not row.isVisible():
                continue
            if not self._validate_one(key):
                ok_all = False

        if ok_all:
            self.settingsSaved.emit(self.values())
        else:
            self._append_error("Fix the highlighted fields before saving.")

    def _cancel_clicked(self):
        self.canceled.emit()

    def _on_any_value_change(self, *args):
        # Don't check initial values until all are loaded
        if getattr(self, "_booting", False):
            return

        # live-validate only fields that use custom validators
        editor = self.sender()
        if editor in self._editors.values():
            # find key for this editor
            for k, w in self._editors.items():
                if w is editor:
                    spec = self._schema.get(k)
                    if spec and spec.validator == "custom":
                        self._validate_one(k)
                    break
        self.refresh_visibility()

    def _install_visibility_triggers(self):
        # Already connected via _create_editor for each widget.
        pass


# ---------------- Dialog wrapper ----------------

class SettingsDialog(QDialog):
    def __init__(self, schema: List[SettingSpec], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(settings_icon())
        self.widget = SettingsWidget(schema, self)
        lay = QVBoxLayout(self)
        lay.addWidget(self.widget)
        self.result_values: Optional[Dict[str, Any]] = None
        self.widget.settingsSaved.connect(self._accept_with_values)
        self.widget.canceled.connect(self.reject)

    def showEvent(self, event):
        super().showEvent(event)
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            ag  = screen.availableGeometry()
            geo = self.frameGeometry()
            x   = max(ag.left(),  min(geo.x(), ag.right()  - geo.width()))
            y   = max(ag.top(),   min(geo.y(), ag.bottom() - geo.height()))
            if x != geo.x() or y != geo.y():
                self.move(x, y)

    def set_values(self, values: Dict[str, Any]) -> None:
        self.widget.set_values(values)

    def _accept_with_values(self, values: Dict[str, Any]):
        self.result_values = values
        self.accept()


# ---------------- Settings Manager ----------------

class SettingsManager(QWidget):
    def __init__(self, schema: List[SettingSpec], path: str = "settings.json", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.schema = schema
        self.path = path
        self._defaults: Dict[str, Any] = {s.key: s.default for s in schema}
        self._values: Dict[str, Any] = dict(self._defaults)

    def get_live(self, key: str, default=None):
        """Return the current value.
        If the settings dialog is open, prefer the in-dialog (unsaved) value; otherwise return stored value.
        """
        dlg = getattr(self, "_open_dialog", None)
        if dlg is not None and getattr(dlg, "widget", None) is not None:
            try:
                return dlg.widget.values().get(key, default)
            except Exception:
                pass
        return self.get(key, default)

    def values_live(self) -> Dict[str, Any]:
        """Return the current values dict; if dialog open, reflect its current (unsaved) edits."""
        dlg = getattr(self, "_open_dialog", None)
        if dlg is not None and getattr(dlg, "widget", None) is not None:
            try:
                return dlg.widget.values()
            except Exception:
                pass
        return self.values()
    changed = Signal(dict)
    saved   = Signal(str)


    # Read-only access
    def values(self) -> Dict[str, Any]:
        return dict(self._values)

    def values_view(self):
        return MappingProxyType(self._values)

    def get(self, key: str, default=None):
        return self._values.get(key, default)

    # Mutations
    def set(self, key: str, value: Any, emit=True):
        self._values[key] = value
        if emit:
            self.changed.emit(self.values())

    def set_many(self, updates: Dict[str, Any], emit=True):
        self._values.update(updates)
        if emit:
            self.changed.emit(self.values())

    # Persistence
    def load(self) -> Dict[str, Any]:
        data = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        self._values = {**self._defaults, **data}
        self.changed.emit(self.values())
        # Now put these settings into the keywords used in the imaging routine
        if config.keywords_from_settings_fn is not None:
            config.keywords_from_settings_fn()
        return self.values()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".settings.", dir=os.path.dirname(self.path) or ".")
        os.close(fd)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._values, f, indent=2)
            shutil.move(tmp, self.path)
            self.saved.emit(self.path)
            # Now put these settings into the keywords used in the imaging routine
            if config.keywords_from_settings_fn is not None:
                config.keywords_from_settings_fn()
        finally:
            try: os.remove(tmp)
            except: pass


    def set_combo_options(self, key: str, options: list, *, keep_value: bool = True, select: 'Optional[str]' = None) -> None:
        """Update the option list for a combo-type setting.

        This updates the schema so newly created widgets use the new list.
        If an editor dialog is currently open, it also updates the live widget.
        """
        # 1) Update schema
        updated = False
        for s in self.schema:
            if s.key == key:
                s.options = [str(o) for o in options]
                updated = True
                break
        if not updated:
            raise KeyError(f"Unknown setting key: {key}")

        # 2) Update a currently-open dialog, if any
        dlg = getattr(self, "_open_dialog", None)
        if dlg is not None and getattr(dlg, "widget", None) is not None:
            try:
                dlg.widget.set_combo_options(key, options, keep_value=keep_value, select=select)
            except Exception:
                pass

    def set_many_combo_options(self, mapping: dict) -> None:
        """Bulk update multiple combo option lists in the schema (and live dialog if open)."""
        for k, opts in mapping.items():
            self.set_combo_options(k, opts)

    # Open modal editor and persist on Save
    def edit_with_widget(self, parent=None) -> bool:
        # Parent the dialog to this manager so style/props propagate
        dlg = SettingsDialog(self.schema, parent or self)
        self._open_dialog = dlg
        dlg.set_values(self._values)

        # Apply Fusion ONLY to this dialog (and its children)
        """
        fusion = QStyleFactory.create("Fusion")
        if fusion is not None:
            dlg.setStyle(fusion)
            dlg.widget.setStyle(fusion)
            # Ensure combo popups also use Fusion
            for cb in dlg.widget.findChildren(QComboBox):
                try:
                    cb.view().setStyle(fusion)
                except Exception:
                    pass
        """

        saved = {"ok": False}
        def on_saved(vals: dict):
            self.set_many(vals)
            self.save()
            saved["ok"] = True
        dlg.widget.settingsSaved.connect(on_saved)
        if dlg.exec():
            # dialog closed; clear the temporary reference
            try:
                del self._open_dialog
            except Exception:
                pass
            return saved["ok"]
        # dialog closed; clear the temporary reference
        try:
            del self._open_dialog
        except Exception:
            pass
        return False

###############################################################################
# TASK_RUNNER
###############################################################################



import threading
import traceback
from time import monotonic, sleep
from typing import Callable, Any, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot


class StopToken:
    def __init__(self, pulse_cb: Optional[Callable[[float], None]] = None):
        self._ev = threading.Event()
        self._pulse_cb = pulse_cb
        self._log_cb = None  # set by runner/worker

    def log(self, message: str, color: str = "black"):
        """Send a log message (with color) to the GUI thread safely."""
        cb = getattr(self, "_log_cb", None)
        if cb:
            cb(message, color)

    # (optional convenience helpers)
    def info(self, message: str):  self.log(message, "black")
    def ok(self, message: str):    self.log(message, "green")
    def warn(self, message: str):  self.log(message, "orange")
    def err(self, message: str):   self.log(message, "red")

    # stopping
    def request_stop(self) -> None:
        self._ev.set()

    def stop_requested(self) -> bool:
        return self._ev.is_set()

    # cooperative utilities
    def pulse(self) -> None:
        """Send a heartbeat (I'm alive)."""
        if self._pulse_cb:
            self._pulse_cb(monotonic())

    def checkpoint(self) -> bool:
        """Pulse + return whether stop was requested."""
        self.pulse()
        return self.stop_requested()

    def sleep(self, seconds: float) -> bool:
        """Sleep in small chunks; return True if stop requested during the sleep."""
        remaining = max(0.0, float(seconds))
        chunk = 0.05  # 50 ms responsiveness
        while remaining > 0.0 and not self._ev.is_set():
            s = chunk if remaining > chunk else remaining
            sleep(s)
            remaining -= s
        return self._ev.is_set()


class _LongWorker(QObject):
    """Lives in a QThread; runs the user function once."""
    heartbeat = Signal(float)   # monotonic timestamp
    result    = Signal(object)  # Any
    error     = Signal(str)     # traceback string
    started   = Signal()
    finished  = Signal()        # emitted in finally
    log       = Signal(str, str)   # <-- add this (message, color)

    def __init__(self, fn: Callable[[StopToken], Any]):
        super().__init__()
        self._fn = fn
        self._token = StopToken(self._emit_pulse)
        self._token._log_cb = lambda msg, color="black": self.log.emit(msg, color)
        self._running = False

    @Slot()
    def start(self):
        if self._running:
            return
        self._running = True
        self.started.emit()
        try:
            out = self._fn(self._token)  # run user function
            self.result.emit(out)
        except SystemExit:
            pass  # sys.exit() used as cooperative stop — swallow so Qt can
                  # process the queued thread.quit() and emit thread.finished
        except Exception:
            self.error.emit(traceback.format_exc())
        finally:
            self._running = False
            self.finished.emit()

    @Slot()
    def request_stop(self):
        self._token.request_stop()

    def _emit_pulse(self, ts: float):
        self.heartbeat.emit(ts)

class LongTaskRunner(QObject):
    result   = Signal(object)
    error    = Signal(str)
    started  = Signal()
    finished = Signal()
    stalled  = Signal(float)
    log      = Signal(str, str)  # (message, color)
    job_started  = Signal(str)   # tag
    job_finished = Signal(str)   # tag

    def __init__(
        self,
        fn: Callable[[StopToken], Any],
        *,
        stall_threshold_ms: int = 15000,
        watchdog_check_ms: int = 1000,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._fn = fn
        self._job_tag = "default"
        self._last_beat = monotonic()
        self._stall_threshold = max(100, int(stall_threshold_ms)) / 1000.0

        self._thread: Optional[QThread] = None
        self._worker: Optional[_LongWorker] = None

        # watchdog (runs in GUI thread)
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(max(250, int(watchdog_check_ms)))
        self._watchdog.timeout.connect(self._check_watchdog)

    # ---- lifecycle ---------------------------------------------------------
    def _spawn_worker(self):
        thread = QThread(self)
        thread.setObjectName(f"LongTask-{self._job_tag}")
        worker = _LongWorker(self._fn)
        worker.moveToThread(thread)

        self._thread = thread
        self._worker = worker

        # Start job when thread starts
        thread.started.connect(worker.start)

        # When job ends, quit the thread (this is the ONLY place that calls quit)
        worker.finished.connect(thread.quit)

        # UI/status signals
        worker.started.connect(self._on_started)
        worker.heartbeat.connect(self._on_heartbeat)
        worker.result.connect(self.result)
        worker.error.connect(self.error)
        worker.log.connect(self.log)
        worker.finished.connect(self._on_finished)       # stop watchdog & notify

        # Cleanup after the thread stops.  Capture thread/worker by identity so
        # a late-firing signal from a previous run cannot accidentally destroy a
        # newly-spawned pair (the race condition that prevented restart).
        def _thread_done(t=thread, w=worker):
            if self._thread is t:
                self._thread = None
            if self._worker is w:
                self._worker = None
            try: w.deleteLater()
            except Exception: pass
            try: t.deleteLater()
            except Exception: pass

        thread.finished.connect(_thread_done)

    def _cleanup_worker(self):
        """Idempotent: safe even if called twice."""
        thr = getattr(self, "_thread", None)
        wkr = getattr(self, "_worker", None)

        try:
            # Stop thread if still running (defensive)
            if thr is not None and hasattr(thr, "isRunning") and thr.isRunning():
                thr.quit()
                thr.wait()
        except Exception:
            pass

        try:
            if wkr is not None:
                wkr.deleteLater()
        except Exception:
            pass
        try:
            if thr is not None:
                thr.deleteLater()
        except Exception:
            pass

        self._thread = None
        self._worker = None

    # ---- control -----------------------------------------------------------
    def start_with(self, fn, *, job_tag: str = "default"):
        """Start a new run with a different function and optional tag."""
        if self.is_running():
            return False
        self._fn = fn
        self._job_tag = job_tag
        self.start()
        return True

    def start(self):
        if self._thread is not None and self._thread.isRunning():
            return  # already running
        # Always spawn a fresh worker/thread pair.  Reusing a finished thread
        # would restart the old worker (with the old function) and races with
        # _thread_done's cleanup, producing "QThread destroyed while running".
        self._spawn_worker()

        self._last_beat = monotonic()
        self._thread.start()
        self._watchdog.start()

    def cancel(self):
        """Politely request the job to stop; thread will quit via worker.finished."""
        try:
            if self._worker is not None:
                self._worker.request_stop()
        except Exception:
            pass

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.isRunning())

    # ---- internals ---------------------------------------------------------

    @Slot()
    def _on_started(self):
        self.started.emit()
        self.job_started.emit(self._job_tag)
        self._last_beat = monotonic()

    @Slot(float)
    def _on_heartbeat(self, ts: float):
        self._last_beat = ts

    @Slot()
    def _on_finished(self):
        # Worker signalled done; DO NOT touch self._thread here
        if self._watchdog.isActive():
            self._watchdog.stop()
        # Capture tag before emitting finished: handlers connected to finished
        # (e.g. _emergency_park_after_crash) may call start_with() and change
        # self._job_tag before job_finished fires.
        tag = self._job_tag
        self.finished.emit()         # let UI flip buttons
        self.job_finished.emit(tag)

    @Slot()
    def _check_watchdog(self):
        late = monotonic() - self._last_beat
        if late > self._stall_threshold:
            self.stalled.emit(late)
            # optional: auto-cancel or restart
            # self.cancel()

    def __del__(self):
        try:
            self._cleanup_worker()
        except Exception:
            pass

def park_job(token: StopToken):
    token.info(logtime()+"Parking telescope…")
    if token.checkpoint(): return {"status": "cancelled"}
    # Ensure scope is connected before issuing park — without this the
    # ParkAndDoNotDisconnect command hangs if the scope is not connected.
    if connectscope():
        token.err(logtime() + "Park aborted: could not connect to scope.")
        return {"status": "error"}
    # issue park (async so we can poll and remain cancellable)
    TSXSendTry("sky6RASCOMTele.Asynchronous = true;sky6RASCOMTele.ParkAndDoNotDisconnect();sky6RASCOMTele.Asynchronous = false")
    token.info(logtime()+"Park command sent; turning coolers off...")
    turncoolingoff()

    # Poll until parked or cancelled
    for _ in range(3000):  # up to ~300s
        if token.sleep(0.1):     # responsive cancel
            return {"status": "cancelled"}
        token.pulse()            # heartbeat while waiting
        if TSXSendTry("sky6RASCOMTele.IsParked()")[0] == "true": break
    token.ok(logtime()+"Park complete.")
    return {"status": "ok"}


###############################################################################
# POLAR_UI
###############################################################################



import os
from typing import Optional

from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)




# Colours for the screening verdict in the Settings message pane.
_SCREEN_COLOURS = {"good": "#1a7f37", "warn": "#c07a00", "error": "#d1453b"}


def _layout_holding(layout, widget):
    """The layout that directly contains widget, searched depth first.

    The Settings dialog is built by the shared settings module, so its footer
    is not exposed by name.  Finding it this way adds the help button without
    a change to a module the scheduler and planner also ship.
    """
    if layout is None:
        return None
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is widget:
            return layout
        found = _layout_holding(item.layout(), widget)
        if found is not None:
            return found
    return None


# Shown by the Settings dialog's "Choosing the points..." button.  This is the
# standing explanation of what the three alignment settings do; the message
# pane only says what is wrong with the current values.
_POINT_HELP = """\
<p style='margin-top:0'>The tool images the same declination at two different
hour angles and works out where the mount's axis really points from how the
sky moved between them.</p>

<p><b>Declination</b> &mdash; where both images are taken.<br>
<b>First and second hour angle</b> &mdash; how far east (&minus;) or west (+)
of the meridian each one is taken, in hours.  The mount slews to the first,
images, slews to the second, images, and then reports the correction while
standing at the second point.</p>

<p><b>A good pair:</b></p>
<ol>
<li><b>Both points visible.</b>  Checked against your custom horizon if you
have one, so a point behind a tree is caught even when it is well up.  Points
below the skyline cannot be saved.</li>
<li><b>Both hour angles the same sign.</b>  Opposite signs put the images
either side of the meridian, so the mount flips between them and the tube
changes sides of the pier.  The solve reads the change in flexure as
misalignment.</li>
<li><b>Three to five hours apart.</b>  This is where the solve gets its
leverage, and the error falls off as one over the separation: about 16&Prime;
of axis error at 4&nbsp;h against 63&Prime; at 1&nbsp;h.  Much beyond five
hours the two points sit at very different altitudes, so flexure differs more
between them.</li>
<li><b>The second point clear of the zenith and of due east and west.</b>
Only the second matters &mdash; that is where the mount stands while you
adjust it.  Near the zenith, turning the azimuth bolts does not move the
star; near the east&ndash;west axis, turning the altitude bolts does not.
Either way one of the two adjustments stops telling you anything, and the
correction reported is magnified.</li>

<li><b>Work away from the meridian, not towards it.</b>  The correction is
read where the mount ends up, so the same two hour angles taken in the other
order can be two or three times worse.</li>
<li><b>Declination well away from the celestial equator.</b>  Two axes fit
both images equally well and the tool picks the one nearer the pole.  Near the
equator they sit at nearly equal distances and that choice stops being
reliable.</li>
</ol>

<p>A declination of 60&deg; with hour angles of &minus;1&nbsp;h and
&minus;5&nbsp;h suits most northern sites.  The mirror image, +1&nbsp;h to
+5&nbsp;h, is just as good where the western sky is the clearer one.  The message pane below shows what your own choice will
achieve: <i>10&Prime; of plate-solve error or flexure would put the polar axis
about 16&Prime; out</i> &mdash; that is the floor on how well the alignment
can be nulled, not the alignment you will end up with.</p>
"""


class _LogSink(QObject):
    """Minimal sink for utils.output().

    polar_align reports progress through output(), which writes to
    utils._log_sink.  The scheduler's AppLogger would do, but it lives in
    ui_widgets alongside a lot of scheduler-only table machinery; this is the
    whole of what the polar tool needs.  The signal carries the message to the
    GUI thread, since output() is called from the worker.
    """
    message = Signal(str, str)   # (text, colour)

    def log(self, text: str, colour: str = "black") -> None:
        self.message.emit(text, colour)


# Whether TheSkyX has a filter wheel, established once at startup.  None means
# it could not be established, because TheSkyX was not running, and then a
# saved filter is still honoured: the wheel is probably there and the run will
# say so if it is not.  False is a positive answer -- TheSkyX is running and
# has no wheel selected -- and then a filter saved from an earlier session is
# ignored rather than acted on, or the run would open by trying to connect a
# wheel that does not exist.  The saved value is left alone on disk so that it
# comes back with the hardware.
_wheel_present: Optional[bool] = None


class _Site:
    """Latitude and custom horizon, shared with the settings validators.

    The validators are plain callables stored in the schema, with no route
    back to the window, so what they need lives here instead.
    """

    lat: Optional[float] = None
    horizon: Optional[list] = None          # .hrz altitudes, or None

    @classmethod
    def limit(cls, az: float) -> float:
        """Horizon altitude at this azimuth; 0 with no custom horizon."""
        if not cls.horizon:
            return 0.0
        return _horizon_limit(cls.horizon, az)


# Shown in place of a filter name when the wheel should be left alone.  A
# blank combo entry would look like a missing value rather than a choice.
_FILTER_ANY = "(leave unchanged)"

# Floor for the icon between the two readings, in logical pixels; normally it
# takes its size from the indicators either side of it.
_BADGE_MIN_PX = 96


def build_polar_schema() -> list:
    """Settings for the polar alignment tool.

    These were hand-edited constants at the top of PAUI.py; the image scale in
    particular changes with the site and had to be edited in the source.
    """
    return [
        SettingSpec(key="pa_cam_duration", label="Exposure",
            default=4.0, group="Camera",
            tooltip="Exposure for each plate-solve image.",
            editor="doublespin", validator="float_range",
            validator_args={"min": 0.1, "max": 120.0, "decimals": 1, "step": 1},
            suffix="s", required=True),

        SettingSpec(key="pa_cam_binning", label="Binning",
            default=4, group="Camera",
            tooltip="Camera binning for the plate-solve images. Higher binning "
                    "solves faster but needs the scale below to match.",
            editor="spin", validator="int",
            validator_args={"min": 1, "max": 8}, required=True),

        SettingSpec(key="pa_cam_scale", label="Image scale",
            default=6.764, group="Camera",
            tooltip="Arcseconds per pixel AT THE BINNING ABOVE — used for plate "
                    "solving. Site- and camera-specific; change it when you "
                    "move rigs or alter binning.",
            editor="doublespin", validator="float_range",
            validator_args={"min": 0.1, "max": 60.0, "decimals": 3, "step": 1},
            suffix="\"/px", required=True),

        SettingSpec(key="pa_cam_filter", label="Filter",
            default=_FILTER_ANY, group="Camera",
            tooltip="Filter to use for plate solving. The list is read from "
                    "the filter wheel when the window opens; choose "
                    f"{_FILTER_ANY} to image with whichever filter is "
                    "already in place.",
            editor="combo", options=[_FILTER_ANY]),

        SettingSpec(key="pa_cam_subframe", label="Frame area",
            default="Centre quarter", group="Camera",
            tooltip="Cropping the frame speeds up plate solving on large "
                    "cameras. Use the full frame if solves are failing.",
            editor="combo",
            options=["Full frame", "Centre half", "Centre quarter"]),

        SettingSpec(key="pa_dec", label="Declination",
            default=60.0, group="Alignment",
            tooltip="Declination to take both images at. Keep well away "
                    "from the celestial equator, and away from your latitude "
                    "\u2014 at that declination the second point passes close "
                    "to the zenith.",
            editor="doublespin", validator="float_range",
            validator_args={"min": -80.0, "max": 80.0, "decimals": 1, "step": 5},
            suffix="°", required=True),

        SettingSpec(key="pa_ha1", label="First hour angle",
            default=-1.0, group="Alignment",
            tooltip="Hour angle of the first image, west of the meridian "
                    "if positive.",
            editor="doublespin", validator="float_range",
            validator_args={"min": -11.0, "max": 11.0, "decimals": 1, "step": 1},
            suffix="h", required=True),

        SettingSpec(key="pa_ha2", label="Second hour angle",
            default=-5.0, group="Alignment",
            tooltip="Hour angle of the second image. Three to five hours "
                    "from the first, and the same sign, gives the best "
                    "result: wider separations leave the two points at very "
                    "different altitudes, where flexure differs more. Work "
                    "away from the meridian, not towards it \u2014 the "
                    "correction is measured here, and it is read more "
                    "cleanly low than high.",
            editor="doublespin", validator="float_range",
            validator_args={"min": -11.0, "max": 11.0, "decimals": 1, "step": 1},
            suffix="h", required=True),

        SettingSpec(key="pa_keep_files", label="Keep image files",
            default=False, group="Advanced",
            tooltip="Keep the FITS and .SRC files instead of deleting them "
                    "after each solve.",
            editor="combo", options=["No", "Yes"]),

        SettingSpec(key="pa_compare_refraction", label="Log refraction check",
            default=False, group="Advanced",
            tooltip="Also compute Alt/Az via TheSkyX (which applies "
                    "refraction) and log the difference against the local "
                    "calculation. Diagnostic only — costs one extra call per "
                    "conversion.",
            editor="combo", options=["No", "Yes"]),
    ]


_SUBFRAME_VALUES = {"Full frame": 1, "Centre half": 2, "Centre quarter": 4}


def apply_polar_settings(settings: SettingsManager) -> None:
    """Push saved settings into config for the worker to read."""
    config.PA_CAM_DURATION = settings.get("pa_cam_duration")
    config.PA_CAM_BINNING  = settings.get("pa_cam_binning")
    config.PA_CAM_SCALE    = settings.get("pa_cam_scale")
    chosen                 = settings.get("pa_cam_filter")
    if _wheel_present is False:
        chosen = _FILTER_ANY
    config.PA_CAM_FILTER   = "" if chosen in (None, "", _FILTER_ANY) else chosen
    config.PA_CAM_SUBFRAME = _SUBFRAME_VALUES.get(
        settings.get("pa_cam_subframe"), 4)
    config.PA_DEC          = settings.get("pa_dec")
    config.PA_HA1          = settings.get("pa_ha1")
    config.PA_HA2          = settings.get("pa_ha2")
    config.PA_KEEP_FILES   = settings.get("pa_keep_files") == "Yes"
    config.PA_COMPARE_REFRACTION = settings.get("pa_compare_refraction") == "Yes"

# Correction thresholds (degrees) that colour the indicators.  Green is
# "good enough to stop", amber "keep going", red "a long way out".
_GOOD_DEG  = 0.17    # ~10 arcmin
_CLOSE_DEG = 1.0


def _correction_colour(value: float) -> str:
    """Traffic-light colour for a remaining correction, in degrees."""
    if abs(value) > _CLOSE_DEG:
        return "#d1453b"
    if abs(value) > _GOOD_DEG:
        return "#d97706"
    return "#1f9d57"


class _Indicator(QWidget):
    """One large glyph plus a magnitude, for altitude or azimuth."""

    # Wide enough for the longest reading the formatter produces
    # (e.g. -10° 33' 48") at the 22pt value font — without this the text is
    # silently clipped at both ends rather than eliding visibly.
    _MIN_WIDTH = 240

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(self._MIN_WIDTH)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        self._title = QLabel(title)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(
            f"font-size:11px; font-weight:700; color:{theme.monitor_label_col()};")

        self._glyph = QLabel("·")
        self._glyph.setAlignment(Qt.AlignCenter)
        self._glyph.setFont(QFont("Helvetica", 60))

        self._value = QLabel("Waiting")
        self._value.setAlignment(Qt.AlignCenter)
        self._value.setFont(QFont("Helvetica", 22))

        # Normally empty; carries "mount moving?" and the like while the
        # reading above is from an earlier image.
        self._note = QLabel("")
        self._note.setAlignment(Qt.AlignCenter)
        self._note.setStyleSheet(
            f"font-size:11px; color:{theme.log_color('orange')};")

        lay.addWidget(self._title)
        lay.addWidget(self._glyph)
        lay.addWidget(self._value)
        lay.addWidget(self._note)

    def set_correction(self, value: float, positive_glyph: str,
                       negative_glyph: str) -> None:
        colour = _correction_colour(value)
        self._note.setText("")
        self._glyph.setText(positive_glyph if value > 0 else negative_glyph)
        self._glyph.setStyleSheet(f"color:{colour};")
        self._value.setText(DegFormat(abs(value)))
        self._value.setStyleSheet(f"color:{colour}; font-weight:600;")

    def set_stale(self, note: str) -> None:
        """Keep the reading but mark it as no longer current.

        An image taken while the mount is being adjusted will not solve, and
        that is the normal state of affairs during alignment rather than a
        fault.  The last good correction is exactly what the user is turning
        the bolts towards, so it stays on screen — dimmed, and captioned with
        why — instead of being replaced by an error they cannot act on.
        """
        dim = theme.monitor_label_col()
        self._glyph.setStyleSheet(f"color:{dim};")
        self._value.setStyleSheet(f"color:{dim}; font-weight:600;")
        self._note.setText(note)

    def set_message(self, text: str, colour: str = "") -> None:
        """Show a word instead of a measurement (Waiting, Error, …)."""
        self._note.setText("")
        self._glyph.setText("·")
        self._glyph.setStyleSheet(f"color:{colour or theme.monitor_label_col()};")
        self._value.setText(text)
        self._value.setStyleSheet(f"color:{colour or theme.monitor_label_col()};")


class PolarAlignWindow(QDialog):
    """Main window for the polar alignment tool."""

    # Emitted from the worker thread; queued to the GUI thread by Qt.
    adjustment = Signal(float, float)
    staleness  = Signal(str)      # a loop image did not solve
    failure    = Signal(str)      # expected failure, already explained

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Polar Alignment")
        self.setWindowIcon(polar_app_icon())
        self.setMinimumSize(640, 480)

        # Asked once per session, not once per run — see _on_start.
        self._pointing_confirmed = False
        # True once a run has reported a failure, so that the
        # finished handler does not clear it off the gauges.
        self._failed = False
        # Site latitude, read from TheSkyX when the filter wheel is; needed to
        # turn a declination and hour angle into a position in the sky.  None
        # until TheSkyX has answered.
        self._lat: Optional[float] = None

        # Own settings file so the tool can be installed beside the scheduler
        # without the two overwriting each other's preferences.
        self._settings = SettingsManager(
            build_polar_schema(),
            path=os.path.expanduser("~/.tsxpolar.json"),
        )
        self._settings.load()
        apply_polar_settings(self._settings)

        self._build_ui()

        # polar_align reports through utils.output(); route that here.
        self._sink = _LogSink()
        self._sink.message.connect(self._append_log)
        utils._log_sink = self._sink

        # First line in the log, before anything that can go wrong: a version
        # in a screenshot or a pasted log is what makes a bug report usable,
        # and the title bar deliberately does not carry one.
        self._append_log(f"Polar Alignment v{config.POLAR_VERSION}")

        # Offer the real filter names in Settings, now that the log exists to
        # report what was found.
        self._load_filter_list()

        self._runner = LongTaskRunner(self._job, parent=self)
        self._runner.log.connect(self._append_log)
        self._runner.started.connect(self._on_started)
        self._runner.finished.connect(self._on_finished)
        self._runner.error.connect(self._on_error)
        self.adjustment.connect(self._on_adjustment)
        self.staleness.connect(self._on_stale)
        self.failure.connect(self._on_error)

    # ── construction ────────────────────────────────────────────────────

    def _badge(self) -> QLabel:
        """The app icon, sitting between the two readings as PAUI.py had it.

        Sized from the indicators beside it rather than to a fixed number, so
        it stays in proportion if their fonts ever change.  That lands near
        the art's own 150 pixels, which is as large as it wants to be drawn.

        Rendered at the screen's device pixel ratio rather than scaled up
        afterwards: asking the icon for the size actually needed keeps one
        resampling step instead of two.
        """
        side  = max(_BADGE_MIN_PX, self._alt.sizeHint().height())
        label = QLabel()
        dpr   = self.devicePixelRatioF() or 1.0
        px    = polar_app_icon().pixmap(
            QSize(round(side * dpr), round(side * dpr)))
        px.setDevicePixelRatio(dpr)
        label.setPixmap(px)
        label.setAlignment(Qt.AlignCenter)
        return label

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # Indicators
        row = QHBoxLayout()
        row.setSpacing(24)
        self._alt = _Indicator("ALTITUDE")
        self._az  = _Indicator("AZIMUTH")
        row.addStretch()
        row.addWidget(self._alt)
        row.addWidget(self._badge(), 0, Qt.AlignVCenter)
        row.addWidget(self._az)
        row.addStretch()
        frame = QFrame()
        frame.setObjectName("indicators")
        frame.setLayout(row)
        frame.setStyleSheet(
            "QFrame#indicators { border:1px solid #e2e6ec; border-radius:6px; }")
        outer.addWidget(frame)

        # Log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "QTextEdit { border:1px solid #e2e6ec; border-radius:4px; "
            "  font-size:11px; }")
        outer.addWidget(self._log, stretch=1)

        # Buttons
        buttons = QHBoxLayout()
        self._btn_start = QPushButton("Start")
        self._btn_start.setObjectName("primary")
        self._btn_stop  = QPushButton("Stop")
        self._btn_stop.setEnabled(False)
        self._btn_clear = QPushButton("Clear")
        self._btn_settings = QPushButton("⚙  Settings…")
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_clear.clicked.connect(self._log.clear)
        self._btn_settings.clicked.connect(self._on_settings)
        buttons.addWidget(self._btn_start)
        buttons.addWidget(self._btn_stop)
        buttons.addWidget(self._btn_clear)
        buttons.addStretch()
        buttons.addWidget(self._btn_settings)
        outer.addLayout(buttons)

    # ── worker ──────────────────────────────────────────────────────────

    def _job(self, token) -> None:
        """Runs on the worker thread — must not touch widgets directly."""
        try:
            self._run_polar_align(token)
        except PolarAlignError as exc:
            # These carry a message written for the user and are raised for
            # things that genuinely happen — no stars, no solve, TheSkyX busy.
            # A traceback would bury that message in machinery the user can do
            # nothing about.  Anything else still propagates and is reported
            # with its traceback, because it means a bug.
            self.failure.emit(str(exc))

    def _run_polar_align(self, token) -> None:
        run_polar_align(
            token,
            exposure=float(config.PA_CAM_DURATION),
            binning=int(config.PA_CAM_BINNING),
            scale=float(config.PA_CAM_SCALE),
            subframe=int(config.PA_CAM_SUBFRAME),
            filter_name=str(config.PA_CAM_FILTER),
            pa_dec=float(config.PA_DEC),
            ha1=float(config.PA_HA1),
            ha2=float(config.PA_HA2),
            keep_files=bool(config.PA_KEEP_FILES),
            compare_refraction=bool(config.PA_COMPARE_REFRACTION),
            # Signal, not a direct call: this fires on the worker thread and
            # Qt queues it across to the GUI thread.
            on_adjustment=self.adjustment.emit,
            on_stale=self.staleness.emit,
        )

    # ── slots ───────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        # TPoint corrections would move the mount between the two images and
        # invalidate the solve, so confirm once before the first run.
        if not self._pointing_confirmed:
            answer = QMessageBox.question(
                self, "Pointing corrections",
                "Have you disabled TPoint pointing corrections?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self._append_log(
                    logtime() + "Disable pointing corrections before continuing.",
                    "orange")
                return
            self._pointing_confirmed = True

        self._alt.set_message("Waiting")
        self._az.set_message("Waiting")
        self._append_log(logtime() + "Starting polar alignment routine.")
        self._failed = False
        self._runner.start_with(self._job, job_tag="polar")

    def _on_stop(self) -> None:
        self._append_log(logtime() + "Completing current task, then stopping.")
        self._btn_stop.setEnabled(False)
        self._runner.cancel()

    def _on_started(self) -> None:
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_settings.setEnabled(False)

    def _on_finished(self) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_settings.setEnabled(True)
        # finished is emitted from a finally, so it arrives after error and
        # would otherwise wipe the reason the run stopped off the gauges.
        if self._failed:
            return
        self._alt.set_message("Waiting")
        self._az.set_message("Waiting")

    def _on_error(self, message: str) -> None:
        self._failed = True
        self._append_log(logtime() + message, "red")
        self._alt.set_message("Error", "#d1453b")
        self._az.set_message("Error", "#d1453b")

    def _on_stale(self, reason: str) -> None:
        """An image in the loop did not solve; the gauges are out of date."""
        self._alt.set_stale(reason)
        self._az.set_stale(reason)

    def _on_adjustment(self, theta: float, phi: float) -> None:
        # theta > 0 means the axis must come down; phi > 0 counter-clockwise.
        self._alt.set_correction(theta, "↓", "↑")
        self._az.set_correction(phi, "⟲", "⟳")

    def _load_filter_list(self) -> None:
        """Read the wheel's filter names and offer them in Settings.

        Best effort by design: this runs at startup, when TheSkyX may not be
        open and there may be no filter wheel at all, and neither is a reason
        to complain.  Whatever is already saved stays selectable even when it
        cannot be confirmed, so starting without TheSkyX does not quietly
        discard a filter the user chose earlier.
        """
        saved   = self._settings.get("pa_cam_filter")
        options = [_FILTER_ANY]

        if not tsx_available():
            self._append_log(
                logtime() + "TheSkyX is not running, so the filter list could "
                "not be read.  Settings will offer only the saved filter.",
                "orange")
        else:
            try:
                names = filter_names()
            except Exception as exc:                  # noqa: BLE001
                names = []
                self._append_log(
                    logtime() + f"Could not read the filter names: {exc}",
                    "orange")
            global _wheel_present
            _wheel_present = bool(names)
            if names:
                options += names
                self._append_log(logtime() + "Filter wheel: " + ", ".join(names))
            else:
                self._append_log(
                    logtime() + "No filter wheel found \u2014 imaging with "
                    "whichever filter is in place.")
                if saved not in (None, "", _FILTER_ANY):
                    self._append_log(logtime() + (
                        f"The saved filter ({saved}) will be ignored while "
                        "there is no wheel.  It is still in Settings and will "
                        "be used again if one appears."), "orange")
                # config was filled from the saved settings before the wheel
                # was known; redo it now that it is.
                apply_polar_settings(self._settings)
            # We are already talking to TheSkyX, so collect the latitude too:
            # without it the alignment points cannot be screened until a run
            # starts, which is too late to be useful.
            try:
                self._lat = LatLongLstUT()[0]
                _Site.lat = self._lat
            except Exception as exc:                  # noqa: BLE001
                self._append_log(
                    logtime() + f"Could not read the site latitude: {exc}",
                    "orange")

        # The custom horizon is a file, so it is worth having whether or not
        # TheSkyX is running.
        _Site.horizon = load_horizon()
        if _Site.horizon:
            self._append_log(logtime() + (
                f"Custom horizon loaded: {len(_Site.horizon)} points, "
                f"{min(_Site.horizon):.0f}\N{DEGREE SIGN} to "
                f"{max(_Site.horizon):.0f}\N{DEGREE SIGN}."))

        # With no wheel there is nothing to choose between, so take the row
        # out of the dialog rather than offer a list of one.
        has_wheel = len(options) > 1
        for spec in self._settings.schema:
            if spec.key == "pa_cam_filter":
                spec.visible = has_wheel
                break

        if saved and saved not in options:
            options.append(saved)

        try:
            self._settings.set_combo_options("pa_cam_filter", options,
                                             keep_value=True)
        except Exception as exc:                      # noqa: BLE001
            self._append_log(
                logtime() + f"Could not update the filter list: {exc}", "orange")

    # Keys whose values decide where the two alignment points land.
    _POINT_KEYS = ("pa_dec", "pa_ha1", "pa_ha2")

    def _on_settings(self) -> None:
        # SettingsManager builds the dialog from its own schema, seeds it with
        # the current values and writes them back on Save, so there is nothing
        # to re-read afterwards — only to re-apply.
        #
        # The screening has to be attached from inside the dialog's own event
        # loop, since edit_with_widget blocks until it closes.  A zero-delay
        # timer fires as soon as that loop starts running.
        QTimer.singleShot(0, self._attach_screening)
        if self._settings.edit_with_widget(self):
            apply_polar_settings(self._settings)

    def _attach_screening(self) -> None:
        """Report on the alignment points inside the open Settings dialog.

        Shown there rather than in the main log because that is where the
        numbers are chosen: it is worth knowing what a declination and pair of
        hour angles will achieve while they can still be changed, not once the
        mount is already slewing.
        """
        dlg = getattr(self._settings, "_open_dialog", None)
        if dlg is None or getattr(dlg, "widget", None) is None:
            return
        widget = dlg.widget

        def refresh() -> None:
            self._screen_into(widget)

        for key in self._POINT_KEYS:
            editor = widget._editors.get(key)
            signal = getattr(editor, "valueChanged", None)
            if signal is not None:
                signal.connect(lambda *_: refresh())

        # Refuse to save points that cannot be observed at all.  Done by
        # taking over the Save button rather than through the per-field
        # validators, which already carry the range checks and take one value
        # each, where this needs the declination and both hour angles together.
        button = getattr(widget, "_save_btn", None)
        if button is not None:
            try:
                button.clicked.disconnect(widget._save_clicked)
            except (TypeError, RuntimeError):
                pass                       # never connected; nothing to undo
            button.clicked.connect(lambda: self._guarded_save(widget))

        self._add_help_button(widget)
        refresh()

    def _point_values(self, widget) -> Optional[tuple[float, float, float]]:
        """The declination and the two hour angles as the dialog has them."""
        try:
            return (float(widget._editors["pa_dec"].value()),
                    float(widget._editors["pa_ha1"].value()),
                    float(widget._editors["pa_ha2"].value()))
        except (KeyError, AttributeError, TypeError, ValueError):
            return None

    def _screening(self, widget) -> list[tuple[str, str]]:
        """Screen the dialog's current points; empty if they cannot be read.

        The latitude is fetched once and kept: it decides where a declination
        and hour angle land in the sky, and without it nothing can be judged.
        """
        if self._lat is None:
            if not tsx_available():
                return []                  # nothing to check against yet
            try:
                self._lat = LatLongLstUT()[0]
            except Exception:              # noqa: BLE001
                return []

        values = self._point_values(widget)
        if values is None:
            return []
        dec, ha1, ha2 = values
        horizon = _Site.limit if _Site.horizon else None
        return screen_geometry(self._lat, dec, ha1, ha2, horizon=horizon)

    def _guarded_save(self, widget) -> None:
        """Save, unless the points cannot work at all.

        Done by taking over the Save button rather than through the per-field
        validators, which take one value each where this needs the declination
        and both hour angles together.
        """
        blocked = [note for level, note in self._screening(widget)
                   if level == "error"]
        if not blocked:
            widget._save_clicked()
            return
        area = getattr(widget, "_error_area", None)
        if area is not None:
            area.clear()
            area.append("<b style='color:#d1453b'>These points cannot be "
                        "used</b>")
            for note in blocked:
                area.append(f"<span style='color:#d1453b'>• {note}</span>")

    def _screen_into(self, widget) -> None:
        """Write the verdict on the dialog's current values into its pane."""
        area = getattr(widget, "_error_area", None)
        if area is None:
            return
        notes = self._screening(widget)
        if not notes:
            return

        area.clear()
        for level, note in notes:
            colour = _SCREEN_COLOURS.get(level, "#5b6472")
            bullet = "" if level == "good" else "• "
            area.append(f"<span style='color:{colour}'>{bullet}{note}</span>")

    def _add_help_button(self, widget) -> None:
        """Put a help button in the dialog footer, beside Restore defaults.

        The screening says what is wrong with a choice; this says what the
        three settings mean and what a good pair looks like, which is what
        someone meeting the dialog for the first time actually needs.
        """
        anchor = getattr(widget, "_defaults_btn", None)
        if anchor is None or getattr(widget, "_pa_help_btn", None) is not None:
            return
        footer = _layout_holding(widget.layout(), anchor)
        if footer is None or not hasattr(footer, "insertWidget"):
            return

        button = QPushButton("Choosing the points…")
        button.setAutoDefault(False)
        button.setDefault(False)
        button.clicked.connect(self._show_point_help)
        footer.insertWidget(footer.indexOf(anchor) + 1, button)
        widget._pa_help_btn = button

    def _show_point_help(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Choosing the alignment points")
        box.setTextFormat(Qt.RichText)
        box.setText(_POINT_HELP)
        box.setStandardButtons(QMessageBox.Close)
        box.exec()


    # ── logging ─────────────────────────────────────────────────────────

    def _append_log(self, message: str, colour: str = "black") -> None:
        self._log.setTextColor(QColor(theme.log_color(colour)))
        self._log.append(message)
        self._log.setTextColor(QColor(theme.log_color("black")))
        bar = self._log.verticalScrollBar()
        bar.setValue(bar.maximum())

###############################################################################
# __MAIN__ ENTRY POINT
###############################################################################



import sys

from PySide6.QtWidgets import QApplication, QMessageBox



def _require_theskyx() -> None:
    """Refuse to open without TheSkyX, offering a retry rather than a relaunch.

    Every useful thing this tool does is a TheSkyX call, so a window without
    one can only disappoint: the filter list is unread, the alignment points
    cannot be screened, and Start fails on the first slew.

    It fails badly, too.  That first call goes through TSXSendTry, which reads
    a dead connection as TheSkyX having crashed mid-run: it sends mail, kills
    and relaunches TheSkyX, and exits the process.  That is the right reflex
    for the scheduler running unattended all night, and quite the wrong one
    here, where the usual cause is simply not having opened TheSkyX yet.

    So ask first, with a plain socket, and say what to do about it.  Retry
    rather than quit outright: the fix is to start a program that is already
    on the screen, and making the user launch this one again afterwards would
    be a poor reward for it.
    """

    while not tsx_available():
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("TheSkyX not found")
        box.setText("Polar Alignment needs TheSkyX, which is not answering.")
        box.setInformativeText(
            "Nothing replied on port 3040 of this machine.  Check that "
            "TheSkyX is running here, and that its TCP server is switched on "
            "and listening on port 3040.\n\n"
            "Start TheSkyX, then choose Retry.")
        retry = box.addButton("Retry", QMessageBox.AcceptRole)
        box.addButton("Quit", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not retry:
            sys.exit(1)


def _standalone_main() -> None:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "mcgillca.TSXSPolarAlignment.1"
        )

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Polar Alignment")
    app.setOrganizationName("mcgillca")
    app.setQuitOnLastWindowClosed(True)

    app.setWindowIcon(polar_app_icon())   # title bar and taskbar

    config.standalone = True

    # Before the window: everything in it depends on TheSkyX.
    _require_theskyx()

    window = PolarAlignWindow()
    # No version in the title — it would date every manual screenshot.  The
    # version is logged at startup and shown in the Settings dialog.
    window.setWindowTitle("Polar Alignment")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    _standalone_main()
