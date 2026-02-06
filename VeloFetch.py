import customtkinter as ctk
import subprocess
import os
import sys
import signal
import threading
import shutil
import re
import json
import shlex
from tkinter import filedialog

# --- 外観設定 ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "VeloFetch_config.json"
APP_NAME = "VeloFetch"
ACCENT_COLOR = "#007AFF" 

class VeloFetchApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- ウィンドウ基本設定 ---
        self.title(f"{APP_NAME}")
        self.geometry("640x580") 
        self.resizable(False, False)
        self.configure(fg_color="#121212")

        # --- 内部変数 ---
        self.process = None
        self.is_windows = (sys.platform == "win32")
        self.audio_only_var = ctk.BooleanVar(value=False)
        
        # 設定のロード
        self.load_config()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # グリッド構成
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(7, weight=1) 
        
        # --- 1. Header Area ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=30, pady=(30, 15), sticky="ew")
        
        self.title_v = ctk.CTkLabel(self.header_frame, text="V", font=("Inter", 28, "bold"), text_color=ACCENT_COLOR)
        self.title_v.pack(side="left")
        self.title_rest = ctk.CTkLabel(self.header_frame, text="eloFetch", font=("Inter", 28, "bold"), text_color="#ffffff")
        self.title_rest.pack(side="left")
        
        self.settings_btn = ctk.CTkButton(
            self.header_frame, 
            text="⚙ Settings", 
            width=90, 
            height=28, 
            fg_color="#2b2b2b", 
            hover_color="#3d3d3d",
            font=("Inter", 12), 
            command=self.open_settings
        )
        self.settings_btn.pack(side="right")

        # --- 2. URL Input Area ---
        self.url_label = ctk.CTkLabel(self, text="VIDEO URL", font=("Inter", 11, "bold"), text_color="#666666")
        self.url_label.grid(row=1, column=0, padx=35, sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Paste URL here...", 
            width=570, 
            height=45, 
            fg_color="#1e1e1e", 
            border_color="#333333",
            text_color="#ffffff"
        )
        self.url_entry.grid(row=2, column=0, padx=30, pady=(5, 15))

        # --- 3. Format Options ---
        self.option_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.option_frame.grid(row=3, column=0, padx=35, pady=(5, 0), sticky="w")
        
        self.audio_checkbox = ctk.CTkCheckBox(
            self.option_frame, 
            text="Extract Audio only (M4A)", 
            variable=self.audio_only_var,
            font=("Inter", 12),
            fg_color=ACCENT_COLOR
        )
        self.audio_checkbox.pack(side="left")

        # --- 4. Advanced Command Area ---
        self.adv_label = ctk.CTkLabel(self, text="ADVANCED COMMAND (yt-dlp args)", font=("Inter", 11, "bold"), text_color="#666666")
        self.adv_label.grid(row=4, column=0, padx=35, sticky="w", pady=(15, 0))
        
        self.adv_entry = ctk.CTkEntry(
            self, 
            placeholder_text="e.g. --list-formats (Overrides standard UI settings)", 
            width=570, 
            height=35, 
            fg_color="#1e1e1e", 
            border_color="#333333",
            text_color=ACCENT_COLOR
        )
        self.adv_entry.grid(row=5, column=0, padx=30, pady=(5, 0))
        self.adv_entry.bind("<KeyRelease>", self.update_ui_state)

        # --- 5. Action Buttons ---
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=6, column=0, padx=30, pady=20, sticky="ew")
        self.button_frame.grid_columnconfigure(0, weight=3)
        self.button_frame.grid_columnconfigure(1, weight=1)
        
        self.dl_button = ctk.CTkButton(
            self.button_frame, 
            text="START FETCH", 
            font=("Inter", 15, "bold"), 
            fg_color=ACCENT_COLOR, 
            hover_color="#005ecb",
            height=50, 
            command=self.start_download_thread
        )
        self.dl_button.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.stop_button = ctk.CTkButton(
            self.button_frame, 
            text="STOP", 
            font=("Inter", 14, "bold"), 
            fg_color="#2b2b2b", 
            height=50, 
            state="disabled", 
            command=self.stop_conversion
        )
        self.stop_button.grid(row=0, column=1, sticky="ew")

        # --- 6. Console/Log Output ---
        self.log_text = ctk.CTkTextbox(
            self, 
            width=580, 
            height=140, 
            fg_color="#0a0a0a", 
            font=("Menlo", 11), 
            text_color="#888888",
            border_width=1,
            border_color="#222222"
        )
        self.log_text.grid(row=7, column=0, padx=30, pady=(0, 10), sticky="nsew")

        # --- 7. Status & Progress Bar ---
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=8, column=0, padx=35, pady=(0, 20), sticky="ew")
        
        self.status_label = ctk.CTkLabel(self.progress_frame, text="READY", font=("Inter", 11, "bold"), text_color="#555555")
        self.status_label.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8, fg_color="#1e1e1e", progress_color=ACCENT_COLOR)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x")

    def update_ui_state(self, *args):
        is_adv = len(self.adv_entry.get().strip()) > 0
        if is_adv:
            self.url_entry.configure(state="disabled", fg_color="#1a1a1a")
            self.audio_checkbox.configure(state="disabled")
            self.adv_entry.configure(border_color=ACCENT_COLOR)
        else:
            self.url_entry.configure(state="normal", fg_color="#1e1e1e")
            self.audio_checkbox.configure(state="normal")
            self.adv_entry.configure(border_color="#333333")

    def load_config(self):
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: config = json.load(f)
            except: pass
        self.save_path = config.get("save_path", "")
        self.custom_ytdlp = config.get("custom_ytdlp", "")
        self.custom_ffmpeg = config.get("custom_ffmpeg", "")
        env = self.get_hybrid_env()
        if not self.custom_ytdlp: self.custom_ytdlp = shutil.which("yt-dlp", path=env["PATH"]) or ""
        if not self.custom_ffmpeg: self.custom_ffmpeg = shutil.which("ffmpeg", path=env["PATH"]) or ""

    def save_config_to_file(self):
        config = {"save_path": self.save_path, "custom_ytdlp": self.custom_ytdlp, "custom_ffmpeg": self.custom_ffmpeg}
        with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)

    def show_ctk_message(self, title, message):
        msg_window = ctk.CTkToplevel(self)
        msg_window.title(title); msg_window.geometry("400x180"); msg_window.attributes("-topmost", True); msg_window.configure(fg_color="#161616")
        ctk.CTkLabel(msg_window, text=message, font=("Inter", 13), wraplength=350).pack(expand=True, pady=20)
        ctk.CTkButton(msg_window, text="OK", width=120, height=35, fg_color=ACCENT_COLOR, command=msg_window.destroy).pack(pady=(0, 20))

    def open_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings"); dialog.geometry("580x350"); dialog.configure(fg_color="#161616")
        dialog.transient(self); dialog.grab_set()

        ctk.CTkLabel(dialog, text="VeloFetch Configuration", font=("Inter", 18, "bold")).pack(pady=(15, 20))
        
        def select_dir():
            path = filedialog.askdirectory(initialdir=ent_path.get())
            if path: ent_path.delete(0, "end"); ent_path.insert(0, path)
        def select_yt():
            path = filedialog.askopenfilename(); 
            if path: ent_yt.delete(0, "end"); ent_yt.insert(0, path)
        def select_ff():
            path = filedialog.askopenfilename(); 
            if path: ent_ff.delete(0, "end"); ent_ff.insert(0, path)

        # --- Save Path ---
        f0 = ctk.CTkFrame(dialog, fg_color="transparent"); f0.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(f0, text="Save To:", width=80, anchor="w").pack(side="left")
        ent_path = ctk.CTkEntry(f0, width=300); ent_path.pack(side="left", padx=5); ent_path.insert(0, self.save_path)
        ctk.CTkButton(f0, text="Browse", width=60, command=select_dir).pack(side="right")

        # --- yt-dlp ---
        f1 = ctk.CTkFrame(dialog, fg_color="transparent"); f1.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(f1, text="yt-dlp:", width=80, anchor="w").pack(side="left")
        ent_yt = ctk.CTkEntry(f1, width=300); ent_yt.pack(side="left", padx=5); ent_yt.insert(0, self.custom_ytdlp)
        ctk.CTkButton(f1, text="Browse", width=60, command=select_yt).pack(side="right")
        
        # --- ffmpeg ---
        f2 = ctk.CTkFrame(dialog, fg_color="transparent"); f2.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(f2, text="ffmpeg:", width=80, anchor="w").pack(side="left")
        ent_ff = ctk.CTkEntry(f2, width=300); ent_ff.pack(side="left", padx=5); ent_ff.insert(0, self.custom_ffmpeg)
        ctk.CTkButton(f2, text="Browse", width=60, command=select_ff).pack(side="right")
        
        def apply():
            self.save_path = ent_path.get(); self.custom_ytdlp = ent_yt.get(); self.custom_ffmpeg = ent_ff.get()
            self.save_config_to_file(); dialog.destroy()
        
        ctk.CTkButton(dialog, text="SAVE CHANGES", fg_color=ACCENT_COLOR, height=40, command=apply).pack(pady=30)

    def get_hybrid_env(self):
        env = os.environ.copy()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        paths = [current_dir, os.path.join(current_dir, "bin")] if self.is_windows else ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin"]
        env["PATH"] = os.pathsep.join(paths) + os.pathsep + env.get("PATH", "")
        return env

    def start_download_thread(self):
        if not self.custom_ytdlp or not self.custom_ffmpeg:
            self.show_ctk_message("Tool Missing", "yt-dlp or ffmpeg not found.")
            return
        if not self.save_path:
            self.show_ctk_message("Path Missing", "Please select a save directory in Settings.")
            return
            
        url = self.url_entry.get().strip()
        adv_cmd = self.adv_entry.get().strip()
        if not adv_cmd and not url:
            self.show_status("ERROR: INPUT MISSING", "#FF453A")
            return
        self.show_status("INITIALIZING...", ACCENT_COLOR)
        self.progress_bar.set(0) # プログレスバーのリセット
        self.dl_button.configure(state="disabled"); self.stop_button.configure(state="normal")
        self.log_text.delete("1.0", "end")
        threading.Thread(target=self.run_download, args=(url, adv_cmd), daemon=True).start()

    def run_download(self, url, adv_cmd):
        try:
            cmd = [self.custom_ytdlp, "--ffmpeg-location", self.custom_ffmpeg]
            if adv_cmd:
                cmd += shlex.split(adv_cmd)
                if url and url not in adv_cmd: cmd.append(url)
            else:
                output = os.path.join(self.save_path, "%(title)s.%(ext)s")
                cmd += ["--no-check-certificate"]
                if self.audio_only_var.get():
                    cmd += ["-f", "bestaudio[ext=m4a]/bestaudio", "--extract-audio", "--audio-format", "m4a"]
                else:
                    cmd += ["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"]
                cmd += ["-o", output, "--newline", url]
            
            info = subprocess.STARTUPINFO() if self.is_windows else None
            if self.is_windows: info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self.get_hybrid_env(), startupinfo=info)
            for line in self.process.stdout:
                match = re.search(r'(\d+\.\d+)%', line)
                if match:
                    p = float(match.group(1)) / 100.0
                    self.after(0, lambda v=p: self.progress_bar.set(v))
                    self.show_status(f"FETCHING: {int(p*100)}%", ACCENT_COLOR)
                self.update_log(line)
            self.process.wait()
            if self.process.returncode == 0: self.show_status("SUCCESS", "#32D74B")
            else: self.show_status("STOPPED / FAILED", "#FF453A")
        except Exception as e:
            self.update_log(f"\nError: {e}")
        finally:
            self.process = None
            self.after(0, lambda: (self.dl_button.configure(state="normal"), self.stop_button.configure(state="disabled")))

    def stop_conversion(self):
        if self.process:
            if self.is_windows: 
                # --- Windows用修正: 子プロセス(ffmpeg)を含めて強制終了 ---
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], 
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else: 
                self.process.send_signal(signal.SIGINT)

    def on_closing(self):
        if self.process: 
            try: self.stop_conversion() # 共通の停止ロジックを使用
            except: pass
        self.save_config_to_file(); self.destroy()

    def show_status(self, msg, col="#555555"):
        self.after(0, lambda: self.status_label.configure(text=msg.upper(), text_color=col))

    def update_log(self, msg):
        self.after(0, lambda: (self.log_text.insert("end", msg), self.log_text.see("end")))

if __name__ == "__main__":
    VeloFetchApp().mainloop()