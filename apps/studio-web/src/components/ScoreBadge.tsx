import { TrendingUp } from 'lucide-react'

export function ScoreBadge({ score }: { score: number }) {
  return (
    <span className="score-badge" title="Predicted creative score">
      <TrendingUp size={13} />
      {score}
    </span>
  )
}
