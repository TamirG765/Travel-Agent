

import os
import sys
from dotenv import load_dotenv
import uuid
from langchain_core.messages import HumanMessage
from src.graph import create_travel_agent_graph

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    
    # Check if Ollama is accessible (optional check)
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"Using Ollama at: {ollama_url}")
    print("Make sure Ollama is running with a model like 'llama3.2' installed")

def print_welcome():
    """Print welcome message and instructions"""
    print("=" * 60)
    print("🧳 TRAVEL ASSISTANT - LangGraph Demo")
    print("=" * 60)
    print("I'm your AI travel assistant! I can help you with:")
    print("• 🌍 Destination recommendations")
    print("• 🎒 Packing suggestions")
    print("• 🎭 Local attractions and activities")
    print("• 🌤️  Weather information")
    print()
    print("Type 'quit' or 'exit' to end the conversation.")
    print("Type 'reset' to start a new conversation.")
    print("=" * 60)
    print()

def print_response(message_content: str):
    """Print the assistant's response with formatting"""
    print(f"\n🤖 Assistant:")
    print("-" * 50)
    # Properly format newlines in response
    formatted_response = message_content.replace('\\n', '\n')
    print(formatted_response)
    print("-" * 50)
    print()

def main():
    """Main CLI application"""
    try:
        # Load environment variables
        load_environment()
        
        # Create the travel agent graph
        print("Initializing Travel Assistant...")
        app = create_travel_agent_graph()
        
        # Create config with thread_id for conversation memory
        uid = uuid.uuid4()
        config = {"configurable": {"thread_id": str(uid)}}
        
        # Print welcome message
        print_welcome()
        
        while True:
            try:
                # Get user input
                user_input = input("🗣️  You: ").strip()
                
                # Handle exit commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Thank you for using Travel Assistant! Safe travels!")
                    break
                
                # Handle reset command
                if user_input.lower() == 'reset':
                    # Create new thread_id to reset conversation
                    uid = uuid.uuid4()
                    config = {"configurable": {"thread_id": str(uid)}}
                    print("\n🔄 Conversation reset. How can I help you with your travel plans?")
                    continue
                
                # Skip empty inputs
                if not user_input:
                    continue
                
                print("\n🤔 Thinking...")
                
                # Create message for this interaction
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=user_input)]
                
                # Process the input through the graph with config
                result = app.invoke({"messages": messages}, config)
                
                # Print the assistant's response
                last_message = result["messages"][-1]
                print_response(last_message.content)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Safe travels!")
                break
            except Exception as e:
                print(f"\n❌ An error occurred: {e}")
                print("Please try again or type 'reset' to start over.")
                
    except Exception as e:
        print(f"❌ Failed to initialize Travel Assistant: {e}")
        print("\nPlease make sure:")
        print("1. Ollama is running (ollama serve)")
        print("2. You have a model installed (ollama pull llama3.2)")
        print("3. All dependencies are installed (pip install -r requirements.txt)")
        sys.exit(1)

if __name__ == "__main__":
    main()