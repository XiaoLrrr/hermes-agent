import { DEFAULT_REASONING_EFFORT, isReasoningEffort, REASONING_EFFORTS, type ReasoningEffort } from '@hermes/shared'

import { normalize } from '@/lib/text'

/** Compact labels for chrome where space is tight (pill, picker rows). Menus
 *  and settings use the translated `shell.modelOptions` strings instead. */
const SHORT_LABELS: Record<string, string> = {
  none: 'Off',
  minimal: 'Min',
  low: 'Low',
  medium: 'Med',
  high: 'High',
  xhigh: 'XHigh',
  max: 'Max',
  ultra: 'Ultra'
}

export function reasoningEffortLabel(effort: string): string {
  const key = normalize(effort)

  return key ? (SHORT_LABELS[key] ?? effort) : ''
}

/** Thinking is on unless a level explicitly says otherwise; an empty value
 *  means "inherit", so it resolves through `fallback` first. */
export const isThinkingEnabled = (effort: string, fallback: string = DEFAULT_REASONING_EFFORT): boolean =>
  normalize(effort || fallback) !== 'none'

/** The level a scale control should show. Empty inherits `fallback`; `none`
 *  (thinking off) selects nothing; anything unrecognized clamps to the default. */
export function resolveReasoningEffort(effort: string, fallback: string = DEFAULT_REASONING_EFFORT): string {
  const value = normalize(effort || fallback)

  if (value === 'none') {
    return ''
  }

  return isReasoningEffort(value) ? value : DEFAULT_REASONING_EFFORT
}

export function supportedReasoningEffort(effort: string, supported?: readonly string[] | null): string {
  const available = REASONING_EFFORTS.filter(value => !supported || supported.includes(value))
  const requested = resolveReasoningEffort(effort)

  if (requested && available.includes(requested as ReasoningEffort)) return requested
  if (available.includes(DEFAULT_REASONING_EFFORT)) return DEFAULT_REASONING_EFFORT
  if (available.includes('high')) return 'high'

  return available[0] ?? ''
}
