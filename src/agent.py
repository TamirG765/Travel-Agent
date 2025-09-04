"""
Travel Agent Module

This module handles the creation and configuration of the travel assistant agent.
It uses LangGraph's ReAct agent with memory capabilities.
"""

import os
import logging
from typing import Dict, Any
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from .tools import TRAVEL_TOOLS
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class TravelAgent:
    """Travel Assistant Agent with memory and tool capabilities"""
    
    def __init__(self, model_name: str = None, temperature: float = 0.2):
        """
        Initialize the travel agent
        
        Args:
            model_name: Name of the Ollama model to use
            temperature: Model temperature for response randomness
        """
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.temperature = temperature
        self.agent = None
        self.checkpointer = None
        
        logger.info(f"Initializing TravelAgent with model: {self.model_name}")
        self._create_agent()
    
    def _create_agent(self):
        """Create the ReAct agent with tools and memory"""
        try:
            # Initialize the language model
            model = ChatOllama(
                model=self.model_name, 
                temperature=self.temperature
            )
            
            # Initialize memory checkpointer
            self.checkpointer = MemorySaver()
            
            # Create the agent
            self.agent = create_react_agent(
                model=model,
                tools=TRAVEL_TOOLS,
                checkpointer=self.checkpointer,
                prompt=SYSTEM_PROMPT
            )
            
            logger.info(f"Agent created successfully with {len(TRAVEL_TOOLS)} tools")
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise
    
    def get_agent(self):
        """Get the initialized agent"""
        if not self.agent:
            raise RuntimeError("Agent not initialized")
        return self.agent
    
    def get_config(self, thread_id: str) -> Dict[str, Any]:
        """Get configuration for agent with specific thread ID"""
        return {"configurable": {"thread_id": thread_id}}
    
    def invoke(self, messages: list, thread_id: str):
        """
        Invoke the agent with messages and thread context
        
        Args:
            messages: List of messages to process
            thread_id: Thread ID for conversation context
            
        Returns:
            Agent response state
        """
        try:
            config = self.get_config(thread_id)
            state = {"messages": messages}
            
            logger.info(f"Invoking agent for thread: {thread_id}")
            result = self.agent.invoke(state, config)
            logger.info("Agent invocation completed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "tools_count": len(TRAVEL_TOOLS),
            "tools": [tool.name for tool in TRAVEL_TOOLS]
        }


def create_travel_agent(model_name: str = None, temperature: float = 0.2) -> TravelAgent:
    """
    Factory function to create a travel agent
    
    Args:
        model_name: Ollama model name
        temperature: Response randomness (0.0 - 1.0)
        
    Returns:
        Initialized TravelAgent instance
    """
    return TravelAgent(model_name=model_name, temperature=temperature)