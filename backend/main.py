"""
RepoWhisperer — FastAPI Application

Main entry point with all API routes.
"""

import asyncio
import json
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

from config import get_settings
from models import RepoRequest, RepoInfo, ChatRequest, ChatResponse
from repo_ingestion import ingest_repo, generate_repo_id, parse_github_url
from agent_service import GradientAIService, RepoContextBuilder

# ─── Persistence helpers ─────────────────────────────────────
# Simple JSON persistence so repos survive server restarts (--reload).

STORE_FILE = os.path.join(os.path.dirname(__file__), ".repos_store.json")

def _save_store():
    """Persist repos_store to disk (skip non-serializable fields)."""
    try:
        serializable = {}
        for rid, data in repos_store.items():
            entry = {k: v for k, v in data.items() if k != "_task"}
            serializable[rid] = entry
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f)
    except Exception:
        pass  # best-effort

def _load_store():
    """Load repos_store from disk if file exists."""
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

# ─── App Setup ───────────────────────────────────────────────

app = FastAPI(
    title="RepoWhisperer",
    description="AI-powered code repository understanding tool built on DigitalOcean Gradient AI",
    version="1.0.0",
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Accept requests from any origin (dev-friendly; tighten for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-Memory Store ─────────────────────────────────────────
# In production, replace with DigitalOcean Managed Database

repos_store: dict[str, dict] = _load_store()  # repo_id -> repo_data  (restored from disk)
indexing_tasks: dict[str, asyncio.Task] = {}

# ─── Gradient AI Service ─────────────────────────────────────

ai_service = GradientAIService()


@app.on_event("startup")
async def startup():
    if ai_service.is_demo:
        print("\n" + "=" * 60)
        print("  🚀 RepoWhisperer running in DEMO MODE")
        print("  No API key detected — using local analysis")
        print("  Set DO_AGENT_KEY in .env for full AI mode")
        print("=" * 60 + "\n")
    else:
        print("\n  🚀 RepoWhisperer connected to DigitalOcean Gradient AI\n")

    # Re-ingest any repos that were stuck in "indexing" state (e.g. after a restart)
    for repo_id, data in list(repos_store.items()):
        if data.get("status") == "indexing":
            repo_url = data.get("repo_url", "")
            if repo_url:
                print(f"  ↻ Re-indexing {data.get('repo_name', repo_id)} ...")

                async def _re_index(rid=repo_id, url=repo_url):
                    try:
                        result = await ingest_repo(url)
                        result["status"] = "ready"
                        repos_store[rid] = result
                        _save_store()
                    except Exception as e:
                        repos_store[rid]["status"] = "error"
                        repos_store[rid]["error"] = str(e)
                        _save_store()

                task = asyncio.create_task(_re_index())
                indexing_tasks[repo_id] = task

# ─── API Routes ──────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "app": "RepoWhisperer",
        "version": "1.0.0",
        "description": "Chat with any GitHub repository using AI",
        "powered_by": "DigitalOcean Gradient AI",
        "demo_mode": ai_service.is_demo,
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "demo_mode": ai_service.is_demo}


# ─── Repo Management ─────────────────────────────────────────


@app.post("/api/repos", response_model=RepoInfo)
async def index_repo(request: RepoRequest):
    """Start indexing a GitHub repository."""
    repo_url = request.repo_url.strip()

    # Validate URL
    if not repo_url.startswith("https://github.com/"):
        raise HTTPException(
            status_code=400,
            detail="Only GitHub URLs are supported (https://github.com/owner/repo)"
        )

    repo_id = generate_repo_id(repo_url)
    _, repo_name = parse_github_url(repo_url)

    # Check if already indexed or indexing
    if repo_id in repos_store:
        existing = repos_store[repo_id]
        return RepoInfo(
            id=repo_id,
            name=existing["repo_name"],
            url=repo_url,
            status=existing.get("status", "ready"),
            file_count=existing.get("file_count", 0),
            language_breakdown=existing.get("language_breakdown", {}),
            description=existing.get("structure_summary", ""),
        )

    # Start indexing in background
    repos_store[repo_id] = {
        "repo_name": repo_name,
        "repo_url": repo_url,
        "status": "indexing",
        "file_count": 0,
        "language_breakdown": {},
        "structure_summary": "",
    }

    async def _do_index():
        try:
            result = await ingest_repo(repo_url)
            result["status"] = "ready"
            repos_store[repo_id] = result
            _save_store()
        except Exception as e:
            repos_store[repo_id]["status"] = "error"
            repos_store[repo_id]["error"] = str(e)
            _save_store()

    task = asyncio.create_task(_do_index())
    indexing_tasks[repo_id] = task

    return RepoInfo(
        id=repo_id,
        name=repo_name,
        url=repo_url,
        status="indexing",
    )


@app.get("/api/repos/{repo_id}", response_model=RepoInfo)
async def get_repo(repo_id: str):
    """Get status and info of an indexed repository."""
    if repo_id not in repos_store:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = repos_store[repo_id]
    return RepoInfo(
        id=repo_id,
        name=repo.get("repo_name", ""),
        url=repo.get("repo_url", ""),
        status=repo.get("status", "unknown"),
        file_count=repo.get("file_count", 0),
        language_breakdown=repo.get("language_breakdown", {}),
        description=repo.get("structure_summary", ""),
    )


@app.get("/api/repos")
async def list_repos():
    """List all indexed repositories."""
    return [
        RepoInfo(
            id=repo_id,
            name=data.get("repo_name", ""),
            url=data.get("repo_url", ""),
            status=data.get("status", "unknown"),
            file_count=data.get("file_count", 0),
            language_breakdown=data.get("language_breakdown", {}),
        )
        for repo_id, data in repos_store.items()
    ]


@app.delete("/api/repos/{repo_id}")
async def delete_repo(repo_id: str):
    """Remove an indexed repository."""
    if repo_id not in repos_store:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Cancel indexing if in progress
    if repo_id in indexing_tasks:
        indexing_tasks[repo_id].cancel()
        del indexing_tasks[repo_id]

    del repos_store[repo_id]
    _save_store()
    return {"status": "deleted"}


@app.get("/api/repos/{repo_id}/tree")
async def get_repo_tree(repo_id: str):
    """Get the file tree of an indexed repository."""
    if repo_id not in repos_store:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = repos_store[repo_id]
    if repo.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Repository is still indexing")

    return {"tree": repo.get("tree", "")}


@app.get("/api/repos/{repo_id}/files/{file_path:path}")
async def get_file_content(repo_id: str, file_path: str):
    """Get the content of a specific file in the indexed repo."""
    if repo_id not in repos_store:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = repos_store[repo_id]
    if repo.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Repository is still indexing")

    for f in repo.get("files", []):
        if f["path"] == file_path:
            return {"path": f["path"], "content": f["content"], "language": f["language"]}

    raise HTTPException(status_code=404, detail="File not found")


# ─── Chat ─────────────────────────────────────────────────────


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the AI about an indexed repository."""
    if request.repo_id not in repos_store:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = repos_store[request.repo_id]
    if repo.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Repository is still indexing")

    # Build context
    context_builder = RepoContextBuilder(repo)
    context = context_builder.build_query_context(request.message)

    # Build messages
    messages = [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})

    try:
        response = await ai_service.chat_completion(
            messages=messages,
            repo_context=context,
            model=request.model,
        )

        # Extract referenced files from response
        sources = _extract_file_references(response, repo.get("files", []))

        return ChatResponse(message=response, sources=sources)

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {e.response.status_code}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream a chat response from the AI."""
    if request.repo_id not in repos_store:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = repos_store[request.repo_id]
    if repo.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Repository is still indexing")

    context_builder = RepoContextBuilder(repo)
    context = context_builder.build_query_context(request.message)

    messages = [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})

    async def generate():
        try:
            async for chunk in ai_service.chat_completion_stream(
                messages=messages,
                repo_context=context,
                model=request.model,
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ─── WebSocket Chat ───────────────────────────────────────────


@app.websocket("/ws/chat/{repo_id}")
async def websocket_chat(websocket: WebSocket, repo_id: str):
    """WebSocket endpoint for real-time streaming chat."""
    await websocket.accept()

    if repo_id not in repos_store:
        await websocket.send_json({"error": "Repository not found"})
        await websocket.close()
        return

    repo = repos_store[repo_id]
    if repo.get("status") != "ready":
        await websocket.send_json({"error": "Repository is still indexing"})
        await websocket.close()
        return

    context_builder = RepoContextBuilder(repo)
    chat_history = []

    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            model = data.get("model")

            if not user_message:
                continue

            # Build context for this query
            context = context_builder.build_query_context(user_message)

            # Add to history
            chat_history.append({"role": "user", "content": user_message})

            # Stream response
            full_response = ""
            try:
                async for chunk in ai_service.chat_completion_stream(
                    messages=chat_history.copy(),
                    repo_context=context,
                    model=model,
                ):
                    full_response += chunk
                    await websocket.send_json({"type": "chunk", "content": chunk})

                # Send completion signal
                sources = _extract_file_references(full_response, repo.get("files", []))
                await websocket.send_json({
                    "type": "done",
                    "sources": sources,
                })

                # Add to history
                chat_history.append({"role": "assistant", "content": full_response})

                # Keep history manageable (last 20 messages)
                if len(chat_history) > 20:
                    chat_history = chat_history[-20:]

            except Exception as e:
                await websocket.send_json({"type": "error", "content": str(e)})

    except WebSocketDisconnect:
        pass


# ─── Helpers ──────────────────────────────────────────────────


def _extract_file_references(response: str, files: list[dict]) -> list[str]:
    """Extract file paths mentioned in the AI response."""
    sources = set()
    for f in files:
        path = f["path"]
        # Check if the file path appears in the response
        if path in response or path.split("/")[-1] in response:
            sources.add(path)
    return sorted(sources)[:10]  # Limit to 10 references


# ─── Available Models ─────────────────────────────────────────


@app.get("/api/models")
async def list_models():
    """List available AI models on Gradient AI."""
    if ai_service.is_demo:
        return {
            "models": [
                {"id": "demo", "name": "Demo Mode (local)", "provider": "RepoWhisperer"},
            ],
            "demo_mode": True,
        }
    return {
        "models": [
            {"id": "llama3.3-70b-instruct", "name": "Llama 3.3 70B", "provider": "Meta"},
            {"id": "deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 70B", "provider": "DeepSeek"},
            {"id": "mistral-nemo-instruct-2407", "name": "Mistral Nemo", "provider": "Mistral"},
            {"id": "llama3-8b-instruct", "name": "Llama 3 8B (fast)", "provider": "Meta"},
        ]
    }


# ─── Serve Frontend ──────────────────────────────────────────

@app.get("/app", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the single-page frontend."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found. Run from the backend directory.</h1>", status_code=404)
