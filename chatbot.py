import streamlit as st
from openai import OpenAI
from streamlit_feedback import streamlit_feedback
import datetime
import streamlit_analytics2 as streamlit_analytics
import firebase_admin
from firebase_admin import credentials, firestore
import json

MODEL_NAME = "meta-llama-3.1-70b-instruct"
API_KEY = st.secrets["inference_api_key"]["key"]
BASE_URL = st.secrets["inference_api_key"]["base_url"]
SYSTEM_PROMPT = st.secrets["llm_system_prompt"]["prompt"]

def initialize_firebase():
    if not firebase_admin._apps:
        firebase_config = json.loads(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def render_sidebar():
    st.sidebar.header("Co-Pilot Information")
    st.sidebar.markdown('''
        <small> LLM Memory Usage is calculated as follows </small>:
    ''', unsafe_allow_html=True)
    latext = r'''
    $$ 
    M = \left( \frac{P \cdot 4B}{\frac{32}{Q}} \right) \times 1.2 
    $$ 
    '''
    st.sidebar.write(latext)
    st.sidebar.markdown('''
    | Symbol | Description |
    |--------|-------------|
    | M      | GPU memory expressed in Gigabyte |
    | P      | The amount of parameters in the model. E.g. a 7B model has 7 billion parameters. |
    | 4B     | 4 bytes, expressing the bytes used for each parameter |
    | 32     | There are 32 bits in 4 bytes |
    | Q      | The amount of bits that should be used for loading the model. E.g. 16 bits, 8 bits or 4 bits. |
    | 1.2    | Represents a 20% overhead of loading additional things in GPU memory. |
    ''', unsafe_allow_html=True)
    st.sidebar.markdown('<hr>', unsafe_allow_html=True)
    st.sidebar.markdown('''
        <small>GPU Bot v0.1 | Jul 2024 | Contact: Shelby Thomas | sthomas@octo.ai | <a href="https://github.com/octoml/octo-bots-mirror" target="_blank">Github</a> </small>
    ''', unsafe_allow_html=True)

def render_main_content():
    st.title("🐙 GPU and LLM Memory Usage")
    st.markdown('''
        <h6> Co-Pilot may produce inaccurate outputs; double-check outputs.</span>  
        <br> All prompts are logged anonymously for improvement. 
        <br> Please up and downvote responses to improve accuracy. </h6>
    ''', unsafe_allow_html=True)

def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": "I'm ready to answer questions about an LLMs Memory Usage, GPU capabilities, and Octo's available GPUs."}
        ]
    if "response" not in st.session_state:
        st.session_state["response"] = None

def display_chat_messages():
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

def handle_user_input(client, system_message):
    if prompt := st.chat_input("Message"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # Only send the system message and the latest user message
        messages_for_api = [system_message, {"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model=MODEL_NAME, 
            messages=messages_for_api, 
            max_tokens=4096
        )
        msg = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.session_state["response"] = msg
        st.chat_message("assistant").write(msg)

def write_feedback_to_firestore(db, who, up_down, feedback_message, chat_history, timestamp):
    feedback_ref = db.collection("feedback")
    feedback_ref.add({
        "who": who,
        "up_down": up_down,
        "feedback_message": feedback_message,
        "chat_history": chat_history,
        "timestamp": timestamp
    })

def handle_feedback(db):
    if st.session_state["response"]:
        feedback = streamlit_feedback(
            feedback_type="thumbs",
            optional_text_label="[Optional]",
            key="feedback",
        )
        if feedback:
            who = st.session_state.get('username', 'anon')
            feedback_score = feedback.get("score")
            up_down = feedback_score
            feedback_message = feedback.get("text", "")
            chat_history = str(st.session_state.messages)
            timestamp = datetime.datetime.now().isoformat()

            write_feedback_to_firestore(db, who, up_down, feedback_message, chat_history, timestamp)
            st.toast("Feedback recorded!", icon="📝")

def main():
    render_sidebar()
    render_main_content()
    initialize_session_state()
    display_chat_messages()

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    system_message = {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
    handle_user_input(client, system_message)
    handle_feedback(db)

# analytics and Firebase initialization
with streamlit_analytics.track(firestore_collection_name="counts", streamlit_secrets_firestore_key="firebase", firestore_project_name="octo-gtmbot"):
    db = initialize_firebase()
    main()