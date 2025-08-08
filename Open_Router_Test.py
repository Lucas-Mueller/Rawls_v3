from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel
import os, sys

@function_tool
def get_weather(city: str):
    return f"The weather in {city} is sunny."

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or input("Enter OpenRouter API key: ")

agent = Agent(
    name="Assistant",
    instructions="You only respond in haikus.",
    model=LitellmModel(
        # Use OpenRouter provider prefix so no base URL is needed
        model="openrouter/anthropic/claude-3.5-sonnet",
        api_key=OPENROUTER_API_KEY,
        # Optional but recommended on OpenRouter:
        extra_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "AgentsSDK Test",
        },
    ),
    tools=[get_weather],
)

result = Runner.run_sync(agent, "What's the weather in Tokyo?")
print(result.final_output)
