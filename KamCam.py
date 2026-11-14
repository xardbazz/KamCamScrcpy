#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADB_DIR = os.path.join(BASE_DIR, "adb")
SCRCPY_DIR = os.path.join(BASE_DIR, "scrcpy")

# Add both subfolders to the system PATH
os.environ["PATH"] += os.pathsep + ADB_DIR
os.environ["PATH"] += os.pathsep + SCRCPY_DIR

if platform.system() == "Windows":
    # Explicitly point to the subfolders
    ADB_EXE = os.path.join(ADB_DIR, "adb.exe")
    ADB_PATH = ADB_EXE if os.path.exists(ADB_EXE) else "adb"
    
    SCRCPY_EXE = os.path.join(SCRCPY_DIR, "scrcpy.exe")
    SCRCPY_PATH = SCRCPY_EXE if os.path.exists(SCRCPY_EXE) else "scrcpy"
else:
    ADB_PATH = "adb"
    SCRCPY_PATH = "scrcpy"
# ==========================================

def get_android_sdk():
    """Get the Android SDK version to determine if native camera streaming is supported."""
    cmd = [ADB_PATH]
    if current_target_device: cmd.extend(["-s", current_target_device])
    cmd.extend(["shell", "getprop", "ro.build.version.sdk"])
    try:
        out = subprocess.check_output(cmd, timeout=5).decode("utf-8").strip()
        return int(out)
    except:
        return 0

def dim_screen():
    cmd = [ADB_PATH]
    if current_target_device: cmd.extend(["-s", current_target_device])
    try:
        subprocess.run(cmd + ["shell", "settings", "put", "system", "screen_brightness_mode", "0"], check=True, timeout=5)
        subprocess.run(cmd + ["shell", "settings", "put", "system", "screen_brightness", "1"], check=True, timeout=5)
        subprocess.run(cmd + ["shell", "svc", "power", "stayon", "true"], check=True, timeout=5)
        messagebox.showinfo("Success", "Screen dimmed to 1% and forced to stay awake.\n\nTo restore: Re-enable Auto-Brightness on the phone.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to dim screen:\n{e}")

def detect_phone_size():
    cmd = [ADB_PATH]
    if current_target_device: cmd.extend(["-s", current_target_device])
    cmd.extend(["shell", "wm", "size"])
    
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5).decode("utf-8", errors="replace")
    except Exception as e:
        messagebox.showerror("Error", f"adb failed:\n{e}")
        return

    override = None
    physical = None
    for line in out.splitlines():
        line = line.strip()
        low = line.lower()
        if low.startswith("override size:"): override = line.split(":", 1)[1].strip()
        elif low.startswith("physical size:"): physical = line.split(":", 1)[1].strip()

    chosen = override or physical
    if not chosen or "x" not in chosen: return

    try:
        w_str, h_str = chosen.split("x", 1)
        phone_size["w"], phone_size["h"] = int(w_str), int(h_str)
        phone_size_label.config(text=f"Using: {w_str} × {h_str}")
    except ValueError:
        pass

def connect_wifi():
    global current_target_device
    ip = wifi_ip_entry.get().strip()
    if not ip: return
    
    target = f"{ip}:5555"
    try:
        subprocess.run([ADB_PATH, "tcpip", "5555"], check=True, timeout=5)
        subprocess.run([ADB_PATH, "connect", target], check=True, timeout=5)
        current_target_device = target
        messagebox.showinfo("Success", f"Connected to {target}\nYou can now unplug the USB cable.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect.\nMake sure USB is plugged in.\n\n{e}")

def get_scrcpy_base_cmd():
    cmd = [SCRCPY_PATH]
    if current_target_device: cmd.extend(["-s", current_target_device])
    return cmd

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
    cmd = get_scrcpy_base_cmd()
    if hwdec_disabled_var.get(): cmd.append("--hwdec=disabled")
    if crop: cmd.append(crop)
    try:
        subprocess.Popen(cmd)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start scrcpy:\n{e}")

def start_camera():
    sdk = get_android_sdk()
    cmd_adb = [ADB_PATH]
    if current_target_device: cmd_adb.extend(["-s", current_target_device])

    crop = build_crop_flag()
    cmd = get_scrcpy_base_cmd()
    
    # Global Android Support Logic
    if sdk >= 31: # Android 12+
        cmd.extend(["--video-source=camera"])
    else: # Android 11 and older (Your F105)
        subprocess.run(cmd_adb + ["shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"])

    cmd.extend(["--window-title=KamCam Feed"])
    if hwdec_disabled_var.get(): cmd.append("--hwdec=disabled")
    if crop: cmd.append(crop)

    try:
        subprocess.Popen(cmd)
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

# --- App Setup ---
root = tk.Tk()
root.title("KamCam (Scrcpy)")
root.geometry("400x720")
root.configure(bg="#1e1e2e")
root.resizable(False, False)

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

detect_frame = tk.Frame(root, bg="#1e1e2e")
detect_frame.pack(fill="x", padx=25, pady=(6, 2))

btn_detect = tk.Button(detect_frame, text="🔍  Detect Phone Size", command=detect_phone_size, bg="#94e2d5", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_detect.pack(side="left")

phone_size_label = tk.Label(detect_frame, text=f"Using: {phone_size['w']} × {phone_size['h']}", fg="#a6adc8", bg="#1e1e2e", font=("Cantarell", 9))
phone_size_label.pack(side="left", padx=(10, 0))

hwdec_disabled_var = tk.BooleanVar(value=True)
btn_toggle = tk.Button(root, command=toggle_hwdec, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(15, 5), ipady=4)
update_toggle_ui()

btn_dim = tk.Button(root, text="🌑  Dim Phone Screen (1%)", command=dim_screen, bg="#45475a", fg="#cdd6f4", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_dim.pack(anchor="w", padx=25, ipadx=55, pady=(5, 15), ipady=4)

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