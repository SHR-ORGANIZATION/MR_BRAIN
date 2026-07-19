"""
AMAZON AI - DistilBERT NLU Model Training Script
Fine-tunes DistilBERT for intent classification on the AMAZON desktop agent dataset.
Uses transfer learning: pretrained DistilBERT base + fine-tuning on AMAZON commands.

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
    get_linear_schedule_with_warmup,
)
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from pathlib import Path
import logging
from datetime import datetime

# =====================================================================
#  CONFIGURATION
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
# Use auto_training_data.csv (has correct format: command,intent)
DATASET_PATH = BASE_DIR / "learning" / "auto_training_data.csv"
# Fallback to ml/dataset.csv if auto_training_data doesn't exist
DATASET_PATH_FALLBACK = BASE_DIR / "ml" / "dataset.csv"
MODEL_SAVE_DIR = BASE_DIR / "ml" / "nlu_model"
LABEL_MAP_PATH = BASE_DIR / "ml" / "label_map.json"
CHECKPOINT_PATH = MODEL_SAVE_DIR / "checkpoint.pt"

# Training hyperparameters
BATCH_SIZE = 16
EPOCHS = 10
LEARNING_RATE = 2e-5
MAX_LENGTH = 64
MODEL_NAME = "distilbert-base-uncased"
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
GRADIENT_CLIP = 1.0
SEED = 42

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "ml" / "training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Reproducibility
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {DEVICE}")


# =====================================================================
#  DATASET
# =====================================================================
class NovaNLUDataset(Dataset):
    """Dataset for AMAZON AI intent classification."""

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
#  TRAINING FUNCTIONS
# =====================================================================
def train_epoch(model, dataloader, optimizer, scheduler, gradient_clip=1.0):
    """Train model for one epoch."""
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for batch_idx, batch in enumerate(dataloader):
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
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=gradient_clip)
        optimizer.step()
        scheduler.step()

        # Log progress every 50 batches
        if batch_idx % 50 == 0:
            current_lr = scheduler.get_last_lr()[0]
            logger.debug(f"Batch {batch_idx}, Loss: {loss.item():.4f}, LR: {current_lr:.2e}")

    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total
    return avg_loss, accuracy


def evaluate(model, dataloader, label_names, return_preds=False):
    """Evaluate model on validation/test set."""
    model.eval()
    all_preds = []
    all_labels = []
    total_loss = 0

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(DEVICE)
            attention_mask = batch["attention_mask"].to(DEVICE)
            labels = batch["label"].to(DEVICE)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            total_loss += loss.item()

            preds = torch.argmax(outputs.logits, dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(dataloader)
    accuracy = accuracy_score(all_labels, all_preds)
    
    # Only report on classes present in test set
    unique_labels_in_test = sorted(set(all_labels))
    target_names_for_report = [label_names[i] for i in unique_labels_in_test]
    
    report = classification_report(
        all_labels, all_preds, 
        labels=unique_labels_in_test,
        target_names=target_names_for_report,
        zero_division=0,
        digits=4
    )
    
    if return_preds:
        return accuracy, report, avg_loss, all_preds, all_labels
    return accuracy, report, avg_loss


def load_data(dataset_path):
    """Load and preprocess dataset."""
    logger.info(f"Loading dataset from: {dataset_path}")
    
    # If main dataset doesn't exist, try fallback
    if not dataset_path.exists():
        fallback = BASE_DIR / "ml" / "dataset.csv"
        if fallback.exists():
            logger.info(f"Main dataset not found, using fallback: {fallback}")
            dataset_path = fallback
        else:
            raise FileNotFoundError(f"No dataset found at {dataset_path} or {fallback}")
    
    # Try different encodings
    encodings = ['utf-8', 'latin-1', 'cp1252']
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(dataset_path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    
    if df is None:
        raise ValueError(f"Could not read dataset with any encoding: {dataset_path}")
    
    # Clean and validate data
    df = df.dropna(subset=['command', 'intent'])
    df['command'] = df['command'].astype(str).str.strip()
    df['intent'] = df['intent'].astype(str).str.strip()
    
    # Remove empty commands
    df = df[df['command'] != '']
    
    logger.info(f"Loaded {len(df)} samples, {df['intent'].nunique()} unique intents")
    
    # Show intent distribution
    intent_counts = df['intent'].value_counts()
    logger.info(f"Intent distribution:\n{intent_counts}")
    
    return df


def create_label_map(labels):
    """Create label to ID mapping."""
    unique_labels = sorted(set(labels))
    label_map = {label: idx for idx, label in enumerate(unique_labels)}
    reverse_label_map = {idx: label for label, idx in label_map.items()}
    return label_map, reverse_label_map, unique_labels


# =====================================================================
#  MAIN
# =====================================================================
def main():
    logger.info("=" * 60)
    logger.info("AMAZON AI - DistilBERT NLU Model Training")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now()}")

    # Create model directory
    MODEL_SAVE_DIR.mkdir(parents=True, exist_ok=True)

    # Load dataset
    df = load_data(DATASET_PATH)
    texts = df["command"].tolist()
    labels = df["intent"].tolist()

    # Create label map
    label_map, reverse_label_map, unique_labels = create_label_map(labels)
    logger.info(f"Number of unique intents: {len(unique_labels)}")
    logger.info(f"Intents: {unique_labels}")

    # Save label map
    with open(LABEL_MAP_PATH, "w") as f:
        json.dump({
            "label_map": label_map,
            "reverse_label_map": {str(k): v for k, v in reverse_label_map.items()},
            "intents": unique_labels,
            "num_intents": len(unique_labels),
            "created_at": datetime.now().isoformat()
        }, f, indent=2)
    logger.info(f"Label map saved to: {LABEL_MAP_PATH}")

    # Train/test split with stratification (only if all classes have >= 2 samples)
    from collections import Counter
    label_counts = Counter(labels)
    min_class_size = min(label_counts.values())
    
    if min_class_size >= 2:
        # Use stratified split
        train_texts, test_texts, train_labels, test_labels = train_test_split(
            texts, labels, 
            test_size=0.2, 
            random_state=SEED, 
            stratify=labels
        )
    else:
        # Use simple split (no stratification) for small datasets
        logger.info(f"Some classes have < 2 samples, using simple split")
        train_texts, test_texts, train_labels, test_labels = train_test_split(
            texts, labels, 
            test_size=0.2, 
            random_state=SEED
        )
    logger.info(f"Train: {len(train_texts)} samples")
    logger.info(f"Test: {len(test_texts)} samples")

    # Load tokenizer
    logger.info(f"Loading tokenizer: {MODEL_NAME}")
    tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)

    # Create datasets
    train_dataset = NovaNLUDataset(train_texts, train_labels, tokenizer, MAX_LENGTH, label_map)
    test_dataset = NovaNLUDataset(test_texts, test_labels, tokenizer, MAX_LENGTH, label_map)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # Load model
    logger.info(f"Loading model: {MODEL_NAME} ({len(unique_labels)} classes)")
    model = DistilBertForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=len(unique_labels),
    )
    model.to(DEVICE)

    # Setup optimizer
    optimizer = AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    # Setup scheduler with warmup
    total_steps = len(train_loader) * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps
    )
    logger.info(f"Total steps: {total_steps}, Warmup steps: {warmup_steps}")

    # Check for checkpoint
    start_epoch = 0
    best_accuracy = 0
    
    if CHECKPOINT_PATH.exists():
        logger.info(f"Resuming from checkpoint: {CHECKPOINT_PATH}")
        checkpoint = torch.load(str(CHECKPOINT_PATH), map_location=DEVICE, weights_only=False)
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        scheduler.load_state_dict(checkpoint["scheduler_state"])
        start_epoch = checkpoint["epoch"] + 1
        best_accuracy = checkpoint["best_accuracy"]
        logger.info(f"Resuming at epoch {start_epoch}, best accuracy: {best_accuracy:.2%}")

    # Training loop
    logger.info("\n" + "=" * 60)
    logger.info(f"Training for {EPOCHS} epochs on {DEVICE}")
    logger.info(f"Total steps: {total_steps}, Warmup: {warmup_steps}")
    logger.info("=" * 60 + "\n")

    training_history = {
        "epochs": [],
        "train_loss": [],
        "train_acc": [],
        "test_loss": [],
        "test_acc": []
    }

    for epoch in range(start_epoch, EPOCHS):
        # Train
        train_loss, train_acc = train_epoch(
            model, train_loader, optimizer, scheduler, GRADIENT_CLIP
        )
        
        # Evaluate
        test_acc, test_report, test_loss = evaluate(
            model, test_loader, unique_labels
        )

        logger.info(f"Epoch {epoch+1}/{EPOCHS} | "
                   f"Train Loss: {train_loss:.4f} | "
                   f"Train Acc: {train_acc:.2%} | "
                   f"Test Loss: {test_loss:.4f} | "
                   f"Test Acc: {test_acc:.2%}")

        # Save history
        training_history["epochs"].append(epoch + 1)
        training_history["train_loss"].append(train_loss)
        training_history["train_acc"].append(train_acc)
        training_history["test_loss"].append(test_loss)
        training_history["test_acc"].append(test_acc)

        # Save best model
        if test_acc > best_accuracy:
            best_accuracy = test_acc
            model.save_pretrained(str(MODEL_SAVE_DIR))
            tokenizer.save_pretrained(str(MODEL_SAVE_DIR))
            
            # Save best model checkpoint
            torch.save({
                "epoch": epoch,
                "best_accuracy": best_accuracy,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "scheduler_state": scheduler.state_dict(),
                "config": {
                    "model_name": MODEL_NAME,
                    "num_labels": len(unique_labels),
                    "max_length": MAX_LENGTH,
                    "batch_size": BATCH_SIZE,
                    "learning_rate": LEARNING_RATE,
                }
            }, str(MODEL_SAVE_DIR / "best_model.pt"))
            
            logger.info(f"  -> Best model saved (accuracy: {best_accuracy:.2%})")

        # Save checkpoint for resumption
        torch.save({
            "epoch": epoch,
            "best_accuracy": best_accuracy,
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict(),
        }, str(CHECKPOINT_PATH))

        # Early stopping
        if epoch > 3:
            recent_acc = training_history["test_acc"][-3:]
            if len(recent_acc) == 3 and all(acc <= best_accuracy * 0.99 for acc in recent_acc):
                logger.info(f"Early stopping at epoch {epoch+1} - no improvement in last 3 epochs")
                break

    # Final evaluation
    logger.info("\n" + "=" * 60)
    logger.info("Final Evaluation")
    logger.info("=" * 60)
    
    final_acc, final_report, final_loss, preds, true_labels = evaluate(
        model, test_loader, unique_labels, return_preds=True
    )
    
    logger.info(f"\nBest Accuracy: {best_accuracy:.2%}")
    logger.info(f"Final Accuracy: {final_acc:.2%}")
    logger.info(f"\nClassification Report:\n{final_report}")

    # Confusion matrix analysis
    cm = confusion_matrix(true_labels, preds)
    logger.info(f"\nConfusion Matrix:\n{cm}")

    # Find misclassified examples
    misclassified = []
    for i, (pred, true) in enumerate(zip(preds, true_labels)):
        if pred != true:
            misclassified.append({
                "text": test_texts[i],
                "true_label": unique_labels[true],
                "pred_label": unique_labels[pred]
            })
    
    if misclassified:
        logger.info(f"\nMisclassified examples ({len(misclassified)}):")
        for item in misclassified[:10]:  # Show first 10
            logger.info(f"  Text: '{item['text']}' -> True: {item['true_label']}, Pred: {item['pred_label']}")
    
    # Save training history
    history_path = MODEL_SAVE_DIR / "training_history.json"
    with open(history_path, "w") as f:
        json.dump({
            "history": training_history,
            "best_accuracy": best_accuracy,
            "final_accuracy": final_acc,
            "num_samples": len(texts),
            "num_intents": len(unique_labels),
            "intents": unique_labels,
            "epochs": EPOCHS,
            "completed_epochs": len(training_history["epochs"]),
            "completed_at": datetime.now().isoformat()
        }, f, indent=2)

    # Save config
    config = {
        "model_name": MODEL_NAME,
        "num_labels": len(unique_labels),
        "max_length": MAX_LENGTH,
        "batch_size": BATCH_SIZE,
        "epochs": EPOCHS,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "warmup_ratio": WARMUP_RATIO,
        "gradient_clip": GRADIENT_CLIP,
        "best_accuracy": best_accuracy,
        "final_accuracy": final_acc,
        "device": str(DEVICE),
        "dataset_size": len(texts),
        "train_size": len(train_texts),
        "test_size": len(test_texts),
        "trained_at": datetime.now().isoformat()
    }
    config_path = MODEL_SAVE_DIR / "amazon_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    logger.info(f"\nModel saved to: {MODEL_SAVE_DIR}")
    logger.info(f"Config saved to: {config_path}")
    logger.info(f"History saved to: {history_path}")
    logger.info(f"Training completed at: {datetime.now()}")
    logger.info("=" * 60)
    logger.info("✅ Training complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Training interrupted by user. Checkpoint saved.")
    except Exception as e:
        logger.error(f"\n❌ Error during training: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise