interface MetricCardProps {
  label: string
  value: string
  tone?: 'good' | 'bad' | 'neutral'
  sub?: string
  hint?: string
}

export default function MetricCard({ label, value, tone = 'neutral', sub, hint }: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="label">
        {label}
        {hint && (
          <span className="info-tip" title={hint}>
            ⓘ
          </span>
        )}
      </div>
      <div className={`value${tone !== 'neutral' ? ` ${tone}` : ''}`}>{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}
