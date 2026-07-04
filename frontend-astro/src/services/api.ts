const API_BASE = '/api/v1'

export async function fetchLatestSnapshot(minScore?: number, industry?: string) {
  const params = new URLSearchParams()
  if (minScore !== undefined) params.append('min_score', String(minScore))
  if (industry) params.append('industry', industry)
  const res = await fetch(`${API_BASE}/snapshot/latest?${params}`)
  return res.json()
}

export async function fetchSnapshotDates() {
  const res = await fetch(`${API_BASE}/snapshot/dates`)
  return res.json()
}

export async function fetchSnapshotByDate(date: string) {
  const res = await fetch(`${API_BASE}/snapshot/${date}`)
  return res.json()
}

export async function fetchStockDetail(symbol: string) {
  const res = await fetch(`${API_BASE}/stock/${symbol}`)
  return res.json()
}

export async function runPipeline() {
  const res = await fetch(`${API_BASE}/run`, { method: 'POST' })
  return res.json()
}

export async function fetchRunStatus(jobId: string) {
  const res = await fetch(`${API_BASE}/run/status/${jobId}`)
  return res.json()
}

export async function fetchLogs() {
  const res = await fetch(`${API_BASE}/logs`)
  return res.json()
}

export async function fetchQualitySummary() {
  const res = await fetch(`${API_BASE}/quality/summary`)
  return res.json()
}

export async function fetchBacktest() {
  const res = await fetch(`${API_BASE}/backtest/simple`)
  return res.json()
}

export async function fetchQualityDetail() {
  const res = await fetch(`${API_BASE}/quality/detail`)
  return res.json()
}


export function getWatchlistDownloadUrl(): string {
  return `${API_BASE}/export/watchlist`
}

export async function advisorChat(messages: { role: string; content: string }[]) {
  const res = await fetch(`${API_BASE}/advisor/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  })
  return res.json()
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/settings`)
  return res.json()
}

export async function updateSettings(settings: Record<string, string>) {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
  return res.json()
}

export async function resetSettings() {
  const res = await fetch(`${API_BASE}/settings/reset`, { method: 'POST' })
  return res.json()
}
