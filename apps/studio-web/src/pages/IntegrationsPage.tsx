import { ExternalLink, Link2, Plus, ShieldCheck } from 'lucide-react'

const integrations = [
  { name: 'Meta Ads', code: 'M', color: 'meta', description: 'Sync campaign performance and push media.' },
  { name: 'Google Ads', code: 'G', color: 'google', description: 'Analyze creatives and upload new assets.' },
  { name: 'LinkedIn Ads', code: 'in', color: 'linkedin', description: 'Publish media for B2B campaigns.' },
  { name: 'TikTok Ads', code: '♪', color: 'tiktok', description: 'Bring short-form performance into one view.' },
  { name: 'Shopify', code: 'S', color: 'shopify', description: 'Import products, images, and offers.' },
  { name: 'Google Drive', code: '△', color: 'drive', description: 'Export approved assets to shared folders.' },
]

export function IntegrationsPage() {
  return (
    <div className="page collection-page">
      <section className="collection-heading">
        <div><p className="eyebrow">CONNECTIONS</p><h2>Integrations</h2><p className="page-subtitle">Connect your ad, commerce, and asset workflows.</p></div>
        <button type="button" className="secondary-button"><Plus size={15} /> Request integration</button>
      </section>
      <section className="integration-security-banner">
        <span><ShieldCheck size={19} /></span>
        <div><strong>Your connections are protected</strong><p>OAuth tokens are encrypted and can be revoked at any time.</p></div>
        <button type="button">Security details <ExternalLink size={13} /></button>
      </section>
      <div className="integration-grid">
        {integrations.map((integration) => (
          <article className="integration-card" key={integration.name}>
            <div className={`integration-logo ${integration.color}`}>{integration.code}</div>
            <div className="integration-copy"><strong>{integration.name}</strong><p>{integration.description}</p></div>
            <button type="button" className="integration-connect"><Link2 size={13} /> Connect</button>
          </article>
        ))}
      </div>
    </div>
  )
}
