import os
import sys
import wave
import pyaudio
import keyboard
import asyncio
import getpass
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs import Voice, VoiceSettings, ElevenLabs
from langchain_openai import ChatOpenAI
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from io import BytesIO
from browser_use import Controller, ActionResult
from elevenlabs import play as play_audio
from browser_use.agent.views import (
	ActionResult,
	AgentError,
	AgentHistory,
	AgentHistoryList,
	AgentOutput,
	AgentStepInfo,
)
# Load environment variables
load_dotenv()

class AgentWithSpeech(Agent):
    def _log_response(self, response: AgentOutput) -> None:
        # Call the original _log_response method
        super()._log_response(response)
        # Call the text_to_speech function
        text_to_speech(response.current_state.evaluation_previous_goal)


if "MISTRAL_API_KEY" not in os.environ:
    os.environ["MISTRAL_API_KEY"] = getpass.getpass("Enter your Mistral API key: ")

if "ELEVENLABS_API_KEY" not in os.environ:
    os.environ["ELEVENLABS_API_KEY"] = getpass.getpass("Enter your ElevenLabs API key: ")

client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)
# Configure browser
browser = Browser(
    config=BrowserConfig(
        chrome_instance_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
)

controller = Controller()

# Audio recording parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
AUDIO_FILE = "recorded_audio.wav"

@controller.action('Ask user for information')
def ask_human(question: str) -> str:
    """Starts recording when 'A' is pressed and stops when 'S' is pressed, then transcribes the text."""
    print(f"\n{question}\nPress 'A' to start recording.")
    audio = client.text_to_speech.convert(
        text=question,  # Text to convert to speech
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
    )
    play_audio(audio)

    keyboard.wait('a')  # Wait for 'A' to be pressed to start recording
    print("Recording... Speak now.")
    print("Press 'S' to stop recording.")

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []

    while True:
        if keyboard.is_pressed('s'):  # Stop recording when 'S' is pressed
            print("Manual stop detected. Stopping recording.")
            break
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    print("Recording stopped.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save recorded audio
    with wave.open(AUDIO_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    # Transcribe audio
    transcribed_text = transcribe_audio()
    print(f"Transcribed Text: {transcribed_text}")

    return ActionResult(extracted_content=transcribed_text)


@controller.action("Recieve feedback")
def recieve_feedback(feedback: str):
    """Recieves feedback from the user."""
    print(f"\nFeedback: {feedback}")
    audio = client.text_to_speech.convert(
        text=feedback,  # Text to convert to speech
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
    )
    play_audio(audio)

    return ActionResult()

# Audio recording parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
AUDIO_FILE = "recorded_audio.wav"

def transcribe(audio_file):
    transcription = client.speech_to_text.convert(
    file=BytesIO(audio_file.read()), # Audio file to transcribe
    model_id="scribe_v1", # Model to use, for now only "scribe_v1" and "scribe_v1_base" are supported
    tag_audio_events=True, # Tag audio events like laughter, applause, etc.
    language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
    diarize=True, # Whether to annotate who is speaking
)
    return transcription.text


def record_audio():
    """Records audio until the 'X' key is released."""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    
    print("Recording... Press 'X' to stop.")
    while keyboard.is_pressed('x'):
        data = stream.read(CHUNK)
        frames.append(data)
    
    print("Recording stopped.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save recorded audio
    with wave.open(AUDIO_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def transcribe_audio():
    """Transcribes recorded audio using ElevenLabs API."""
    with open(AUDIO_FILE, "rb") as audio_file:
        transcription = transcribe(audio_file)
    return transcription

def text_to_speech(text, play=True):
    audio = client.text_to_speech.convert(
        text=text,  # Text to convert to speech
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    if play:
        play_audio(audio)
    return audio


async def main():

    # audio = client.text_to_speech.convert(
    #     text="How can i help you today",  # Text to convert to speech
    # voice_id="JBFqnCBsd6RMkjVDRZzb",
    # model_id="eleven_multilingual_v2",
    # output_format="mp3_44100_128",
    # )
    # play_audio(audio)
    
    print("Press 'X' to start recording.")
    
    keyboard.wait('x')  # Wait for 'X' key press
    record_audio()  # Start recording
    task_text = transcribe_audio()  # Transcribe recorded audio
    print(f"Transcribed Text: {task_text}")
    
    # Initialize and run agent with the transcribed task
    agent = AgentWithSpeech(
        task="If any information is missing to achieve the goal, for example details about the user ask a question to the user using 'Ask user for information'. Your ultimate goal is this task: \n" + task_text,
        llm=ChatOpenAI(model='gpt-4o'),
        browser=browser,
        controller=controller,
        

    )



    
    await agent.run()
    await browser.close()

    input('Press Enter to close...')

if __name__ == '__main__':
    asyncio.run(main())
