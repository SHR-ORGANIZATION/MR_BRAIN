
```markdown
# 🧠 AMAZON AI — Intelligent Desktop Assistant

> A powerful cross-platform AI desktop assistant combining **local Large Language Models (LLMs), machine learning, and system automation** into one intelligent ChatGPT-like experience.

AMAZON AI is a privacy-focused desktop assistant that runs primarily on your local machine. It combines:

- 🤖 **Local Conversational AI** using Ollama + Llama 3.2
- 🧠 **Offline Natural Language Understanding** using DistilBERT
- ⚙️ **Computer Automation**
- 📂 **Advanced File Management**
- 📄 **Document Generation**
- 🎙️ **Voice Interaction**
- 🔎 **Semantic Search**
- 📚 **Continuous Learning**

No cloud API is required for core AI functionality.

---

# 🚀 Core Features

| Feature | Description |
|---|---|
| 🤖 **AMAZON CHAT** | ChatGPT-like conversations powered by Ollama + Llama 3.2 running locally |
| ⚙️ **System Automation** | Open/close applications, execute commands, manage files and folders |
| 🔍 **Universal Search** | Search files across all drives, volumes, and mounted locations |
| 📄 **Document Generation** | Create Word, Excel, PowerPoint, PDF documents and reports |
| 🌐 **Web & Research** | Open websites, search the web, and collect information |
| 🎙️ **Voice Assistant** | Speech-to-text commands and text-to-speech responses |
| 📧 **Email Assistant** | Compose, manage and send emails |
| 🖥️ **Computer Intelligence** | Scan hardware, monitor processes and analyze system information |
| 🧠 **Auto Learning** | Learns user patterns and improves over time |

---

# 🏗️ System Architecture

```

```
                USER INPUT
            (Text / Voice Command)
                     |
                     ▼
          ┌───────────────────┐
          │   NLU ENGINE      │
          │   DistilBERT      │
          │ Intent Detection  │
          └─────────┬─────────┘
                    |
      ┌─────────────┴─────────────┐
      │                           │
      ▼                           ▼
```

SYSTEM AUTOMATION              AMAZON CHAT
│                           │
│                           ▼
│                   ┌─────────────┐
│                   │   Ollama    │
│                   │  Llama 3.2  │
│                   └─────────────┘
│                           |
▼                           ▼

COMPUTER ACTION              AI RESPONSE

```
      └─────────────┬─────────────┘
                    |
                    ▼
          UI DISPLAY + VOICE OUTPUT
```

```

---

# 📁 Project Structure

```

MR_BRAIN/

├── agent.py
├── intent_router.py
├── voice.py
├── requirements.txt

│
├── ai_assistant/
│
│   ├── core/
│   │   ├── amazon_chat.py
│   │   ├── agent_engine.py
│   │   ├── memory.py
│   │   ├── planner.py
│   │   ├── reasoning.py
│   │   ├── security.py
│   │   └── task_manager.py
│
│   ├── models/
│   │   ├── llm_manager.py
│   │   ├── ollama_client.py
│   │   └── hardware_detector.py
│
│   ├── platform/
│   │   ├── base_platform.py
│   │   ├── windows_platform.py
│   │   ├── macos_platform.py
│   │   ├── linux_platform.py
│   │   └── platform_factory.py
│
│   ├── tools/
│   │   ├── browser_tool.py
│   │   ├── file_tool.py
│   │   ├── email_tool.py
│   │   ├── code_analysis_tool.py
│   │   └── system_monitor_tool.py
│
│   └── bridge.py

├── automation/

│   ├── file_tasks.py
│   ├── file_discovery.py
│   ├── computer_indexer.py
│   ├── document_generator.py
│   ├── document_analyzer.py
│   ├── web_tasks.py
│   ├── app_tasks.py
│   └── semantic_search.py

├── ml/

│   ├── nlu_model.py
│   ├── train_nlu.py
│   ├── nlu_model/
│   └── semantic_index/

├── system/

│   ├── environment_scanner.py
│   ├── computer_scanner.py
│   ├── conversation_manager.py
│   ├── auto_learner.py
│   ├── os_commands.py
│   └── typo_corrector.py

├── ui/

│   ├── main.py
│   └── voice_ui.py

├── learning/
├── database/
├── assets/
└── installer/

```

---

# 🧠 AI Engine

## 1. Natural Language Understanding

Technology:

- DistilBERT
- HuggingFace Transformers
- PyTorch


Purpose:

- Understand user commands
- Detect user intent
- Route requests to the correct action


Example:

```

User:
"Open Chrome"

AI Understanding:

Intent:
open_app

Application:
Chrome

```

---

# 2. AMAZON CHAT Engine

Powered by:

```

Ollama
+
Llama 3.2

```

Capabilities:

- General questions
- Explanations
- Writing assistance
- Programming help
- Research assistance
- Conversation


Example:

```

User:
Explain Laravel middleware

AMAZON AI:

Laravel middleware is a filtering layer...

```

---

# 3. Automation Engine

AMAZON AI can control the computer:

### Applications

Examples:

```

Open Chrome

Close Spotify

Launch VS Code

```

---

### Files

Examples:

```

Create folder Projects

Find invoice.pdf

Delete temporary files

```

---

### System

Examples:

```

Show RAM usage

Check running processes

Analyze computer

```

---

# 📄 Document Generation

Supported formats:

| Format | Library |
|-|-|
| Word | python-docx |
| Excel | openpyxl |
| PowerPoint | python-pptx |
| PDF | reportlab |


Examples:

```

Create a research proposal about AI

Generate a business report

Create PowerPoint presentation

```

---

# 🔎 Intelligent Search

AMAZON AI supports:

- File name search
- Content search
- Semantic search
- Cross-drive indexing


Technology:

```

FAISS
+
Sentence Transformers
+
SQLite Index

```

---

# 🎙️ Voice Assistant

Features:

Input:

```

Speech → Text

```

Output:

```

Text → Speech

````

Supported:

- Windows
- macOS
- Linux


---

# 🌍 Cross Platform Support

| Capability | Windows | macOS | Linux |
|-|-|-|-|
| Drive discovery | A-Z drives | /Volumes | /mnt /media |
| App launching | PowerShell | open command | xdg-open |
| Terminal | CMD | zsh | bash |
| File management | ✅ | ✅ | ✅ |


---

# 📦 Installation

## Requirements

- Python 3.9+
- Ollama
- Minimum 8GB RAM recommended


---

## Install Dependencies

```bash
pip install -r requirements.txt
````

---

# Install Ollama

Start Ollama:

```bash
ollama serve
```

Download AI model:

```bash
ollama pull llama3.2
```

---

# Run AMAZON AI

```bash
python -m ui.main
```

---

# 🎯 Supported Intents

Currently supported:

| Intent            | Example                 |
| ----------------- | ----------------------- |
| open_app          | open chrome             |
| close_app         | close spotify           |
| create_file       | create notes.txt        |
| create_folder     | create projects folder  |
| delete_file       | delete report.pdf       |
| search_file       | find assignment         |
| find_anything     | search azampay          |
| generate_document | create report           |
| open_website      | open youtube            |
| search_web        | search python tutorials |
| amazon_chat       | explain AI              |
| greeting          | hello                   |
| system_info       | show system info        |
| send_email        | send email              |
| analyze_document  | analyze PDF             |
| retrain_model     | retrain AI              |

Total:

```
43+ intelligent intents
```

---

# 🧠 Auto Learning System

AMAZON AI improves through usage:

Process:

```
User Interaction

        ↓

Conversation Recording

        ↓

Pattern Analysis

        ↓

Training Data Update

        ↓

Model Retraining

        ↓

Improved Understanding
```

Stored in:

```
learning/
database/
```

---

# 🔐 Privacy

AMAZON AI is designed for privacy:

✅ Local AI processing
✅ No cloud API required
✅ User data stays on device
✅ Offline operation supported

---

# 🛠️ Technology Stack

| Component      | Technology                     |
| -------------- | ------------------------------ |
| AI Chat        | Ollama + Llama 3.2             |
| NLP            | DistilBERT                     |
| ML Framework   | PyTorch                        |
| Vector Search  | FAISS                          |
| GUI            | CustomTkinter                  |
| Documents      | python-docx/openpyxl/reportlab |
| System Monitor | psutil                         |
| Voice          | SpeechRecognition + TTS        |
| Packaging      | PyInstaller                    |

---

# 🔮 Future Roadmap

* Multi-agent reasoning
* Better memory system
* Computer vision
* Plugin marketplace
* Mobile companion app
* Personal AI knowledge base
* Advanced autonomous task execution

---

# 📌 Project Status

AMAZON AI is an evolving intelligent desktop assistant designed to become a complete local AI operating companion.

```
Think.
Learn.
Automate.
Assist.
```
