"""
Travel Assistant Tools

This module contains all the tools used by the travel agent:
- Weather data retrieval
- Web search for travel information  
- Chat continuation for generic advice
"""

import os
import requests
import logging
from datetime import datetime, timezone
from langchain.tools import tool
from langchain_tavily import TavilySearch

# Set up logging for tool usage
logger = logging.getLogger(__name__)


@tool
def get_weather_forecast(location: str, days: int = 5) -> str:
    """
    Get weather forecast for the next 1-5 days for trip planning and packing decisions.
    
    Args:
        location (str): City or location name (e.g., "London", "New York", "Tokyo")
        days (int): Number of days to forecast (1-5, default: 5)
    
    Returns:
        str: Formatted forecast data with daily weather summaries including:
             - Date and day of week
             - Temperature range (min/max in Celsius)
             - Weather description
             - Humidity and precipitation probability
    
    Use this tool when users ask about:
    - Weather for upcoming days/week
    - Trip planning weather conditions
    - What to pack based on forecast
    - Weather trends over multiple days
    
    Example usage:
    - "What's the weather forecast for Paris for the next 3 days?"
    - "I'm traveling to Tokyo next week, what should I expect?"
    - "Will it rain in London this week?"
    """
    logger.info(f"Getting {days}-day weather forecast for: {location}")
    
    # Input validation
    if not location or not isinstance(location, str) or len(location.strip()) < 2:
        logger.warning(f"Invalid location input: {location}")
        return "I need a valid city/location name to get weather forecast."
    
    if not isinstance(days, int) or days < 1 or days > 5:
        days = 5
        logger.info(f"Invalid days parameter, defaulting to {days} days")
    
    location = location.strip()
    api_key = os.getenv("WEATHER_API_KEY")
    
    if not api_key:
        logger.warning("Weather API key not configured")
        return "Weather forecast unavailable: API key not configured"

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": location, "appid": api_key, "units": "metric"}
    
    try:
        logger.debug(f"Weather forecast API request for {location}")
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("list"):
            logger.warning(f"No forecast data available for {location}")
            return f"No weather forecast available for {location}"
        
        # Process forecast data
        forecasts = data["list"]
        city_name = data.get("city", {}).get("name", location)
        
        # Group forecasts by date
        daily_forecasts = {}
        today = datetime.now().date()
        
        for forecast in forecasts:
            dt_txt = forecast.get("dt_txt", "")
            if not dt_txt:
                continue
                
            try:
                forecast_datetime = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
                forecast_date = forecast_datetime.date()
                
                # Only include forecasts for today and the next 'days' days
                days_from_today = (forecast_date - today).days
                if days_from_today < 0 or days_from_today >= days:
                    continue
                
                if forecast_date not in daily_forecasts:
                    daily_forecasts[forecast_date] = {
                        'temps': [],
                        'descriptions': [],
                        'humidity': [],
                        'pop': [],  # precipitation probability
                        'times': []
                    }
                
                # Extract data
                main = forecast.get("main", {})
                weather = forecast.get("weather", [{}])[0]
                
                daily_forecasts[forecast_date]['temps'].append(main.get("temp", 0))
                daily_forecasts[forecast_date]['descriptions'].append(weather.get("description", ""))
                daily_forecasts[forecast_date]['humidity'].append(main.get("humidity", 0))
                daily_forecasts[forecast_date]['pop'].append(forecast.get("pop", 0) * 100)  # Convert to percentage
                daily_forecasts[forecast_date]['times'].append(forecast_datetime.strftime("%H:%M"))
                
            except ValueError as e:
                logger.warning(f"Error parsing forecast datetime '{dt_txt}': {e}")
                continue
        
        if not daily_forecasts:
            return f"No valid forecast data found for {location}"
        
        # Format the response
        result_lines = [f"Weather forecast for {city_name}:"]
        
        for date in sorted(daily_forecasts.keys()):
            day_data = daily_forecasts[date]
            
            if not day_data['temps']:
                continue
            
            # Calculate daily summary
            min_temp = round(min(day_data['temps']), 1)
            max_temp = round(max(day_data['temps']), 1)
            avg_humidity = round(sum(day_data['humidity']) / len(day_data['humidity']))
            max_pop = round(max(day_data['pop'])) if day_data['pop'] else 0
            
            # Get most common description
            desc_counts = {}
            for desc in day_data['descriptions']:
                desc_counts[desc] = desc_counts.get(desc, 0) + 1
            most_common_desc = max(desc_counts, key=desc_counts.get) if desc_counts else "unknown"
            
            # Format date
            day_name = date.strftime("%A")
            date_str = date.strftime("%Y-%m-%d")
            
            # Determine if it's today, tomorrow, etc.
            days_from_today = (date - today).days
            if days_from_today == 0:
                date_label = "Today"
            elif days_from_today == 1:
                date_label = "Tomorrow"
            else:
                date_label = f"{day_name}"
            
            result_lines.append(
                f"{date_label} ({date_str}): {min_temp}°C - {max_temp}°C, {most_common_desc}, "
                f"humidity {avg_humidity}%, precipitation chance {max_pop}%"
            )
        
        result = "\n".join(result_lines)
        logger.info(f"Weather forecast retrieved successfully for {location} ({len(daily_forecasts)} days)")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather forecast API request failed: {e}")
        return f"Weather forecast unavailable for {location}: Network error"
    except Exception as e:
        logger.error(f"Unexpected error getting weather forecast: {e}")
        return f"Weather forecast unavailable for {location}: {str(e)}"


@tool
def web_search_tavily(query: str, max_results: int = 2) -> str:
    """Use for DESTINATION IDEAS and LOCAL ATTRACTIONS. Avoid for packing/weather.
    Return: 'sources: [{title: "...", url: "...", summary: "..."}]'."""
    logger.info(f"Searching web for: {query}")
    
    if not query or not isinstance(query, str) or len(query.strip()) == 0:
        logger.warning("Empty or invalid search query")
        return "sources: []"
    
    query = query.strip()

    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.warning("Tavily API key not configured")
            return "Search unavailable: TAVILY_API_KEY not configured"

        tavily_search = TavilySearch(
            api_wrapper_kwargs={"api_key": api_key},
            max_results=max_results
        )

        search_response = None
        
        # Retry logic
        for attempt in range(2):
            try:
                logger.debug(f"Tavily search attempt {attempt + 1} for: {query}")
                search_response = tavily_search.invoke(query)
                break
            except Exception as e:
                logger.warning(f"Tavily search failed (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    continue
                return "sources: []"

        # Normalize results to list of dicts
        results = []
        if isinstance(search_response, dict) and "results" in search_response:
            results = search_response["results"] or []
        elif isinstance(search_response, list):
            results = search_response
        else:
            # Unknown format fallback
            logger.warning(f"Unexpected search response format: {type(search_response)}")
            return f'sources: [{{title: "Result", url: "tavily-search", summary: "{str(search_response)[:200]}..."}}]'

        # Format results
        normalized = []
        for doc in results[:max_results if max_results else 2]:
            if not isinstance(doc, dict):
                continue
                
            url = (doc.get("url") or "").strip()
            title = (doc.get("title") or "").strip()
            content = (doc.get("content") or doc.get("raw_content") or "").strip()
            summary = (content[:280] + "…") if len(content) > 280 else content
            
            if url or title or summary:
                # Ensure quotes are safe in the output
                safe_title = title.replace('"', "'")
                safe_url = url.replace('"', "'")
                safe_summary = summary.replace('"', "'")
                normalized.append(f'{{title: "{safe_title}", url: "{safe_url}", summary: "{safe_summary}"}}')

        if not normalized:
            logger.info(f"No results found for query: {query}")
            return "sources: []"

        result = f'sources: [{", ".join(normalized)}]'
        logger.info(f"Web search completed successfully for: {query} ({len(normalized)} results)")
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in web search: {e}")
        return "sources: []"


@tool
def continue_chat(user_message: str) -> str:
    """Handle generic advice or chit-chat when no external data is needed. 
    The agent may use this when the answer is stable and non-volatile (when the query in not about one of the three main tasks)."""
    logger.info(f"Handling generic chat for: {user_message[:50]}...")
    return "CONTINUE_CHAT"


# Export all tools for easy import
TRAVEL_TOOLS = [get_weather_forecast, web_search_tavily, continue_chat]