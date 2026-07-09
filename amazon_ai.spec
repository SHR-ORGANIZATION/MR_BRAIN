# -*- mode: python ; coding: utf-8 -*-
"""
AMAZON AI - PyInstaller Spec File
Cross-platform spec for building macOS .app and Windows .exe
"""
import sys
import os
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH) if 'SPECPATH' in dir() else Path(__file__).parent

# ─── Collect all Python source packages ──────────────────────────────────────
hiddenimports = [
    # Core
    'agent', 'intent_router', 'voice',
    # UI
    'ui', 'ui.main',
    # AI Assistant
    'ai_assistant', 'ai_assistant.bridge',
    'ai_assistant.core', 'ai_assistant.core.agent_engine',
    'ai_assistant.core.memory', 'ai_assistant.core.planner',
    'ai_assistant.core.reasoning', 'ai_assistant.core.security',
    'ai_assistant.core.task_manager',
    'ai_assistant.models', 'ai_assistant.models.hardware_detector',
    'ai_assistant.models.llm_manager', 'ai_assistant.models.ollama_client',
    'ai_assistant.platform', 'ai_assistant.platform.base_platform',
    'ai_assistant.platform.linux_platform', 'ai_assistant.platform.macos_platform',
    'ai_assistant.platform.platform_factory', 'ai_assistant.platform.windows_platform',
    'ai_assistant.tools', 'ai_assistant.tools.base_tool',
    'ai_assistant.tools.code_analysis_tool', 'ai_assistant.tools.email_tool',
    'ai_assistant.tools.file_operation_tool', 'ai_assistant.tools.system_monitor_tool',
    'ai_assistant.tools.tool_registry', 'ai_assistant.tools.web_browser_tool',
    'ai_assistant.memory', 'ai_assistant.memory.conversation_memory',
    'ai_assistant.memory.document_ingest', 'ai_assistant.memory.knowledge_retriever',
    # ML
    'ml', 'ml.nlu_model',
    # System
    'system', 'system.auto_learner', 'system.computer_scanner',
    'system.conversation_manager', 'system.environment_scanner',
    'system.os_commands', 'system.typo_corrector',
    # Automation
    'automation', 'automation.app_tasks', 'automation.computer_indexer',
    'automation.dev_tasks', 'automation.document_analyzer',
    'automation.document_generator', 'automation.document_tasks',
    'automation.file_discovery', 'automation.file_tasks',
    'automation.network_tasks', 'automation.search_tasks',
    'automation.semantic_search', 'automation.web_tasks',
    # Third-party
    'customtkinter', 'PIL', 'psutil', 'requests', 'numpy',
    'torch', 'transformers', 'sklearn', 'pandas',
    'sentence_transformers', 'faiss',
    'PyPDF2', 'docx', 'openpyxl', 'pptx', 'reportlab',
]

# ─── Data files to bundle ────────────────────────────────────────────────────
datas = [
    # Assets (icons, logos)
    (str(ROOT / 'assets'), 'assets'),
    # ML model files (required for NLU)
    (str(ROOT / 'ml' / 'label_map.json'), 'ml'),
    (str(ROOT / 'ml' / 'nlu_model' / 'config.json'), 'ml/nlu_model'),
    (str(ROOT / 'ml' / 'nlu_model' / 'amazon_config.json'), 'ml/nlu_model'),
    (str(ROOT / 'ml' / 'nlu_model' / 'nova_config.json'), 'ml/nlu_model'),
    (str(ROOT / 'ml' / 'nlu_model' / 'model.safetensors'), 'ml/nlu_model'),
    (str(ROOT / 'ml' / 'nlu_model' / 'vocab.txt'), 'ml/nlu_model'),
    (str(ROOT / 'ml' / 'nlu_model' / 'tokenizer_config.json'), 'ml/nlu_model'),
    (str(ROOT / 'ml' / 'nlu_model' / 'special_tokens_map.json'), 'ml/nlu_model'),
    # Semantic index
    (str(ROOT / 'ml' / 'semantic_index' / 'metadata.json'), 'ml/semantic_index'),
    (str(ROOT / 'ml' / 'semantic_index' / 'vectors.faiss'), 'ml/semantic_index'),
    # Database & learning (initial empty/state files)
    (str(ROOT / 'database' / 'chat_sessions.json'), 'database'),
    (str(ROOT / 'cache' / 'environment_index.json'), 'cache'),
]

# Include learning files if they exist
learning_dir = ROOT / 'learning'
if learning_dir.exists():
    for f in learning_dir.iterdir():
        if f.is_file():
            datas.append((str(f), 'learning'))

# ─── Platform-specific settings ──────────────────────────────────────────────
is_mac = sys.platform == 'darwin'
is_win = sys.platform == 'win32'

a = Analysis(
    [str(ROOT / 'ui' / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'IPython', 'notebook',
        'pytest', 'setuptools', 'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ─── Executable ──────────────────────────────────────────────────────────────
# Use onedir mode: no 2GB extraction on launch (fixes macOS disk-write kill)
icon_path = str(ROOT / 'assets' / 'nova_icon.ico')

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir: binaries go into COLLECT, not the exe
    name='AMAZON AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,           # No terminal window
    disable_windowed_traceback=False,
    argv_emulation=is_mac,   # macOS: handle file open events
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if (is_win or is_mac) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='AMAZON AI',
)

# ─── macOS .app bundle ──────────────────────────────────────────────────────
if is_mac:
    app = BUNDLE(
        coll,
        name='AMAZON AI.app',
        icon=icon_path,
        bundle_identifier='com.amazon.ai.assistant',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSMicrophoneUsageDescription': 'AMAZON AI needs microphone access for voice commands.',
            'NSSpeechRecognitionUsageDescription': 'AMAZON AI uses speech recognition for voice input.',
        },
    )
