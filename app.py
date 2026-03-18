import streamlit as st

from agents.multi_agent import run_multi_agent
from agents.single_agent import run_single_agent

st.title("Mini Project 3: Agentic AI in FinTech")


def get_conversation() -> str:
    # return: A formatted string representation of the conversation.
    # ... (code for getting conversation history)
    conversation = ""
    for msg in st.session_state["messages"]:
        role = msg["role"]
        content = msg["content"]
        conversation += f"{role}: {content}\n"
    return conversation

if "messages" not in st.session_state:
    # ... (initialize messages)
    st.session_state["messages"] = []

def clear_conversation():
    st.session_state.messages = []

with st.sidebar:
    agent_type = st.selectbox("Agent selector", ("Single Agent", "Multi Agent"), index=0)
    model_type = st.selectbox("Model selector", ("gpt-4o-mini", "gpt-4o"), index=0)
    st.button("Clear Conversation", on_click=clear_conversation, use_container_width=True)

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
    if agent_type == "Single Agent":
        agent_result = run_single_agent(prompt, conv_hist=conversation_history, active_model=model_type)
        ai_response = agent_result.answer
    elif agent_type == "Multi Agent":
        agent_result = run_multi_agent(prompt, conversation_history, model_type)
        ai_response = agent_result.get("final_answer", "")

    with st.chat_message("assistant"):
        response = f"Response generated using {agent_type} and {model_type}.\n\n {ai_response}"
        st.markdown(response)

    # ... (append AI response to messages)
    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )
