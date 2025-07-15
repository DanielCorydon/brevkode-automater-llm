import os
import pandas as pd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

# Import tool functions from tools.py
from components.tools import (
    search_and_replace,
    replace_titels_with_nogle,
)


# --- Minimal Excel mapping loader ---
def load_excel_mapping(path):
    try:
        df = pd.read_excel(path, sheet_name=None)
        # Try to find the right sheet ("query" or first sheet)
        sheet = df["query"] if "query" in df else next(iter(df.values()))
        # Expect columns: "Titel" and "Nøgle"
        if "Titel" in sheet.columns and "Nøgle" in sheet.columns:
            return dict(zip(sheet["Titel"], sheet["Nøgle"]))
    except Exception:
        pass
    return {}


# Path to default mapping Excel
DEFAULT_MAPPING_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "documents",
    "Liste over alle nøgler.xlsx",
)
MAPPINGS_DICT = load_excel_mapping(DEFAULT_MAPPING_PATH)

credential = DefaultAzureCredential(
    exclude_environment_credential=True,
    exclude_developer_cli_credential=True,
    exclude_workload_identity_credential=True,
    exclude_managed_identity_credential=True,
    exclude_visual_studio_code_credential=True,
    exclude_shared_token_cache_credential=True,
    exclude_interactive_browser_credential=True,
)
token_provider = get_bearer_token_provider(
    credential, "https://cognitiveservices.azure.com/.default"
)

llm = AzureChatOpenAI(
    azure_endpoint="https://oai02-aiserv.openai.azure.com/",
    api_version="2024-10-21",
    azure_ad_token_provider=token_provider,
    azure_deployment="gpt-4o-2024-08-06",
)
llm_with_tools = llm.bind_tools([search_and_replace, replace_titels_with_nogle])


def tool_calling_llm(state: MessagesState):
    # LLM should output a dict: {"content": ...} or {"tool_call": {"tool": ..., "tool_input": {...}}}
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


graph_builder = StateGraph(MessagesState)
# *** NODES ***
graph_builder.add_node(
    "tool_calling_llm",
    tool_calling_llm,
)
graph_builder.add_node(
    "tools",
    ToolNode([search_and_replace, replace_titels_with_nogle]),
)

# *** EDGES ***

# ReAct-style recursive agent: tools node loops back to LLM node
graph_builder.add_edge(START, "tool_calling_llm")
graph_builder.add_conditional_edges(
    "tool_calling_llm",
    tools_condition,  # routes to tools or END
)
graph_builder.add_edge("tools", "tool_calling_llm")

graph = graph_builder.compile()
