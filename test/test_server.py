#!/usr/bin/env python3

import socket
import time

def test_server_connection(host="localhost", port=8554):
    """Test basic server connection and LIST command"""
    
    print(f"Testing connection to {host}:{port}")
    
    try:
        # Test basic TCP connection
        print("1. Testing TCP connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        print("   ✓ TCP connection successful")
        
        # Test LIST command
        print("2. Sending LIST command...")
        list_request = "LIST\n1\n"
        print(f"   Sending: {repr(list_request)}")
        sock.send(list_request.encode('utf-8'))
        
        # Wait for response
        print("3. Waiting for response...")
        sock.settimeout(10)
        response = sock.recv(4096)
        
        if response:
            response_str = response.decode('utf-8')
            print(f"   ✓ Received response ({len(response)} bytes):")
            print("   " + "-" * 50)
            for i, line in enumerate(response_str.split('\n')):
                print(f"   {i:2}: '{line}'")
            print("   " + "-" * 50)
            
            if "200 OK" in response_str:
                print("   ✓ Server supports LIST command")
                return True
            else:
                print("   ✗ Server returned error response")
                return False
        else:
            print("   ✗ No response received")
            return False
            
    except socket.timeout:
        print("   ✗ Connection timed out")
        print("   Server may not be responding or doesn't support LIST")
        return False
    except ConnectionRefusedError:
        print("   ✗ Connection refused")
        print("   Server is not running or wrong port")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def test_old_server_format(host="localhost", port=8554):
    """Test if server is using old SETUP format"""
    
    print(f"\n4. Testing with old SETUP format...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        # Send old SETUP request
        setup_request = "SETUP movie.Mjpeg\n1\n RTSP/1.0 RTP/UDP 25000"
        print(f"   Sending SETUP: {repr(setup_request)}")
        sock.send(setup_request.encode('utf-8'))
        
        sock.settimeout(5)
        response = sock.recv(1024)
        
        if response:
            response_str = response.decode('utf-8')
            print(f"   ✓ SETUP response: {repr(response_str)}")
            if "200 OK" in response_str:
                print("   ✓ Server responds to SETUP (old format)")
                return True
        else:
            print("   ✗ No SETUP response")
            
    except Exception as e:
        print(f"   ✗ SETUP test error: {e}")
        
    finally:
        try:
            sock.close()
        except:
            pass
    
    return False

def main():
    print("=" * 60)
    print("RTSP Server Test")
    print("=" * 60)
    
    # Test LIST command
    list_works = test_server_connection()
    
    # Test old SETUP format  
    setup_works = test_old_server_format()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"LIST command:  {'✓ Works' if list_works else '✗ Failed'}")
    print(f"SETUP command: {'✓ Works' if setup_works else '✗ Failed'}")
    
    if not list_works and setup_works:
        print("\nDIAGNOSIS: Server is running OLD code without LIST support")
        print("SOLUTION: Use the updated multi_server.py code")
        
    elif not list_works and not setup_works:
        print("\nDIAGNOSIS: Server not running or not responding")
        print("SOLUTION: Start your RTSP server first")
        
    elif list_works:
        print("\nDIAGNOSIS: Server supports LIST - discovery should work")
        print("SOLUTION: Check client code or network issues")
        
    print("=" * 60)

if __name__ == "__main__":
    main()