# Things I could do in a future

- Try different stt/tts/llm
    - stt: whisper instead of gpt-4o-transcribe
    - tts: different speed/voice. Model `tts-1` (proposed by gemini)

- Things I have noticed

    - First bot:
        - The latency is huge, it looks like it's because it first generates the text answer and then does tts. It would be better if streamed.
        - It talks slowly

    - First bot following the conversation:
        - It doesn't hang for now, I will have to solve that
        - \<say-as interpret-as="digits"\> is not necessary
        - It talks for waaay too long, I should indicate in the prompt to do one sentence at a time.