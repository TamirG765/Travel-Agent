from typing import Dict, Any
import os
import requests
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage
from .state import TravelState
from .prompts import TRAVEL_ASSISTANT_SYSTEM_MESSAGE

def get_weather_data(location: str) -> str:
    """Get real-time weather data for a location using OpenWeatherMap API"""
    try:
        # Get API key from environment
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            return f"Weather data unavailable: API key not configured"
        
        # Make API call to OpenWeatherMap forecast endpoint
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we have forecast data
        if not data.get("list"):
            return f"No weather data available for {location}"
        
        # Get the most current forecast (first entry in the list)
        current_forecast = data["list"][0]
        
        # Extract temperature (convert from Kelvin to Celsius)
        temp_kelvin = current_forecast["main"]["temp"]
        temp_celsius = round(temp_kelvin - 273.15, 1)
        
        # Extract weather description
        weather_desc = current_forecast["weather"][0]["description"]
        
        # Extract humidity
        humidity = current_forecast["main"]["humidity"]
        
        # Extract forecast time
        forecast_time = current_forecast["dt_txt"]
        
        # Format the response
        return f"Weather in {location}: {temp_celsius}°C, {weather_desc}, humidity {humidity}% (forecast for {forecast_time})"
        
    except requests.exceptions.RequestException as e:
        return f"Failed to get weather data for {location}: Network error"
    except KeyError as e:
        return f"Failed to parse weather data for {location}: Invalid response format"
    except Exception as e:
        return f"Weather data unavailable for {location}: {str(e)}"

# Tools list
tools = [get_weather_data]

# LLM with tools bound
llm_with_tools = ChatOllama(model="qwen3", temperature=0).bind_tools(tools)

# System message
sys_msg = SystemMessage(content=TRAVEL_ASSISTANT_SYSTEM_MESSAGE)

# Assistant node
def assistant(state: TravelState) -> Dict[str, Any]:
    """Assistant node that handles conversation with tool calling"""
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}


