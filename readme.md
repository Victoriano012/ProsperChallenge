# Structure of the code

The main file of the bot is `bot.py`. This file is abstracted from the specifics of the task, creating a general voice chatbot, whose system prompt and tools is provided by `utils.py`, which uses the files in `data/` to obtain the system_prompt. When it has a call, it will register the obtained answers in the `registers` folder and also send them to my email.

The folder `old/` has previous efforts of doing this bot using Daily instead of Twilio and `analyze_logs.py` is used for latency evaluation.


# Deployment

To run the bot locally just run 
```
python bot.py
```
to link it to the telephone number, use the following command instead 
```
python bot.py --transport twilio --proxy your-ngrok-url.ngrok.io
```

The bot is accessible by calling the phone number `(229) 515-9541`.


# Latency Evaluation

### Simple model latency evaluation

I had a couple of conversations locally, logging the default Pipecat logs (see an example at `data/example.log`) and using `analyze_logs.py` to analyze latencies.

The result are that Cartesia TTS and Deepgram STT are extremely fast, requiring around $10^{-3}$ s/query and never going over $10^{-2}$ s/query. Clearly negligible compared to the ~$1$ s/query on average of the OpenAI gpt-4.1 LLM.

(Cartesia does multiple calls per LLM generation, which implies a bit more latency, but it's not relevant because it's in the middle of the agent turn and it doesn't make their speech less fluid)

They are also much faster than OpenAI's STT/TTS, which took around $1$ s/sample each.

### Couple of notes

The default values for `stop_secs` and `start_secs` (silence time required after person talks and before agent starts speaking respectively) was 0.2. Testing, I noted that it would normally consider I stopped talking before I was finished saying the request number, thus I changed `stop_secs=0.3` and since the latency is already quite big, I also changed `start_secs=0.0`. Therefore the total waiting time should be $1.3$ s

I also tried gpt-4.1-mini and gpt-4.1-nano, but even though they were slightly faster, they said non-sensical things. Therefore I discarded using them.

It might be a good option to stream the outputs of the LLM into Cartesia TTS, since the average TTFB is of ~$0.65$ s/sample for the LLM, we'd be then winning ~$0.35$ s/sample.

### Block times analysis

Interestingly, the time between the `End of Turn result: EndOfTurnState` log and the `Bot started speaking` log (called `block time` in `analyze_logs.py`) is quite bigger than $1.3$ s, generally close to $2$ seconds at least. Sometimes it's bigger, when the register has been updated; because it requires 2 LLM usages, one to call the tool to register and another to then speak. This latter observation could be solved by having two LLMs in the conversation, one listening and logging while the other maintaining the conversastion. Or it could also be solved by analysing the conversation and doing the registry at the end of the conversation, not during it.

More worring is the difference between ~$1.3$ s/sample that we should be getting and ~$2$ s/sample we are actually seeing in the logs, and would require more investigation.

### "Real latency"

Getting the real latency is much harder, even though looking at the block time is close, it's not quite the same. We would have to record some audio of a conversation and do the analysis there.

I have done an approximation of that, manually timing the time between when I stopped speaking and when the bot started speaking, and the result was around $2.5$/$2.6$ s/sample. This aligns with the $2$ seconds of block time, + $0.3$ seconds of `stop_secs` + $0.2$ or $0.3$ seconds of human reaction.

This was done locally, the same could be done on the phone call. Through the call the latency is bigger, but that extra latency is purely due to the communication and out of our control.


# Extra things that could be done

- The registers could have a fixed format
- Decrease latency: Stream LLM output into TTS / Register answers "offline" / Investigate Cartesia TTFB


# Attribution

- `bot.py` is based on https://github.com/pipecat-ai/pipecat-quickstart-phone-bot/blob/main/bot.py
