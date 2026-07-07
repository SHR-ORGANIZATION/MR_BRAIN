"""
NOVA AI - DistilBERT NLU Inference Module
Loads the fine-tuned DistilBERT model and provides intent predictions.
Runs fully offline - no API calls, no internet required.

Usage:
    from ml.nlu_model import NOVANLU
    nlu = NOVANLU()
    intent, confidence = nlu.predict("copy ABDUL.docx to MADAM")
"""
import json
import torch
import numpy as np
from pathlib import Path
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification


MODEL_DIR = Path(__file__).resolve().parent / "nlu_model"
LABEL_MAP_PATH = Path(__file__).resolve().parent / "label_map.json"
MAX_LENGTH = 64


class NOVANLU:
    """NOVA AI Natural Language Understanding model.
    
    Fine-tuned DistilBERT for intent classification.
    Loads once, predicts fast — fully offline.
    """

    def __init__(self, model_dir=None, label_map_path=None):
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self.label_map_path = Path(label_map_path) if label_map_path else LABEL_MAP_PATH

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"NLU model not found at {self.model_dir}. "
                f"Run 'python ml/train_nlu.py' to train the model first."
            )

        # Load label map
        with open(self.label_map_path, "r") as f:
            maps = json.load(f)
        self.label_map = maps["label_map"]
        self.reverse_label_map = {int(k): v for k, v in maps["reverse_label_map"].items()}
        self.label_names = [self.reverse_label_map[i] for i in range(len(self.reverse_label_map))]

        # Load model + tokenizer
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = DistilBertTokenizer.from_pretrained(str(self.model_dir))
        self.model = DistilBertForSequenceClassification.from_pretrained(str(self.model_dir))
        self.model.to(self.device)
        self.model.eval()

        print(f"NLU model loaded ({len(self.label_names)} intents, device={self.device})")

    def predict(self, text):
        """Predict intent for a single command.
        
        Returns:
            tuple: (intent_name: str, confidence: float)
        """
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

        return intent, confidence

    def predict_top_k(self, text, k=3):
        """Predict top-k intents for a command.
        
        Returns:
            list of tuples: [(intent_name, confidence), ...]
        """
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

    def get_all_probabilities(self, text):
        """Get probability distribution over all intents.
        
        Returns:
            dict: {intent_name: confidence, ...}
        """
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


# =====================================================================
#  STANDALONE TEST
# =====================================================================
if __name__ == "__main__":
    nlu = NOVANLU()

    test_commands = [
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
    ]

    print("\n" + "=" * 60)
    print("NOVA AI NLU Model - Test Predictions")
    print("=" * 60 + "\n")

    for cmd in test_commands:
        intent, conf = nlu.predict(cmd)
        top3 = nlu.predict_top_k(cmd, k=3)
        top3_str = ", ".join(f"{i}({c:.0%})" for i, c in top3)
        print(f'  "{cmd}"')
        print(f"    -> {intent} ({conf:.2%})  |  Top 3: {top3_str}\n")
