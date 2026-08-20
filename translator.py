"""Core command translation and safety logic for exercise 1."""

from __future__ import annotations

import json
import re
from typing import Optional, Tuple
from urllib import error, parse, request

from .config import get_openai_api_key, get_serpapi_api_key
from .constants import (
    BUILD_WORDS,
    DANGEROUS_MESSAGE,
    EMPTY_INPUT_MESSAGE,
    EXAMPLE_TO_COMMAND,
    GIT_DANGEROUS_PATTERNS,
    INSTALL_ALL_PHRASES,
    INSTALL_WORDS,
    LANGUAGE_ALIASES,
    RUN_WORDS,
    STOP_WORDS,
    UNSUPPORTED_MESSAGE,
)

TOKEN_PATTERN = re.compile(r"[a-z0-9.+#\u0590-\u05FF]+")


def normalize(text: str) -> str:
    """Return a lowercase, trimmed version of user input."""
    normalized = text.strip().lower()
    synonym_map = {
        "deps": "dependencies",
        "dependancies": "dependencies",
        "cmd": "command",
        "v s code": "vs code",
        "node js": "nodejs",
        "pyhton": "python",
        "pyton": "python",
        "pytron": "python",
        "reglaur c": "regular c",
        "c sharp": "c#",
        "source control": "git",
        "libs": "dependencies",
        "biggest": "largest",
    }
    for source, target in synonym_map.items():
        normalized = normalized.replace(source, target)
    return normalized


def extract_package_name(text: str) -> str:
    """Extract a package name from free text like 'install package requests'."""
    markers = (
        "install package ",
        "install the package ",
        "add package ",
        "add the package ",
        "install ",
        "add ",
    )
    for marker in markers:
        if marker in text:
            candidate = text.split(marker, 1)[1].strip()
            candidate = candidate.split(" and ", 1)[0].strip()
            candidate = candidate.split(" for ", 1)[0].strip()
            candidate = candidate.rstrip("?.!,")
            if candidate and " " not in candidate:
                return candidate
    return ""


def extract_folder_name(text: str) -> str:
    """Extract a folder name from request text; fallback to a safe default."""
    if text.startswith("mkdir "):
        candidate = text.split("mkdir ", 1)[1].strip()
        candidate = candidate.split(" ", 1)[0].strip().rstrip("?.!,")
        candidate = re.sub(r"[^a-zA-Z0-9._-]", "_", candidate)
        if candidate:
            return candidate

    markers = ("folder ", "directory ", "named ", "called ")
    for marker in markers:
        if marker in text:
            candidate = text.split(marker, 1)[1].strip()
            candidate = candidate.split(" in ", 1)[0].strip()
            candidate = candidate.split(" under ", 1)[0].strip()
            candidate = candidate.split(" on ", 1)[0].strip()
            candidate = candidate.rstrip("?.!,")
            candidate = re.sub(r"^(named|called)[_\s-]+", "", candidate)
            candidate = re.sub(r"[^a-zA-Z0-9._-]", "_", candidate)
            if candidate:
                return candidate
    return "new_folder"


def intent_tokens(text: str) -> set[str]:
    """Return normalized tokens for lightweight semantic intent matching."""
    tokens = set(TOKEN_PATTERN.findall(normalize(text)))
    return {token for token in tokens if token and token not in STOP_WORDS}


def example_based_command(text: str) -> Optional[str]:
    """Map paraphrased requests to known commands using token overlap scoring."""
    query_tokens = intent_tokens(text)
    if not query_tokens:
        return None

    best_command: Optional[str] = None
    best_score = 0.0
    for example, command in EXAMPLE_TO_COMMAND.items():
        example_tokens = intent_tokens(example)
        if not example_tokens:
            continue
        overlap = len(query_tokens & example_tokens)
        if overlap == 0:
            continue
        union = len(query_tokens | example_tokens)
        score = overlap / union if union else 0.0
        if overlap >= 2:
            score += 0.15
        if any(token in query_tokens for token in ("git", "node", "dotnet", "java", "python")):
            score += 0.05
        if score > best_score:
            best_score = score
            best_command = command

    # Require stronger evidence to avoid unrelated command matches.
    if best_score >= 0.55:
        return best_command
    return None


def is_dangerous_request(text: str) -> bool:
    """Block requests that can delete or modify files."""
    danger_keywords = (
        "delete",
        "del ",
        "remove",
        "rm ",
        "erase",
        "modify",
        "edit",
        "update",
        "replace",
        "rename",
        "move",
        "copy",
        "write",
        "create file",
        "truncate",
        "format",
        "מחק",
        "למחוק",
        "שנה",
        "לשנות",
        "ערוך",
        "עדכן",
        "החלף",
        "שנה שם",
        "העבר",
        "העתק",
        "צור קובץ",
        "פרמט",
    )
    if any(keyword in text for keyword in danger_keywords):
        return True
    return any(pattern in text for pattern in GIT_DANGEROUS_PATTERNS)


def is_vscode_install_request(text: str) -> bool:
    """Detect requests to download/install Visual Studio Code."""
    asks_install = any(word in text for word in ("download", "install", "setup", "התקן", "להתקין"))
    mentions_vscode = any(
        word in text
        for word in (
            "visual studio code",
            "visual code",
            "visul code",
            "vs code",
            "vscode",
        )
    )
    return asks_install and mentions_vscode


def is_run_python_web_request(text: str) -> bool:
    """Detect requests about running the local Python web app/site."""
    run_words = ("run", "start", "launch", "open", "how do i run", "איך להריץ")
    web_words = ("website", "web app", "site", "localhost", "שרת", "אתר")
    python_words = ("python", "pytron", "pyton")
    asks_run = any(word in text for word in run_words)
    mentions_web = any(word in text for word in web_words)
    mentions_python = any(word in text for word in python_words)
    return asks_run and (mentions_web or mentions_python)


def is_run_dotnet_request(text: str) -> bool:
    """Detect requests about running a local .NET app."""
    run_words = ("run", "start", "launch", "open", "how do i run", "איך להריץ")
    dotnet_words = ("dotnet", ".net", "c#", "csproj")
    asks_run = any(word in text for word in run_words)
    mentions_dotnet = any(word in text for word in dotnet_words)
    return asks_run and mentions_dotnet


def is_build_dotnet_request(text: str) -> bool:
    """Detect requests about building a local .NET project."""
    build_words = ("build", "compile", "איך לבנות", "לקמפל")
    dotnet_words = ("dotnet", ".net", "c#", "csproj")
    asks_build = any(word in text for word in build_words)
    mentions_dotnet = any(word in text for word in dotnet_words)
    return asks_build and mentions_dotnet


def is_node_install_request(text: str) -> bool:
    """Detect requests to install/download Node.js."""
    install_words = ("download", "install", "setup", "get")
    node_words = ("node", "nodejs", "node.js")
    asks_install = any(word in text for word in install_words)
    mentions_node = any(word in text for word in node_words)
    return asks_install and mentions_node


def is_python_install_request(text: str) -> bool:
    """Detect requests to install/download Python."""
    install_words = ("download", "install", "setup", "get")
    python_words = ("python", "python3", "python 3")
    asks_install = any(word in text for word in install_words)
    mentions_python = any(word in text for word in python_words)
    return asks_install and mentions_python


def is_project_dependencies_request(text: str) -> bool:
    """Detect requests that ask to install project dependencies."""
    asks_install = any(word in text for word in ("install", "add", "setup"))
    mentions_deps = any(word in text for word in ("dependencies", "requirements", "packages"))
    mentions_scope = any(word in text for word in ("project", "this project", "for project", "for this project", "all"))
    return asks_install and mentions_deps and mentions_scope


def mentions_language(text: str, language: str) -> bool:
    """Check whether free text mentions a specific programming language."""
    aliases = LANGUAGE_ALIASES.get(language, ())
    if language in ("c", "go"):
        padded = f" {text} "
        if language == "c" and ("c#" in text or "csharp" in text):
            return False
        return any(alias in padded for alias in aliases)
    if language == "java":
        tokens = set(re.findall(r"[a-z0-9.+#]+", text))
        return "java" in tokens or "jdk" in tokens
    return any(alias in text for alias in aliases)


def resolve_language_command(text: str) -> Optional[str]:
    """Return install/build/run commands for common programming languages."""
    asks_install = any(word in text for word in INSTALL_WORDS)
    asks_run = any(word in text for word in RUN_WORDS)
    asks_build = any(word in text for word in BUILD_WORDS)

    if asks_install:
        if mentions_language(text, "python"):
            return "winget install -e --id Python.Python.3.13"
        if mentions_language(text, "nodejs"):
            return "winget install -e --id OpenJS.NodeJS.LTS"
        if mentions_language(text, "typescript"):
            return "npm install -g typescript"
        if mentions_language(text, "dotnet"):
            return "winget install -e --id Microsoft.DotNet.SDK.8"
        if mentions_language(text, "java"):
            return "winget install -e --id EclipseAdoptium.Temurin.21.JDK"
        if mentions_language(text, "go"):
            return "winget install -e --id GoLang.Go"
        if mentions_language(text, "rust"):
            return "winget install -e --id Rustlang.Rustup"
        if mentions_language(text, "php"):
            return "winget install -e --id PHP.PHP"
        if mentions_language(text, "ruby"):
            return "winget install -e --id RubyInstallerTeam.Ruby"
        if mentions_language(text, "kotlin"):
            return "winget install -e --id JetBrains.Kotlin"
        if mentions_language(text, "c") or mentions_language(text, "cpp"):
            return "winget install -e --id LLVM.LLVM"

    if asks_build:
        if mentions_language(text, "dotnet"):
            return "dotnet build"
        if mentions_language(text, "java"):
            return "javac Main.java"
        if mentions_language(text, "c"):
            return "gcc main.c -o main"
        if mentions_language(text, "cpp"):
            return "g++ main.cpp -o main"
        if mentions_language(text, "go"):
            return "go build"
        if mentions_language(text, "rust"):
            return "cargo build"
        if mentions_language(text, "typescript"):
            return "npm run build"
        if mentions_language(text, "python"):
            return "python -m compileall ."
        if mentions_language(text, "php"):
            return "php -l index.php"
        if mentions_language(text, "ruby"):
            return "ruby -c main.rb"
        if mentions_language(text, "kotlin"):
            return "kotlinc main.kt -include-runtime -d main.jar"

    if asks_run:
        if mentions_language(text, "python"):
            return "python main.py"
        if mentions_language(text, "dotnet"):
            return "dotnet run"
        if mentions_language(text, "java"):
            return "java Main"
        if mentions_language(text, "c") or mentions_language(text, "cpp"):
            return ".\\main.exe"
        if mentions_language(text, "go"):
            return "go run ."
        if mentions_language(text, "rust"):
            return "cargo run"
        if mentions_language(text, "typescript"):
            return "npx ts-node index.ts"
        if mentions_language(text, "nodejs"):
            return "node index.js"
        if mentions_language(text, "php"):
            return "php index.php"
        if mentions_language(text, "ruby"):
            return "ruby main.rb"
        if mentions_language(text, "kotlin"):
            return "java -jar main.jar"

    return None


def resolve_git_command(text: str) -> Optional[str]:
    """Resolve common Git-related requests into CLI commands."""
    mentions_git = "git" in text or "repo" in text or "repository" in text
    if (
        "save changes" in text
        or "add it" in text
        or "stage" in text
        or "add files" in text
    ):
        return "git add ."

    if not mentions_git:
        return None

    if "push" in text:
        return "git push"

    if "current" in text and "branch" in text:
        return "git branch --show-current"

    if "switch" in text and "branch" in text:
        return "git switch <branch-name>"

    if "branches" in text or "list branch" in text:
        return "git branch -a"

    if "clone" in text:
        return "git clone <repo-url>"

    if (
        "pull" in text
        or "update from remote" in text
        or "get code from git" in text
        or "bring code from git" in text
        or ("get" in text and "code" in text and "git" in text)
        or ("bring" in text and "code" in text and "git" in text)
    ):
        return "git pull"

    if "stage" in text or "add files" in text or ("save" in text and "changes" in text):
        return "git add ."

    if "fetch" in text:
        return "git fetch --all --prune"

    if "diff" in text:
        return "git diff"

    if any(word in text for word in ("status", "state", "changes")):
        return "git status"

    if "commit" in text:
        return "git commit -m \"your message\""

    if "init" in text:
        return "git init"

    if "remote" in text:
        return "git remote -v"

    if (
        "put my project into git" in text
        or "put project into git" in text
        or "connect project to git" in text
        or "start git for this project" in text
        or "initialize git" in text
        or "init git" in text
        or "git repository" in text
    ):
        return "git init"

    if any(word in text for word in ("history", "log", "commits")):
        return "git log --oneline --decorate -n 20"

    return None


def risk_color(risk: int) -> str:
    """Return the display color for a risk score from 1 to 10."""
    if risk < 3:
        return "#1f9d55"
    if 3 <= risk <= 5:
        return "#d4a017"
    if 5 < risk < 8:
        return "#f08c00"
    return "#d62828"


def risk_badge(risk: int, match_score: float) -> str:
    """Render color-coded risk and match score as HTML."""
    color = risk_color(risk)
    match_percent = round(match_score * 100)
    return (
        "<div style='font-weight:700;font-size:1.05rem;'>"
        f"Risk: <span style='color:{color}'>{risk}/10</span>"
        f" | Match: <span>{match_percent}%</span>"
        "</div>"
    )


def command_intent_keywords(command: str) -> set[str]:
    """Return intent keywords that should align with the request text."""
    text = command.lower().strip()
    if text.startswith("git add"):
        return {"git", "add", "stage", "save", "changes", "הוסף", "שינויים"}
    if text.startswith("git commit"):
        return {"git", "commit", "save", "changes", "קומיט"}
    if text.startswith("git fetch"):
        return {"git", "fetch", "remote", "update"}
    if text.startswith("git diff"):
        return {"git", "diff", "changes", "difference"}
    if text.startswith("git clone"):
        return {"git", "clone", "repository", "repo"}
    if text.startswith("git switch"):
        return {"git", "switch", "branch"}
    if text.startswith("git remote"):
        return {"git", "remote", "repository", "repo"}
    if text.startswith("git branch --show-current"):
        return {"git", "branch", "current"}
    if text.startswith("git status"):
        return {"git", "status", "changes"}
    if text.startswith("git pull"):
        return {"git", "pull", "remote"}
    if text.startswith("git push"):
        return {"git", "push", "remote"}
    if text.startswith("git init"):
        return {"git", "init", "repository"}
    if text.startswith("winget install") and "nodejs" in text:
        return {"install", "node", "nodejs", "download", "התקן", "להתקין"}
    if text.startswith("winget install") and "python" in text:
        return {"install", "python", "download", "התקן", "להתקין"}
    if text.startswith("winget install") and "visualstudiocode" in text:
        return {"install", "vscode", "visual", "code", "download", "התקן", "להתקין"}
    if text.startswith("dotnet run"):
        return {"dotnet", "run", "c#", "start", "launch", "הרץ", "להריץ"}
    if text.startswith("dotnet build"):
        return {"dotnet", "build", "compile", "c#", "לקמפל", "לבנות"}
    if text.startswith("python main.py"):
        return {"python", "run", "start", "launch", "web", "website", "app", "localhost", "הרץ", "להריץ", "אתר", "שרת"}
    if text.startswith("uv run python"):
        return {"uv", "python", "run", "start", "launch", "web", "website", "app", "localhost", "הרץ", "להריץ", "אתר", "שרת"}
    if text.startswith("uv sync"):
        return {"install", "dependencies", "project", "packages", "התקן", "תלויות", "חבילות"}
    if text.startswith("uv add"):
        return {"install", "add", "package", "dependency", "חבילה", "התקן"}
    if text.startswith("mkdir "):
        return {"create", "folder", "directory", "mkdir", "צור", "תיקיה", "ספריה"}
    if text.startswith("ipconfig"):
        return {"ip", "address", "network", "כתובת", "רשת", "מחשב"}
    if text.startswith("tasklist"):
        return {"process", "processes", "running", "תהליכים", "רץ", "רצים", "מערכת"}
    if text.startswith("dir /o-s"):
        return {"sort", "files", "size", "largest", "סדר", "קבצים", "גודל", "הכי"}
    if text.startswith("node "):
        return {"node", "javascript", "run"}
    if text.startswith("cargo run"):
        return {"rust", "run", "start", "launch"}
    if text.startswith("go run"):
        return {"go", "golang", "run", "start", "launch"}
    if text.startswith("java "):
        return {"java", "run", "start", "launch"}
    if text.startswith("javac "):
        return {"java", "build", "compile", "jdk"}
    if text.startswith("gcc "):
        return {"c", "compile", "build"}
    if text.startswith("g++ "):
        return {"c++", "cpp", "compile", "build"}

    command_tokens = set(re.findall(r"[a-z0-9.+#-]+", text))
    return {token for token in command_tokens if token not in {"-e", "--id"}}


def request_command_match_score(user_text: str, command: str) -> float:
    """Score how close a request is to the selected command, between 0 and 1."""
    if command.lower().startswith("error:"):
        return 0.0

    request_tokens = intent_tokens(user_text)
    command_tokens = command_intent_keywords(command)
    if not request_tokens or not command_tokens:
        return 0.0

    overlap = len(request_tokens & command_tokens)
    score = overlap / len(command_tokens)

    # Small boost for action verbs alignment.
    has_install = "install" in request_tokens and "install" in command_tokens
    has_run = "run" in request_tokens and "run" in command_tokens
    has_build = "build" in request_tokens and "build" in command_tokens
    if has_install or has_run or has_build:
        score += 0.1

    return min(score, 1.0)


def fetch_serpapi_snippets(command: str) -> list[str]:
    """Fetch short web snippets about the command using SerpAPI."""
    payload = fetch_serpapi_payload(f"windows command safety {command}", num_results=5)
    if not payload:
        return []

    snippets: list[str] = []
    for item in payload.get("organic_results", [])[:5]:
        title = str(item.get("title", ""))
        snippet = str(item.get("snippet", ""))
        if title or snippet:
            snippets.append(f"{title} {snippet}".strip().lower())
    return snippets


def web_risk_signal(command: str) -> int:
    """Estimate risk from web snippets; returns 0 when unavailable."""
    snippets = fetch_serpapi_snippets(command)
    if not snippets:
        return 0

    corpus = " ".join(snippets)
    high_risk_terms = (
        "delete",
        "remove",
        "erase",
        "format",
        "overwrite",
        "destructive",
        "dangerous",
        "recursive",
        "permanently",
        "wipe",
        "registry",
    )
    medium_risk_terms = (
        "admin",
        "administrator",
        "privilege",
        "security",
        "execution policy",
        "script",
    )
    low_risk_terms = (
        "list",
        "display",
        "show",
        "read-only",
        "status",
        "information",
    )

    high_hits = sum(1 for term in high_risk_terms if term in corpus)
    medium_hits = sum(1 for term in medium_risk_terms if term in corpus)
    low_hits = sum(1 for term in low_risk_terms if term in corpus)

    if high_hits >= 2:
        return 9
    if high_hits == 1:
        return 7
    if medium_hits >= 2:
        return 6
    if low_hits >= 2:
        return 2
    return 0


def fetch_serpapi_payload(query: str, num_results: int = 5) -> dict:
    """Fetch SerpAPI payload for a query; returns empty dict when unavailable."""
    api_key = get_serpapi_api_key()
    if not api_key:
        return {}

    params = parse.urlencode(
        {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": num_results,
        }
    )
    url = f"https://serpapi.com/search.json?{params}"

    try:
        with request.urlopen(url, timeout=6) as response:
            return json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return {}


def extract_command_candidates_from_text(text: str) -> list[str]:
    """Extract likely CLI command candidates from free text snippets."""
    patterns = (
        r"winget install -e --id [a-zA-Z0-9._-]+",
        r"uv add [a-zA-Z0-9._-]+",
        r"uv sync",
        r"uv run python [a-zA-Z0-9._\\/-]+",
        r"dotnet run",
        r"dotnet build",
        r"pip install [a-zA-Z0-9._-]+",
        r"python -m pip install [a-zA-Z0-9._-]+",
        r"npm install(?: -g)? [a-zA-Z0-9._-]+",
        r"ipconfig",
        r"tasklist",
        r"dir /o-s",
    )
    combined = re.compile("|".join(f"({pattern})" for pattern in patterns), re.IGNORECASE)
    seen: set[str] = set()
    candidates: list[str] = []
    for match in combined.finditer(text):
        value = match.group(0).strip()
        normalized_value = re.sub(r"\s+", " ", value)
        lower_value = normalized_value.lower()
        if lower_value not in seen:
            seen.add(lower_value)
            candidates.append(normalized_value)
    return candidates


def serpapi_command_fallback(user_text: str) -> Optional[str]:
    """Use SerpAPI to discover likely command examples for unknown requests."""
    payload = fetch_serpapi_payload(f"windows command: {user_text}", num_results=8)
    if not payload:
        return None

    text_parts: list[str] = []
    answer_box = payload.get("answer_box", {})
    for key in ("answer", "snippet", "title"):
        value = answer_box.get(key)
        if isinstance(value, str) and value.strip():
            text_parts.append(value)

    for item in payload.get("organic_results", [])[:8]:
        for key in ("title", "snippet"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                text_parts.append(value)

    corpus = "\n".join(text_parts)
    if not corpus:
        return None

    for candidate in extract_command_candidates_from_text(corpus):
        normalized_candidate = normalize(candidate)
        if is_dangerous_request(normalized_candidate):
            continue
        if is_allowed_command(candidate):
            return candidate
    return None


def risk_from_command(command: str) -> int:
    """Return risk score based on the resulting command string."""
    text = command.strip().lower()
    if text == DANGEROUS_MESSAGE.lower():
        return 10
    if text.startswith("winget install"):
        return 5
    if text.startswith("npm install"):
        return 4
    if text.startswith("git status") or text.startswith("git log") or text.startswith("git branch"):
        return 2
    if text.startswith("git diff") or text.startswith("git fetch") or text.startswith("git pull"):
        return 4
    if text.startswith("git clone"):
        return 4
    if text.startswith("git add") or text.startswith("git commit") or text.startswith("git push"):
        return 6
    if text.startswith("git switch"):
        return 4
    if text.startswith("javac ") or text.startswith("java "):
        return 4
    if text.startswith("gcc ") or text.startswith("g++ "):
        return 4
    if text.startswith("go ") or text.startswith("cargo "):
        return 4
    if text.startswith("php ") or text.startswith("ruby "):
        return 4
    if text.startswith("kotlinc "):
        return 4
    if text.startswith("npx ") or text.startswith("node "):
        return 4
    if text.startswith("mkdir "):
        return 3
    if text.startswith(".\\"):
        return 4
    if text.startswith("uv sync") or text.startswith("uv add"):
        return 3
    if text.startswith("uv run") or text.startswith("python "):
        return 4
    if text.startswith("dotnet run"):
        return 4
    if text.startswith("dotnet build"):
        return 4
    if text.startswith("tasklist") or text.startswith("dir "):
        return 2
    if text.startswith("ipconfig"):
        return 1
    if text.startswith("error:"):
        return 1
    return 4


def is_allowed_command(command: str) -> bool:
    """Allow only safe single commands in known families."""
    text = command.strip().lower()
    if not text:
        return False

    if any(token in text for token in ("&&", "||", "|", ";", ">", "<")):
        return False

    if any(pattern in text for pattern in GIT_DANGEROUS_PATTERNS):
        return False

    blocked_starts = (
        "del ",
        "erase ",
        "rm ",
        "rmdir ",
        "remove-item",
        "set-content",
        "add-content",
        "ren ",
        "rename-item",
        "move ",
        "copy ",
        "copy-item",
        "format ",
    )
    if any(text.startswith(prefix) for prefix in blocked_starts):
        return False

    allowed_starts = (
        "ipconfig",
        "tasklist",
        "dir ",
        "uv ",
        "winget ",
        "dotnet ",
        "git ",
        "python ",
        "npm ",
        "npx ",
        "node ",
        "java ",
        "javac ",
        "gcc ",
        "g++ ",
        "go ",
        "cargo ",
        "php ",
        "ruby ",
        "kotlinc ",
        "mkdir ",
        ".\\",
        "pip ",
        "start ",
    )
    return any(text.startswith(prefix) for prefix in allowed_starts)


def validate_candidate_command(candidate: str, user_text: str) -> Optional[str]:
    """Validate fallback command candidate and enforce safety policy."""
    normalized_candidate = normalize(candidate)
    if normalized_candidate == DANGEROUS_MESSAGE.lower():
        return DANGEROUS_MESSAGE
    if is_dangerous_request(normalized_candidate):
        return DANGEROUS_MESSAGE
    if request_command_match_score(user_text, candidate) < 0.20:
        return None
    if is_allowed_command(candidate):
        return candidate
    return None


def resolve_rule_based_command(text: str) -> Optional[str]:
    """Resolve deterministic command mappings from normalized text."""
    git_command = resolve_git_command(text)
    if git_command:
        return git_command

    language_command = resolve_language_command(text)
    if language_command:
        return language_command

    if is_vscode_install_request(text):
        return "winget install -e --id Microsoft.VisualStudioCode"

    if is_node_install_request(text):
        return "winget install -e --id OpenJS.NodeJS.LTS"

    if is_python_install_request(text):
        return "winget install -e --id Python.Python.3.13"

    if is_project_dependencies_request(text):
        return "uv sync"

    if is_run_python_web_request(text):
        return "uv run python main.py"

    if is_run_dotnet_request(text):
        return "dotnet run"

    if is_build_dotnet_request(text):
        return "dotnet build"

    if "ip" in text or "כתובת" in text:
        return "ipconfig"

    if "size" in text and ("sort" in text or "סדר" in text):
        return "dir /o-s"

    if "process" in text or "תהליכים" in text:
        return "tasklist"

    if any(phrase in text for phrase in INSTALL_ALL_PHRASES):
        return "uv sync"

    if (
        "create folder" in text
        or "create a folder" in text
        or "new folder" in text
        or "make folder" in text
        or "make a folder" in text
        or "create directory" in text
        or "create a directory" in text
        or "make directory" in text
        or "make a directory" in text
        or "mkdir" in text
    ):
        folder_name = extract_folder_name(text)
        return f"mkdir {folder_name}"

    package_name = extract_package_name(text)
    if package_name:
        return f"uv add {package_name}"

    # Last deterministic fallback: infer nearest known intent from examples.
    return example_based_command(text)


def llm_command_fallback(user_text: str) -> Optional[str]:
    """Use OpenAI to translate free text into one safe Windows command."""
    api_key = get_openai_api_key()
    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Convert user text to one Windows CLI command only. "
                        "No markdown. No explanations. "
                        "If request asks to delete or modify files, return exactly: "
                        f"{DANGEROUS_MESSAGE}. "
                        "Prefer uv for Python project commands. "
                        "Examples: install all packages -> uv sync; "
                        "install package requests -> uv add requests; "
                        "run this Python web app -> uv run python main.py."
                    ),
                },
                {"role": "user", "content": user_text},
            ],
        )
    except Exception:
        return None

    output = getattr(response, "output_text", "")
    if not output:
        return None

    first_line = next((line.strip() for line in output.splitlines() if line.strip()), "")
    return first_line or None


def command_and_risk(user_text: str) -> Tuple[str, str]:
    """Map text to a command and return a separate colored risk display."""
    command = to_safe_command(user_text)
    risk = risk_from_command(command)
    match_score = request_command_match_score(user_text, command)

    if not command.lower().startswith("error:"):
        web_risk = web_risk_signal(command)
        if web_risk >= 8:
            command = DANGEROUS_MESSAGE
            risk = 10
            match_score = request_command_match_score(user_text, command)
        elif web_risk > 0:
            risk = max(risk, web_risk)

    return command, risk_badge(risk, match_score)


def to_safe_command(user_text: str) -> str:
    """Map safe natural-language intents to Windows CLI commands."""
    text = normalize(user_text)
    if not text:
        return EMPTY_INPUT_MESSAGE

    if is_dangerous_request(text):
        return DANGEROUS_MESSAGE

    deterministic = resolve_rule_based_command(text)
    if deterministic:
        return deterministic

    candidate = serpapi_command_fallback(user_text)
    if candidate:
        validated = validate_candidate_command(candidate, user_text)
        if validated:
            return validated

    candidate = llm_command_fallback(user_text)
    if candidate:
        validated = validate_candidate_command(candidate, user_text)
        if validated:
            return validated

    return UNSUPPORTED_MESSAGE
