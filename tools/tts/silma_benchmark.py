from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "benchmarks" / "tts" / "silma"
DEFAULT_TEXT = (
    "لم يكن صباحاً عادياً، بل كانت تسبقه ليلة طويلة من المعارك الخفية مع الذات.\n"
    "كنت أعرف أن وقود هذا اليوم لن يكون النوم، بل اليقين."
)


def env_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value) if value else None


def find_reference_audio(output_dir: Path) -> Path | None:
    configured = env_path("REF_AUDIO")
    if configured and configured.exists():
        return configured

    candidates = [
        output_dir / "reference_voice.wav",
        ROOT / "tools" / "tts" / "reference_voice.wav",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def find_reference_text(reference_audio: Path | None) -> str | None:
    configured = os.getenv("REF_TEXT", "").strip()
    if configured:
        return configured
    if not reference_audio:
        return None

    candidates = [
        reference_audio.with_suffix(".txt"),
        reference_audio.parent / "ref_text.txt",
        reference_audio.parent / "reference_text.txt",
    ]
    for path in candidates:
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text
    return None


def detect_device() -> str:
    try:
        import torch

        return "GPU" if torch.cuda.is_available() else "CPU"
    except Exception:
        return "unknown"


def instantiate_tts(silma_cls: type[Any]) -> Any:
    try:
        return silma_cls()
    except TypeError as exc:
        raise RuntimeError(f"Could not instantiate SilmaTTS with no arguments: {exc}") from exc


def call_silma(tts: Any, text: str, output_wav: Path, reference_audio: Path | None, ref_text: str, speed: float) -> None:
    method_names = [
        "tts_to_file",
        "text_to_file",
        "synthesize_to_file",
        "generate_to_file",
        "save_wav",
        "tts",
        "synthesize",
        "generate",
    ]
    kwargs = {
        "text": text,
        "output_path": str(output_wav),
        "file_path": str(output_wav),
        "out_path": str(output_wav),
        "speaker_wav": str(reference_audio) if reference_audio else None,
        "ref_audio": str(reference_audio) if reference_audio else None,
        "reference_audio": str(reference_audio) if reference_audio else None,
        "ref_text": ref_text,
        "reference_text": ref_text,
        "speed": speed,
    }

    errors: list[str] = []
    for method_name in method_names:
        method = getattr(tts, method_name, None)
        if not callable(method):
            continue
        signature = inspect.signature(method)
        accepted_kwargs = {}
        for name in signature.parameters:
            if name in kwargs and kwargs[name] is not None:
                accepted_kwargs[name] = kwargs[name]

        try:
            result = method(**accepted_kwargs)
        except TypeError as exc:
            errors.append(f"{method_name}: {exc}")
            continue

        if output_wav.exists():
            return
        if isinstance(result, (str, Path)) and Path(result).exists():
            shutil.copyfile(result, output_wav)
            return
        errors.append(f"{method_name}: completed but did not create {output_wav}")

    methods = ", ".join(name for name in method_names if callable(getattr(tts, name, None)))
    raise RuntimeError(
        "Could not generate audio with the installed SilmaTTS API. "
        f"Detected callable methods: {methods or 'none'}. Errors: {' | '.join(errors)}"
    )


def convert_to_mp3(output_wav: Path, output_mp3: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[WARN] ffmpeg not found. MP3 output skipped.")
        return False
    subprocess.run(
        [ffmpeg, "-y", "-i", str(output_wav), "-codec:a", "libmp3lame", "-qscale:a", "2", str(output_mp3)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return output_mp3.exists()


def main() -> int:
    output_dir = env_path("SILMA_OUTPUT_DIR") or DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_wav = output_dir / "test_audio_silma.wav"
    output_mp3 = output_dir / "test_audio_silma.mp3"
    text = os.getenv("SILMA_TEXT", DEFAULT_TEXT)
    speed = float(os.getenv("SILMA_SPEED", "1.0"))

    print("[INFO] SILMA benchmark starting")
    print(f"[INFO] Output directory: {output_dir}")
    print(f"[INFO] Device: {detect_device()}")

    reference_audio = find_reference_audio(output_dir)
    if reference_audio:
        print(f"[INFO] Reference audio found: {reference_audio}")
    else:
        print("[WARN] Reference audio not found.")
        print(f"[WARN] Put a permitted reference_voice.wav at: {output_dir / 'reference_voice.wav'}")
        print("[WARN] Continuing without reference audio if the installed SILMA API supports it.")

    ref_text = find_reference_text(reference_audio)
    if reference_audio and not ref_text:
        print("[FAIL] Reference audio exists but no permitted REF_TEXT was provided or found next to it.")
        print("[HINT] Set REF_TEXT explicitly or provide ref_text.txt beside reference_voice.wav.")
        return 2

    try:
        from silma_tts.api import SilmaTTS
    except Exception as exc:
        print(f"[FAIL] Could not import SilmaTTS: {exc}")
        print("[HINT] Install with: pip install silma-tts soundfile")
        return 1

    started = time.perf_counter()
    try:
        tts = instantiate_tts(SilmaTTS)
        call_silma(tts, text, output_wav, reference_audio, ref_text, speed)
    except Exception as exc:
        print(f"[FAIL] SILMA generation failed: {exc}")
        return 1

    generation_seconds = time.perf_counter() - started
    print(f"[OK] WAV generated: {output_wav}")
    print(f"[OK] Generation time seconds: {generation_seconds:.2f}")

    try:
        if convert_to_mp3(output_wav, output_mp3):
            print(f"[OK] MP3 generated: {output_mp3}")
    except Exception as exc:
        print(f"[WARN] MP3 conversion failed: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
