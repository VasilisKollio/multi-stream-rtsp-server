#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import socket
import threading
import os
import time
import glob
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class SimpleRTSPClient:
    INIT = 0
    READY = 1
    PLAYING = 2

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    def __init__(self, root):
        self.root = root
        self.root.title("Simple RTSP Player with Auto-Discovery")
        self.root.geometry("800x650")
        
        # Connection settings
        self.serverAddr = "localhost"
        self.serverPort = 8554
        self.rtpPort = 25000
        
        # Current session state
        self.state = self.INIT
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.frameNbr = 0
        self.rtspSocket = None
        self.rtpSocket = None
        self.playEvent = None
        
        # Available videos and current selection
        self.available_videos = []
        self.current_video = None
        
        self.setup_ui()
        self.auto_discover_videos()  # Automatically discover videos
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Create simple GUI interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="5")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Server settings in one row
        ttk.Label(settings_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.server_var = tk.StringVar(value=self.serverAddr)
        server_entry = ttk.Entry(settings_frame, textvariable=self.server_var, width=12)
        server_entry.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(settings_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.port_var = tk.StringVar(value=str(self.serverPort))
        port_entry = ttk.Entry(settings_frame, textvariable=self.port_var, width=8)
        port_entry.grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(settings_frame, text="RTP:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.rtp_port_var = tk.StringVar(value=str(self.rtpPort))
        rtp_entry = ttk.Entry(settings_frame, textvariable=self.rtp_port_var, width=8)
        rtp_entry.grid(row=0, column=5, padx=(0, 5))
        
        # Refresh button
        refresh_btn = ttk.Button(settings_frame, text="Refresh", command=self.auto_discover_videos)
        refresh_btn.grid(row=0, column=6)
        
        # Video selection frame
        video_frame = ttk.LabelFrame(main_frame, text="Video Selection", padding="5")
        video_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Video dropdown instead of listbox
        ttk.Label(video_frame, text="Choose Video:").pack(side=tk.LEFT, padx=(0, 5))
        self.video_var = tk.StringVar()
        self.video_combo = ttk.Combobox(video_frame, textvariable=self.video_var, state="readonly", width=30)
        self.video_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.video_combo.bind('<<ComboboxSelected>>', self.on_video_select)
        
        # Manual entry for custom video name
        ttk.Label(video_frame, text="or enter:").pack(side=tk.LEFT, padx=(10, 5))
        self.manual_video_var = tk.StringVar()
        manual_entry = ttk.Entry(video_frame, textvariable=self.manual_video_var, width=20)
        manual_entry.pack(side=tk.LEFT)
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.setup_btn = ttk.Button(control_frame, text="Setup", command=self.setup_movie)
        self.setup_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.play_btn = ttk.Button(control_frame, text="Play", command=self.play_movie, state='disabled')
        self.play_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pause_btn = ttk.Button(control_frame, text="Pause", command=self.pause_movie, state='disabled')
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.teardown_btn = ttk.Button(control_frame, text="Stop", command=self.teardown_movie, state='disabled')
        self.teardown_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Status
        self.status_var = tk.StringVar(value="Select a video to start")
        status_label = ttk.Label(control_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT)
        
        # Video display area
        video_display_frame = ttk.LabelFrame(main_frame, text="Video Stream", padding="5")
        video_display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.video_label = tk.Label(video_display_frame, bg='black', text="Setup and play a video", 
                                   fg='white', font=('Arial', 12))
        self.video_label.pack(fill=tk.BOTH, expand=True)

    def auto_discover_videos(self):
        """Auto-discover videos using multiple methods"""
        discovered_videos = []
        
        self.serverAddr = self.server_var.get().strip()
        self.serverPort = int(self.port_var.get().strip())
        
        if self.serverAddr in ['localhost', '127.0.0.1']:
            local_videos = glob.glob("*.Mjpeg") + glob.glob("*.mjpeg")
            for video in local_videos:
                if video not in discovered_videos:
                    discovered_videos.append(video)
                    print(f"Found locally: {video}")
        
        # Update GUI
        if discovered_videos:
            self.available_videos = discovered_videos
            self.video_combo['values'] = discovered_videos
            self.video_combo.set(discovered_videos[0])  # Select first video
            self.current_video = discovered_videos[0]
            self.update_status(f"Found {len(discovered_videos)} videos")
            print(f"Total discovered: {discovered_videos}")
        else:
            self.update_status("No videos found - enter video name manually")
            self.video_combo['values'] = []
            
    def test_video_available(self, video_name):
        """Test if video is available by sending quick SETUP request"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)  # Quick timeout
            test_socket.connect((self.serverAddr, self.serverPort))
            
            # Send SETUP request
            test_request = f"SETUP {video_name}\n1\n RTSP/1.0 RTP/UDP {self.rtpPort + 1000}"
            test_socket.send(test_request.encode('utf-8'))
            
            # Wait for response
            response = test_socket.recv(1024)
            test_socket.close()
            
            # Check for success response
            if response and b"200 OK" in response:
                return True
                
        except:
            pass  # Ignore errors during testing
        
        return False

    def on_video_select(self, event=None):
        """Handle video selection"""
        selected = self.video_var.get()
        if selected:
            self.current_video = selected
            self.manual_video_var.set("")  # Clear manual entry

    def get_selected_video(self):
        """Get currently selected video (from dropdown or manual entry)"""
        manual_video = self.manual_video_var.get().strip()
        if manual_video:
            return manual_video
        return self.video_var.get()

    def update_status(self, message):
        """Update status message"""
        self.status_var.set(message)
        print(f"Status: {message}")

    def setup_movie(self):
        """Setup connection with selected video"""
        video_name = self.get_selected_video()
        if not video_name:
            messagebox.showwarning("Setup", "Please select or enter a video name")
            return
            
        self.current_video = video_name
        
        if self.state == self.INIT:
            self.serverAddr = self.server_var.get().strip()
            self.serverPort = int(self.port_var.get().strip())
            self.rtpPort = int(self.rtp_port_var.get().strip())
            
            if self.connect_to_server():
                self.send_rtsp_request(self.SETUP)
                self.update_status(f"Setting up: {self.current_video}")
                self.setup_btn.config(state='disabled')
            else:
                self.update_status("Failed to connect to server")

    def play_movie(self):
        """Play the current video"""
        if self.state == self.READY:
            threading.Thread(target=self.listen_rtp, daemon=True).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.send_rtsp_request(self.PLAY)
            self.update_status(f"Playing: {self.current_video}")
            
            self.play_btn.config(state='disabled')
            self.pause_btn.config(state='normal')

    def pause_movie(self):
        """Pause the video"""
        if self.state == self.PLAYING:
            self.send_rtsp_request(self.PAUSE)
            self.update_status(f"Paused: {self.current_video}")
            
            self.play_btn.config(state='normal')
            self.pause_btn.config(state='disabled')

    def teardown_movie(self):
        """Teardown connection"""
        if self.state != self.INIT:
            self.send_rtsp_request(self.TEARDOWN)
            self.cleanup_session()
            self.update_status("Connection closed")
            
            self.setup_btn.config(state='normal')
            self.play_btn.config(state='disabled')
            self.pause_btn.config(state='disabled')
            self.teardown_btn.config(state='disabled')

    def connect_to_server(self):
        """Connect to RTSP server"""
        try:
            self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            return True
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Could not connect to {self.serverAddr}:{self.serverPort}\n{e}")
            return False

    def send_rtsp_request(self, request_code):
        """Send RTSP request to server"""
        if request_code == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recv_rtsp_reply, daemon=True).start()
            
            self.rtspSeq = 1
            request = f"SETUP {self.current_video}\n{self.rtspSeq}\n RTSP/1.0 RTP/UDP {self.rtpPort}"
            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.SETUP

        elif request_code == self.PLAY and self.state == self.READY:
            self.rtspSeq += 1
            request = f"PLAY \n{self.rtspSeq}"
            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.PLAY

        elif request_code == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq += 1
            request = f"PAUSE \n{self.rtspSeq}"
            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.PAUSE

        elif request_code == self.TEARDOWN and self.state != self.INIT:
            self.rtspSeq += 1
            request = f"TEARDOWN \n{self.rtspSeq}"
            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.TEARDOWN

    def recv_rtsp_reply(self):
        """Receive RTSP replies from server"""
        try:
            while True:
                reply = self.rtspSocket.recv(1024)
                if reply:
                    self.parse_rtsp_reply(reply.decode("utf-8"))
                
                if self.requestSent == self.TEARDOWN:
                    break
        except Exception as e:
            print(f"RTSP reply error: {e}")

    def parse_rtsp_reply(self, data):
        """Parse RTSP reply from server"""
        try:
            lines = data.split('\n')
            seq_num = int(lines[1].split(' ')[1])
            
            if seq_num == self.rtspSeq:
                session = int(lines[2].split(' ')[1])
                
                if self.sessionId == 0:
                    self.sessionId = session
                
                if self.sessionId == session:
                    if int(lines[0].split(' ')[1]) == 200:  # OK response
                        if self.requestSent == self.SETUP:
                            self.state = self.READY
                            self.open_rtp_port()
                            self.root.after(0, lambda: self.update_status(f"Ready: {self.current_video}"))
                            self.root.after(0, lambda: self.play_btn.config(state='normal'))
                            self.root.after(0, lambda: self.teardown_btn.config(state='normal'))
                            
                        elif self.requestSent == self.PLAY:
                            self.state = self.PLAYING
                            
                        elif self.requestSent == self.PAUSE:
                            self.state = self.READY
                            if self.playEvent:
                                self.playEvent.set()
                                
                        elif self.requestSent == self.TEARDOWN:
                            self.teardownAcked = 1
                            
        except Exception as e:
            print(f"Error parsing RTSP reply: {e}")

    def open_rtp_port(self):
        """Open RTP socket for receiving video data"""
        try:
            self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtpSocket.settimeout(0.5)
            self.rtpSocket.bind(('', self.rtpPort))
            print(f"RTP socket bound to port {self.rtpPort}")
        except Exception as e:
            messagebox.showerror("RTP Error", f"Could not bind to RTP port {self.rtpPort}: {e}")

    def listen_rtp(self):
        """Listen for RTP packets and update video"""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtp_packet = RtpPacket()
                    rtp_packet.decode(data)
                    
                    curr_frame_nbr = rtp_packet.seqNum()
                    
                    if curr_frame_nbr > self.frameNbr:
                        self.frameNbr = curr_frame_nbr
                        # Update video in main thread
                        self.root.after(0, self.update_video, rtp_packet.getPayload())
                        
            except socket.timeout:
                if self.playEvent and self.playEvent.isSet():
                    break
                continue
            except Exception as e:
                if self.state == self.PLAYING:
                    self.root.after(0, self.pause_movie)
                print(f"RTP receive error: {e}")
                break

    def update_video(self, frame_data):
        """Update the video display with new frame"""
        try:
            # Write frame to temporary file
            cache_name = f"{CACHE_FILE_NAME}{self.sessionId}{CACHE_FILE_EXT}"
            with open(cache_name, "wb") as f:
                f.write(frame_data)
            
            # Load and display image
            image = Image.open(cache_name)
            # Resize image to fit display while maintaining aspect ratio
            display_size = (650, 450)
            image.thumbnail(display_size, Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            self.video_label.config(image=photo, text="")
            self.video_label.image = photo  # Keep reference
            
        except Exception as e:
            print(f"Video update error: {e}")

    def cleanup_session(self):
        """Clean up current session"""
        if self.playEvent:
            self.playEvent.set()
        
        if self.rtpSocket:
            try:
                self.rtpSocket.close()
            except:
                pass
                
        if self.rtspSocket:
            try:
                self.rtspSocket.close()
            except:
                pass
        
        # Clean up cache files
        try:
            for filename in os.listdir():
                if filename.startswith(CACHE_FILE_NAME):
                    os.remove(filename)
        except:
            pass
            
        self.sessionId = 0
        self.rtspSeq = 0
        
        # Clear video display
        self.video_label.config(image="", text="Setup and play a video")
        self.video_label.image = None

    def on_closing(self):
        """Handle window closing"""
        if self.state != self.INIT:
            self.teardown_movie()
        
        self.cleanup_session()
        self.root.destroy()


def main():
    root = tk.Tk()
    client = SimpleRTSPClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()