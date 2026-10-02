import { useState } from 'react'

/**
 * Step 1 — the landing page.
 *
 * The email is a local profile label, not authentication: there is no user
 * database and no password, and the value is kept in this browser only. It
 * gives the app an owner to show in the header and a natural entry point.
 */
export default function Welcome({ onContinue }) {
  const [mode, setMode] = useState('create')
  const [email, setEmail] = useState('')
  const [error, setError] = useState(null)

  const submit = (event) => {
    event.preventDefault()
    const value = email.trim()
    if (!value) {
      setError('Please enter your email address.')
      return
    }
    // Deliberately permissive: enough to catch a typo, not a validation maze.
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) {
      setError('That does not look like a valid email address.')
      return
    }
    setError(null)
    onContinue(value)
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-lg flex-col justify-center px-4 py-10">
      <div className="mb-7 text-center">
        <span className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-accent-500/15 ring-1 ring-accent-400/30">
          <svg className="h-7 w-7 text-accent-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l5-5 4 4 8-8M21 8v5h-5" />
          </svg>
        </span>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Career Engine</h1>
        <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-slate-400">
          Analyse your resume, GitHub profile and target role to get a transparent
          ATS score and an explainable job match.
        </p>
      </div>

      <form
        onSubmit={submit}
        className="rounded-xl border border-ink-700/70 bg-ink-900/70 p-6 shadow-lg shadow-black/20 backdrop-blur-sm"
      >
        <div className="mb-5 flex rounded-lg border border-ink-600 p-0.5" role="tablist">
          {[['create', 'Create account'], ['login', 'Sign in']].map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={mode === id}
              onClick={() => setMode(id)}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                mode === id
                  ? 'bg-accent-500/20 text-accent-300'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-slate-300">
          Email address
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => { setEmail(e.target.value); setError(null) }}
          placeholder="you@college.edu"
          autoComplete="email"
          autoFocus
          className="w-full rounded-lg border border-ink-600 bg-ink-850/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-accent-500 placeholder:text-slate-600"
        />
        {error && <p className="mt-1.5 text-[11px] text-bad-400">{error}</p>}

        <button
          type="submit"
          className="mt-4 w-full rounded-lg bg-accent-500 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-accent-400"
        >
          {mode === 'create' ? 'Create account and continue' : 'Sign in and continue'}
        </button>

        <p className="mt-4 border-t border-ink-800 pt-3 text-[11px] leading-relaxed text-slate-500">
          No password needed. This is a local project, so your email is only stored
          in this browser to label your session — it is never sent anywhere and there
          is no account server.
        </p>
      </form>
    </div>
  )
}
