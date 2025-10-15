# Structure of the bot code

The main file of the bot is `bot.py`. This file is abstracted from the specifics of the task, creating a general voice chatbot, whose system prompt and tools is provided by `utils.py`, which uses the files in `data` to obtain the system_prompt. When it has a call, it will register the obtained answers in the `registers` folder and also send them to my email.


# Status of Deployment

The bot is not accessible through a phone number.

The bot is currently deployed at pipecat cloud, and it can be accessed by running `talk_to_agent.sh` setting the environment variable PIPECAT_API_KEY (I think my personal key is necessary, so it's provided in the `data/PIPECAT_API_KEY` file, please do not use it unfaithfully).

The `server.py` script should make the bot accessible through the phone number `+12096553791`, which I bought from daily. After running the script with `ENV=local` and ngrok tunneling, when we call, Daily makes a request to our API, then through this script we create a Daily room, the bot joins the room and we request Daily to redirect the call to that room through the `https://api.daily.co/v1/dialin/pinlessCallUpdate` endpoint. This requests returns a 200 code, indicating the request was received and processed okay, but then it hungs up the call. (this server is not currently up) (I changed line 172 of `pipecat.runner.daily` to `room_properties.enable_dialout = False`, otherwise it wouldn't create the room, this might have been an issue)


# Latency Evaluation

### Simple model latency evaluation

I had a couple of conversations, logging the default Pipecat logs (see an example at `data/example.log`) and using `analyze_logs.py` to analyze latencies.

The result are that Cartesia TTS and Deepgram STT are extremely fast, requiring around $10^{-3}$ s/query and never going over $10^{-2}$ s/query. Clearly negligible compared to the ~$1$ s/query on average of the OpenAI gpt-4.1 LLM.

(Cartesia does multiple calls per LLM generation, which implies a bit more latency, but it's not relevant because it's in the middle of the agent turn and it doesn't make their speech less fluid)

They are also much faster than OpenAI's STT/TTS, which took around $1$ s/sample each.

### Couple of notes

The default values for `stop_secs` and `start_secs` (silence time required after person talks and before agent starts speaking respectively) was 0.2. Testing, I noted that it would normally consider I stopped talking before I was finished saying the request number, thus I changed `stop_secs=0.3` and since the latency is already quite big, I also changed `start_secs=0.0`. Therefore the total waiting time should be $1.3$ s

I also changed from gpt-4.1 to gpt-4.1-mini, changing the LLM processing time to $0.7$ on average (this was done after the latency evaluation, so all the comments refer to tests with gpt-4.1). I also tried with gpt-4.1-nano, but it said non-sensical things.

It might be a good option to stream the outputs of the LLM into Cartesia TTS, since the average TTFB is of ~$0.65$ s/sample for the LLM, we'd be then winning ~$0.35$ s/sample.

### Block times analysis

Interestingly, the time between the `End of Turn result: EndOfTurnState` log and the `Bot started speaking` log (called `block time` in `analyze_logs.py`) is quite bigger than $1.3$ s, generally close to $2$ seconds at least. Sometimes it's bigger, when the register has been updated; because it requires 2 LLM usages, one to call the tool to register and another to then speak. This latter observation could be solved by having two LLMs in the conversation, one listening and logging while the other maintaining the conversastion. Or it could also be solved by analysing the conversation and doing the registry at the end of the conversation, not during it.

More worringly is the difference between ~$1.3$ s/sample that we should be getting and ~$2$ s/sample we are actually seeing in the logs, and would require more investigation.

### "Real latency"

Getting the real latency is much harder, even though looking at the block time is close, it's not quite the same. We would have to record some audio of a conversation and do the analysis there.

I have done an approximation of that, manually timing the time between when I stopped speaking and when the bot started speaking, and the result was around $2.5$/$2.6$ s/sample. This aligns with the $2$ seconds of block time, + $0.3$ seconds of `stop_secs` + $0.2$ or $0.3$ seconds of human reaction.


# Extra things I could do

- The registers could have a fixed format
- Allow it to hung up
- Decrease latency: Stream LLM output into TTS / Register answers "offline"


# Attribution

- `server.py` is based on https://github.com/pipecat-ai/pipecat-examples/blob/main/phone-chatbot/daily-pstn-dial-in/server.py
- Many things are based on https://github.com/pipecat-ai/pipecat-quickstart
