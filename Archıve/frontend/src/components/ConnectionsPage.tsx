import {
  Check,
  ExternalLink,
  Instagram,
  Music2,
  Plug,
  ShieldCheck,
  Youtube,
} from "lucide-react";
import type { AppConnection } from "../types";

interface ConnectionsPageProps {
  connections: AppConnection[];
  loading: boolean;
  onConnect: (provider: AppConnection["provider"]) => Promise<void>;
  onDisconnect: (provider: AppConnection["provider"]) => Promise<void>;
}

const providerIcons = {
  youtube: Youtube,
  tiktok: Music2,
  instagram: Instagram,
};

export function ConnectionsPage({
  connections,
  loading,
  onConnect,
  onDisconnect,
}: ConnectionsPageProps) {
  return (
    <section className="connections-page">
      <div className="page-heading-row">
        <div>
          <span className="page-kicker">Distribution</span>
          <h1>App connections</h1>
          <p>Connect publishing destinations without exposing account passwords.</p>
        </div>
      </div>

      <div className="connection-security">
        <ShieldCheck size={20} />
        <div>
          <strong>Server-side OAuth</strong>
          <span>
            Access and refresh tokens are encrypted and never sent to the browser.
          </span>
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <Plug className="spin" size={28} />
          <h2>Checking app connections</h2>
        </div>
      ) : (
        <div className="connections-grid">
          {connections.map((connection) => {
            const Icon = providerIcons[connection.provider];
            const connected = connection.status === "connected";
            return (
              <article
                className={`connection-card provider-${connection.provider}`}
                key={connection.provider}
              >
                <div className="connection-card-top">
                  <span className="provider-icon">
                    <Icon size={25} />
                  </span>
                  <span
                    className={`connection-state ${
                      connected ? "is-connected" : ""
                    }`}
                  >
                    {connected ? <Check size={12} /> : null}
                    {connected ? "Connected" : connection.availabilityNote}
                  </span>
                </div>
                <h2>{connection.name}</h2>
                <p>{connection.description}</p>
                {connected ? (
                  <div className="connected-account">
                    <span>Connected as</span>
                    <strong>{connection.accountLabel}</strong>
                  </div>
                ) : null}
                <button
                  className={connected ? "disconnect-button" : "connect-button"}
                  type="button"
                  disabled={!connected && !connection.available}
                  onClick={() =>
                    void (connected
                      ? onDisconnect(connection.provider)
                      : onConnect(connection.provider))
                  }
                >
                  {connected ? "Disconnect" : "Connect app"}
                  {!connected && connection.available ? (
                    <ExternalLink size={15} />
                  ) : null}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
