from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from .state import TravelState
from .nodes import assistant, tools

def chat_condition(state: TravelState) -> str:
    """Custom condition function to determine next node in conversation flow"""
    # Get the latest assistant message
    last_msg = state["messages"][-1]
    
    # If the latest message from assistant is a tool call -> route to tools
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "tools"
    
    # If we have an assistant response without tool calls, end and wait for user input
    return END

def create_travel_agent_graph():
    """Create the LangGraph workflow for the travel assistant"""
    
    # Initialize the state graph
    builder = StateGraph(TravelState)
    
    # Define nodes: these do the work
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    
    # Define edges: these determine how the control flow moves
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        chat_condition,
        {
            "tools": "tools",
            END: END
        }
    )
    builder.add_edge("tools", "assistant")
    
    # Create memory saver for conversation persistence
    memory = MemorySaver()
    
    # Compile the graph with checkpointer
    react_graph = builder.compile(checkpointer=memory)
    
    return react_graph