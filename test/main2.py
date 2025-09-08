#!/usr/bin/env python3

import socket
import threading
import sys
import os
import glob
from VideoStream import VideoStream
from RtpPacket import RtpPacket
from random import randint

MJPEG_TYPE = 26

class MultiVideoRTSPServer:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    SWITCH = 'SWITCH'  # Custom command for switching videos
    
    INIT = 0
    READY = 1
    PLAYING = 2
    
    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    def __init__(self, video_directory="./", port=8554):
        self.video_directory = video_directory
        self.port = port
        self.available_videos = self.scan_videos()
        self.active_clients = {}
        
        print("Available videos:")
        for i, video in enumerate(self.available_videos):
            print(f"  {i+1}. {video}")

    def scan_videos(self):
        """Scan directory for available video files"""
        video_extensions = ['*.Mjpeg', '*.mjpeg', '*.MJPEG']
        videos = []
        
        for ext in video_extensions:
            videos.extend(glob.glob(os.path.join(self.video_directory, ext)))
        
        # Remove directory path, keep just filename
        videos = [os.path.basename(v) for v in videos]
        return videos

    def start_server(self):
        """Start the multi-video RTSP server"""
        print("=" * 60)
        print(f"Multi-Video RTSP Server")
        print(f"Port: {self.port}")
        print(f"Video Directory: {self.video_directory}")
        print(f"Available Videos: {len(self.available_videos)}")
        print("=" * 60)

        rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rtsp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            rtsp_socket.bind(('', self.port))
            rtsp_socket.listen(10)  # Allow more concurrent connections
            print(f"Server listening on port {self.port}")
            print("Stream URLs:")
            for video in self.available_videos:
                print(f"  rtsp://localhost:{self.port}/{video}")
            print("\nPress Ctrl+C to stop")
            
            while True:
                print(f"\nWaiting for client... (Active: {len(self.active_clients)})")
                client_socket, client_addr = rtsp_socket.accept()
                client_id = f"{client_addr[0]}:{client_addr[1]}"
                print(f"Client connected: {client_id}")
                
                # Handle each client in a separate thread
                client_handler = MultiVideoClientHandler(
                    client_socket, client_addr, self.available_videos, 
                    self.video_directory, client_id
                )
                
                self.active_clients[client_id] = client_handler
                threading.Thread(target=self.handle_client_lifecycle, 
                               args=(client_handler, client_id)).start()
                
        except KeyboardInterrupt:
            print("\nShutting down server...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            rtsp_socket.close()

    def handle_client_lifecycle(self, client_handler, client_id):
        """Handle client connection lifecycle"""
        try:
            client_handler.handle_client()
        finally:
            # Remove client from active list when disconnected
            if client_id in self.active_clients:
                del self.active_clients[client_id]
            print(f"Client {client_id} removed from active list")


class MultiVideoClientHandler:
    def __init__(self, client_socket, client_addr, available_videos, video_directory, client_id):
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.available_videos = available_videos
        self.video_directory = video_directory
        self.client_id = client_id
        
        self.state = MultiVideoRTSPServer.INIT
        self.session_id = randint(100000, 999999)
        
        # Current video being streamed
        self.current_video = None
        self.video_stream = None
        self.rtp_socket = None
        self.rtp_port = None
        self.send_event = None
        self.worker_thread = None

    def handle_client(self):
        """Handle RTSP requests from client"""
        try:
            while True:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                
                request = data.decode("utf-8")
                print(f"[{self.client_id}] Request: {request.split()[0] if request.split() else 'UNKNOWN'}")
                self.process_request(request)
                
        except Exception as e:
            print(f"[{self.client_id}] Client error: {e}")
        finally:
            self.cleanup()

    def process_request(self, data):
        """Process RTSP request with video selection support"""
        request = data.split('\n')
        line1 = request[0].split(' ')
        request_type = line1[0]
        
        # Extract requested video filename
        requested_video = line1[1] if len(line1) > 1 else None
        
        # Parse sequence number
        seq = "1"
        if len(request) > 1:
            second_line = request[1].strip()
            if second_line.isdigit():
                seq = second_line

        # Handle LIST command to return available videos
        if request_type == "LIST":
            self.handle_list(seq)
            return

        # Handle video selection/switching
        if requested_video:
            if requested_video in self.available_videos:
                if self.current_video != requested_video:
                    print(f"[{self.client_id}] Switching to video: {requested_video}")
                    self.switch_video(requested_video)
                self.current_video = requested_video
            else:
                # If video not found, use first available video
                if self.available_videos:
                    self.current_video = self.available_videos[0]
                    print(f"[{self.client_id}] Video not found, using: {self.current_video}")

        if request_type == MultiVideoRTSPServer.SETUP:
            self.handle_setup(seq, request)
        elif request_type == MultiVideoRTSPServer.PLAY:
            self.handle_play(seq)
        elif request_type == MultiVideoRTSPServer.PAUSE:
            self.handle_pause(seq)
        elif request_type == MultiVideoRTSPServer.TEARDOWN:
            self.handle_teardown(seq)

    def handle_list(self, seq):
        """Handle LIST request - return available videos"""
        try:
            # Create response with video list
            video_list = "\n".join(self.available_videos)
            reply = f'RTSP/1.0 200 OK\nCSeq: {seq}\nContent-Type: text/plain\nContent-Length: {len(video_list)}\n\n{video_list}'
            self.client_socket.send(reply.encode())
            print(f"[{self.client_id}] LIST - Sent {len(self.available_videos)} videos")
        except Exception as e:
            print(f"[{self.client_id}] LIST error: {e}")
            reply = f'RTSP/1.0 500 Internal Server Error\nCSeq: {seq}'
            self.client_socket.send(reply.encode())

    def switch_video(self, new_video):
        """Switch to a different video during playback"""
        if self.video_stream:
            # Close current video stream
            self.video_stream.close()
        
        # Open new video stream
        try:
            video_path = os.path.join(self.video_directory, new_video)
            self.video_stream = VideoStream(video_path)
            print(f"[{self.client_id}] Video switched to: {new_video}")
        except Exception as e:
            print(f"[{self.client_id}] Error switching video: {e}")

    def handle_setup(self, seq, request):
        """Handle SETUP request"""
        if self.state == MultiVideoRTSPServer.INIT:
            try:
                # Use current video or first available
                if not self.current_video and self.available_videos:
                    self.current_video = self.available_videos[0]
                
                if not self.current_video:
                    raise IOError("No video files available")
                
                video_path = os.path.join(self.video_directory, self.current_video)
                self.video_stream = VideoStream(video_path)
                self.state = MultiVideoRTSPServer.READY
                
                # Parse RTP port
                self.rtp_port = 25000  # default
                for line in request:
                    if 'RTP/UDP' in line:
                        parts = line.split()
                        for part in parts:
                            if part.isdigit() and int(part) > 1024:
                                self.rtp_port = int(part)
                                break
                        break
                
                self.send_rtsp_reply(MultiVideoRTSPServer.OK_200, seq)
                print(f"[{self.client_id}] SETUP successful")
                print(f"  Video: {self.current_video}")
                print(f"  RTP Port: {self.rtp_port}")
                
            except IOError as e:
                self.send_rtsp_reply(MultiVideoRTSPServer.FILE_NOT_FOUND_404, seq)
                print(f"[{self.client_id}] SETUP failed: {e}")

    def handle_play(self, seq):
        """Handle PLAY request"""
        if self.state == MultiVideoRTSPServer.READY:
            self.state = MultiVideoRTSPServer.PLAYING
            
            # Create RTP socket
            self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Start streaming thread
            self.send_event = threading.Event()
            self.worker_thread = threading.Thread(target=self.send_rtp)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            
            self.send_rtsp_reply(MultiVideoRTSPServer.OK_200, seq)
            print(f"[{self.client_id}] PLAY - Streaming: {self.current_video}")

    def handle_pause(self, seq):
        """Handle PAUSE request"""
        if self.state == MultiVideoRTSPServer.PLAYING:
            self.state = MultiVideoRTSPServer.READY
            
            if self.send_event:
                self.send_event.set()
            
            self.send_rtsp_reply(MultiVideoRTSPServer.OK_200, seq)
            print(f"[{self.client_id}] PAUSE")

    def handle_teardown(self, seq):
        """Handle TEARDOWN request"""
        if self.send_event:
            self.send_event.set()
        
        self.state = MultiVideoRTSPServer.INIT
        self.send_rtsp_reply(MultiVideoRTSPServer.OK_200, seq)
        print(f"[{self.client_id}] TEARDOWN")

    def send_rtp(self):
        """Send RTP packets with continuous looping"""
        frame_delay = 0.04  # 25 FPS (40ms delay)
        
        while True:
            if self.send_event and self.send_event.wait(frame_delay):
                break
            
            if self.video_stream:
                data = self.video_stream.nextFrame()
                if data:
                    frame_number = self.video_stream.frameNbr()
                    rtp_packet = self.make_rtp(data, frame_number)
                    
                    try:
                        self.rtp_socket.sendto(rtp_packet, (self.client_addr[0], self.rtp_port))
                    except Exception as e:
                        print(f"[{self.client_id}] RTP send error: {e}")
                        break
                else:
                    # If no frame data, video might have ended - let VideoStream handle looping
                    continue

    def make_rtp(self, payload, frame_nbr):
        """Create RTP packet"""
        rtp_packet = RtpPacket()
        rtp_packet.encode(2, 0, 0, 0, frame_nbr, 0, MJPEG_TYPE, 0, payload)
        return rtp_packet.getPacket()

    def send_rtsp_reply(self, code, seq):
        """Send RTSP reply"""
        if code == MultiVideoRTSPServer.OK_200:
            reply = f'RTSP/1.0 200 OK\nCSeq: {seq}\nSession: {self.session_id}'
            self.client_socket.send(reply.encode())
        elif code == MultiVideoRTSPServer.FILE_NOT_FOUND_404:
            reply = f'RTSP/1.0 404 NOT FOUND\nCSeq: {seq}'
            self.client_socket.send(reply.encode())

    def cleanup(self):
        """Clean up resources"""
        if self.send_event:
            self.send_event.set()
        
        if self.rtp_socket:
            self.rtp_socket.close()
        
        if self.video_stream:
            self.video_stream.close()
        
        if self.client_socket:
            self.client_socket.close()
        
        print(f"[{self.client_id}] Client disconnected and cleaned up")


def main():
    video_directory = sys.argv[1] if len(sys.argv) > 1 else "./"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8554
    
    # Start the multi-video server
    server = MultiVideoRTSPServer(video_directory, port)
    
    if not server.available_videos:
        print("No .Mjpeg video files found in directory!")
        print("Please add some MJPEG video files and try again.")
        return
    
    server.start_server()

if __name__ == "__main__":
    main()