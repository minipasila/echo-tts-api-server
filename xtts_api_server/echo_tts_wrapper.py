# echo_tts_wrapper.py

import torch
import torchaudio
from functools import partial
from pathlib import Path
from loguru import logger
from datetime import datetime
import os
import time
import re
import json
import socket
import io
import wave
import numpy as np

# Echo TTS imports
try:
    from inference import (
        load_model_from_hf,
        load_fish_ae_from_hf,
        load_pca_state_from_hf,
        load_audio,
        sample_pipeline,
        sample_euler_cfg_independent_guidances,
    )
    ECHO_AVAILABLE = True
except ImportError:
    logger.warning("Echo TTS inference module not available. Please install Echo TTS.")
    ECHO_AVAILABLE = False

# Class to check tts settings
class InvalidSettingsError(Exception):
    pass

# List of supported language codes (Echo TTS primarily supports English)
# We keep the same list for API compatibility but will warn for non-English
supported_languages = {
    "ar":"Arabic",
    "pt":"Brazilian Portuguese",
    "zh-cn":"Chinese",
    "cs":"Czech",
    "nl":"Dutch",
    "en":"English",
    "et":"Estonian",
    "fi":"Finnish",
    "fr":"French",
    "de":"German",
    "it":"Italian",
    "pl":"Polish",
    "ru":"Russian",
    "es":"Spanish",
    "tr":"Turkish",
    "ja":"Japanese",
    "ko":"Korean",
    "hu":"Hungarian",
    "hi":"Hindi"
}

# Echo TTS default settings
default_echo_tts_settings = {
    "num_steps": 40,
    "cfg_scale_text": 3.0,
    "cfg_scale_speaker": 8.0,
    "cfg_min_t": 0.5,
    "cfg_max_t": 1.0,
    "truncation_factor": 0.8,
    "rescale_k": 1.2,
    "rescale_sigma": 3.0,
    "sequence_length": 640,  # ~30 seconds
    "speaker_kv_scale": None,
    "speaker_kv_max_layers": None,
    "speaker_kv_min_t": None,
}

# XTTS settings for compatibility (will be mapped to Echo TTS)
default_tts_settings = {
    "temperature" : 0.75,
    "length_penalty" : 1.0,
    "repetition_penalty": 5.0,
    "top_k" : 50,
    "top_p" : 0.85,
    "speed" : 1,
    "enable_text_splitting": True
}

reversed_supported_languages = {name: code for code, name in supported_languages.items()}

class EchoTTSWrapper:
    def __init__(self, output_folder="./output", speaker_folder="./speakers", 
                 model_folder="./models", lowvram=False, model_source="local",
                 model_version="base", device="cuda", deepspeed=False, 
                 enable_cache_results=True):
        
        self.cuda = device
        self.device = 'cpu' if lowvram else (self.cuda if torch.cuda.is_available() else "cpu")
        self.lowvram = lowvram
        
        self.model_source = model_source
        self.model_version = model_version
        self.tts_settings = default_tts_settings
        self.echo_settings = default_echo_tts_settings.copy()
        self.stream_chunk_size = 100
        
        self.deepspeed = deepspeed  # Not used by Echo TTS but kept for compatibility
        
        self.speaker_folder = speaker_folder
        self.output_folder = output_folder
        self.model_folder = model_folder
        
        # Echo TTS model components
        self.model = None
        self.fish_ae = None
        self.pca_state = None
        
        self.create_directories()
        
        self.enable_cache_results = enable_cache_results
        self.cache_file_path = os.path.join(output_folder, "cache.json")
        
        if self.enable_cache_results:
            with open(self.cache_file_path, 'w') as cache_file:
                json.dump({}, cache_file)
    
    def create_directories(self):
        directories = [self.output_folder, self.speaker_folder, self.model_folder]
        
        for sanctuary in directories:
            absolute_path = os.path.abspath(os.path.normpath(sanctuary))
            
            if not os.path.exists(absolute_path):
                os.makedirs(absolute_path)
                logger.info(f"Folder in the path {absolute_path} has been created")
    
    def load_model(self, load=True):
        """Load Echo TTS model from HuggingFace"""
        if not ECHO_AVAILABLE:
            raise ImportError("Echo TTS is not available. Please install the required dependencies.")
        
        logger.info("Loading Echo TTS model from HuggingFace...")
        logger.info("This may take 1-2 minutes on first run (models will be cached).")
        
        try:
            # Load Echo TTS model components
            self.model = load_model_from_hf(delete_blockwise_modules=True)
            self.fish_ae = load_fish_ae_from_hf()
            self.pca_state = load_pca_state_from_hf()
            
            # Move to device safely
            # load_model_from_hf often handles device placement automatically
            try:
                # Check if model is already on the correct device or if it's a meta tensor
                current_device = next(self.model.parameters()).device
                if current_device.type != 'meta' and str(current_device) != str(self.device):
                    logger.info(f"Moving model from {current_device} to {self.device}...")
                    self.model = self.model.to(self.device)
                else:
                    logger.info(f"Model already on {current_device}, skipping .to()")
            except Exception as e:
                logger.warning(f"Could not move model to {self.device}: {e}")

            try:
                current_ae_device = next(self.fish_ae.parameters()).device
                if current_ae_device.type != 'meta' and str(current_ae_device) != str(self.device):
                    logger.info(f"Moving Fish AE from {current_ae_device} to {self.device}...")
                    self.fish_ae = self.fish_ae.to(self.device)
                else:
                    logger.info(f"Fish AE already on {current_ae_device}, skipping .to()")
            except Exception as e:
                logger.warning(f"Could not move Fish AE to {self.device}: {e}")
            
            logger.info("Echo TTS model loaded successfully!")
            logger.info(f"Model device: {self.device}")
            logger.info(f"Model version: {self.model_version}")
            
        except Exception as e:
            logger.error(f"Failed to load Echo TTS model: {e}")
            raise
    
    def switch_model(self, model_name):
        """Switch model (not applicable for Echo TTS, kept for compatibility)"""
        logger.warning("Echo TTS does not support model switching. Using current model.")
        pass
    
    def get_models_list(self):
        """Get available models (Echo TTS has one model)"""
        return ["base"]
    
    def get_wav_header(self, channels: int = 1, sample_rate: int = 44100, width: int = 2) -> bytes:
        """Get WAV header for streaming"""
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(width)
            out.setframerate(sample_rate)
            out.writeframes(b"")
        wav_buf.seek(0)
        return wav_buf.read()
    
    def map_xtts_to_echo_settings(self):
        """Map XTTS settings to Echo TTS settings"""
        # Map temperature to cfg_scale_text
        # Higher temperature (more random) -> lower cfg_scale_text
        temp = self.tts_settings.get('temperature', 0.75)
        self.echo_settings['cfg_scale_text'] = 3.0 * (1.0 - temp * 0.5)
        
        # Map top_p to cfg_scale_speaker
        top_p = self.tts_settings.get('top_p', 0.85)
        self.echo_settings['cfg_scale_speaker'] = 8.0 * top_p
        
        # Map top_k to num_steps
        top_k = self.tts_settings.get('top_k', 50)
        self.echo_settings['num_steps'] = int(20 + top_k * 0.4)
        
        # Map length_penalty to truncation_factor
        length_penalty = self.tts_settings.get('length_penalty', 1.0)
        self.echo_settings['truncation_factor'] = 0.8 * length_penalty
        
        # Map repetition_penalty to rescale_k
        rep_penalty = self.tts_settings.get('repetition_penalty', 5.0)
        self.echo_settings['rescale_k'] = 1.2 * (rep_penalty / 5.0)
        
        # Map speed to sequence_length (affects generation length)
        speed = self.tts_settings.get('speed', 1.0)
        # Higher speed -> shorter sequence
        self.echo_settings['sequence_length'] = int(640 / speed)
        # Clamp to valid range
        self.echo_settings['sequence_length'] = max(160, min(640, self.echo_settings['sequence_length']))
    
    def clean_text(self, text):
        """Clean and prepare text for Echo TTS"""
        # Remove asterisks and line breaks (keep for compatibility with XTTS)
        text = re.sub(r'[*\r\n]', '', text)
        # Replace double quotes with single quotes
        text = re.sub(r'"\s?(.*?)\s?"', r"'\1'", text)
        
        # Echo TTS requires [S1] prefix for speaker diarization
        if not text.startswith('[S1]'):
            text = '[S1] ' + text
        
        return text
    
    def load_speaker_audio(self, speaker_wav):
        """Load and process speaker reference audio for Echo TTS"""
        if not ECHO_AVAILABLE:
            raise ImportError("Echo TTS is not available.")
        
        try:
            if isinstance(speaker_wav, list):
                # Concatenate multiple audio files
                audio_segments = []
                for wav_path in speaker_wav:
                    audio = load_audio(wav_path)
                    audio_segments.append(audio)
                speaker_audio = torch.cat(audio_segments, dim=-1)
            else:
                speaker_audio = load_audio(speaker_wav)
            
            # Move to device
            speaker_audio = speaker_audio.to(self.device)
            
            return speaker_audio
            
        except Exception as e:
            logger.error(f"Failed to load speaker audio: {e}")
            raise ValueError(f"Failed to load speaker audio: {str(e)}")
    
    def get_speaker_wav(self, speaker_name_or_path):
        """Get the speaker_wav(s) for a given speaker name or path"""
        if speaker_name_or_path.endswith('.wav'):
            # it's a file name
            if os.path.isabs(speaker_name_or_path):
                # absolute path; nothing to do
                speaker_wav = speaker_name_or_path
            else:
                # make it a full path
                speaker_wav = os.path.join(self.speaker_folder, speaker_name_or_path)
        else:
            # it's a speaker name
            full_path = os.path.join(self.speaker_folder, speaker_name_or_path)
            wav_file = f"{full_path}.wav"
            if os.path.isdir(full_path):
                # multi-sample speaker
                speaker_wav = [os.path.join(full_path, wav) for wav in self.get_wav_files(full_path)]
                if len(speaker_wav) == 0:
                    raise ValueError(f"no wav files found in {full_path}")
            elif os.path.isfile(wav_file):
                speaker_wav = wav_file
            else:
                raise ValueError(f"Speaker {speaker_name_or_path} not found.")
        
        return speaker_wav
    
    def get_wav_files(self, directory):
        """Find all wav files in a directory"""
        wav_files = [f for f in os.listdir(directory) if f.endswith('.wav')]
        return wav_files
    
    def check_cache(self, text_params):
        """Check if result is cached"""
        if not self.enable_cache_results:
            return None
        
        try:
            with open(self.cache_file_path) as cache_file:
                cache_data = json.load(cache_file)
            
            for entry in cache_data.values():
                if all(entry[key] == value for key, value in text_params.items()):
                    return entry['file_name']
            
            return None
        
        except FileNotFoundError:
            return None
    
    def update_cache(self, text_params, file_name):
        """Update cache with new result"""
        if not self.enable_cache_results:
            return None
        
        try:
            if os.path.exists(self.cache_file_path) and os.path.getsize(self.cache_file_path) > 0:
                with open(self.cache_file_path, 'r') as cache_file:
                    cache_data = json.load(cache_file)
            else:
                cache_data = {}
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cache_data[timestamp] = {**text_params, 'file_name': file_name}
            
            with open(self.cache_file_path, 'w') as cache_file:
                json.dump(cache_data, cache_file)
            
            logger.info("Cache updated successfully.")
        except IOError as e:
            logger.error(f"I/O error occurred while updating the cache: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error occurred while updating the cache: {str(e)}")
    
    def set_speaker_folder(self, folder):
        """Set speaker folder"""
        if os.path.exists(folder) and os.path.isdir(folder):
            self.speaker_folder = folder
            self.create_directories()
            logger.info(f"Speaker folder is set to {folder}")
        else:
            raise ValueError("Provided path is not a valid directory")
    
    def set_out_folder(self, folder):
        """Set output folder"""
        if os.path.exists(folder) and os.path.isdir(folder):
            self.output_folder = folder
            self.create_directories()
            logger.info(f"Output folder is set to {folder}")
        else:
            raise ValueError("Provided path is not a valid directory")
    
    def set_tts_settings(self, temperature, speed, length_penalty,
                         repetition_penalty, top_p, top_k, enable_text_splitting, stream_chunk_size):
        """Set TTS settings (XTTS compatibility)"""
        # Validate each parameter
        if not (0.01 <= temperature <= 1):
            raise InvalidSettingsError("Temperature must be between 0.01 and 1.")
        
        if not (0.2 <= speed <= 2):
            raise InvalidSettingsError("Speed must be between 0.2 and 2.")
        
        if not isinstance(length_penalty, float):
            raise InvalidSettingsError("Length penalty must be a floating point number.")
        
        if not (0.1 <= repetition_penalty <= 10.0):
            raise InvalidSettingsError("Repetition penalty must be between 0.1 and 10.0.")
        
        if not (0.01 <= top_p <= 1):
            raise InvalidSettingsError("Top_p must be between 0.01 and 1 and must be a float.")
        
        if not (1 <= top_k <= 100):
            raise InvalidSettingsError("Top_k must be an integer between 1 and 100.")
        
        if not (20 <= stream_chunk_size <= 400):
            raise InvalidSettingsError("Stream chunk size must be an integer between 20 and 400.")
        
        if not isinstance(enable_text_splitting, bool):
            raise InvalidSettingsError("Enable text splitting must be either True or False.")
        
        # Apply settings
        self.tts_settings = {
            "temperature": temperature,
            "speed": speed,
            "length_penalty": length_penalty,
            "repetition_penalty": repetition_penalty,
            "top_p": top_p,
            "top_k": top_k,
            "enable_text_splitting": enable_text_splitting,
        }
        
        self.stream_chunk_size = stream_chunk_size
        
        # Map to Echo TTS settings
        self.map_xtts_to_echo_settings()
        
        logger.info("Successfully updated TTS settings.")
        logger.info(f"Mapped Echo TTS settings: {self.echo_settings}")
    
    def _get_speakers(self):
        """Get info on all speakers"""
        speakers = []
        for f in os.listdir(self.speaker_folder):
            full_path = os.path.join(self.speaker_folder, f)
            if os.path.isdir(full_path):
                # multi-sample voice
                subdir_files = self.get_wav_files(full_path)
                if len(subdir_files) == 0:
                    continue
                
                speaker_name = f
                speaker_wav = [os.path.join(self.speaker_folder, f, s) for s in subdir_files]
                preview = os.path.join(f, subdir_files[0])
                speakers.append({
                    'speaker_name': speaker_name,
                    'speaker_wav': speaker_wav,
                    'preview': preview
                })
            
            elif f.endswith('.wav'):
                speaker_name = os.path.splitext(f)[0]
                speaker_wav = full_path
                preview = f
                speakers.append({
                    'speaker_name': speaker_name,
                    'speaker_wav': speaker_wav,
                    'preview': preview
                })
        return speakers
    
    def get_speakers(self):
        """Get available speakers"""
        speakers = [s['speaker_name'] for s in self._get_speakers()]
        return speakers
    
    def get_speakers_special(self):
        """Get speakers in special format for SillyTavern"""
        BASE_URL = os.getenv('BASE_URL', '127.0.0.1:8020')
        BASE_HOST = os.getenv('BASE_HOST', '127.0.0.1')
        BASE_PORT = os.getenv('BASE_PORT', '8020')
        TUNNEL_URL = os.getenv('TUNNEL_URL', '')
        
        is_local_host = BASE_HOST == '127.0.0.1' or BASE_HOST == "localhost"
        
        if TUNNEL_URL == "" and not is_local_host:
            TUNNEL_URL = f"http://{self.get_local_ip()}:{BASE_PORT}"
        
        speakers_special = []
        speakers = self._get_speakers()
        
        for speaker in speakers:
            if TUNNEL_URL == "":
                preview_url = f"{BASE_URL}/sample/{speaker['preview']}"
            else:
                preview_url = f"{TUNNEL_URL}/sample/{speaker['preview']}"
            
            speaker_special = {
                'name': speaker['speaker_name'],
                'voice_id': speaker['speaker_name'],
                'preview_url': preview_url
            }
            speakers_special.append(speaker_special)
        
        return speakers_special
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('10.255.255.255', 1))
                IP = s.getsockname()[0]
        except Exception as e:
            logger.error(f"Failed to obtain a local IP: {e}")
            return None
        return IP
    
    def list_languages(self):
        """List supported languages"""
        return reversed_supported_languages
    
    def local_generation(self, text, speaker_name, speaker_wav, language, output_file):
        """Generate audio using Echo TTS"""
        if not ECHO_AVAILABLE:
            raise ImportError("Echo TTS is not available.")
        
        generate_start_time = time.time()
        
        # Warn about non-English languages
        if language.lower() != 'en':
            logger.warning(f"Echo TTS primarily supports English. Requested language: {language}")
        
        # Load speaker audio
        speaker_audio = self.load_speaker_audio(speaker_wav)
        
        # Configure sampler
        sample_fn = partial(
            sample_euler_cfg_independent_guidances,
            num_steps=self.echo_settings['num_steps'],
            cfg_scale_text=self.echo_settings['cfg_scale_text'],
            cfg_scale_speaker=self.echo_settings['cfg_scale_speaker'],
            cfg_min_t=self.echo_settings['cfg_min_t'],
            cfg_max_t=self.echo_settings['cfg_max_t'],
            truncation_factor=self.echo_settings['truncation_factor'],
            rescale_k=self.echo_settings['rescale_k'],
            rescale_sigma=self.echo_settings['rescale_sigma'],
            speaker_kv_scale=self.echo_settings['speaker_kv_scale'],
            speaker_kv_max_layers=self.echo_settings['speaker_kv_max_layers'],
            speaker_kv_min_t=self.echo_settings['speaker_kv_min_t'],
            sequence_length=self.echo_settings['sequence_length'],
        )
        
            # Generate
        try:
            audio_out, _ = sample_pipeline(
                model=self.model,
                fish_ae=self.fish_ae,
                pca_state=self.pca_state,
                sample_fn=sample_fn,
                text_prompt=text,
                speaker_audio=speaker_audio,
                rng_seed=0,
            )
            
            # Save at 44.1kHz (Echo TTS native sample rate)
            torchaudio.save(output_file, audio_out[0].cpu(), 44100)
            
            generate_end_time = time.time()
            generate_elapsed_time = generate_end_time - generate_start_time
            
            logger.info(f"Processing time: {generate_elapsed_time:.2f} seconds.")
            
        except torch.cuda.OutOfMemoryError:
            logger.error("CUDA out of memory. Echo TTS requires at least 8GB VRAM.")
            raise
        except Exception as e:
            logger.error(f"Echo TTS generation failed: {e}")
            raise
    
    async def stream_generation(self, text, speaker_name, speaker_wav, language, output_file):
        """Stream audio generation using Echo TTS (experimental)"""
        if not ECHO_AVAILABLE:
            raise ImportError("Echo TTS is not available.")
        
        logger.warning("Streaming mode with Echo TTS is experimental and may not work reliably.")
        
        generate_start_time = time.time()
        
        # Warn about non-English languages
        if language.lower() != 'en':
            logger.warning(f"Echo TTS primarily supports English. Requested language: {language}")
        
        # Load speaker audio
        speaker_audio = self.load_speaker_audio(speaker_wav)
        
        # For streaming, we'll generate the full audio and stream it in chunks
        # This is not true streaming but provides compatibility
        try:
            # Configure sampler
            sample_fn = partial(
                sample_euler_cfg_independent_guidances,
                num_steps=self.echo_settings['num_steps'],
                cfg_scale_text=self.echo_settings['cfg_scale_text'],
                cfg_scale_speaker=self.echo_settings['cfg_scale_speaker'],
                cfg_min_t=self.echo_settings['cfg_min_t'],
                cfg_max_t=self.echo_settings['cfg_max_t'],
                truncation_factor=self.echo_settings['truncation_factor'],
                rescale_k=self.echo_settings['rescale_k'],
                rescale_sigma=self.echo_settings['rescale_sigma'],
                sequence_length=self.echo_settings['sequence_length'],
            )
            
            # Generate full audio
            audio_out, _ = sample_pipeline(
                model=self.model,
                fish_ae=self.fish_ae,
                pca_state=self.pca_state,
                sample_fn=sample_fn,
                text_prompt=text,
                speaker_audio=speaker_audio,
                rng_seed=0,
            )
            
            # Save for caching at 44.1kHz
            torchaudio.save(output_file, audio_out[0].cpu(), 44100)
            
            # Stream in chunks
            audio_numpy = audio_out[0].cpu().numpy()
            chunk_size = self.stream_chunk_size * 44100 // 1000  # Convert ms to samples (44.1kHz)
            
            for i in range(0, len(audio_numpy), chunk_size):
                chunk = audio_numpy[i:i + chunk_size]
                chunk = chunk[None, : len(chunk)]
                chunk = np.clip(chunk, -1, 1)
                chunk = (chunk * 32767).astype(np.int16)
                yield chunk.tobytes()
            
            generate_end_time = time.time()
            generate_elapsed_time = generate_end_time - generate_start_time
            
            logger.info(f"Processing time: {generate_elapsed_time:.2f} seconds.")
            
        except torch.cuda.OutOfMemoryError:
            logger.error("CUDA out of memory. Echo TTS requires at least 8GB VRAM.")
            raise
        except Exception as e:
            logger.error(f"Echo TTS streaming failed: {e}")
            raise
    
    def process_tts_to_file(self, text, speaker_name_or_path, language, 
                           file_name_or_path="out.wav", stream=False):
        """Main TTS processing function"""
        try:
            speaker_wav = self.get_speaker_wav(speaker_name_or_path)
            
            # Determine output path
            if os.path.isabs(file_name_or_path):
                output_file = file_name_or_path
            else:
                output_file = os.path.join(self.output_folder, file_name_or_path)
            
            # Check if text is a file path
            if os.path.isfile(text) and text.lower().endswith('.txt'):
                with open(text, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            # Generate unique name for cached result
            if self.enable_cache_results:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                file_name_or_path = timestamp + "_cache_" + file_name_or_path
                output_file = os.path.join(self.output_folder, file_name_or_path)
            
            # Clean text
            clear_text = self.clean_text(text)
            
            # Generate cache parameters
            text_params = {
                'text': clear_text,
                'speaker_name_or_path': speaker_name_or_path,
                'language': language
            }
            
            # Check cache
            cached_result = self.check_cache(text_params)
            
            if cached_result is not None:
                logger.info("Using cached result.")
                return cached_result
            
            # Map settings
            self.map_xtts_to_echo_settings()
            
            # Generate
            if stream:
                async def stream_fn():
                    async for chunk in self.stream_generation(
                        clear_text, speaker_name_or_path, speaker_wav, language, output_file
                    ):
                        yield chunk
                    self.update_cache(text_params, output_file)
                return stream_fn()
            else:
                self.local_generation(clear_text, speaker_name_or_path, speaker_wav, language, output_file)
            
            # Update cache
            self.update_cache(text_params, output_file)
            return output_file
        
        except Exception as e:
            logger.error(f"TTS processing failed: {e}")
            raise
