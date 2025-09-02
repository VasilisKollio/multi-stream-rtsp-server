# Multi-Stream RTSP Server with Video Upload 
A Python project for uploading videos and streaming them via RTSP protocol.

## Tools used:
```bash
# Python 3.11
# Flask (backend API)
# Streamlit (web UI)
# FFmpeg (video processing)
# Windows 11 development environment
```
---

## Flask Framework - main.py
- File upload endpoint that accepts video files
- Saves uploaded videos to `uploads/` folder  
- Starts FFmpeg processes to stream videos via RTSP
- API endpoints: `/upload`, `/status`, `/`

## UI: Streamlit - ui.py
- Simple web form for video upload
- Text input for stream names
- Sends requests to Flask backend
- Shows success/error messages

## Features Working so far
1. Video file upload and storage
2. File validation and secure naming
3. FFmpeg process creation and management

## Current Problems
### Main Issue - VLC Cannot Connect:
- FFmpeg processes start successfully according to logs
- VLC shows "Connection failed: VLC could not connect to localhost:8554"
- Streams appear as "running" in status API but aren't accessible

## Current Status

The application successfully handles file uploads and manages FFmpeg processes, but the core streaming functionality isn't working. Users can upload videos and see "success" messages, but cannot actually view the streams in VLC or other RTSP clients

# How to Run

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run Application
```bash
# Terminal 1
python main.py

# Terminal 2  
streamlit run ui.py
```

## Access
- Web UI: http://localhost:8501
- API: http://localhost:5000

