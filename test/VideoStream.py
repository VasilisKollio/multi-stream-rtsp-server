#!/usr/bin/env python3

class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except Exception as e:
            raise IOError(f"Could not open file: {filename}. Error: {e}")
        self.frameNum = 0
        print(f"VideoStream initialized with file: {filename}")
        
    def nextFrame(self):
        """Get next frame with automatic looping"""
        try:
            # Read frame length (first 5 bytes)
            data = self.file.read(5)
            
            # If end of file reached, loop back to beginning
            if not data or len(data) < 5:
                print("End of video reached, looping...")
                self.file.seek(0)
                self.frameNum = 0
                data = self.file.read(5)
            
            if data and len(data) == 5:
                try:
                    framelength = int(data)
                except ValueError:
                    # If we can't convert to int, try to recover
                    print(f"Invalid frame length data: {data}")
                    self.file.seek(0)
                    self.frameNum = 0
                    return None
                
                # Read the actual frame data
                frame_data = self.file.read(framelength)
                
                # If incomplete frame, loop back
                if not frame_data or len(frame_data) < framelength:
                    print("Incomplete frame data, looping...")
                    self.file.seek(0)
                    self.frameNum = 0
                    data = self.file.read(5)
                    if data and len(data) == 5:
                        try:
                            framelength = int(data)
                            frame_data = self.file.read(framelength)
                        except:
                            return None
                    else:
                        return None
                
                self.frameNum += 1
                return frame_data
            
        except Exception as e:
            print(f"Error reading frame: {e}")
            # Try to recover by seeking to beginning
            try:
                self.file.seek(0)
                self.frameNum = 0
            except:
                pass
        
        return None
        
    def frameNbr(self):
        """Get current frame number"""
        return self.frameNum
    
    def close(self):
        """Close the video file"""
        if hasattr(self, 'file') and self.file:
            self.file.close()

if __name__ == "__main__":
    # Test the VideoStream class
    import sys
    if len(sys.argv) > 1:
        vs = VideoStream(sys.argv[1])
        frame = vs.nextFrame()
        if frame:
            print(f"Successfully read frame {vs.frameNbr()}, size: {len(frame)} bytes")
        else:
            print("Failed to read frame")
        vs.close()