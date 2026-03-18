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
from static_ffmpeg import add_paths

# --- 1. SİSTEM VE FFmpeg HAZIRLIĞI ---
def refresh_ffmpeg():
    try:
        add_paths() 
    except Exception: pass

refresh_ffmpeg()

# --- 2. ICON VE DOSYA GİZLEME AYARLARI ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ICON_PATH = resource_path("icon.ico")

try:
    if os.name == 'nt':
        myappid = 'mycompany.videodownloader.pro.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception: pass

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
USER_VIDEOS_DIR = str(os.path.join(Path.home(), "Videos"))

def set_file_visibility(file_path, hide=True):
    """
    hide=True ise dosyayı gizler.
    hide=False ise dosyayı normal (görünür) yapar.
    """
    try:
        if os.name == 'nt' and os.path.exists(file_path):
            # 0x02: Gizli, 0x80: Normal/Görünür
            attr = 0x02 if hide else 0x80
            ctypes.windll.kernel32.SetFileAttributesW(file_path, attr)
    except: pass

def clean_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', str(text)).strip()

# --- 3. DİL PAKETLERİ ---
LANGUAGES = {
    "TR": {"title": "Video İndirici", "v_btn": "Video İndir", "a_btn": "Ses İndir", "entry": "Link...", "settings": "Ayarlar", "set_path": "Konumu Değiştir", "set_lang": "Dili Değiştir", "back": "Geri Dön", "done": "Bitti!", "error": "Hata!", "cur_path": "Konum:", "yt_err": "YouTube desteklenmemektedir. Lütfen başka siteler kullanın."},
    "EN": {"title": "Video Downloader", "v_btn": "Download Video", "a_btn": "Download Audio", "entry": "Link...", "settings": "Settings", "set_path": "Change Path", "set_lang": "Change Language", "back": "Back", "done": "Done!", "error": "Error!", "cur_path": "Path:", "yt_err": "YouTube is not supported."},
    "ES": {"title": "Descargador", "v_btn": "Video", "a_btn": "Audio", "entry": "Enlace...", "settings": "Ajustes", "set_path": "Ruta", "set_lang": "Idioma", "back": "Volver", "done": "¡Listo!", "error": "¡Error!", "cur_path": "Ruta:", "yt_err": "YouTube no es compatible."},
    "RU": {"title": "Загрузчик", "v_btn": "Видео", "a_btn": "Аудио", "entry": "Ссылка...", "settings": "Настройки", "set_path": "Путь", "set_lang": "Язык", "back": "Назад", "done": "Готово!", "error": "Ошибка!", "cur_path": "Путь:", "yt_err": "YouTube не поддерживается."},
    "ZH": {"title": "下载器", "v_btn": "视频", "a_btn": "音频", "entry": "链接...", "settings": "设置", "set_path": "路径", "set_lang": "语言", "back": "返回", "done": "完成！", "error": "错误！", "cur_path": "路径:", "yt_err": "不支持 YouTube。"},
    "AR": {"title": "محمل", "v_btn": "فيديو", "a_btn": "صوت", "entry": "رابط...", "settings": "الإعدادات", "set_path": "المسار", "set_lang": "اللغة", "back": "رجوع", "done": "تم!", "error": "خطأ!", "cur_path": "المسار:", "yt_err": "يوتيوب غير مدعوم."}
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("700x550")
        
        try:
            if os.path.exists(ICON_PATH):
                self.iconbitmap(ICON_PATH)
        except Exception: pass

        self.config = self.load_config()
        self.lang = self.config.get("language", "TR")
        self.base_path = self.config.get("path", USER_VIDEOS_DIR)
        ctk.set_appearance_mode("dark")
        
        if not self.config.get("language"): self.show_lang_screen(True)
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
        ctk.CTkLabel(self, text="Select Language", font=("Arial", 22, "bold")).pack(pady=30)
        btns = [("Türkçe", "TR"), ("English", "EN"), ("Español", "ES"), ("Русский", "RU"), ("简体中文", "ZH"), ("العربية", "AR")]
        for text, code in btns:
            ctk.CTkButton(self, text=text, width=220, height=40, command=lambda c=code: self.set_lang(c, first)).pack(pady=5)

    def set_lang(self, code, first):
        self.lang = code
        self.save_config()
        if first: self.setup_main_ui()
        else: self.setup_main_ui()

    def setup_main_ui(self):
        for w in self.winfo_children(): w.destroy()
        t = LANGUAGES[self.lang]
        self.title(t["title"])
        ctk.CTkButton(self, text="⚙", width=35, fg_color="gray30", command=self.setup_settings_ui).place(relx=0.97, rely=0.03, anchor="ne")
        
        ctk.CTkLabel(self, text=t["title"], font=("Arial", 30, "bold")).pack(pady=(60, 20))
        self.url_input = ctk.CTkEntry(self, placeholder_text=t["entry"], width=560, height=45, justify="center")
        self.url_input.pack(pady=10)
        
        self.perc_label = ctk.CTkLabel(self, text="%0", font=("Arial", 52, "bold"), text_color="#3B8ED0")
        self.perc_label.pack()
        
        self.progress_bar = ctk.CTkProgressBar(self, width=560, height=15)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)
        
        info_f = ctk.CTkFrame(self, fg_color="transparent", width=560)
        info_f.pack()
        self.speed_label = ctk.CTkLabel(info_f, text="0 MiB/s", font=("Arial", 13, "bold"), text_color="gray")
        self.speed_label.pack(side="left", padx=20)
        self.eta_label = ctk.CTkLabel(info_f, text="ETA: 00:00", font=("Arial", 13, "bold"), text_color="gray")
        self.eta_label.pack(side="right", padx=20)
        
        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=30)
        ctk.CTkButton(btn_f, text=t["v_btn"], width=270, height=60, font=("Arial", 18, "bold"), command=lambda: self.start_dl("video")).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_f, text=t["a_btn"], width=270, height=60, fg_color="transparent", border_width=2, command=lambda: self.start_dl("audio")).grid(row=0, column=1, padx=10)

    def setup_settings_ui(self):
        for w in self.winfo_children(): w.destroy()
        t = LANGUAGES[self.lang]
        self.title(t["settings"])
        ctk.CTkLabel(self, text=t["settings"], font=("Arial", 26, "bold")).pack(pady=30)
        ctk.CTkLabel(self, text=f"{t['cur_path']} {self.base_path}", wraplength=450).pack(pady=10)
        ctk.CTkButton(self, text=t["set_path"], command=self.change_path_settings).pack(pady=10)
        ctk.CTkButton(self, text=t["set_lang"], fg_color="gray30", command=lambda: self.show_lang_screen(False)).pack(pady=10)
        ctk.CTkButton(self, text=t["back"], fg_color="transparent", border_width=1, command=self.setup_main_ui).pack(pady=40)

    def change_path_settings(self):
        p = filedialog.askdirectory()
        if p: self.base_path = p; self.save_config(); self.setup_settings_ui()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p_str = clean_ansi(d.get('_percent_str', '0%'))
            s_str = clean_ansi(d.get('_speed_str', '0 MiB/s'))
            e_str = clean_ansi(d.get('_eta_str', '00:00'))
            
            # Geçici dosyayı hemen gizle
            tmp = d.get('tmpfilename') or d.get('filename')
            if tmp: set_file_visibility(tmp, hide=True)
            
            try:
                p_val = float(p_str.replace('%', '')) / 100
                self.after(0, lambda: self.perc_label.configure(text=p_str))
                self.after(0, lambda: self.progress_bar.set(p_val))
                self.after(0, lambda: self.speed_label.configure(text=s_str))
                self.after(0, lambda: self.eta_label.configure(text=f"ETA: {e_str}"))
            except: pass
        
        elif d['status'] == 'finished':
            # İndirme bittiğinde dosyayı görünür yap
            final_file = d.get('filename')
            if final_file: set_file_visibility(final_file, hide=False)

    def start_dl(self, mode):
        url = self.url_input.get().strip()
        if url: threading.Thread(target=self.worker, args=(url, mode), daemon=True).start()

    def worker(self, url, mode):
        t = LANGUAGES[self.lang]
        if "youtube.com" in url or "youtu.be" in url:
            self.after(0, lambda: messagebox.showwarning(t["title"], t["yt_err"]))
            return

        refresh_ffmpeg()
        folder = "video_downloader" if mode == "video" else "audio_downloader"
        path = os.path.join(self.base_path, folder)
        if not os.path.exists(path): os.makedirs(path)

        try:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if mode == 'video' else 'bestaudio/best',
                'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True, 'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4',
                }] if mode == 'video' else [{
                    'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192',
                }]
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # İndirme ve dönüştürme işlemi
                info = ydl.extract_info(url, download=True)
                # FFmpeg sonrası oluşan nihai dosyayı bul ve görünür yap
                dest_file = ydl.prepare_filename(info)
                # MP4 veya MP3 uzantısını kontrol et
                if mode == 'audio':
                    dest_file = dest_file.rsplit('.', 1)[0] + ".mp3"
                set_file_visibility(dest_file, hide=False)

            self.after(0, lambda: messagebox.showinfo(t["title"], t["done"]))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(t["error"], str(e)))

if __name__ == "__main__":
    app = App()
    app.mainloop()
