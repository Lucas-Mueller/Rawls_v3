#!/usr/bin/env python3
import json
import re

# Load the notebook
with open('hypothesis_testing/hypothesis_2/Hypothesis_2_main.ipynb', 'r') as f:
    notebook = json.load(f)

# Find the cell with build_config
for cell in notebook['cells']:
    if cell['cell_type'] == 'code' and 'build_config' in cell['source'][0]:
        # Update the source
        source = cell['source'][0]  # It's a single string with escaped newlines

        # Replace the function signature
        source = source.replace(
            'def build_config(temp: float, models: list[str]) -> dict:',
            'def build_config(temp: float, models: list[str], transcript_output_path: str) -> dict:'
        )

        # Replace the return dict to add transcript_logging
        source = source.replace(
            "'original_values_mode': { 'enabled': True },",
            "'original_values_mode': { 'enabled': True },\n        'transcript_logging': {\n            'enabled': True,\n            'output_path': transcript_output_path,\n            'include_memory_updates': True,\n            'include_instructions': True,\n            'include_input_prompts': True,\n            'include_agent_responses': True,\n        },"
        )

        # Replace the function call
        source = source.replace(
            'cfg = build_config(temp=temp,models=models)',
            "transcript_path = str(TRANSCRIPTS_BASE / group_key / f'hypothesis_2_{group_key}_condition_{idx}_transcript.json')\n                cfg = build_config(temp=temp, models=models, transcript_output_path=transcript_path)"
        )

        cell['source'] = [source]
        break

# Save the notebook
with open('hypothesis_testing/hypothesis_2/Hypothesis_2_main.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)

print("Notebook updated successfully")