from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel
import os

@function_tool
def get_weather(city: str):
    return f"The weather in {city} is sunny."

agent = Agent(
    name="Assistant",
    instructions="You only respond in haikus.",
    model=LitellmModel(
        # Pick any OpenRouter-listed model; these IDs work with LiteLLM
        # Good, safe pick for tool-calling via OpenAI spec:
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    tools=[get_weather],
)

result = Runner.run_sync(agent, "What's the weather in Tokyo?")
print(result.final_output)
