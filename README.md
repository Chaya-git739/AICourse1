# Safe CLI Command Translator

This project turns natural-language requests into safe Windows command-line commands. It accepts user input such as “what is my ip address”, “install java”, or “show git status”, and returns a matching command while blocking dangerous or destructive requests.

## Project description

The app is a Python + Gradio project designed to help users translate everyday developer prompts into safe Windows CLI commands. It uses a rule-based command resolver first, then falls back to external AI/SerpAPI logic when needed.

Key features:
- Converts common requests into commands such as git, dotnet, node, Python, package installation, and system checks.
- Blocks dangerous requests like deleting files, formatting drives, or destructive Git actions.
- Returns a risk score and match score in the UI.
- Runs locally in a browser with a simple interface.

## Project structure

- `main.py` – app logic, command detection, and Gradio interface.
- `.env.example` – example environment variables for optional AI-based fallback.
- `pyproject.toml` – project metadata and dependencies.
- `tests/test_main.py` – basic regression checks.

## Requirements

- Python 3.12+
- pip or uv
- Optional: `OPENAI_API_KEY` and `SERPAPI_API_KEY` for AI-based fallback features

## Setup

1. Open a terminal in the project root.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you use uv in this project, the alternative is:

```bash
uv sync
```

4. Create your local environment file:

```bash
copy .env.example .env
```

Then add your real keys to `.env` if you want the OpenAI/SerpAPI fallback enabled.

## Run the project

Start the app from the project root with:

```bash
python main.py
```

Then open the local Gradio page in your browser, usually:

```text
http://127.0.0.1:7860
```

## Example requests

- “what is my ip address” → `ipconfig`
- “install java” → `winget install -e --id EclipseAdoptium.Temurin.21.JDK`
- “show git status” → `git status`
- “install package requests” → `uv add requests`
- “run rust project” → `cargo run`
- “delete all files in my downloads” → blocked as unsafe

## Run the tests

```bash
python -m unittest discover -s tests
```

This checks common safe requests and confirms dangerous actions are blocked.

## Safety notes

This app is intentionally conservative. Requests that could delete files, rewrite data, or perform destructive Git operations are rejected with a safety message instead of producing a command.

## Troubleshooting

- If the app does not run, make sure your virtual environment is active and dependencies are installed.
- If AI keys are missing, the app still works in safe rule-based mode.
- If Gradio does not open, confirm you are using the correct local port.
