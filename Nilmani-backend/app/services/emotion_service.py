"""
Speech Emotion Recognition service for CPU-only inference.

The trained model uses a Wav2Vec2 + BiLSTM + Attention architecture and expects
16 kHz mono audio padded or truncated to 4 seconds.
"""

from __future__ import annotations

import io
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import Wav2Vec2Model, Wav2Vec2Processor

from app.core.config import settings

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = APP_DIR / "models" / "ser_wav2vec2_bilstm_attention.pth"
DEFAULT_METADATA_PATH = APP_DIR / "models" / "ser_metadata.json"


class Attention(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Linear(hidden_dim * 2, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weights = torch.softmax(self.attn(x), dim=1)
        return torch.sum(weights * x, dim=1)


class SERModel(nn.Module):
    def __init__(self, num_classes: int, cache_dir: str | None = None):
        super().__init__()

        # Allow supplying a local HF cache dir to avoid remote downloads
        if cache_dir:
            self.wav2vec = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base", cache_dir=cache_dir)
        else:
            self.wav2vec = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")
        for param in self.wav2vec.parameters():
            param.requires_grad = False

        self.lstm = nn.LSTM(
            input_size=768,
            hidden_size=256,
            num_layers=2,
            bidirectional=True,
            batch_first=True,
        )
        self.attention = Attention(256)
        self.classifier = nn.Linear(512, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            features = self.wav2vec(x).last_hidden_state

        lstm_out, _ = self.lstm(features)
        attn_out = self.attention(lstm_out)
        return self.classifier(attn_out)


class EmotionService:
    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = Path(settings.SER_MODEL_PATH or DEFAULT_MODEL_PATH)
        self.metadata_path = Path(settings.SER_METADATA_PATH or DEFAULT_METADATA_PATH)
        self.sample_rate = settings.SER_SAMPLE_RATE
        self.max_seconds = settings.SER_MAX_SECONDS
        self.max_length = self.sample_rate * self.max_seconds
        self.min_samples = int(self.sample_rate * 0.5)

        self.labels = self._load_labels()
        # Use a local HF cache inside the app to avoid repeated remote downloads.
        hf_cache_dir = APP_DIR / "models" / "hf_cache"
        hf_cache_dir.mkdir(parents=True, exist_ok=True)

        # One-time download will store files under hf_cache_dir; subsequent runs use local cache.
        self.processor = Wav2Vec2Processor.from_pretrained(
            "facebook/wav2vec2-base",
            cache_dir=str(hf_cache_dir),
        )
        self.model = self._load_model(hf_cache_dir)

    def _load_labels(self) -> List[str]:
        if self.metadata_path.exists():
            with self.metadata_path.open("r", encoding="utf-8") as metadata_file:
                metadata = json.load(metadata_file)
            labels = metadata.get("labels")
            if labels:
                return list(labels)

        return [
            "angry",
            "calm",
            "disgust",
            "fear",
            "happy",
            "neutral",
            "sad",
            "surprise",
        ]

    def _load_model(self, hf_cache_dir: Path | None = None) -> SERModel:
        if not self.model_path.exists():
            raise FileNotFoundError(f"SER model not found at {self.model_path}")

        # Instantiate model architecture
        model = SERModel(len(self.labels), cache_dir=str(hf_cache_dir) if hf_cache_dir is not None else None)

        # Attempt to load saved object/state in a few ways to support different checkpoint formats
        try:
            # Preferred: saved state_dict (clean)
            try:
                state = torch.load(self.model_path, map_location=self.device, weights_only=False)
            except TypeError:
                state = torch.load(self.model_path, map_location=self.device)

            # If the saved object is a full Module instance
            if isinstance(state, nn.Module):
                logger.info("Loaded full Module object from checkpoint. Using it directly.")
                model = state
            # If checkpoint is a dict, unwrap common wrapper formats first.
            elif isinstance(state, dict):
                candidate_state_dict = None

                if "model_state_dict" in state and isinstance(state["model_state_dict"], dict):
                    candidate_state_dict = state["model_state_dict"]
                elif "state_dict" in state and isinstance(state["state_dict"], dict):
                    candidate_state_dict = state["state_dict"]
                else:
                    candidate_state_dict = state

                try:
                    model.load_state_dict(candidate_state_dict)
                except RuntimeError:
                    # Some older checkpoints were serialized as full objects.
                    state_alt = torch.load(self.model_path, map_location=self.device, weights_only=False)
                    if isinstance(state_alt, dict):
                        for key in ("model_state_dict", "state_dict"):
                            if key in state_alt and isinstance(state_alt[key], dict):
                                model.load_state_dict(state_alt[key])
                                break
                        else:
                            model.load_state_dict(state_alt)
                    elif isinstance(state_alt, nn.Module):
                        model = state_alt
                    else:
                        raise
            else:
                raise RuntimeError("Unrecognized checkpoint format")

        except Exception as e:
            logger.error("Failed to load model checkpoint: %s", str(e), exc_info=True)
            raise

        model.to(self.device)
        model.eval()

        logger.info("Loaded SER model from %s on %s", self.model_path, self.device)
        return model

    @staticmethod
    def _decode_audio(file_bytes: bytes) -> Tuple[torch.Tensor, int]:
        if not file_bytes:
            raise ValueError("Empty audio payload")

        audio_data, sample_rate = sf.read(io.BytesIO(file_bytes), dtype="float32")
        waveform = torch.tensor(audio_data, dtype=torch.float32)

        if waveform.ndim > 1:
            waveform = waveform.mean(dim=1)

        if waveform.numel() == 0:
            raise ValueError("Unable to decode audio")

        peak = waveform.abs().max()
        if peak > 0:
            waveform = waveform / peak

        return waveform, int(sample_rate)

    def _resample_if_needed(self, waveform: torch.Tensor, sample_rate: int) -> torch.Tensor:
        if sample_rate == self.sample_rate:
            return waveform

        target_length = max(1, int(waveform.shape[-1] * self.sample_rate / sample_rate))
        return F.interpolate(
            waveform.unsqueeze(0).unsqueeze(0),
            size=target_length,
            mode="linear",
            align_corners=False,
        ).squeeze(0).squeeze(0)

    def _pad_or_trim(self, waveform: torch.Tensor) -> torch.Tensor:
        if waveform.shape[-1] < self.min_samples:
            raise ValueError("Audio is too short for emotion analysis")

        if waveform.shape[-1] > self.max_length:
            waveform = waveform[: self.max_length]
        elif waveform.shape[-1] < self.max_length:
            waveform = F.pad(waveform, (0, self.max_length - waveform.shape[-1]))

        return waveform

    def predict(self, file_bytes: bytes) -> Dict[str, Any]:
        waveform, sample_rate = self._decode_audio(file_bytes)
        waveform = self._resample_if_needed(waveform, sample_rate)
        waveform = self._pad_or_trim(waveform)

        inputs = self.processor(
            waveform.numpy(),
            sampling_rate=self.sample_rate,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        input_values = inputs.input_values.to(self.device)

        with torch.no_grad():
            logits = self.model(input_values)
            probabilities = torch.softmax(logits, dim=-1).squeeze(0).detach().cpu().numpy()

        best_index = int(np.argmax(probabilities))
        label = self.labels[best_index]

        return {
            "label": label,
            "confidence": float(probabilities[best_index]),
            "scores": {
                self.labels[index]: float(probability)
                for index, probability in enumerate(probabilities)
            },
            "sample_rate": self.sample_rate,
            "duration_seconds": round(float(waveform.shape[-1]) / self.sample_rate, 2),
        }


@lru_cache(maxsize=1)
def get_emotion_service() -> EmotionService:
    return EmotionService()


def predict_emotion(file_bytes: bytes) -> Dict[str, Any]:
    return get_emotion_service().predict(file_bytes)