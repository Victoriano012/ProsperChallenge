import os
import random
import string
import json
import yaml
from datetime import datetime
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.openai.llm import OpenAILLMService
from functools import lru_cache
from loguru import logger


######## System Prompt ########


def get_claim_number():
    """Generates a random, formatted claim number."""

    # Generate 7 random alphanumeric characters
    alphanumeric_chars = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=7)
    )

    # Insert "000" at a random position within the 7 characters
    insert_pos = random.randint(0, 7)
    claim_number = (
        alphanumeric_chars[:insert_pos] + "000" + alphanumeric_chars[insert_pos:]
    )

    return claim_number


@lru_cache
def get_questions():
    """Loads and caches the list of questions from a JSON file."""
    with open("questions.json", "r") as f:
        return json.load(f)


def get_system_prompt() -> str:
    """Constructs the full system prompt by loading a template and formatting it."""
    # Get a new claim number and the list of questions.
    claim_number = get_claim_number()
    claim_info = get_questions()

    # Load and format the system prompt.
    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read().strip()
    return system_prompt.format(claim_number=claim_number, claim_info=claim_info)


######## Log Answer Tool ########


def register_answer_func(filename: str):
    """Returns a closure that registers an answer to a specific YAML file."""

    if not os.path.exists(filename):
        with open(filename, "w") as f:
            yaml.dump({}, f)

    async def inner(params: FunctionCallParams):
        """The actual tool handler that logs the key/answer pair."""
        # Extract arguments from the function call.
        key = params.arguments["key"]
        answer = params.arguments["answer"]
        logger.info(f"Logging answer to {filename}: {key} = {answer}")

        # Read the existing data, update it, and write it back to the YAML file.
        with open(filename, "r") as f:
            data = yaml.safe_load(f) or {}
        data[key] = answer
        with open(filename, "w") as f:
            yaml.dump(data, f, indent=2)

        # Send a result back to the LLM.
        await params.result_callback(f"{key} registered")

    return inner


def get_register_tool(llm: OpenAILLMService):
    """Creates and registers the 'register_answer' tool with the LLM."""

    # Create a YAML filename store the answers and register the function.
    os.makedirs("registers", exist_ok=True)
    filename = f"registers/claim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    func = register_answer_func(filename)
    llm.register_function("register_answer", func)

    # Get the list of possible keys for the 'key' argument from the questions file.
    possible_keys = [question["key"] for question in get_questions()]

    # Define the schema for the 'register_answer' tool.
    register_answer_function = FunctionSchema(
        name="register_answer",
        description="Registers the extracted answer for a given question key",
        properties={
            "key": {
                "type": "string",
                "enum": possible_keys,
                "description": "The key for the question that was answered, e.g. 'submission_date'.",
            },
            "answer": {
                "type": "string",
                "description": "The answer extracted from the user's response.",
            },
        },
        required=["key", "answer"],
    )

    return register_answer_function
