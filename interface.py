"""Gradio interface and runtime entrypoint for exercise 1."""

from __future__ import annotations

import gradio as gr

from .config import load_dotenv
from .translator import command_and_risk


def build_interface() -> gr.Interface:
    """Create a Gradio interface for safe request-to-command translation."""
    examples = [
        ["what is my ip address"],
        ["install java"],
        ["run rust project"],
        ["compile regular c"],
        ["i want to download visul code to the computer"],
        ["how do i download node"],
        ["what do i need to run in order to install all packages"],
        ["install package requests"],
        ["sort files by size from largest to smallest"],
        ["which processes are running now"],
        ["how do i run dotnet"],
        ["show git status"],
        ["delete all .tmp files in downloads"],
    ]

    return gr.Interface(
        fn=command_and_risk,
        inputs=gr.Textbox(
            lines=2,
            label="Natural-language request",
            placeholder="Example: what is my ip address",
        ),
        outputs=[
            gr.Textbox(label="CLI command or error"),
            gr.HTML(label="Risk level"),
        ],
        title="Safe CLI Command Translator",
        description=(
            "Transforms natural-language requests into Windows CLI commands. "
            "It uses rules first, then an AI fallback with strict safety checks. "
            "When configured, SerpAPI search evidence is used to raise risk or block commands. "
            "Requests that try to delete or modify files are blocked."
        ),
        examples=examples,
    )


def main() -> None:
    """Start the localhost Gradio app."""
    load_dotenv()
    app = build_interface()
    app.launch(server_name="127.0.0.1", server_port=7860)
