"""
NOVA AI - DistilBERT NLU Model Training Script
Fine-tunes DistilBERT for intent classification on the NOVA desktop agent dataset.
Uses transfer learning: pretrained DistilBERT base + fine-tuning on NOVA commands.

Usage:
    python ml/train_nlu.py
"""
import os
import sys
import json
import csv
import random
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
)
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from pathlib import Path

# =====================================================================
#  CONFIGURATION
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "ml" / "dataset.csv"
MODEL_SAVE_DIR = BASE_DIR / "ml" / "nlu_model"
LABEL_MAP_PATH = BASE_DIR / "ml" / "label_map.json"

# Training hyperparameters
BATCH_SIZE = 16
EPOCHS = 8
LEARNING_RATE = 2e-5
MAX_LENGTH = 64
MODEL_NAME = "distilbert-base-uncased"
SEED = 42

# Reproducibility
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")


# =====================================================================
#  DATASET
# =====================================================================
class NovaNLUDataset(Dataset):
    """Dataset for NOVA AI intent classification."""

    def __init__(self, texts, labels, tokenizer, max_length, label_map):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.label_map = label_map

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        label_id = self.label_map[label]

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "label": torch.tensor(label_id, dtype=torch.long),
        }


# =====================================================================
#  TRAINING LOOP
# =====================================================================
def train_epoch(model, dataloader, optimizer, scheduler):
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for batch in dataloader:
        input_ids = batch["input_ids"].to(DEVICE)
        attention_mask = batch["attention_mask"].to(DEVICE)
        labels = batch["label"].to(DEVICE)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        total_loss += loss.item()

        preds = torch.argmax(outputs.logits, dim=-1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total
    return avg_loss, accuracy


def evaluate(model, dataloader, label_names):
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(DEVICE)
            attention_mask = batch["attention_mask"].to(DEVICE)
            labels = batch["label"].to(DEVICE)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=-1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = accuracy_score(all_labels, all_preds)
    report = classification_report(all_labels, all_preds, target_names=label_names, zero_division=0)
    return accuracy, report


# =====================================================================
#  MAIN
# =====================================================================
def main():
    print("=" * 60)
    print("NOVA AI - DistilBERT NLU Model Training")
    print("=" * 60)

    # Load dataset
    print(f"\nLoading dataset from: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    texts = df["command"].tolist()
    labels = df["intent"].tolist()
    print(f"Dataset: {len(texts)} samples, {df['intent'].nunique()} unique intents")

    # Create label map
    unique_labels = sorted(df["intent"].unique().tolist())
    label_map = {label: idx for idx, label in enumerate(unique_labels)}
    reverse_label_map = {idx: label for label, idx in label_map.items()}
    print(f"Label map: {len(label_map)} intents")

    # Save label map
    with open(LABEL_MAP_PATH, "w") as f:
        json.dump({"label_map": label_map, "reverse_label_map": {str(k): v for k, v in reverse_label_map.items()}}, f, indent=2)
    print(f"Label map saved to: {LABEL_MAP_PATH}")

    # Train/test split
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=SEED, stratify=labels
    )
    print(f"Train: {len(train_texts)}, Test: {len(test_texts)}")

    # Load tokenizer
    print(f"\nLoading tokenizer: {MODEL_NAME}")
    tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)

    # Create datasets
    train_dataset = NovaNLUDataset(train_texts, train_labels, tokenizer, MAX_LENGTH, label_map)
    test_dataset = NovaNLUDataset(test_texts, test_labels, tokenizer, MAX_LENGTH, label_map)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # Load model (resume from checkpoint if available)
    CHECKPOINT_PATH = MODEL_SAVE_DIR / "checkpoint.pt"
    if CHECKPOINT_PATH.exists():
        print(f"Resuming from checkpoint: {CHECKPOINT_PATH}")
        checkpoint = torch.load(str(CHECKPOINT_PATH), map_location=DEVICE, weights_only=False)
        model = DistilBertForSequenceClassification.from_pretrained(
            str(MODEL_SAVE_DIR), num_labels=len(unique_labels),
        )
        model.to(DEVICE)
        optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
        optimizer.load_state_dict(checkpoint["optimizer"])
        start_epoch = checkpoint["epoch"]
        best_accuracy = checkpoint["best_accuracy"]
        print(f"  Resuming at epoch {start_epoch+1}, best accuracy so far: {best_accuracy:.2%}")
    else:
        print(f"Loading model: {MODEL_NAME} ({len(unique_labels)} classes)")
        model = DistilBertForSequenceClassification.from_pretrained(
            MODEL_NAME, num_labels=len(unique_labels),
        )
        model.to(DEVICE)
        optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
        start_epoch = 0
        best_accuracy = 0

    # Optimizer & scheduler
    total_steps = len(train_loader) * EPOCHS
    warmup_steps = int(total_steps * 0.1)
    # Warmup + linear decay scheduler (pure PyTorch)
    def lr_lambda(current_step, warmup_steps=warmup_steps, total_steps=total_steps):
        if current_step < warmup_steps:
            return float(current_step) / float(max(1, warmup_steps))
        return max(0.0, float(total_steps - current_step) / float(max(1, total_steps - warmup_steps)))

    scheduler = LambdaLR(optimizer, lr_lambda=lr_lambda)

    # Training loop
    print(f"\n{'='*60}")
    print(f"Training for {EPOCHS} epochs on {DEVICE}")
    print(f"{'='*60}\n")

    for epoch in range(start_epoch, EPOCHS):
        train_loss, train_acc = train_epoch(model, train_loader, optimizer, scheduler)
        test_acc, _ = evaluate(model, test_loader, unique_labels)

        print(f"Epoch {epoch+1}/{EPOCHS} | "
              f"Train Loss: {train_loss:.4f} | "
              f"Train Acc: {train_acc:.2%} | "
              f"Test Acc: {test_acc:.2%}")

        if test_acc > best_accuracy:
            best_accuracy = test_acc
            # Save best model
            model.save_pretrained(str(MODEL_SAVE_DIR))
            tokenizer.save_pretrained(str(MODEL_SAVE_DIR))
            print(f"  -> Best model saved (accuracy: {best_accuracy:.2%})")

        # Save checkpoint for resumption
        torch.save({
            "epoch": epoch + 1,
            "best_accuracy": best_accuracy,
            "optimizer": optimizer.state_dict(),
        }, str(CHECKPOINT_PATH))

    # Final evaluation
    print(f"\n{'='*60}")
    print("Final Evaluation")
    print(f"{'='*60}")
    final_acc, report = evaluate(model, test_loader, unique_labels)
    print(f"\nBest Accuracy: {best_accuracy:.2%}")
    print(f"Final Accuracy: {final_acc:.2%}")
    print(f"\nClassification Report:\n{report}")

    # Save config
    config = {
        "model_name": MODEL_NAME,
        "num_labels": len(unique_labels),
        "max_length": MAX_LENGTH,
        "batch_size": BATCH_SIZE,
        "epochs": EPOCHS,
        "learning_rate": LEARNING_RATE,
        "best_accuracy": best_accuracy,
        "device": str(DEVICE),
        "dataset_size": len(texts),
    }
    config_path = MODEL_SAVE_DIR / "nova_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nModel saved to: {MODEL_SAVE_DIR}")
    print(f"Config saved to: {config_path}")
    print("Training complete!")


if __name__ == "__main__":
    main()
