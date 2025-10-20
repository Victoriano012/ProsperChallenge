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
from collections import defaultdict

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

######## Event Dispatcher ########


class EventDispatcher:
    def __init__(self):
        self._listeners = defaultdict(list)

    def event_handler(self, event_name: str):
        """Decorator to register a listener for an event."""

        def decorator(func):
            self._listeners[event_name].append(func)
            return func

        return decorator

    async def dispatch(self, event_name: str, *args, **kwargs):
        if event_name in self._listeners:
            for listener in self._listeners[event_name]:
                await listener(*args, **kwargs)


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
    with open("data/questions.json", "r") as f:
        return json.load(f)


def get_system_prompt() -> str:
    """Constructs the full system prompt by loading a template and formatting it."""
    # Get a new claim number and the list of questions.
    claim_number = get_claim_number()
    claim_info = get_questions()

    # Load and format the system prompt.
    with open("data/system_prompt.txt", "r") as f:
        system_prompt = f.read().strip()
    return system_prompt.format(claim_number=claim_number, claim_info=claim_info)


######## Log Answer Tool ########


def send_email(recipient_email: str, subject: str, body: str):
    """Sends an email using SMTP."""
    sender_email = os.getenv("SENDER_EMAIL")
    # For Gmail, this should be an App Password if 2FA is enabled
    sender_password = os.getenv("SENDER_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))

    if not all([sender_email, sender_password]):
        logger.error(
            "SENDER_EMAIL or SENDER_PASSWORD environment variables not set. Cannot send email."
        )
        return

    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        # Connect to the server and send the email
        logger.info(
            f"Connecting to SMTP server {smtp_server}:{smtp_port} to send email..."
        )
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)
            logger.info(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def register_answer_func(filename: str):
    """Returns a closure that registers an answer to a specific YAML file."""

    if not os.path.exists(filename):
        with open(filename, "w") as f:
            yaml.dump({}, f)
    num_questions = len(get_questions())

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

        # I will get the registers on my email as well
        if len(data) >= num_questions:
            logger.info("Sending email with collected data...")
            recipient = "victorconchello@gmail.com"
            subject = "Claim Information Collected"
            # Format the data nicely for the email body
            body = "The following claim information has been collected:\n\n"
            body += yaml.dump(data)
            send_email(recipient, subject, body)

        # Send a result back to the LLM.
        await params.result_callback(f"{key} registered")

    return inner


def hang_up_func(dispatcher: EventDispatcher):

    async def inner(params: FunctionCallParams):
        """Dispatches a 'hang_up' event to terminate the call."""
        logger.info("LLM requested to hang up the call. Dispatching hang_up event.")
        await dispatcher.dispatch("hang_up")

    return inner


def get_tools(
    llm: OpenAILLMService, dispatcher: EventDispatcher
) -> list[FunctionSchema]:
    """Creates and registers the 'register_answer' tool with the LLM."""
    # Create a YAML filename store the answers and register the function.
    os.makedirs("registers", exist_ok=True)
    filename = f"registers/claim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    llm.register_function("register_answer", register_answer_func(filename))

    # Get the list of possible keys for the 'key' argument from the questions file.
    possible_keys = [question["key"] for question in get_questions()]

    # Define the schema for the 'register_answer' tool.
    register_answer_tool = FunctionSchema(
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

    ### Hang up tool
    llm.register_function("hang_up", hang_up_func(dispatcher))
    hang_up_tool = FunctionSchema(
        name="hang_up",
        description="Ends the current call. To be used only after all questions have been answered and both parts have said their goodbyes.",
        properties={},
        required=[],
    )

    return [register_answer_tool, hang_up_tool]
