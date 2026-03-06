const API_BASE = '/api';

/**
 * Safely parse a fetch Response as JSON.
 * Throws a descriptive error if the body is empty or not valid JSON
 * (e.g. when the backend is unreachable and the proxy returns HTML/empty).
 */
async function safeJson(res) {
  const text = await res.text();
  if (!text) {
    throw new Error('Empty response from server — is the backend running?');
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON response from server: ${text.slice(0, 120)}`);
  }
}

export async function indexRepo(repoUrl) {
  const res = await fetch(`${API_BASE}/repos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  const data = await safeJson(res);
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to index repository');
  }
  return data;
}

export async function getRepo(repoId) {
  const res = await fetch(`${API_BASE}/repos/${repoId}`);
  if (!res.ok) throw new Error('Repository not found');
  return safeJson(res);
}

export async function listRepos() {
  const res = await fetch(`${API_BASE}/repos`);
  return safeJson(res);
}

export async function deleteRepo(repoId) {
  await fetch(`${API_BASE}/repos/${repoId}`, { method: 'DELETE' });
}

export async function getRepoTree(repoId) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/tree`);
  return safeJson(res);
}

export async function getFileContent(repoId, filePath) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/files/${filePath}`);
  return safeJson(res);
}

export async function getModels() {
  const res = await fetch(`${API_BASE}/models`);
  const data = await safeJson(res);
  return data.models;
}

export async function* streamChat(repoId, message, history = [], model = null) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo_id: repoId,
      message,
      history,
      model,
    }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim();
        if (data === '[DONE]') return;
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) throw new Error(parsed.error);
          if (parsed.content) yield parsed.content;
        } catch (e) {
          if (e.message !== 'Unexpected end of JSON input') {
            console.error('Stream parse error:', e);
          }
        }
      }
    }
  }
}
