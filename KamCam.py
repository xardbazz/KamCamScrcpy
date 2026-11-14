#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FOLDER = "USB and IP"

def find_executable(name, target_folder):
    """Searches inside the specific target folder, then root."""
    sub = "adb" if "adb" in name else "scrcpy"
    candidates = [
        os.path.join(BASE_DIR, target_folder, sub, name), # e.g. .../USB and IP/adb/adb.exe
        os.path.join(BASE_DIR, target_folder, name),      # e.g. .../USB and IP/adb.exe
        os.path.join(BASE_DIR, sub, name),                # e.g. .../adb/adb.exe
        os.path.join(BASE_DIR, name),                     # e.g. .../adb.exe
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return name # Fallback to system PATH

if platform.system() == "Windows":
    ADB_PATH = find_executable("adb.exe", TARGET_FOLDER)
    SCRCPY_PATH = find_executable("scrcpy.exe", TARGET_FOLDER)
else:
    ADB_PATH = "adb"
    SCRCPY_PATH = "scrcpy"

# ==========================================

current_target_device = ""
phone_size = {"w": 720, "h": 1520} 

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
    # Uses -d (USB) if no Wi-Fi device is connected
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

def detect_phone_size():
    cmd = [ADB_PATH, "-d", "shell", "wm", "size"]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).decode("utf-8", errors="replace")
    except FileNotFoundError:
        messagebox.showerror("ADB Not Found", f"adb.exe not found at:\n{ADB_PATH}")
        return
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
root.geometry("400x870") 
root.configure(bg="#1e1e2e")
root.resizable(False, False)

# Tkinter variables MUST be created after root = tk.Tk()
console_hidden_var = tk.BooleanVar(value=False)
hwdec_disabled_var = tk.BooleanVar(value=True)
audio_disabled_var = tk.BooleanVar(value=False)

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

btn_toggle = tk.Button(root, command=toggle_hwdec, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(15, 5), ipady=4)
update_toggle_ui()

btn_audio_toggle = tk.Button(root, command=toggle_audio, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_audio_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(0, 5), ipady=4)
update_audio_ui()

btn_console_toggle = tk.Button(root, command=toggle_console, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_console_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(0, 5), ipady=4)
update_console_ui()

btn_verify = tk.Button(root, text="🔧  Verify File Paths", command=verify_paths, bg="#f9e2af", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_verify.pack(anchor="w", padx=25, ipadx=55, pady=(0, 5), ipady=4)

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