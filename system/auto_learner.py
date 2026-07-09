"""
Auto-Learning Engine for AMAZON AI
Continuously learns from user interactions, retrains model automatically,
and improves command understanding over time - like GPT.
"""
import json
import os
import csv
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# Storage location
LEARNING_DIR = Path(__file__).resolve().parent.parent / "learning"
USAGE_LOG_FILE = LEARNING_DIR / "usage_log.json"
PATTERNS_FILE = LEARNING_DIR / "learned_patterns.json"
STATS_FILE = LEARNING_DIR / "learning_stats.json"
CONTEXT_FILE = LEARNING_DIR / "conversation_context.json"
AUTO_TRAIN_THRESHOLD = 10  # Retrain after this many new interactions (lowered for faster learning)


class AutoLearner:
    """Continuously learns from user interactions to improve AI responses."""
    
    def __init__(self):
        self.usage_log = []
        self.learned_patterns = {}
        self.context_history = []  # Recent conversation context
        self.stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "unknown_commands": 0,
            "most_used_intents": [],
            "most_used_entities": [],
            "learning_since": None,
            "last_retrain": None,
            "new_samples_since_retrain": 0,
            "auto_retrain_enabled": True,
        }
        self._load_data()
    
    def _load_data(self):
        """Load existing learning data."""
        try:
            if USAGE_LOG_FILE.exists():
                with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
                    self.usage_log = json.load(f)
        except Exception:
            pass
        
        try:
            if PATTERNS_FILE.exists():
                with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                    self.learned_patterns = json.load(f)
        except Exception:
            pass
        
        try:
            if STATS_FILE.exists():
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    self.stats = json.load(f)
        except Exception:
            pass
        
        try:
            if CONTEXT_FILE.exists():
                with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                    self.context_history = json.load(f)
        except Exception:
            pass
    
    def _save_data(self):
        """Save learning data to disk."""
        try:
            LEARNING_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(USAGE_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.usage_log[-1000:], f, indent=2)
            
            with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.learned_patterns, f, indent=2)
            
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2)
            
            with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.context_history[-100:], f, indent=2)
        except Exception as e:
            print(f"[AutoLearner] Error saving data: {e}")
    
    def record_interaction(self, command, intent, entity, success, response=""):
        """Record a user interaction for learning."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "intent": intent,
            "entity": entity,
            "success": success,
            "response": response[:200] if response else "",
        }
        self.usage_log.append(entry)
        
        # Update context history
        self.context_history.append({
            "command": command,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Update stats
        self.stats["total_commands"] += 1
        self.stats["new_samples_since_retrain"] += 1
        
        if intent == "unknown":
            self.stats["unknown_commands"] += 1
        elif success:
            self.stats["successful_commands"] += 1
        else:
            self.stats["failed_commands"] += 1
        
        # Update most used intents
        intent_counter = Counter([e["intent"] for e in self.usage_log if e.get("intent") and e["intent"] != "unknown"])
        self.stats["most_used_intents"] = [intent for intent, _ in intent_counter.most_common(10)]
        
        # Update most used entities
        entity_counter = Counter([e["entity"] for e in self.usage_log if e.get("entity")])
        self.stats["most_used_entities"] = [entity for entity, _ in entity_counter.most_common(10)]
        
        if not self.stats["learning_since"]:
            self.stats["learning_since"] = datetime.now().isoformat()
        
        # Learn from unknown commands
        if intent == "unknown":
            self._learn_from_unknown(command)
        
        # Auto-retrain when enough new data is collected
        if (self.stats["auto_retrain_enabled"] and 
            self.stats["new_samples_since_retrain"] >= AUTO_TRAIN_THRESHOLD):
            self._auto_retrain()
        
        # Save periodically
        if self.stats["total_commands"] % 10 == 0:
            self._save_data()
    
    def _learn_from_unknown(self, command):
        """Try to learn from unknown commands by analyzing patterns."""
        cmd_lower = command.lower().strip()
        
        action_words = ["create", "make", "open", "close", "delete", "remove", 
                       "find", "search", "move", "copy", "rename", "edit", "read",
                       "empty", "clear", "clean", "show", "list", "run", "launch"]
        
        target_words = ["file", "folder", "app", "application", "document", "trash",
                       "bin", "recycle", "web", "website", "chrome", "vscode"]
        
        for action in action_words:
            if action in cmd_lower:
                for target in target_words:
                    if target in cmd_lower:
                        pattern_key = f"{action} {target}"
                        if pattern_key not in self.learned_patterns:
                            self.learned_patterns[pattern_key] = {
                                "intent": f"{action}_{target}",
                                "confidence": 0.5,
                                "times_seen": 1,
                                "first_seen": datetime.now().isoformat(),
                                "last_seen": datetime.now().isoformat(),
                                "auto_learned": True,
                            }
                        else:
                            self.learned_patterns[pattern_key]["times_seen"] += 1
                            self.learned_patterns[pattern_key]["last_seen"] = datetime.now().isoformat()
                        break
        
        # Auto-learn new app names from "open <app>" commands
        if any(cmd_lower.startswith(prefix) for prefix in ["open ", "launch ", "start "]):
            self._learn_app_name(command)
    
    def _learn_app_name(self, command):
        """Auto-learn new app names from commands."""
        import re
        from pathlib import Path
        
        cmd_lower = command.lower().strip()
        
        # Extract app name from command
        for prefix in ["open ", "launch ", "start "]:
            if cmd_lower.startswith(prefix):
                app_name = cmd_lower[len(prefix):].strip()
                
                # Remove trailing phrases
                trailing_phrases = [
                    r'\s+(on|in|with|using)\s+(a\s+)?new\s+window.*$',
                    r'\s+(on|in|with|using)\s+(a\s+)?new\s+instance.*$',
                    r'\s+please.*$',
                ]
                for phrase in trailing_phrases:
                    app_name = re.sub(phrase, '', app_name, flags=re.I).strip()
                
                # Remove filler words
                for filler in ["the", "app", "application", "program"]:
                    app_name = re.sub(r'\b' + filler + r'\b', '', app_name, flags=re.I).strip()
                
                # Only learn if it looks like an app name (not a file/folder)
                if app_name and not any(word in app_name for word in ["file", "folder", "directory", ".txt", ".pdf", ".doc"]):
                    # Store learned app name
                    learned_apps_file = LEARNING_DIR / "learned_apps.json"
                    learned_apps = {}
                    
                    try:
                        if learned_apps_file.exists():
                            with open(learned_apps_file, "r", encoding="utf-8") as f:
                                learned_apps = json.load(f)
                    except Exception:
                        pass
                    
                    # Add to learned apps
                    app_key = app_name.lower()
                    if app_key not in learned_apps:
                        learned_apps[app_key] = {
                            "display_name": app_name.title(),
                            "times_used": 1,
                            "first_seen": datetime.now().isoformat(),
                            "last_seen": datetime.now().isoformat(),
                            "auto_learned": True,
                        }
                    else:
                        learned_apps[app_key]["times_used"] += 1
                        learned_apps[app_key]["last_seen"] = datetime.now().isoformat()
                    
                    # Save learned apps
                    try:
                        LEARNING_DIR.mkdir(parents=True, exist_ok=True)
                        with open(learned_apps_file, "w", encoding="utf-8") as f:
                            json.dump(learned_apps, f, indent=2)
                    except Exception as e:
                        print(f"[AutoLearner] Error saving learned apps: {e}")
                break
    
    def _auto_retrain(self):
        """Automatically retrain the NLU model with new data."""
        try:
            temp_dataset = LEARNING_DIR / "auto_training_data.csv"
            
            with open(temp_dataset, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["command", "intent"])
                
                for pattern, data in self.learned_patterns.items():
                    if data.get("confidence", 0) >= 0.7:
                        writer.writerow([pattern, data["intent"]])
                
                for entry in self.usage_log[-100:]:
                    if entry.get("success") and entry.get("command") and entry.get("intent"):
                        if entry["intent"] != "unknown":
                            writer.writerow([entry["command"], entry["intent"]])
            
            project_root = Path(__file__).resolve().parent.parent
            train_script = project_root / "ml" / "train_nlu.py"
            
            if train_script.exists():
                checkpoint = project_root / "ml" / "nlu_model" / "checkpoint.pt"
                if checkpoint.exists():
                    checkpoint.unlink()
                
                subprocess.Popen(
                    ["python", str(train_script)],
                    cwd=str(project_root),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                
                self.stats["last_retrain"] = datetime.now().isoformat()
                self.stats["new_samples_since_retrain"] = 0
                
                print(f"[AutoLearner] Auto-retrain triggered at {self.stats['last_retrain']}")
        except Exception as e:
            print(f"[AutoLearner] Auto-retrain error: {e}")
    
    def learn_pattern(self, command_pattern, intent, confidence=1.0):
        """Learn a new command pattern."""
        pattern_key = command_pattern.lower().strip()
        
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = {
                "intent": intent,
                "confidence": confidence,
                "times_seen": 1,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            }
        else:
            self.learned_patterns[pattern_key]["times_seen"] += 1
            self.learned_patterns[pattern_key]["last_seen"] = datetime.now().isoformat()
            self.learned_patterns[pattern_key]["confidence"] = min(1.0, 
                self.learned_patterns[pattern_key]["confidence"] + 0.05)
        
        self._save_data()
    
    def get_context_aware_suggestions(self, current_command, limit=5):
        """Get suggestions based on conversation context."""
        suggestions = []
        
        recent_intents = [c["intent"] for c in self.context_history[-10:] if c.get("intent")]
        
        if recent_intents:
            most_recent = recent_intents[-1]
            related = [e["command"] for e in self.usage_log 
                      if e.get("intent") == most_recent and e.get("success")]
            if related:
                suggestions.append({
                    "type": "related",
                    "intent": most_recent,
                    "example": related[-1],
                })
        
        for intent in self.stats["most_used_intents"][:3]:
            examples = [e["command"] for e in self.usage_log 
                       if e.get("intent") == intent and e.get("success")]
            if examples:
                suggestions.append({
                    "type": "frequent",
                    "intent": intent,
                    "example": examples[-1],
                })
        
        return suggestions[:limit]
    
    def get_learning_report(self):
        """Get a summary of what the AI has learned."""
        success_rate = (self.stats['successful_commands'] / max(1, self.stats['total_commands'])) * 100
        
        return {
            "total_interactions": self.stats["total_commands"],
            "success_rate": f"{success_rate:.1f}%",
            "unknown_commands": self.stats["unknown_commands"],
            "learning_since": self.stats["learning_since"],
            "last_retrain": self.stats["last_retrain"],
            "samples_until_retrain": AUTO_TRAIN_THRESHOLD - self.stats["new_samples_since_retrain"],
            "top_intents": self.stats["most_used_intents"][:5],
            "top_entities": self.stats["most_used_entities"][:5],
            "learned_patterns": len(self.learned_patterns),
            "auto_retrain_enabled": self.stats["auto_retrain_enabled"],
        }
    
    def import_training_data(self, dataset_path):
        """Import external training data from a CSV file."""
        imported = 0
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    command = row.get("command", "").strip()
                    intent = row.get("intent", "").strip()
                    
                    if command and intent:
                        self.learn_pattern(command, intent, confidence=0.8)
                        imported += 1
            
            self._save_data()
            return f"Imported {imported} training examples"
        except Exception as e:
            return f"Error importing data: {str(e)}"
    
    def export_training_data(self, output_path):
        """Export learned patterns as training data."""
        try:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["command", "intent"])
                
                for pattern, data in self.learned_patterns.items():
                    writer.writerow([pattern, data["intent"]])
                
                for entry in self.usage_log:
                    if entry.get("success") and entry.get("command") and entry.get("intent"):
                        if entry["intent"] != "unknown":
                            writer.writerow([entry["command"], entry["intent"]])
            
            return f"Exported training data to {output_path}"
        except Exception as e:
            return f"Error exporting data: {str(e)}"
    
    def download_online_training_data(self, url):
        """Download training data from online source."""
        try:
            import urllib.request
            
            temp_file = LEARNING_DIR / "online_training_data.csv"
            urllib.request.urlretrieve(url, temp_file)
            
            result = self.import_training_data(str(temp_file))
            
            if temp_file.exists():
                temp_file.unlink()
            
            return f"Downloaded and imported: {result}"
        except Exception as e:
            return f"Error downloading data: {str(e)}"


# Global learner instance
_learner = None


def get_learner() -> AutoLearner:
    """Get the global auto-learner instance."""
    global _learner
    if _learner is None:
        _learner = AutoLearner()
    return _learner


def record_interaction(command, intent, entity, success, response=""):
    """Record a user interaction."""
    learner = get_learner()
    learner.record_interaction(command, intent, entity, success, response)


def get_suggestions(current_command="", limit=5):
    """Get command suggestions."""
    learner = get_learner()
    return learner.get_context_aware_suggestions(current_command, limit)


def get_learning_report():
    """Get learning summary."""
    learner = get_learner()
    return learner.get_learning_report()


def import_training_data(dataset_path):
    """Import external training data."""
    learner = get_learner()
    return learner.import_training_data(dataset_path)


def export_training_data(output_path):
    """Export learned patterns."""
    learner = get_learner()
    return learner.export_training_data(output_path)


def download_online_data(url):
    """Download training data from online."""
    learner = get_learner()
    return learner.download_online_training_data(url)


def force_retrain():
    """Force immediate model retraining with all learned data."""
    learner = get_learner()
    # Reset threshold to trigger retrain
    learner.stats["new_samples_since_retrain"] = AUTO_TRAIN_THRESHOLD
    learner._save_data()
    learner._auto_retrain()
    return {
        "status": "retrain_initiated",
        "message": "Model retraining started in background"
    }


def merge_learned_patterns_to_dataset():
    """Merge learned patterns into the main training dataset."""
    learner = get_learner()
    dataset_path = Path(__file__).resolve().parent.parent / "ml" / "dataset.csv"
    
    try:
        # Read existing dataset
        existing_commands = set()
        if dataset_path.exists():
            with open(dataset_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_commands.add(row.get("command", "").lower().strip())
        
        # Add new patterns
        new_count = 0
        with open(dataset_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            
            # Add learned patterns with high confidence
            for pattern, data in learner.learned_patterns.items():
                if data.get("confidence", 0) >= 0.8:
                    if pattern.lower().strip() not in existing_commands:
                        writer.writerow([pattern, data["intent"]])
                        existing_commands.add(pattern.lower().strip())
                        new_count += 1
            
            # Add successful interactions
            for entry in learner.usage_log[-500:]:
                if entry.get("success") and entry.get("command") and entry.get("intent"):
                    if entry["intent"] != "unknown":
                        cmd = entry["command"].lower().strip()
                        if cmd not in existing_commands:
                            writer.writerow([entry["command"], entry["intent"]])
                            existing_commands.add(cmd)
                            new_count += 1
        
        return {
            "status": "success",
            "new_samples_added": new_count,
            "dataset_path": str(dataset_path)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# =====================================================================
# OS COMMAND LEARNING
# =====================================================================

def get_os_command_suggestions(query):
    """Get OS command suggestions based on user query."""
    from system.os_commands import get_os_commands, get_all_actions
    
    query_lower = query.lower()
    os_commands = get_os_commands()
    
    suggestions = []
    
    # Check for keyword matches
    for action, command in os_commands.items():
        action_words = action.lower().split()
        query_words = query_lower.split()
        
        # Check if any action word matches query
        if any(word in query_words for word in action_words):
            suggestions.append({
                "action": action,
                "command": command,
                "confidence": 0.9
            })
    
    # Sort by confidence
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    
    return suggestions[:5]  # Return top 5 suggestions


def learn_os_command_usage(command, action, success):
    """Learn from OS command usage."""
    try:
        os_usage_file = LEARNING_DIR / "os_command_usage.json"
        os_usage = {}
        
        try:
            if os_usage_file.exists():
                with open(os_usage_file, "r", encoding="utf-8") as f:
                    os_usage = json.load(f)
        except Exception:
            pass
        
        action_key = action.lower()
        if action_key not in os_usage:
            os_usage[action_key] = {
                "command": command,
                "times_used": 1,
                "success_count": 1 if success else 0,
                "last_used": datetime.now().isoformat(),
            }
        else:
            os_usage[action_key]["times_used"] += 1
            if success:
                os_usage[action_key]["success_count"] += 1
            os_usage[action_key]["last_used"] = datetime.now().isoformat()
        
        # Save
        LEARNING_DIR.mkdir(parents=True, exist_ok=True)
        with open(os_usage_file, "w", encoding="utf-8") as f:
            json.dump(os_usage, f, indent=2)
        
        return True
    except Exception as e:
        print(f"[AutoLearner] Error learning OS command: {e}")
        return False


def get_popular_os_commands():
    """Get most popular OS commands based on usage."""
    try:
        os_usage_file = LEARNING_DIR / "os_command_usage.json"
        if not os_usage_file.exists():
            return []
        
        with open(os_usage_file, "r", encoding="utf-8") as f:
            os_usage = json.load(f)
        
        # Sort by times_used
        sorted_commands = sorted(
            os_usage.items(),
            key=lambda x: x[1].get("times_used", 0),
            reverse=True
        )
        
        return [
            {
                "action": action,
                "command": data["command"],
                "times_used": data["times_used"],
                "success_rate": data.get("success_count", 0) / max(data.get("times_used", 1), 1)
            }
            for action, data in sorted_commands[:10]
        ]
    except Exception:
        return []
