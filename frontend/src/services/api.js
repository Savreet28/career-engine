/**
 * api.js
 * ======
 *
 * Every call to the FastAPI backend lives here. Requests go to relative
 * `/api/...` paths, which Vite proxies to http://localhost:8000 during
 * development (see vite.config.js).
 */

const BASE = '/api'

const UNREACHABLE =
  'Could not reach the backend. Is it running on http://localhost:8000?'

/** Turn a failed response into an Error carrying the backend's own message. */
async function toError(response) {
  const raw = await response.text().catch(() => '')

  // Vite's dev proxy answers with an EMPTY 500 when it cannot reach the API
  // server, so a bodyless 5xx means the backend is down rather than broken.
  // A real backend error always carries a JSON {"detail": ...} body.
  if (!raw.trim() && response.status >= 500) {
    const error = new Error(UNREACHABLE)
    error.status = 0
    return error
  }

  let detail = `Request failed with status ${response.status}`
  try {
    const body = JSON.parse(raw)
    if (typeof body.detail === 'string') {
      detail = body.detail
    } else if (Array.isArray(body.detail)) {
      // FastAPI validation errors arrive as a list of field problems.
      detail = body.detail
        .map((e) => `${(e.loc || []).slice(1).join('.') || 'field'}: ${e.msg}`)
        .join('; ')
    }
  } catch {
    /* not JSON; keep the status-based message */
  }
  const error = new Error(detail)
  error.status = response.status
  return error
}

async function getJSON(path) {
  let response
  try {
    response = await fetch(`${BASE}${path}`)
  } catch {
    throw new Error(UNREACHABLE)
  }
  if (!response.ok) throw await toError(response)
  return response.json()
}

export const getRoles = () => getJSON('/roles')
export const getExperienceLevels = () => getJSON('/experience-levels')

// The backend also exposes /health, /rag/status, /rag/search and
// /job-descriptions. They are not called from the UI -- they exist for
// inspecting the system directly (see http://localhost:8000/docs).

/** Build the multipart body shared by every analysis endpoint. */
function analysisFormData({ resumeFile, roleId, experienceLevel, githubUsername, jobDescriptionText }) {
  const form = new FormData()
  form.append('resume', resumeFile)
  form.append('role_id', roleId)
  if (experienceLevel) form.append('experience_level', experienceLevel)
  if (githubUsername?.trim()) form.append('github_username', githubUsername.trim())
  if (jobDescriptionText?.trim()) form.append('job_description', jobDescriptionText.trim())
  return form
}

/** Non-streaming pipeline call. Used as a fallback if streaming fails. */
export async function analyze(options) {
  let response
  try {
    response = await fetch(`${BASE}/analyze`, {
      method: 'POST',
      body: analysisFormData(options),
    })
  } catch {
    throw new Error(UNREACHABLE)
  }
  if (!response.ok) throw await toError(response)
  return response.json()
}

/**
 * Streaming pipeline call.
 *
 * The backend emits Server-Sent Events as each stage actually starts and
 * finishes, so `onStage` fires on real backend progress -- there is no
 * simulated timer or invented percentage anywhere in this file.
 *
 * EventSource cannot POST a file, so we read the SSE body from fetch directly.
 */
export async function analyzeStream(options, { onStage, signal } = {}) {
  let response
  try {
    response = await fetch(`${BASE}/analyze/stream`, {
      method: 'POST',
      body: analysisFormData(options),
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error(UNREACHABLE)
  }
  if (!response.ok) throw await toError(response)
  if (!response.body) throw new Error('This browser cannot read a streaming response.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result = null
  let streamError = null

  // SSE frames are separated by a blank line.
  const handleFrame = (frame) => {
    let event = 'message'
    const dataLines = []
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (!dataLines.length) return
    let payload
    try {
      payload = JSON.parse(dataLines.join('\n'))
    } catch {
      return
    }
    if (event === 'stage') onStage?.(payload)
    else if (event === 'result') result = payload
    else if (event === 'error') streamError = payload
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let split
    while ((split = buffer.indexOf('\n\n')) !== -1) {
      handleFrame(buffer.slice(0, split))
      buffer = buffer.slice(split + 2)
    }
  }
  if (buffer.trim()) handleFrame(buffer)

  if (streamError) {
    const error = new Error(streamError.detail || 'Analysis failed.')
    error.status = streamError.error_type === 'resume_parse_error' ? 422 : 500
    throw error
  }
  if (!result) throw new Error('The analysis ended without returning a result.')
  return result
}

/** The pipeline stages, in the order the backend runs them. */
export const PIPELINE_STAGES = [
  { id: 'parse_resume', label: 'Parsing resume' },
  { id: 'analyze_github', label: 'Analysing GitHub profile' },
  { id: 'rag_retrieval', label: 'Retrieving job-description evidence' },
  { id: 'ats_score', label: 'Calculating ATS score' },
  { id: 'job_match', label: 'Matching skills against requirements' },
  { id: 'summary', label: 'Preparing summary' },
]
