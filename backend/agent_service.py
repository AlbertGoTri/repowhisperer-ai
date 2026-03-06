"""
RepoWhisperer — Gradient AI Agent Service

Interfaces with DigitalOcean Gradient AI for:
- Knowledge Base management (create, upload chunks, query)
- Agent chat (serverless inference with RAG context)

Includes a DEMO MODE that works without any API key,
generating smart responses from the indexed repo data.
"""

import asyncio
import httpx
import json
from typing import Optional
from config import get_settings

SYSTEM_PROMPT = """You are RepoWhisperer, an expert AI senior software engineer assistant.
You have deep knowledge of a specific code repository that has been indexed for you.

Your capabilities:
1. **Explain code**: Break down how any part of the codebase works, from high-level architecture to individual functions.
2. **Find code**: Locate where specific functionality is implemented (authentication, routing, database queries, etc.).
3. **Generate code**: Write new code (tests, features, refactors) that follows the patterns and style of the existing codebase.
4. **Review & suggest**: Identify potential bugs, security issues, performance improvements, and suggest refactors.
5. **Onboarding**: Help new developers understand the project structure, conventions, and how to get started.

Guidelines:
- Always reference specific file paths when discussing code.
- Use code blocks with the appropriate language tag.
- When generating new code, match the style and patterns of the existing codebase.
- If you're unsure about something, say so rather than guessing.
- Be concise but thorough. Developers value precision.
- When explaining architecture, start with the big picture and then zoom into details.

You are friendly, knowledgeable, and efficient. You speak like a helpful senior dev on the team."""


class GradientAIService:
    """Service for interacting with DigitalOcean Gradient AI."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.do_agent_endpoint
        self.headers = {
            "Authorization": f"Bearer {self.settings.do_agent_key}",
            "Content-Type": "application/json",
        }

    @property
    def is_demo(self) -> bool:
        return self.settings.is_demo

    async def chat_completion(
        self,
        messages: list[dict],
        repo_context: str,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a chat completion request to Gradient AI with repo context.
        Falls back to demo mode if no API key is configured.
        """
        if self.is_demo:
            return self._demo_response(messages, repo_context)

        selected_model = model or "llama3.3-70b-instruct"

        full_messages = [
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\n\n---\n\nRepository Context:\n{repo_context}"
            },
            *messages,
        ]

        payload = {
            "model": selected_model,
            "messages": full_messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_completion_stream(
        self,
        messages: list[dict],
        repo_context: str,
        model: Optional[str] = None,
    ):
        """
        Stream a chat completion response for real-time output.
        Falls back to demo mode streaming if no API key.
        """
        if self.is_demo:
            response = self._demo_response(messages, repo_context)
            # Simulate streaming by yielding word by word
            words = response.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.03)  # simulate typing delay
            return

        selected_model = model or "llama3.3-70b-instruct"

        full_messages = [
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\n\n---\n\nRepository Context:\n{repo_context}"
            },
            *messages,
        ]

        payload = {
            "model": selected_model,
            "messages": full_messages,
            "temperature": 0.3,
            "max_tokens": 4096,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    def _demo_response(self, messages: list[dict], repo_context: str) -> str:
        """
        Generate a smart demo response without calling any external API.
        Analyzes the repo context and user question to produce relevant output.
        """
        user_msg = messages[-1]["content"].lower() if messages else ""

        # Parse repo info from context
        lines = repo_context.split("\n")
        repo_name = ""
        file_count = ""
        languages = ""
        tree_section = ""
        code_sections = []

        in_tree = False
        in_code = False
        current_code = []

        for line in lines:
            if line.startswith("# Repository:"):
                repo_name = line.replace("# Repository:", "").strip()
            elif line.startswith("Files indexed:"):
                file_count = line.replace("Files indexed:", "").strip()
            elif line.startswith("Languages:"):
                languages = line.replace("Languages:", "").strip()
            elif line.startswith("## Project Structure"):
                in_tree = True
            elif in_tree and line.startswith("```"):
                if tree_section:
                    in_tree = False
                else:
                    continue
            elif in_tree:
                tree_section += line + "\n"
            elif line.startswith("# File:"):
                if current_code:
                    code_sections.append("\n".join(current_code))
                current_code = [line]
                in_code = True
            elif in_code:
                current_code.append(line)

        if current_code:
            code_sections.append("\n".join(current_code))

        # Route to appropriate demo handler
        if any(w in user_msg for w in ["what does", "what is", "overview", "about", "describe", "qué hace", "qué es"]):
            return self._demo_overview(repo_name, file_count, languages, tree_section, code_sections)
        elif any(w in user_msg for w in ["structure", "architecture", "organized", "folder", "estructura", "arquitectura"]):
            return self._demo_structure(repo_name, tree_section, languages)
        elif any(w in user_msg for w in ["dependencies", "depend", "libraries", "packages", "dependencias"]):
            return self._demo_dependencies(repo_name, code_sections)
        elif any(w in user_msg for w in ["bug", "issue", "problem", "improve", "review", "error", "mejora"]):
            return self._demo_review(repo_name, code_sections)
        elif any(w in user_msg for w in ["test", "testing", "spec"]):
            return self._demo_tests(repo_name, code_sections)
        elif any(w in user_msg for w in ["how", "where", "find", "cómo", "dónde", "busca"]):
            return self._demo_search(user_msg, repo_name, code_sections)
        else:
            return self._demo_general(user_msg, repo_name, file_count, languages, tree_section, code_sections)

    def _demo_overview(self, repo_name, file_count, languages, tree, code_sections) -> str:
        # Try to find README content
        readme_content = ""
        for section in code_sections:
            if "readme" in section.lower()[:50]:
                readme_content = section[section.find("\n") + 1:][:500]
                break

        response = f"## 📖 Overview of **{repo_name}**\n\n"
        if readme_content:
            response += f"Based on the README and source code:\n\n{readme_content}\n\n"
        response += f"**Stats:**\n"
        response += f"- 📁 **{file_count}** files indexed\n"
        response += f"- 🔤 **Languages:** {languages}\n\n"
        if tree:
            response += f"**Project structure:**\n```\n{tree[:1000]}```\n\n"
        response += "*🔔 Running in demo mode — connect your DigitalOcean Gradient AI key for full AI-powered analysis!*"
        return response

    def _demo_structure(self, repo_name, tree, languages) -> str:
        response = f"## 🏗️ Project Structure — **{repo_name}**\n\n"
        response += f"**Languages used:** {languages}\n\n"
        if tree:
            response += f"```\n{tree[:2000]}```\n\n"
        else:
            response += "The project tree is still being processed.\n\n"
        response += "*🔔 Demo mode — connect Gradient AI for deeper architectural analysis!*"
        return response

    def _demo_dependencies(self, repo_name, code_sections) -> str:
        response = f"## 📦 Dependencies — **{repo_name}**\n\n"
        found_deps = False
        for section in code_sections:
            lower = section.lower()
            if any(f in lower[:80] for f in ["package.json", "requirements", "cargo.toml", "go.mod", "pyproject.toml", "gemfile", "build.gradle"]):
                file_name = section.split("\n")[0].replace("# File:", "").strip()
                content = "\n".join(section.split("\n")[2:])[:1500]
                response += f"### `{file_name}`\n```\n{content}\n```\n\n"
                found_deps = True
        if not found_deps:
            response += "I found the following code sections but couldn't identify a specific dependency file. "
            response += "Look for files like `package.json`, `requirements.txt`, `Cargo.toml`, etc.\n\n"
        response += "*🔔 Demo mode — connect Gradient AI for full dependency analysis and vulnerability checks!*"
        return response

    def _demo_review(self, repo_name, code_sections) -> str:
        response = f"## 🔍 Code Review Notes — **{repo_name}**\n\n"
        response += "Here are some general observations based on the codebase:\n\n"
        if code_sections:
            response += f"- 📄 Analyzed **{len(code_sections)}** code sections\n"
            # Count some basic patterns
            total_code = " ".join(code_sections)
            if "todo" in total_code.lower():
                response += "- ⚠️ Found `TODO` comments — there may be unfinished work\n"
            if "console.log" in total_code or "print(" in total_code:
                response += "- 🧹 Found debug logging statements (`console.log`/`print`) that might need cleanup\n"
            if "password" in total_code.lower() or "secret" in total_code.lower():
                response += "- 🔐 Found references to passwords/secrets — verify they're not hardcoded\n"
            if "try" in total_code and "except" not in total_code and "catch" not in total_code:
                response += "- ⚡ Some error handling might be incomplete\n"
            response += "- 📝 Consider adding more inline documentation\n"
            response += "- 🧪 Ensure test coverage for critical paths\n\n"
        response += "*🔔 Demo mode — connect Gradient AI for deep AI-powered code review with specific suggestions!*"
        return response

    def _demo_tests(self, repo_name, code_sections) -> str:
        response = f"## 🧪 Testing — **{repo_name}**\n\n"
        test_files = [s for s in code_sections if "test" in s.lower()[:80]]
        if test_files:
            response += f"Found **{len(test_files)}** test-related files:\n\n"
            for section in test_files[:3]:
                file_name = section.split("\n")[0].replace("# File:", "").strip()
                response += f"- `{file_name}`\n"
            response += "\n"
        else:
            response += "No test files were found in the indexed sections. Consider adding tests!\n\n"
        response += "*🔔 Demo mode — connect Gradient AI to auto-generate tests for any module!*"
        return response

    def _demo_search(self, query, repo_name, code_sections) -> str:
        response = f"## 🔎 Search Results — **{repo_name}**\n\n"
        # Find relevant sections
        query_terms = [w for w in query.split() if len(w) > 3]
        matches = []
        for section in code_sections:
            score = sum(1 for term in query_terms if term in section.lower())
            if score > 0:
                matches.append((score, section))
        matches.sort(key=lambda x: -x[0])

        if matches:
            response += f"Found **{len(matches)}** relevant code sections:\n\n"
            for _, section in matches[:5]:
                file_line = section.split("\n")[0].replace("# File:", "").strip()
                preview = "\n".join(section.split("\n")[2:8])
                response += f"### `{file_line}`\n```\n{preview}\n```\n\n"
        else:
            response += f"No exact matches found for your query in the indexed code.\n\n"
            response += "Try asking about specific file names, function names, or broader topics like 'authentication' or 'database'.\n\n"
        response += "*🔔 Demo mode — connect Gradient AI for intelligent semantic search!*"
        return response

    def _demo_general(self, query, repo_name, file_count, languages, tree, code_sections) -> str:
        response = f"## 💬 About **{repo_name}**\n\n"
        response += f"This repository contains **{file_count}** files using **{languages}**.\n\n"
        # Show most relevant code
        if code_sections:
            query_terms = [w for w in query.split() if len(w) > 2]
            best_match = None
            best_score = 0
            for section in code_sections:
                score = sum(1 for t in query_terms if t in section.lower())
                if score > best_score:
                    best_score = score
                    best_match = section
            if best_match and best_score > 0:
                file_line = best_match.split("\n")[0].replace("# File:", "").strip()
                preview = "\n".join(best_match.split("\n")[2:15])
                response += f"Most relevant file: `{file_line}`\n```\n{preview}\n```\n\n"

        response += "Here are some things you can ask me:\n\n"
        response += "- **\"What does this project do?\"** — overview based on README & code\n"
        response += "- **\"How is it structured?\"** — file tree and architecture\n"
        response += "- **\"What are the dependencies?\"** — package/requirements analysis\n"
        response += "- **\"Find [feature]\"** — search for specific code\n"
        response += "- **\"Review the code\"** — basic code review\n\n"
        response += "*🔔 Running in **demo mode** — for full AI-powered conversations, set your `DO_AGENT_KEY` in `.env` to use DigitalOcean Gradient AI!*"
        return response


class RepoContextBuilder:
    """Builds optimized context from indexed repo data for the AI agent."""

    def __init__(self, repo_data: dict):
        self.repo_data = repo_data

    def build_base_context(self) -> str:
        """Build the base repo context (structure + summary)."""
        return (
            f"# Repository: {self.repo_data['repo_name']}\n"
            f"URL: {self.repo_data['repo_url']}\n"
            f"Files indexed: {self.repo_data['file_count']}\n"
            f"Languages: {', '.join(self.repo_data['language_breakdown'].keys())}\n\n"
            f"## Project Structure\n```\n{self.repo_data['tree']}\n```\n"
        )

    def find_relevant_chunks(self, query: str, max_chunks: int = 15) -> list[dict]:
        """
        Simple keyword-based retrieval from chunks.
        In production, this would use Gradient AI Knowledge Base vector search.
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored_chunks = []
        for chunk in self.repo_data.get("chunks", []):
            content_lower = chunk["content"].lower()
            file_path_lower = chunk["file_path"].lower()

            score = 0
            # Exact phrase match bonus
            if query_lower in content_lower:
                score += 10

            # Term matching
            for term in query_terms:
                if len(term) > 2:  # Skip very short terms
                    count = content_lower.count(term)
                    score += count

            # File path relevance bonus
            for term in query_terms:
                if term in file_path_lower:
                    score += 5

            # Boost important files
            important_files = ["readme", "main", "app", "index", "config", "setup", "package.json", "requirements"]
            for important in important_files:
                if important in file_path_lower:
                    score += 2

            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort by score descending
        scored_chunks.sort(key=lambda x: -x[0])

        return [chunk for _, chunk in scored_chunks[:max_chunks]]

    def build_query_context(self, query: str) -> str:
        """Build context for a specific query, including relevant code chunks."""
        base = self.build_base_context()

        relevant_chunks = self.find_relevant_chunks(query)

        if not relevant_chunks:
            # If no relevant chunks found, include key files
            relevant_chunks = self._get_key_files()

        chunks_text = "\n\n---\n\n".join(
            chunk["content"] for chunk in relevant_chunks
        )

        return (
            f"{base}\n\n"
            f"## Relevant Code Sections\n\n{chunks_text}"
        )

    def _get_key_files(self, max_files: int = 10) -> list[dict]:
        """Get key files (README, configs, entry points) as fallback context."""
        key_patterns = [
            "readme", "main", "app", "index", "config",
            "setup.py", "package.json", "cargo.toml", "go.mod",
            "requirements.txt", "pyproject.toml",
        ]

        key_chunks = []
        seen_files = set()

        for chunk in self.repo_data.get("chunks", []):
            file_lower = chunk["file_path"].lower()
            if any(p in file_lower for p in key_patterns) and file_lower not in seen_files:
                key_chunks.append(chunk)
                seen_files.add(file_lower)
                if len(key_chunks) >= max_files:
                    break

        return key_chunks


# Singleton
gradient_ai = GradientAIService()
