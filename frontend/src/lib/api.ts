type TokenGetter = () => Promise<string | null>

type ChatCallbacks = {
  onChunk: (content: string) => void
  onError: (message: string) => void
}

type StreamChatOptions = {
  model?: string | null
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  model?: string | null
  created_at?: string
}

export type ChatThreadSummary = {
  id: string
  title: string
  preview: string | null
  created_at: string
  updated_at: string
}

export type ChatThreadDetail = ChatThreadSummary & {
  messages: ChatMessage[]
}

async function getAuthHeaders(getToken: TokenGetter) {
  const token = await getToken()

  if (!token) {
    throw new Error('No active Clerk session token found.')
  }

  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
}

export async function fetchMe(getToken: TokenGetter) {
  const response = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/me`, {
    headers: await getAuthHeaders(getToken),
  })

  if (!response.ok) {
    throw new Error('Failed to load profile.')
  }

  return response.json() as Promise<{
    id: string
    email: string | null
    display_name: string
  }>
}

export async function fetchProvider(getToken: TokenGetter) {
  const response = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/providers`, {
    headers: await getAuthHeaders(getToken),
  })

  if (!response.ok) {
    throw new Error('Failed to load provider config.')
  }

  return response.json() as Promise<{
    name: string
    provider_type: string
    base_url: string
    default_model: string
    is_local: boolean
  }>
}

export async function fetchOllamaModels(getToken: TokenGetter) {
  const response = await fetch(
    `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/providers/models`,
    {
      headers: await getAuthHeaders(getToken),
    },
  )

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: 'Failed to list Ollama models.' }))
    const detail =
      typeof payload.detail === 'string' ? payload.detail : 'Failed to list Ollama models.'
    throw new Error(detail)
  }

  return response.json() as Promise<{ models: string[] }>
}

export async function testProvider(getToken: TokenGetter) {
  const response = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/providers/test`, {
    method: 'POST',
    headers: await getAuthHeaders(getToken),
  })

  const payload = await response.json().catch(() => ({ detail: 'Provider test failed.' }))

  if (!response.ok) {
    const detail = typeof payload.detail === 'string' ? payload.detail : 'Provider test failed.'
    throw new Error(detail)
  }

  return payload as { ok: boolean; message: string }
}

export async function fetchChatThreads(getToken: TokenGetter) {
  const response = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/chat/threads`, {
    headers: await getAuthHeaders(getToken),
  })

  if (!response.ok) {
    throw new Error('Failed to load chats.')
  }

  return response.json() as Promise<ChatThreadSummary[]>
}

export async function createChatThread(getToken: TokenGetter) {
  const response = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/chat/threads`, {
    method: 'POST',
    headers: await getAuthHeaders(getToken),
  })

  if (!response.ok) {
    throw new Error('Failed to create chat.')
  }

  return response.json() as Promise<ChatThreadSummary>
}

export async function fetchChatThread(threadId: string, getToken: TokenGetter) {
  const response = await fetch(
    `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/chat/threads/${threadId}`,
    {
      headers: await getAuthHeaders(getToken),
    },
  )

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const detail =
      typeof (payload as { detail?: string }).detail === 'string'
        ? (payload as { detail: string }).detail
        : 'Failed to load chat.'
    throw new Error(detail)
  }

  return response.json() as Promise<ChatThreadDetail>
}

type SseEvent = {
  event: string
  data: Record<string, string>
}

function parseSseChunk(chunk: string): SseEvent[] {
  return chunk
    .split('\n\n')
    .filter(Boolean)
    .map((block) => {
      const lines = block.split('\n')
      const event = lines.find((line) => line.startsWith('event:'))?.slice(6).trim() ?? 'message'
      const dataLine = lines.find((line) => line.startsWith('data:'))?.slice(5).trim() ?? '{}'
      return {
        event,
        data: JSON.parse(dataLine) as Record<string, string>,
      }
    })
}

export async function streamChat(
  threadId: string,
  message: string,
  getToken: TokenGetter,
  callbacks: ChatCallbacks,
  options?: StreamChatOptions,
) {
  const body: { message: string; model?: string } = { message }
  const trimmed = options?.model?.trim()
  if (trimmed) {
    body.model = trimmed
  }

  const response = await fetch(
    `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/chat/threads/${threadId}/stream`,
    {
      method: 'POST',
      headers: await getAuthHeaders(getToken),
      body: JSON.stringify(body),
    },
  )

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const detail =
      typeof (payload as { detail?: string }).detail === 'string'
        ? (payload as { detail: string }).detail
        : 'Failed to start chat stream.'
    throw new Error(detail)
  }

  if (!response.body) {
    throw new Error('Failed to start chat stream.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatchSseEvent = (rawBlock: string) => {
    if (!rawBlock.trim()) {
      return
    }
    const [event] = parseSseChunk(`${rawBlock}\n\n`)
    if (!event) {
      return
    }
    if (event.event === 'chunk' && event.data.content) {
      callbacks.onChunk(event.data.content)
    }
    if (event.event === 'error') {
      callbacks.onError(event.data.message ?? 'Streaming failed.')
    }
  }

  while (true) {
    const { value, done } = await reader.read()

    if (value) {
      buffer += decoder.decode(value, { stream: true })
    }

    // sse-starlette uses CRLF (`\r\n`) between SSE fields and events; splitting on
    // `\n\n` only never sees a frame boundary, so chunks never dispatch.
    const normalized = buffer.replace(/\r\n/g, '\n')
    const parts = normalized.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      dispatchSseEvent(part)
    }

    if (done) {
      dispatchSseEvent(buffer.replace(/\r\n/g, '\n'))
      break
    }
  }
}
