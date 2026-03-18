# Echo TTS API Server

This project is a FastAPI server for [Echo TTS](https://github.com/jordandare/echo-tts), a diffusion-based text-to-speech model with fast, high-fidelity voice cloning.

This server was created for [SillyTavern](https://github.com/SillyTavern/SillyTavern) but you can use it for your needs.

Feel free to make PRs or use code for your own needs.

## About Echo TTS

Echo TTS is a 2.4B parameter diffusion model that:
- Generates high-quality 44.1kHz audio
- Supports voice cloning using reference audio (up to 5 minutes)
- Generates up to 30 seconds of audio per request
- Requires 8GB+ VRAM for GPU inference
- Is primarily optimized for English (limited multilingual support)

**Model:** [jordand/echo-tts-base](https://huggingface.co/jordand/echo-tts-base) | **Demo:** [echo-tts-preview](https://huggingface.co/spaces/jordand/echo-tts-preview)

**Blog Post:** [Echo - Diffusion-based text-to-speech with fast, high-fidelity voice cloning](https://jordandarefsky.com/blog/2025/echo/)

## Changelog

You can keep track of all changes on [release page](https://github.com/minipasila/echo-tts-api-server/releases)

## TODO
- [x] Migrate from XTTS to Echo TTS
- [ ] Add proper multilingual support when Echo TTS expands
- [ ] Implement true streaming with blockwise generation

## Installation

### Prerequisites

- Python 3.10+
- CUDA-capable GPU with at least 8GB VRAM
- FFmpeg (for audio processing)

### Simple Installation

```bash
pip install -r requirements.txt
```

This will install all necessary dependencies, including PyTorch and Echo TTS dependencies.

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install torch>=2.9.1 torchaudio>=2.9.1 --index-url https://download.pytorch.org/whl/cu121
```

### Linux

```bash
sudo apt install -y python3-dev python3-venv portaudio19-dev ffmpeg
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install torch>=2.9.1 torchaudio>=2.9.1 --index-url https://download.pytorch.org/whl/cu121
```

### Manual Installation

```bash
# Clone REPO
git clone https://github.com/minipasila/echo-tts-api-server
cd echo-tts-api-server
# Create virtual env
python -m venv venv
venv/scripts/activate  # or source venv/bin/activate on Linux
# Install deps
pip install -r requirements.txt
# Launch server
python -m xtts_api_server
```

## Starting Server

`python -m xtts_api_server` will run on default ip and port (localhost:8020)

```
usage: xtts_api_server [-h] [-hs HOST] [-p PORT] [-sf SPEAKER_FOLDER] [-o OUTPUT] [-t TUNNEL_URL] [--listen] [--use-cache] [--lowvram] [--streaming-mode]

Run Echo TTS within a FastAPI application

options:
  -h, --help            show this help message and exit
  -hs HOST, --host HOST
  -p PORT, --port PORT
  -d DEVICE, --device DEVICE
                        `cpu` or `cuda`, you can specify which video card to use, for example, `cuda:0`
  -sf SPEAKER_FOLDER, --speaker-folder
                        The folder where you get samples for tts
  -o OUTPUT, --output   Output folder
  -mf MODELS_FOLDERS, --model-folder
                        Folder where models will be stored (Echo TTS models are cached from HuggingFace)
  -t TUNNEL_URL, --tunnel
                        URL of tunnel used (e.g: ngrok, localtunnel)
  --listen               Allows server to be used outside of local computer, similar to -hs 0.0.0.0
  --use-cache            Enables caching of results, your results will be saved and if there will be a repeated request, you will get a file instead of generation
  --lowvram              The mode in which model will be stored in RAM and when processing will move to VRAM (not recommended for Echo TTS)
  --streaming-mode       Enables streaming mode (experimental with Echo TTS)
```

## Model Loading

The first time you run the server, Echo TTS models will be automatically downloaded from HuggingFace:
- Echo Model (~4.8GB)
- Fish Speech S1-DAC Autoencoder (~500MB)
- PCA State (~50MB)

This may take 1-2 minutes depending on your internet connection. Models are cached locally for subsequent runs.

## About Streaming Mode

Streaming mode with Echo TTS is **experimental**. The current implementation generates the full audio first, then streams it in chunks. True streaming with blockwise generation is planned for future updates.

**Limitations:**
1. Not true streaming (generates full audio first)
2. May have higher latency than non-streaming mode
3. Works best with shorter texts (< 30 seconds)

For best results, use non-streaming mode.

## API Documentation

API Docs can be accessed from [http://localhost:8020/docs](http://localhost:8020/docs)

### Endpoints

All endpoints maintain compatibility with the original XTTS API server:

- `GET /speakers_list` - Get list of available speakers
- `GET /speakers` - Get speakers with preview URLs (SillyTavern format)
- `GET /languages` - Get supported languages
- `GET /get_folders` - Get current folder paths
- `GET /get_models_list` - Get available models
- `GET /get_tts_settings` - Get current TTS settings
- `GET /sample/{file_name}` - Get speaker sample audio
- `POST /set_output` - Set output folder
- `POST /set_speaker_folder` - Set speaker folder
- `POST /switch_model` - Switch model (not applicable for Echo TTS)
- `POST /set_tts_settings` - Update TTS generation parameters
- `GET /tts_stream` - Stream audio generation (experimental)
- `POST /tts_to_audio` - Generate audio and return file
- `POST /tts_to_file` - Generate audio and save to file

### TTS Settings

The following parameters can be set via `/set_tts_settings`:

| Parameter | Range | Description | Echo TTS Mapping |
|-----------|--------|-------------|-----------------|
| temperature | 0.01 - 1.0 | Randomness/creativity | cfg_scale_text |
| speed | 0.2 - 2.0 | Speaking speed | sequence_length |
| length_penalty | float | Output length control | truncation_factor |
| repetition_penalty | 0.1 - 10.0 | Reduce repetition | rescale_k |
| top_p | 0.01 - 1.0 | Nucleus sampling | cfg_scale_speaker |
| top_k | 1 - 100 | Top-k sampling | num_steps |
| enable_text_splitting | bool | Split long texts | N/A |
| stream_chunk_size | 20 - 400 | Streaming chunk size (ms) | N/A |

## How to Add Speakers

By default, a `speakers` folder should appear in the project directory. You need to put WAV files with voice samples there. You can also create a folder and put several voice samples in it for more accurate results.

### Speaker Audio Requirements

For best voice cloning results with Echo TTS:

1. **Duration:** 7-10 seconds is ideal (up to 5 minutes supported)
2. **Format:** WAV file, any sample rate (will be resampled to 44.1kHz)
3. **Quality:** Clean audio without background noise or music
4. **Content:** Natural flowing speech with vocal range
5. **Avoid:** Breath sounds at start/end, long pauses, gaps

Example:
```
speakers/
├── male.wav
├── female.wav
└── calm_female/
    ├── sample1.wav
    ├── sample2.wav
    └── sample3.wav
```

## Selecting Folders

You can change the folders for speakers and output via the API:

```bash
curl -X POST "http://localhost:8020/set_speaker_folder" \
  -H "Content-Type: application/json" \
  -d '{"speaker_folder": "/path/to/speakers"}'

curl -X POST "http://localhost:8020/set_output" \
  -H "Content-Type: application/json" \
  -d '{"output_folder": "/path/to/output"}'
```

## Language Support

Echo TTS is primarily optimized for **English**. While the API accepts all language codes for compatibility, non-English text may produce lower quality results.

Supported language codes (for API compatibility):
- `en` - English (best quality)
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `pl` - Polish
- `ru` - Russian
- `nl` - Dutch
- `cs` - Czech
- `ar` - Arabic
- `zh-cn` - Chinese
- `ja` - Japanese
- `ko` - Korean
- `hu` - Hungarian
- `hi` - Hindi
- `tr` - Turkish

**Note:** For non-English languages, the model will attempt to generate speech but quality may vary.

## Performance

### Generation Speed
- **10 seconds of text:** ~0.5 seconds on A100
- **30 seconds of text:** ~1.5 seconds on A100
- **RTF (Real-Time Factor):** < 0.05 on A100

### Memory Requirements
- **VRAM:** 8GB+ recommended (5.35GB total)
  - Echo Model: ~4.8GB
  - Fish AE: ~500MB
  - Speaker Audio: ~50MB
- **RAM:** 16GB+ recommended

### Audio Quality
- **Sample Rate:** 44.1kHz (high quality)
- **Max Duration:** 30 seconds per request

## Responsible Use

Don't use this model to:
- Impersonate real people without their consent
- Generate deceptive audio (e.g., fraud, misinformation, deepfakes)

You are responsible for complying with local laws regarding biometric data and voice cloning.

## Credit

1. **Echo TTS** by [Jordan Darefsky](https://jordandarefsky.com/) - The underlying TTS model
2. **Original XTTS API Server** by [daswer123](https://github.com/daswer123/xtts-api-server) - Server architecture and API design
3. **RealtimeTTS** by [Kolja Beigel](https://github.com/KoljaB/RealtimeTTS) - Streaming code inspiration
4. **Fish Speech** - S1-DAC autoencoder for audio encoding/decoding

## License

Code in this repo is MIT-licensed except where file headers specify otherwise.

Echo TTS model weights are licensed under CC-BY-NC-SA-4.0.

Audio outputs are CC-BY-NC-SA-4.0 due to the dependency on the Fish Speech S1-DAC autoencoder.

## Citation

If you use Echo TTS in your research, please cite:

```bibtex
@misc{darefsky2025echo,
    author = {Darefsky, Jordan},
    title = {Echo-TTS},
    year = {2025},
    url = {https://jordandarefsky.com/blog/2025/echo/}
}
```

## Migration from XTTS

If you're migrating from the original XTTS API server:

1. **Backup your speakers folder** - Echo TTS uses the same speaker format
2. **Update dependencies** - Run `pip install -r requirements.txt`
3. **Check VRAM** - Echo TTS requires 8GB+ (vs ~2GB for XTTS)
4. **Test with English first** - Echo TTS is optimized for English
5. **Adjust settings** - Parameter mapping may require tuning for your use case

See [`plans/echo-tts-migration-plan.md`](plans/echo-tts-migration-plan.md) for detailed migration documentation.
