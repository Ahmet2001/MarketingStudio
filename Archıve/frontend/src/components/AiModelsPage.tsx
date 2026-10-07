import {
  Check,
  ChevronRight,
  Cpu,
  KeyRound,
  Layers3,
  LoaderCircle,
  LockKeyhole,
  Pencil,
  Plus,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { useState } from "react";
import type { AiModel, AiProvider, AiProviderId } from "../types";

interface AiModelsPageProps {
  providers: AiProvider[];
  models: AiModel[];
  loading: boolean;
  onSaveKey: (provider: AiProviderId, apiKey: string) => Promise<void>;
  onRemoveKey: (provider: AiProviderId) => Promise<void>;
  onSaveModel: (model: AiModel) => Promise<void>;
  onDeleteModel: (modelId: string) => Promise<void>;
}

const EMPTY_MODEL: AiModel = {
  name: "",
  provider: "replicate",
  modelIdentifier: "",
  configuration: {
    aspect_ratio: "9:16",
    output_format: "png",
    num_outputs: 1,
  },
  enabled: true,
  isDefault: false,
};

function providerLabel(provider: AiProviderId): string {
  if (provider === "fal") return "fal.ai";
  if (provider === "together") return "Together AI";
  if (provider === "gemini") return "Google Gemini";
  return "Replicate";
}

export function AiModelsPage({
  providers,
  models,
  loading,
  onSaveKey,
  onRemoveKey,
  onSaveModel,
  onDeleteModel,
}: AiModelsPageProps) {
  const [keys, setKeys] = useState<Record<AiProviderId, string>>({
    replicate: "",
    fal: "",
    together: "",
    gemini: "",
  });
  const [busyProvider, setBusyProvider] = useState<AiProviderId | null>(null);
  const [credentialError, setCredentialError] = useState("");
  const [editing, setEditing] = useState<AiModel | null>(null);
  const [configJson, setConfigJson] = useState("{}");
  const [formError, setFormError] = useState("");
  const [savingModel, setSavingModel] = useState(false);

  const openModelForm = (model?: AiModel) => {
    const value = model ? { ...model } : { ...EMPTY_MODEL };
    setEditing(value);
    setConfigJson(JSON.stringify(value.configuration, null, 2));
    setFormError("");
  };

  const handleKeySave = async (provider: AiProviderId) => {
    const apiKey = keys[provider].trim();
    if (!apiKey) return;
    setBusyProvider(provider);
    setCredentialError("");
    try {
      await onSaveKey(provider, apiKey);
      setKeys((current) => ({ ...current, [provider]: "" }));
    } catch (error) {
      setCredentialError(
        error instanceof Error ? error.message : "Could not save API key.",
      );
    } finally {
      setBusyProvider(null);
    }
  };

  const handleKeyRemove = async (provider: AiProviderId) => {
    setBusyProvider(provider);
    setCredentialError("");
    try {
      await onRemoveKey(provider);
    } catch (error) {
      setCredentialError(
        error instanceof Error ? error.message : "Could not remove API key.",
      );
    } finally {
      setBusyProvider(null);
    }
  };

  const handleModelSave = async () => {
    if (!editing) return;
    setFormError("");
    let configuration: Record<string, unknown>;
    try {
      const parsed = JSON.parse(configJson) as unknown;
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
        throw new Error("Configuration must be a JSON object.");
      }
      configuration = parsed as Record<string, unknown>;
    } catch (error) {
      setFormError(
        error instanceof Error ? error.message : "Configuration is not valid JSON.",
      );
      return;
    }
    if (!editing.name.trim() || !editing.modelIdentifier.trim()) {
      setFormError("Add a display name and model identifier.");
      return;
    }
    setSavingModel(true);
    try {
      await onSaveModel({
        ...editing,
        name: editing.name.trim(),
        modelIdentifier: editing.modelIdentifier.trim(),
        configuration,
      });
      setEditing(null);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Could not save model.");
    } finally {
      setSavingModel(false);
    }
  };

  const handleModelDelete = async (model: AiModel) => {
    if (!model.id) return;
    if (!window.confirm(`Remove ${model.name} from your model list?`)) return;
    setCredentialError("");
    try {
      await onDeleteModel(model.id);
    } catch (error) {
      setCredentialError(
        error instanceof Error ? error.message : "Could not remove model.",
      );
    }
  };

  return (
    <section className="ai-models-page">
      <div className="page-heading-row">
        <div>
          <span className="page-kicker">
            <Cpu size={14} />
            AI infrastructure
          </span>
          <h1>API & models</h1>
          <p>
            Bring your own provider keys and build the visual model list used by
            video projects.
          </p>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={() => openModelForm()}
        >
          <Plus size={16} />
          Add model
        </button>
      </div>

      <div className="connection-security">
        <ShieldCheck size={20} />
        <div>
          <strong>Your API keys stay on the server</strong>
          <span>
            Keys are encrypted at rest and injected only into generation workers.
          </span>
        </div>
      </div>

      <div className="provider-api-grid">
        {providers.map((provider) => (
          <article className="provider-api-card" key={provider.provider}>
            <div className="provider-api-heading">
              <span className={`provider-logo provider-${provider.provider}`}>
                {provider.provider === "fal" ? (
                  <Zap size={21} />
                ) : provider.provider === "together" ? (
                  <Layers3 size={21} />
                ) : provider.provider === "gemini" ? (
                  <Sparkles size={21} />
                ) : (
                  <Cpu size={21} />
                )}
              </span>
              <div>
                <h2>{provider.name}</h2>
                <span
                  className={`credential-state ${
                    provider.configured ? "is-configured" : ""
                  }`}
                >
                  {provider.configured ? <Check size={11} /> : <KeyRound size={11} />}
                  {provider.configured ? "Configured" : "Key required"}
                </span>
              </div>
            </div>
            <p>{provider.description}</p>
            {provider.configured ? (
              <div className="saved-key-row">
                <span>
                  <LockKeyhole size={14} />
                  {provider.keyHint}
                </span>
                <button
                  type="button"
                  disabled={busyProvider === provider.provider}
                  onClick={() => void handleKeyRemove(provider.provider)}
                >
                  Remove
                </button>
              </div>
            ) : (
              <div className="api-key-entry">
                <label htmlFor={`${provider.provider}-api-key`}>API key</label>
                <div>
                  <input
                    id={`${provider.provider}-api-key`}
                    type="password"
                    value={keys[provider.provider]}
                    autoComplete="off"
                    placeholder={
                      provider.provider === "replicate"
                        ? "r8_••••••••••••"
                        : provider.provider === "fal"
                          ? "fal key"
                          : provider.provider === "together"
                            ? "Together API key"
                            : "Gemini API key"
                    }
                    onChange={(event) =>
                      setKeys((current) => ({
                        ...current,
                        [provider.provider]: event.target.value,
                      }))
                    }
                  />
                  <button
                    type="button"
                    disabled={
                      !keys[provider.provider].trim() ||
                      busyProvider === provider.provider
                    }
                    onClick={() => void handleKeySave(provider.provider)}
                  >
                    {busyProvider === provider.provider ? (
                      <LoaderCircle className="spin" size={15} />
                    ) : (
                      <Save size={15} />
                    )}
                    Save
                  </button>
                </div>
              </div>
            )}
          </article>
        ))}
      </div>
      {credentialError ? (
        <div className="form-error" role="alert">
          {credentialError}
        </div>
      ) : null}

      <div className="model-library-heading">
        <div>
          <span className="page-kicker">Reusable presets</span>
          <h2>Model list</h2>
        </div>
        <span>{models.length} models</span>
      </div>

      {loading ? (
        <div className="empty-state">
          <LoaderCircle className="spin" size={28} />
          <h2>Loading model list</h2>
        </div>
      ) : (
        <div className="model-list">
          {models.map((model) => {
            const provider = providers.find(
              (item) => item.provider === model.provider,
            );
            return (
              <article className="model-row" key={model.id}>
                <span className={`model-provider-mark provider-${model.provider}`}>
                  {model.provider === "fal" ? (
                    <Zap size={18} />
                  ) : model.provider === "together" ? (
                    <Layers3 size={18} />
                  ) : model.provider === "gemini" ? (
                    <Sparkles size={18} />
                  ) : (
                    <Cpu size={18} />
                  )}
                </span>
                <div className="model-row-copy">
                  <div>
                    <h3>{model.name}</h3>
                    {model.isDefault ? <span>Default</span> : null}
                    {!model.enabled ? <span className="is-muted">Disabled</span> : null}
                  </div>
                  <code>{model.modelIdentifier}</code>
                  <small>
                    {providerLabel(model.provider)} ·{" "}
                    {Object.keys(model.configuration).length} configured inputs ·{" "}
                    {provider?.configured ? "API ready" : "API key needed"}
                  </small>
                </div>
                <div className="model-row-actions">
                  <button
                    type="button"
                    aria-label={`Edit ${model.name}`}
                    onClick={() => openModelForm(model)}
                  >
                    <Pencil size={15} />
                  </button>
                  {!model.builtIn && model.id ? (
                    <button
                      className="danger-icon-button"
                      type="button"
                      aria-label={`Delete ${model.name}`}
                      onClick={() => void handleModelDelete(model)}
                    >
                      <Trash2 size={15} />
                    </button>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {editing ? (
        <div className="model-editor-backdrop" role="presentation">
          <section
            className="model-editor"
            role="dialog"
            aria-modal="true"
            aria-labelledby="model-editor-title"
          >
            <div className="model-editor-heading">
              <div>
                <span>{editing.id ? "Edit preset" : "New preset"}</span>
                <h2 id="model-editor-title">
                  {editing.id ? editing.name : "Add an AI model"}
                </h2>
              </div>
              <button
                type="button"
                aria-label="Close model editor"
                onClick={() => setEditing(null)}
              >
                <X size={19} />
              </button>
            </div>

            <div className="model-editor-grid">
              <label>
                <span>Display name</span>
                <input
                  value={editing.name}
                  placeholder="FLUX Schnell"
                  onChange={(event) =>
                    setEditing((current) =>
                      current ? { ...current, name: event.target.value } : current,
                    )
                  }
                />
              </label>
              <label>
                <span>Provider</span>
                <select
                  value={editing.provider}
                  onChange={(event) =>
                    setEditing((current) =>
                      current
                        ? {
                            ...current,
                            provider: event.target.value as AiProviderId,
                          }
                        : current,
                    )
                  }
                >
                  <option value="replicate">Replicate</option>
                  <option value="fal">fal.ai</option>
                  <option value="together">Together AI</option>
                  <option value="gemini">Google Gemini</option>
                </select>
              </label>
              <label className="model-identifier-field">
                <span>Model identifier</span>
                <input
                  value={editing.modelIdentifier}
                  placeholder={
                    editing.provider === "replicate"
                      ? "black-forest-labs/flux-schnell"
                      : editing.provider === "fal"
                        ? "fal-ai/flux/schnell"
                        : editing.provider === "together"
                          ? "black-forest-labs/FLUX.1-schnell"
                          : "gemini-2.5-flash-image"
                  }
                  onChange={(event) =>
                    setEditing((current) =>
                      current
                        ? { ...current, modelIdentifier: event.target.value }
                        : current,
                    )
                  }
                />
                <small>Use the exact owner/model path shown by the provider.</small>
              </label>
              <label className="model-config-field">
                <span>Model input configuration</span>
                <textarea
                  value={configJson}
                  rows={11}
                  spellCheck={false}
                  onChange={(event) => setConfigJson(event.target.value)}
                />
                <small>
                  Valid JSON. Storyforge adds the prompt and scene seed automatically.
                </small>
              </label>
            </div>

            <div className="model-editor-options">
              <label>
                <input
                  type="checkbox"
                  checked={editing.enabled}
                  onChange={(event) =>
                    setEditing((current) =>
                      current
                        ? { ...current, enabled: event.target.checked }
                        : current,
                    )
                  }
                />
                Available when creating videos
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={editing.isDefault}
                  onChange={(event) =>
                    setEditing((current) =>
                      current
                        ? { ...current, isDefault: event.target.checked }
                        : current,
                    )
                  }
                />
                Make default model
              </label>
            </div>

            {formError ? (
              <div className="form-error" role="alert">
                {formError}
              </div>
            ) : null}
            <div className="model-editor-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => setEditing(null)}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={savingModel}
                onClick={() => void handleModelSave()}
              >
                {savingModel ? (
                  <LoaderCircle className="spin" size={16} />
                ) : (
                  <Save size={16} />
                )}
                Save model
                <ChevronRight size={15} />
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
