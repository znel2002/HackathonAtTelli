import os
import wave
import pyaudio
import gradio as gr
import asyncio
import threading
from io import BytesIO
from elevenlabs import ElevenLabs, play as play_audio
from langchain_openai import ChatOpenAI
from browser_use import Agent, Controller, ActionResult
from browser_use.browser.browser import Browser, BrowserConfig
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize ElevenLabs
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Configure browser
browser = Browser(
    config=BrowserConfig(
        chrome_instance_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
)

controller = Controller()

# Audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
AUDIO_FILE = "recorded_audio.wav"

# Global variable to control recording state
recording = False

def record_audio():
    """Records audio until stopped manually."""
    global recording
    recording = True
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    
    print("Recording started. Speak now.")
    while recording:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    
    print("Recording stopped.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(AUDIO_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def start_recording():
    """Starts the recording in a separate thread."""
    global recording
    if not recording:
        threading.Thread(target=record_audio, daemon=True).start()
    return "Recording... Press 'Stop' when done."

def stop_recording():
    """Stops the recording."""
    global recording
    recording = False
    return transcribe_audio()

def transcribe_audio():
    """Transcribes recorded audio using ElevenLabs."""
    with open(AUDIO_FILE, "rb") as audio_file:
        transcription = client.speech_to_text.convert(
            file=BytesIO(audio_file.read()),
            model_id="scribe_v1",
            tag_audio_events=True,
            language_code="eng",
            diarize=True,
        )
    return transcription.text

@controller.action('Ask user for information')
def ask_human(question: str) -> ActionResult:
    """Prompts the user via speech, records their response, and transcribes it."""
    print(f"\n{question}")
    audio = client.text_to_speech.convert(
        text=question,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    play_audio(audio)
    return ActionResult(extracted_content=stop_recording())

@controller.action("Receive feedback")
def receive_feedback(feedback: str) -> ActionResult:
    """Receives feedback from the user and plays it as speech."""
    print(f"\nFeedback: {feedback}")
    audio = client.text_to_speech.convert(
        text=feedback,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    play_audio(audio)
    return ActionResult()

# Gradio UI
with gr.Blocks() as app:
    gr.Markdown("# 🗣️ Voice-Powered AI Dashboard")
    
    with gr.Row():
        record_btn = gr.Button("🎤 Start Recording")
        stop_btn = gr.Button("🛑 Stop Recording")
    
    transcribed_text = gr.Textbox(label="Transcribed Text")
    generate_btn = gr.Button("🚀 Send to AI Agent")
    agent_response = gr.Textbox(label="Agent Response")
    play_audio_btn = gr.Button("🔊 Play Response")
    
    record_btn.click(start_recording, outputs=transcribed_text)
    stop_btn.click(stop_recording, outputs=transcribed_text)
    generate_btn.click(lambda user_input: ask_human(user_input).extracted_content, inputs=transcribed_text, outputs=agent_response)
    play_audio_btn.click(lambda response_text: receive_feedback(response_text), inputs=agent_response)

app.launch()
