from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel
import os
from agents.model_settings import ModelSettings


agent = Agent(
    name="Assistant",
    instructions="You only respond in haikus.",
    model=LitellmModel(
        # Pick any OpenRouter-listed model; these IDs work with LiteLLM
        # Good, safe pick for tool-calling via OpenAI spec:
        model="openrouter/google/gemini-2.5-flash",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    model_settings=ModelSettings(
    temperature=0,
)
)

result = Runner.run_sync(agent, "How are you doing today")
print(result.final_output)
