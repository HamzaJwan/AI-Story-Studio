FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/opt/silma_stubs

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/silma_stubs/nemo_text_processing/text_normalization \
    && touch /opt/silma_stubs/nemo_text_processing/__init__.py \
    && touch /opt/silma_stubs/nemo_text_processing/text_normalization/__init__.py \
    && printf '%s\n' \
        'class Normalizer:' \
        '    def __init__(self, *args, **kwargs):' \
        '        pass' \
        '    def normalize(self, text, *args, **kwargs):' \
        '        return text' \
        > /opt/silma_stubs/nemo_text_processing/text_normalization/normalize.py

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        "numpy<=1.26.4" \
        cached_path \
        catt_tashkeel==1.0.2 \
        click \
        "ema_pytorch>=0.5.2" \
        gradio \
        "hydra-core>=1.3.0" \
        librosa \
        matplotlib \
        pydub \
        safetensors \
        soundfile \
        tomli \
        torchcodec \
        torchdiffeq \
        "tqdm>=4.65.0" \
        transformers \
        transformers_stream_generator \
        unidecode \
        vocos \
        "x_transformers>=1.31.14" \
    && python -m pip install --no-cache-dir --no-deps silma-tts

CMD ["python", "tools/tts/silma_benchmark.py"]
