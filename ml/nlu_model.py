"""
AMAZON AI - DistilBERT NLU Inference Module
Loads the fine-tuned DistilBERT model and provides intent predictions.
Runs fully offline - no API calls, no internet required.

Usage:
    from ml.nlu_model import AMAZONNLU
    nlu = AMAZONNLU()
    intent, confidence = nlu.predict("copy ABDUL.docx to MADAM")
"""
import json
import torch
import numpy as np
from pathlib import Path
from typing import Union, List, Tuple, Dict, Optional
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import re
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent / "nlu_model"
LABEL_MAP_PATH = Path(__file__).resolve().parent / "label_map.json"
MAX_LENGTH = 64
DEFAULT_CONFIDENCE_THRESHOLD = 0.5


class AMAZONNLU:
    """AMAZON AI Natural Language Understanding model.
    
    Fine-tuned DistilBERT for intent classification.
    Loads once, predicts fast — fully offline.
    
    Features:
    - Single prediction
    - Top-K predictions
    - Full probability distribution
    - Batch prediction
    - Confidence thresholding
    - Fallback to unknown intent
    """

    def __init__(
        self, 
        model_dir: Optional[Union[str, Path]] = None,
        label_map_path: Optional[Union[str, Path]] = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        fallback_intent: str = "unknown"
    ):
        """Initialize the NLU model.
        
        Args:
            model_dir: Directory containing the trained model
            label_map_path: Path to label mapping JSON file
            confidence_threshold: Minimum confidence for a prediction (0.0-1.0)
            fallback_intent: Intent to return when confidence is below threshold
        """
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self.label_map_path = Path(label_map_path) if label_map_path else LABEL_MAP_PATH
        self.confidence_threshold = confidence_threshold
        self.fallback_intent = fallback_intent

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"NLU model not found at {self.model_dir}. "
                f"Run 'python ml/train_nlu.py' to train the model first."
            )

        # Load label map
        self._load_label_map()

        # Load model + tokenizer
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading model on {self.device}...")
        
        self.tokenizer = DistilBertTokenizer.from_pretrained(str(self.model_dir))
        self.model = DistilBertForSequenceClassification.from_pretrained(str(self.model_dir))
        self.model.to(self.device)
        self.model.eval()

        # Load config if available
        self.config = self._load_config()
        
        logger.info(f"✅ NLU model loaded ({len(self.label_names)} intents, device={self.device})")
        logger.info(f"   Confidence threshold: {self.confidence_threshold}")
        logger.info(f"   Fallback intent: {self.fallback_intent}")

    def _load_label_map(self) -> None:
        """Load label mapping from JSON file."""
        with open(self.label_map_path, "r") as f:
            maps = json.load(f)
        
        self.label_map = maps.get("label_map", {})
        self.reverse_label_map = {
            int(k): v for k, v in maps.get("reverse_label_map", {}).items()
        }
        
        # Handle both old and new format
        if "intents" in maps:
            self.label_names = maps["intents"]
        else:
            # Create label names from reverse_label_map
            max_id = max(self.reverse_label_map.keys()) if self.reverse_label_map else 0
            self.label_names = [
                self.reverse_label_map.get(i, f"unknown_{i}") 
                for i in range(max_id + 1)
            ]
        
        self.num_intents = len(self.label_names)
        logger.info(f"Loaded {self.num_intents} intents: {self.label_names}")

    def _load_config(self) -> Dict:
        """Load model configuration if available."""
        config_path = self.model_dir / "amazon_config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)
        return {}

    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize input text."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove special characters (keep alphanumeric and basic punctuation)
        text = re.sub(r'[^a-zA-Z0-9\s\.\,\-\_\']', '', text)
        
        return text

    def predict(
        self, 
        text: str,
        preprocess: bool = True,
        apply_threshold: bool = True
    ) -> Tuple[str, float]:
        """Predict intent for a single command.
        
        Args:
            text: Command text to classify
            preprocess: Whether to preprocess the text
            apply_threshold: Whether to apply confidence threshold
            
        Returns:
            tuple: (intent_name: str, confidence: float)
        """
        if preprocess:
            text = self._preprocess_text(text)
        
        # Skip empty text
        if not text.strip():
            return self.fallback_intent, 0.0

        encoding = self.tokenizer(
            text,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)

        probabilities = torch.softmax(outputs.logits, dim=-1).squeeze().cpu().numpy()
        predicted_id = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_id])
        intent = self.label_names[predicted_id]

        # Apply confidence threshold
        if apply_threshold and confidence < self.confidence_threshold:
            return self.fallback_intent, confidence

        return intent, confidence

    def predict_top_k(
        self, 
        text: str, 
        k: int = 3, 
        preprocess: bool = True
    ) -> List[Tuple[str, float]]:
        """Predict top-k intents for a command.
        
        Args:
            text: Command text to classify
            k: Number of top predictions to return
            preprocess: Whether to preprocess the text
            
        Returns:
            list of tuples: [(intent_name, confidence), ...]
        """
        if preprocess:
            text = self._preprocess_text(text)
        
        if not text.strip():
            return [(self.fallback_intent, 0.0)]

        encoding = self.tokenizer(
            text,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)

        probabilities = torch.softmax(outputs.logits, dim=-1).squeeze().cpu().numpy()
        top_ids = np.argsort(probabilities)[::-1][:k]

        return [(self.label_names[int(i)], float(probabilities[i])) for i in top_ids]

    def predict_batch(
        self, 
        texts: List[str],
        preprocess: bool = True,
        apply_threshold: bool = True
    ) -> List[Tuple[str, float]]:
        """Predict intents for multiple commands in batch.
        
        Args:
            texts: List of command texts
            preprocess: Whether to preprocess texts
            apply_threshold: Whether to apply confidence threshold
            
        Returns:
            List of (intent_name, confidence) tuples
        """
        if preprocess:
            texts = [self._preprocess_text(t) for t in texts]
        
        # Filter empty texts
        results = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text.strip():
                valid_texts.append((i, text))
            else:
                results.append((i, self.fallback_intent, 0.0))

        if not valid_texts:
            return [(self.fallback_intent, 0.0) for _ in texts]

        # Tokenize all texts at once
        encodings = self.tokenizer(
            [t for _, t in valid_texts],
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encodings["input_ids"].to(self.device)
        attention_mask = encodings["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)

        probabilities = torch.softmax(outputs.logits, dim=-1).cpu().numpy()
        
        # Map results back to original order
        result_map = {}
        for idx, (orig_idx, _) in enumerate(valid_texts):
            probs = probabilities[idx]
            predicted_id = int(np.argmax(probs))
            confidence = float(probs[predicted_id])
            intent = self.label_names[predicted_id]
            
            if apply_threshold and confidence < self.confidence_threshold:
                intent = self.fallback_intent
            
            result_map[orig_idx] = (intent, confidence)

        return [result_map[i] for i in range(len(texts))]

    def get_all_probabilities(
        self, 
        text: str, 
        preprocess: bool = True
    ) -> Dict[str, float]:
        """Get probability distribution over all intents.
        
        Args:
            text: Command text to classify
            preprocess: Whether to preprocess the text
            
        Returns:
            dict: {intent_name: confidence, ...}
        """
        if preprocess:
            text = self._preprocess_text(text)
        
        if not text.strip():
            return {intent: 0.0 for intent in self.label_names}

        encoding = self.tokenizer(
            text,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)

        probabilities = torch.softmax(outputs.logits, dim=-1).squeeze().cpu().numpy()
        return {self.label_names[i]: float(probabilities[i]) for i in range(len(self.label_names))}

    def get_model_info(self) -> Dict:
        """Get model information."""
        info = {
            "model_dir": str(self.model_dir),
            "device": str(self.device),
            "num_intents": self.num_intents,
            "intents": self.label_names,
            "confidence_threshold": self.confidence_threshold,
            "fallback_intent": self.fallback_intent,
            "max_length": MAX_LENGTH,
        }
        info.update(self.config)
        return info

    def evaluate_commands(self, commands: List[str]) -> Dict:
        """Evaluate a list of commands and return detailed predictions.
        
        Args:
            commands: List of command strings
            
        Returns:
            Dictionary with predictions and metadata
        """
        results = []
        for cmd in commands:
            intent, conf = self.predict(cmd)
            top3 = self.predict_top_k(cmd, k=3)
            results.append({
                "command": cmd,
                "intent": intent,
                "confidence": conf,
                "top_3": top3,
                "above_threshold": conf >= self.confidence_threshold
            })
        
        return {
            "num_commands": len(commands),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }


# =====================================================================
#  STANDALONE TEST
# =====================================================================
if __name__ == "__main__":
    # Initialize NLU
    print("=" * 60)
    print("AMAZON AI NLU Model - Test Predictions")
    print("=" * 60 + "\n")
    
    # Try to load from different paths
    try:
        nlu = AMAZONNLU(confidence_threshold=0.3)
    except FileNotFoundError:
        # Try parent directory
        parent_model_dir = Path(__file__).resolve().parent.parent / "ml" / "nlu_model"
        if parent_model_dir.exists():
            nlu = AMAZONNLU(
                model_dir=parent_model_dir,
                confidence_threshold=0.3
            )
        else:
            print("❌ Model not found! Please train the model first.")
            print("   Run: python ml/train_nlu.py")
            exit(1)
    
    # Show model info
    print("Model Info:")
    print(json.dumps(nlu.get_model_info(), indent=2))
    print("\n" + "=" * 60 + "\n")

    test_commands = [
        # Basic commands
        "open chrome",
        "open tiktok",
        "copy ABDUL.docx to MADAM",
        "copy ABDUL.docx to MADAM FOLDER",
        "search folder named madam",
        "fina nyumba",
        "findi SHAKIRA",
        "tengeneza faili report",
        "nakili folder backup to desktop",
        "delete the old report file",
        "rename my invoice to paid_invoice",
        "hello how are you",
        "what is the weather today",
        "create a new folder called work",
        "move all photos to the pictures folder",
        
        # Edge cases
        "",
        "   ",
        "chrome",
        "close",
        "123456",
        
        # Swahili commands
        "fungua notepad",
        "funga chrome",
        "tengeneza kabrasha mpya",
        "futa faili la zamani",
        "nakili faili hii",
        "hamisha kabrasha desktop",
        "tafuta faili shakira",
        "badilisha jina la faili",
        "soma faili hii",
        "onyesha michakato",
        
        # Complex commands
        "please open google chrome browser for me now",
        "i would like to create a new folder called projects on my desktop",
        "can you find the file called report.pdf in my documents folder",
        "copy all files from the downloads folder to the backup folder",
        "rename the project folder from old to new version",
        "move the file report.docx to the archive directory",
        
        # Web commands
        "open youtube",
        "go to google",
        "search for python tutorials",
        "visit stackoverflow",
        "open facebook for me",
        
        # File operations
        "delete file notes.txt",
        "create file report.docx",
        "read file config.json",
        "rename file old.txt to new.txt",
        "move file data.csv to archive",
        
        # Folder operations
        "create folder school",
        "delete folder temp",
        "rename folder projects to archive",
        "move folder documents to backup",
        "copy folder work to backup",
        
        # Run commands
        "run command dir",
        "execute ipconfig",
        "ping google.com",
        "show running processes",
        "list active applications",
    ]

    # Test predictions
    for cmd in test_commands:
        intent, conf = nlu.predict(cmd)
        top3 = nlu.predict_top_k(cmd, k=3)
        top3_str = ", ".join(f"{i}({c:.0%})" for i, c in top3)
        
        # Highlight if confidence is below threshold
        status = "⚠️" if conf < nlu.confidence_threshold else "✅"
        
        print(f'{status}  "{cmd}"')
        print(f"    -> {intent} ({conf:.2%})  |  Top 3: {top3_str}\n")

    # Test batch prediction
    print("\n" + "=" * 60)
    print("Batch Prediction Test")
    print("=" * 60 + "\n")
    
    batch_commands = test_commands[:5]
    batch_results = nlu.predict_batch(batch_commands)
    
    for cmd, (intent, conf) in zip(batch_commands, batch_results):
        print(f'  "{cmd}" -> {intent} ({conf:.2%})')

    # Test all probabilities
    print("\n" + "=" * 60)
    print("Full Probability Distribution")
    print("=" * 60 + "\n")
    
    test_cmd = "open chrome"
    probs = nlu.get_all_probabilities(test_cmd)
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print(f'  "{test_cmd}"')
    for intent, prob in sorted_probs:
        if prob > 0.01:
            print(f"    {intent}: {prob:.2%}")
    
    # Test evaluation
    print("\n" + "=" * 60)
    print("Evaluation Test")
    print("=" * 60 + "\n")
    
    eval_results = nlu.evaluate_commands([
        "open chrome",
        "create folder test",
        "delete file old.txt",
        "hello world"
    ])
    
    print(json.dumps(eval_results, indent=2))
    
    print("\n✅ All tests completed!")