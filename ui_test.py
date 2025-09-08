import streamlit as st
import requests
import subprocess

st.title(" RTSP Stream Server")

# Base URL
BASE_URL = "http://localhost:5000"


# UPLOAD & START STREAM
st.header(" Upload & Start Stream")

uploaded_file = st.file_uploader(
    "Choose a video file", 
    type=['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm']
)

stream_name = st.text_input(
    "Stream Name", 
    help="Letters, numbers, underscores, and hyphens only"
)

if st.button("Start Stream", type="primary"):
    if uploaded_file and stream_name:
        with st.spinner("Starting stream..."):
            files = {'file': uploaded_file}
            data = {'stream_name': stream_name}
            
            try:
                response = requests.post(f'{BASE_URL}/upload', files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(" Stream started successfully!")
                    
                    if 'rtsp_url' in result:
                        rtsp_url = result['rtsp_url']
                        st.info(f" RTSP URL: `{rtsp_url}`")
                    
                    # Show response details
                    with st.expander(" Response Details"):
                        st.json(result)
                else:
                    error_data = response.json() if response.content else {}
                    st.error(f" Error: {error_data.get('error', 'Unknown error')}")
                    
            except requests.exceptions.RequestException as e:
                st.error(f" Connection error: {str(e)}")
    else:
        st.warning(" Please select a file and enter a stream name")


# VIEW ACTIVE STREAMS
st.header(" Active Streams")

if st.button(" Refresh Streams"):
    st.rerun()

try:
    response = requests.get(f'{BASE_URL}/status')
    
    if response.status_code == 200:
        status_data = response.json()
        
        st.metric("Server", status_data.get('rtsp_server', 'Unknown'))
        st.metric("Total Streams", status_data.get('total_streams', 0))
    
        # Show active streams
        streams = status_data.get('streams', {})
        
        if streams:
            st.subheader(" Active Streams")
            
            for stream_name, stream_info in streams.items():
                with st.expander(f" {stream_name} - {' Running' if stream_info.get('is_running') else ' Stopped'}"):                   
                    
                        st.write(f"**Filename:** `{stream_info.get('filename', 'N/A')}`")
                        st.write(f"**Status:** `{' Running' if stream_info.get('is_running') else ' Stopped'}`")
                        st.write(f"**RTSP URL:** `{stream_info.get('rtsp_url', 'N/A')}`")
                        st.write(f"**Uptime:** `{round(stream_info.get('uptime_seconds', 0) / 60, 1)}` minutes")
                        
                        if stream_info.get('pid'):
                            st.write(f"**Process ID:** {stream_info.get('pid')}")
                    
                        # Copy URL button
                        st.code(stream_info.get('rtsp_url', ''), language='text')
        else:
            st.info("No active streams. Upload a video to start streaming.")
    else:
        st.error(" Could not get stream status")
        
except requests.exceptions.RequestException as e:
    st.error(f" Connection error: {str(e)}")


# SERVER STATUS
st.header(" Server Status")

try:
    response = requests.get(f'{BASE_URL}/')
    
    if response.status_code == 200:
        server_info = response.json()
        st.success(" Server is running on Docker")
                
        # Show all server info
        with st.expander(" Full Server Response"):
            st.json(server_info)
    else:
        st.error(" Server not responding properly")
        
except requests.exceptions.RequestException as e:
    st.error(f" Cannot connect to server: {str(e)}")
    st.info("Make sure your Flask server is running on http://localhost:5000")

