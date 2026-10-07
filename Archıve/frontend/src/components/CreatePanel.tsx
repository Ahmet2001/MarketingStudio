import {
  ArrowLeft,
  ArrowRight,
  CalendarClock,
  Check,
  ChevronDown,
  Clock3,
  Cpu,
  Dices,
  LoaderCircle,
  KeyRound,
  Plus,
  Settings2,
  Sparkles,
} from "lucide-react";
import { useId, useState } from "react";
import { getLuckyPrompt } from "../api";
import type {
  AiModel,
  AiProvider,
  CreateProjectOptions,
  ProjectMode,
} from "../types";

interface CreatePanelProps {
  mode: ProjectMode;
  aiModels: AiModel[];
  aiProviders: AiProvider[];
  onBack: () => void;
  onOpenAiModels: () => void;
  onCreate: (options: CreateProjectOptions) => Promise<void>;
  onSchedule: (
    options: CreateProjectOptions,
    runAt: string,
  ) => Promise<void>;
}

const durations = [30, 45, 60, 90];

function localDateTimeValue(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function CreatePanel({
  mode,
  aiModels,
  aiProviders,
  onBack,
  onOpenAiModels,
  onCreate,
  onSchedule,
}: CreatePanelProps) {
  const topicId = useId();
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState(45);
  const [language, setLanguage] = useState("English");
  const [scenes, setScenes] = useState(7);
  const [niche, setNiche] = useState("general-storytelling");
  const [skipResearch, setSkipResearch] = useState(false);
  const [researchRegion, setResearchRegion] = useState("us-en");
  const [speakingStyle, setSpeakingStyle] =
    useState<CreateProjectOptions["settings"]["speakingStyle"]>("serious");
  const [characterStyle, setCharacterStyle] =
    useState<CreateProjectOptions["settings"]["characterStyle"]>("auto");
  const [realPhotoMinMatch, setRealPhotoMinMatch] = useState(70);
  const availableAiModels = aiModels.filter((model) => model.enabled);
  const [aiModelId, setAiModelId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [ideaStatus, setIdeaStatus] = useState("");
  const [ideaError, setIdeaError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleAt, setScheduleAt] = useState(() =>
    localDateTimeValue(new Date(Date.now() + 60 * 60 * 1000)),
  );

  const effectiveAiModelId =
    aiModelId ??
    availableAiModels.find((model) => model.isDefault)?.id ??
    availableAiModels[0]?.id ??
    null;
  const selectedAiModel = availableAiModels.find(
    (model) => model.id === effectiveAiModelId,
  );
  const selectedProvider = aiProviders.find(
    (provider) => provider.provider === selectedAiModel?.provider,
  );

  const projectOptions = (): CreateProjectOptions => ({
    topic: topic.trim(),
    duration,
    language,
    scenes,
    settings: {
      niche,
      skipResearch,
      researchRegion,
      speakingStyle,
      speechSpeed: null,
      characterStyle,
      realPhotoMinMatch,
      aiModelId: mode.id === "ai-photos" ? effectiveAiModelId : null,
    },
  });

  const submit = async (action: () => Promise<void>) => {
    setSubmitError("");
    setIsSubmitting(true);
    try {
      await action();
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Could not start this project.",
      );
      setIsSubmitting(false);
    }
  };

  const handleSubmit = () => submit(() => onCreate(projectOptions()));

  const handleSchedule = () =>
    submit(() =>
      onSchedule(projectOptions(), new Date(scheduleAt).toISOString()),
    );

  const handleLuckyPrompt = async () => {
    setIdeaError("");
    setIdeaStatus("");
    setIsSuggesting(true);
    try {
      const idea = await getLuckyPrompt(mode.id, language, niche);
      setTopic(idea.prompt);
      setIdeaStatus(
        idea.source === "ai"
          ? "Your AI-generated idea is ready."
          : "Here’s a fresh studio idea.",
      );
    } catch (error) {
      setIdeaError(
        error instanceof Error
          ? error.message
          : "Could not find a lucky idea right now.",
      );
    } finally {
      setIsSuggesting(false);
    }
  };

  return (
    <section className="create-panel" aria-labelledby="create-panel-title">
      <button className="back-link" type="button" onClick={onBack}>
        <ArrowLeft size={17} />
        All video types
      </button>

      <div className="create-panel-layout">
        <div className="create-form-card">
          <div className="selected-mode-heading">
            <span className={`selected-mode-icon accent-${mode.accent}`}>
              <mode.Icon size={22} />
            </span>
            <div>
              <span>{mode.engine}</span>
              <h1 id="create-panel-title">{mode.title}</h1>
            </div>
          </div>

          <div className="prompt-label-row">
            <label className="field-label" htmlFor={topicId}>
              What should your video be about?
            </label>
            <button
              className="lucky-prompt-button"
              type="button"
              disabled={isSuggesting || isSubmitting}
              onClick={() => void handleLuckyPrompt()}
            >
              {isSuggesting ? (
                <LoaderCircle className="spin" size={15} />
              ) : (
                <Dices size={15} />
              )}
              {isSuggesting ? "Finding an idea…" : "I feel lucky today"}
            </button>
          </div>
          <div className="topic-field">
            <textarea
              id={topicId}
              value={topic}
              onChange={(event) => {
                setTopic(event.target.value);
                setIdeaStatus("");
                setIdeaError("");
              }}
              placeholder={mode.promptPlaceholder}
              maxLength={500}
              rows={6}
              autoFocus
            />
            <div className="topic-field-footer">
              <span>
                <Sparkles size={14} /> AI will research and write the script
              </span>
              <span>{topic.length}/500</span>
            </div>
          </div>
          {ideaStatus ? (
            <p className="idea-status" role="status">
              <Sparkles size={13} />
              {ideaStatus}
            </p>
          ) : null}
          {ideaError ? (
            <p className="idea-status is-error" role="alert">
              {ideaError}
            </p>
          ) : null}

          <div className="form-row">
            <fieldset>
              <legend>Duration</legend>
              <div className="segmented-options">
                {durations.map((item) => (
                  <button
                    className={duration === item ? "is-selected" : ""}
                    type="button"
                    key={item}
                    onClick={() => setDuration(item)}
                  >
                    {item} sec
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>Format</legend>
              <div className="locked-format">
                <strong>9:16</strong>
                <span>Vertical short</span>
              </div>
            </fieldset>
          </div>

          <label className="field-label" htmlFor="language">
            Narration language
          </label>
          <select
            id="language"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            <option>English</option>
            <option>Turkish</option>
            <option>Spanish</option>
            <option>German</option>
            <option>French</option>
          </select>

          {mode.id === "ai-photos" ? (
            <div className="visual-model-picker">
              <div className="visual-model-picker-heading">
                <span>
                  <Cpu size={16} />
                  Visual AI model
                </span>
                <button type="button" onClick={onOpenAiModels}>
                  Manage models
                </button>
              </div>
              {availableAiModels.length ? (
                <>
                  <select
                    value={effectiveAiModelId ?? ""}
                    onChange={(event) => setAiModelId(event.target.value)}
                    aria-label="Visual AI model"
                  >
                    {availableAiModels.map((model) => (
                      <option value={model.id} key={model.id}>
                        {model.name} ·{" "}
                        {model.provider === "fal"
                          ? "fal.ai"
                          : model.provider === "together"
                            ? "Together AI"
                            : model.provider === "gemini"
                              ? "Google Gemini"
                              : "Replicate"}
                      </option>
                    ))}
                  </select>
                  <div
                    className={`model-readiness ${
                      selectedProvider?.configured ? "is-ready" : ""
                    }`}
                  >
                    {selectedProvider?.configured ? (
                      <Check size={13} />
                    ) : (
                      <KeyRound size={13} />
                    )}
                    <span>
                      <strong>{selectedAiModel?.modelIdentifier}</strong>
                      {selectedProvider?.configured
                        ? `${selectedProvider.name} API ready`
                        : `Add a ${selectedProvider?.name ?? "provider"} API key to generate`}
                    </span>
                  </div>
                </>
              ) : (
                <button
                  className="empty-model-button"
                  type="button"
                  onClick={onOpenAiModels}
                >
                  <Plus size={15} />
                  Add your first visual model
                </button>
              )}
            </div>
          ) : null}

          <details className="advanced-settings">
            <summary>
              <span>
                <Settings2 size={16} />
                Advanced settings
              </span>
              <ChevronDown size={16} />
            </summary>
            <div className="advanced-settings-content">
              <div className="advanced-grid">
                <label>
                  <span>Scenes</span>
                  <select
                    value={scenes}
                    onChange={(event) => setScenes(Number(event.target.value))}
                  >
                    {[4, 5, 6, 7, 8, 9, 10].map((count) => (
                      <option value={count} key={count}>
                        {count} scenes
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Research region</span>
                  <select
                    value={researchRegion}
                    onChange={(event) => setResearchRegion(event.target.value)}
                  >
                    <option value="us-en">United States</option>
                    <option value="uk-en">United Kingdom</option>
                    <option value="tr-tr">Türkiye</option>
                  </select>
                </label>

                {mode.engine === "Storyteller engine" ? (
                  <>
                    <label>
                      <span>Narration style</span>
                      <select
                        value={speakingStyle}
                        onChange={(event) =>
                          setSpeakingStyle(
                            event.target.value as typeof speakingStyle,
                          )
                        }
                      >
                        <option value="serious">Serious</option>
                        <option value="mysterious">Mysterious</option>
                        <option value="excited">Excited</option>
                        <option value="sad">Reflective</option>
                        <option value="angry">Intense</option>
                      </select>
                    </label>
                    <label>
                      <span>Story niche</span>
                      <select
                        value={niche}
                        onChange={(event) => setNiche(event.target.value)}
                      >
                        <option value="general-storytelling">General story</option>
                        <option value="history">History</option>
                        <option value="horror">Horror</option>
                        <option value="psychology">Psychology</option>
                        <option value="motivation">Motivation</option>
                      </select>
                    </label>
                  </>
                ) : null}

                {mode.id === "ai-photos" ? (
                  <label>
                    <span>Character direction</span>
                    <select
                      value={characterStyle}
                      onChange={(event) =>
                        setCharacterStyle(
                          event.target.value as typeof characterStyle,
                        )
                      }
                    >
                      <option value="auto">Automatic</option>
                      <option value="life-sim">Stylized life simulation</option>
                      <option value="animal">Expressive animal</option>
                      <option value="horror">Non-graphic horror</option>
                      <option value="animated-human">Animated human</option>
                    </select>
                  </label>
                ) : null}

                {mode.engine === "Research engine" ? (
                  <label>
                    <span>Photo match threshold</span>
                    <select
                      value={realPhotoMinMatch}
                      onChange={(event) =>
                        setRealPhotoMinMatch(Number(event.target.value))
                      }
                    >
                      <option value={60}>Flexible · 60%</option>
                      <option value={70}>Balanced · 70%</option>
                      <option value={80}>Strict · 80%</option>
                    </select>
                  </label>
                ) : null}
              </div>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={skipResearch}
                  onChange={(event) => setSkipResearch(event.target.checked)}
                />
                <span>
                  <strong>Skip web research</strong>
                  <small>Best for fictional stories or offline testing.</small>
                </span>
              </label>
            </div>
          </details>

          {submitError ? (
            <div className="form-error" role="alert">
              {submitError}
            </div>
          ) : null}

          {scheduleOpen ? (
            <div className="schedule-picker">
              <label htmlFor="schedule-time">Start generation at</label>
              <input
                id="schedule-time"
                type="datetime-local"
                value={scheduleAt}
                min={localDateTimeValue(new Date(Date.now() + 60_000))}
                onChange={(event) => setScheduleAt(event.target.value)}
              />
              <small>
                Displayed in {Intl.DateTimeFormat().resolvedOptions().timeZone}
              </small>
            </div>
          ) : null}

          <div className="create-actions">
            <button
              className="generate-button"
              type="button"
              disabled={
                !topic.trim() ||
                isSubmitting ||
                (mode.id === "ai-photos" &&
                  (!selectedAiModel || !selectedProvider?.configured))
              }
              onClick={scheduleOpen ? handleSchedule : handleSubmit}
            >
              {isSubmitting ? (
                <>
                  <LoaderCircle className="spin" size={18} />
                  Saving project…
                </>
              ) : scheduleOpen ? (
                <>
                  Schedule video
                  <CalendarClock size={18} />
                </>
              ) : (
                <>
                  Generate video
                  <ArrowRight size={18} />
                </>
              )}
            </button>
            <button
              className={`schedule-toggle ${scheduleOpen ? "is-active" : ""}`}
              type="button"
              disabled={isSubmitting}
              onClick={() => setScheduleOpen((value) => !value)}
              aria-pressed={scheduleOpen}
            >
              <CalendarClock size={17} />
              {scheduleOpen ? "Generate now" : "Schedule for later"}
            </button>
          </div>
        </div>

        <aside className="creation-summary">
          <span className="summary-eyebrow">Your video recipe</span>
          <h2>From prompt to published-ready short.</h2>
          <ol>
            <li>
              <span>01</span>
              <div>
                <strong>Research & script</strong>
                <small>Grounded story structure and a strong hook</small>
              </div>
              <Check size={16} />
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Visual direction</strong>
                <small>Scene-by-scene media matched to narration</small>
              </div>
              <Check size={16} />
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Voice & captions</strong>
                <small>Natural narration with animated subtitles</small>
              </div>
              <Check size={16} />
            </li>
          </ol>
          <div className="estimate-pill">
            <Clock3 size={16} />
            <span>
              Estimated generation
              <strong>3–6 minutes</strong>
            </span>
          </div>
        </aside>
      </div>
    </section>
  );
}
