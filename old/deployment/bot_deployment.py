# This script merges bot.py, utils.py, questions.json and system_prompt.txt into a single file for easier deployment.

################################################################################################
######################################## Utils #################################################
################################################################################################

import os
import random
import string
import yaml
from datetime import datetime
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.openai.llm import OpenAILLMService
from loguru import logger

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

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


def get_questions():
    """Loads and caches the list of questions from a JSON file."""
    return [
        {"key": "submission_date", "question": "When was the claim submitted?"},
        {"key": "status", "question": "What is the status?"},
        {"key": "claim_number", "question": "What is the claim number?"},
    ]


system_prompt = """### Persona
You are a professional and polite AI agent from an insurance company. Your task is to call a service center to retrieve specific information about a claim.

**IMPORTANT**: Your responses must be very brief. You must only perform **one action at a time** and then **wait for the other person to respond** before continuing. For example, after your greeting, you must wait for a response before stating the claim number.

### Your Goal
Your goal is to gather the following information for claim number **{claim_number}**:
```json
{claim_info}
```

### Conversation Flow
Follow these steps precisely:

1.  **Greeting:** Start with a friendly and professional greeting. **Then wait for a response.**
2.  **State Claim Number:** Clearly state that you are calling about a claim and provide the number. When you output the claim number, format it with spaces between each character. This ensures it is read out digit by digit. **Then wait for a response.**
3.  **Ask Questions:** Based on the JSON object above, ask for the required information **one question at a time, waiting for a response after each one.**
4.  **Handle Responses:**
    *   If you get a clear answer, acknowledge it and move to the next question.
    *   If the answer is unclear or you don't get one, politely ask the same question again.
    *   If you still don't get an answer after the second attempt, say "Okay, I'll move on for now" and proceed to the next question. Do not get stuck.
5.  **Conclusion:** Once you have attempted to get an answer for all questions, politely end the conversation with a thank you and a goodbye."""


def get_system_prompt() -> str:
    """Constructs the full system prompt by loading a template and formatting it."""
    # Get a new claim number and the list of questions.
    claim_number = get_claim_number()
    claim_info = get_questions()

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


def get_tools(llm: OpenAILLMService):
    """Creates and registers the 'register_answer' tool with the LLM."""

    # Create a YAML filename store the answers and register the function.
    os.makedirs("registers", exist_ok=True)
    filename = f"registers/claim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    func = register_answer_func(filename)
    llm.register_function("register_answer", func)

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

    return [register_answer_tool]


################################################################################################
######################################### Bot ##################################################
################################################################################################

import os
from dotenv import load_dotenv
from loguru import logger

print("🚀 Starting Pipecat bot...")

logger.info("Loading Local Smart Turn Analyzer V3...")
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

logger.info("✅ Local Smart Turn Analyzer V3 loaded")
logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")

from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame

logger.info("Loading pipeline components...")
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService

from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.adapters.schemas.tools_schema import ToolsSchema

logger.info("✅ All components loaded successfully!")

# Load environment variables from .env file and get the OpenAI API key.
load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")

    # Initialize the STT, TTS, LLM, and RTVI services.
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="e07c00bc-4134-4eae-9ea4-1a55fb45746b",
    )
    # stt = OpenAISTTService(api_key=OPENAI_API_KEY)
    # tts = OpenAITTSService(api_key=OPENAI_API_KEY)
    llm = OpenAILLMService(api_key=OPENAI_API_KEY, model="gpt-4.1-mini")
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Set up the initial LLM context with a system prompt and tools.
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    tools = ToolsSchema(standard_tools=get_tools(llm))
    context = LLMContext(messages, tools)
    context_aggregator = LLMContextAggregatorPair(context)

    # Define the processing pipeline with all the services.
    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi,  # RTVI processor
            stt,
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    # Create a pipeline task with metrics enabled and an observer.
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Kick off the conversation.
        logger.info(f"Client connected")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    # Create a runner and run the pipeline task.
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""
    stop_secs = 0.3
    start_secs = 0.0

    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(stop_secs=stop_secs, start_secs=start_secs)
            ),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(stop_secs=stop_secs, start_secs=start_secs)
            ),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
