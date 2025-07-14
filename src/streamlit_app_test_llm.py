# import streamlit as st
from components.graph_agent import (
    AzureChatOpenAIWithAAD,
)
import logging
from langchain_core.messages import HumanMessage


# logging.basicConfig(level=logging.DEBUG)

# st.set_page_config(page_title="Brevkoder-automater", layout="wide")
# st.title("Brevkoder-automater")

# Set your Azure OpenAI deployment/model name and API version here
azure_Controller = AzureChatOpenAIWithAAD(
    azure_endpoint="https://oai02-aiserv.openai.azure.com/", api_version="2024-10-21"
)
graph = azure_Controller.create_graph_agent(
    azure_deployment="gpt-4.1-nano",
)

# st.write("Chat with the LLM below:")

# --- Show Graph PNG Button ---
# if st.button("Vis Graph PNG"):  # Danish for 'Show Graph PNG'
#     try:
#         graph_png_bytes = azure_Controller.get_graph_png_bytes()
#         st.image(
#             graph_png_bytes, caption="Graph PNG", use_container_width=False, width=300
#         )
#     except Exception as e:
#         st.error(f"Kunne ikke vise grafen: {e}")

messages = [HumanMessage(content="Hello, what is 2 multiplied by 2?")]
messages = graph.invoke({"messages": messages}, recursion_limit=10)
for m in messages["messages"]:
    m.pretty_print()
