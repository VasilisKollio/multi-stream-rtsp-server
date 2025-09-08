import os
import uuid
import subprocess
import logging
import time
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
import threading
import requests


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max upload size

##RTSP_HOST = 'localhost'
##RTSP_PORT = 8554

# MediaMTX settings - now points to Docker container
RTSP_HOST = 'localhost'  # Docker container accessible on localhost
RTSP_PORT = 8554
MEDIAMTX_API_PORT = 9997

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Global dictionary to track running/active streams
active_streams = {}

def check_mediamtx_running(): ##
    """Check if MediaMTX Docker container is running and accessible"""
    try:
        # Try to access MediaMTX API
        response = requests.get(f'http://{RTSP_HOST}:{MEDIAMTX_API_PORT}/v3/config/global/get', timeout=3)
        if response.status_code == 200:
            logger.info("MediaMTX Docker container is running and accessible")
            return True
    except requests.exceptions.RequestException:
        pass
    
    # Fallback: try to connect to RTSP port
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((RTSP_HOST, RTSP_PORT))
        sock.close()
        if result == 0:
            logger.info("MediaMTX RTSP port is accessible")
            return True
    except Exception:
        pass
    
    logger.warning("MediaMTX not accessible. Make sure Docker container is running.")
    return False

def start_mediamtx():
    """Check MediaMTX status instead of starting local executable"""
    if check_mediamtx_running():
        logger.info("MediaMTX Docker container is already running")
        return True
    else:
        logger.error("MediaMTX Docker container is not running!")
        logger.error("Please start it with: docker-compose up -d")
        return False ##
    

##def start_mediamtx():
##    mediamtx_path = os.path.join(os.path.dirname(__file__), 'rtsp_server', 'mediamtx.exe')
    
##    if os.path.isfile(mediamtx_path):
##        subprocess.Popen([mediamtx_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
##        logger.info("MediaMTX started.")
##    else:
##        logger.error("MediaMTX not found. Please check the path.")


""" Helper Functions """
def allowed_file(filename):
    # Check if file extension is allowed
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def start_rtsp_stream(stream_name, video_path):
    # Start RTSP stream using FFmpeg
    rtsp_url = f"rtsp://{RTSP_HOST}:{RTSP_PORT}/{stream_name}"
   
    # FFmpeg command for RTSP streaming with infinite loop
    ffmpeg_cmd = [
        'ffmpeg',
        '-re',                          # Read input at native frame rate
        '-stream_loop', '-1',           # Loop video indefinitely
        '-i', video_path,               # Input video file
        '-c:v', 'libx264',              # Video codec H.264
        '-preset', 'ultrafast',         # Fast encoding preset
        '-tune', 'zerolatency',         # Low latency tuning
        '-g', '30',                     # GOP size (keyframe interval)
        '-c:a', 'aac',                  # Audio codec
        '-b:a', '128k',                 # Audio bitrate
        '-f', 'rtsp',                   # Output format RTSP
        '-rtsp_transport', 'tcp',       ## Use TCP for reliability with Docker ##
        rtsp_url                        # RTSP output URL
    ]
    
    try:
        # Start FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            #universal_newlines=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
                
        logger.info(f"RTSP stream started for '{stream_name}' at {rtsp_url}")
        return process, rtsp_url
        
    except Exception as e:
        logger.error(f"Failed to start RTSP stream for '{stream_name}': {e}")
        return None, None


def stop_existing_stream(stream_name):
    # Stop existing stream if it exists
    if stream_name in active_streams:
        existing_process = active_streams[stream_name].get('process')
        if existing_process and existing_process.poll() is None:
            existing_process.terminate()
            logger.info(f"Stopped existing stream: {stream_name}")


def start_stream_background(stream_name, video_path, filename):
    def target():
        process, rtsp_url = start_rtsp_stream(stream_name, video_path)
        
        if process and rtsp_url:
            active_streams[stream_name] = {
                'process': process,
                'rtsp_url': rtsp_url,
                'filename': filename,
                'file_path': video_path,
                'created_at': time.time(),
                'stream_name': stream_name

            }
        else:
            logger.error(f"Failed to start stream in the background for {stream_name}")

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread


@app.route('/', methods=['GET'])
def landing_page():
    # Landing page - returns JSON with instructions and active streams
    mediamtx_status = "running" if check_mediamtx_running() else "not accessible" ##

    # Get current status of all streams
    active_stream_list = []
    for stream_name, stream_info in active_streams.items():
        process = stream_info.get('process')
        is_running = process and process.poll() is None
        
        active_stream_list.append({
            'stream_name': stream_name,
            'filename': stream_info.get('filename', 'Unknown'),
            'rtsp_url': stream_info.get('rtsp_url', ''),
            'is_running': is_running,
            'started_at': time.strftime('%Y-%m-%d %H:%M:%S', 
                                     time.localtime(stream_info.get('created_at', 0)))
        })
    
    return jsonify({
        'message': 'Multi-Stream RTSP Server',
        'mediamtx_status': mediamtx_status,
        'instructions': {
            'upload': 'POST /upload with multipart form: file (video) + stream_name (string)',
            'status': 'GET /status for all active streams',
            'supported_formats': list(ALLOWED_EXTENSIONS),
            'rtsp_access': f'rtsp://{RTSP_HOST}:{RTSP_PORT}/[stream_name]',##
            'docker_note': 'MediaMTX runs in Docker container'
        },
        'active_streams': active_stream_list,
        'total_active_streams': len(active_stream_list)
    })

@app.route('/upload', methods=['POST'])
def upload_video():
    # Upload video and start RTSP stream

    ## Check if MediaMTX is accessible ##
    if not check_mediamtx_running():
        return jsonify({
            'error': 'MediaMTX server not accessible. Please start Docker container with: docker-compose up -d'
        }), 503
       
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    # Check if stream_name is present
    if 'stream_name' not in request.form:
        return jsonify({'error': 'No stream_name provided'}), 400
    
    file = request.files['file']
    stream_name = request.form['stream_name'].strip()
    
    # Validate inputs
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not stream_name:
        return jsonify({'error': 'Stream name cannot be empty'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # Validate stream_name (alphanumeric, underscore, hyphen only)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', stream_name):
        return jsonify({'error': 'Stream name can only contain letters, numbers, underscores, and hyphens'}), 400
    
    try:
        # Stop existing stream with same name if it exists
        stop_existing_stream(stream_name)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        # Use stream_name as part of the filename to avoid conflicts
        safe_filename = f"{stream_name}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        file.save(file_path)
        
        logger.info(f"File saved: {file_path}")
        
        # Start RTSP stream
        start_stream_background(stream_name, file_path, filename)

        # Give it time to initialize 
        time.sleep(1)

        stream_info = active_streams.get(stream_name)
        if not stream_info:
         return jsonify({'error': 'Failed to start RTSP stream'}), 500

        rtsp_url = stream_info['rtsp_url']
        
        logger.info(f"Stream '{stream_name}' started successfully")
        
        return jsonify({
            'success': True,
            'stream_name': stream_name,
            'rtsp_url': rtsp_url,
            'message': f'Stream started successfully for {stream_name}'
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/status', methods=['GET'])
def get_status():
    # Check active streams and return JSON with all active streams and process status
    mediamtx_accessible = check_mediamtx_running()


    status_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        'mediamtx_accessible': mediamtx_accessible,
        'mediamtx_host': RTSP_HOST,
        'mediamtx_port': RTSP_PORT,
        'total_streams': len(active_streams),
        'rtsp_server': f'rtsp://{RTSP_HOST}:{RTSP_PORT}',
        'streams': {}
    }
    
    for stream_name, stream_info in active_streams.items():
        process = stream_info.get('process')
        
        # Check if process is still running
        if process:
            is_running = process.poll() is None
            if is_running:
                process_status = 'running'
                pid = process.pid
            else:
                process_status = 'stopped'
                pid = None
        else:
            is_running = False
            process_status = 'no_process'
            pid = None
        
        status_data['streams'][stream_name] = {
            'rtsp_url': stream_info.get('rtsp_url', ''),
            'filename': stream_info.get('filename', ''),
            'file_path': stream_info.get('file_path', ''),
            'status': process_status,
            'is_running': is_running,
            'pid': pid,
            'created_at': stream_info.get('created_at', 0),
            'uptime_seconds': time.time() - stream_info.get('created_at', 0) if is_running else 0
        }
    
    return jsonify(status_data)

##if __name__ == '__main__':
##    start_mediamtx()
##    logger.info(" Starting Multi-Stream RTSP Server...")
##    logger.info(f" RTSP Server: rtsp://{RTSP_HOST}:{RTSP_PORT}/[stream_name]")
##    logger.info(f" Web Interface: http://0.0.0.0:5000")
##    logger.info(f" Upload Directory: {UPLOAD_FOLDER}/")
##    logger.info("=" * 50)
##    
##    app.run(debug=False, host='0.0.0.0', port=5000)

@app.route('/mediamtx/health', methods=['GET'])
def mediamtx_health():
    """Check MediaMTX Docker container health"""
    is_running = check_mediamtx_running()
    return jsonify({
        'mediamtx_accessible': is_running,
        'timestamp': time.time(),
        'rtsp_endpoint': f'rtsp://{RTSP_HOST}:{RTSP_PORT}',
        'api_endpoint': f'http://{RTSP_HOST}:{MEDIAMTX_API_PORT}'
    })

if __name__ == '__main__':
    logger.info("Starting Multi-Stream RTSP Server with Docker MediaMTX...")
    logger.info("=" * 60)
    logger.info("IMPORTANT: Make sure MediaMTX Docker container is running!")
    logger.info("Start with: docker-compose up -d")
    logger.info("=" * 60)
    
    # Check MediaMTX status on startup
    if start_mediamtx():
        logger.info(f"RTSP Server: rtsp://{RTSP_HOST}:{RTSP_PORT}/[stream_name]")
        logger.info(f"Web Interface: http://0.0.0.0:5000")
        logger.info(f"Upload Directory: {UPLOAD_FOLDER}/")
        logger.info("=" * 50)
    else:
        logger.error("MediaMTX not accessible! Streams may fail.")
    
    app.run(debug=False, host='0.0.0.0', port=5000)