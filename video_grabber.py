"""
Video Grabber - paste a link from (almost) any social media site and download the video.
Powered by yt-dlp (supports YouTube, TikTok, Instagram, X/Twitter, Twitch, Reddit,
Facebook, Vimeo, Twitch clips/VODs and 1000+ more).

Run:  python video_grabber.py
First launch auto-installs what it needs (yt-dlp + a bundled ffmpeg).
"""
import os
import sys
import subprocess
import threading
import queue
import importlib

# ---------------------------------------------------------------- dependencies
REQUIRED = {"yt_dlp": "yt-dlp", "imageio_ffmpeg": "imageio-ffmpeg"}


def ensure_deps():
    missing = []
    for mod, pkg in REQUIRED.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Installing:", ", ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *missing])
        importlib.invalidate_caches()


ensure_deps()

import yt_dlp  # noqa: E402
import imageio_ffmpeg  # noqa: E402
import tkinter as tk  # noqa: E402
from tkinter import ttk, filedialog, messagebox  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Video Grabber")

QUALITY = {
    "Best available": "bestvideo*+bestaudio/best",
    "1080p": "bestvideo*[height<=1080]+bestaudio/best[height<=1080]/best",
    "720p": "bestvideo*[height<=720]+bestaudio/best[height<=720]/best",
    "480p": "bestvideo*[height<=480]+bestaudio/best[height<=480]/best",
    "Audio only (MP3)": "bestaudio/best",
}

import re  # noqa: E402

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
_BARE_RE = re.compile(r"^(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S*$", re.I)


def extract_urls(text):
    """Pull real links out of whatever was pasted; ignore error text and junk."""
    found = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        hits = _URL_RE.findall(line)
        if not hits and _BARE_RE.match(line):  # e.g. tiktok.com/@user/video/123
            hits = ["https://" + line]
        for u in hits:
            u = u.rstrip(").,;]")
            if u not in found:
                found.append(u)
    return found


# ---------------------------------------------------------------- colors
BG, PANEL, FG, MUTED, ACCENT, OK, ERR = (
    "#16161d", "#22222c", "#ececf1", "#9a9aae", "#8b5cf6", "#22c55e", "#ef4444")


class App:
    def __init__(self, root):
        self.root = root
        self.msgs = queue.Queue()
        self.busy = False
        self.cancel_flag = False

        root.title("Video Grabber")
        root.geometry("720x580")
        root.minsize(560, 480)
        root.configure(bg=BG)

        style = ttk.Style()
        style.theme_use("clam")
        # Quality box: white field, bold dark-purple text (easy to read)
        style.configure("Q.TCombobox", fieldbackground="#ffffff", background=ACCENT,
                        foreground="#5b21b6", arrowcolor="#ffffff", padding=4,
                        selectbackground="#ffffff", selectforeground="#5b21b6")
        style.map("Q.TCombobox",
                  fieldbackground=[("readonly", "#ffffff")],
                  foreground=[("readonly", "#5b21b6")],
                  selectbackground=[("readonly", "#ffffff")],
                  selectforeground=[("readonly", "#5b21b6")],
                  background=[("active", "#7c3aed"), ("readonly", ACCENT)])
        # Dropdown list: black text on white, purple highlight
        root.option_add("*TCombobox*Listbox.background", "#ffffff")
        root.option_add("*TCombobox*Listbox.foreground", "#000000")
        root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
        style.configure("bar.Horizontal.TProgressbar", troughcolor=PANEL,
                        background=ACCENT, bordercolor=PANEL, lightcolor=ACCENT,
                        darkcolor=ACCENT)

        pad = dict(padx=16)

        tk.Label(root, text="Video Grabber", bg=BG, fg=FG,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(14, 0), **pad)
        tk.Label(root, text="Paste one or more links (one per line) and hit Download.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", **pad)

        # links box
        box = tk.Frame(root, bg=BG)
        box.pack(fill="x", pady=(10, 0), **pad)
        self.links = tk.Text(box, height=5, bg=PANEL, fg=FG, insertbackground=FG,
                             relief="flat", font=("Consolas", 10), wrap="none")
        self.links.pack(side="left", fill="x", expand=True)
        side = tk.Frame(box, bg=BG)
        side.pack(side="left", fill="y", padx=(8, 0))
        self._btn(side, "Paste", self.paste).pack(fill="x")
        self._btn(side, "Clear", lambda: self.links.delete("1.0", "end")).pack(fill="x", pady=(6, 0))

        # options row
        opts = tk.Frame(root, bg=BG)
        opts.pack(fill="x", pady=(12, 0), **pad)
        tk.Label(opts, text="Quality", bg=BG, fg=FG, font=("Segoe UI", 10, "bold")).pack(side="left")
        self.quality = ttk.Combobox(opts, values=list(QUALITY), state="readonly", width=18,
                                    style="Q.TCombobox", font=("Segoe UI", 10, "bold"))
        self.quality.set("Best available")
        self.quality.bind("<<ComboboxSelected>>", lambda e: self.quality.selection_clear())
        self.quality.pack(side="left", padx=(6, 16))
        self.mp4 = tk.BooleanVar(value=True)
        tk.Checkbutton(opts, text="Always save as MP4", variable=self.mp4, bg=BG, fg=FG,
                       selectcolor=PANEL, activebackground=BG, activeforeground=FG
                       ).pack(side="left")
        self.preview = tk.BooleanVar(value=True)
        tk.Checkbutton(opts, text="Preview after download", variable=self.preview, bg=BG,
                       fg=FG, selectcolor=PANEL, activebackground=BG, activeforeground=FG
                       ).pack(side="left", padx=(12, 0))

        # folder row
        frow = tk.Frame(root, bg=BG)
        frow.pack(fill="x", pady=(10, 0), **pad)
        tk.Label(frow, text="Save to", bg=BG, fg=MUTED).pack(side="left")
        self.folder = tk.StringVar(value=DEFAULT_DIR)
        tk.Entry(frow, textvariable=self.folder, bg=PANEL, fg=FG, insertbackground=FG,
                 relief="flat").pack(side="left", fill="x", expand=True, padx=6, ipady=4)
        self._btn(frow, "Browse", self.browse).pack(side="left")
        self._btn(frow, "Open", self.open_folder).pack(side="left", padx=(6, 0))

        # action row
        arow = tk.Frame(root, bg=BG)
        arow.pack(fill="x", pady=(14, 0), **pad)
        self.dl_btn = self._btn(arow, "Download", self.start, primary=True)
        self.dl_btn.pack(side="left")
        self.cancel_btn = self._btn(arow, "Cancel", self.cancel)
        self.cancel_btn.pack(side="left", padx=8)
        self.cancel_btn.config(state="disabled")
        self._btn(arow, "Update downloader", self.update_ytdlp).pack(side="right")

        # progress
        self.status = tk.Label(root, text="Ready.", bg=BG, fg=MUTED, anchor="w")
        self.status.pack(fill="x", pady=(14, 2), **pad)
        self.bar = ttk.Progressbar(root, style="bar.Horizontal.TProgressbar", maximum=100)
        self.bar.pack(fill="x", **pad)

        # log
        self.log = tk.Text(root, bg=PANEL, fg=MUTED, relief="flat", height=8,
                           font=("Consolas", 9), state="disabled")
        self.log.pack(fill="both", expand=True, pady=(12, 14), **pad)
        self.log.tag_config("ok", foreground=OK)
        self.log.tag_config("err", foreground=ERR)

        root.bind("<Control-Return>", lambda e: self.start())
        self.root.after(100, self.pump)

    # ------------------------------------------------------------ ui helpers
    def _btn(self, parent, text, cmd, primary=False):
        return tk.Button(parent, text=text, command=cmd, relief="flat", cursor="hand2",
                         bg=ACCENT if primary else PANEL, fg="white" if primary else FG,
                         activebackground="#7c3aed" if primary else "#2e2e3a",
                         activeforeground="white", padx=14, pady=5,
                         font=("Segoe UI", 10, "bold" if primary else "normal"))

    def write(self, text, tag=None):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def paste(self):
        try:
            clip = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        current = self.links.get("1.0", "end").strip()
        self.links.insert("end", ("\n" if current else "") + clip)

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.folder.get())
        if d:
            self.folder.set(d)

    def open_folder(self):
        d = self.folder.get()
        os.makedirs(d, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(d)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["xdg-open", d])

    def pump(self):
        """Apply messages from the worker thread to the UI."""
        try:
            while True:
                kind, val = self.msgs.get_nowait()
                if kind == "status":
                    self.status.config(text=val)
                elif kind == "progress":
                    self.bar["value"] = val
                elif kind == "log":
                    self.write(*val)
                elif kind == "preview":
                    PreviewWindow(self.root, *val)
                elif kind == "done":
                    self.busy = False
                    self.dl_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    # ------------------------------------------------------------ actions
    def start(self):
        if self.busy:
            return
        urls = extract_urls(self.links.get("1.0", "end"))
        if not urls:
            messagebox.showinfo("Video Grabber",
                                "No links found. Paste a link that starts with https:// "
                                "(or like tiktok.com/...).")
            return
        # Show only the cleaned-up links in the box
        self.links.delete("1.0", "end")
        self.links.insert("1.0", "\n".join(urls))
        self.busy = True
        self.cancel_flag = False
        self.dl_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        threading.Thread(target=self.worker, args=(urls,), daemon=True).start()

    def cancel(self):
        self.cancel_flag = True
        self.msgs.put(("status", "Cancelling..."))

    def update_ytdlp(self):
        def run():
            self.msgs.put(("status", "Updating yt-dlp..."))
            r = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                self.msgs.put(("log", ("Downloader updated. Restart the app to use the new version.", "ok")))
                self.msgs.put(("status", "Updated - restart the app."))
            else:
                self.msgs.put(("log", ("Update failed:\n" + r.stderr[-500:], "err")))
                self.msgs.put(("status", "Update failed."))
        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------ download
    def hook(self, d):
        if self.cancel_flag:
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user")
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            speed = d.get("_speed_str", "").strip()
            eta = d.get("_eta_str", "").strip()
            self.msgs.put(("progress", pct))
            self.msgs.put(("status", f"Downloading {pct:5.1f}%   {speed}   ETA {eta}"))
        elif d["status"] == "finished":
            self.msgs.put(("progress", 100))
            self.msgs.put(("status", "Processing (merging / converting)..."))

    def build_opts(self):
        q = self.quality.get()
        out = self.folder.get()
        os.makedirs(out, exist_ok=True)
        # Work inside the download folder so temp files never land somewhere
        # protected (e.g. C:\Windows\System32 when launched as admin).
        os.chdir(out)
        tmp = os.path.join(out, ".temp")
        os.makedirs(tmp, exist_ok=True)
        opts = {
            "format": QUALITY[q],
            "paths": {"home": out, "temp": tmp},
            "outtmpl": "%(extractor_key)s - %(title).120B [%(id)s].%(ext)s",
            "cachedir": os.path.join(os.path.expanduser("~"), ".video_grabber_cache"),
            "ffmpeg_location": FFMPEG,
            "progress_hooks": [self.hook],
            "noplaylist": True,
            "windowsfilenames": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 5,
            "concurrent_fragment_downloads": 4,
        }
        if q.startswith("Audio"):
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                       "preferredcodec": "mp3", "preferredquality": "192"}]
        elif self.mp4.get():
            opts["merge_output_format"] = "mp4"
            opts["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]
        return opts

    def worker(self, urls):
        ok = fail = 0
        for i, url in enumerate(urls, 1):
            if self.cancel_flag:
                break
            self.msgs.put(("progress", 0))
            self.msgs.put(("log", (f"[{i}/{len(urls)}] {url}", None)))
            try:
                with yt_dlp.YoutubeDL(self.build_opts()) as ydl:
                    info = ydl.extract_info(url, download=True) or {}
                    path = final_path(ydl, info)
                title = info.get("title", "video")
                self.msgs.put(("log", (f"   Saved: {title}", "ok")))
                ok += 1
                if self.preview.get() and path:
                    self.msgs.put(("status", "Making preview..."))
                    thumb = make_thumbnail(path)
                    self.msgs.put(("preview", (path, title, info.get("duration"), thumb)))
            except yt_dlp.utils.DownloadCancelled:
                self.msgs.put(("log", ("   Cancelled.", "err")))
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e).replace("\x1b[0;31m", "").replace("\x1b[0m", "")
                self.msgs.put(("log", (f"   Failed: {msg[:300]}", "err")))
                if "login" in msg.lower() or "private" in msg.lower():
                    self.msgs.put(("log", ("   (This post may be private or need a login.)", "err")))
                fail += 1
        self.msgs.put(("status", f"Done - {ok} saved, {fail} failed."))
        self.msgs.put(("done", None))


# ---------------------------------------------------------------- preview
AUDIO_EXT = (".mp3", ".m4a", ".opus", ".ogg", ".wav", ".aac", ".flac")


def final_path(ydl, info):
    """Find the file yt-dlp actually wrote (after merging / converting)."""
    for d in info.get("requested_downloads") or []:
        p = d.get("filepath")
        if p and os.path.exists(p):
            return p
    try:
        p = ydl.prepare_filename(info)
    except Exception:  # noqa: BLE001
        return None
    base = os.path.splitext(p)[0]
    for ext in (".mp4", ".mkv", ".webm", ".mp3", ".m4a", os.path.splitext(p)[1]):
        if os.path.exists(base + ext):
            return base + ext
    return None


def make_thumbnail(path):
    """Grab a frame from the video as a PNG (Tk can show PNG natively)."""
    if path.lower().endswith(AUDIO_EXT):
        return None
    tmp_dir = os.path.join(os.path.dirname(path), ".temp")
    os.makedirs(tmp_dir, exist_ok=True)
    out = os.path.join(tmp_dir, f"preview_{abs(hash(path))}.png")
    flags = 0x08000000 if sys.platform.startswith("win") else 0  # no console popup
    for seek in ("1", "0"):  # 1s in (skips black first frames); fall back to start
        try:
            subprocess.run([FFMPEG, "-y", "-ss", seek, "-i", path, "-frames:v", "1",
                            "-vf", "scale='min(560,iw)':-2", out],
                           capture_output=True, timeout=30, creationflags=flags)
        except Exception:  # noqa: BLE001
            return None
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return out
    return None


def fmt_duration(sec):
    if not sec:
        return "?"
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def open_path(p):
    if sys.platform.startswith("win"):
        os.startfile(p)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


def show_in_folder(p):
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(p)])
    else:
        open_path(os.path.dirname(p))


class PreviewWindow(tk.Toplevel):
    def __init__(self, root, path, title, duration, thumb):
        super().__init__(root)
        self.title("Preview - " + (title or "video")[:60])
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(root)

        img_box = tk.Frame(self, bg="#000000")
        img_box.pack(padx=14, pady=(14, 8))
        self.img = None
        if thumb:
            try:
                self.img = tk.PhotoImage(file=thumb)
            except tk.TclError:
                self.img = None
        if self.img:
            pic = tk.Label(img_box, image=self.img, bg="#000000", cursor="hand2")
            pic.pack()
            pic.bind("<Button-1>", lambda e: open_path(path))
            tk.Label(img_box, text="▶  click to play", bg="#000000", fg="white",
                     font=("Segoe UI", 9)).place(relx=0.5, rely=0.92, anchor="center")
        else:
            label = "♫  Audio file" if path.lower().endswith(AUDIO_EXT) else "No preview image"
            tk.Label(img_box, text=label, bg="#000000", fg=MUTED, width=50, height=10,
                     font=("Segoe UI", 12)).pack()

        tk.Label(self, text=title, bg=BG, fg=FG, font=("Segoe UI", 11, "bold"),
                 wraplength=540, justify="left").pack(anchor="w", padx=14)
        try:
            size = f"{os.path.getsize(path) / 1_048_576:.1f} MB"
        except OSError:
            size = "?"
        tk.Label(self, text=f"Length {fmt_duration(duration)}   •   {size}   •   "
                            f"{os.path.splitext(path)[1].lstrip('.').upper()}",
                 bg=BG, fg=MUTED).pack(anchor="w", padx=14)
        tk.Label(self, text=os.path.basename(path), bg=BG, fg=MUTED,
                 font=("Consolas", 8), wraplength=540, justify="left").pack(anchor="w", padx=14)

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=14, pady=14)

        def btn(text, cmd, primary=False):
            return tk.Button(row, text=text, command=cmd, relief="flat", cursor="hand2",
                             bg=ACCENT if primary else PANEL, fg="white" if primary else FG,
                             activebackground="#7c3aed" if primary else "#2e2e3a",
                             activeforeground="white", padx=14, pady=5)
        btn("▶ Play", lambda: open_path(path), True).pack(side="left")
        btn("Show in folder", lambda: show_in_folder(path)).pack(side="left", padx=8)
        btn("Close", self.destroy).pack(side="right")
        self.lift()
        self.focus_force()


if __name__ == "__main__":
    # Never run from a protected folder like System32.
    os.makedirs(DEFAULT_DIR, exist_ok=True)
    os.chdir(DEFAULT_DIR)
    import tempfile
    os.environ.setdefault("TMP", tempfile.gettempdir())
    root = tk.Tk()
    App(root)
    root.mainloop()
