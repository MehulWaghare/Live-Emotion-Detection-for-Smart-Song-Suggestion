import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import cv2 
import numpy as np 
import mediapipe as mp 
from keras.models import load_model
import webbrowser
import os

# Load Model and Labels
try:
    model = load_model("model.h5")
    label = np.load("labels.npy")
except Exception as e:
    st.error(f"Error loading model or labels: {e}")
    st.stop()

# Initialize Mediapipe
holistic = mp.solutions.holistic
hands = mp.solutions.hands
holis = holistic.Holistic()
drawing = mp.solutions.drawing_utils

st.header("Emotion-Based Music Recommender")

# Session State Initialization
if "run" not in st.session_state:
    st.session_state["run"] = "true"

# Load Emotion File
emotion = ""
if os.path.exists("emotion.npy"):
    try:
        emotion = np.load("emotion.npy")[0]
    except Exception:
        emotion = ""

# Update session state based on emotion
st.session_state["run"] = "true" if not emotion else "false"

# Emotion Processor Class
class EmotionProcessor:
    def recv(self, frame):
        frm = frame.to_ndarray(format="bgr24")

        # Flip Image for Better Orientation
        frm = cv2.flip(frm, 1)

        res = holis.process(cv2.cvtColor(frm, cv2.COLOR_BGR2RGB))

        lst = []

        if res.face_landmarks:
            for i in res.face_landmarks.landmark:
                lst.append(i.x - res.face_landmarks.landmark[1].x)
                lst.append(i.y - res.face_landmarks.landmark[1].y)

            if res.left_hand_landmarks:
                for i in res.left_hand_landmarks.landmark:
                    lst.append(i.x - res.left_hand_landmarks.landmark[8].x)
                    lst.append(i.y - res.left_hand_landmarks.landmark[8].y)
            else:
                lst.extend([0.0] * 42)  # Append 42 zero values

            if res.right_hand_landmarks:
                for i in res.right_hand_landmarks.landmark:
                    lst.append(i.x - res.right_hand_landmarks.landmark[8].x)
                    lst.append(i.y - res.right_hand_landmarks.landmark[8].y)
            else:
                lst.extend([0.0] * 42)  # Append 42 zero values

            lst = np.array(lst).reshape(1, -1)

            try:
                pred = label[np.argmax(model.predict(lst))]
            except Exception:
                pred = "Unknown"

            print(pred)
            cv2.putText(frm, str(pred), (50, 50), cv2.FONT_ITALIC, 1, (255, 0, 0), 2)

            np.save("emotion.npy", np.array([pred]))

        # Draw Face and Hand Landmarks
        drawing.draw_landmarks(frm, res.face_landmarks, holistic.FACEMESH_TESSELATION,
                               landmark_drawing_spec=drawing.DrawingSpec(color=(0, 0, 255), thickness=-1, circle_radius=1),
                               connection_drawing_spec=drawing.DrawingSpec(thickness=1))
        drawing.draw_landmarks(frm, res.left_hand_landmarks, hands.HAND_CONNECTIONS)
        drawing.draw_landmarks(frm, res.right_hand_landmarks, hands.HAND_CONNECTIONS)

        return av.VideoFrame.from_ndarray(frm, format="bgr24")

# Input Fields
lang = st.text_input("Language")
singer = st.text_input("Singer")

if lang and singer and st.session_state["run"] != "false":
    webrtc_streamer(key="key", desired_playing_state=True, video_processor_factory=EmotionProcessor)

btn = st.button("Recommend me songs")

if btn:
    if not emotion:
        st.warning("Please let me capture your emotion first")
        st.session_state["run"] = "true"
    else:
        search_query = f"https://www.youtube.com/results?search_query={lang}+{emotion}+song+{singer}"
        webbrowser.open(search_query)
        np.save("emotion.npy", np.array([""]))
        st.session_state["run"] = "false"
