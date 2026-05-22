"use client"

interface RiskGaugeProps {
  score: number
  size?: number
}

export function RiskGauge({ score, size = 120 }: RiskGaugeProps) {
  const radius = (size - 16) / 2
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const offset = circumference - progress

  let color: string
  let label: string
  let bgRing: string

  if (score < 30) {
    color = "stroke-emerald-500"
    bgRing = "stroke-emerald-500/10"
    label = "Low Risk"
  } else if (score < 70) {
    color = "stroke-amber-500"
    bgRing = "stroke-amber-500/10"
    label = "Medium Risk"
  } else {
    color = "stroke-red-500"
    bgRing = "stroke-red-500/10"
    label = "High Risk"
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="-rotate-90"
          viewBox={`0 0 ${size} ${size}`}
        >
          {/* Background ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={8}
            className={bgRing}
          />
          {/* Progress ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={8}
            strokeLinecap="round"
            className={`${color} transition-all duration-1000 ease-out`}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold">{score}</span>
          <span className="text-[10px] text-muted-foreground">/100</span>
        </div>
      </div>
      <span className="text-xs font-semibold text-muted-foreground">{label}</span>
    </div>
  )
}
