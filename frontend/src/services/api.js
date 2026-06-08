const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export async function loginDemoUser({ name, role }) {
  const response = await fetch(`${API_BASE_URL}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, role }),
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(body.detail || 'Unable to start session.')
  }

  return body
}

export async function sendChatMessage({ question, role, history = [], sessionToken }) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
    },
    body: JSON.stringify({ question, role, history }),
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(body.detail || 'The assistant service is unavailable.')
  }

  return body
}

export async function getChatHistory({ sessionToken }) {
  const response = await fetch(`${API_BASE_URL}/chat/history`, {
    headers: {
      ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
    },
  })
  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(body.detail || 'Unable to load chat history.')
  }

  return body
}

export async function clearChatHistory({ sessionToken }) {
  const response = await fetch(`${API_BASE_URL}/chat/history`, {
    method: 'DELETE',
    headers: {
      ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
    },
  })
  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(body.detail || 'Unable to clear chat history.')
  }

  return body
}

export async function getServiceStatus() {
  const response = await fetch(`${API_BASE_URL}/status`)
  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(body.detail || 'Unable to load service status.')
  }

  return body
}

export async function getMonitoringMetrics() {
  const response = await fetch(`${API_BASE_URL}/metrics`)
  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(body.detail || 'Unable to load monitoring metrics.')
  }

  return body
}
