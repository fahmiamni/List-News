"""AI Summarizer using Hugging Face Transformers (Free)."""
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from typing import Optional
import threading
import torch


class NewsSummarizer:
    """Summarizes news articles using a free Hugging Face model."""
    
    # Using DistilBART - smaller, faster, but good quality
    MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
    
    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._lock = threading.Lock()
        self._loading = False
    
    def _load_model(self):
        """Lazy-load the model on first use."""
        if self._model is None and not self._loading:
            self._loading = True
            print("[AI] Loading summarization model (first time)...")
            print("   Model: distilbart-cnn-12-6 (free, runs locally)")
            print("   This may take 30-60 seconds...")
            
            try:
                # Load tokenizer and model directly
                self._tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
                self._model = AutoModelForSeq2SeqLM.from_pretrained(self.MODEL_NAME)
                
                # Set to evaluation mode
                self._model.eval()
                
                print("   [OK] Model loaded successfully!")
            except Exception as e:
                print(f"   [ERROR] Failed to load model: {e}")
                raise
            finally:
                self._loading = False
    
    def summarize(self, text: str, max_length: int = 120, min_length: int = 30) -> str:
        """
        Summarize the given text to ~100 words.
        
        Args:
            text: The text to summarize
            max_length: Maximum summary length (in tokens)
            min_length: Minimum summary length (in tokens)
        
        Returns:
            Summarized text (~100 words)
        """
        with self._lock:
            if self._model is None:
                self._load_model()
        
        # Clean up the text
        text = text.strip().replace("\n", " ").replace("  ", " ")
        
        # Truncate if too long (model has max input limit)
        max_input = 1024
        words = text.split()
        if len(words) > max_input:
            text = " ".join(words[:max_input])
        
        # Skip summarization if text is already short
        if len(words) < 50:
            return text
        
        try:
            # Tokenize input
            inputs = self._tokenizer(
                text,
                max_length=1024,
                truncation=True,
                return_tensors="pt"
            )
            
            # Generate summary
            with torch.no_grad():
                summary_ids = self._model.generate(
                    inputs["input_ids"],
                    max_length=max_length,
                    min_length=min_length,
                    length_penalty=2.0,
                    num_beams=4,
                    early_stopping=True
                )
            
            # Decode summary
            result = self._tokenizer.decode(
                summary_ids[0],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )
            
            # Post-process: ensure it ends with proper punctuation
            result = result.strip()
            if result and result[-1] not in '.!?':
                result += '.'
            
            return result
            
        except Exception as e:
            print(f"[WARNING] Summarization error: {e}")
            # Fallback to first part of text
            return " ".join(words[:100]) + "..."
    
    def summarize_batch(self, texts: list, max_length: int = 120, min_length: int = 30) -> list:
        """
        Summarize multiple texts efficiently.
        
        Args:
            texts: List of texts to summarize
            max_length: Maximum summary length
            min_length: Minimum summary length
        
        Returns:
            List of summarized texts
        """
        with self._lock:
            if self._model is None:
                self._load_model()
        
        results = []
        for i, text in enumerate(texts):
            print(f"   Summarizing {i+1}/{len(texts)}...", end="\r")
            results.append(self.summarize(text, max_length, min_length))
        print()  # New line after progress
        
        return results


# Singleton instance
_summarizer_instance = None


def get_summarizer() -> NewsSummarizer:
    """Get the singleton summarizer instance."""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = NewsSummarizer()
    return _summarizer_instance


def summarize_text(text: str, max_words: int = 100) -> str:
    """
    Convenience function to summarize text.
    
    Args:
        text: Text to summarize
        max_words: Approximate max word count (translated to tokens)
    
    Returns:
        Summarized text
    """
    summarizer = get_summarizer()
    # Approximate: 1 word ≈ 1.3 tokens
    max_tokens = int(max_words * 1.3)
    min_tokens = int(max_words * 0.5)
    return summarizer.summarize(text, max_length=max_tokens, min_length=min_tokens)
