#!/usr/bin/env python3
"""
demo.py
- Uses LangGraph prebuilt ReAct agent (create_react_agent)
- Memory via MemorySaver (threaded checkpointer)
- Mock tools (weather_data, country_info)
- Simple CLI using agent.invoke(...) per turn (no streaming)
- Prints tool calls (args) and tool outputs so you can see the whole process

Run:
  python demo.py

Optional env:
  OLLAMA_MODEL=llama3.2
"""

import os
import uuid
import json
import sys
from typing import List
import requests
from pydantic import BaseModel, Field
from datetime import datetime

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_tavily import TavilySearch

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)
from langchain.tools import tool
from prompts import SYSTEM_PROMPT

from dotenv import load_dotenv
load_dotenv()

MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

# ---------------------------
# Pydantic Models
# ---------------------------
class SearchQuery(BaseModel):
    """Search query for web search"""
    search_query: str = Field(description="Search query for web search")

# ---------------------------
# Tools
# ---------------------------
@tool
def get_weather_data(location: str) -> str:
    """Use for PACKING or weather context. Input must be a city or location name.
    Return: 'weather: {temp_c: <float>, feels_like_c: <float>, description: "<text>", humidity: <int>, timestamp: "<YYYY-MM-DD HH:MM:SS>"}'."""
    # Input sanity
    if not location or not isinstance(location, str) or len(location.strip()) < 2:
        return "I need a city/location name to check weather."
    location = location.strip()

    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return "Weather data unavailable: API key not configured"

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": location, "appid": api_key}
    last_error = None

    # Tiny resilience: retry once on transient failures
    for attempt in range(2):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("list"):
                return f"No weather data available for {location}"
            cf = data["list"][0]
            temp_c = round(cf["main"]["temp"] - 273.15, 1)
            feels_c = round(cf["main"]["feels_like"] - 273.15, 1) if "feels_like" in cf["main"] else temp_c
            desc = cf["weather"][0]["description"]
            hum = int(cf["main"]["humidity"])
            t = cf.get("dt_txt") or datetime.utcfromtimestamp(cf.get("dt", 0)).strftime("%Y-%m-%d %H:%M:%S")
            # Mini-JSON-ish string the model can parse reliably
            return f'weather: {{temp_c: {temp_c}, feels_like_c: {feels_c}, description: "{desc}", humidity: {hum}, timestamp: "{t}"}}'
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt == 0:
                continue
        except Exception as e:
            last_error = e
            break

    return f"Weather data unavailable for {location}: {last_error or 'Unknown error'}"

@tool
def web_search_tavily(query: str, max_results: int = 2) -> str:
    """Use for DESTINATION IDEAS and LOCAL ATTRACTIONS. Avoid for packing/weather.
    Return: 'sources: [{title: "...", url: "...", summary: "..."}]'."""
    if not query or not isinstance(query, str) or len(query.strip()) == 0:
        return "sources: []"
    query = query.strip()

    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Search unavailable: TAVILY_API_KEY not configured"

        tavily_search = TavilySearch(
            api_wrapper_kwargs={"api_key": api_key},
            max_results=max_results
        )

        last_error = None
        for attempt in range(2):
            try:
                search_response = tavily_search.invoke(query)
                break
            except Exception as e:
                last_error = e
                if attempt == 0:
                    continue
                return "sources: []"

        # Normalize to list of dicts
        results = []
        if isinstance(search_response, dict) and "results" in search_response:
            results = search_response["results"] or []
        elif isinstance(search_response, list):
            results = search_response
        else:
            # Unknown shape; best-effort wrap
            return f'sources: [{{title: "Result", url: "tavily-search", summary: "{str(search_response)[:200]}..."}}]'

        normalized = []
        for doc in results[: max_results if max_results else 2]:
            if not isinstance(doc, dict):
                continue
            url = (doc.get("url") or "").strip()
            title = (doc.get("title") or "").strip()
            content = (doc.get("content") or doc.get("raw_content") or "").strip()
            summary = (content[:280] + "…") if len(content) > 280 else content
            if url or title or summary:
                # Ensure quotes are safe in the mini-JSON string
                safe_title = title.replace('"', "'")
                safe_url = url.replace('"', "'")
                safe_summary = summary.replace('"', "'")
                normalized.append(f'{{title: "{safe_title}", url: "{safe_url}", summary: "{safe_summary}"}}')

        if not normalized:
            return "sources: []"

        return f'sources: [{", ".join(normalized)}]'
    except Exception as e:
        return "sources: []"

@tool
def continue_chat(user_message: str) -> str:
    """Handle generic advice or chit-chat when no external data is needed. The agent may use this when the answer is stable and non-volatile (e.g., general packing principles)."""
    _ = user_message  # Mark as used
    return "CONTINUE_CHAT"


TOOLS = [get_weather_data, web_search_tavily, continue_chat]

# ---------------------------
# Agent builder
# ---------------------------
def build_agent():
    model = ChatOllama(model=MODEL_NAME, temperature=0.2)
    checkpointer = MemorySaver()
    agent = create_react_agent(
        model=model,
        tools=TOOLS,
        checkpointer=checkpointer,
        prompt=SYSTEM_PROMPT
    )
    return agent

# ---------------------------
# Pretty printer for the "whole process"
# We diff by "new messages since last turn" to show this turn's chain:
# - AIMessage with tool_calls -> print tool name + args
# - ToolMessage -> print tool output
# - Final AIMessage -> print assistant reply
# ---------------------------
def print_turn(messages: List[BaseMessage], start_idx: int = 0) -> int:
    """
    Print messages starting from start_idx.
    Returns the new message count (len(messages)) so the caller can store it.
    """
    new_msgs = messages[start_idx:]
    if not new_msgs:
        return len(messages)

    for msg in new_msgs:
        if isinstance(msg, HumanMessage):
            print(f"\nYou: {msg.content}")

        elif isinstance(msg, AIMessage):
            # If this AIMessage contains tool calls, print them (args)
            tool_calls = msg.additional_kwargs.get("tool_calls", [])
            if tool_calls:
                print("\nAssistant (planning/tool calls):")
                for i, tc in enumerate(tool_calls, 1):
                    name = (tc.get("function") or {}).get("name")
                    args = (tc.get("function") or {}).get("arguments")
                    # args is a JSON string in OpenAI-format tool calls. Try to pretty-print.
                    try:
                        parsed = json.loads(args) if isinstance(args, str) else args
                    except Exception:
                        parsed = args
                    print(f"  {i}. call -> {name}({json.dumps(parsed, ensure_ascii=False)})")
            else:
                # Regular assistant content
                if msg.content and msg.content.strip():
                    print(f"\nAssistant: {msg.content}")

        elif isinstance(msg, ToolMessage):
            # Tool result content
            tool_name = (msg.name or "tool").strip()
            out = msg.content if isinstance(msg.content, str) else str(msg.content)
            # Truncate very long outputs for readability if needed
            display = out if len(out) < 2000 else (out[:2000] + "... [truncated]")
            print(f"\n[Tool output] {tool_name}: {display}")

        else:
            # Other message types (SystemMessage, etc.) are usually not printed each turn
            pass

    return len(messages)

# ---------------------------
# CLI using invoke()
# ---------------------------
def main():
    print(f"Travel CLI Agent (invoke-mode, model={MODEL_NAME}) — composite tools enabled")
    print("Type your message. Type 'exit' to quit.")

    print("\nTry these:")
    print("  • Warm places in November?")
    print("  • What should I pack for Tokyo next week?")
    print("  • Top attractions in Rome for a day trip")

    agent = build_agent()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Seed memory with system prompt (store once)
    init_state = {"messages": [HumanMessage(content="Hey")] }
    state = agent.invoke(init_state, config)
    seen = len(state.get("messages", []))  # track how many messages we've printed

    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user:
            continue
        if user.lower() in {"exit", "quit", 'q'}:
            print("Bye!")
            break

        # only print the last message returned from the model
        print("\nAssistant:", end=" ")
        # One-turn invocation
        turn_state = {"messages": [HumanMessage(content=user)]}
        try:
            state = agent.invoke(turn_state, config)
        except Exception as e:
            print(f"\n[error] {e}")
            continue

        msgs: List[BaseMessage] = state.get("messages", [])
        seen = print_turn(msgs, start_idx=seen)

if __name__ == "__main__":
    # Small guard so the script exits cleanly in some terminals
    try:
        main()
    except Exception as exc:
        print(f"\n[Fatal] {exc}", file=sys.stderr)
        sys.exit(1)