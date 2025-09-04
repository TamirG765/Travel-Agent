# Travel Assistant

An AI travel assistant built with LangGraph, LangChain, and Streamlit.

## Features

- **Smart Travel Assistant**: Uses Ollama - local LLMs
- **Real-time Data**: Weather API (OpenWeatherMap) and web search API (Tavily)
- **Clean Chat Interface**: Streamlit-based UI focused on conversation
- **Memory & Context**: Maintains conversation history across interactions in-chat

## Project Structure

```
Travel-Agent/
├── src/
│   ├── __init__.py        # Package initialization
│   ├── tools.py           # Weather & web search tools
│   ├── agent.py           # Agent creation & configuration
│   └── prompts.py         # System prompts with anti-hallucination
├── streamlit_app.py       # Main Streamlit application
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables
```

## Setup

0. **Install Ollama** from [Ollama](https://ollama.com/)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment** (create `.env` file):
   ```bash
   OLLAMA_MODEL=llama3.2
   WEATHER_API_KEY=your_openweather_api_key
   TAVILY_API_KEY=your_tavily_api_key
   ```

3. **Start Ollama / Open terminal** and pull the model:
   ```bash
   ollama pull llama3.2
   ```

## Usage

### Streamlit Web Interface (Recommended)

```bash
streamlit run streamlit_app.py
```

Features:
- Clean chat interface (user/assistant messages only)

## API Keys

- **Weather**: Get free API key from [OpenWeatherMap - Used the free 5 day forecast API](https://openweathermap.org/forecast5)
- **Web Search**: Get API key from [Tavily](https://tavily.com/)

Both are optional - the app provides fallback responses when APIs are unavailable.

## Model Configuration

Supported Ollama models:
- `llama3.2` (default) - Fast, efficient
- `llama3.1` - Larger context window
- `qwen2.5` - Alternative option
- `mistral` - Lightweight option

Configure via environment variable or Streamlit sidebar.

## Architecture

This travel assistant uses a **ReAct (Reasoning + Acting) architecture** where the agent:

1. **Reasons** about the user's query
2. **Acts** by calling tools when needed (weather API, web search)
3. **Observes** the tool results  
4. **Responds** with informed, up-to-date information

The modular structure makes it easy to:
- Add new tools in `src/tools.py`
- Modify agent behavior in `src/agent.py` 
- Update prompts in `src/prompts.py`
- Extend the UI in `streamlit_app.py`

## Example Queries

- "What should I pack for Tokyo next week?"
- "Warm places to visit in November?"
- "Top attractions in Rome for a day trip"
- "Weather in Barcelona today"

## Usage Examples

### Destination Recommendations
```
You: I'm looking for a romantic getaway in Europe for next spring
Assistant: Let me think through some perfect romantic European destinations for spring...
```

### Packing Advice
```
You: What should I pack for a trip to Japan in December?
Assistant: For Japan in December, you'll need to prepare for cold weather and potentially some snow...
```

### Local Attractions
```
You: What are the best museums to visit in Paris?
Assistant: Paris has incredible museums! Let me recommend the top ones with practical visiting tips...
```

### Weather Information
```
You: What's the weather like in Bangkok right now?
Assistant: Based on current weather data for Bangkok...
```

## Architecture

### LangGraph Workflow
```
User Input → Context Management → Query Classification → External Data Check → Data Fetching (if needed) → Response Generation
```

### Key Components
- **State Management**: Typed state with conversation history
- **Query Classification**: Automatic categorization of user queries
- **Context Management**: Maintains conversation memory and user preferences
- **External APIs**: Weather and country information integration
- **Conditional Routing**: Smart workflow decisions based on query needs

### Prompt Engineering Highlights
- Role-based system prompts for each query type
- Chain-of-thought prompting for complex reasoning
- Few-shot examples for consistent classification
- Context-aware response generation

## Technical Implementation

### Dependencies
- `langgraph`: Workflow orchestration
- `langchain`: LLM integration framework
- `langchain-ollama`: Ollama integration
- `requests`: External API calls
- `python-dotenv`: Environment configuration

### External APIs
- **Weather**: OpenWeatherMap API (falls back to mock data)
- **Country Info**: REST Countries API (public, no key required)

## Error Handling

The system gracefully handles:
- Network timeouts for external APIs
- Missing API keys (falls back to mock data)  
- Ollama connection issues
- Malformed user inputs
- LLM generation errors

## Sample Conversation

```
🧳 TRAVEL ASSISTANT - LangGraph Demo
================================================================

🗣️  You: I want to plan a family trip to Japan

🌍 Assistant:
--------------------------------------------------
Let me help you plan an amazing family trip to Japan! 

First, let me think through what makes Japan perfect for families:

1. **Timing Considerations**: Japan offers different experiences by season
2. **Family-Friendly Destinations**: Cities with activities for all ages
3. **Cultural Experiences**: Kid-friendly cultural attractions
4. **Practical Factors**: Transportation, accommodation, food

**Top Recommendations:**

**Tokyo (5-7 days)**
- Tokyo Disneyland & DisneySea for magical experiences
- Ueno Zoo and National Museum for educational fun
- Harajuku and Shibuya for cultural immersion
- Easy subway system with English signage

**Kyoto (3-4 days)**  
- Fushimi Inari shrine with thousands of torii gates
- Bamboo Grove in Arashiyama
- Traditional temples that fascinate children
- Geisha spotting in Gion district

**Next Steps:**
- What time of year are you planning to travel?
- What are the ages of your children?
- What's your approximate budget range?

This will help me provide more specific recommendations!
--------------------------------------------------

🗣️  You: We're planning for spring with two kids aged 8 and 12

🌍 Assistant:
--------------------------------------------------
Perfect timing! Spring in Japan (March-May) is absolutely magical for families, especially with kids those ages.

Let me think through the best spring strategy:

1. **Season Benefits**: Cherry blossoms, mild weather, school holidays
2. **Age-Appropriate Activities**: Engaging for both 8 and 12-year-olds
3. **Educational Opportunities**: History and culture they can appreciate
4. **Fun Factor**: Mix of traditional and modern experiences

**Detailed Spring Itinerary:**

**Tokyo (6 days) - Arrive late March/early April**
- **Cherry Blossom Spots**: Ueno Park for hanami picnics
- **Kid Favorites**: Tokyo Skytree, teamLab Borderless digital museum
- **Cultural Mix**: Senso-ji Temple + nearby Nakamise shopping street
- **Modern Fun**: Harajuku for quirky fashion, Shibuya crossing experience

**Day Trip to Nikko (1 day)**
- UNESCO World Heritage shrines in stunning mountain setting
- Perfect for 12-year-old's growing interest in history

**Kyoto (4 days)**
- **Arashiyama**: Bamboo grove + monkey park with Mt. Fuji views
- **Kiyomizu-dera**: Temple with city views (great for photos)
- **Nijo Castle**: Nightingale floors fascinate kids
- **Gion**: Early evening geisha spotting

**Spring-Specific Tips:**
- Pack layers - mornings cool, afternoons warm
- Book accommodations early (peak season)
- Hanami season means crowds but incredible beauty
- Kids will love the seasonal sakura-flavored treats!

Would you like specific recommendations for family-friendly accommodations or transportation tips?
--------------------------------------------------
```

## Development Notes

### Prompt Engineering Decisions
- **Chain-of-Thought**: Guides LLM through systematic reasoning steps
- **Role Playing**: Each node has a specific expert persona
- **Context Integration**: Seamlessly blends conversation history with new queries
- **Few-Shot Examples**: Improves classification accuracy
- **Error Recovery**: Graceful fallbacks for edge cases

### Future Enhancements
- Add more external APIs (flights, hotels, exchange rates)
- Implement user preference learning
- Add image generation for destination visualization
- Support for multiple languages
- Integration with booking platforms