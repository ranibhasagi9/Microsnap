from google import genai
from google.genai import types
import streamlit as st

import smtplib
import time
from email.mime.text import MIMEText

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    SUMMARY_REQUEST_PROMPT,
    EXAM_MODE_PROMPT,
    MCQ_MODE_PROMPT,
)


# ==================================================
# Gemini API Configuration
# ==================================================

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]


# ==================================================
# Gmail SMTP Configuration
# ==================================================

GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()

MODEL_NAME = "gemini-3.8-flash"


# ==================================================
# Microsnap Onboarding
# ==================================================

if "onboarded" not in st.session_state:

    st.title("Microsnap 🤖")
    st.caption("👋 I'm Snap & Study AI 📚")

    with st.form("onboarding_form"):

        name = st.text_input(
            "👤 Your name",
            placeholder="Enter your name"
        )

        email_address = st.text_input(
            "📧 Gmail address",
            placeholder="example@gmail.com"
        )

        submitted = st.form_submit_button(
            "Let's start learning 🚀"
        )

    # ----------------------------------------------
    # When user clicks Start
    # ----------------------------------------------

    if submitted:

        # Check name and email
        if not name.strip() or not email_address.strip():

            st.warning(
                "⚠️ Please fill in both your name and Gmail address."
            )

        # Basic email validation
        elif "@" not in email_address or "." not in email_address:

            st.warning(
                "📧 Please enter a valid Gmail address."
            )

        else:

            # --------------------------------------
            # Save student's information
            # --------------------------------------

            st.session_state.name = name.strip()

            st.session_state.email_address = (
                email_address.strip()
            )

            # --------------------------------------
            # Create Gemini Chat
            # --------------------------------------

            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                ),
            )

            # --------------------------------------
            # Store messages
            # --------------------------------------

            st.session_state.messages = []

            # --------------------------------------
            # Store quick action
            # --------------------------------------

            st.session_state.quick_action = None

            # --------------------------------------
            # Store uploaded image
            # --------------------------------------

            st.session_state.uploaded_image = None

            # --------------------------------------
            # Mark onboarding completed
            # --------------------------------------

            st.session_state.onboarded = True

            # --------------------------------------
            # Restart application
            # --------------------------------------

            st.rerun()

    # Stop the app here until onboarding is completed
    st.stop()


# ==================================================
# Initialize Session State
# ==================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


if "quick_action" not in st.session_state:

    st.session_state.quick_action = None


if "uploaded_image" not in st.session_state:

    st.session_state.uploaded_image = None


# ==================================================
# Chat Interface
# ==================================================

st.title("Microsnap 🤖")
st.caption("👋 I'm Snap & Study AI 📚")


# ==================================================
# Welcome Message
# ==================================================

if not st.session_state.messages:

    welcome_message = WELCOME_MESSAGE_TEMPLATE.format(
        name=st.session_state.name
    )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "kind": "text",
            "content": welcome_message,
        }
    )


# ==================================================
# Display Messages
# ==================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        if message["kind"] == "text":

            st.write(message["content"])

        elif message["kind"] == "image":

            st.image(
                message["content"],
                caption="📚 Your study material",
                use_container_width=True
            )


# ==================================================
# Gemini Chat Function
# ==================================================

def ask_gemini(parts):

    for attempt in range(3):

        try:

            response = st.session_state.chat.send_message(parts)

            return response.text

        except Exception as error:

            error_text = str(error)

            if "503" in error_text or "UNAVAILABLE" in error_text:

                if attempt < 2:

                    time.sleep(2 ** attempt)
                    continue

                return (
                    "⚠️ Gemini is temporarily busy right now. "
                    "Please try again in a few seconds."
                )

            return f"Sorry, something went wrong: {error_text}"


# ==================================================
# Gmail Send Function
# ==================================================

def send_email(to_address, subject, body):

    message = MIMEText(body, "plain", "utf-8")

    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_address

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:

        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(
            GMAIL_ADDRESS,
            GMAIL_APP_PASSWORD
        )

        server.send_message(message)


# ==================================================
# Add Message Function
# ==================================================

def add_message(role, kind, content):

    st.session_state.messages.append(
        {
            "role": role,
            "kind": kind,
            "content": content,
        }
    )


# ==================================================
# Chat Input + Study Image Upload
# ==================================================

user_input = st.chat_input(
    "Ask a question, or attach a photo of your study material 📚",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)


if user_input:

    photo = (
        user_input.files[0]
        if user_input.files
        else None
    )

    text = user_input.text

    parts = []


    # --------------------------------------------------
    # Handle Uploaded Photo
    # --------------------------------------------------

    if photo is not None:

        photo_bytes = photo.getvalue()

        add_message(
            "user",
            "image",
            photo_bytes
        )

        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type
            )
        )


    # --------------------------------------------------
    # Handle Text Question
    # --------------------------------------------------

    if text:

        add_message(
            "user",
            "text",
            text
        )

        parts.append(text)


    # --------------------------------------------------
    # If Only Photo Was Uploaded
    # --------------------------------------------------

    elif photo is not None:

        parts.append(
            """
            Analyze this study material carefully.

            Identify the question, topic, diagram, notes,
            assignment, or academic content in the image.

            Explain it in simple English.

            Give the important points that a student should
            understand and remember for exams.
            """
        )


    # --------------------------------------------------
    # Send to Gemini
    # --------------------------------------------------

    if parts:

        with st.spinner(
            "📚 Snap & Study AI is thinking..."
        ):

            answer = ask_gemini(parts)


        # ----------------------------------------------
        # Add Gemini Response
        # ----------------------------------------------

        add_message(
            "assistant",
            "text",
            answer
        )


        # ----------------------------------------------
        # Refresh App
        # ----------------------------------------------

        st.rerun()


# ==================================================
# Send Study Summary to Gmail
# ==================================================

st.markdown("### 📧 Study Summary")


if st.button(
    "📧 Send to Gmail",
    use_container_width=True
):

    with st.spinner("📚 Preparing your study summary..."):

        summary = ask_gemini(
            [SUMMARY_REQUEST_PROMPT]
        )


    # Do not send a Gemini error message by email
    if (
        summary.startswith("⚠️")
        or summary.startswith("Sorry, something went wrong")
    ):

        st.error(
            "❌ Gemini could not create the summary. "
            "Please try again."
        )

    else:

        try:

            send_email(
                st.session_state.email_address,
                "📚 Microsnap Study Summary",
                summary
            )

            st.success(
                "✅ Study summary sent to your Gmail!"
            )

        except Exception as error:

            st.error(
                f"❌ Gmail sending failed: {error}"
            )


# ==================================================
# Quick Actions
# ==================================================

st.markdown("### 💡 What would you like to do?")


col1, col2 = st.columns(2)


# --------------------------------------------------
# Left Column
# --------------------------------------------------

with col1:

    if st.button(
        "💡 Explain Simply",
        use_container_width=True
    ):

        st.session_state.quick_action = (
            "Explain the uploaded study material in simple English."
        )

    if st.button(
        "📝 Exam Answer",
        use_container_width=True
    ):

        st.session_state.quick_action = EXAM_MODE_PROMPT

    if st.button(
        "🔑 Key Points",
        use_container_width=True
    ):

        st.session_state.quick_action = (
            "Give me the most important points "
            "from this study material."
        )


# --------------------------------------------------
# Right Column
# --------------------------------------------------

with col2:

    if st.button(
        "❓ Generate MCQs",
        use_container_width=True
    ):

        st.session_state.quick_action = MCQ_MODE_PROMPT

    if st.button(
        "🇮🇳 Explain in Kannada",
        use_container_width=True
    ):

        st.session_state.quick_action = (
            "Explain this study material in simple Kannada."
        )

    if st.button(
        "📖 Summarize",
        use_container_width=True
    ):

        st.session_state.quick_action = SUMMARY_REQUEST_PROMPT


# ==================================================
# Study Tips
# ==================================================
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello! My Flask App is Running Successfully."

if __name__ == '__main__':
    app.run(debug=True)

with st.expander("🎓 Study Tips"):

    st.write(
        """
        💡 Ask me to explain difficult concepts.

        📝 Ask for exam-ready answers.

        ❓ Generate MCQs for practice.

        🔑 Get important points for quick revision.

        🇮🇳 Ask me to explain the topic in Kannada.
        """
    )