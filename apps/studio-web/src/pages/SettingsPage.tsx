import { useEffect, useState } from 'react'
import { Bell, Check, Coins, Image, LockKeyhole, Palette, Sparkles } from 'lucide-react'
import { getSettings, saveSettings, type SettingsRecord } from '../lib/api'

interface SettingsPageProps {
  onSaved: () => void
}

const settings: Array<{ icon: typeof Sparkles; field: keyof SettingsRecord; title: string; description: string }> = [
  { icon: Sparkles, field: 'aiGeneration', title: 'AI generation', description: 'Use brand memory and previous approvals to improve outputs.' },
  { icon: Image, field: 'backgroundRemoval', title: 'Automatic background removal', description: 'Remove product backgrounds immediately after upload.' },
  { icon: Bell, field: 'generationNotifications', title: 'Generation notifications', description: 'Notify me when long-running videos and batches are ready.' },
  { icon: Palette, field: 'experimentalStyles', title: 'Experimental styles', description: 'Show beta visual styles in generation workflows.' },
]

export function SettingsPage({ onSaved }: SettingsPageProps) {
  const [values, setValues] = useState<SettingsRecord>({
    aiGeneration: true,
    backgroundRemoval: true,
    generationNotifications: true,
    experimentalStyles: false,
  })
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getSettings().then((record) => {
      if (active) setValues(record)
    }).catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      await saveSettings(values)
      onSaved()
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Could not save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page account-page">
      <section className="collection-heading">
        <div><p className="eyebrow">WORKSPACE</p><h2>Settings</h2><p className="page-subtitle">Control generation defaults, notifications, privacy, and usage.</p>{saveError ? <p className="inline-save-error" role="alert">{saveError}</p> : null}</div>
        <button type="button" className="primary-button" onClick={() => void handleSave()} disabled={saving}><Check size={15} /> {saving ? 'Saving…' : 'Save settings'}</button>
      </section>
      <div className="settings-layout">
        <section className="settings-panel">
          <div className="settings-section-heading"><span><Sparkles size={17} /></span><div><h3>Creation preferences</h3><p>Defaults applied to new projects.</p></div></div>
          <div className="setting-list">
            {settings.map(({ icon: Icon, field, title, description }) => (
              <label className="setting-row" key={title}>
                <span className="setting-icon"><Icon size={16} /></span>
                <span><strong>{title}</strong><small>{description}</small></span>
                <input
                  type="checkbox"
                  checked={values[field]}
                  onChange={(event) => setValues((current) => ({ ...current, [field]: event.target.checked }))}
                />
                <i />
              </label>
            ))}
          </div>
        </section>
        <aside className="settings-side">
          <section>
            <div className="settings-section-heading"><span><Coins size={17} /></span><div><h3>Plan & usage</h3><p>Professional plan</p></div></div>
            <div className="usage-meter"><span><i /></span><p><strong>0 credits</strong><small>of 500 used this month</small></p></div>
            <button type="button" className="secondary-button">Manage plan</button>
          </section>
          <section>
            <div className="settings-section-heading"><span><LockKeyhole size={17} /></span><div><h3>Privacy</h3><p>Your products stay private.</p></div></div>
            <p className="settings-note">Uploads and generated assets are encrypted and are not used to train shared models.</p>
            <button type="button" className="text-button">Review data controls</button>
          </section>
        </aside>
      </div>
    </div>
  )
}
