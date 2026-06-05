# M.A.R.C.U.S. (Multi-Agent RAG & Cognitive Utility System)

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-GUI-green.svg)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-RAG-purple.svg)
![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorStore-orange.svg)

M.A.R.C.U.S. is a fully autonomous, multi-threaded AI desktop assistant engineered for deep academic and professional productivity. Built with a custom asynchronous event bus, it seamlessly orchestrates local hardware daemons, a decoupled Qt UI, and a scalable Retrieval-Augmented Generation (RAG) cognitive engine.

## 🌟 Core Architecture

Unlike standard wrapper scripts, MARCUS operates on a highly scalable, event-driven architecture designed for zero-latency UI rendering and continuous background processing.

* **Asynchronous Event Engine:** A custom `bus.emit()` system decouples the heavy cognitive load (API calls, RAG embedding, TTS synthesis) from the PySide6 main thread, ensuring the GUI never stutters.
* **Semantic Router:** Employs a dynamic LLM-based tool selector to classify user intent across 20+ custom agentic tools, preventing context-window bloat.
* **Dual-Memory Matrix:**
  * **Episodic Knowledge Graph:** Uses NetworkX and a 3D-Force HTML engine to map and visualize conversational metadata in real-time.
  * **Local RAG Document Engine:** Uses a continuous file-system watchdog to detect, chunk, and embed newly saved PDFs and code files into a local ChromaDB vector store using HuggingFace embeddings.
* **Decoupled Interface:** Features a modular "Hacker Aesthetic" UI spanning multiple independent borderless windows (Terminal, HUD, Brain Map, Timer, and Face).

## 🚀 Key Features

* **Proactive Daemons:** Continuously monitors Google Calendar and local file changes to independently initiate briefings or RAG indexing without user prompting.
* **Deep Work Protocol:** A highly strict focus mode that severs external audio/mic hardware links, clears the desktop UI, and locks the user into an active Pomodoro session.
* **Hardware-Synced Voice:** Utilizes Edge TTS and Pygame audio streaming, dynamically mapping real-time audio RMS amplitudes to the visual UI for accurate lip-syncing.
* **Full External API Integration:** Actively reads and writes to Google Calendar, Notion databases (Tasks/Shopping), and fetches live market/weather data via NewsAPI.

## 🖼️ Interface Showcase

`![Terminal View](docs\images\MARCUS_TERMINAL_IMAGE.png)`

`![Brain Matrix View](docs\images\MARCUS_BRAIN_IMAGE.png)`

## ⚙️ Local Setup & Installation

**1. Clone the repository**
```bash
git clone [https://github.com/](https://github.com/)<YOUR_USERNAME>/MARCUS-AI.git
cd MARCUS-AI