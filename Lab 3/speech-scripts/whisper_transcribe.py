#!/usr/bin/env python3
"""
Live transcription using OpenAI Whisper with microphone input.
Requires: pip install openai-whisper sounddevice numpy scipy
"""

import argparse
import queue
import sys
import threading
import numpy as np
import sounddevice as sd
import whisper
import warnings
import time
from scipy.io.wavfile import write
import tempfile
import os

# Suppress warnings
warnings.filterwarnings("ignore")

class WhisperLiveTranscriber:
    def __init__(self, model_size="tiny", sample_rate=16000, chunk_duration=5.0, 
                 overlap_duration=0.5, energy_threshold=0.01, device=None):
        """
        Initialize the live transcriber.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            sample_rate: Audio sample rate (16000 recommended for Whisper)
            chunk_duration: Duration of audio chunks to transcribe (seconds)
            overlap_duration: Overlap between chunks to avoid cutting words (seconds)
            energy_threshold: Minimum energy to trigger transcription
            device: Audio input device (None for default)
        """
        print(f"Loading Whisper model '{model_size}'...")
        self.model = whisper.load_model(model_size)
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.energy_threshold = energy_threshold
        self.device = device
        
        # Calculate buffer sizes
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.overlap_samples = int(sample_rate * overlap_duration)
        
        # Audio buffer
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        
        # Queue for audio data
        self.audio_queue = queue.Queue()
        
        # Transcription state
        self.is_running = False
        self.last_transcription = ""
        
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio stream."""
        if status:
            print(f"Audio callback status: {status}", file=sys.stderr)
        
        # Convert to float32 and put in queue
        audio_data = indata[:, 0].astype(np.float32)
        self.audio_queue.put(audio_data)
    
    def process_audio_queue(self):
        """Process audio from queue and add to buffer."""
        while self.is_running:
            try:
                # Get audio data with timeout
                audio_data = self.audio_queue.get(timeout=0.1)
                
                with self.buffer_lock:
                    # Add to buffer
                    self.audio_buffer = np.concatenate([self.audio_buffer, audio_data])
                    
                    # Keep buffer size manageable (max 30 seconds)
                    max_samples = int(self.sample_rate * 30)
                    if len(self.audio_buffer) > max_samples:
                        self.audio_buffer = self.audio_buffer[-max_samples:]
                        
            except queue.Empty:
                continue
    
    def transcription_worker(self):
        """Worker thread for transcription."""
        print("Transcription worker started...")
        
        while self.is_running:
            with self.buffer_lock:
                # Check if we have enough audio
                if len(self.audio_buffer) < self.chunk_samples:
                    time.sleep(0.1)
                    continue
                
                # Get chunk with overlap from previous
                if len(self.audio_buffer) >= self.chunk_samples:
                    audio_chunk = self.audio_buffer[:self.chunk_samples].copy()
                    
                    # Remove processed audio (keeping overlap)
                    self.audio_buffer = self.audio_buffer[self.chunk_samples - self.overlap_samples:]
                else:
                    time.sleep(0.1)
                    continue
            
            # Check if audio has sufficient energy
            energy = np.sqrt(np.mean(audio_chunk**2))
            if energy < self.energy_threshold:
                continue
            
            # Transcribe the chunk
            try:
                # Use a temporary file for audio
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    # Convert to int16 for WAV file
                    audio_int16 = (audio_chunk * 32767).astype(np.int16)
                    write(tmp_file.name, self.sample_rate, audio_int16)
                    
                    # Transcribe
                    result = self.model.transcribe(
                        tmp_file.name, 
                        language="en",  # Change as needed
                        fp16=False,
                        verbose=False
                    )
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
                
                # Get transcription text
                text = result["text"].strip()
                
                # Only print if there's new content
                if text and text != self.last_transcription:
                    print(f"\r\033[K[Transcribed]: {text}")
                    self.last_transcription = text
                    
            except Exception as e:
                print(f"Transcription error: {e}", file=sys.stderr)
    
    def start(self):
        """Start live transcription."""
        print("=" * 80)
        print("Starting live transcription...")
        print(f"Model: {self.model.dims.n_text_layer} layers")
        print(f"Sample rate: {self.sample_rate} Hz")
        print(f"Chunk duration: {self.chunk_duration} seconds")
        print(f"Device: {self.device if self.device else 'Default'}")
        print("=" * 80)
        print("Press Ctrl+C to stop")
        print("-" * 80)
        
        self.is_running = True
        
        # Start worker threads
        queue_thread = threading.Thread(target=self.process_audio_queue, daemon=True)
        queue_thread.start()
        
        transcription_thread = threading.Thread(target=self.transcription_worker, daemon=True)
        transcription_thread.start()
        
        # Start audio stream
        try:
            with sd.InputStream(
                device=self.device,
                channels=1,
                samplerate=self.sample_rate,
                callback=self.audio_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
            ):
                # Keep main thread alive
                while self.is_running:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\n\nStopping transcription...")
            self.stop()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            self.stop()
    
    def stop(self):
        """Stop transcription."""
        self.is_running = False
        print("Transcription stopped.")


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


def main():
    parser = argparse.ArgumentParser(description="Live transcription using Whisper")
    
    parser.add_argument(
        "-l", "--list-devices", action="store_true",
        help="Show list of audio devices and exit"
    )
    parser.add_argument(
        "-d", "--device", type=int_or_str,
        help="Input device (numeric ID or substring)"
    )
    parser.add_argument(
        "-m", "--model", type=str, default="tiny",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: tiny)"
    )
    parser.add_argument(
        "-r", "--samplerate", type=int, default=16000,
        help="Sampling rate (default: 16000, recommended for Whisper)"
    )
    parser.add_argument(
        "-c", "--chunk", type=float, default=5.0,
        help="Chunk duration in seconds (default: 5.0)"
    )
    parser.add_argument(
        "-o", "--overlap", type=float, default=0.5,
        help="Overlap duration in seconds (default: 0.5)"
    )
    parser.add_argument(
        "-e", "--energy", type=float, default=0.01,
        help="Energy threshold for voice activity (default: 0.01)"
    )
    
    args = parser.parse_args()
    
    # List devices if requested
    if args.list_devices:
        print(sd.query_devices())
        sys.exit(0)
    
    # Create and start transcriber
    transcriber = WhisperLiveTranscriber(
        model_size=args.model,
        sample_rate=args.samplerate,
        chunk_duration=args.chunk,
        overlap_duration=args.overlap,
        energy_threshold=args.energy,
        device=args.device
    )
    
    transcriber.start()


if __name__ == "__main__":
    main()