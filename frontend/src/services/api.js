const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export async function sendChatMessage({ question, role, history = [] }) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, role, history }),
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(body.detail || 'The assistant service is unavailable.')
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
