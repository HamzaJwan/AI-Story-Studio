from __future__ import annotations

import wave
from pathlib import Path

VOICE_NAME = "ar_JO-kareem-medium"
VOICE_DIR = Path("/workspace/data/piper_voices")


def ensure_voice() -> tuple[Path, Path]:
    from piper.download_voices import download_voice

    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    model_path = VOICE_DIR / f"{VOICE_NAME}.onnx"
    config_path = VOICE_DIR / f"{VOICE_NAME}.onnx.json"
    if not model_path.exists() or not config_path.exists():
        download_voice(VOICE_NAME, VOICE_DIR)
    return model_path, config_path


def synthesize_to_wav(text: str, output_wav: Path, speed: float = 1.0) -> None:
    from piper import PiperVoice, SynthesisConfig

    model_path, config_path = ensure_voice()
    voice = PiperVoice.load(model_path, config_path=config_path, use_cuda=False)
    syn_config = SynthesisConfig(length_scale=1.0 / max(speed, 0.1))
    with wave.open(str(output_wav), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=syn_config)
