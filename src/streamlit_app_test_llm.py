import streamlit as st
import pandas as pd
import os
from components.graph_agent import (
    AzureChatOpenAIWithAAD,
)
import logging

# logging.basicConfig(level=logging.DEBUG)

st.set_page_config(page_title="Brevkoder-automater", layout="wide")
st.title("Brevkoder-automater")

# Set your Azure OpenAI deployment/model name and API version here
azure_Controller = AzureChatOpenAIWithAAD(
    azure_endpoint="https://oai02-aiserv.openai.azure.com/", api_version="2024-10-21"
)
graph = azure_Controller.create_graph_agent(
    azure_deployment="gpt-4.1-nano",
)

# --- Streamlit Chatbot Logic ---

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

st.write("Chat with the LLM below:")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

user_input = st.chat_input("Skriv din besked her...")


def get_graph_response(messages):
    # Use the graph agent to get a response given the conversation history
    events = graph.stream({"messages": messages})
    response = ""
    for event in events:
        for value in event.values():
            response = value["messages"][-1].content
    return response


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("LLM svarer..."):
        response = get_graph_response(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(response)
