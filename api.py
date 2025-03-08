import os
import sys
import wave
import asyncio
import base64
import getpass
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from elevenlabs import ElevenLabs, play as play_audio
from langchain_openai import ChatOpenAI
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from io import BytesIO
from browser_use import Controller, ActionResult
from browser_use.agent.views import (
	ActionResult,

	AgentStepInfo,
)

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
# Load environment variables
load_dotenv()

if "MISTRAL_API_KEY" not in os.environ:
    os.environ["MISTRAL_API_KEY"] = getpass.getpass("Enter your Mistral API key: ")

if "ELEVENLABS_API_KEY" not in os.environ:
    os.environ["ELEVENLABS_API_KEY"] = getpass.getpass("Enter your ElevenLabs API key: ")

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Configure browser
browser = Browser(
    config=BrowserConfig(
        chrome_instance_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
)

controller = Controller()

# Audio file path used for saving client-sent audio
AUDIO_FILE = "recorded_audio.wav"

def transcribe(audio_file):
    transcription = client.speech_to_text.convert(
        file=BytesIO(audio_file.read()),
        model_id="scribe_v1",
        tag_audio_events=True,
        language_code="eng",
        diarize=True,
    )
    return transcription.text

def transcribe_audio():
    with open(AUDIO_FILE, "rb") as audio_file:
        transcription = transcribe(audio_file)
    return transcription

async def text_to_speech(text):
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    # Optionally play audio locally if desired
    return audio

# Global variable to hold the active websocket connection
client_websocket = None

async def send_to_client(msg_type: str, data: str):
    global client_websocket
    if client_websocket:
        await client_websocket.send_json({"type": msg_type, "data": data})
    else:
        print("No client websocket connection")

# Extend the Agent class so that whenever it logs a response it sends feedback to the client
import asyncio

import base64
import asyncio

class AgentWithSpeech(Agent):
    def _log_response(self, response: ActionResult) -> None:
        super()._log_response(response)
        text_feedback = response.current_state.evaluation_previous_goal
        # Schedule sending both text and audio feedback
        # asyncio.create_task(self.send_feedback_audio(text_feedback))
        asyncio.create_task(self.send_feedback_text(text_feedback))

    async def step(self, step_info: Optional[AgentStepInfo] = None) -> None:
        await super().step(step_info)
        # If the agent is waiting for user input, send a message to the client
        if len(self._last_result) > 0 and self._last_result[-1].is_done:
            await send_to_client("finished","Final Result: " + self._last_result[-1].extracted_content)
            await self.send_feedback_audio("Final Result: " + self._last_result[-1].extracted_content)
    
    async def send_feedback_audio(self, text: str):
        # Generate audio from the text
        audio = await text_to_speech(text)
        # Convert the generator output to a bytes object by joining the chunks
        audio_bytes = b"".join(audio)
        # Base64-encode the audio bytes
        encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
        # Send audio feedback to the client
        await send_to_client("feedback_audio", encoded_audio)
        # Optionally, also send the text feedback
        await send_to_client("feedback_text", text)


    async def send_feedback_text(self, text: str):
        await send_to_client("feedback_text", text)






# When the agent needs to ask the user for additional information the question is sent to the client
@controller.action("Ask user for information")
async def ask_human(question: str) -> ActionResult:
    global client_websocket
    if client_websocket:
        # Send the question to the client over the WebSocket
        await client_websocket.send_json({"type": "question", "data": question})
        audio = await text_to_speech(question)
        # Convert the generator output to a bytes object by joining the chunks
        audio_bytes = b"".join(audio)
        # Base64-encode the audio bytes
        encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
        # Send audio feedback to the client
        await send_to_client("feedback_audio", encoded_audio)
        await send_to_client("feedback_audio", question)
        # Wait for the client's response
        response = await client_websocket.receive_json()
        if response.get("type") == "audio":
            # Decode the base64-encoded audio and save it to a file
            audio_base64 = response.get("data")
            audio_data = base64.b64decode(audio_base64)
            with open(AUDIO_FILE, "wb") as f:
                f.write(audio_data)
            # Transcribe the saved audio and return the text
            transcribed_text = transcribe_audio()
            return ActionResult(extracted_content=transcribed_text)
        else:
            # If the response is text, return it directly
            text = response.get("data", "")
            
            return ActionResult(extracted_content=text)
    else:
        raise Exception("No client websocket connection")

# When the agent wants to deliver feedback this action sends it to the client
@controller.action("Recieve feedback")
async def recieve_feedback(feedback: str) -> ActionResult:
    global client_websocket
    if client_websocket:
        await client_websocket.send_json({"type": "feedback", "data": feedback})
        return ActionResult()
    else:
        raise Exception("No client websocket connection")

async def run_agent(task_text: str):
    global agent
    agent = AgentWithSpeech(
        task="If any information is missing to achieve the goal, for example details about the user ask a question to the user using 'Ask user for information'. Your ultimate goal is this task: \n" + task_text,
        llm=ChatOpenAI(model="gpt-4o"),
        browser=browser,
        controller=controller,
    )
    
    await agent.run()
    await browser.close()

# Set up FastAPI and the WebSocket endpoint
app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global client_websocket
    await websocket.accept()
    client_websocket = websocket
    try:
        # Wait for a start message from the client containing the initial task text.
        message = await websocket.receive_json()
        if message.get("type") == "start":
            task_text = message.get("data", "")
            await websocket.send_json({"type": "ack", "data": "Starting agent with task: " + task_text})
            # Run the agent using the provided task text.
            await run_agent(task_text)
        if message.get("type") == "newAgent":
            await websocket.send_json({"type": "ack", "data": "Starting agent with task: " + message.get("data")})
            text = "Starting agent with task: " + message.get("data")
            audio = await text_to_speech(text)
        # Convert the generator output to a bytes object by joining the chunks
            audio_bytes = b"".join(audio)
            # Base64-encode the audio bytes
            encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
            # Send audio feedback to the client
            await send_to_client("feedback_audio", encoded_audio)
            await run_agent(message.get("data"))
        # Keep the connection open.
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        client_websocket = None

    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
