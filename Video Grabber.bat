@echo off
cd /d "%~dp0"
python video_grabber.py
if errorlevel 1 pause
