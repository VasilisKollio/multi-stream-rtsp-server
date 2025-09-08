#!/usr/bin/env python3

import socket
import sys
import time

def test_rtsp_connection(server_addr="localhost", server_port=8554, rtp_port=25000, filename="movie.Mjpeg"):
    """Test RTSP connection step by step with detailed output"""
    
    print("=" * 60)
    print("RTSP Connection Debug Test")
    print("=" * 60)
    print(f"Server: {server_addr}:{server_port}")
    print(f"RTP Port: {rtp_port}")
    print(f"Video: {filename}")
    print("-" * 60)
    
    # Step 1: Test basic TCP connection
    print("Step 1: Testing TCP connection to RTSP server...")
    try:
        rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rtsp_socket.settimeout(5)  # 5 second timeout
        rtsp_socket.connect((server_addr, server_port))
        print("✓ TCP connection successful")
    except Exception as e:
        print(f"✗ TCP connection failed: {e}")
        print("\nPossible solutions:")
        print("1. Make sure your RTSP server is running")
        print("2. Check if the server is listening on the correct port")
        print("3. Verify firewall settings")
        return False
    
    # Step 2: Send SETUP request
    print("\nStep 2: Sending SETUP request...")
    try:
        setup_request = f"SETUP {filename}\n1\n RTSP/1.0 RTP/UDP {rtp_port}"
        print(f"Sending: {repr(setup_request)}")
        
        rtsp_socket.send(setup_request.encode('utf-8'))
        print("✓ SETUP request sent")
        
        # Wait for response with timeout
        print("Waiting for SETUP response...")
        rtsp_socket.settimeout(10)  # 10 second timeout for response
        response = rtsp_socket.recv(1024)
        
        if response:
            response_str = response.decode('utf-8')
            print(f"✓ Received response ({len(response)} bytes):")
            print("-" * 40)
            print(response_str)
            print("-" * 40)
            
            # Parse response
            lines = response_str.split('\n')
            if len(lines) >= 3:
                status_line = lines[0]
                seq_line = lines[1] if len(lines) > 1 else ""
                session_line = lines[2] if len(lines) > 2 else ""
                
                print(f"Status: {status_line}")
                print(f"Sequence: {seq_line}")
                print(f"Session: {session_line}")
                
                if "200 OK" in status_line:
                    print("✓ SETUP successful!")
                    return True
                else:
                    print("✗ SETUP failed - server returned error")
                    return False
            else:
                print("✗ Invalid response format")
                return False
        else:
            print("✗ No response received from server")
            return False
            
    except socket.timeout:
        print("✗ Timeout waiting for server response")
        print("The server might be:")
        print("1. Not processing RTSP requests correctly")
        print("2. Hanging on the request")
        print("3. Not sending proper responses")
        return False
    except Exception as e:
        print(f"✗ Error during SETUP: {e}")
        return False
    finally:
        rtsp_socket.close()

def test_rtp_port(rtp_port=25000):
    """Test if RTP port can be bound"""
    print(f"\nStep 3: Testing RTP port {rtp_port}...")
    try:
        rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rtp_socket.bind(('', rtp_port))
        rtp_socket.close()
        print(f"✓ RTP port {rtp_port} is available")
        return True
    except Exception as e:
        print(f"✗ Cannot bind to RTP port {rtp_port}: {e}")
        print("Try using a different RTP port (e.g., 25001, 25002)")
        return False

def main():
    # Get parameters from command line or use defaults
    server_addr = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8554
    rtp_port = int(sys.argv[3]) if len(sys.argv) > 3 else 25000
    filename = sys.argv[4] if len(sys.argv) > 4 else "movie.Mjpeg"
    
    # Run tests
    tcp_ok = test_rtsp_connection(server_addr, server_port, rtp_port, filename)
    rtp_ok = test_rtp_port(rtp_port)
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"TCP Connection: {'✓ OK' if tcp_ok else '✗ FAILED'}")
    print(f"RTP Port:       {'✓ OK' if rtp_ok else '✗ FAILED'}")
    
    if tcp_ok and rtp_ok:
        print("\n✓ All tests passed! The client should work.")
    else:
        print("\n✗ Issues found. Fix these before running the GUI client.")
        
    print("=" * 60)

if __name__ == "__main__":
    main()