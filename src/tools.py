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
def get_weather_data(location: str) -> str:
    """Use for PACKING or weather context. Input must be a city or location name.
    Return: 'weather: {temp_c: <float>, feels_like_c: <float>, description: "<text>", humidity: <int>, timestamp: "<YYYY-MM-DD HH:MM:SS>"}'."""
    logger.info(f"Getting weather data for: {location}")
    
    # Input validation
    if not location or not isinstance(location, str) or len(location.strip()) < 2:
        logger.warning(f"Invalid location input: {location}")
        return "I need a city/location name to check weather."
    
    location = location.strip()
    api_key = os.getenv("WEATHER_API_KEY")
    
    if not api_key:
        logger.warning("Weather API key not configured")
        return "Weather data unavailable: API key not configured"

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": location, "appid": api_key}
    last_error = None

    # Retry logic for resilience
    for attempt in range(2):
        try:
            logger.debug(f"Weather API request attempt {attempt + 1} for {location}")
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("list"):
                logger.warning(f"No weather data available for {location}")
                return f"No weather data available for {location}"
            
            # Parse weather data
            cf = data["list"][0]
            temp_c = round(cf["main"]["temp"] - 273.15, 1)
            feels_c = round(cf["main"]["feels_like"] - 273.15, 1) if "feels_like" in cf["main"] else temp_c
            desc = cf["weather"][0]["description"]
            hum = int(cf["main"]["humidity"])
            t = cf.get("dt_txt") or datetime.fromtimestamp(cf.get("dt", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
            result = f'weather: {{temp_c: {temp_c}, feels_like_c: {feels_c}, description: "{desc}", humidity: {hum}, timestamp: "{t}"}}'
            logger.info(f"Weather data retrieved successfully for {location}")
            return result
            
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(f"Weather API request failed (attempt {attempt + 1}): {e}")
            if attempt == 0:
                continue
        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error getting weather data: {e}")
            break

    logger.error(f"Failed to get weather data for {location}: {last_error}")
    return f"Weather data unavailable for {location}: {last_error or 'Unknown error'}"


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

        last_error = None
        search_response = None
        
        # Retry logic
        for attempt in range(2):
            try:
                logger.debug(f"Tavily search attempt {attempt + 1} for: {query}")
                search_response = tavily_search.invoke(query)
                break
            except Exception as e:
                last_error = e
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
TRAVEL_TOOLS = [get_weather_data, web_search_tavily, continue_chat]