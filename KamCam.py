#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FOLDER = "USB and IP"

def find_executable(name, target_folder):
    sub = "adb" if "adb" in name else "scrcpy"
    candidates = [
        os.path.join(BASE_DIR, target_folder, sub, name),
        os.path.join(BASE_DIR, target_folder, name),
        os.path.join(BASE_DIR, sub, name),
        os.path.join(BASE_DIR, name),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return name

if platform.system() == "Windows":
    ADB_PATH = find_executable("adb.exe", TARGET_FOLDER)
    SCRCPY_PATH = find_executable("scrcpy.exe", TARGET_FOLDER)
else:
    ADB_PATH = "adb"
    SCRCPY_PATH = "scrcpy"

# ==========================================

current_target_device = ""
phone_size = {"w": 720, "h": 1280} 

def launch_app(cmd):
    if platform.system() == "Windows" and console_hidden_var.get():
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(cmd)

def verify_paths():
    msg = f"Python Script Folder:\n{BASE_DIR}\n\n"
    msg += f"Target Subfolder: {TARGET_FOLDER}\n\n"
    msg += f"Looking for ADB at:\n{ADB_PATH}\n"
    msg += f"   EXISTS: {os.path.exists(ADB_PATH) if os.path.isabs(ADB_PATH) else 'NO (using system PATH)'}\n\n"
    msg += f"Looking for scrcpy at:\n{SCRCPY_PATH}\n"
    msg += f"   EXISTS: {os.path.exists(SCRCPY_PATH) if os.path.isabs(SCRCPY_PATH) else 'NO (using system PATH)'}\n\n"
    msg += f"Console Debug Info:\n"
    if platform.system() == "Windows":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        msg += f"   Console Handle: {hwnd}\n"
        msg += f"   Toggle State: {'HIDDEN' if console_hidden_var.get() else 'VISIBLE'}"
    messagebox.showinfo("Path Verification", msg)

def get_android_sdk():
    cmd = [ADB_PATH]
    if current_target_device:
        cmd.extend(["-s", current_target_device])
    else:
        cmd.extend(["-d"])
    cmd.extend(["shell", "getprop", "ro.build.version.sdk"])
    
    try:
        out = subprocess.check_output(cmd, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        return int(out.decode("utf-8").strip())
    except FileNotFoundError:
        messagebox.showerror("ADB Not Found", f"Windows cannot find adb.exe.\n\nPath tried:\n{ADB_PATH}\n\nPlease click 'Verify Paths' to see where the app is looking.")
        return 0
    except Exception:
        return 0

def detect_orientation():
    """Detects if the phone is currently held in Portrait or Landscape."""
    cmd = [ADB_PATH]
    if current_target_device:
        cmd.extend(["-s", current_target_device])
    else:
        cmd.extend(["-d"])
    
    # METHOD 1: dumpsys window displays (Extracts current window bounds)
    try:
        out = subprocess.check_output(cmd + ["shell", "dumpsys", "window", "displays"], 
                                      timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).decode("utf-8", errors="ignore")
        import re
        # Find 'cur=1520x720' or 'init=1520x720'
        matches = re.findall(r'cur=(\d+)x(\d+)', out)
        if matches:
            w, h = map(int, matches[-1])
            if w > h:
                return "Landscape"
            elif h > w:
                return "Portrait"
            
        # Fallback: Look for mRotation=1
        for line in out.splitlines():
            if "mRotation=" in line:
                val = line.split("mRotation=")[1].split()[0]
                if val in ['1', '3']:
                    return "Landscape"
                elif val in ['0', '2']:
                    return "Portrait"
    except Exception:
        pass

    # METHOD 2: dumpsys input (Older Android fallback)
    try:
        out = subprocess.check_output(cmd + ["shell", "dumpsys", "input"], 
                                      timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).decode("utf-8", errors="ignore")
        for line in out.splitlines():
            if "SurfaceOrientation" in line:
                val = int(line.split(":")[1].strip())
                if val in [1, 3]:
                    return "Landscape"
                else:
                    return "Portrait"
    except Exception:
        pass

    # METHOD 3: wm size (Extract override size if rotated)
    try:
        out = subprocess.check_output(cmd + ["shell", "wm", "size"], 
                                      timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).decode("utf-8", errors="ignore")
        for line in out.splitlines():
            if "override size:" in line.lower() or "physical size:" in line.lower():
                dims = line.split(":")[1].strip()
                w, h = map(int, dims.split("x"))
                if w > h:
                    return "Landscape"
                elif h > w:
                    return "Portrait"
    except Exception:
        pass
        
    return "Unknown"

def btn_detect_orientation():
    ori = detect_orientation()
    if ori == "Landscape":
        camera_res_var.set("1920x1080")
        messagebox.showinfo("Orientation", "Phone detected as LANDSCAPE.\nCamera resolution set to 1920x1080.")
    elif ori == "Portrait":
        camera_res_var.set("1080x1920")
        messagebox.showinfo("Orientation", "Phone detected as PORTRAIT.\nCamera resolution set to 1080x1920.")
    else:
        messagebox.showerror("Orientation", "Could not detect phone orientation.\nEnsure USB debugging is active.")

def detect_phone_size():
    """Detects the physical screen size and adjusts it based on orientation."""
    global phone_size
    cmd = [ADB_PATH]
    if current_target_device:
        cmd.extend(["-s", current_target_device])
    else:
        cmd.extend(["-d"])
    cmd.extend(["shell", "wm", "size"])
    
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).decode("utf-8", errors="replace")
    except Exception as e:
        messagebox.showerror("Error", f"adb failed:\n{e}")
        return

    chosen = None
    for line in out.splitlines():
        line = line.strip()
        low = line.lower()
        if low.startswith("override size:"): chosen = line.split(":", 1)[1].strip()
        elif low.startswith("physical size:") and not chosen: chosen = line.split(":", 1)[1].strip()

    if not chosen or "x" not in chosen: return
    try:
        w_str, h_str = chosen.split("x", 1)
        w = int(w_str)
        h = int(h_str)
        
        # Adjust size based on orientation
        ori = detect_orientation()
        if ori == "Landscape":
            phone_size["w"] = max(w, h)
            phone_size["h"] = min(w, h)
        else:
            phone_size["w"] = min(w, h)
            phone_size["h"] = max(w, h)
            
        phone_size_label.config(text=f"Screen: {phone_size['w']} × {phone_size['h']}")
        messagebox.showinfo("Phone Size", f"Detected Size: {phone_size['w']} × {phone_size['h']} ({ori})")
    except ValueError:
        pass

def force_focus():
    cmd = [ADB_PATH]
    if current_target_device:
        cmd.extend(["-s", current_target_device])
    else:
        cmd.extend(["-d"])
    
    # Tap the center of the screen based on detected size
    cx = str(phone_size["w"] // 2)
    cy = str(phone_size["h"] // 2)
    
    cmd.extend(["shell", "input", "tap", cx, cy])
    try:
        subprocess.run(cmd, check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Focus", f"Tapped center ({cx}, {cy}) to lock focus.")
    except Exception as e:
        messagebox.showerror("Focus Error", f"Failed to trigger focus:\n{e}")

def dim_screen():
    cmd = [ADB_PATH, "-d", "shell"]
    try:
        subprocess.run(cmd + ["settings", "put", "system", "screen_brightness_mode", "0"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(cmd + ["settings", "put", "system", "screen_brightness", "1"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(cmd + ["svc", "power", "stayon", "true"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Success", "Screen dimmed to 1% and forced to stay awake.")
    except FileNotFoundError:
        messagebox.showerror("ADB Not Found", f"adb.exe not found at:\n{ADB_PATH}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to dim screen:\n{e}")

def connect_wifi():
    global current_target_device
    ip = wifi_ip_entry.get().strip()
    if not ip: return
    target = f"{ip}:5555"
    try:
        subprocess.run([ADB_PATH, "tcpip", "5555"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run([ADB_PATH, "connect", target], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        current_target_device = target
        messagebox.showinfo("Success", f"Connected to {target}")
    except FileNotFoundError:
        messagebox.showerror("ADB Not Found", f"adb.exe not found at:\n{ADB_PATH}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect:\n{e}")

def build_crop_flag():
    try:
        t = int(trim_top.get() or 0); b = int(trim_bottom.get() or 0)
        l = int(trim_left.get() or 0); r = int(trim_right.get() or 0)
    except ValueError:
        return ""
    if (t, b, l, r) == (0, 0, 0, 0): return ""
    w = phone_size["w"] - l - r; h = phone_size["h"] - t - b
    return f"--crop={w}:{h}:{l}:{t}"

def start_normal():
    crop = build_crop_flag()
    cmd = [SCRCPY_PATH, "-d"]
    if hwdec_disabled_var.get(): cmd.append("--hwdec=disabled")
    if audio_disabled_var.get(): cmd.append("--no-audio")
    
    bitrate = bitrate_var.get()
    if bitrate != "Default":
        cmd.append(f"--video-bit-rate={bitrate}")
        
    if crop: cmd.append(crop)
    try:
        launch_app(cmd)
    except FileNotFoundError:
        messagebox.showerror("scrcpy Not Found", f"scrcpy.exe not found at:\n{SCRCPY_PATH}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start scrcpy:\n{e}")

def start_camera():
    sdk = get_android_sdk()
    if sdk == 0:
        messagebox.showerror("No Device", "Could not detect phone.\n\nMake sure it is plugged in via USB and 'USB Debugging' is enabled in Developer Options.")
        return

    crop = build_crop_flag()
    cmd = [SCRCPY_PATH, "-d"]
    
    if sdk >= 31:
        cmd.extend(["--video-source=camera"])
        
        res = camera_res_var.get()
        if res != "Default":
            cmd.append(f"--camera-size={res}")
            
        fps = fps_var.get()
        if fps != "Default":
            cmd.append(f"--camera-fps={fps}")
            
    else:
        try:
            subprocess.run([ADB_PATH, "-d", "shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"], 
                           check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        except FileNotFoundError:
            messagebox.showerror("ADB Not Found", f"adb.exe not found at:\n{ADB_PATH}")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch camera app:\n{e}")
            return

    bitrate = bitrate_var.get()
    if bitrate != "Default":
        cmd.append(f"--video-bit-rate={bitrate}")

    cmd.extend(["--window-title=KamCam Feed"])
    if hwdec_disabled_var.get(): cmd.append("--hwdec=disabled")
    if audio_disabled_var.get(): cmd.append("--no-audio")
    if crop: cmd.append(crop)

    try:
        launch_app(cmd)
    except FileNotFoundError:
        messagebox.showerror("scrcpy Not Found", f"scrcpy.exe not found at:\n{SCRCPY_PATH}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start camera stream:\n{e}")

def toggle_hwdec():
    hwdec_disabled_var.set(not hwdec_disabled_var.get())
    update_toggle_ui()

def update_toggle_ui():
    if hwdec_disabled_var.get():
        btn_toggle.config(text="⚡ HW Decoding: DISABLED (CPU Mode)", bg="#f38ba8", activebackground="#f5e0dc")
    else:
        btn_toggle.config(text="⚡ HW Decoding: ENABLED (GPU Mode)", bg="#a6e3a1", activebackground="#b4befe")

def toggle_audio():
    audio_disabled_var.set(not audio_disabled_var.get())
    update_audio_ui()

def update_audio_ui():
    if audio_disabled_var.get():
        btn_audio_toggle.config(text="🔇 Audio Capture: DISABLED", bg="#f38ba8", activebackground="#f5e0dc")
    else:
        btn_audio_toggle.config(text="🔊 Audio Capture: ENABLED", bg="#a6e3a1", activebackground="#b4befe")

def toggle_console():
    if platform.system() != "Windows":
        messagebox.showinfo("Not Supported", "Console toggle only works on Windows.")
        return
    
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if not hwnd:
        messagebox.showinfo("No Console", "No console window attached to this process.\n\nThis happens if you run the script via pythonw.exe or as a compiled .exe.")
        return
    
    if console_hidden_var.get():
        ctypes.windll.user32.ShowWindow(hwnd, 5)
        console_hidden_var.set(False)
    else:
        ctypes.windll.user32.ShowWindow(hwnd, 0)
        console_hidden_var.set(True)
    
    update_console_ui()

def update_console_ui():
    if console_hidden_var.get():
        btn_console_toggle.config(text="💻 Console Window: HIDDEN", bg="#a6e3a1", activebackground="#b4befe")
    else:
        btn_console_toggle.config(text="💻 Console Window: VISIBLE", bg="#f38ba8", activebackground="#f5e0dc")

# --- App Setup ---
root = tk.Tk()
root.title("KamCam (Scrcpy)")
root.geometry("400x1020")
root.configure(bg="#1e1e2e")
root.resizable(False, False)

console_hidden_var = tk.BooleanVar(value=False)
hwdec_disabled_var = tk.BooleanVar(value=True)
audio_disabled_var = tk.BooleanVar(value=False)
camera_res_var = tk.StringVar(value="1920x1080")
bitrate_var = tk.StringVar(value="8M")
fps_var = tk.StringVar(value="30")

title = tk.Label(root, text="📷 KamCam Controls (Scrcpy)", font=("Cantarell", 14, "bold"), fg="#cdd6f4", bg="#1e1e2e")
title.pack(pady=10)

wifi_frame = tk.Frame(root, bg="#313244", bd=1, relief="solid")
wifi_frame.pack(fill="x", padx=20, pady=10)
tk.Label(wifi_frame, text="Wi-Fi Mode (Unplug USB after connecting)", fg="#a6adc8", bg="#313244", font=("Cantarell", 9, "italic")).pack(pady=(5,0))
wifi_inner = tk.Frame(wifi_frame, bg="#313244")
wifi_inner.pack(pady=5)

wifi_ip_entry = tk.Entry(wifi_inner, width=15)
wifi_ip_entry.insert(0, "192.168.1.") 
wifi_ip_entry.pack(side="left", padx=5)

btn_wifi = tk.Button(wifi_inner, text="🔗 Connect", command=connect_wifi, bg="#fab387", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat")
btn_wifi.pack(side="left")

# Detection Buttons
detect_frame = tk.Frame(root, bg="#1e1e2e")
detect_frame.pack(fill="x", padx=25, pady=(10, 2))

btn_detect_ori = tk.Button(detect_frame, text="🧭 Detect Orientation", command=btn_detect_orientation, bg="#94e2d5", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat", cursor="hand2")
btn_detect_ori.pack(side="left", padx=(0, 5))

btn_detect_size = tk.Button(detect_frame, text="📏 Detect Phone Size", command=detect_phone_size, bg="#94e2d5", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat", cursor="hand2")
btn_detect_size.pack(side="left")

phone_size_label = tk.Label(root, text=f"Screen: {phone_size['w']} × {phone_size['h']}", fg="#a6adc8", bg="#1e1e2e", font=("Cantarell", 9))
phone_size_label.pack(pady=(2, 5))

# Camera Resolution Dropdown
res_frame = tk.Frame(root, bg="#1e1e2e")
res_frame.pack(fill="x", padx=25, pady=(5, 2))
tk.Label(res_frame, text="Camera Res (WxH):", fg="#cdd6f4", bg="#1e1e2e", font=("Cantarell", 10, "bold")).pack(side="left", padx=(0, 10))
camera_res_combo = ttk.Combobox(res_frame, textvariable=camera_res_var, values=["Default", "1920x1080", "1280x720", "640x480", "1080x1920", "720x1280", "480x640"], state="readonly", width=15)
camera_res_combo.pack(side="left")

# Quality Settings (Bitrate & FPS)
quality_frame = tk.Frame(root, bg="#1e1e2e")
quality_frame.pack(fill="x", padx=25, pady=(5, 5))
tk.Label(quality_frame, text="Video Bitrate:", fg="#cdd6f4", bg="#1e1e2e", font=("Cantarell", 10, "bold")).pack(side="left")
bitrate_combo = ttk.Combobox(quality_frame, textvariable=bitrate_var, values=["4M", "8M", "16M", "24M", "32M"], state="readonly", width=6)
bitrate_combo.pack(side="left", padx=(5, 20))

tk.Label(quality_frame, text="FPS:", fg="#cdd6f4", bg="#1e1e2e", font=("Cantarell", 10, "bold")).pack(side="left")
fps_combo = ttk.Combobox(quality_frame, textvariable=fps_var, values=["15", "30", "60"], state="readonly", width=5)
fps_combo.pack(side="left", padx=(5, 0))

btn_toggle = tk.Button(root, command=toggle_hwdec, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(10, 5), ipady=4)
update_toggle_ui()

btn_audio_toggle = tk.Button(root, command=toggle_audio, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_audio_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(0, 5), ipady=4)
update_audio_ui()

btn_console_toggle = tk.Button(root, command=toggle_console, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_console_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(0, 5), ipady=4)
update_console_ui()

# Action Buttons (Verify, Focus)
action_frame = tk.Frame(root, bg="#1e1e2e")
action_frame.pack(fill="x", padx=25, pady=(0, 5))

btn_verify = tk.Button(action_frame, text="🔧 Verify Paths", command=verify_paths, bg="#f9e2af", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat", cursor="hand2")
btn_verify.pack(side="left", expand=True, fill="x", padx=(0, 2))

btn_focus = tk.Button(action_frame, text="🎯 Force Focus", command=force_focus, bg="#94e2d5", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat", cursor="hand2")
btn_focus.pack(side="left", expand=True, fill="x", padx=(2, 0))

btn_dim = tk.Button(root, text="🌑  Dim Phone Screen (1%)", command=dim_screen, bg="#45475a", fg="#cdd6f4", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_dim.pack(anchor="w", padx=25, ipadx=55, pady=(5, 15), ipady=4)

# Trim Settings
trim_frame = tk.Frame(root, bg="#1e1e2e")
trim_frame.pack(fill="x", padx=25, pady=6)

trim_top = tk.StringVar(value="0"); trim_bottom = tk.StringVar(value="0")
trim_left = tk.StringVar(value="0"); trim_right = tk.StringVar(value="0")
fields = [("Trim Top", trim_top), ("Trim Bottom", trim_bottom), ("Trim Left", trim_left), ("Trim Right", trim_right)]

for i, (label, var) in enumerate(fields):
    row, col = divmod(i, 2)
    tk.Label(trim_frame, text=label, fg="#cdd6f4", bg="#1e1e2e", font=("Cantarell", 10)).grid(row=row, column=col * 2, sticky="w", padx=(0, 6), pady=2)
    tk.Entry(trim_frame, textvariable=var, width=6).grid(row=row, column=col * 2 + 1, sticky="w", padx=(0, 20), pady=2)

btn_normal = tk.Button(root, text="🖥️  Start Window Stream", command=start_normal, bg="#89b4fa", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_normal.pack(anchor="w", padx=25, ipadx=85, pady=(15, 12), ipady=4)

btn_camera = tk.Button(root, text="📹  Start Camera Feed", command=start_camera, bg="#cba6f7", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_camera.pack(anchor="w", padx=25, ipadx=75, pady=(0, 12), ipady=4)

root.mainloop()