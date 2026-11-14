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
            
            # Launch camera app
            subprocess.run(cmd_adb + ["shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"])
            time.sleep(2)
            
            while True:
                try:
                    frame = subprocess.check_output(cmd_adb + ["exec-out", "screencap", "-p"])
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

def start_scrcpy_camera():
    """Starts a high-speed native video stream for Android 12+ devices."""
    sdk = get_android_sdk()
    if sdk < 31:
        messagebox.showerror("Not Supported", f"This feature requires Android 12+ (SDK 31).\nYour device is SDK {sdk}.\n\nPlease use the 'Start IP Webcam' button instead.")
        return

    cmd = [SCRCPY_PATH]
    if current_target_device: cmd.extend(["-s", current_target_device])
    cmd.extend(["--video-source=camera", "--window-title=KamCam High-Speed Stream"])

    try:
        subprocess.Popen(cmd)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start scrcpy:\n{e}")

def dim_screen():
    cmd = [ADB_PATH]
    if current_target_device: cmd.extend(["-s", current_target_device])
    try:
        subprocess.run(cmd + ["shell", "settings", "put", "system", "screen_brightness_mode", "0"], check=True, timeout=5)
        subprocess.run(cmd + ["shell", "settings", "put", "system", "screen_brightness", "1"], check=True, timeout=5)
        subprocess.run(cmd + ["shell", "svc", "power", "stayon", "true"], check=True, timeout=5)
        messagebox.showinfo("Success", "Screen dimmed to 1% and forced to stay awake.\n\nTo restore: Re-enable Auto-Brightness on the phone.")
    except FileNotFoundError:
        messagebox.showerror("Error", "adb not found. Make sure it is installed or in the script folder.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to dim screen:\n{e}")

def connect_wifi():
    global current_target_device
    ip = wifi_ip_entry.get().strip()
    if not ip: return
    
    target = f"{ip}:5555"
    try:
        subprocess.run([ADB_PATH, "tcpip", "5555"], check=True, timeout=5)
        subprocess.run([ADB_PATH, "connect", target], check=True, timeout=5)
        current_target_device = target
        messagebox.showinfo("Success", f"Connected to {target}")
    except FileNotFoundError:
        messagebox.showerror("Error", "adb not found. Make sure it is installed or in the script folder.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to connect.\nMake sure USB is plugged in.\n\n{e}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect.\n{e}")

# --- App Setup ---
root = tk.Tk()
root.title("KamCam (IP & Stream)")
root.geometry("400x600") # Slightly taller to fit new button
root.configure(bg="#1e1e2e")
root.resizable(False, False)

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

btn_wifi = tk.Button(wifi_inner, text="🔗 Connect", command=connect_wifi, bg="#fab387", fg="#11111b", font=("Cantarell", 9, "bold"), relief="flat")
btn_wifi.pack(side="left")

btn_dim = tk.Button(root, text="🌑  Dim Phone Screen (1%)", command=dim_screen, bg="#45475a", fg="#cdd6f4", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_dim.pack(anchor="w", padx=25, ipadx=55, pady=(15, 15), ipady=4)

# IP Webcam Button
btn_camera = tk.Button(root, text="🌐  Start IP Webcam (Browser)", command=start_ip_webcam, bg="#cba6f7", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_camera.pack(anchor="w", padx=25, ipadx=50, pady=(0, 10), ipady=4)

# New Android 12+ High-Speed Stream Button
btn_scrcpy = tk.Button(root, text="🎥  High-Speed Stream (Android 12+)", command=start_scrcpy_camera, bg="#a6e3a1", fg="#11111b", font=("Cantarell", 10, "bold"), relief="flat", cursor="hand2")
btn_scrcpy.pack(anchor="w", padx=25, ipadx=25, pady=(0, 12), ipady=4)

root.mainloop()