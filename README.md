# Video Grabber

A simple desktop app for downloading videos from social media. Paste a link, click **Download**, done.

Works with YouTube, TikTok, Instagram, X/Twitter, Twitch (clips and VODs), Reddit, Facebook, Vimeo and [1,000+ other sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md), powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- **Paste and go**: paste one link or many (one per line). Error text and junk in the box are ignored automatically.
- **Quality picker**: Best available, 1080p, 720p, 480p, or Audio only (MP3)
- **Always save as MP4**: converts downloads to MP4 so they play everywhere
- **Preview after download**: pops up a window with a still frame, length and file size, plus **Play** and **Show in folder** buttons
- **Progress bar** with speed and time left, plus a **Cancel** button
- **Update downloader** button for when a site stops working
- **No manual setup**: installs what it needs the first time it runs, including its own copy of ffmpeg

## Requirements

- Windows, macOS or Linux
- [Python 3.9 or newer](https://www.python.org/downloads/)
  - On Windows, tick **"Add Python to PATH"** during install.

## Getting started

1. Download `video_grabber.py` and `Video Grabber.bat` into the same folder.
2. **Windows:** double-click `Video Grabber.bat`.
   **Mac/Linux:** open a terminal in that folder and run:
   ```
   python3 video_grabber.py
   ```
3. The first launch takes a minute while it installs `yt-dlp` and `imageio-ffmpeg`. After that it opens right away.

## How to use

1. Copy a video link from the site or app (the **Share → Copy link** button works).
2. Click **Paste** (or paste into the box yourself). Add more links on new lines if you want.
3. Pick a **Quality**.
4. Click **Download** (or press **Ctrl+Enter**).

Videos save to `Downloads/Video Grabber` by default. Use **Browse** to choose another folder, or **Open** to jump to it.

## What the .bat file does

`Video Grabber.bat` is just a launcher. It switches to its own folder, starts the app with Python, and keeps the window open if something crashes so you can read the error. If double-clicking `video_grabber.py` already opens the app on your PC, you don't need it.

Tip: rename the file to `video_grabber.pyw` to run it without the black console window. Do this only once everything is working, because errors won't be shown.

## Troubleshooting

| Problem | Fix |
|---|---|
| A site that used to work now fails | Click **Update downloader**, then restart the app. Sites change often, and yt-dlp updates usually fix it. |
| "Private" or "login required" error | The post is private, age-restricted or needs an account. These can't be downloaded. |
| `'python' is not recognized` | Reinstall Python and tick **"Add Python to PATH"**. |
| Double-clicking the .py opens Notepad / VS Code | Use `Video Grabber.bat` instead. |
| "No links found" | Make sure you pasted the full link (e.g. `https://www.tiktok.com/...`). |

## Please use responsibly

Only download videos you own or have permission to use. Respect creators' rights and each platform's terms of service.

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp): the download engine
- [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg): bundled ffmpeg for merging, converting and previews
