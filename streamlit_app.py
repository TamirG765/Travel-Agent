import streamlit as st
import uuid
import logging
from typing import Dict
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our modules
from src.agent import create_travel_agent, invoke_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Travel Assistant", 
    page_icon="✈️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better chat UI
st.markdown("""
<style>
.user-message {
    background-color: #007bff;
    color: white;
    padding: 10px 15px;
    border-radius: 20px 20px 5px 20px;
    margin: 5px 0;
    max-width: 70%;
    margin-left: auto;
    text-align: right;
}

.assistant-message {
    background-color: #f1f1f1;
    color: #333;
    padding: 10px 15px;
    border-radius: 20px 20px 20px 5px;
    margin: 5px 0;
    max-width: 70%;
    margin-right: auto;
}

</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    if 'agent_ready' not in st.session_state:
        st.session_state.agent_ready = False
    
    


def create_agent():
    """Create or recreate the agent with current settings"""
    try:
        create_travel_agent()
        st.session_state.agent_ready = True
        logger.info("Agent created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        st.error(f"Failed to create agent: {e}")
        return False


def extract_final_answer(messages) -> str:
    """Extract the clean final answer from agent response messages"""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.additional_kwargs.get("tool_calls"):
            full_response = msg.content.strip()
            # Extract only the text after the LAST "Final answer:"
            if "Final answer:" in full_response:
                # Split by "Final answer:" and take the last part
                parts = full_response.split("Final answer:")
                return parts[-1].strip()
            else:
                return full_response
    return ""


def display_message(message: Dict[str, str]):
    """Display a chat message with proper styling"""
    if message["role"] == "user":
        st.markdown(f'<div class="user-message">{message["content"]}</div>', 
                   unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">{message["content"]}</div>', 
                   unsafe_allow_html=True)


def sidebar():
    """Create the sidebar with About section and clear button"""
    with st.sidebar:
        
        # Brief explanation
        st.subheader("ℹ️ About")
        st.markdown("""
        This is a **Travel AI Agent** using a simple **ReAct Agent architecture**.
        
        **Real-time capabilities:**
        - 🌤️ Weather data for packing advice
        - 🔍 Web search for current travel info
        """)
        
        st.divider()
        
                # Clear conversation
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()


def main():
    """Main Streamlit app"""
    init_session_state()
    
    # Create agent if not exists
    if not st.session_state.agent_ready:
        with st.spinner("Initializing Travel Assistant..."):
            if not create_agent():
                st.stop()
    
    # Sidebar
    sidebar()
    
    # Main chat interface
    st.title("✈️ Travel Assistant")
    st.markdown("*Your friendly travel companion for planning, weather, and destination advice*")
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display conversation history
        for message in st.session_state.messages:
            display_message(message)
    
    # Chat input
    if prompt := st.chat_input("Ask me about travel, weather, destinations..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with chat_container:
            display_message({"role": "user", "content": prompt})
        
        # Get agent response
        with st.spinner("✈️ Thinking..."):
            try:
                # Invoke agent
                result = invoke_agent(
                    [HumanMessage(content=prompt)], 
                    st.session_state.thread_id
                )
                
                messages = result.get("messages", [])
                
                # Get final assistant response
                assistant_response = extract_final_answer(messages)
                
                if assistant_response:
                    # Add assistant response to history
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                    
                    # Display assistant response
                    with chat_container:
                        display_message({"role": "assistant", "content": assistant_response})
                else:
                    st.error("No response generated")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                st.error(f"Error: {e}")


if __name__ == "__main__":
    main()