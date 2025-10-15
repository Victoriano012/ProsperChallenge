# Structure of the bot code

The main file of the bot is `bot.py`. This file is abstracted from the specifics of the task, creating a general voice chatbot, whose system prompt and tools is provided by `utils.py`, which uses the files in `data` to obtain the system_prompt. When it has a call, it will register the obtained answers in the `registers` folder.


# Status of Deployment

The bot is not accessible through a phone number.

The bot is currently deployed at pipecat cloud, and it can be accessed by running `talk_to_agent.sh` setting the environment variable PIPECAT_API_KEY (I think my personal key is necessary, so it's provided in the `data/PIPECAT_API_KEY` file, please do not use it unfaithfully).

The `server.py` script should make the bot accessible through the phone number `+12096553791`, which I bought from daily. After running the script with `ENV=local` and ngrok tunneling, when we call, Daily makes a request to our API, then through this script we create a Daily room, the bot joins the room and we request Daily to redirect the call to that room through the `https://api.daily.co/v1/dialin/pinlessCallUpdate` endpoint. This requests returns a 200 code, indicating the request was received and processed okay, but then it hungs up the call. (this server is not currently up) (I changed line 172 of `pipecat.runner.daily` to `room_properties.enable_dialout = False`, otherwise it wouldn't create the room, this might have been an issue)


# Things I could do

- I would like to use Cartesia/Deepgram since they should be faster.
- Measure latency
- I want the bot to email me the results of a call
- The registers could have a fixed format
- Allow it to hung up?
