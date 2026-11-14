# KamCam

> Hello! KamCam is a Python project I've been working on.
>
> KamCam creates a virtual camera using **scrcpy** as a mainframe for connecting through USB or Wi-Fi to the PC. I'm still working on it, so please **AWAIT PROGRESS!!!**

---

## What it does

Turns your Android phone into a virtual webcam. It pipes the phone's screen or camera feed through `scrcpy` to your PC, which any app can then use as a normal camera — OBS, Discord, Zoom, or any streaming software.

Because browsers and streaming apps often block direct hardware access, KamCam includes a bridge to OBS Virtual Camera, allowing you to use your phone as a high-quality webcam.

## Features

- Stream phone screen or camera to your PC as a standard webcam
- Dual scripts: `KamCam.py` for high-speed USB, `KamCamIP.py` for wireless Wi-Fi
- Toggle hardware decoding (GPU or CPU)
- Toggle audio capture on or off
- Adjustable crop — hide status bars and phone UI from the feed
- Hide the background Python console window for a clean desktop
- Auto-detect phone resolution via `adb`
- Simple Tkinter GUI, no terminal required to operate

## Requirements

- Windows (or Linux with `v4l2loopback` kernel module)
- `scrcpy` 5.0 or newer
- `adb` (from `android-tools`)
- Python 3.10+ with Tkinter
- An Android phone with USB debugging enabled
- OBS Studio (Required to bridge the feed as a Virtual Camera to Discord/Zoom)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/xardbazz/KamCam.git
cd KamCam
```

### 2. Folder Structure

The repository is split into two main folders so you can run a USB camera and a Wi-Fi camera at the same time without the `adb` servers conflicting.

- `USB and IP/` — Contains the `adb` and `scrcpy` executables used by `KamCam.py`
- `IP/` — Contains the `adb` and `scrcpy` executables used by `KamCamIP.py`

Make sure your `.exe` files are placed inside these respective folders.

### 3. Install Python dependencies

If you are on Linux, install the system packages. If you are on Windows, ensure Python is installed.

```bash
sudo pacman -S scrcpy android-tools v4l2loopback-dkms python tk
```

### 4. Running the scripts

Run the script based on your desired connection method.

For USB connections:

```bash
python KamCam.py
```

For Wi-Fi connections:

```bash
python KamCamIP.py
```

### 5. How to use it as a webcam in Discord or Zoom

`scrcpy` opens a window, it does not natively create a Windows DirectShow device. To use it as a webcam:

1. Open **OBS Studio**
2. Add a **Window Capture** source and select the `scrcpy` feed window
3. Click **Start Virtual Camera** in OBS
4. Select **OBS Virtual Camera** in Discord, Zoom, or Teams

---

## Custom OBS Overlay

This repository also contains the code for the custom audio-reactive OBS overlay (WebGL Fluid Simulation + Visualizer).

**IMPORTANT:** The custom `logo.png` used in the visualizer is the intellectual property of the developer and is not included in this repository. You must create and place your own `models/logo.png` file for the overlay to work correctly. See the `overlay` directory for specific setup instructions.
