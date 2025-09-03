from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import tools_condition, ToolNode


def weather_data(location):
    """return weather data"""
    return f"Demo weather data for {location}"
def country_info(location):
    """return country info"""
    return f"Demo country info for {location}"

tools = [weather_data, country_info]

llm_with_tools = ChatOllama(model="llama3.2",
                 temperature=0,
                 ).bind_tools(tools)

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked to answer about weather or country info.")

# Node
def assistant(state: MessagesState):
   return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

builder = StateGraph(MessagesState)

# Define nodes: these do the work
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
builder.add_edge("tools", "assistant")
react_graph = builder.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "1"}}

messages = [HumanMessage(content="what is the weather in New York? and what is the country info for France?")]

result = react_graph.invoke({"messages": messages}, config)

for m in result['messages']:
    m.pretty_print()



# Demo for memory
"""
# System message
system_message = SystemMessage(content="You are a helpful assistant.")

def assistant(state: MessagesState):
    return {"messages": [llm.invoke([system_message] + state["messages"])]}

graph = StateGraph(MessagesState)
graph.add_node("assistant", assistant)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "assistant")
graph.add_conditional_edges(
    "assistant",
    tools_condition,
)
graph.add_edge("tools", "assistant")

react_graph = graph.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "1"}}

messages = [HumanMessage(content="my name is tamir")]

result = react_graph.invoke({"messages": messages}, config)

print(result)

messages = [HumanMessage(content="what is my name?")]

result = react_graph.invoke({"messages": messages}, config)

print (50 * "=")

print(result)
"""
