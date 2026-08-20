"""Constants and keyword maps for exercise 1."""

DANGEROUS_MESSAGE = "Error: dangerous command not allowed"
UNSUPPORTED_MESSAGE = "Error: unsupported request"
EMPTY_INPUT_MESSAGE = "Error: empty input"

INSTALL_ALL_PHRASES = (
    "install all packages",
    "add all packages",
    "install project dependencies",
    "install dependencies",
    "install the dependencies",
    "what do i need to run in order to install all packages",
    "install all deps",
    "install deps",
    "install all requirements",
    "install requirements",
)

INSTALL_WORDS = ("download", "install", "setup", "get")
RUN_WORDS = ("run", "start", "launch", "execute")
BUILD_WORDS = ("build", "compile", "make")

STOP_WORDS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "of",
    "on",
    "in",
    "my",
    "this",
    "that",
    "please",
    "how",
    "do",
    "i",
    "can",
    "you",
    "me",
    "with",
    "all",
    "latest",
    "currently",
    "project",
    "machine",
    "onto",
    "under",
    "source",
    "control",
}

EXAMPLE_TO_COMMAND = {
    "show git status": "git status",
    "show git history": "git log --oneline --decorate -n 20",
    "what is my current git branch": "git branch --show-current",
    "pull latest changes from git": "git pull",
    "get code from git": "git pull",
    "bring code from git": "git pull",
    "stage all git changes": "git add .",
    "save changes add it": "git add .",
    "push my git commits": "git push",
    "how do i put my project into git": "git init",
    "install dependencies for this project": "uv sync",
    "install package requests": "uv add requests",
    "how do i run dotnet": "dotnet run",
    "build my c# project": "dotnet build",
    "how do i download node": "winget install -e --id OpenJS.NodeJS.LTS",
    "install java": "winget install -e --id EclipseAdoptium.Temurin.21.JDK",
    "run javascript app": "node index.js",
    "compile regular c": "gcc main.c -o main",
    "compile c++ code": "g++ main.cpp -o main",
    "run rust project": "cargo run",
    "what is my ip address": "ipconfig",
    "which processes are running now": "tasklist",
    "sort files by size from largest to smallest": "dir /o-s",
}

LANGUAGE_ALIASES = {
    "python": ("python", "python3"),
    "nodejs": ("node", "nodejs", "node.js", "javascript", "js"),
    "typescript": ("typescript", "ts"),
    "dotnet": ("dotnet", ".net", "c#", "csharp"),
    "c": (" c ", "regular c", "lang c", "programming c", " c language"),
    "cpp": ("c++", "cpp", "c plus plus"),
    "java": ("java", "jdk"),
    "go": ("go", "golang"),
    "rust": ("rust", "cargo"),
    "php": ("php",),
    "ruby": ("ruby",),
    "kotlin": ("kotlin",),
}

GIT_DANGEROUS_PATTERNS = (
    "git reset --hard",
    "git clean -fd",
    "git clean -xdf",
    "git checkout --",
)
