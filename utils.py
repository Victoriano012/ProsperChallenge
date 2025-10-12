import random
import string
import json
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.openai.llm import OpenAILLMService
from functools import lru_cache
from loguru import logger

######## System Prompt ########


def get_claim_number():

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
    with open("questions.json", "r") as f:
        return json.load(f)


def get_system_prompt() -> str:
    claim_number = get_claim_number()
    claim_info = get_questions()

    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read().strip()

    return system_prompt.format(claim_number=claim_number, claim_info=claim_info)


######## Log Answer Tool ########


async def register_answer(params: FunctionCallParams):
    logger.info(
        f"Logging answer: {params.arguments['key']} = {params.arguments['answer']}"
    )


def get_register_tool(llm: OpenAILLMService):
    llm.register_function("register_answer", register_answer)

    questions = get_questions()
    possible_keys = [question["key"] for question in questions]

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
