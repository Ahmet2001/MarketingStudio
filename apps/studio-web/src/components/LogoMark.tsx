export function LogoMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo-lockup" aria-label="ProductMarketer home">
      <span className="logo-mark" aria-hidden="true">
        <span />
        <span />
      </span>
      {compact ? null : <span className="logo-word">ProductMarketer</span>}
    </div>
  )
}
