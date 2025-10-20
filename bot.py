import os

from pipecat.audio.vad.vad_analyzer import VADParams

from utils import EventDispatcher, get_system_prompt, get_tools
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.runner.utils import create_transport
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.transports.base_transport import TransportParams

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def run_bot(transport: BaseTransport):
    logger.info(f"Starting bot")

    # Initialize the STT, TTS, LLM, and RTVI services.
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="e07c00bc-4134-4eae-9ea4-1a55fb45746b",
    )
    # stt = OpenAISTTService(api_key=OPENAI_API_KEY)
    # tts = OpenAITTSService(api_key=OPENAI_API_KEY)
    llm = OpenAILLMService(api_key=OPENAI_API_KEY, model="gpt-4.1")
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Set up the initial LLM context with a system prompt and tools.
    dispatcher = EventDispatcher()
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    tools = ToolsSchema(standard_tools=get_tools(llm, dispatcher))
    context = LLMContext(messages, tools)
    context_aggregator = LLMContextAggregatorPair(context)

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

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @dispatcher.event_handler("hang_up")
    async def on_hang_up():
        logger.info("Hang up event received, ending the call.")
        await task.queue_frame(EndFrame())

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Kick off the conversation.
        await task.queue_frame(LLMRunFrame())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""

    common_transport_params = {
        "audio_in_enabled": True,
        "audio_out_enabled": True,
        "vad_analyzer": SileroVADAnalyzer(
            params=VADParams(stop_secs=0.3, start_secs=0.0)
        ),
    }
    transport_params = {
        "webrtc": lambda: TransportParams(
            **common_transport_params,
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
        "twilio": lambda: FastAPIWebsocketParams(
            **common_transport_params,
        ),
    }
    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
