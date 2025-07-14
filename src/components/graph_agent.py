from typing_extensions import TypedDict
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated
from components.graph_tools import replace_string_in_text, multiply


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


# Wrapper to use Azure AD token for AzureChatOpenAI and auto-refresh when expired
class AzureChatOpenAIWithAAD:
    def __init__(
        self,
        azure_endpoint="https://oai02-aiserv.openai.azure.com/",
        api_version="2024-10-21",
    ):
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        self.credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_developer_cli_credential=True,
            exclude_workload_identity_credential=True,
            exclude_managed_identity_credential=True,
            exclude_visual_studio_code_credential=True,
            exclude_shared_token_cache_credential=True,
            exclude_interactive_browser_credential=True,
        )
        self.token_provider = get_bearer_token_provider(
            self.credential, "https://cognitiveservices.azure.com/.default"
        )
        self.graph = None

    def create_graph_agent(
        self,
        azure_deployment="gpt-4.1-nano",
    ):
        """
        Creates a StateGraph for the graph agent with the specified Azure OpenAI parameters.
        Adds a router node so the LLM can decide tool usage and input based on the prompt.
        """
        from .graph_tools import replace_string_in_text

        llm = AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_version=self.api_version,
            azure_ad_token_provider=self.token_provider,
            azure_deployment=azure_deployment,
        )
        llm_with_tools = llm.bind_tools(
            # [replace_string_in_text, multiply],
            [multiply]
        )

        def tool_calling_llm(state: MessagesState):
            # LLM should output a dict: {"content": ...} or {"tool_call": {"tool": ..., "tool_input": {...}}}
            return {"messages": [llm_with_tools.invoke(state["messages"])]}

        graph_builder = StateGraph(State)
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

        self.graph = graph_builder.compile()
        return self.graph

    def get_graph_png_bytes(self) -> bytes:
        """
        Returns the graph as PNG bytes for use in Streamlit or web apps.
        """
        return self.graph.get_graph().draw_mermaid_png()
