# Multi-Stream RTSP Server with Video Upload 
A Python project for uploading videos and streaming them via RTSP protocol.

## Tools used:
```bash
# Python 3.11
# Flask (backend API)
# Streamlit (web UI)
# FFmpeg (video processing)
# MediaMTX – Handles the RTSP delivery.
# Windows 11 development environment
```
---

## Project structure
```bash
.
├── main.py              # Flask API + MediaMTX server launcher
├── ui.py                # Streamlit UI for video upload
├── uploads/             # Folder to store uploaded videos
├── rtsp_server/
│   └── mediamtx.exe     # RTSP server binary
├── requirements.txt     # Python dependencies
├── README.md      
└── mediamtx.yml         # Configuration file
```

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

# Then open the UI in your browser:
http://localhost:8501

From the UI, you can:

Upload video files

Assign a unique stream_name

Begin streaming to an RTSP URL (e.g. rtsp://localhost:8554/stream_name)

## View the stream in a media player like VLC
```

## Access
- Web UI: http://localhost:8501
- Status Endpoint http://localhost:5000/status

# Viewing Stream
Once a stream is started:
- Open VLC or another RTSP-compatible player
Enter the URL:
```bash
rtsp://localhost:8554/[stream_name]
```
You can open multiple streams simultaneously in VLC.

# Stream Status
To check the status of all running or recently started streams:
```bash
http://localhost:5000/status
```
This will return a JSON overview including:

- Stream names
- Status (running/stopped)
- Process IDs
- Uptime
- Associated video file