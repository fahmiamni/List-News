"""AI Summarizer using Hugging Face Transformers (Free) — optional, not imported by default."""
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from typing import Optional
import threading
import torch


class NewsSummarizer:
    """Summarizes news articles using a free Hugging Face model."""

    MODEL_NAME = "sshleifer/distilbart-cnn-12-6"

    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._lock = threading.Lock()
        self._loading = False

    def _load_model(self):
        if self._model is None and not self._loading:
            self._loading = True
            print("[AI] Loading summarization model (first time)...")
            print("   Model: distilbart-cnn-12-6 (free, runs locally)")
            print("   This may take 30-60 seconds...")
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
                self._model = AutoModelForSeq2SeqLM.from_pretrained(self.MODEL_NAME)
                self._model.eval()
                print("   [OK] Model loaded successfully!")
            except Exception as e:
                print(f"   [ERROR] Failed to load model: {e}")
                raise
            finally:
                self._loading = False

    def summarize(self, text: str, max_length: int = 120, min_length: int = 30) -> str:
        with self._lock:
            if self._model is None:
                self._load_model()

        text = text.strip().replace("\n", " ").replace("  ", " ")
        max_input = 1024
        words = text.split()
        if len(words) > max_input:
            text = " ".join(words[:max_input])
        if len(words) < 50:
            return text

        try:
            inputs = self._tokenizer(
                text, max_length=1024, truncation=True, return_tensors="pt"
            )
            with torch.no_grad():
                summary_ids = self._model.generate(
                    inputs["input_ids"],
                    max_length=max_length,
                    min_length=min_length,
                    length_penalty=2.0,
                    num_beams=4,
                    early_stopping=True
                )
            result = self._tokenizer.decode(
                summary_ids[0],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )
            result = result.strip()
            if result and result[-1] not in '.!?':
                result += '.'
            return result
        except Exception as e:
            print(f"[WARNING] Summarization error: {e}")
            return " ".join(words[:100]) + "..."

    def summarize_batch(self, texts: list, max_length: int = 120, min_length: int = 30) -> list:
        with self._lock:
            if self._model is None:
                self._load_model()
        results = []
        for i, text in enumerate(texts):
            print(f"   Summarizing {i+1}/{len(texts)}...", end="\r")
            results.append(self.summarize(text, max_length, min_length))
        print()
        return results