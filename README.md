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

## Setup - In the project's directory
```bash
python -m venv .venv
.venv\Scripts\activate
pip install streamlit
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

# Latest Progress 8/9
## Docker Container
 I migrated from the local executable to a containerized MediaMTX server using Docker in order to have cross-platform access and easier deployment. Created `docker-compose.yml` with the official MediaMTX image. Created `mediamtx.yml` to disable authentication and configure protocols. Modified `main.py` to connect to the Docker container instead of local executable.

```bash
# Start MediaMTX in Docker (required first!)
docker-compose up -d

# Verify container is running
docker ps

# Install requirements

# Run the Flask server 
python main.py

# Install Streamlit
pip install streamlit

# Run the web interface
streamlit run ui.py

# RUN THE NEW UI 
streamlit run ui_test.py
```
## New UI
I modified the UI of the project creating a new file called `ui_test.py`. It's core features are listed below:

#### Upload & Streaming
- Drag & drop video file upload
- Support for MP4, AVI, MOV, MKV, WMV, FLV, WEBM formats
- Stream name input with validation
- Start stream with one button click
- Display RTSP URL for copying

#### Stream Monitoring
- View all active streams in real-time
- Show stream status (running/stopped)
- Display stream details: filename, uptime, process ID
- Refresh streams manually
- Copy RTSP URLs easily

#### Server Status
- Check Flask server connection
- Monitor MediaMTX Docker container health
- View server information and API endpoints
- Direct link to Flask status page in browser