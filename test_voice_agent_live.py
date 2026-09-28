import asyncio
import base64
import json
import urllib.parse
import wave
import websockets
import os
import sys

def generate_temporary_token(expires_in=300):
    import requests
    env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key and os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("ASSEMBLYAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
    resp = requests.get(
        "https://agents.assemblyai.com/v1/token",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"expires_in_seconds": expires_in},
        timeout=10,
    )
    if resp.status_code == 405:
        resp = requests.post(
            "https://agents.assemblyai.com/v1/token",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"expires_in_seconds": expires_in},
            timeout=10,
        )
    resp.raise_for_status()
    return resp.json()["token"]

async def test_live_voice():
    # 1. Read the wav file
    wf = wave.open("test_speech.wav", "rb")
    print(f"WAV parameters: channels={wf.getnchannels()}, sampwidth={wf.getsampwidth()}, framerate={wf.getframerate()}, nframes={wf.getnframes()}")
    raw_audio = wf.readframes(wf.getnframes())
    wf.close()

    # 2. Get token
    token = generate_temporary_token(300)
    ws_url = f"wss://agents.assemblyai.com/v1/ws?token={urllib.parse.quote(token)}"

    async with websockets.connect(ws_url) as ws:
        print("Connected to AssemblyAI WebSocket!")

        # 3. Send session.update
        tools = [
            {
                "type": "function",
                "name": "save_observation",
                "description": "Record an observation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field_name": {"type": "string"},
                        "value": {"type": "string"}
                    },
                    "required": ["field_name", "value"]
                }
            }
        ]

        session_update = {
            "type": "session.update",
            "session": {
                "system_prompt": "You are FieldVoice, an industrial inspection assistant. Record observations using save_observation.",
                "greeting": "Hi, I am FieldVoice. What are your readings?",
                "input": {
                    "format": {"encoding": "audio/pcm"},
                    "turn_detection": {
                        "vad_threshold": 0.3,
                        "min_silence": 600,
                        "max_silence": 1500,
                        "interrupt_response": True
                    },
                    "keyterms": ["temperature", "pressure", "vibration", "leakage"]
                },
                "output": {
                    "format": {"encoding": "audio/pcm"},
                    "voice": "james"
                },
                "tools": tools
            }
        }
        await ws.send(json.dumps(session_update))

        # 4. Background listener for incoming events
        async def listen():
            try:
                async for raw in ws:
                    msg = json.loads(raw)
                    mtype = msg.get("type")
                    if mtype == "reply.audio":
                        continue
                    print(f"\n[EVENT FROM SERVER] type={mtype} -> {json.dumps({k: v for k, v in msg.items() if k != 'audio'})}")
            except Exception as e:
                print(f"Listener ended: {e}")

        listener_task = asyncio.create_task(listen())

        # Wait for greeting to finish
        print("Waiting 4 seconds for greeting...")
        await asyncio.sleep(4)

        # 5. Stream the speech in 50ms chunks (1200 samples = 2400 bytes)
        chunk_size = 2400
        print(f"Streaming {len(raw_audio)} bytes of speech in 50ms chunks...")
        for offset in range(0, len(raw_audio), chunk_size):
            chunk = raw_audio[offset:offset+chunk_size]
            b64 = base64.b64encode(chunk).decode("ascii")
            await ws.send(json.dumps({"type": "input.audio", "audio": b64}))
            await asyncio.sleep(0.05)

        print("Finished sending speech audio. Sending 2 seconds of silence for turn detection...")
        silence_chunk = bytes(2400)
        for _ in range(40): # 2 seconds of silence
            b64 = base64.b64encode(silence_chunk).decode("ascii")
            await ws.send(json.dumps({"type": "input.audio", "audio": b64}))
            await asyncio.sleep(0.05)

        print("Waiting 6 seconds for agent reply...")
        await asyncio.sleep(6)
        listener_task.cancel()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))
    asyncio.run(test_live_voice())
