/**
 * Top bar. Product identity on the left, the signed-in session on the right.
 * Backend/index diagnostics deliberately stay out of the header — they live in
 * the API (/api/health, /api/rag/status) rather than in the user's way.
 */
export default function Navbar({ email, onSignOut }) {
  return (
    <header className="sticky top-0 z-20 border-b border-ink-700/70 bg-ink-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-x-4 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent-500/15 ring-1 ring-accent-400/30">
            <svg className="h-4 w-4 text-accent-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l5-5 4 4 8-8M21 8v5h-5" />
            </svg>
          </span>
          <div className="leading-tight">
            <h1 className="text-[15px] font-semibold text-slate-100">Career Engine</h1>
            <p className="hidden text-[11px] text-slate-400 sm:block">
              ATS analysis &amp; job matching
            </p>
          </div>
        </div>

        {email && (
          <div className="ml-auto flex items-center gap-2.5">
            <span className="hidden max-w-[200px] truncate text-[11px] text-slate-400 sm:block" title={email}>
              {email}
            </span>
            <button
              type="button"
              onClick={onSignOut}
              className="rounded-md border border-ink-600 px-2 py-1 text-[11px] text-slate-400 transition hover:border-accent-400 hover:text-slate-100"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
