#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
import socket
import http.server
import socketserver
import threading
import time
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FOLDER = "IP"

def find_executable(name, target_folder):
    """Searches inside the specific target folder, then root."""
    sub = "adb" if "adb" in name else "scrcpy"
    candidates = [
        os.path.join(BASE_DIR, target_folder, sub, name), # e.g. .../IP/adb/adb.exe
        os.path.join(BASE_DIR, target_folder, name),      # e.g. .../IP/adb.exe
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
PORT = 8080

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

def launch_app(cmd):
    if platform.system() == "Windows" and console_hidden_var.get():
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(cmd)

def get_android_sdk():
    if not current_target_device: return 0
    cmd = [ADB_PATH, "-s", current_target_device, "shell", "getprop", "ro.build.version.sdk"]
    try:
        out = subprocess.check_output(cmd, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        return int(out.decode("utf-8").strip())
    except:
        return 0

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class StreamHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = f"<html><body style='background:#1e1e2e; color:#cdd6f4; text-align:center; font-family:sans-serif;'><h1>📷 KamCam IP Webcam</h1><img src='/stream' style='width:100%; max-width:720px; border: 2px solid #89b4fa; border-radius: 10px;'></body></html>"
            self.wfile.write(html.encode())
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            
            cmd_adb = [ADB_PATH]
            if current_target_device: cmd_adb.extend(["-s", current_target_device])
            
            subprocess.run(cmd_adb + ["shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(2)
            
            while True:
                try:
                    frame = subprocess.check_output(cmd_adb + ["exec-out", "screencap", "-p"], creationflags=subprocess.CREATE_NO_WINDOW)
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.1)
                except (BrokenPipeError, ConnectionResetError):
                    break
                except Exception as e:
                    print(f"Stream error: {e}")
                    break

def start_ip_webcam():
    if not current_target_device:
        messagebox.showerror("Error", "No Wi-Fi device connected.\nPlease click 'Connect' first.")
        return
        
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"
    
    def run_server():
        handler = StreamHandler
        socketserver.TCPServer.allow_reuse_address = True 
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            httpd.serve_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    msg = (
        f"IP Webcam Started!\n\n"
        f"Open this link in any browser on your network:\n{url}\n\n"
        f"(Note: Keep the camera app open on the phone.)"
    )
    messagebox.showinfo("IP Webcam Server", msg)

def start_scrcpy_control():
    if not current_target_device:
        messagebox.showerror("Error", "No Wi-Fi device connected.\nPlease click 'Connect' first.")
        return
        
    cmd = [SCRCPY_PATH, "-s", current_target_device, "--window-title=KamCam Remote Control"]
    if audio_disabled_var.get(): cmd.append("--no-audio")

    try:
        launch_app(cmd)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start scrcpy:\n{e}")

def start_scrcpy_camera():
    if not current_target_device:
        messagebox.showerror("Error", "No Wi-Fi device connected.\nPlease click 'Connect' first.")
        return
        
    sdk = get_android_sdk()
    if sdk < 31:
        messagebox.showerror("Not Supported", f"This feature requires Android 12+ (SDK 31).\nYour device is SDK {sdk}.\n\nPlease use the 'Start IP Webcam' button instead.")
        return

    cmd = [SCRCPY_PATH, "-s", current_target_device, "--video-source=camera", "--window-title=KamCam High-Speed Stream"]
    if audio_disabled_var.get(): cmd.append("--no-audio")

    try:
        launch_app(cmd)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start scrcpy:\n{e}")

def dim_screen():
    if not current_target_device:
        messagebox.showerror("Error", "No Wi-Fi device connected.\nPlease click 'Connect' first.")
        return
        
    cmd = [ADB_PATH, "-s", current_target_device]
    try:
        subprocess.run(cmd + ["shell", "settings", "put", "system", "screen_brightness_mode", "0"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(cmd + ["shell", "settings", "put", "system", "screen_brightness", "1"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(cmd + ["shell", "svc", "power", "stayon", "true"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Success", "Screen dimmed to 1% and forced to stay awake.\n\nTo restore: Re-enable Auto-Brightness on the phone.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to dim screen:\n{e}")

def enable_wifi_mode():
    try:
        subprocess.run([ADB_PATH, "-d", "tcpip", "5555"], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Success", "Wi-Fi mode enabled!\nYou can now unplug the USB cable from this phone.")
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "Failed. Make sure ONLY the target phone is plugged in via USB (unplug the other one temporarily).")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to enable Wi-Fi mode:\n{e}")

def connect_wifi():
    global current_target_device
    ip = wifi_ip_entry.get().strip()
    if not ip: return
    target = f"{ip}:5555"
    try:
        subprocess.run([ADB_PATH, "connect", target], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        current_target_device = target
        messagebox.showinfo("Success", f"Connected to {target}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect:\n{e}")

def disconnect_wifi():
    global current_target_device
    ip = wifi_ip_entry.get().strip()
    target = f"{ip}:5555" if ip else current_target_device
    if not target: return
    
    try:
        subprocess.run([ADB_PATH, "disconnect", target], check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        current_target_device = ""
        messagebox.showinfo("Disconnected", f"Disconnected from {target}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to disconnect:\n{e}")

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
root.title("KamCam (IP & Stream)")
root.geometry("420x870") 
root.configure(bg="#1e1e2e")
root.resizable(False, False)

# All Tkinter variables must be defined AFTER root = tk.Tk()
console_hidden_var = tk.BooleanVar(value=False) 
audio_disabled_var = tk.BooleanVar(value=False) 

title = tk.Label(root, text="📷 KamCam Controls (IP)", font=("Cantarell", 14, "bold"), fg="#cdd6f4", bg="#1e1e2e")
title.pack(pady=10)

wifi_frame = tk.Frame(root, bg="#313244", bd=1, relief="solid")
wifi_frame.pack(fill="x", padx=20, pady=10)

tk.Label(wifi_frame, text="ADB Wi-Fi Mode (No USB needed after connect)", fg="#a6adc8", bg="#313244", font=("Cantarell", 9, "italic")).pack(pady=(5,0))
wifi_inner = tk.Frame(wifi_frame, bg="#313244")
wifi_inner.pack(pady=5)

wifi_ip_entry = tk.Entry(wifi_inner, width=15)
wifi_ip_entry.insert(0, "192.168.1.") 
wifi_ip_entry.pack(side="left", padx=5)

btn_connect = tk.Button(wifi_inner, text="🔗 Connect", command=connect_wifi, bg="#fab387", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat")
btn_connect.pack(side="left", padx=(0, 5))

btn_disconnect = tk.Button(wifi_inner, text="🔌 Disconnect", command=disconnect_wifi, bg="#f38ba8", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat")
btn_disconnect.pack(side="left")

btn_enable = tk.Button(wifi_frame, text="⚙️ One-Time Setup (Requires USB)", command=enable_wifi_mode, bg="#f9e2af", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat")
btn_enable.pack(pady=(0, 5))

btn_dim = tk.Button(root, text="🌑  Dim Phone Screen (1%)", command=dim_screen, bg="#45475a", fg="#cdd6f4", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_dim.pack(anchor="w", padx=25, ipadx=55, pady=(15, 15), ipady=4)

btn_audio_toggle = tk.Button(root, command=toggle_audio, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_audio_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(0, 5), ipady=4)
update_audio_ui()

btn_console_toggle = tk.Button(root, command=toggle_console, font=("Cantarell", 10, "bold"), fg="#11111b", relief="flat", cursor="hand2")
btn_console_toggle.pack(anchor="w", padx=25, ipadx=40, pady=(0, 5), ipady=4)
update_console_ui()

btn_verify = tk.Button(root, text="🔧  Verify File Paths", command=verify_paths, bg="#f9e2af", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_verify.pack(anchor="w", padx=25, ipadx=55, pady=(0, 5), ipady=4)

btn_scrcpy_control = tk.Button(root, text="🎮  Start scrcpy Control (Wi-Fi)", command=start_scrcpy_control, bg="#89b4fa", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_scrcpy_control.pack(anchor="w", padx=25, ipadx=45, pady=(0, 10), ipady=4)

btn_scrcpy_cam = tk.Button(root, text="🎥  Start Camera Stream (Android 12+)", command=start_scrcpy_camera, bg="#a6e3a1", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_scrcpy_cam.pack(anchor="w", padx=25, ipadx=20, pady=(0, 10), ipady=4)

btn_ip_webcam = tk.Button(root, text="🌐  Start IP Webcam (Browser)", command=start_ip_webcam, bg="#cba6f7", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_ip_webcam.pack(anchor="w", padx=25, ipadx=50, pady=(0, 12), ipady=4)

root.mainloop()