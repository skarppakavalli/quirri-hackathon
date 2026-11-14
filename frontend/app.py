
import os
import hashlib

import requests
import streamlit as st


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

# Local backend URL.
# When deployed, change this using the API_BASE_URL environment variable.
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"
)

st.set_page_config(
    page_title="KIT AI Assistant",
    page_icon="🎓",
    layout="centered"
)


# --------------------------------------------------
# 2. SESSION STATE
# --------------------------------------------------

# Streamlit reruns the script after every interaction.
# Session state preserves data across those reruns.

defaults = {
    "session_id": None,
    "user": None,
    "messages": [],
    "pending_confirmation": None,
    "last_audio_hash": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --------------------------------------------------
# 3. API HELPER
# --------------------------------------------------

def api_request(method, endpoint, **kwargs):
    """Send a request to our FastAPI backend."""

    response = requests.request(
        method,
        f"{API_BASE_URL}{endpoint}",
        timeout=90,
        **kwargs
    )

    if not response.ok:
        try:
            error = response.json()
        except ValueError:
            error = response.text

        raise Exception(f"API error {response.status_code}: {error}")

    return response


def session_headers():
    """Attach the opaque session ID, never the college access token."""

    return {
        "X-Session-Id": st.session_state.session_id
    }


# --------------------------------------------------
# 4. LOGIN
# --------------------------------------------------

def login(login_id, password):
    response = api_request(
        "POST",
        "/auth/login",
        json={
            "login_id": login_id,
            "password": password
        }
    )

    data = response.json()

    # The backend returns a session ID, not the college token.
    st.session_state.session_id = data["session_id"]
    st.session_state.user = data["user"]

    st.session_state.messages = []
    st.session_state.pending_confirmation = None


def logout():
    for key in defaults:
        st.session_state[key] = defaults[key]

    st.rerun()


# --------------------------------------------------
# 5. TEXT-TO-SPEECH
# --------------------------------------------------

def generate_audio(text):
    """Generate speech. If TTS fails, continue with text."""

    try:
        response = api_request(
            "POST",
            "/voice/speak",
            json={"text": text}
        )

        return response.content

    except Exception as error:
        print("TTS unavailable:", error)
        return None


# --------------------------------------------------
# 6. CHAT FUNCTION
# --------------------------------------------------

def send_message(message):
    """Send the user's message to the LangGraph agent."""

    message = message.strip()

    if not message:
        return

    st.session_state.messages.append({
        "role": "user",
        "content": message
    })

    try:
        response = api_request(
            "POST",
            "/chat",
            headers=session_headers(),
            json={"message": message}
        )

        data = response.json()

        reply = data.get("reply", "I couldn't generate a response.")

        # Store the assistant response.
        st.session_state.messages.append({
            "role": "assistant",
            "content": reply,
            "audio": generate_audio(reply)
        })

        # Keep the pending OD/leave draft for explicit confirmation.
        st.session_state.pending_confirmation = data.get(
            "pending_confirmation"
        )

    except Exception as error:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Sorry, something went wrong: {error}",
            "audio": None
        })

    st.rerun()


# --------------------------------------------------
# 7. VOICE INPUT
# --------------------------------------------------

def process_audio(audio_file):
    """Transcribe recorded audio using Deepgram via FastAPI."""

    audio_bytes = audio_file.getvalue()

    # Prevent the same recording from being processed repeatedly
    # during Streamlit reruns.
    audio_hash = hashlib.sha256(audio_bytes).hexdigest()

    if audio_hash == st.session_state.last_audio_hash:
        return

    st.session_state.last_audio_hash = audio_hash

    try:
        response = api_request(
            "POST",
            "/voice/transcribe",
            headers=session_headers(),
            files={
                "file": (
                    "recording.wav",
                    audio_bytes,
                    audio_file.type or "audio/wav"
                )
            }
        )

        data = response.json()

        # Adjust this key if your backend uses a different response name.
        transcript = data.get("transcript", "").strip()

        if transcript:
            st.success(f"Transcribed: {transcript}")
            send_message(transcript)
        else:
            st.warning("I couldn't recognize your speech. Please try again.")

    except Exception as error:
        st.error(f"Voice transcription failed: {error}")
        st.info("You can use the text chat as a fallback.")


# --------------------------------------------------
# 8. LEAVE / OD CONFIRMATION
# --------------------------------------------------

def confirm_request():
    """Submit a draft only after the student clicks Confirm."""

    draft = st.session_state.pending_confirmation

    if not draft:
        return

    draft_id = draft["draft_id"]

    try:
        response = api_request(
            "POST",
            f"/requests/{draft_id}/confirm",
            headers=session_headers()
        )

        result = response.json()

        confirmation_message = (
            f"Your request was submitted successfully. "
            f"Current status: {result.get('status', 'unknown')}."
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": confirmation_message,
            "audio": generate_audio(confirmation_message)
        })

        st.session_state.pending_confirmation = None
        st.rerun()

    except Exception as error:
        st.error(f"Could not submit your request: {error}")


# --------------------------------------------------
# 9. APPLICATION UI
# --------------------------------------------------

st.title("🎓 KIT AI Assistant")
st.caption("Your campus assistant for academic and administrative queries.")

# ---------------- LOGIN SCREEN ----------------

if not st.session_state.session_id:

    st.subheader("Student / Teacher Login")

    with st.form("login_form"):

        login_id = st.text_input("Login ID")
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True
        )

        if submitted:
            try:
                login(login_id, password)
                st.rerun()

            except Exception as error:
                st.error(f"Login failed: {error}")

    st.stop()


# ---------------- LOGGED-IN SCREEN ----------------

user = st.session_state.user

st.write(
    f"Welcome, **{user.get('full_name', 'Student')}**!"
)

col1, col2 = st.columns([3, 1])

with col1:
    st.caption(f"Role: {user.get('role', 'User')}")

with col2:
    if st.button("Logout"):
        logout()


st.divider()


# ---------------- CHAT HISTORY ----------------

st.subheader("Chat")

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])

        # Play the assistant's generated audio if available.
        if message["role"] == "assistant" and message.get("audio"):
            st.audio(
                message["audio"],
                format="audio/mpeg"
            )


# ---------------- PENDING REQUEST ----------------

draft = st.session_state.pending_confirmation

if draft:

    st.divider()
    st.subheader("Review your request")

    request = draft["request"]

    st.write("Please check the details before submission.")

    st.json(request)

    st.warning(
        "This request has not been submitted yet."
    )

    if st.button(
        "Confirm and Submit Request",
        type="primary",
        use_container_width=True
    ):
        confirm_request()


# ---------------- TEXT INPUT ----------------

user_message = st.chat_input(
    "Ask about attendance, timetable, leave, OD..."
)

if user_message:
    send_message(user_message)


# ---------------- VOICE INPUT ----------------

st.divider()
st.subheader("🎙️ Ask using your voice")

audio_file = st.audio_input(
    "Record your question"
)

if audio_file:
    process_audio(audio_file)
