import os
from dotenv import load_dotenv
from loguru import logger

from utils import get_system_prompt, get_tools

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
    llm = OpenAILLMService(api_key=OPENAI_API_KEY)
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
