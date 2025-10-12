# Things I could do in a future

- Try different stt/tts/llm
    - stt: whisper instead of gpt-4o-transcribe
    - tts: different speed/voice. Model `tts-1` (proposed by gemini)

- Things I have noticed
    - The latency is huge, it looks like it's because it first generates the text answer and then does tts. It would be better if streamed.
    - It talks slowly