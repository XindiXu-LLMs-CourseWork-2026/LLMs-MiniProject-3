import streamlit as st

from client.openai_client import OpenAIClient

st.title("Mini Project 3: Agentic AI in FinTech")


# Define a function to get the conversation history (Not required for Part-2, will be useful in Part-3)
def get_conversation() -> str:
    # return: A formatted string representation of the conversation.
    # ... (code for getting conversation history)
    conversation = ""
    for msg in st.session_state["messages"]:
        role = msg["role"]
        content = msg["content"]
        conversation += f"{role}: {content}\n"
    return conversation


# Check for existing session state variables
if "openai_model" not in st.session_state:
    # ... (initialize model)
    st.session_state["openai_model"] = 'gpt-3.5-turbo'

if "messages" not in st.session_state:
    # ... (initialize messages)
    st.session_state["messages"] = []

agent_type = st.sidebar.selectbox("Agent selector", ("Single Agent", "Multi-Agent"), index=1)
model_type = st.sidebar.selectbox("Model selector", ("gpt-4o-mini", "gpt-4o"), index=1)
openai_client = OpenAIClient(model_type=model_type)

# Display existing chat messages
# ... (code for displaying messages)
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Wait for user input
if prompt := st.chat_input("What would you like to chat about?"):
    # ... (append user message to messages)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    # ... (display user message)
    with st.chat_message("user"):
        st.markdown(prompt)

    # ... (get AI response and display it)
    conversation_history = get_conversation()  # Get conversation history if needed
    ai_response = ""

    with st.chat_message("assistant"):
        st.markdown(ai_response)

    # ... (append AI response to messages)
    st.session_state.messages.append(
        {"role": "assistant", "content": ai_response}
    )
