from pydantic import BaseModel
from typing import Optional


class RepoRequest(BaseModel):
    """Request to index a GitHub repository."""
    repo_url: str


class RepoInfo(BaseModel):
    """Information about an indexed repository."""
    id: str
    name: str
    url: str
    status: str  # "indexing", "ready", "error"
    file_count: int = 0
    language_breakdown: dict[str, int] = {}
    description: str = ""
    structure_summary: str = ""


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request to chat with an indexed repo."""
    repo_id: str
    message: str
    history: list[ChatMessage] = []
    model: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the AI agent."""
    message: str
    sources: list[str] = []  # files referenced in the response


class RepoFile(BaseModel):
    """A file in the repository."""
    path: str
    content: str
    language: str
    size: int
