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

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)
from langchain.tools import tool

# ---------------------------
# Setup
# ---------------------------
load_dotenv()
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = """You are a friendly, precise travel assistant.
- Maintain context across turns (use memory).
- Use tools for weather and country facts.
- Keep answers concise; use lists when helpful.
- Only show short reasoning takeaways if useful.
- End with a helpful next-step when appropriate.

Tool policy:
- Weather queries -> call weather_data.
- Country facts (visa, currency, safety, tipping) -> call country_info.
"""

# ---------------------------
# Tools (mock)
# ---------------------------
@tool
def get_weather_data(location: str) -> str:
    """Get real-time weather data for a location using OpenWeatherMap API"""
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            return "Weather data unavailable: API key not configured"
        url = "https://api.openweathermap.org/data/2.5/forecast"
        resp = requests.get(url, params={"q": location, "appid": api_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("list"):
            return f"No weather data available for {location}"
        cf = data["list"][0]
        temp_c = round(cf["main"]["temp"] - 273.15, 1)
        desc = cf["weather"][0]["description"]
        hum = cf["main"]["humidity"]
        t = cf["dt_txt"]
        return f"Weather in {location}: {temp_c}°C, {desc}, humidity {hum}% (forecast for {t})"
    except requests.exceptions.RequestException:
        return f"Failed to get weather data for {location}: Network error"
    except KeyError:
        return f"Failed to parse weather data for {location}: Invalid response format"
    except Exception as e:
        return f"Weather data unavailable for {location}: {e}"

@tool
def country_info(location: str) -> str:
    """Get country information for a location (mock)."""
    return f"[mock] Country info for {location}: Currency EUR, Schengen, Safety High, Tipping Optional"

TOOLS = [get_weather_data, country_info]

# ---------------------------
# Agent builder
# ---------------------------
def build_agent():
    model = ChatOllama(model=MODEL_NAME)
    checkpointer = MemorySaver()
    agent = create_react_agent(
        model=model,
        tools=TOOLS,
        checkpointer=checkpointer,
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
    print(f"Travel CLI Agent (invoke-mode, model={MODEL_NAME})")
    print("Type your message. Type 'exit' to quit.")

    agent = build_agent()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Seed memory with system prompt (store once)
    init_state = {"messages": [SystemMessage(content=SYSTEM_PROMPT)]}
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
        if user.lower() in {"exit", "quit"}:
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
        seen = print(msgs[-1].content)

if __name__ == "__main__":
    # Small guard so the script exits cleanly in some terminals
    try:
        main()
    except Exception as exc:
        print(f"\n[Fatal] {exc}", file=sys.stderr)
        sys.exit(1)