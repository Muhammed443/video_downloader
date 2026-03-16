import customtkinter as ctk
import yt_dlp
import os
import threading
import sys
import json
import re
import ctypes
from tkinter import messagebox, filedialog
from pathlib import Path
from static_ffmpeg import add_paths  # --- YENİ: static-ffmpeg entegrasyonu ---

# --- 1. KRİTİK AYAR: DPI FARKINDALIĞI ---
try:
    if os.name == 'nt':
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# --- 2. FFmpeg OTOMATİK HAZIRLIK ---
# Bu komut FFmpeg dosyalarını indirir/bulur ve sistem yoluna (PATH) ekler.
try:
    add_paths()
except Exception as e:
    print(f"FFmpeg yolları eklenirken hata: {e}")

# --- 3. DOSYA YOLU YÖNETİCİSİ (PyInstaller İçin) ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 4. SİSTEM SABİTLERİ ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
# FFMPEG_BIN artık gerekli değil çünkü static-ffmpeg PATH üzerinden çalışıyor.
USER_VIDEOS_DIR = str(os.path.join(Path.home(), "Videos"))

def hide_file(file_path):
    try:
        if os.name == 'nt' and os.path.exists(file_path):
            ctypes.windll.kernel32.SetFileAttributesW(file_path, 0x02)
    except: pass

def clean_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', str(text)).strip()

# --- 5. DİL PAKETLERİ ---
LANGUAGES = {
    "TR": {"title": "Video İndirici", "v_btn": "Video İndir", "a_btn": "Ses İndir", "entry": "Link...", "settings": "Ayarlar", "set_path": "Konumu Değiştir", "set_lang": "Dili Değiştir", "back": "Geri Dön", "done": "Bitti!", "error": "Hata!", "cur_path": "Konum:"},
    "EN": {"title": "Video Downloader", "v_btn": "Download Video", "a_btn": "Download Audio", "entry": "Link...", "settings": "Settings", "set_path": "Change Path", "set_lang": "Change Language", "back": "Back", "done": "Done!", "error": "Error!", "cur_path": "Path:"},
    "ES": {"title": "Descargador", "v_btn": "Video", "a_btn": "Audio", "entry": "Enlace...", "settings": "Ajustes", "set_path": "Ruta", "set_lang": "Idioma", "back": "Volver", "done": "¡Listo!", "error": "¡Error!", "cur_path": "Ruta:"},
    "RU": {"title": "Загрузчик", "v_btn": "Видео", "a_btn": "Аудио", "entry": "Ссылка...", "settings": "Настройки", "set_path": "Путь", "set_lang": "Язык", "back": "Назад", "done": "Готово!", "error": "Ошибка!", "cur_path": "Путь:"},
    "ZH": {"title": "下载器", "v_btn": "视频", "a_btn": "音频", "entry": "链接...", "settings": "设置", "set_path": "路径", "set_lang": "语言", "back": "返回", "done": "完成！", "error": "错误！", "cur_path": "路径:"},
    "AR": {"title": "محمل", "v_btn": "فيديو", "a_btn": "صوت", "entry": "رابط...", "settings": "الإعدادات", "set_path": "المسار", "set_lang": "اللغة", "back": "رجوع", "done": "تم!", "error": "خطأ!", "cur_path": "المسار:"}
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Video Downloader") 
        self.geometry("700x500")
        
        self.config = self.load_config()
        self.lang = self.config.get("language")
        self.base_path = self.config.get("path")
        
        ctk.set_appearance_mode("dark")

        try:
            icon_p = resource_path("icon.ico")
            self.iconbitmap(icon_p)
        except: pass

        if not self.lang: self.show_lang_screen(True)
        elif not self.base_path: self.show_path_screen()
        else: self.setup_main_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
            except: return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"language": self.lang, "path": self.base_path}, f)

    def show_lang_screen(self, first):
        for w in self.winfo_children(): w.destroy()
        self.title("Select Language")
        self.geometry("400x550")
        ctk.CTkLabel(self, text="Select Language", font=("Arial", 22, "bold")).pack(pady=30)
        btns = [("Türkçe", "TR"), ("English", "EN"), ("Español", "ES"), ("Русский", "RU"), ("简体中文", "ZH"), ("العربية", "AR")]
        for text, code in btns:
            ctk.CTkButton(self, text=text, width=220, height=40, command=lambda c=code: self.set_lang(c, first)).pack(pady=5)

    def set_lang(self, code, first):
        self.lang = code
        self.save_config()
        if first: self.show_path_screen()
        else: self.setup_settings_ui()

    def show_path_screen(self):
        for w in self.winfo_children(): w.destroy()
        self.title("Setup Storage")
        self.geometry("450x300")
        ctk.CTkLabel(self, text=f"Default Path: {USER_VIDEOS_DIR}", wraplength=400).pack(pady=40)
        ctk.CTkButton(self, text="Select Folder", command=self.pick_path).pack(pady=10)
        ctk.CTkButton(self, text="Use Default", command=self.skip_path).pack(pady=5)

    def pick_path(self):
        p = filedialog.askdirectory()
        if p: self.base_path = p; self.save_config(); self.setup_main_ui()

    def skip_path(self):
        self.base_path = USER_VIDEOS_DIR; self.save_config(); self.setup_main_ui()

    def setup_main_ui(self):
        for w in self.winfo_children(): w.destroy()
        t = LANGUAGES[self.lang]
        self.title(t["title"])
        self.geometry("700x500")

        ctk.CTkButton(self, text="⚙", width=35, fg_color="gray30", command=self.setup_settings_ui).place(relx=0.97, rely=0.03, anchor="ne")

        self.main_label = ctk.CTkLabel(self, text=t["title"], font=("Arial", 30, "bold"))
        self.main_label.pack(pady=(60, 20))

        self.url_input = ctk.CTkEntry(self, placeholder_text=t["entry"], width=560, height=45, justify="center")
        self.url_input.pack(pady=10)

        self.perc_label = ctk.CTkLabel(self, text="%0", font=("Arial", 52, "bold"), text_color="#3B8ED0")
        self.perc_label.pack(pady=(10, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self, width=560, height=15)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.info_frame = ctk.CTkFrame(self, fg_color="transparent", width=560)
        self.info_frame.pack()
        self.speed_label = ctk.CTkLabel(self.info_frame, text="0 MiB/s", font=("Arial", 13, "bold"), text_color="gray")
        self.speed_label.pack(side="left", padx=10)
        self.eta_label = ctk.CTkLabel(self.info_frame, text="ETA: 00:00", font=("Arial", 13, "bold"), text_color="gray")
        self.eta_label.pack(side="right", padx=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=30)
        ctk.CTkButton(btn_frame, text=t["v_btn"], width=270, height=60, font=("Arial", 18, "bold"), command=lambda: self.start_dl("video")).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text=t["a_btn"], width=270, height=60, fg_color="transparent", border_width=2, command=lambda: self.start_dl("audio")).grid(row=0, column=1, padx=10)

    def setup_settings_ui(self):
        for w in self.winfo_children(): w.destroy()
        t = LANGUAGES[self.lang]
        self.title(t["settings"])
        self.geometry("550x500")

        ctk.CTkLabel(self, text=t["settings"], font=("Arial", 26, "bold")).pack(pady=30)
        ctk.CTkLabel(self, text=f"{t['cur_path']} {self.base_path}", wraplength=450, text_color="gray").pack(pady=10)
        
        ctk.CTkButton(self, text=t["set_path"], command=self.change_path_settings).pack(pady=10)
        ctk.CTkButton(self, text=t["set_lang"], fg_color="gray30", command=lambda: self.show_lang_screen(False)).pack(pady=10)
        ctk.CTkButton(self, text=t["back"], fg_color="transparent", border_width=1, command=self.setup_main_ui).pack(pady=40)

    def change_path_settings(self):
        p = filedialog.askdirectory()
        if p: self.base_path = p; self.save_config(); self.setup_settings_ui()

    # --- İNDİRME MANTIĞI ---
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p_str = clean_ansi(d.get('_percent_str', '0%'))
            s_str = clean_ansi(d.get('_speed_str', '0 MiB/s'))
            e_str = clean_ansi(d.get('_eta_str', '00:00'))
            
            temp_file = d.get('tmpfilename') or d.get('filename')
            if temp_file: hide_file(temp_file)
            
            try:
                p_val = float(p_str.replace('%', '')) / 100
                self.after(0, lambda: self.perc_label.configure(text=p_str))
                self.after(0, lambda: self.progress_bar.set(p_val))
                self.after(0, lambda: self.speed_label.configure(text=s_str))
                self.after(0, lambda: self.eta_label.configure(text=f"ETA: {e_str}"))
            except: pass

    def start_dl(self, mode):
        url = self.url_input.get().strip()
        if not url: return
        threading.Thread(target=self.worker, args=(url, mode), daemon=True).start()

    def worker(self, url, mode):
        t = LANGUAGES[self.lang]
        folder = "video_downloader" if mode == "video" else "audio_downloader"
        path = os.path.join(self.base_path, folder)
        if not os.path.exists(path): os.makedirs(path)

        try:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
                # static-ffmpeg sayesinde ffmpeg_location belirtmeye gerek yok, PATH'ten okunur
                'progress_hooks': [self.progress_hook],
                'quiet': True, 'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }] if mode == 'video' else [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            self.after(0, lambda: messagebox.showinfo(t["title"], t["done"]))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(t["error"], str(e)))

if __name__ == "__main__":
    app = App()
    app.mainloop()