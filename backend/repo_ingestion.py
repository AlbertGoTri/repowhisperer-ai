"""
RepoWhisperer — Repo Ingestion Service

Clones a GitHub repository, parses files, and prepares them
for indexing into DigitalOcean Gradient AI Knowledge Base.
"""

import os
import hashlib
import shutil
import asyncio
from pathlib import Path
from typing import Optional
from git import Repo
from config import get_settings

# File extensions to index, mapped to language names
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript-react",
    ".jsx": "javascript-react",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c-header",
    ".hpp": "cpp-header",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".vue": "vue",
    ".svelte": "svelte",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".md": "markdown",
    ".txt": "text",
    ".dockerfile": "dockerfile",
    ".tf": "terraform",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
}

# Directories to always skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", "out", ".cache",
    "coverage", ".nyc_output", "vendor", "target", ".gradle",
    "bin", "obj", ".idea", ".vscode", ".vs", "packages",
}

# Max file size to index (500KB)
MAX_FILE_SIZE = 500 * 1024


def generate_repo_id(repo_url: str) -> str:
    """Generate a deterministic ID from a repo URL."""
    return hashlib.sha256(repo_url.encode()).hexdigest()[:12]


def parse_github_url(repo_url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    url = repo_url.rstrip("/").rstrip(".git")
    parts = url.split("/")
    owner = parts[-2]
    name = parts[-1]
    return owner, name


async def clone_repo(repo_url: str) -> tuple[str, str]:
    """
    Clone a GitHub repository to a local directory.
    Returns (repo_id, local_path).
    """
    settings = get_settings()
    repo_id = generate_repo_id(repo_url)
    _, repo_name = parse_github_url(repo_url)
    local_path = os.path.join(settings.repos_dir, f"{repo_id}_{repo_name}")

    # Remove existing clone if present
    if os.path.exists(local_path):
        shutil.rmtree(local_path)

    os.makedirs(settings.repos_dir, exist_ok=True)

    # Clone in a thread to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: Repo.clone_from(repo_url, local_path, depth=1)
    )

    return repo_id, local_path


def get_file_language(file_path: str) -> Optional[str]:
    """Determine file language from extension."""
    ext = Path(file_path).suffix.lower()

    # Special case for Dockerfile
    if Path(file_path).name.lower() in ("dockerfile", "dockerfile.dev", "dockerfile.prod"):
        return "dockerfile"

    return LANGUAGE_MAP.get(ext)


def scan_repo_files(local_path: str) -> list[dict]:
    """
    Scan a cloned repo and extract indexable files.
    Returns list of {path, content, language, size}.
    """
    files = []
    repo_root = Path(local_path)

    for file_path in repo_root.rglob("*"):
        # Skip directories
        if file_path.is_dir():
            continue

        # Skip if any parent dir is in skip list
        if any(part in SKIP_DIRS for part in file_path.relative_to(repo_root).parts):
            continue

        # Skip large files
        try:
            size = file_path.stat().st_size
            if size > MAX_FILE_SIZE or size == 0:
                continue
        except OSError:
            continue

        # Check if file type is supported
        language = get_file_language(str(file_path))
        if language is None:
            continue

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        files.append({
            "path": rel_path,
            "content": content,
            "language": language,
            "size": size,
        })

    return files


def build_language_breakdown(files: list[dict]) -> dict[str, int]:
    """Count files per language."""
    breakdown = {}
    for f in files:
        lang = f["language"]
        breakdown[lang] = breakdown.get(lang, 0) + 1
    return dict(sorted(breakdown.items(), key=lambda x: -x[1]))


def build_tree_structure(files: list[dict], max_depth: int = 4) -> str:
    """Build a visual tree representation of the repo structure."""
    tree: dict = {}

    for f in files:
        parts = f["path"].split("/")
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = None  # leaf file

    def render(node: dict, prefix: str = "", depth: int = 0) -> list[str]:
        if depth >= max_depth:
            return [f"{prefix}..."]
        lines = []
        items = sorted(node.items(), key=lambda x: (x[1] is not None, x[0]))
        for i, (name, subtree) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}{'/' if subtree is not None else ''}")
            if subtree is not None:
                extension = "    " if is_last else "│   "
                lines.extend(render(subtree, prefix + extension, depth + 1))
        return lines

    return "\n".join(render(tree))


def chunk_file_content(file_path: str, content: str, language: str, chunk_size: int = 2000, overlap: int = 200) -> list[dict]:
    """
    Split a file into overlapping chunks for better RAG retrieval.
    Each chunk includes file metadata as context.
    """
    lines = content.split("\n")
    chunks = []
    current_chunk_lines = []
    current_size = 0
    chunk_index = 0

    header = f"# File: {file_path}\n# Language: {language}\n\n"

    for line in lines:
        line_size = len(line) + 1  # +1 for newline
        if current_size + line_size > chunk_size and current_chunk_lines:
            chunk_content = header + "\n".join(current_chunk_lines)
            chunks.append({
                "file_path": file_path,
                "chunk_index": chunk_index,
                "content": chunk_content,
                "language": language,
            })
            chunk_index += 1

            # Keep overlap
            overlap_lines = []
            overlap_size = 0
            for prev_line in reversed(current_chunk_lines):
                if overlap_size + len(prev_line) > overlap:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_size += len(prev_line) + 1

            current_chunk_lines = overlap_lines
            current_size = overlap_size

        current_chunk_lines.append(line)
        current_size += line_size

    # Last chunk
    if current_chunk_lines:
        chunk_content = header + "\n".join(current_chunk_lines)
        chunks.append({
            "file_path": file_path,
            "chunk_index": chunk_index,
            "content": chunk_content,
            "language": language,
        })

    return chunks


async def ingest_repo(repo_url: str) -> dict:
    """
    Full pipeline: clone → scan → chunk → prepare for Knowledge Base.
    Returns repo metadata and chunked content.
    """
    # Clone
    repo_id, local_path = await clone_repo(repo_url)
    _, repo_name = parse_github_url(repo_url)

    # Scan files
    files = scan_repo_files(local_path)

    # Build metadata
    language_breakdown = build_language_breakdown(files)
    tree = build_tree_structure(files)

    # Chunk all files
    all_chunks = []
    for f in files:
        chunks = chunk_file_content(f["path"], f["content"], f["language"])
        all_chunks.extend(chunks)

    # Generate repo summary context
    summary = (
        f"Repository: {repo_name}\n"
        f"URL: {repo_url}\n"
        f"Total files indexed: {len(files)}\n"
        f"Total chunks: {len(all_chunks)}\n"
        f"Languages: {', '.join(language_breakdown.keys())}\n\n"
        f"Structure:\n{tree}"
    )

    return {
        "repo_id": repo_id,
        "repo_name": repo_name,
        "repo_url": repo_url,
        "local_path": local_path,
        "file_count": len(files),
        "chunk_count": len(all_chunks),
        "language_breakdown": language_breakdown,
        "structure_summary": summary,
        "tree": tree,
        "files": files,
        "chunks": all_chunks,
    }
