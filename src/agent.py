import os
import logging
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from .tools import TRAVEL_TOOLS
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Global variables to store the agent and checkpointer
_agent = None
_checkpointer = None


def get_agent():
    """Get the initialized agent, creating it if necessary"""
    if _agent is None:
        create_travel_agent()
    return _agent


def invoke_agent(messages: list, thread_id: str):
    """
    Invoke the agent with messages and thread context
    
    Args:
        messages: List of messages to process
        thread_id: Thread ID for conversation context
        
    Returns:
        Agent response state
    """
    try:
        agent = get_agent()
        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": messages}
        
        logger.info(f"Invoking agent for thread: {thread_id}")
        result = agent.invoke(state, config)
        logger.info("Agent invocation completed successfully")
        
        return result
        
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}")
        raise


def create_travel_agent(model_name: str = None, temperature: float = 0.2):
    """
    Create or recreate the travel agent with specified configuration
    
    Args:
        model_name: Ollama model name
        temperature: Response randomness (0.0 - 1.0)
    """
    global _agent, _checkpointer
    
    model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.1")
    
    try:
        # Initialize the language model
        model = ChatOllama(
            model=model_name, 
            temperature=temperature
        )
        
        # Initialize memory checkpointer
        _checkpointer = MemorySaver()
        
        # Create the agent
        _agent = create_react_agent(
            model=model,
            tools=TRAVEL_TOOLS,
            checkpointer=_checkpointer,
            prompt=SYSTEM_PROMPT
        )
        
        logger.info(f"Agent created successfully with model: {model_name} and {len(TRAVEL_TOOLS)} tools")
        
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise
