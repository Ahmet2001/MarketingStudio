import {
  Bell,
  Check,
  ChevronRight,
  CreditCard,
  Globe2,
  KeyRound,
  Languages,
  Moon,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import { useState } from "react";

export function ProfilePage() {
  return (
    <section className="account-page">
      <div className="page-heading-row">
        <div>
          <span className="page-kicker">Account</span>
          <h1>Your profile</h1>
          <p>Manage your creator identity and see your studio activity.</p>
        </div>
        <button className="secondary-button" type="button">
          Edit profile
        </button>
      </div>

      <div className="profile-hero">
        <div className="large-avatar">RA</div>
        <div>
          <h2>Rifat A.</h2>
          <p>Short-form storyteller · Istanbul</p>
          <div className="profile-tags">
            <span>
              <Check size={13} /> Creator profile complete
            </span>
            <span>Pro plan</span>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <article>
          <span>Videos created</span>
          <strong>24</strong>
          <small>+6 this month</small>
        </article>
        <article>
          <span>Minutes generated</span>
          <strong>18.4</strong>
          <small>Across 4 formats</small>
        </article>
        <article>
          <span>Favorite mode</span>
          <strong className="stat-text">AI photo story</strong>
          <small>11 projects</small>
        </article>
      </div>

      <div className="account-card">
        <div className="account-card-heading">
          <h2>Creator details</h2>
          <p>Used to personalize scripts and narration suggestions.</p>
        </div>
        <div className="detail-row">
          <span>
            <UserRound size={18} /> Display name
          </span>
          <strong>Rifat A.</strong>
        </div>
        <div className="detail-row">
          <span>
            <Languages size={18} /> Default language
          </span>
          <strong>English</strong>
        </div>
        <div className="detail-row">
          <span>
            <Globe2 size={18} /> Timezone
          </span>
          <strong>Europe / Istanbul</strong>
        </div>
      </div>
    </section>
  );
}

interface ToggleRowProps {
  icon: typeof Bell;
  title: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}

function ToggleRow({
  icon: Icon,
  title,
  description,
  enabled,
  onToggle,
}: ToggleRowProps) {
  return (
    <div className="setting-row">
      <span className="setting-icon">
        <Icon size={18} />
      </span>
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
      <button
        className={`toggle ${enabled ? "is-on" : ""}`}
        type="button"
        onClick={onToggle}
        aria-pressed={enabled}
        aria-label={`${enabled ? "Disable" : "Enable"} ${title}`}
      >
        <span />
      </button>
    </div>
  );
}

export function SettingsPage() {
  const [notifications, setNotifications] = useState(true);
  const [darkExport, setDarkExport] = useState(false);

  return (
    <section className="account-page">
      <div className="page-heading-row">
        <div>
          <span className="page-kicker">Preferences</span>
          <h1>Settings</h1>
          <p>Set the defaults Storyforge uses for every new project.</p>
        </div>
      </div>

      <div className="settings-layout">
        <div className="account-card settings-card">
          <div className="account-card-heading">
            <h2>Studio preferences</h2>
            <p>Adjust generation behavior and notifications.</p>
          </div>
          <ToggleRow
            icon={Bell}
            title="Generation notifications"
            description="Tell me when a video is ready to review."
            enabled={notifications}
            onToggle={() => setNotifications((value) => !value)}
          />
          <ToggleRow
            icon={Moon}
            title="High-contrast captions"
            description="Use dark caption plates for stronger readability."
            enabled={darkExport}
            onToggle={() => setDarkExport((value) => !value)}
          />
          <button className="setting-link-row" type="button">
            <span className="setting-icon">
              <Languages size={18} />
            </span>
            <span>
              <strong>Language & voice</strong>
              <small>English · Serious narrator</small>
            </span>
            <ChevronRight size={18} />
          </button>
          <button className="setting-link-row" type="button">
            <span className="setting-icon">
              <Sparkles size={18} />
            </span>
            <span>
              <strong>Generation defaults</strong>
              <small>45 seconds · 9:16 · 5 scenes</small>
            </span>
            <ChevronRight size={18} />
          </button>
        </div>

        <div className="account-card settings-card">
          <div className="account-card-heading">
            <h2>Billing & security</h2>
            <p>Manage your plan, API connections, and account.</p>
          </div>
          <button className="setting-link-row" type="button">
            <span className="setting-icon">
              <CreditCard size={18} />
            </span>
            <span>
              <strong>Pro plan</strong>
              <small>Renews August 21 · 12 minutes remaining</small>
            </span>
            <ChevronRight size={18} />
          </button>
          <button className="setting-link-row" type="button">
            <span className="setting-icon">
              <KeyRound size={18} />
            </span>
            <span>
              <strong>Connected services</strong>
              <small>Gemini, ElevenLabs, Replicate</small>
            </span>
            <ChevronRight size={18} />
          </button>
          <button className="setting-link-row" type="button">
            <span className="setting-icon">
              <ShieldCheck size={18} />
            </span>
            <span>
              <strong>Privacy & security</strong>
              <small>Password, sessions, and data controls</small>
            </span>
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </section>
  );
}
