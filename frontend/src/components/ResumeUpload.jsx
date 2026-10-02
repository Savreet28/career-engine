import { useRef, useState } from 'react'

const ACCEPTED = ['.pdf', '.docx']
const MAX_BYTES = 10 * 1024 * 1024

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/**
 * Drag-and-drop resume picker with client-side validation.
 *
 * Validating here is a convenience, not a security boundary -- the backend
 * re-validates the extension, the magic bytes and the extracted text.
 */
export default function ResumeUpload({ file, onChange, disabled }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState(null)

  const accept = (candidate) => {
    if (!candidate) return
    const name = candidate.name.toLowerCase()
    if (!ACCEPTED.some((ext) => name.endsWith(ext))) {
      setError('Only PDF and DOCX files are supported.')
      return
    }
    if (candidate.size > MAX_BYTES) {
      setError(`That file is ${formatSize(candidate.size)}. The limit is 10 MB.`)
      return
    }
    if (candidate.size === 0) {
      setError('That file is empty.')
      return
    }
    setError(null)
    onChange(candidate)
  }

  const clear = () => {
    setError(null)
    onChange(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-slate-300">
        Resume <span className="text-bad-400">*</span>
      </label>

      {file ? (
        <div className="flex items-center gap-3 rounded-lg border border-accent-400/40 bg-accent-500/10 px-3 py-2.5">
          <svg className="h-5 w-5 shrink-0 text-accent-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v4a1 1 0 001 1h4M5 21V5a2 2 0 012-2h7l5 5v13a2 2 0 01-2 2H7a2 2 0 01-2-2z" />
          </svg>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-slate-100">{file.name}</p>
            <p className="text-[11px] text-slate-400">
              {formatSize(file.size)} · {file.name.toLowerCase().endsWith('.pdf') ? 'PDF' : 'DOCX'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
            className="rounded-md border border-ink-600 px-2 py-1 text-[11px] text-slate-300 transition hover:border-accent-400 hover:text-slate-100 disabled:opacity-50"
          >
            Change
          </button>
          <button
            type="button"
            onClick={clear}
            disabled={disabled}
            aria-label="Remove selected file"
            className="rounded-md border border-ink-600 px-2 py-1 text-[11px] text-slate-400 transition hover:border-bad-400 hover:text-bad-400 disabled:opacity-50"
          >
            Remove
          </button>
        </div>
      ) : (
        <div
          role="button"
          tabIndex={0}
          onClick={() => !disabled && inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              if (!disabled) inputRef.current?.click()
            }
          }}
          onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            if (!disabled) accept(e.dataTransfer.files?.[0])
          }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-7 text-center transition
            ${dragging ? 'border-accent-400 bg-accent-500/10' : 'border-ink-600 bg-ink-850/50 hover:border-accent-500/60 hover:bg-ink-800/50'}
            ${disabled ? 'pointer-events-none opacity-50' : ''}`}
        >
          <svg className="mb-2 h-6 w-6 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
          </svg>
          <p className="text-xs text-slate-300">
            <span className="font-medium text-accent-300">Browse</span> or drag a file here
          </p>
          <p className="mt-1 text-[11px] text-slate-500">PDF or DOCX · up to 10 MB</p>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="hidden"
        onChange={(e) => accept(e.target.files?.[0])}
      />

      {error && <p className="mt-1.5 text-[11px] text-bad-400">{error}</p>}
    </div>
  )
}
