# Migration Guide: XTTS → Echo TTS

This guide helps you migrate from the original XTTS API server to the Echo TTS version.

## What Changed?

### Model
- **Old:** XTTS v2 (Autoregressive GPT, ~2B parameters)
- **New:** Echo TTS (Diffusion DiT, 2.4B parameters)

### Audio Quality
- **Old:** 24kHz output
- **New:** 44.1kHz output (higher quality)

### Performance
- **Old:** ~2-3 seconds for 10s text
- **New:** ~0.5 seconds for 10s text (on A100)

### Hardware Requirements
- **Old:** ~2GB VRAM
- **New:** 8GB+ VRAM required

### Language Support
- **Old:** 18 languages with good quality
- **New:** Primarily English (limited multilingual support)

### Generation Limit
- **Old:** Unlimited duration
- **New:** 30 seconds maximum per request

## Quick Start

### 1. Backup Your Data

```bash
# Backup your speakers folder
cp -r speakers speakers_backup

# Backup any custom models
cp -r models models_backup
```

### 2. Update Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install new dependencies
pip install -r requirements.txt
```

### 3. Verify Hardware

```bash
# Check GPU VRAM
nvidia-smi

# You should see at least 8GB of VRAM available
```

### 4. Start the Server

```bash
python -m xtts_api_server
```

The first run will download Echo TTS models from HuggingFace (~5GB total). This may take 1-2 minutes.

### 5. Test with a Simple Request

```bash
curl -X POST "http://localhost:8020/tts_to_audio" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test of the Echo TTS model.",
    "speaker_wav": "male",
    "language": "en"
  }' \
  --output test.wav
```

## Parameter Mapping

Your existing XTTS settings will be automatically mapped to Echo TTS parameters:

| XTTS Parameter | Echo TTS Parameter | Effect |
|----------------|-------------------|---------|
| `temperature: 0.75` | `cfg_scale_text: 1.5` | Lower temperature → higher text guidance |
| `top_p: 0.85` | `cfg_scale_speaker: 6.8` | Higher top_p → stronger speaker conditioning |
| `top_k: 50` | `num_steps: 40` | Higher top_k → more sampling steps |
| `length_penalty: 1.0` | `truncation_factor: 0.8` | Controls output length |
| `repetition_penalty: 5.0` | `rescale_k: 1.2` | Temporal score rescaling |
| `speed: 1.0` | `sequence_length: 640` | Higher speed → shorter sequence |

### Fine-Tuning Settings

If you want to adjust Echo TTS settings directly, you can modify them in the code:

```python
# In xtts_api_server/echo_tts_wrapper.py
default_echo_tts_settings = {
    "num_steps": 40,              # More steps = better quality, slower
    "cfg_scale_text": 3.0,         # Higher = more text adherence
    "cfg_scale_speaker": 8.0,       # Higher = stronger speaker cloning
    "cfg_min_t": 0.5,              # CFG timestep range
    "cfg_max_t": 1.0,
    "truncation_factor": 0.8,        # Output length control
    "rescale_k": 1.2,              # Temporal rescaling
    "rescale_sigma": 3.0,
    "sequence_length": 640,           # Max 640 (~30 seconds)
}
```

## API Compatibility

All existing API endpoints work exactly the same way:

```python
# Example: Generate audio
import requests

response = requests.post(
    "http://localhost:8020/tts_to_audio",
    json={
        "text": "Hello world!",
        "speaker_wav": "male",
        "language": "en"
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

### Streaming Mode

Streaming mode is **experimental** with Echo TTS:

```python
# Works, but generates full audio first then streams
response = requests.get(
    "http://localhost:8020/tts_stream",
    params={
        "text": "Hello world!",
        "speaker_wav": "male",
        "language": "en"
    },
    stream=True
)

for chunk in response.iter_content(chunk_size=1024):
    # Process audio chunks
    pass
```

For best results, use non-streaming mode.

## Speaker Audio

Your existing speaker files will work with Echo TTS! No conversion needed.

### Recommended Speaker Format

For best voice cloning:

1. **Duration:** 7-10 seconds (up to 5 minutes supported)
2. **Format:** WAV (any sample rate, will be resampled)
3. **Quality:** Clean, no background noise
4. **Content:** Natural speech with vocal range

### Multi-Sample Speakers

Echo TTS supports multiple reference samples:

```
speakers/
└── my_voice/
    ├── sample1.wav
    ├── sample2.wav
    └── sample3.wav
```

All samples will be concatenated for speaker conditioning.

## Language Considerations

### English (Recommended)
Best quality and performance. Use `language: "en"`.

### Other Languages
Echo TTS is primarily trained on English. Other languages may work but with lower quality.

**Workaround:** For non-English text, try:
1. Using English text with phonetic spelling
2. Adjusting `cfg_scale_text` (lower for more flexibility)
3. Using shorter text segments

## Troubleshooting

### Out of Memory Error

```
CUDA out of memory. Echo TTS requires at least 8GB VRAM.
```

**Solutions:**
1. Use a GPU with 8GB+ VRAM
2. Close other GPU applications
3. Use `--lowvram` flag (not recommended, slower)
4. Run on CPU (very slow)

### Model Download Fails

```
Failed to load Echo TTS model
```

**Solutions:**
1. Check internet connection
2. Verify HuggingFace access
3. Check disk space (need ~5GB free)
4. Try manual download from HuggingFace

### Poor Audio Quality

**Solutions:**
1. Use better speaker reference audio
2. Adjust `cfg_scale_speaker` (try 5.0-10.0)
3. Adjust `cfg_scale_text` (try 2.0-4.0)
4. Use shorter text segments
5. Ensure text is in English

### Slow Generation

**Solutions:**
1. Check GPU is being used (not CPU)
2. Reduce `num_steps` (try 20-30)
3. Use shorter text segments
4. Update PyTorch to latest version

## Rollback

If you need to revert to XTTS:

```bash
# Restore original files
git checkout HEAD -- requirements.txt xtts_api_server/server.py

# Reinstall XTTS dependencies
pip install coqui-tts[languages]==0.24.1

# Start server
python -m xtts_api_server
```

## Performance Comparison

| Metric | XTTS | Echo TTS |
|---------|-------|-----------|
| 10s text generation | ~2-3s | ~0.5s |
| 30s text generation | ~6-8s | ~1.5s |
| VRAM usage | ~2GB | ~5.4GB |
| Audio quality | 24kHz | 44.1kHz |
| Max duration | Unlimited | 30s |
| Languages | 18 (good) | 1 (English) |

## Next Steps

1. **Test thoroughly** with your use cases
2. **Fine-tune settings** for your speakers
3. **Monitor performance** on your hardware
4. **Provide feedback** on issues

## Support

- **Echo TTS Issues:** [GitHub Issues](https://github.com/jordandare/echo-tts/issues)
- **Server Issues:** [GitHub Issues](https://github.com/daswer123/xtts-api-server/issues)
- **Documentation:** See [`plans/echo-tts-migration-plan.md`](plans/echo-tts-migration-plan.md)

## Credits

- **Echo TTS:** Jordan Darefsky
- **Original Server:** daswer123
- **Migration Plan:** See [`plans/`](plans/) directory
