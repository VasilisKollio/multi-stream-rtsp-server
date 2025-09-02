import streamlit as st
import requests

st.title(" RTSP Stream Server")

uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'avi', 'mov'])
stream_name = st.text_input("Stream Name")

if st.button("Start Stream"):
    if uploaded_file and stream_name:
        # Send to Flask server
        files = {'file': uploaded_file}
        data = {'stream_name': stream_name}
        response = requests.post('http://localhost:5000/upload', files=files, data=data)
        st.success(f"Stream started: {response.json()}")