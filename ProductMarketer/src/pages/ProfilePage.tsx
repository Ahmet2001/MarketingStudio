import { useEffect, useState } from 'react'
import { Camera, Check, Mail, ShieldCheck, Upload, UserRound } from 'lucide-react'
import { getProfile, saveProfile, type ProfileRecord } from '../lib/api'

interface ProfilePageProps {
  onSaved: () => void
}

export function ProfilePage({ onSaved }: ProfilePageProps) {
  const [profile, setProfile] = useState<ProfileRecord>({
    firstName: 'Alex',
    lastName: 'Morgan',
    email: 'alex@kora.co',
    jobTitle: 'Creative Director',
    timezone: 'Europe/Istanbul',
    bio: 'Building bold product stories for Kora Coffee.',
  })
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getProfile().then((record) => {
      if (active) setProfile(record)
    }).catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  const update = (field: keyof ProfileRecord, value: string) => {
    setProfile((current) => ({ ...current, [field]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      await saveProfile(profile)
      onSaved()
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Could not save profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page account-page">
      <section className="collection-heading">
        <div><p className="eyebrow">YOUR ACCOUNT</p><h2>Profile</h2><p className="page-subtitle">Manage how you appear across your workspace and shared projects.</p>{saveError ? <p className="inline-save-error" role="alert">{saveError}</p> : null}</div>
        <button type="button" className="primary-button" onClick={() => void handleSave()} disabled={saving}><Check size={15} /> {saving ? 'Saving…' : 'Save changes'}</button>
      </section>
      <div className="account-layout">
        <aside className="profile-card">
          <div className="profile-avatar"><UserRound size={40} /><button type="button" aria-label="Change profile photo"><Camera size={14} /></button></div>
          <h3>{profile.firstName} {profile.lastName}</h3><p>{profile.jobTitle}</p>
          <span><ShieldCheck size={13} /> Workspace owner</span>
          <button type="button" className="secondary-button"><Upload size={14} /> Upload new photo</button>
        </aside>
        <div className="account-form-card">
          <div className="settings-section-heading"><span><UserRound size={17} /></span><div><h3>Personal information</h3><p>Used for project activity and collaboration.</p></div></div>
          <div className="account-form-grid">
            <label><span>First name</span><input value={profile.firstName} onChange={(event) => update('firstName', event.target.value)} /></label>
            <label><span>Last name</span><input value={profile.lastName} onChange={(event) => update('lastName', event.target.value)} /></label>
            <label className="full-field"><span>Email address</span><div className="input-with-icon"><Mail size={15} /><input value={profile.email} onChange={(event) => update('email', event.target.value)} /></div></label>
            <label><span>Job title</span><input value={profile.jobTitle} onChange={(event) => update('jobTitle', event.target.value)} /></label>
            <label><span>Timezone</span><select value={profile.timezone} onChange={(event) => update('timezone', event.target.value)}><option>Europe/Istanbul</option><option>America/New_York</option><option>Europe/London</option></select></label>
            <label className="full-field"><span>Short bio</span><textarea value={profile.bio} onChange={(event) => update('bio', event.target.value)} /></label>
          </div>
        </div>
      </div>
    </div>
  )
}
