from openai import OpenAI
import streamlit as st
from google.oauth2.service_account import Credentials
from streamlit_feedback import streamlit_feedback
import datetime
import streamlit_analytics2 as streamlit_analytics
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, firestore
import json


# db = firestore.Client.from_service_account_json("firestore-key.json")

# def check_password():
#     """Returns `True` if the user had the correct username and password."""
#     def credentials_entered():
#         """Checks whether the username and password entered by the user are correct."""
#         username = st.session_state["username"]
#         password = st.session_state["password"]
        
#         if username.endswith("octo.ai") and hmac.compare_digest(password, "1234"):
#             st.session_state["credentials_correct"] = True
#             st.session_state["username"] = username  # Store the username in session state
#             # del st.session_state["username"]  # Don't store the username.
#             del st.session_state["password"]  # Don't store the password.
#         else:
#             st.session_state["credentials_correct"] = False

#     # Return True if the credentials are validated.
#     if st.session_state.get("credentials_correct", False):
#         return True

#     # Show input for username and password.
#     st.text_input("Username", key="username", on_change=credentials_entered)
#     st.text_input("Password", type="password", key="password", on_change=credentials_entered)
    
#     if "credentials_correct" in st.session_state and not st.session_state["credentials_correct"]:
#         st.error("😕 Username or password incorrect")
#     return False

# if not check_password():
#     st.stop()  # Do not continue if check_password is not True.

def main():
    with st.sidebar:
        st.sidebar.header("Co-Pilot Information");
        st.sidebar.markdown('''
            <small> LLM Memory Usage is calculated as follows </small>:
        ''', unsafe_allow_html=True)
        latext = r'''
    $$ 
    M = \left( \frac{P \cdot 4B}{\frac{32}{Q}} \right) \times 1.2 
    $$ 
    '''
        st.write(latext)
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
    

        st.sidebar.markdown('''<hr>''', unsafe_allow_html=True)
        st.sidebar.markdown('''<small>GPU Bot v0.1 | Jul 2024 | Contact: Shelby Thomas | sthomas@octo.ai </small>''', unsafe_allow_html=True)
 
    st.title("🐙 GTM Co-Pilot")
    st.markdown("<h6> Co-Pilot may product inaccurate outputs double check outputs.</span>  <br> All prompts are logged anonymously for improvement. <br> Please up and downvote responses to improve accuracy. </h6>", unsafe_allow_html=True)


    # System message containing the blog post
    system_message = {
        "role": "system",
        "content": st.secrets["llm_system_prompt"]["prompt"]
    }

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "I'm ready to answer questions about an LLMs Memory Usage, GPU capabilities, and Octo's available GPUs."}]
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": "I'm ready to answer questions about an LLMs Memory Usage, GPU capabilities, and Octo's available GPUs."}
        ]
    
    if "response" not in st.session_state:
        st.session_state["response"] = None

    # Display chat messages
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
 
    if prompt := st.chat_input("Message"):
        client = OpenAI(api_key=st.secrets["inference_api_key"]["key"],
                        base_url="https://text.octoai.run/v1")
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # Include the system message in the API request
        messages_for_api = [system_message] + st.session_state.messages
        response = client.chat.completions.create(model="meta-llama-3.1-70b-instruct", messages=messages_for_api, max_tokens=4096)
        msg = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.session_state["response"] = msg  # Set the response in session state
        st.chat_message("assistant").write(msg)
   
    def write_feedback_to_gsheet(who, up_down, feedback_message, chat_history, timestamp):
                # Create a reference to the feedback collection
        feedback_ref = db.collection("feedback")

        # Create a new feedback document
        feedback_ref.add({
            "who": who,
            "up_down": up_down,
            "feedback_message": feedback_message,
            "chat_history": chat_history,
            "timestamp": timestamp
        })

        # Define the scope
        # scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

        # # Add credentials to the account
        # creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)

        # # Authorize the clientsheet 
        # client = gspread.authorize(creds)

        # # Get the instance of the Spreadsheet
        # sheet = client.open("FeedbackSheet").sheet1  # Replace "FeedbackSheet" with your Google Sheet name

        # # Add the feedback to the sheet
        # sheet.append_row([who, up_down, feedback_message, chat_history, timestamp])

    # Your existing code
    if st.session_state["response"]:
        feedback = streamlit_feedback(
            feedback_type="thumbs",
            optional_text_label="[Optional]",
            # key=f"feedback_{len(st.session_state.messages)}",
            key="feedback",
        )
        if feedback:
            who = st.session_state.get('username','anon')  # Get the username from session state or use "Anonymous"
            feedback_score = feedback.get("score")
            up_down = feedback_score 
            feedback_message = feedback.get("text", "")
            chat_history = str(st.session_state.messages)  # Convert chat history to string
            timestamp = datetime.datetime.now().isoformat()  # Get the current timestamp

            # Write feedback to Google Sheets
            write_feedback_to_gsheet(who, up_down, feedback_message, chat_history, timestamp)

            st.toast("Feedback recorded!", icon="📝")
            
with streamlit_analytics.track(firestore_collection_name="counts", streamlit_secrets_firestore_key="firebase", firestore_project_name="octo-gtmbot"):
    
    if not firebase_admin._apps:
        firebase_config = json.loads(st.secrets["firebase"])
        cred = credentials.Certificate((firebase_config))
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()

    main()