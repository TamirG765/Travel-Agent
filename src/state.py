from typing import Optional, Literal
from dataclasses import dataclass
from langgraph.graph import MessagesState

QueryType = Literal["destination", "packing", "attractions", "weather"]

@dataclass
class WeatherData:
    temperature: float
    description: str
    humidity: int
    location: str

@dataclass
class CountryInfo:
    name: str
    capital: str
    currency: str
    language: str
    timezone: str

class TravelState(MessagesState):
    user_input: str
    query_type: Optional[QueryType]
    conversation_context: dict
    weather_data: Optional[WeatherData]
    country_info: Optional[CountryInfo]
    response: str
    needs_external_data: bool