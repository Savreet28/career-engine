import { PIPELINE_STAGES } from '../services/api.js'

const ICONS = {
  done: (
    <svg className="h-3.5 w-3.5 text-good-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 111.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z" clipRule="evenodd" />
    </svg>
  ),
  warning: (
    <svg className="h-3.5 w-3.5 text-warn-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.19-1.458-1.517-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
    </svg>
  ),
  skipped: (
    <svg className="h-3.5 w-3.5 text-slate-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9.75A.75.75 0 017.75 9h4.5a.75.75 0 010 1.5h-4.5A.75.75 0 017 9.75z" clipRule="evenodd" />
    </svg>
  ),
}

/**
 * Live pipeline progress.
 *
 * Every state shown here comes from a Server-Sent Event emitted by the backend
 * as the stage actually starts and finishes. There is no timer and no
 * simulated percentage: a stage that has not reported yet is simply "pending".
 */
export default function LoadingStages({ stages }) {
  return (
    <div className="rounded-xl border border-ink-700/70 bg-ink-900/70 p-5 shadow-lg shadow-black/20 backdrop-blur-sm">
      <div className="mb-3 flex items-center gap-2">
        <svg className="h-4 w-4 animate-spin text-accent-400" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
        <h2 className="text-sm font-semibold text-slate-100">Running analysis</h2>
      </div>

      <ol className="space-y-1" aria-live="polite">
        {PIPELINE_STAGES.map((stage) => {
          const state = stages[stage.id]
          const status = state?.status || 'pending'
          const running = status === 'running'
          return (
            <li
              key={stage.id}
              className={`flex items-start gap-2.5 rounded-lg px-2.5 py-2 transition ${
                running ? 'bg-accent-500/10' : ''
              }`}
            >
              <span className="mt-0.5 grid h-3.5 w-3.5 shrink-0 place-items-center">
                {running ? (
                  <span className="h-2 w-2 animate-pulse rounded-full bg-accent-400" />
                ) : status === 'pending' ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-ink-600" />
                ) : (
                  ICONS[status] || ICONS.done
                )}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className={`text-xs ${
                    status === 'pending' ? 'text-slate-600'
                      : running ? 'text-accent-300'
                      : 'text-slate-200'
                  }`}>
                    {stage.label}
                  </span>
                  {state?.ms !== undefined && (
                    <span className="shrink-0 text-[10px] tabular-nums text-slate-500">
                      {state.ms < 1000 ? `${Math.round(state.ms)} ms` : `${(state.ms / 1000).toFixed(1)} s`}
                    </span>
                  )}
                </div>
                {state?.detail && (
                  <p className={`mt-0.5 text-[11px] leading-relaxed ${
                    status === 'warning' ? 'text-warn-400' : 'text-slate-500'
                  }`}>
                    {state.detail}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
