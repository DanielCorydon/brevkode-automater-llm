from typing_extensions import TypedDict
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated


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

        graph_builder = StateGraph(State)

        def chatbot(state: State):
            # LLM should output a dict: {"content": ...} or {"tool_call": {"tool": ..., "tool_input": {...}}}
            return {"messages": [llm.invoke(state["messages"])]}

        def router(state: State):
            last_message = state["messages"][-1]
            if isinstance(last_message, dict) and "tool_call" in last_message:
                return "replace_string_in_text"
            return END

        def string_replace_tool(state: State):
            last_message = state["messages"][-1]
            tool_call = last_message.get("tool_call")
            if not tool_call or tool_call.get("tool") != "replace_string_in_text":
                return {"messages": [{"content": "No valid tool_call provided."}]}
            tool_input = tool_call.get("tool_input")
            if not tool_input:
                return {
                    "messages": [
                        {"content": "No tool_input provided for string replacement."}
                    ]
                }
            result = replace_string_in_text(tool_input)
            return {"messages": [{"content": result["modified_text"]}]}

        graph_builder.add_node("chatbot", chatbot)
        graph_builder.add_node("router", router)
        graph_builder.add_node("replace_string_in_text", string_replace_tool)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("chatbot", "router")
        graph_builder.add_edge(
            "router",
            "replace_string_in_text",
            condition=lambda state: state["messages"][-1]
            .get("tool_call", {})
            .get("tool")
            == "replace_string_in_text",
        )
        graph_builder.add_edge(
            "router",
            END,
            condition=lambda state: not (
                isinstance(state["messages"][-1], dict)
                and "tool_call" in state["messages"][-1]
            ),
        )
        graph_builder.add_edge("replace_string_in_text", END)
        self.graph = graph_builder.compile()
        return self.graph
