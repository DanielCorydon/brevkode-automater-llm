from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition


def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b


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
    azure_deployment="gpt-4.1-nano",
)
llm_with_tools = llm.bind_tools(
    # [replace_string_in_text, multiply],
    [multiply]
)


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
    # ToolNode([multiply, replace_string_in_text]),
    ToolNode([multiply]),
)

# *** EDGES ***
graph_builder.add_edge(START, "tool_calling_llm")
graph_builder.add_conditional_edges(
    "tool_calling_llm",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
graph_builder.add_edge("tools", END)

graph = graph_builder.compile()
