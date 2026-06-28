import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8810";

const AUTO_TONE_VALUE = "تلقائي";
const TONES = [AUTO_TONE_VALUE, "عسكري هادئ", "وثائقي مؤثر", "قصصي دافئ", "تشويقي"];

const TONE_DESCRIPTIONS: Record<string, string> = {
  [AUTO_TONE_VALUE]: "يحلّل النظام بداية ونهاية القصة ويقترح الأسلوب الأنسب تلقائياً (يمكنك اختيار نبرة محددة بدلاً منه في أي وقت).",
  "عسكري هادئ": "لغة منضبطة ومباشرة، بإيقاع ثابت ومن دون مبالغة. مناسب للتجارب القيادية والرسمية.",
  "وثائقي مؤثر": "سرد واقعي يشرح الأحداث بعمق ويبرز أثرها الإنساني. مناسب للقصص الحقيقية والمشاريع.",
  "قصصي دافئ": "لغة حميمة وناعمة تركز على المشاعر والذكريات. مناسب للقصص الشخصية والعائلية.",
  "تشويقي": "جمل أسرع وتصاعد تدريجي ونهايات تثير الفضول. مناسب للقصص الدرامية والمغامرات.",
};

const SAMPLE_STORY = `في ليلة هادئة، جلس الراوي أمام نافذة قديمة يتأمل المدينة التي تغيّرت كثيراً. كانت الذكريات تعود إليه مثل موج البحر، تحمل وجوهاً وأصواتاً ومواقف لم تغب عن قلبه. وفي تلك اللحظة، أدرك أن الحكاية لم تكن عن الماضي وحده، بل عن الشجاعة التي يحتاجها الإنسان كي يبدأ من جديد.`;

type ReviewStatus = "pending" | "approved" | "needs_retry" | "rejected";

type Scene = {
  scene_id: string;
  title_ar: string;
  narration_ar: string;
  visual_description_ar: string;
  image_prompt_en: string;
  duration_seconds: number;
  review_status?: ReviewStatus;
  review_notes?: string;
  review_updated_at?: string | null;
};

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: "قيد الانتظار",
  approved: "مقبول",
  needs_retry: "يحتاج إعادة",
  rejected: "مرفوض",
};

type ApiEnvelope<T> = {
  data: T;
  meta: Record<string, unknown>;
  errors: string[];
};

type ConfigData = {
  provider: string;
  model: string;
  ollama_configured: boolean;
  long_story_chunk_chars: number;
  story_job_threshold_chars?: number;
  long_story_max_total_seconds?: number;
  ollama_timeout_seconds?: number;
};

const DEFAULT_LONG_STORY_CHUNK_CHARS = 3000;
const DEFAULT_STORY_JOB_THRESHOLD_CHARS = 1500;
const DEFAULT_OLLAMA_TIMEOUT_SECONDS = 180;

type ToneAnalysisInfo = {
  requestedTone: string;
  resolvedTone: string;
  genre: string | null;
  pacing: string | null;
  reasonAr: string | null;
  analysisFallback: boolean;
};

type SplitData = {
  project_id: string | null;
  story_title: string;
  scenes: Scene[];
};

type VideoMode = "static" | "ken_burns";
type VideoTransition = "none" | "fade";
type SafetySourceType = "own_content" | "licensed" | "generated" | "unknown";
type SafetyConsent = "yes" | "no" | "not_applicable";
type SafetyAppliesTo = "voice" | "image_reference" | "music_sfx" | "person_likeness";

type Project = {
  project_id: string;
  title: string;
  original_story: string;
  improved_story: string;
  scenes: Scene[];
  created_at: string;
  updated_at: string;
  story_style_bible: string;
  character_bible: string;
  location_bible: string;
  object_bible: string;
  negative_prompt: string;
  style_preset: string;
  video_mode: VideoMode;
  video_transition: VideoTransition;
  safety_source_type: SafetySourceType;
  safety_consent_confirmed: SafetyConsent;
  safety_rights_notes: string;
  safety_applies_to: SafetyAppliesTo[];
};

type StylePreset = { key: string; prompt_prefix: string };

type ProjectListItem = {
  project_id: string;
  title: string;
  scene_count: number;
  created_at: string;
  updated_at: string;
};

type ProjectListData = {
  projects: ProjectListItem[];
};

type TtsHealthData = {
  enabled: boolean;
  configured: boolean;
  service_url_configured: boolean;
  remote_ok: boolean | null;
  latency_ms?: number;
};

type TtsVoice = {
  voice_id: string;
  display_name_ar: string;
  gender: "male" | "female" | "unknown";
  language: string;
  engine: string;
  quality_label: string;
  experimental: boolean;
  default: boolean;
  notes_ar: string;
  available: boolean;
};

type TtsLanguage = {
  language: string;
  label: string;
  default: boolean;
};

type TtsVoicesData = {
  voices: TtsVoice[];
  languages: TtsLanguage[];
  default_voice_id: string | null;
  single_voice_available: boolean;
};

type SceneAudioInfo = {
  scene_id: string;
  has_audio: boolean;
  audio_format: string | null;
  audio_bytes: number | null;
  audio_generated_at: string | null;
  audio_voice_id: string | null;
  audio_engine: string | null;
  url: string | null;
};

type ProjectAudioData = {
  project_id: string;
  scenes: SceneAudioInfo[];
  final_story: { has_audio: boolean; url: string | null };
};

const STYLE_PRESET_LABELS: Record<string, string> = {
  cinematic_realistic: "سينمائي واقعي",
  warm_storybook: "كتاب قصص دافئ",
  anime_cartoon: "أنيمي/كارتون",
  military_documentary: "وثائقي عسكري",
  horror_suspense: "رعب وتشويق",
  marketing_poster: "بوستر تسويقي",
};

function presetLabel(key: string): string {
  return STYLE_PRESET_LABELS[key] ?? key;
}

const FALLBACK_TTS_VOICES: TtsVoicesData = {
  voices: [
    {
      voice_id: "ar_JO-kareem-medium",
      display_name_ar: "كريم (عربي - رجل)",
      gender: "male",
      language: "ar",
      engine: "piper",
      quality_label: "medium",
      experimental: false,
      default: true,
      notes_ar: "",
      available: true,
    },
  ],
  languages: [{ language: "ar", label: "العربية", default: true }],
  default_voice_id: "ar_JO-kareem-medium",
  single_voice_available: true,
};

function voiceGenderLabel(gender: TtsVoice["gender"]): string {
  if (gender === "male") return "رجل";
  if (gender === "female") return "امرأة";
  return "غير محدد";
}

type TtsBusyAction = "health" | "scene" | "project" | "refresh" | null;

type ImageHealthData = {
  enabled: boolean;
  configured: boolean;
  service_url_configured: boolean;
  remote_ok: boolean | null;
  latency_ms?: number;
};

type ImageJobFile = { filename: string; subfolder: string; type: string };

type ImageJobData = {
  job_id?: string;
  status?: string;
  error?: string | null;
  files?: ImageJobFile[];
};

type SceneImageInfo = {
  scene_id: string;
  has_image: boolean;
  image_format: string | null;
  image_bytes: number | null;
  image_width: number | null;
  image_height: number | null;
  image_seed: number | null;
  image_engine: string | null;
  image_generated_at: string | null;
  url: string | null;
};

type ProjectImagesData = {
  project_id: string;
  scenes: SceneImageInfo[];
};

type ProjectVideoData = {
  project_id: string;
  has_video: boolean;
  url: string | null;
  duration_seconds: number | null;
  video_bytes: number | null;
  rendered_at: string | null;
  included_scenes: string[];
  skipped_scenes: { scene_id: string; reason: string }[];
};

type ImageBusyAction = "health" | "scene" | "refresh" | "all" | null;

type SystemStatusData = {
  ollama: { ok: boolean; model: string; base_url_configured: boolean; latency_ms: number | null };
  tts: { enabled: boolean; configured: boolean; remote_ok: boolean | null; latency_ms?: number };
  image: { enabled: boolean; configured: boolean; remote_ok: boolean | null; latency_ms?: number };
  ffmpeg: { available: boolean };
  benchmark_notes_doc: string;
};

type LoadingAction =
  | "test"
  | "improve"
  | "split"
  | "new"
  | "save"
  | "load"
  | "delete"
  | "package"
  | null;

type StudioStep =
  | "story"
  | "scenes"
  | "audio"
  | "images"
  | "video"
  | "timeline"
  | "assets"
  | "review"
  | "image_studio"
  | "assistant"
  | "export";

// ── Helpers ───────────────────────────────────────────────────────────────────

function getSceneWarnings(scene: Scene): string[] {
  const w: string[] = [];
  if (!scene.title_ar.trim()) w.push("العنوان فارغ");
  if (!scene.narration_ar.trim()) w.push("نص الراوي فارغ");
  if (!scene.duration_seconds || scene.duration_seconds < 3) w.push("المدة أقل من 3 ثوانٍ (الحد الأدنى المسموح)");
  return w;
}

function BusyNotice({ busy, message }: { busy: boolean; message: string }) {
  if (!message) return null;
  return (
    <div className={busy ? "notice-banner notice-banner--busy" : "notice-banner"}>
      {busy && <span className="inline-spinner" aria-hidden="true" />}
      {message}
    </div>
  );
}

function ProjectHeader({
  title,
  projectId,
  isDirty,
  sceneCount,
  audioCount,
  imageCount,
  hasVideo,
  loading,
  onNewProject,
  onSaveProject,
  onDownloadZip,
}: {
  title: string;
  projectId: string | null;
  isDirty: boolean;
  sceneCount: number;
  audioCount: number;
  imageCount: number;
  hasVideo: boolean;
  loading: LoadingAction;
  onNewProject: () => void;
  onSaveProject: () => void;
  onDownloadZip: () => void;
}) {
  return (
    <section className="studio-sticky-header glass-panel">
      <div className="studio-project-summary">
        <span className="eyebrow">Studio Workflow</span>
        <strong>{title || "مشروع بدون عنوان"}</strong>
        <small>
          {projectId ? `ID: ${projectId.slice(0, 8)}` : "غير محفوظ بعد"}
          {projectId && (
            <span className={isDirty ? "save-state save-state--dirty" : "save-state save-state--saved"}>
              {isDirty ? " · تغييرات غير محفوظة" : " · محفوظ"}
            </span>
          )}
        </small>
      </div>
      <div className="studio-status-strip" aria-label="حالة المشروع">
        <span>{sceneCount} مشاهد</span>
        <span>{audioCount}/{sceneCount || 0} صوت</span>
        <span>{imageCount}/{sceneCount || 0} صور</span>
        <span>{hasVideo ? "فيديو جاهز" : "لا يوجد فيديو"}</span>
      </div>
      <div className="project-actions compact-actions">
        <button onClick={onNewProject} disabled={loading !== null}>
          مشروع جديد
        </button>
        <button onClick={onSaveProject} disabled={loading !== null}>
          {loading === "save" ? "جاري الحفظ..." : "حفظ"}
        </button>
        <button
          className="download-button"
          onClick={onDownloadZip}
          disabled={!projectId || loading !== null}
          title={!projectId ? "احفظ المشروع أولاً قبل تحميل ZIP" : undefined}
        >
          ZIP
        </button>
      </div>
    </section>
  );
}

type StudioStepInfo = { key: StudioStep; label: string; hint: string; done: boolean };

function StudioStepper({
  steps,
  activeStep,
  onSelect,
}: {
  steps: StudioStepInfo[];
  activeStep: StudioStep;
  onSelect: (step: StudioStep) => void;
}) {
  return (
    <nav className="studio-stepper glass-panel" aria-label="خطوات الاستوديو">
      {steps.map((step, index) => (
        <button
          key={step.key}
          type="button"
          className={activeStep === step.key ? "studio-step active" : "studio-step"}
          onClick={() => onSelect(step.key)}
        >
          <span className={step.done ? "step-index step-index--done" : "step-index"}>
            {step.done ? "✓" : index + 1}
          </span>
          <strong>{step.label}</strong>
          <small>{step.hint}</small>
        </button>
      ))}
    </nav>
  );
}

function renumberScenes(list: Scene[]): Scene[] {
  return list.map((s, i) => ({ ...s, scene_id: String(i + 1).padStart(2, "0") }));
}

function swapExpanded(prev: Set<number>, a: number, b: number): Set<number> {
  const next = new Set(prev);
  const hadA = prev.has(a);
  const hadB = prev.has(b);
  if (hadA) next.add(b);
  else next.delete(b);
  if (hadB) next.add(a);
  else next.delete(a);
  return next;
}

// ── HTTP ──────────────────────────────────────────────────────────────────────

async function requestJson<T>(path: string, options?: RequestInit): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload?.detail || payload?.errors?.join?.(" ") || "Request failed.";
    throw new Error(detail);
  }
  return payload;
}

const getJson = <T,>(path: string) => requestJson<T>(path);

const postJson = <T,>(path: string, payload?: unknown) =>
  requestJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : "{}",
  });

const putJson = <T,>(path: string, payload: unknown) =>
  requestJson<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

const deleteJson = <T,>(path: string) => requestJson<T>(path, { method: "DELETE" });

// ── Jobs (Milestone A lightweight progress polling) ────────────────────────────

type JobPhase =
  | "analyzing"
  | "preparing_chunks"
  | "generating"
  | "retrying"
  | "assembling"
  | "done"
  | "failed"
  | "cancelled";

type JobRecord = {
  job_id: string;
  project_id: string;
  job_type: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  current_step: number;
  total_steps: number;
  completed_steps: number;
  message_ar: string;
  safe_error_ar: string | null;
  result_summary: Record<string, unknown> | null;
  affected_scene_ids: string[];
  phase?: JobPhase | null;
  progress_percent?: number | null;
  elapsed_seconds?: number | null;
  estimated_remaining_seconds?: number | null;
  last_activity_at?: string | null;
  generated_units?: number;
  retry_count?: number;
  cancel_requested?: boolean;
};

const JOB_PHASE_LABELS: Record<string, string> = {
  analyzing: "تحليل القصة",
  preparing_chunks: "تجهيز الأجزاء",
  generating: "توليد النص",
  retrying: "إعادة محاولة",
  assembling: "تجميع النتيجة",
  done: "تم",
  failed: "فشل",
  cancelled: "ملغى",
};

function formatElapsed(totalSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

const JOB_TYPE_LABELS: Record<string, string> = {
  story_improve: "تحسين القصة",
  images_generate_all: "توليد كل الصور",
  video_render: "تجميع الفيديو",
  audio_generate_all: "توليد كل الصوت",
};

const JOB_STATUS_LABELS: Record<string, string> = {
  queued: "في الانتظار",
  running: "قيد التنفيذ",
  done: "تم",
  failed: "فشل",
  cancelled: "ملغى",
};

const JOB_POLL_INTERVAL_MS = 1200;
const TERMINAL_JOB_STATUSES = new Set(["done", "failed", "cancelled"]);

async function pollJob(jobId: string, onUpdate: (job: JobRecord) => void): Promise<JobRecord> {
  for (;;) {
    const r = await getJson<JobRecord>(`/api/jobs/${jobId}`);
    onUpdate(r.data);
    if (TERMINAL_JOB_STATUSES.has(r.data.status)) {
      return r.data;
    }
    await new Promise((resolve) => setTimeout(resolve, JOB_POLL_INTERVAL_MS));
  }
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [title, setTitle] = useState("المسرح لي");
  const [storyText, setStoryText] = useState("");
  // TONES[0] is AUTO_TONE_VALUE ("تلقائي") -- the default for a fresh app
  // session/new project. There is no per-project persisted tone field, so
  // loading an existing project (applyProject/handleLoadProject) never
  // touches this state -- whatever the user currently has selected stays
  // selected, satisfying "don't change an existing project's tone."
  const [tone, setTone] = useState(TONES[0]);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [providerMessage, setProviderMessage] = useState("لم يتم الاختبار بعد");
  const [improveProgress, setImproveProgress] = useState("");
  const [improvedText, setImprovedText] = useState("");
  const [improveJob, setImproveJob] = useState<JobRecord | null>(null);
  const [improveJobId, setImproveJobId] = useState<string | null>(null);
  const [improveCancelBusy, setImproveCancelBusy] = useState(false);
  const [toneAnalysisInfo, setToneAnalysisInfo] = useState<ToneAnalysisInfo | null>(null);
  const [tickingElapsedSeconds, setTickingElapsedSeconds] = useState(0);
  const improveJobStartedAtRef = useRef<number | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(new Set([0]));
  const [rawJsonOpen, setRawJsonOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<LoadingAction>(null);
  const [activeStep, setActiveStep] = useState<StudioStep>("story");
  const [isDirty, setIsDirty] = useState(false);
  const skipDirtyEffect = useRef(true);

  const [storyStyleBible, setStoryStyleBible] = useState("");
  const [characterBible, setCharacterBible] = useState("");
  const [locationBible, setLocationBible] = useState("");
  const [objectBible, setObjectBible] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [stylePreset, setStylePreset] = useState("cinematic_realistic");
  const [stylePresets, setStylePresets] = useState<StylePreset[]>([]);

  const [videoMode, setVideoMode] = useState<VideoMode>("static");
  const [videoTransition, setVideoTransition] = useState<VideoTransition>("none");
  const [safetySourceType, setSafetySourceType] = useState<SafetySourceType>("unknown");
  const [safetyConsentConfirmed, setSafetyConsentConfirmed] = useState<SafetyConsent>("not_applicable");
  const [safetyRightsNotes, setSafetyRightsNotes] = useState("");
  const [safetyAppliesTo, setSafetyAppliesTo] = useState<SafetyAppliesTo[]>([]);

  const [promptPreview, setPromptPreview] = useState<{ sceneId: string; prompt: string; negativePrompt: string } | null>(null);
  const [promptPreviewBusy, setPromptPreviewBusy] = useState(false);

  const [systemStatus, setSystemStatus] = useState<SystemStatusData | null>(null);
  const [systemStatusBusy, setSystemStatusBusy] = useState(false);

  const [projectJobs, setProjectJobs] = useState<JobRecord[]>([]);
  const [projectJobsBusy, setProjectJobsBusy] = useState(false);

  const [reviewFilter, setReviewFilter] = useState<"all" | ReviewStatus>("all");

  const [standaloneImage, setStandaloneImage] = useState({
    prompt: "",
    stylePreset: "cinematic_realistic",
    negativePrompt: "",
    seed: "",
    width: 768,
    height: 768,
  });
  const [standaloneImageJob, setStandaloneImageJob] = useState<ImageJobData | null>(null);
  const [standaloneImageBusy, setStandaloneImageBusy] = useState(false);
  const [standaloneImageMessage, setStandaloneImageMessage] = useState("");

  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState("");
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assistantMessage, setAssistantMessage] = useState("");

  useEffect(() => {
    if (skipDirtyEffect.current) {
      skipDirtyEffect.current = false;
      return;
    }
    setIsDirty(true);
  }, [title, storyText, improvedText, scenes, storyStyleBible, characterBible, locationBible, objectBible, negativePrompt, stylePreset]);

  // Milestone 5 -- elapsed time must keep moving every second from
  // started_at even if no new job update has arrived yet (the backend only
  // writes generated_units/last_activity_at at most once per second).
  useEffect(() => {
    if (loading !== "improve" || improveJobStartedAtRef.current === null) {
      return;
    }
    const interval = setInterval(() => {
      if (improveJobStartedAtRef.current !== null) {
        setTickingElapsedSeconds((Date.now() - improveJobStartedAtRef.current) / 1000);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [loading, improveJob?.job_id]);

  const [ttsHealth, setTtsHealth] = useState<TtsHealthData | null>(null);
  const [ttsMessage, setTtsMessage] = useState("");
  const [ttsBusy, setTtsBusy] = useState<TtsBusyAction>(null);
  const [ttsVoices, setTtsVoices] = useState<TtsVoicesData>(FALLBACK_TTS_VOICES);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(
    FALLBACK_TTS_VOICES.voices[0].voice_id,
  );
  const [projectAudio, setProjectAudio] = useState<ProjectAudioData | null>(null);

  const [imageHealth, setImageHealth] = useState<ImageHealthData | null>(null);
  const [imageMessage, setImageMessage] = useState("");
  const [imageJob, setImageJob] = useState<ImageJobData | null>(null);
  const [imageBusy, setImageBusy] = useState<ImageBusyAction>(null);
  const [projectImages, setProjectImages] = useState<ProjectImagesData | null>(null);
  const [generatingSceneId, setGeneratingSceneId] = useState<string | null>(null);

  const [projectVideo, setProjectVideo] = useState<ProjectVideoData | null>(null);
  const [videoMessage, setVideoMessage] = useState("");
  const [videoBusy, setVideoBusy] = useState(false);

  const canRun = storyText.trim().length > 0 && loading === null;
  const longStoryChunkChars = config?.long_story_chunk_chars || DEFAULT_LONG_STORY_CHUNK_CHARS;
  const isLongStory = storyText.trim().length > longStoryChunkChars;
  // Milestone 8 -- routing decision, independent of chunking: any story over
  // this length uses the job endpoint (real progress/cancel/recovery) even
  // if it still fits in a single chunk and would otherwise hit the old
  // fragile blocking synchronous path.
  const storyJobThresholdChars = config?.story_job_threshold_chars || DEFAULT_STORY_JOB_THRESHOLD_CHARS;
  const usesJobEndpoint = storyText.trim().length > storyJobThresholdChars;
  const ollamaTimeoutSeconds = config?.ollama_timeout_seconds || DEFAULT_OLLAMA_TIMEOUT_SECONDS;

  const sceneStats = useMemo(() => {
    const totalDuration = scenes.reduce((sum, s) => sum + (s.duration_seconds || 0), 0);
    const invalidCount = scenes.filter((s) => getSceneWarnings(s).length > 0).length;
    return { totalDuration, invalidCount };
  }, [scenes]);

  const splitData = useMemo<SplitData | null>(
    () => (scenes.length ? { project_id: projectId, story_title: title, scenes } : null),
    [projectId, scenes, title],
  );

  const rawJson = useMemo(
    () => (splitData ? JSON.stringify(splitData, null, 2) : ""),
    [splitData],
  );

  const audioCount = projectAudio?.scenes.filter((scene) => scene.has_audio).length ?? 0;
  const imageCount = projectImages?.scenes.filter((scene) => scene.has_image).length ?? 0;
  const hasVideo = Boolean(projectVideo?.has_video);
  const hasStoryText = Boolean(storyText.trim() || improvedText.trim());

  const approvedCount = scenes.filter((s) => s.review_status === "approved").length;
  const reviewedCount = scenes.filter((s) => (s.review_status || "pending") !== "pending").length;
  const rejectedOrRetryCount = scenes.filter((s) => s.review_status === "rejected" || s.review_status === "needs_retry").length;

  const studioSteps: StudioStepInfo[] = [
    { key: "story", label: "القصة", hint: "ابدأ بكتابة القصة", done: hasStoryText },
    { key: "scenes", label: "المشاهد", hint: "حوّل القصة إلى مشاهد", done: scenes.length > 0 },
    { key: "audio", label: "الصوت", hint: "استمع إلى الصوت", done: audioCount > 0 },
    { key: "images", label: "الصور", hint: "ولّد صور المشاهد", done: imageCount > 0 },
    { key: "video", label: "الفيديو والترجمة", hint: "اصنع فيديو من الصور والصوت", done: hasVideo },
    { key: "timeline", label: "الخط الزمني", hint: "حالة كل مشهد في مكان واحد", done: scenes.length > 0 },
    { key: "assets", label: "مكتبة الأصول", hint: "كل ملفات المشروع", done: scenes.length > 0 },
    { key: "review", label: "مراجعة الجودة", hint: "اعتماد أو إعادة كل مشهد", done: reviewedCount > 0 },
    { key: "image_studio", label: "استوديو الصور المستقل", hint: "صورة واحدة من وصف واحد", done: false },
    { key: "assistant", label: "المساعد المحلي", hint: "اسأل عن مشروعك الحالي", done: false },
    { key: "export", label: "التصدير", hint: "حمّل المشروع كاملاً", done: false },
  ];

  useEffect(() => {
    getJson<ConfigData>("/api/config")
      .then((r) => {
        setConfig(r.data);
        if (r.errors.length) setError(r.errors.join(" "));
      })
      .catch(() => setError("تعذر تحميل إعدادات المزود من backend."));
    refreshProjects();
    checkTtsHealth();
    fetchTtsVoices();
    checkImageHealth();
    getJson<{ presets: StylePreset[] }>("/api/images/style-presets")
      .then((r) => setStylePresets(r.data.presets || []))
      .catch(() => setStylePresets([]));
  }, []);

  async function fetchTtsVoices() {
    try {
      const r = await getJson<TtsVoicesData>("/api/tts/voices");
      const available = r.data.voices.filter((v) => v.available);
      if (available.length) {
        setTtsVoices(r.data);
        const preferred =
          available.find((v) => v.voice_id === r.data.default_voice_id) ??
          available.find((v) => v.default) ??
          available[0];
        setSelectedVoiceId(preferred.voice_id);
      }
      // If nothing came back available, keep FALLBACK_TTS_VOICES rather than
      // showing an empty/broken selector -- Voice Expansion Lab rule (D):
      // never display a voice that doesn't actually work.
    } catch {
      /* keep FALLBACK_TTS_VOICES — never break the selector */
    }
  }

  async function refreshProjectAudio(id: string) {
    try {
      const r = await getJson<ProjectAudioData>(`/api/projects/${id}/audio`);
      setProjectAudio(r.data);
    } catch {
      setProjectAudio(null);
    }
  }

  async function refreshProjectImages(id: string) {
    try {
      const r = await getJson<ProjectImagesData>(`/api/projects/${id}/images`);
      setProjectImages(r.data);
    } catch {
      setProjectImages(null);
    }
  }

  async function refreshProjectVideo(id: string) {
    try {
      const r = await getJson<ProjectVideoData>(`/api/projects/${id}/video`);
      setProjectVideo(r.data);
    } catch {
      setProjectVideo(null);
    }
  }

  async function handleRenderVideo() {
    if (!projectId) {
      setVideoMessage("احفظ المشروع أولاً قبل تجميع الفيديو.");
      return;
    }
    setVideoBusy(true);
    setVideoMessage(
      "جاري تجميع الفيديو من الصور والصوت المحفوظ... يتم استخدام مدة الصوت الفعلية لكل مشهد إن وُجدت، وإلا فمدة المشهد الافتراضية.",
    );
    try {
      const r = await postJson<JobRecord>(`/api/projects/${projectId}/video/render/jobs`);
      if (r.errors.length) {
        setVideoMessage(r.errors.join(" "));
        return;
      }
      const finalJob = await pollJob(r.data.job_id, (job) => {
        setVideoMessage(job.message_ar || `جاري تجميع مشهد ${job.current_step} من ${job.total_steps}...`);
      });
      if (finalJob.status === "done" && finalJob.result_summary) {
        const summary = finalJob.result_summary as {
          included_scenes: string[];
          skipped_scenes: { scene_id: string; reason: string }[];
          duration_seconds: number;
        };
        let msg = `تم تجميع الفيديو من ${summary.included_scenes.length} مشهد، بمدة ${summary.duration_seconds} ثانية تقريباً.`;
        if (summary.skipped_scenes.length) {
          msg += ` تم تجاوز: ${summary.skipped_scenes.map((s) => `${s.scene_id} (${s.reason})`).join(", ")}.`;
        }
        setVideoMessage(msg);
        await refreshProjectVideo(projectId);
      } else {
        setVideoMessage(finalJob.safe_error_ar || "تعذر تجميع الفيديو.");
      }
    } catch (exc) {
      setVideoMessage(exc instanceof Error ? exc.message : "تعذر تجميع الفيديو.");
    } finally {
      setVideoBusy(false);
    }
  }

  async function refreshProjects() {
    try {
      const r = await getJson<ProjectListData>("/api/projects");
      setProjects(r.data.projects || []);
    } catch {
      /* silent — sidebar not critical */
    }
  }

  function showNotice(msg: string) {
    setNotice(msg);
    window.setTimeout(() => setNotice(""), 3500);
  }

  function applyProject(project: Project) {
    skipDirtyEffect.current = true;
    setIsDirty(false);
    setProjectId(project.project_id);
    setTitle(project.title);
    setStoryText(project.original_story || "");
    setImprovedText(project.improved_story || "");
    setScenes(project.scenes || []);
    setExpandedIndices(new Set([0]));
    setRawJsonOpen(Boolean(project.scenes?.length));
    setProjectAudio(null);
    setImageJob(null);
    setImageMessage("");
    setProjectImages(null);
    setProjectVideo(null);
    setVideoMessage("");
    setStoryStyleBible(project.story_style_bible || "");
    setCharacterBible(project.character_bible || "");
    setLocationBible(project.location_bible || "");
    setObjectBible(project.object_bible || "");
    setVideoMode(project.video_mode || "static");
    setVideoTransition(project.video_transition || "none");
    setSafetySourceType(project.safety_source_type || "unknown");
    setSafetyConsentConfirmed(project.safety_consent_confirmed || "not_applicable");
    setSafetyRightsNotes(project.safety_rights_notes || "");
    setSafetyAppliesTo(project.safety_applies_to || []);
    setNegativePrompt(project.negative_prompt || "");
    setStylePreset(project.style_preset || "cinematic_realistic");
    void refreshProjectAudio(project.project_id);
    void refreshProjectImages(project.project_id);
    void refreshProjectVideo(project.project_id);
  }

  // ── Project CRUD ─────────────────────────────────────────────────────────────

  async function handleNewProject() {
    setLoading("new");
    setError("");
    try {
      const r = await postJson<Project>("/api/projects", {
        title: "قصة جديدة",
        original_story: "",
        improved_story: "",
        scenes: [],
      });
      applyProject(r.data);
      setTone(AUTO_TONE_VALUE);
      await refreshProjects();
      showNotice("تم إنشاء مشروع جديد.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر إنشاء مشروع جديد.");
    } finally {
      setLoading(null);
    }
  }

  async function handleLoadProject(id: string) {
    setLoading("load");
    setError("");
    try {
      const r = await getJson<Project>(`/api/projects/${id}`);
      applyProject(r.data);
      showNotice("تم تحميل المشروع.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر تحميل المشروع.");
    } finally {
      setLoading(null);
    }
  }

  async function handleSaveProject() {
    setLoading("save");
    setError("");
    const safeTitle = title.trim() || "مشروع بدون عنوان";
    if (safeTitle !== title) setTitle(safeTitle);
    const payload = {
      title: safeTitle,
      original_story: storyText,
      improved_story: improvedText,
      scenes,
      story_style_bible: storyStyleBible,
      character_bible: characterBible,
      location_bible: locationBible,
      object_bible: objectBible,
      negative_prompt: negativePrompt,
      style_preset: stylePreset,
      video_mode: videoMode,
      video_transition: videoTransition,
      safety_source_type: safetySourceType,
      safety_consent_confirmed: safetyConsentConfirmed,
      safety_rights_notes: safetyRightsNotes,
      safety_applies_to: safetyAppliesTo,
    };
    try {
      const r = projectId
        ? await putJson<Project>(`/api/projects/${projectId}`, payload)
        : await postJson<Project>("/api/projects", payload);
      applyProject(r.data);
      await refreshProjects();
      showNotice("تم حفظ المشروع.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر حفظ المشروع.");
    } finally {
      setLoading(null);
    }
  }

  async function handleDeleteProject() {
    if (!projectId) return;
    if (!window.confirm("هل تريد حذف هذا المشروع؟ لا يمكن التراجع عن الحذف.")) return;
    setLoading("delete");
    setError("");
    try {
      await deleteJson(`/api/projects/${projectId}`);
      skipDirtyEffect.current = true;
      setIsDirty(false);
      setProjectId(null);
      setTitle("قصة جديدة");
      setStoryText("");
      setImprovedText("");
      setScenes([]);
      setExpandedIndices(new Set());
      setRawJsonOpen(false);
      setProjectAudio(null);
      setImageJob(null);
      setImageMessage("");
      setProjectImages(null);
      setProjectVideo(null);
      setVideoMessage("");
      await refreshProjects();
      showNotice("تم حذف المشروع.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر حذف المشروع.");
    } finally {
      setLoading(null);
    }
  }

  // ── AI ────────────────────────────────────────────────────────────────────────

  async function handleTestOllama() {
    setLoading("test");
    setError("");
    try {
      const r = await postJson<{ connected: boolean; latency_ms: number | null; model: string }>(
        "/api/ollama/test",
      );
      if (r.errors.length) {
        setProviderMessage("الاتصال غير جاهز");
        setError(r.errors.join(" "));
      } else {
        setProviderMessage(`متصل عبر ${r.data.model} خلال ${r.data.latency_ms}ms`);
      }
    } catch {
      setProviderMessage("الاتصال غير جاهز");
      setError("تعذر الوصول إلى backend أو Ollama.");
    } finally {
      setLoading(null);
    }
  }

  async function refreshProjectJobs() {
    if (!projectId) return;
    setProjectJobsBusy(true);
    try {
      const r = await getJson<{ project_id: string; jobs: JobRecord[] }>(`/api/projects/${projectId}/jobs`);
      setProjectJobs(r.data.jobs || []);
    } catch {
      /* silent -- job history is a convenience view, not critical */
    } finally {
      setProjectJobsBusy(false);
    }
  }

  async function handleCheckSystemStatus() {
    setSystemStatusBusy(true);
    try {
      const r = await getJson<SystemStatusData>("/api/system/status");
      setSystemStatus(r.data);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر تحميل حالة الخدمات.");
    } finally {
      setSystemStatusBusy(false);
    }
  }

  async function handleImproveStory() {
    setLoading("improve");
    setError("");
    setToneAnalysisInfo(null);
    setImproveJob(null);
    setImproveJobId(null);
    setTickingElapsedSeconds(0);
    improveJobStartedAtRef.current = null;
    setImproveProgress(
      tone === AUTO_TONE_VALUE
        ? "جاري تحليل القصة لاختيار النبرة المناسبة..."
        : isLongStory
        ? "النص طويل، سيتم تحسينه على أجزاء. قد يستغرق ذلك دقيقة أو أكثر..."
        : ""
    );
    try {
      if (usesJobEndpoint) {
        // Stories over storyJobThresholdChars use the job-based endpoint so
        // the UI can show real progress/timing/cancel instead of a single
        // blocking request with no feedback -- this applies even to a story
        // that still fits in one chunk, not just genuinely "long" ones.
        improveJobStartedAtRef.current = Date.now();
        const r = await postJson<JobRecord>(`/api/projects/${projectId ?? "draft"}/story/improve/jobs`, {
          story_text: storyText,
          tone,
          title,
          language: "ar",
        });
        if (r.errors.length) {
          setError(r.errors.join(" "));
          return;
        }
        setImproveJobId(r.data.job_id);
        const finalJob = await pollJob(r.data.job_id, (job) => {
          setImproveJob(job);
          setImproveProgress(job.message_ar || `جاري تحسين الجزء ${job.current_step} من ${job.total_steps}...`);
          const summary = job.result_summary as Record<string, unknown> | null;
          if (summary && typeof summary.resolved_tone === "string") {
            setToneAnalysisInfo({
              requestedTone: String(summary.requested_tone ?? tone),
              resolvedTone: String(summary.resolved_tone),
              genre: (summary.genre as string | null) ?? null,
              pacing: (summary.pacing as string | null) ?? null,
              reasonAr: (summary.reason_ar as string | null) ?? null,
              analysisFallback: Boolean(summary.analysis_fallback),
            });
          }
        });
        setImproveJob(finalJob);
        if (finalJob.status === "done" && finalJob.result_summary) {
          const summary = finalJob.result_summary as { improved_text: string; chunk_count: number };
          setImprovedText(summary.improved_text);
          showNotice(
            summary.chunk_count > 1
              ? `تم تحسين القصة على ${summary.chunk_count} أجزاء. لا تنس حفظ المشروع.`
              : "تم تحسين القصة. لا تنس حفظ المشروع."
          );
        } else if (finalJob.status === "cancelled") {
          showNotice("تم إلغاء تحسين القصة.");
        } else {
          setError(finalJob.safe_error_ar || "تعذر تحسين القصة.");
        }
        return;
      }

      const r = await postJson<{ improved_text: string }>("/api/story/improve", {
        story_text: storyText,
        tone,
        title,
        language: "ar",
      });
      if (r.errors.length) {
        setError(r.errors.join(" "));
      } else {
        setImprovedText(r.data.improved_text);
        if (r.meta && typeof r.meta.resolved_tone === "string") {
          setToneAnalysisInfo({
            requestedTone: String(r.meta.requested_tone ?? tone),
            resolvedTone: String(r.meta.resolved_tone),
            genre: (r.meta.genre as string | null) ?? null,
            pacing: (r.meta.pacing as string | null) ?? null,
            reasonAr: (r.meta.reason_ar as string | null) ?? null,
            analysisFallback: Boolean(r.meta.analysis_fallback),
          });
        }
        showNotice("تم تحسين القصة. لا تنس حفظ المشروع.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تحسين القصة. تحقق من backend وOllama.");
    } finally {
      setLoading(null);
      setImproveProgress("");
      improveJobStartedAtRef.current = null;
    }
  }

  async function handleCancelImprove() {
    if (!improveJobId) return;
    setImproveCancelBusy(true);
    try {
      await postJson<JobRecord>(`/api/jobs/${improveJobId}/cancel`, {});
      showNotice("تم طلب الإلغاء، سيتم الإيقاف عند أول نقطة آمنة.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر إرسال طلب الإلغاء.");
    } finally {
      setImproveCancelBusy(false);
    }
  }

  async function handleSplitScenes() {
    setLoading("split");
    setError("");
    try {
      const r = await postJson<SplitData>("/api/story/split-scenes", {
        title,
        story_text: improvedText || storyText,
        target_scenes: 6,
        tone,
      });
      if (r.errors.length) {
        setError(r.errors.join(" "));
        setScenes([]);
      } else {
        setScenes(r.data.scenes);
        setExpandedIndices(new Set([0]));
        setRawJsonOpen(false);
        setActiveStep("scenes");
        if (r.data.project_id) await saveGeneratedProject(r.data.project_id, r.data.scenes);
        showNotice("تم تقسيم القصة إلى مشاهد وحفظ المشروع.");
      }
    } catch {
      setError("تعذر تقسيم القصة إلى مشاهد. تحقق من استجابة Ollama.");
    } finally {
      setLoading(null);
    }
  }

  async function saveGeneratedProject(genId: string, genScenes: Scene[]) {
    const r = await putJson<Project>(`/api/projects/${genId}`, {
      title,
      original_story: storyText,
      improved_story: improvedText,
      scenes: genScenes,
    });
    applyProject(r.data);
    await refreshProjects();
  }

  // ── Scene Editing ─────────────────────────────────────────────────────────────

  function updateScene(index: number, field: keyof Scene, value: string | number) {
    setScenes((prev) => prev.map((s, i) => (i === index ? { ...s, [field]: value } : s)));
  }

  async function handleSetSceneReview(sceneId: string, status: ReviewStatus) {
    if (!projectId) return;
    const updatedScenes = scenes.map((s) =>
      s.scene_id === sceneId ? { ...s, review_status: status, review_updated_at: new Date().toISOString() } : s,
    );
    setScenes(updatedScenes);
    try {
      await putJson<Project>(`/api/projects/${projectId}`, { scenes: updatedScenes });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر حفظ حالة المراجعة.");
    }
  }

  function updateSceneReviewNotes(sceneId: string, notes: string) {
    setScenes((prev) => prev.map((s) => (s.scene_id === sceneId ? { ...s, review_notes: notes } : s)));
  }

  async function handleSaveSceneReviewNotes(sceneId: string) {
    if (!projectId) return;
    try {
      await putJson<Project>(`/api/projects/${projectId}`, { scenes });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر حفظ ملاحظة المراجعة.");
    }
  }

  function toggleScene(index: number) {
    setExpandedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function moveSceneUp(index: number) {
    if (index === 0) return;
    setScenes((prev) => {
      const next = [...prev];
      [next[index - 1], next[index]] = [next[index], next[index - 1]];
      return next;
    });
    setExpandedIndices((prev) => swapExpanded(prev, index - 1, index));
  }

  function moveSceneDown(index: number) {
    setScenes((prev) => {
      if (index >= prev.length - 1) return prev;
      const next = [...prev];
      [next[index], next[index + 1]] = [next[index + 1], next[index]];
      return next;
    });
    setExpandedIndices((prev) => swapExpanded(prev, index, index + 1));
  }

  function duplicateScene(index: number) {
    setScenes((prev) => {
      const copy: Scene = { ...prev[index] };
      const next = [...prev];
      next.splice(index + 1, 0, copy);
      return renumberScenes(next);
    });
  }

  function deleteSceneAt(index: number) {
    setScenes((prev) => renumberScenes(prev.filter((_, i) => i !== index)));
    setExpandedIndices((prev) => {
      const next = new Set<number>();
      for (const idx of prev) {
        if (idx < index) next.add(idx);
        else if (idx > index) next.add(idx - 1);
      }
      return next;
    });
  }

  function addSceneAfter(index: number) {
    const blank: Scene = {
      scene_id: "00",
      title_ar: "مشهد جديد",
      narration_ar: "",
      visual_description_ar: "",
      image_prompt_en: "",
      duration_seconds: 8,
    };
    setScenes((prev) => {
      const next = [...prev];
      next.splice(index + 1, 0, blank);
      return renumberScenes(next);
    });
    setExpandedIndices((prev) => {
      const next = new Set<number>();
      for (const idx of prev) next.add(idx <= index ? idx : idx + 1);
      next.add(index + 1);
      return next;
    });
  }

  // ── Download ──────────────────────────────────────────────────────────────────

  async function handleDownloadJson() {
    if (!scenes.length) return;
    if (sceneStats.invalidCount > 0) {
      const ok = window.confirm(
        `يوجد ${sceneStats.invalidCount} مشهد فيه تحذيرات (حقول فارغة أو مدة غير صالحة). هل تريد التحميل رغم ذلك؟`,
      );
      if (!ok) return;
    }
    const payload = { project_id: projectId, story_title: title, scenes };
    downloadBlob(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }),
      "scenes.json",
    );
  }

  async function handleDownloadPackage() {
    if (!projectId) {
      setError("احفظ المشروع أولاً قبل تحميل حزمة ZIP.");
      return;
    }
    setLoading("package");
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/export.zip`);
      if (!response.ok) {
        throw new Error("تعذر تجهيز حزمة المشروع.");
      }
      const blob = await response.blob();
      downloadBlob(blob, `project-${projectId.slice(0, 8)}.zip`);
      showNotice("تم تحميل حزمة المشروع.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر تحميل حزمة المشروع.");
    } finally {
      setLoading(null);
    }
  }

  function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  // ── TTS Bridge (Phase 1.5 — Audio Studio UX) ────────────────────────────────────

  async function checkTtsHealth() {
    setTtsBusy("health");
    setTtsMessage("");
    try {
      const r = await getJson<TtsHealthData>("/api/tts/health");
      setTtsHealth(r.data);
      if (r.errors.length) setTtsMessage(r.errors.join(" "));
    } catch {
      setTtsHealth(null);
      setTtsMessage("تعذر فحص خدمة الصوت.");
    } finally {
      setTtsBusy(null);
    }
  }

  async function handleGenerateAudio(mode: "scene") {
    if (!projectId) {
      setTtsMessage("احفظ المشروع أولاً قبل توليد الصوت.");
      return;
    }
    if (!scenes.length) {
      setTtsMessage("لا توجد مشاهد لتوليد صوت لها.");
      return;
    }
    if (isDirty) {
      // Generation reads narration_ar from the SAVED project on disk, not
      // from unsaved in-memory edits -- generating now would narrate stale
      // text without the user realizing it (manual-QA fix pack, 2026-06-28).
      setTtsMessage("لديك تغييرات غير محفوظة. احفظ المشروع أولاً ليتطابق الصوت مع آخر نص.");
      return;
    }
    setTtsBusy(mode);
    setTtsMessage(`جاري توليد صوت المشهد 1 من ${scenes.length}...`);
    try {
      // Persisted, saved generation (fix pack 2026-06-27) -- this used to call
      // the ephemeral /tts/jobs proxy, which never wrote the audio into the
      // project, so it looked like it worked but vanished after a reload.
      const voiceQuery = selectedVoiceId ? `?voice_id=${encodeURIComponent(selectedVoiceId)}` : "";
      const r = await postJson<{ scene_id: string; status: string }>(
        `/api/projects/${projectId}/tts/scenes/${scenes[0].scene_id}/generate${voiceQuery}`,
      );
      if (r.errors.length) {
        setTtsMessage(r.errors.join(" "));
      } else {
        setTtsMessage("تم توليد صوت المشهد الأول وحفظه في المشروع.");
        await refreshProjectAudio(projectId);
      }
    } catch (exc) {
      setTtsMessage(
        exc instanceof Error
          ? exc.message
          : "تعذر توليد صوت المشهد الأول. تحقّق من حالة خدمة الصوت أعلاه.",
      );
    } finally {
      setTtsBusy(null);
    }
  }

  async function handleGenerateAllAudio() {
    if (!projectId) {
      setTtsMessage("احفظ المشروع أولاً قبل توليد الصوت.");
      return;
    }
    if (!scenes.length) {
      setTtsMessage("لا توجد مشاهد لتوليد صوت لها.");
      return;
    }
    if (isDirty) {
      setTtsMessage("لديك تغييرات غير محفوظة. احفظ المشروع أولاً ليتطابق الصوت مع آخر نص لكل مشهد.");
      return;
    }
    setTtsBusy("project");
    setTtsMessage(
      `جاري توليد صوت ${scenes.length} مشهد بالترتيب، مشهداً تلو الآخر — قد يستغرق دقائق حسب عدد المشاهد...`,
    );
    try {
      const voiceQuery = selectedVoiceId ? `?voice_id=${encodeURIComponent(selectedVoiceId)}` : "";
      const r = await postJson<JobRecord>(`/api/projects/${projectId}/tts/generate-all/jobs${voiceQuery}`);
      if (r.errors.length) {
        setTtsMessage(r.errors.join(" "));
        return;
      }
      const finalJob = await pollJob(r.data.job_id, (job) => {
        setTtsMessage(job.message_ar || `جاري توليد صوت المشهد ${job.current_step} من ${job.total_steps}...`);
      });
      if (finalJob.status === "done" && finalJob.result_summary) {
        const summary = finalJob.result_summary as {
          generated: string[];
          failed: { scene_id: string; error: string }[];
          total_scenes: number;
        };
        let msg = `تم توليد ${summary.generated.length} من ${summary.total_scenes}. استمع للمشاهد أدناه.`;
        if (summary.failed.length) msg += ` فشل: ${summary.failed.map((f) => f.scene_id).join(", ")}.`;
        setTtsMessage(msg);
        await refreshProjectAudio(projectId);
      } else {
        setTtsMessage(finalJob.safe_error_ar || "تعذر توليد صوت المشروع.");
      }
    } catch (exc) {
      setTtsMessage(exc instanceof Error ? exc.message : "تعذر توليد صوت المشروع.");
    } finally {
      setTtsBusy(null);
    }
  }

  function ttsStatusClass(): string {
    if (ttsBusy === "health") return "checking";
    if (ttsHealth === null) return "disabled";
    if (!ttsHealth.configured) return "disabled";
    if (ttsHealth.remote_ok === false) return "error";
    if (ttsHealth.remote_ok === true) return "ready";
    return "disabled";
  }

  function ttsStatusLabel(): string {
    if (ttsBusy === "health") return "جاري الفحص...";
    if (ttsHealth === null) return "لم يتم الفحص بعد";
    if (!ttsHealth.configured) return "خدمة الصوت غير مفعّلة";
    if (ttsHealth.remote_ok === false) return "خدمة الصوت غير متصلة";
    if (ttsHealth.remote_ok === true) return "خدمة الصوت متصلة";
    return "خدمة الصوت مفعّلة (بانتظار فحص الاتصال)";
  }

  function audioActionDisabledReason(): string | undefined {
    if (!projectId) return "احفظ المشروع أولاً";
    if (!scenes.length) return "لا توجد مشاهد بعد";
    if (isDirty) return "لديك تغييرات غير محفوظة -- احفظ المشروع أولاً";
    if (!ttsHealth?.configured) return "خدمة الصوت غير مفعّلة";
    return undefined;
  }

  function ttsStatusText(status: string): string {
    switch (status) {
      case "queued":
        return "في الانتظار";
      case "running":
        return "جاري التوليد";
      case "done":
        return "تم بنجاح";
      case "failed":
        return "فشل";
      default:
        return status;
    }
  }

  // ── Image Bridge (Phase 2.1 — جسر اتصال بمحرك صور حقيقي على AI Server) ─────────

  async function checkImageHealth() {
    setImageBusy("health");
    setImageMessage("");
    try {
      const r = await getJson<ImageHealthData>("/api/images/health");
      setImageHealth(r.data);
      if (r.errors.length) setImageMessage(r.errors.join(" "));
    } catch {
      setImageHealth(null);
      setImageMessage("تعذر فحص خدمة الصور.");
    } finally {
      setImageBusy(null);
    }
  }

  async function handleGenerateSceneImage() {
    if (!projectId) {
      setImageMessage("احفظ المشروع أولاً قبل توليد الصور.");
      return;
    }
    if (!scenes.length) {
      setImageMessage("لا توجد مشاهد لتوليد صورة لها.");
      return;
    }
    setImageBusy("scene");
    setImageMessage("جاري توليد صورة المشهد...");
    setImageJob(null);
    try {
      const r = await postJson<ImageJobData>(`/api/projects/${projectId}/images/jobs`, {
        scene_id: scenes[0].scene_id,
      });
      setImageJob(r.data);
      if (r.errors.length) setImageMessage(r.errors.join(" "));
      else setImageMessage("تم إرسال طلب توليد الصورة.");
    } catch (exc) {
      setImageMessage(exc instanceof Error ? exc.message : "تعذر إرسال طلب توليد الصورة.");
    } finally {
      setImageBusy(null);
    }
  }

  async function handleRefreshImageJob() {
    if (!imageJob?.job_id) return;
    setImageBusy("refresh");
    setImageMessage("");
    try {
      const r = await getJson<ImageJobData>(`/api/images/jobs/${imageJob.job_id}`);
      setImageJob(r.data);
      if (r.errors.length) setImageMessage(r.errors.join(" "));
      else if (r.data.status === "done") setImageMessage("تم توليد صورة المشهد.");
      else if (r.data.status === "failed") setImageMessage("فشل توليد صورة المشهد.");
    } catch (exc) {
      setImageMessage(exc instanceof Error ? exc.message : "تعذر تحديث حالة المهمة.");
    } finally {
      setImageBusy(null);
    }
  }

  function imageStatusClass(): string {
    if (imageBusy === "health") return "checking";
    if (imageHealth === null) return "disabled";
    if (!imageHealth.configured) return "disabled";
    if (imageHealth.remote_ok === false) return "error";
    if (imageHealth.remote_ok === true) return "ready";
    return "disabled";
  }

  function imageStatusLabel(): string {
    if (imageBusy === "health") return "جاري الفحص...";
    if (imageHealth === null) return "لم يتم الفحص بعد";
    if (!imageHealth.configured) return "خدمة الصور غير مفعّلة";
    if (imageHealth.remote_ok === false) return "خدمة الصور غير متصلة";
    if (imageHealth.remote_ok === true) return "خدمة الصور متصلة";
    return "خدمة الصور مفعّلة (بانتظار فحص الاتصال)";
  }

  function imageActionDisabledReason(): string | undefined {
    if (!projectId) return "احفظ المشروع أولاً";
    if (!scenes.length) return "لا توجد مشاهد بعد";
    if (!imageHealth?.configured) return "خدمة الصور غير مفعّلة";
    return undefined;
  }

  async function handlePreviewPrompt(sceneId: string) {
    if (!projectId) return;
    setPromptPreviewBusy(true);
    try {
      const r = await getJson<{ scene_id: string; prompt: string; negative_prompt: string }>(
        `/api/projects/${projectId}/images/scenes/${sceneId}/prompt-preview`,
      );
      setPromptPreview({ sceneId: r.data.scene_id, prompt: r.data.prompt, negativePrompt: r.data.negative_prompt });
    } catch (exc) {
      setImageMessage(exc instanceof Error ? exc.message : "تعذر تحضير معاينة الـ prompt.");
    } finally {
      setPromptPreviewBusy(false);
    }
  }

  async function handleGenerateOrRegenerateImage(sceneId: string) {
    if (!projectId) {
      setImageMessage("احفظ المشروع أولاً قبل توليد الصور.");
      return;
    }
    setGeneratingSceneId(sceneId);
    setImageMessage(`جاري توليد صورة المشهد ${sceneId}...`);
    try {
      const r = await postJson<{ scene_id: string; status: string }>(
        `/api/projects/${projectId}/images/scenes/${sceneId}/generate`,
      );
      if (r.errors.length) setImageMessage(r.errors.join(" "));
      else setImageMessage(`تم توليد صورة المشهد ${sceneId}.`);
      await refreshProjectImages(projectId);
    } catch (exc) {
      setImageMessage(exc instanceof Error ? exc.message : "تعذر توليد صورة المشهد.");
    } finally {
      setGeneratingSceneId(null);
    }
  }

  async function handleAskAssistant() {
    if (!projectId) {
      setAssistantMessage("احفظ المشروع أولاً قبل سؤال المساعد عنه.");
      return;
    }
    if (!assistantQuestion.trim()) {
      setAssistantMessage("اكتب سؤالاً أولاً.");
      return;
    }
    setAssistantBusy(true);
    setAssistantMessage("جاري التفكير...");
    setAssistantAnswer("");
    try {
      const r = await postJson<{ answer: string }>(`/api/projects/${projectId}/assistant/ask`, {
        question: assistantQuestion,
      });
      if (r.errors.length) {
        setAssistantMessage(r.errors.join(" "));
      } else {
        setAssistantAnswer(r.data.answer);
        setAssistantMessage("");
      }
    } catch (exc) {
      setAssistantMessage(exc instanceof Error ? exc.message : "تعذر الحصول على إجابة.");
    } finally {
      setAssistantBusy(false);
    }
  }

  async function handleGenerateStandaloneImage() {
    if (!standaloneImage.prompt.trim()) {
      setStandaloneImageMessage("اكتب وصف الصورة أولاً.");
      return;
    }
    setStandaloneImageBusy(true);
    setStandaloneImageMessage("جاري توليد الصورة...");
    setStandaloneImageJob(null);
    try {
      const seedValue = standaloneImage.seed.trim() ? Number(standaloneImage.seed) : undefined;
      const r = await postJson<{ job_id: string }>("/api/images/standalone/jobs", {
        prompt: standaloneImage.prompt,
        style_preset: standaloneImage.stylePreset,
        negative_prompt: standaloneImage.negativePrompt,
        width: standaloneImage.width,
        height: standaloneImage.height,
        seed: seedValue,
      });
      if (r.errors.length) {
        setStandaloneImageMessage(r.errors.join(" "));
        return;
      }
      const jobId = r.data.job_id;
      let finalJob: ImageJobData | null = null;
      for (let attempt = 0; attempt < 80; attempt++) {
        const jobR = await getJson<ImageJobData>(`/api/images/jobs/${jobId}`);
        finalJob = jobR.data;
        setStandaloneImageJob(jobR.data);
        if (jobR.data.status === "done" || jobR.data.status === "failed") break;
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      setStandaloneImageMessage(
        finalJob?.status === "failed" ? finalJob.error || "فشل توليد الصورة." : "تم توليد الصورة.",
      );
    } catch (exc) {
      setStandaloneImageMessage(exc instanceof Error ? exc.message : "تعذر توليد الصورة.");
    } finally {
      setStandaloneImageBusy(false);
    }
  }

  async function handleGenerateAllImages() {
    if (!projectId) {
      setImageMessage("احفظ المشروع أولاً قبل توليد الصور.");
      return;
    }
    if (!scenes.length) {
      setImageMessage("لا توجد مشاهد لتوليد صور لها.");
      return;
    }
    setImageBusy("all");
    setImageMessage(`جاري توليد صور ${scenes.length} مشهد، قد تستغرق 1-3 دقائق حسب عدد المشاهد...`);
    try {
      const r = await postJson<JobRecord>(`/api/projects/${projectId}/images/generate-all/jobs`);
      if (r.errors.length) {
        setImageMessage(r.errors.join(" "));
        return;
      }
      const finalJob = await pollJob(r.data.job_id, (job) => {
        setImageMessage(job.message_ar || `جاري توليد صورة المشهد ${job.current_step} من ${job.total_steps}...`);
      });
      if (finalJob.status === "done" && finalJob.result_summary) {
        const summary = finalJob.result_summary as {
          generated: string[];
          failed: { scene_id: string; error: string }[];
          total_scenes: number;
        };
        let msg = `تم توليد صور ${summary.generated.length} من ${summary.total_scenes} مشهد.`;
        if (summary.failed.length) msg += ` فشل: ${summary.failed.map((f) => f.scene_id).join(", ")}.`;
        setImageMessage(msg);
        await refreshProjectImages(projectId);
      } else {
        setImageMessage(finalJob.safe_error_ar || "تعذر توليد صور المشروع.");
      }
    } catch (exc) {
      setImageMessage(exc instanceof Error ? exc.message : "تعذر توليد صور المشروع.");
    } finally {
      setImageBusy(null);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <main className="app-shell" dir="rtl">
      {/* Hero */}
      <section className="hero-section">
        <div className="hero-copy">
          <span className="phase-pill">Phase 3.1 — استوديو متكامل: صوت، صور، فيديو، ترجمة</span>
          <h1>AI Story Studio</h1>
          <p>حوّل قصتك إلى مشروع محفوظ، سكريبت راوي، مشاهد قابلة للتعديل، وصوت حقيقي تستمع إليه مباشرة.</p>
        </div>
        <div className={`status-chip ${config?.ollama_configured ? "ready" : "warning"}`}>
          <span>{config?.provider || "ollama"}</span>
          <strong>{config?.model || "qwen2.5:7b"}</strong>
          <small>{providerMessage}</small>
        </div>
      </section>

      <details className="glass-panel engine-dashboard">
        <summary>حالة الخدمات (Ollama / الصوت / الصور / ffmpeg)</summary>
        <div className="action-bar">
          <button onClick={handleCheckSystemStatus} disabled={systemStatusBusy}>
            {systemStatusBusy ? "جاري الفحص..." : "فحص حالة الخدمات"}
          </button>
        </div>
        {systemStatus && (
          <div className="studio-status-strip" aria-label="حالة الخدمات">
            <span>
              Ollama:{" "}
              {!systemStatus.ollama.base_url_configured
                ? "يحتاج إعداد (OLLAMA_BASE_URL)"
                : systemStatus.ollama.ok
                  ? `متصل (${systemStatus.ollama.model})`
                  : "غير متصل"}
            </span>
            <span>
              الصوت:{" "}
              {!systemStatus.tts.enabled
                ? "غير مفعّل"
                : !systemStatus.tts.configured
                  ? "يحتاج إعداد (TTS_SERVICE_URL)"
                  : systemStatus.tts.remote_ok
                    ? "متصل"
                    : "غير متصل"}
            </span>
            <span>
              الصور:{" "}
              {!systemStatus.image.enabled
                ? "غير مفعّل"
                : !systemStatus.image.configured
                  ? "يحتاج إعداد (IMAGE_SERVICE_URL)"
                  : systemStatus.image.remote_ok
                    ? "متصل"
                    : "غير متصل"}
            </span>
            <span>ffmpeg: {systemStatus.ffmpeg.available ? "متاح" : "غير متاح"}</span>
            <span>المشاريع المحفوظة محلياً: {projects.length}</span>
          </div>
        )}
        <p className="muted-text field-hint">
          لا تُعرض عناوين أو منافذ AI Server هنا عمداً — فقط حالة الاتصال. ملاحظات قياس الأداء
          (benchmark) في {systemStatus?.benchmark_notes_doc || "docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md"}.
        </p>
      </details>

      {error && <div className="error-banner">{error}</div>}
      {notice && <div className="notice-banner">{notice}</div>}

      <ProjectHeader
        title={title}
        projectId={projectId}
        isDirty={isDirty}
        sceneCount={scenes.length}
        audioCount={audioCount}
        imageCount={imageCount}
        hasVideo={hasVideo}
        loading={loading}
        onNewProject={handleNewProject}
        onSaveProject={handleSaveProject}
        onDownloadZip={handleDownloadPackage}
      />

      <StudioStepper steps={studioSteps} activeStep={activeStep} onSelect={setActiveStep} />

      {/* Project workspace */}
      <section className="project-panel glass-panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">Project Workspace</span>
            <h2>المشاريع المحفوظة</h2>
          </div>
          <div className="project-actions">
            <button onClick={handleNewProject} disabled={loading !== null}>
              {loading === "new" ? "جاري الإنشاء..." : "مشروع جديد"}
            </button>
            <button onClick={handleSaveProject} disabled={loading !== null}>
              {loading === "save" ? "جاري الحفظ..." : projectId ? "حفظ التغييرات" : "حفظ المشروع"}
            </button>
            <button
              className="danger-button"
              onClick={handleDeleteProject}
              disabled={!projectId || loading !== null}
            >
              حذف المشروع
            </button>
          </div>
        </div>
        <div className="project-list">
          {projects.length === 0 && (
            <span className="muted-text">لا توجد مشاريع محفوظة بعد.</span>
          )}
          {projects.map((p) => (
            <button
              key={p.project_id}
              className={p.project_id === projectId ? "project-item active" : "project-item"}
              onClick={() => handleLoadProject(p.project_id)}
              disabled={loading !== null}
            >
              <strong>{p.title}</strong>
              <small>
                {p.scene_count} مشاهد · {new Date(p.updated_at).toLocaleString("ar")}
              </small>
            </button>
          ))}
        </div>
      </section>

      {/* Main workspace */}
      <section className="workspace-grid">
        {/* Left: Story editor */}
        {activeStep === "story" && (
        <div className="glass-panel editor-panel studio-step-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">Story Input</span>
              <h2>مساحة القصة</h2>
            </div>
            <button className="ghost-button" onClick={() => setStoryText(SAMPLE_STORY)}>
              تحميل مثال
            </button>
          </div>

          <label>
            عنوان المشروع
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>

          <label className="story-label">
            نص القصة الأصلي
            <textarea
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              placeholder="اكتب القصة العربية هنا..."
            />
          </label>
          {isLongStory && (
            <p className="muted-text field-hint">
              سيتم تحسين القصة على أجزاء لأن النص طويل ({storyText.trim().length} حرف). كل جزء يُحسَّن
              بطلب منفصل لـ Ollama حتى لا يفشل الطلب بسبب طول النص.
            </p>
          )}

          <label className="story-label">
            سكريبت الراوي المحسن
            <textarea
              className="compact-textarea"
              value={improvedText}
              onChange={(e) => setImprovedText(e.target.value)}
              placeholder="سيظهر النص المحسن هنا، ويمكنك تعديله قبل الحفظ أو التقسيم."
            />
          </label>

          <div className="tone-selector" aria-label="اختيار النبرة">
            {TONES.map((item) => (
              <button
                key={item}
                className={item === tone ? "tone active" : "tone"}
                onClick={() => setTone(item)}
                title={TONE_DESCRIPTIONS[item]}
              >
                {item}
              </button>
            ))}
          </div>
          {TONE_DESCRIPTIONS[tone] && <p className="muted-text field-hint">{TONE_DESCRIPTIONS[tone]}</p>}

          <div className="action-bar">
            <button onClick={handleTestOllama} disabled={loading !== null}>
              {loading === "test" ? "جاري الاختبار..." : "اختبار Ollama"}
            </button>
            <button onClick={handleImproveStory} disabled={!canRun}>
              {loading === "improve"
                ? isLongStory
                  ? "جاري تحسين القصة على أجزاء..."
                  : "جاري التحسين..."
                : "تحسين القصة"}
            </button>
            {loading === "improve" && improveJobId && (
              <button onClick={handleCancelImprove} disabled={improveCancelBusy || improveJob?.cancel_requested}>
                {improveCancelBusy
                  ? "جاري إرسال الإلغاء..."
                  : improveJob?.cancel_requested
                  ? "سيتم الإيقاف عند أول نقطة آمنة..."
                  : "إلغاء العملية"}
              </button>
            )}
            <button onClick={handleSplitScenes} disabled={!canRun}>
              {loading === "split" ? "جاري التقسيم..." : "تقسيم إلى مشاهد"}
            </button>
            <button onClick={handleSaveProject} disabled={loading !== null}>
              {loading === "save" ? "جاري الحفظ..." : "حفظ المشروع"}
            </button>
            <button
              className="download-button"
              onClick={handleDownloadJson}
              disabled={!scenes.length}
            >
              تحميل scenes.json
            </button>
            <button
              className="download-button"
              onClick={handleDownloadPackage}
              disabled={!projectId || loading !== null}
              title={!projectId ? "احفظ المشروع أولاً" : undefined}
            >
              {loading === "package" ? "جاري التجهيز..." : "تحميل حزمة المشروع ZIP"}
            </button>
          </div>
          {improveProgress && <p className="muted-text">{improveProgress}</p>}
          {loading === "improve" && improveJobId && (
            <div className="continuity-controls">
              <p className="muted-text">
                المرحلة: {JOB_PHASE_LABELS[improveJob?.phase || ""] || "جاري التحضير"}
              </p>
              <p className="muted-text">الوقت المنقضي: {formatElapsed(tickingElapsedSeconds)}</p>
              <p className="muted-text">
                آخر نشاط:{" "}
                {improveJob?.last_activity_at
                  ? (() => {
                      const secondsSinceActivity = (Date.now() - new Date(improveJob.last_activity_at as string).getTime()) / 1000;
                      if (secondsSinceActivity < ollamaTimeoutSeconds) {
                        return `منذ ${Math.max(0, Math.round(secondsSinceActivity))} ثوانٍ -- Ollama ما زال يعالج.`;
                      }
                      return "لم يصل نشاط جديد من Ollama، قد تكون العملية متوقفة.";
                    })()
                  : "بانتظار أول استجابة..."}
              </p>
              <p className="muted-text">
                التقدم:{" "}
                {improveJob && improveJob.total_steps > 1
                  ? `الجزء ${improveJob.current_step} من ${improveJob.total_steps}`
                  : improveJob?.progress_percent != null
                  ? `${improveJob.progress_percent}%`
                  : "جزء واحد"}
              </p>
              <p className="muted-text">
                ETA:{" "}
                {improveJob?.estimated_remaining_seconds != null && improveJob.estimated_remaining_seconds > 0
                  ? `حوالي ${formatElapsed(improveJob.estimated_remaining_seconds)} (تقديري)`
                  : "سيظهر الوقت التقديري بعد اكتمال أول جزء."}
              </p>
            </div>
          )}
          {toneAnalysisInfo && toneAnalysisInfo.requestedTone === AUTO_TONE_VALUE && (
            <p className="muted-text field-hint">
              النبرة المقترحة: {toneAnalysisInfo.resolvedTone}
              {toneAnalysisInfo.reasonAr ? ` — لأن ${toneAnalysisInfo.reasonAr}` : ""}
              {toneAnalysisInfo.analysisFallback ? " (تعذّر التحليل التلقائي، استُخدمت نبرة افتراضية)" : ""}
            </p>
          )}
        </div>

        )}

        {/* Right: Scene editor */}
        {activeStep !== "story" && (
        <div className="glass-panel result-panel studio-step-panel">
          {activeStep === "scenes" && (
          <>
          <div className="panel-header">
            <div>
              <span className="eyebrow">Editable Scenes</span>
              <h2>المشاهد</h2>
            </div>
            <span className="project-id-chip">
              {projectId ? `ID: ${projectId.slice(0, 8)}` : "غير محفوظ"}
            </span>
          </div>

          {!scenes.length && (
            <div className="empty-state">
              ابدأ بتحسين القصة أو تقسيمها. بعد توليد المشاهد ستستطيع تعديلها وحفظها وإعادة
              تصدير scenes.json.
            </div>
          )}

          {scenes.length > 0 && (
            <section className="scene-list">
              {/* Stats bar */}
              <div className="scene-stats-bar">
                <span className="scene-stat">{scenes.length} مشهد</span>
                <span className="scene-stat">{sceneStats.totalDuration} ث إجمالي</span>
                {sceneStats.invalidCount > 0 && (
                  <span className="scene-stat scene-stat--warn">
                    ⚠ {sceneStats.invalidCount} تحذير
                  </span>
                )}
              </div>

              {scenes.map((scene, index) => {
                const isOpen = expandedIndices.has(index);
                const warnings = getSceneWarnings(scene);
                const preview =
                  scene.narration_ar.length > 80
                    ? scene.narration_ar.slice(0, 80) + "…"
                    : scene.narration_ar;

                return (
                  <article
                    className={`scene-card${isOpen ? " scene-card--open" : ""}`}
                    key={`scene-${index}`}
                  >
                    {/* Clickable header */}
                    <div
                      className="scene-card-header"
                      onClick={() => toggleScene(index)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && toggleScene(index)}
                    >
                      <span className="scene-number">{scene.scene_id}</span>
                      <span className="scene-header-info">
                        <strong className="scene-card-title">
                          {scene.title_ar || <em className="muted-text">بدون عنوان</em>}
                        </strong>
                        {!isOpen && preview && (
                          <span className="scene-summary-text">{preview}</span>
                        )}
                      </span>
                      <span className="scene-header-meta">
                        {!isOpen && (
                          <span className="duration">{scene.duration_seconds} ث</span>
                        )}
                        <span className="scene-toggle-icon">{isOpen ? "▲" : "▼"}</span>
                      </span>
                    </div>

                    {/* Action buttons */}
                    <div className="scene-actions">
                      <button
                        className="scene-action-btn"
                        title="تحريك لأعلى"
                        onClick={() => moveSceneUp(index)}
                        disabled={index === 0}
                      >
                        ↑
                      </button>
                      <button
                        className="scene-action-btn"
                        title="تحريك لأسفل"
                        onClick={() => moveSceneDown(index)}
                        disabled={index === scenes.length - 1}
                      >
                        ↓
                      </button>
                      <button
                        className="scene-action-btn"
                        title="نسخ المشهد"
                        onClick={() => duplicateScene(index)}
                      >
                        نسخ
                      </button>
                      <button
                        className="scene-action-btn"
                        title="إضافة مشهد بعده"
                        onClick={() => addSceneAfter(index)}
                      >
                        + إضافة
                      </button>
                      <button
                        className="scene-action-btn scene-action-btn--danger"
                        title="حذف المشهد"
                        onClick={() => deleteSceneAt(index)}
                      >
                        حذف
                      </button>
                    </div>

                    {/* Validation warnings */}
                    {warnings.length > 0 && (
                      <div className="scene-warnings">
                        {warnings.map((w, wi) => (
                          <span key={wi} className="scene-warning-item">
                            ⚠ {w}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Expanded fields */}
                    {isOpen && (
                      <div className="scene-card-body">
                        <label>
                          عنوان المشهد
                          <input
                            value={scene.title_ar}
                            onChange={(e) => updateScene(index, "title_ar", e.target.value)}
                          />
                        </label>
                        <label>
                          نص الراوي
                          <textarea
                            className="scene-textarea"
                            value={scene.narration_ar}
                            onChange={(e) => updateScene(index, "narration_ar", e.target.value)}
                          />
                        </label>
                        <label>
                          الوصف البصري
                          <textarea
                            className="scene-textarea"
                            value={scene.visual_description_ar}
                            onChange={(e) =>
                              updateScene(index, "visual_description_ar", e.target.value)
                            }
                          />
                        </label>
                        <label>
                          Visual prompt
                          <textarea
                            className="scene-textarea ltr-field"
                            dir="ltr"
                            value={scene.image_prompt_en}
                            onChange={(e) =>
                              updateScene(index, "image_prompt_en", e.target.value)
                            }
                          />
                        </label>
                        <label>
                          المدة بالثواني (3-180)
                          <input
                            type="number"
                            min="3"
                            max="180"
                            value={scene.duration_seconds}
                            onChange={(e) =>
                              updateScene(index, "duration_seconds", Number(e.target.value))
                            }
                          />
                        </label>
                      </div>
                    )}
                  </article>
                );
              })}
            </section>
          )}

          {rawJson && (
            <section className="json-preview">
              <button className="ghost-button" onClick={() => setRawJsonOpen((v) => !v)}>
                {rawJsonOpen ? "إخفاء JSON" : "عرض JSON المتقدم"}
              </button>
              {rawJsonOpen && <pre dir="ltr">{rawJson}</pre>}
            </section>
          )}

          </>
          )}

          {activeStep === "audio" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Audio Bridge</span>
                <h2>
                  استوديو الصوت <span className="badge-experimental">تجريبي</span>
                </h2>
              </div>
              <span className={`tts-status-chip tts-status--${ttsStatusClass()}`}>{ttsStatusLabel()}</span>
            </div>

            <p className="muted-text">
              توليد الصوت يتم عبر TTS Worker على AI Server من خلال backend فقط — المتصفح لا يتصل
              بأي خدمة على AI Server مباشرة.
            </p>

            <p className="muted-text">
              الأصوات المعروضة هنا هي التي نجح النظام في اكتشافها وتشغيلها فعلياً — لا تُعرض هنا أي
              أصوات لم يتم التأكد من عملها. لا يوجد أي صوت مشاهير أو صوت مستنسخ من شخص حقيقي بدون
              إذنه الصريح في هذا المشروع.
            </p>
            {(() => {
              const availableVoices = ttsVoices.voices.filter((v) => v.available);
              return availableVoices.length <= 1 ? (
                <p className="muted-text">
                  الصوت المتاح حالياً:{" "}
                  <strong>
                    {availableVoices[0]?.display_name_ar ?? "—"} (
                    {voiceGenderLabel(availableVoices[0]?.gender ?? "unknown")})
                  </strong>{" "}
                  فقط — لا يوجد صوت آخر للاختيار منه بعد. اختيار اللغة غير متاح حالياً إلا للعربية.
                  هذا ليس عطلاً — القائمتان ستُفعَّلان تلقائياً عند إضافة أصوات/لغات حقيقية معتمدة لاحقاً.
                </p>
              ) : (
                <div className="tts-selectors">
                  <label>
                    الصوت
                    <select value={selectedVoiceId ?? ""} onChange={(e) => setSelectedVoiceId(e.target.value)}>
                      {availableVoices.map((v) => (
                        <option key={v.voice_id} value={v.voice_id}>
                          {v.display_name_ar} ({voiceGenderLabel(v.gender)})
                          {v.experimental ? " — تجريبي" : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    اللغة
                    <select
                      value={ttsVoices.languages[0]?.language ?? "ar"}
                      disabled
                      title="اختيار اللغة غير متاح حالياً إلا للعربية"
                    >
                      {ttsVoices.languages.map((l) => (
                        <option key={l.language} value={l.language}>
                          {l.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              );
            })()}

            <BusyNotice busy={ttsBusy === "scene" || ttsBusy === "project"} message={ttsMessage} />

            <div className="action-bar">
              <button onClick={checkTtsHealth} disabled={ttsBusy !== null}>
                {ttsBusy === "health" ? "جاري الفحص..." : "فحص خدمة الصوت"}
              </button>
              <button
                onClick={() => handleGenerateAudio("scene")}
                disabled={!projectId || !scenes.length || isDirty || !ttsHealth?.configured || ttsBusy !== null}
                title={audioActionDisabledReason()}
              >
                {ttsBusy === "scene" ? "جاري توليد صوت المشهد..." : "توليد صوت للمشهد الأول"}
              </button>
              <button
                onClick={handleGenerateAllAudio}
                disabled={!projectId || !scenes.length || isDirty || !ttsHealth?.configured || ttsBusy !== null}
                title={audioActionDisabledReason()}
              >
                {ttsBusy === "project" ? "جاري توليد صوت المشروع..." : "توليد صوت للمشروع"}
              </button>
            </div>

            {projectAudio && projectAudio.scenes.some((s) => s.has_audio) && (
              <div className="saved-audio-list">
                <h3>الأصوات المحفوظة للمشاهد</h3>
                {projectAudio.scenes
                  .filter((s) => s.has_audio && s.url)
                  .map((s) => {
                    const url = `${API_BASE_URL}${s.url}`;
                    return (
                      <div key={s.scene_id} className="tts-job-card">
                        <span>مشهد {s.scene_id}</span>
                        <audio controls src={url} className="tts-audio-player" />
                        <a className="ghost-button" href={url} download>
                          تحميل صوت المشهد
                        </a>
                        {s.audio_bytes != null && <small>{Math.round(s.audio_bytes / 1024)} KB</small>}
                        {s.audio_voice_id && (
                          <small>
                            صوت:{" "}
                            {ttsVoices.voices.find((v) => v.voice_id === s.audio_voice_id)?.display_name_ar ??
                              s.audio_voice_id}
                          </small>
                        )}
                      </div>
                    );
                  })}
              </div>
            )}

            {projectAudio?.final_story.has_audio && projectAudio.final_story.url && (
              <div className="tts-job-card">
                <span>صوت القصة كاملة</span>
                <audio
                  controls
                  src={`${API_BASE_URL}${projectAudio.final_story.url}`}
                  className="tts-audio-player"
                />
                <a
                  className="ghost-button"
                  href={`${API_BASE_URL}${projectAudio.final_story.url}`}
                  download
                >
                  تحميل صوت القصة كاملة
                </a>
              </div>
            )}
          </section>
          )}

          {activeStep === "images" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Image Bridge</span>
                <h2>
                  استوديو الصور <span className="badge-experimental">تجريبي</span>
                </h2>
              </div>
              <span className={`tts-status-chip tts-status--${imageStatusClass()}`}>
                {imageStatusLabel()}
              </span>
            </div>

            <p className="muted-text">
              توليد الصور يتم عبر محرك صور (ComfyUI + SDXL) على AI Server من خلال backend فقط —
              المتصفح لا يتصل بأي خدمة على AI Server مباشرة. الجودة تجريبية وقابلة لإعادة التوليد،
              ولم تُعتمد بعد كجودة نهائية للمنتج (راجع docs/IMAGE_QUALITY_APPROVAL_CHECKLIST.md).
            </p>

            <div className="continuity-controls">
              <h3>ضبط الاستمرارية البصرية (اختياري)</h3>
              <p className="muted-text">
                هذه الإعدادات تُضاف تلقائياً إلى كل مشهد عند توليد صورته، لتقليل اختلاف الأسلوب
                بين المشاهد. تُحفظ مع المشروع عند الضغط على "حفظ المشروع".
              </p>
              <label>
                النمط البصري
                <select value={stylePreset} onChange={(e) => setStylePreset(e.target.value)}>
                  {(stylePresets.length
                    ? stylePresets
                    : [{ key: "cinematic_realistic", prompt_prefix: "" }]
                  ).map((p) => (
                    <option key={p.key} value={p.key}>
                      {presetLabel(p.key)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="simple-image-prompt">
                توجيه بصري عام (اختياري)
                <p className="muted-text field-hint">
                  اختياري: اتركه فارغاً ليستخدم النظام وصف كل مشهد تلقائياً (يمكنك الضغط على
                  "توليد صور كل المشاهد" مباشرة بدون كتابة أي شيء هنا). اكتب في هذا الحقل فقط لو
                  تريد توجيه الأسلوب العام (إضاءة، إحساس) لكل صور القصة.
                </p>
                <textarea
                  rows={3}
                  value={storyStyleBible}
                  onChange={(e) => setStoryStyleBible(e.target.value)}
                  placeholder="مثال: إضاءة سينمائية دافئة، واقعية عالية (اختياري — اتركه فارغاً إن لم ترد توجيهاً عاماً)"
                />
              </label>
              <details className="advanced-continuity">
                <summary>إعدادات الاستمرارية المتقدمة</summary>
              <p className="muted-text">
                حقل "توجيه بصري عام" أعلاه يُستخدم كأسلوب عام للقصة (إضاءة، إحساس، نوع الكاميرا). كل
                الحقول هنا اختيارية أيضاً، وتُضاف تلقائياً إلى وصف كل مشهد لتثبيت الشخصيات/المكان/
                العناصر عبر كل المشاهد وتقليل اختلافها بينها.
              </p>
              <label>
                الشخصيات الثابتة (الوصف الذي يجب أن يتكرر في كل مشهد)
                <textarea
                  rows={2}
                  value={characterBible}
                  onChange={(e) => setCharacterBible(e.target.value)}
                  placeholder="مثال: الراوي رجل مسن بلحية رمادية قصيرة، يرتدي معطفاً بنياً من الصوف"
                />
              </label>
              <label>
                المكان الثابت
                <textarea
                  rows={2}
                  value={locationBible}
                  onChange={(e) => setLocationBible(e.target.value)}
                  placeholder="مثال: غرفة خشبية قديمة، نافذة بإطار أبيض"
                />
              </label>
              <label>
                العناصر/الرموز المهمة
                <textarea
                  rows={2}
                  value={objectBible}
                  onChange={(e) => setObjectBible(e.target.value)}
                  placeholder="مثال: كتاب جلدي قديم يحمله الراوي في أغلب المشاهد"
                />
              </label>
              <label>
                Negative Prompt (ما يجب تجنبه في الصور)
                <textarea
                  rows={2}
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  placeholder="افتراضي: blurry, low quality, distorted, watermark, text"
                />
              </label>
              <p className="muted-text field-hint">
                هذه البيانات تقلل تغيّر الشخصيات والأماكن بين المشاهد، لكنها لا تضمن ثباتاً كاملاً —
                كل مشهد لا يزال توليداً مستقلاً بدون ذاكرة حقيقية بين المشاهد. ثبات أقوى يحتاج لاحقاً
                إلى صورة مرجعية (IPAdapter/ControlNet)، غير مفعّلة الآن.
              </p>
              {scenes.length > 0 && (
                <div className="action-bar">
                  <button
                    className="ghost-button"
                    onClick={() => handlePreviewPrompt(scenes[0].scene_id)}
                    disabled={!projectId || promptPreviewBusy}
                    title={!projectId ? "احفظ المشروع أولاً" : undefined}
                  >
                    {promptPreviewBusy ? "جاري التحضير..." : "معاينة prompt المشهد الأول"}
                  </button>
                </div>
              )}
              {promptPreview && (
                <div className="tts-job-card">
                  <small className="muted-text">prompt المُجمَّع لمشهد {promptPreview.sceneId} (إنجليزي، يُرسل لمحرك الصور كما هو):</small>
                  <textarea readOnly rows={4} value={promptPreview.prompt} />
                  <small className="muted-text">negative prompt: {promptPreview.negativePrompt}</small>
                </div>
              )}
              </details>
            </div>

            <div className="continuity-controls">
              <h3>قائمة السلامة والحقوق (اختياري)</h3>
              <p className="muted-text">
                توضيح خفيف لمصدر المحتوى قبل التوسع في مراجع صوت/صورة لاحقاً. لا توقف هذا الإنتاج
                الحالي، فقط تحذير إن كان المصدر غير معروف. قواعد عامة يجب اتباعها دائماً:
              </p>
              <ul className="muted-text">
                <li>لا تستخدم صوت مشاهير أو أشخاص حقيقيين بدون إذن صريح منهم.</li>
                <li>لا تستخدم صوراً مرجعية لا تملك حق استخدامها.</li>
                <li>لا تنشر أي محتوى للعامة قبل إضافة مصادقة/حماية مناسبة للمشروع.</li>
                <li>راجع أي محتوى مولّد بشرياً قبل استخدامه تجارياً.</li>
              </ul>
              <label>
                مصدر المحتوى
                <select
                  value={safetySourceType}
                  onChange={(e) => setSafetySourceType(e.target.value as SafetySourceType)}
                >
                  <option value="own_content">محتوى خاص بي</option>
                  <option value="licensed">مرخّص</option>
                  <option value="generated">مولّد بالذكاء الاصطناعي</option>
                  <option value="unknown">غير معروف</option>
                </select>
              </label>
              <label>
                تأكيد الموافقة (consent)
                <select
                  value={safetyConsentConfirmed}
                  onChange={(e) => setSafetyConsentConfirmed(e.target.value as SafetyConsent)}
                >
                  <option value="yes">نعم</option>
                  <option value="no">لا</option>
                  <option value="not_applicable">غير منطبق</option>
                </select>
              </label>
              <label>
                ينطبق على
                <select
                  multiple
                  value={safetyAppliesTo}
                  onChange={(e) =>
                    setSafetyAppliesTo(Array.from(e.target.selectedOptions).map((o) => o.value as SafetyAppliesTo))
                  }
                >
                  <option value="voice">صوت</option>
                  <option value="image_reference">صورة مرجعية</option>
                  <option value="music_sfx">موسيقى/مؤثرات صوتية</option>
                  <option value="person_likeness">شكل/هوية شخص</option>
                </select>
              </label>
              <label>
                ملاحظات الحقوق (اختياري)
                <textarea
                  rows={2}
                  value={safetyRightsNotes}
                  onChange={(e) => setSafetyRightsNotes(e.target.value)}
                  placeholder="مثال: الصور من تصويري الخاص، لا حاجة لترخيص إضافي"
                />
              </label>
              {safetySourceType === "unknown" && (
                <p className="notice-banner">تنبيه: مصدر المحتوى غير معروف — راجع هذا قبل أي نشر علني.</p>
              )}
            </div>

            <BusyNotice
              busy={imageBusy === "scene" || imageBusy === "all" || generatingSceneId !== null}
              message={imageMessage}
            />

            <div className="action-bar">
              <button onClick={checkImageHealth} disabled={imageBusy !== null}>
                {imageBusy === "health" ? "جاري الفحص..." : "فحص خدمة الصور"}
              </button>
              <button
                onClick={handleGenerateSceneImage}
                disabled={!projectId || !scenes.length || !imageHealth?.configured || imageBusy !== null}
                title={imageActionDisabledReason()}
              >
                {imageBusy === "scene" ? "جاري توليد صورة المشهد..." : "توليد صورة للمشهد الأول (معاينة)"}
              </button>
              <button
                onClick={handleGenerateAllImages}
                disabled={!projectId || !scenes.length || !imageHealth?.configured || imageBusy !== null}
                title={imageActionDisabledReason()}
              >
                {imageBusy === "all" ? "جاري توليد صور المشروع..." : "توليد صور كل المشاهد"}
              </button>
            </div>

            {imageJob && (
              <div className="tts-job-card">
                {imageJob.job_id && (
                  <span>
                    Job ID: <code dir="ltr">{imageJob.job_id}</code>
                  </span>
                )}
                {imageJob.status && <span>الحالة: {ttsStatusText(imageJob.status)}</span>}
                {imageJob.job_id && (
                  <button className="ghost-button" onClick={handleRefreshImageJob} disabled={imageBusy !== null}>
                    {imageBusy === "refresh" ? "جاري التحديث..." : "تحديث الحالة"}
                  </button>
                )}
                {imageJob.status === "done" && imageJob.job_id && (
                  <span className="tts-audio-result">
                    <img
                      src={`${API_BASE_URL}/api/images/jobs/${imageJob.job_id}/download`}
                      alt="صورة المشهد المولّدة"
                      className="scene-image-preview"
                    />
                    <a
                      className="ghost-button"
                      href={`${API_BASE_URL}/api/images/jobs/${imageJob.job_id}/download`}
                      download
                    >
                      تحميل صورة المشهد
                    </a>
                  </span>
                )}
              </div>
            )}

            {projectImages && projectImages.scenes.length > 0 && (
              <div className="saved-audio-list">
                <h3>صور المشاهد المحفوظة</h3>
                {projectImages.scenes.map((s) => {
                  const isGenerating = generatingSceneId === s.scene_id;
                  return (
                    <div key={s.scene_id} className="tts-job-card">
                      <span>مشهد {s.scene_id}</span>
                      {s.has_image && s.url ? (
                        <>
                          <img
                            src={`${API_BASE_URL}${s.url}`}
                            alt={`صورة المشهد ${s.scene_id}`}
                            className="scene-image-preview"
                          />
                          <a className="ghost-button" href={`${API_BASE_URL}${s.url}`} download>
                            تحميل صورة المشهد
                          </a>
                          {s.image_bytes != null && (
                            <small>
                              {s.image_width}×{s.image_height}، {Math.round(s.image_bytes / 1024)} KB
                            </small>
                          )}
                        </>
                      ) : (
                        <small className="muted-text">لا توجد صورة محفوظة لهذا المشهد بعد</small>
                      )}
                      <button
                        className="ghost-button"
                        onClick={() => handleGenerateOrRegenerateImage(s.scene_id)}
                        disabled={!imageHealth?.configured || generatingSceneId !== null || imageBusy !== null}
                        title={!imageHealth?.configured ? "خدمة الصور غير مفعّلة" : undefined}
                      >
                        {isGenerating ? "جاري التوليد..." : s.has_image ? "إعادة توليد الصورة" : "توليد صورة لهذا المشهد"}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
          )}

          {activeStep === "video" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Video Assembly</span>
                <h2>
                  تجميع الفيديو <span className="badge-experimental">تجريبي</span>
                </h2>
              </div>
            </div>

            <p className="muted-text">
              يجمّع backend (عبر ffmpeg) صور المشاهد المحفوظة مع الصوت المحفوظ في فيديو MP4 واحد —
              بدون فيديو بالذكاء الاصطناعي وبدون انتقالات متقدمة، فقط نسخة عملية أولى. المشاهد بلا
              صورة محفوظة يتم تجاوزها.
            </p>

            <label>
              نوع الحركة
              <select value={videoMode} onChange={(e) => setVideoMode(e.target.value as VideoMode)}>
                <option value="static">ثابت (بدون حركة)</option>
                <option value="ken_burns">حركة خفيفة (تقريب تدريجي على الصورة)</option>
              </select>
            </label>
            <label>
              الانتقال بين المشاهد
              <select value={videoTransition} onChange={(e) => setVideoTransition(e.target.value as VideoTransition)}>
                <option value="none">بدون انتقال (قطع مباشر)</option>
                <option value="fade">تلاشي خفيف داخل كل مشهد</option>
              </select>
            </label>
            <p className="muted-text field-hint">
              هذا تحريك خفيف للصور عبر ffmpeg فقط، وليس فيديو بالذكاء الاصطناعي مثل Veo أو Runway.
              "تلاشي خفيف" يعني أن كل مشهد يبدأ وينتهي بتلاشي صغير، وليس مزجاً حقيقياً بين مشهدين
              متتاليين. اضغط "حفظ المشروع" لحفظ هذا الإعداد قبل تجميع الفيديو.
            </p>

            {scenes.length > 0 && audioCount === 0 && (
              <p className="error-banner">
                لم يتم العثور على صوت محفوظ للمشاهد. سيُجمّع الفيديو بدون صوت أو بمدد تقديرية.
              </p>
            )}
            {scenes.length > 0 && audioCount > 0 && audioCount < scenes.length && (
              <p className="notice-banner">
                صوت محفوظ لـ {audioCount} من {scenes.length} مشهد فقط -- المشاهد الباقية ستُجمَّع بصوت صامت
                بمدتها التقديرية.
              </p>
            )}

            <BusyNotice busy={videoBusy} message={videoMessage} />

            <div className="action-bar">
              <button
                onClick={handleRenderVideo}
                disabled={!projectId || !scenes.length || videoBusy}
                title={!projectId ? "احفظ المشروع أولاً" : !scenes.length ? "لا توجد مشاهد بعد" : undefined}
              >
                {videoBusy ? "جاري تجميع الفيديو..." : "تجميع فيديو القصة"}
              </button>
              {projectId && (
                <button className="ghost-button" onClick={() => refreshProjectVideo(projectId)} disabled={videoBusy}>
                  تحديث الحالة
                </button>
              )}
            </div>

            {projectVideo?.has_video && projectVideo.url && (
              <div className="tts-job-card">
                <video
                  src={`${API_BASE_URL}${projectVideo.url}`}
                  controls
                  className="scene-image-preview"
                  style={{ maxWidth: "420px" }}
                />
                <a className="ghost-button" href={`${API_BASE_URL}${projectVideo.url}`} download>
                  تحميل الفيديو
                </a>
                {projectVideo.duration_seconds != null && (
                  <small>
                    {projectVideo.duration_seconds} ثانية، {projectVideo.included_scenes.length} مشهد
                    {projectVideo.video_bytes != null
                      ? `، ${Math.round(projectVideo.video_bytes / 1024)} KB`
                      : ""}
                  </small>
                )}
              </div>
            )}
            {projectId && scenes.length > 0 && (
              <div className="action-bar">
                <a className="ghost-button" href={`${API_BASE_URL}/api/projects/${projectId}/subtitles.srt`} download>
                  تحميل SRT
                </a>
                <a className="ghost-button" href={`${API_BASE_URL}/api/projects/${projectId}/subtitles.vtt`} download>
                  تحميل VTT
                </a>
              </div>
            )}
          </section>
          )}

          {activeStep === "timeline" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Production Timeline</span>
                <h2>الخط الزمني</h2>
              </div>
            </div>
            <p className="muted-text">
              حالة كل مشهد من النص إلى الفيديو في مكان واحد. اضغط "الانتقال للمشهد" للتعديل، أو
              استخدم الأزرار للاستماع/معاينة/إعادة التوليد مباشرة.
            </p>

            <div className="continuity-controls">
              <h3>سجل العمليات الأخيرة</h3>
              <div className="action-bar">
                <button className="ghost-button" onClick={refreshProjectJobs} disabled={!projectId || projectJobsBusy}>
                  {projectJobsBusy ? "جاري التحديث..." : "تحديث السجل"}
                </button>
              </div>
              {!projectJobs.length ? (
                <p className="muted-text">لا توجد عمليات مسجّلة لهذا المشروع بعد، أو لم يتم تحديث السجل.</p>
              ) : (
                <div className="scene-list">
                  {projectJobs.map((job) => (
                    <div key={job.job_id} className="scene-card">
                      <div className="scene-card-header">
                        <strong>{JOB_TYPE_LABELS[job.job_type] || job.job_type}</strong>
                        <span className={`tts-status-chip tts-status--${job.status === "done" ? "ready" : job.status === "failed" ? "error" : "warning"}`}>
                          {JOB_STATUS_LABELS[job.status] || job.status}
                        </span>
                      </div>
                      <p className="muted-text">
                        {job.message_ar || `${job.completed_steps} من ${job.total_steps}`}
                        {job.safe_error_ar ? ` — ${job.safe_error_ar}` : ""}
                      </p>
                    </div>
                  ))}
                </div>
              )}
              <p className="muted-text field-hint">
                لا يوجد إلغاء أو إعادة محاولة مباشرة من هنا حالياً — لإعادة أي عملية، استخدم زر
                التوليد نفسه من خطوته (الصوت/الصور/الفيديو/تحسين القصة).
              </p>
            </div>

            {!scenes.length ? (
              <p className="muted-text">لا توجد مشاهد بعد — ابدأ من خطوة "القصة" ثم "تقسيم إلى مشاهد".</p>
            ) : (
              <div className="scene-list">
                {scenes.map((scene, index) => {
                  const audioInfo = projectAudio?.scenes.find((s) => s.scene_id === scene.scene_id);
                  const imageInfo = projectImages?.scenes.find((s) => s.scene_id === scene.scene_id);
                  const isIncludedInVideo = projectVideo?.included_scenes?.includes(scene.scene_id);
                  const skipReason = projectVideo?.skipped_scenes?.find((s) => s.scene_id === scene.scene_id)?.reason;
                  const warnings = getSceneWarnings(scene);
                  return (
                    <div key={scene.scene_id} className="scene-card">
                      <div className="scene-card-header">
                        <strong>{index + 1}. {scene.title_ar || "(بدون عنوان)"}</strong>
                        <span className="muted-text">{scene.duration_seconds}s</span>
                      </div>
                      <p className="muted-text">{scene.narration_ar.slice(0, 120) || "(بدون نص راوٍ)"}</p>
                      <div className="studio-status-strip">
                        <span>الصوت: {audioInfo?.has_audio ? "✓ موجود" : "✗ غير موجود"}</span>
                        <span>الصورة: {imageInfo?.has_image ? "✓ موجودة" : "✗ غير موجودة"}</span>
                        <span>الترجمة: متوفرة دائماً (من نص الراوي)</span>
                        <span>
                          الفيديو: {isIncludedInVideo ? "✓ مُضمَّن" : skipReason ? `✗ تم تجاوزه (${skipReason})` : "لم يُجمَّع بعد"}
                        </span>
                        <span>المراجعة: {REVIEW_STATUS_LABELS[scene.review_status || "pending"]}</span>
                      </div>
                      {warnings.length > 0 && (
                        <p className="error-banner">{warnings.join(" · ")}</p>
                      )}
                      <div className="action-bar">
                        <button className="ghost-button" onClick={() => setActiveStep("scenes")}>
                          الانتقال للمشهد
                        </button>
                        {audioInfo?.has_audio && audioInfo.url && (
                          <audio controls src={`${API_BASE_URL}${audioInfo.url}`} style={{ height: "32px" }} />
                        )}
                        {imageInfo?.has_image && imageInfo.url && (
                          <img
                            src={`${API_BASE_URL}${imageInfo.url}`}
                            alt={`صورة المشهد ${scene.scene_id}`}
                            style={{ height: "48px", borderRadius: "6px" }}
                          />
                        )}
                        <button className="ghost-button" onClick={() => setActiveStep("images")}>
                          الذهاب للصور
                        </button>
                        <button className="ghost-button" onClick={() => setActiveStep("audio")}>
                          الذهاب للصوت
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
          )}

          {activeStep === "assets" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Asset Library</span>
                <h2>مكتبة الأصول</h2>
              </div>
            </div>
            <p className="muted-text">
              كل ملفات المشروع في مكان واحد، بدون فتح ZIP. كل التحميلات تمر عبر backend فقط — لا روابط
              لمجلدات أو لخادم AI الداخلي.
            </p>

            <div className="continuity-controls">
              <h3>القصة والمشاهد</h3>
              <div className="export-grid">
                {storyText.trim() ? (
                  <span className="asset-ready">النص الأصلي ({storyText.trim().length} حرف)</span>
                ) : (
                  <span className="asset-missing">لا يوجد نص أصلي</span>
                )}
                {improvedText.trim() ? (
                  <span className="asset-ready">السكريبت المحسّن ({improvedText.trim().length} حرف)</span>
                ) : (
                  <span className="asset-missing">لا يوجد سكريبت محسّن</span>
                )}
                {scenes.length > 0 ? (
                  <button className="ghost-button" onClick={handleDownloadJson}>
                    تحميل scenes.json ({scenes.length} مشهد)
                  </button>
                ) : (
                  <span className="asset-missing">لا توجد مشاهد</span>
                )}
              </div>
            </div>

            <div className="continuity-controls">
              <h3>الصوت</h3>
              <div className="export-grid">
                {scenes.map((scene) => {
                  const audioInfo = projectAudio?.scenes.find((s) => s.scene_id === scene.scene_id);
                  return audioInfo?.has_audio && audioInfo.url ? (
                    <div key={scene.scene_id} className="asset-row">
                      <audio controls src={`${API_BASE_URL}${audioInfo.url}`} style={{ height: "32px" }} />
                      <a className="ghost-button" href={`${API_BASE_URL}${audioInfo.url}`} download>
                        صوت مشهد {scene.scene_id}
                        {audioInfo.audio_bytes != null ? ` (${Math.round(audioInfo.audio_bytes / 1024)} KB)` : ""}
                      </a>
                    </div>
                  ) : (
                    <span key={scene.scene_id} className="asset-missing">صوت مشهد {scene.scene_id}: غير موجود</span>
                  );
                })}
                {projectAudio?.final_story.has_audio && projectAudio.final_story.url ? (
                  <div className="asset-row">
                    <audio controls src={`${API_BASE_URL}${projectAudio.final_story.url}`} style={{ height: "32px" }} />
                    <a className="ghost-button" href={`${API_BASE_URL}${projectAudio.final_story.url}`} download>
                      صوت القصة كاملة (final_story.wav)
                    </a>
                  </div>
                ) : (
                  <span className="asset-missing">صوت القصة كاملة: غير موجود (يحتاج صوتاً لمشهدين على الأقل)</span>
                )}
              </div>
            </div>

            <div className="continuity-controls">
              <h3>الصور</h3>
              <div className="export-grid">
                {scenes.map((scene) => {
                  const imageInfo = projectImages?.scenes.find((s) => s.scene_id === scene.scene_id);
                  return imageInfo?.has_image && imageInfo.url ? (
                    <div key={scene.scene_id} className="asset-row">
                      <img
                        src={`${API_BASE_URL}${imageInfo.url}`}
                        alt={`صورة المشهد ${scene.scene_id}`}
                        style={{ height: "56px", borderRadius: "6px" }}
                      />
                      <a className="ghost-button" href={`${API_BASE_URL}${imageInfo.url}`} download>
                        صورة مشهد {scene.scene_id}
                        {imageInfo.image_bytes != null ? ` (${Math.round(imageInfo.image_bytes / 1024)} KB)` : ""}
                      </a>
                      {imageInfo.image_seed != null && (
                        <small className="muted-text">seed: {imageInfo.image_seed}</small>
                      )}
                    </div>
                  ) : (
                    <span key={scene.scene_id} className="asset-missing">صورة مشهد {scene.scene_id}: غير موجودة</span>
                  );
                })}
              </div>
            </div>

            <div className="continuity-controls">
              <h3>الفيديو والترجمات</h3>
              <div className="export-grid">
                {projectVideo?.has_video && projectVideo.url ? (
                  <div className="asset-row">
                    <video
                      src={`${API_BASE_URL}${projectVideo.url}`}
                      controls
                      style={{ height: "80px", borderRadius: "6px" }}
                    />
                    <a className="ghost-button" href={`${API_BASE_URL}${projectVideo.url}`} download>
                      final_story.mp4
                      {projectVideo.duration_seconds != null ? ` — ${projectVideo.duration_seconds} ثانية` : ""}
                      {projectVideo.video_bytes != null ? ` (${Math.round(projectVideo.video_bytes / 1024)} KB)` : ""}
                    </a>
                  </div>
                ) : (
                  <span className="asset-missing">الفيديو: غير مُجمَّع بعد</span>
                )}
                {projectId && scenes.length > 0 ? (
                  <>
                    <a className="ghost-button" href={`${API_BASE_URL}/api/projects/${projectId}/subtitles.srt`} download>
                      subtitles.srt
                    </a>
                    <a className="ghost-button" href={`${API_BASE_URL}/api/projects/${projectId}/subtitles.vtt`} download>
                      subtitles.vtt
                    </a>
                  </>
                ) : (
                  <span className="asset-missing">الترجمات: لا توجد مشاهد بعد</span>
                )}
              </div>
            </div>

            <div className="continuity-controls">
              <h3>التصدير الكامل</h3>
              <div className="export-grid">
                <button
                  className="download-button"
                  onClick={handleDownloadPackage}
                  disabled={!projectId || loading !== null}
                  title={!projectId ? "احفظ المشروع أولاً" : undefined}
                >
                  {loading === "package" ? "جاري التجهيز..." : "تحميل export.zip"}
                </button>
              </div>
            </div>
          </section>
          )}

          {activeStep === "review" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Quality Review Board</span>
                <h2>مراجعة الجودة</h2>
              </div>
            </div>
            <p className="muted-text">
              راجع كل مشهد قبل الفيديو النهائي. هذا تصنيف مرجعي فقط — لا يحذف أي صوت أو صورة، ولا
              يمنع التصدير، لكن يساعدك على تتبع ما تمت مراجعته.
            </p>
            {scenes.length > 0 && approvedCount < scenes.length && (
              <p className="notice-banner">
                {approvedCount} من {scenes.length} مشهد معتمد فقط — راجع الباقي قبل اعتبار المشروع نهائياً.
              </p>
            )}
            {scenes.length > 0 && (
              <div className="tone-selector" aria-label="تصفية المشاهد بحالة المراجعة">
                {(["all", "pending", "needs_retry", "rejected", "approved"] as const).map((key) => (
                  <button
                    key={key}
                    className={reviewFilter === key ? "tone active" : "tone"}
                    onClick={() => setReviewFilter(key)}
                  >
                    {key === "all" ? "الكل" : REVIEW_STATUS_LABELS[key]}
                  </button>
                ))}
              </div>
            )}
            {!scenes.length ? (
              <p className="muted-text">لا توجد مشاهد بعد.</p>
            ) : (
              <div className="scene-list">
                {scenes
                  .filter((scene) => reviewFilter === "all" || (scene.review_status || "pending") === reviewFilter)
                  .map((scene) => {
                  const audioInfo = projectAudio?.scenes.find((s) => s.scene_id === scene.scene_id);
                  const imageInfo = projectImages?.scenes.find((s) => s.scene_id === scene.scene_id);
                  const status = scene.review_status || "pending";
                  const warnings = getSceneWarnings(scene);
                  return (
                    <div key={scene.scene_id} className="scene-card">
                      <div className="scene-card-header">
                        <strong>{scene.scene_id}. {scene.title_ar || "(بدون عنوان)"}</strong>
                        <span className={`tts-status-chip tts-status--${status === "approved" ? "ready" : status === "rejected" ? "error" : "warning"}`}>
                          {REVIEW_STATUS_LABELS[status]}
                        </span>
                      </div>
                      <p className="muted-text">{scene.narration_ar || "(بدون نص راوٍ)"}</p>
                      {warnings.length > 0 && <p className="error-banner">{warnings.join(" · ")}</p>}
                      <div className="action-bar">
                        {audioInfo?.has_audio && audioInfo.url && (
                          <audio controls src={`${API_BASE_URL}${audioInfo.url}`} style={{ height: "32px" }} />
                        )}
                        {imageInfo?.has_image && imageInfo.url && (
                          <img
                            src={`${API_BASE_URL}${imageInfo.url}`}
                            alt={`صورة المشهد ${scene.scene_id}`}
                            style={{ height: "64px", borderRadius: "6px" }}
                          />
                        )}
                      </div>
                      <div className="action-bar">
                        <button
                          className={status === "approved" ? "tone active" : "tone"}
                          onClick={() => handleSetSceneReview(scene.scene_id, "approved")}
                        >
                          اعتماد
                        </button>
                        <button
                          className={status === "needs_retry" ? "tone active" : "tone"}
                          onClick={() => handleSetSceneReview(scene.scene_id, "needs_retry")}
                        >
                          يحتاج إعادة
                        </button>
                        <button
                          className={status === "rejected" ? "tone active" : "tone"}
                          onClick={() => handleSetSceneReview(scene.scene_id, "rejected")}
                        >
                          رفض
                        </button>
                      </div>
                      <label>
                        ملاحظات المراجعة
                        <textarea
                          rows={2}
                          value={scene.review_notes || ""}
                          onChange={(e) => updateSceneReviewNotes(scene.scene_id, e.target.value)}
                          onBlur={() => handleSaveSceneReviewNotes(scene.scene_id)}
                          placeholder="مثال: الصورة جيدة لكن الصوت يحتاج إعادة توليد"
                        />
                      </label>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
          )}

          {activeStep === "image_studio" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Simple Image Studio</span>
                <h2>
                  استوديو الصور المستقل <span className="badge-experimental">تجريبي</span>
                </h2>
              </div>
            </div>
            <p className="muted-text">
              صورة واحدة من وصف واحد، منفصلة تماماً عن صور القصة ومشاهدها — لا تُحفظ مع المشروع
              الحالي ولا تستخدم بيانات الاستمرارية (الشخصيات/المكان). اكتب وصفاً واضغط توليد.
            </p>

            <label>
              اكتب وصف الصورة
              <textarea
                rows={3}
                value={standaloneImage.prompt}
                onChange={(e) => setStandaloneImage((prev) => ({ ...prev, prompt: e.target.value }))}
                placeholder="مثال: منظر طبيعي لجبال خضراء عند الغروب، أسلوب سينمائي واقعي"
              />
            </label>
            <label>
              النمط البصري
              <select
                value={standaloneImage.stylePreset}
                onChange={(e) => setStandaloneImage((prev) => ({ ...prev, stylePreset: e.target.value }))}
              >
                {(stylePresets.length ? stylePresets : [{ key: "cinematic_realistic", prompt_prefix: "" }]).map((p) => (
                  <option key={p.key} value={p.key}>
                    {presetLabel(p.key)}
                  </option>
                ))}
              </select>
            </label>

            <details className="advanced-continuity">
              <summary>خيارات متقدمة</summary>
              <label>
                Negative Prompt (اختياري)
                <textarea
                  rows={2}
                  value={standaloneImage.negativePrompt}
                  onChange={(e) => setStandaloneImage((prev) => ({ ...prev, negativePrompt: e.target.value }))}
                  placeholder="افتراضي: blurry, low quality, distorted, watermark, text"
                />
              </label>
              <label>
                Seed (اختياري)
                <input
                  value={standaloneImage.seed}
                  onChange={(e) => setStandaloneImage((prev) => ({ ...prev, seed: e.target.value }))}
                  placeholder="اتركه فارغاً لاختيار تلقائي"
                />
              </label>
              <label>
                الحجم
                <select
                  value={`${standaloneImage.width}x${standaloneImage.height}`}
                  onChange={(e) => {
                    const [w, h] = e.target.value.split("x").map(Number);
                    setStandaloneImage((prev) => ({ ...prev, width: w, height: h }));
                  }}
                >
                  <option value="512x512">512×512 (أسرع)</option>
                  <option value="768x768">768×768 (افتراضي)</option>
                </select>
              </label>
            </details>

            <BusyNotice busy={standaloneImageBusy} message={standaloneImageMessage} />

            <div className="action-bar">
              <button onClick={handleGenerateStandaloneImage} disabled={standaloneImageBusy || !imageHealth?.configured}>
                {standaloneImageBusy ? "جاري التوليد..." : "توليد الصورة"}
              </button>
            </div>

            {standaloneImageJob?.status === "done" && standaloneImageJob.job_id && (
              <div className="tts-job-card">
                <img
                  src={`${API_BASE_URL}/api/images/jobs/${standaloneImageJob.job_id}/download`}
                  alt="الصورة المولّدة"
                  className="scene-image-preview"
                />
                <a
                  className="ghost-button"
                  href={`${API_BASE_URL}/api/images/jobs/${standaloneImageJob.job_id}/download`}
                  download
                >
                  تحميل الصورة
                </a>
              </div>
            )}
          </section>
          )}

          {activeStep === "assistant" && (
          <section className="audio-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Local Assistant Lab</span>
                <h2>
                  المساعد المحلي <span className="badge-experimental">تجريبي</span>
                </h2>
              </div>
            </div>
            <p className="muted-text">
              سؤال واحد عن المشروع الحالي فقط، يُرسل إلى نفس محرك Ollama المستخدم في "تحسين القصة" —
              بدون بحث إنترنت حقيقي، بدون قاعدة معرفة (RAG) كاملة، وبدون أي ذاكرة محادثة بين الأسئلة.
              هذه نسخة مبسّطة آمنة فقط؛ المساعد الكامل (Open WebUI + RAG) يبقى خطة مستقبلية موثّقة في
              docs/LOCAL_AI_ASSISTANT_LAB_PLAN.md.
            </p>
            <p className="muted-text field-hint">
              قد تكون الإجابة غير دقيقة أو غير مكتملة — راجعها دائماً قبل الاعتماد عليها، ولا تعتبرها
              مصدراً موثقاً بالاستشهادات.
            </p>
            <label>
              سؤالك عن هذا المشروع
              <textarea
                rows={2}
                value={assistantQuestion}
                onChange={(e) => setAssistantQuestion(e.target.value)}
                placeholder="مثال: كم عدد المشاهد في هذه القصة؟ أو: ما موضوع القصة باختصار؟"
              />
            </label>
            <div className="action-bar">
              <button
                onClick={handleAskAssistant}
                disabled={!projectId || assistantBusy}
                title={!projectId ? "احفظ المشروع أولاً" : undefined}
              >
                {assistantBusy ? "جاري التفكير..." : "اسأل"}
              </button>
            </div>
            {assistantMessage && <p className="muted-text">{assistantMessage}</p>}
            {assistantAnswer && (
              <div className="tts-job-card">
                <strong>الإجابة:</strong>
                <p>{assistantAnswer}</p>
              </div>
            )}
          </section>
          )}

          {activeStep === "export" && (
          <section className="audio-panel export-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Export</span>
                <h2>التصدير</h2>
              </div>
            </div>
            <p className="muted-text">
              حمّل المشروع كاملاً كحزمة ZIP تحتوي القصة، المشاهد، الصوت، الصور، الفيديو والترجمات المتاحة.
            </p>
            {scenes.length > 0 && rejectedOrRetryCount > 0 && (
              <p className="error-banner">
                تنبيه: {rejectedOrRetryCount} من {scenes.length} مشهد "مرفوض" أو "يحتاج إعادة" في
                "مراجعة الجودة" — التصدير يعمل رغم ذلك، لكن راجع هذه المشاهد أولاً قبل المشاركة.
              </p>
            )}
            {scenes.length > 0 && rejectedOrRetryCount === 0 && approvedCount < scenes.length && (
              <p className="notice-banner">
                تنبيه: {scenes.length - approvedCount} من {scenes.length} مشهد غير معتمد بعد في "مراجعة
                الجودة" — التصدير يعمل رغم ذلك، هذا فقط تذكير.
              </p>
            )}
            <div className="export-grid">
              <button
                className="download-button"
                onClick={handleDownloadPackage}
                disabled={!projectId || loading !== null}
                title={!projectId ? "احفظ المشروع أولاً قبل تحميل ZIP" : undefined}
              >
                {loading === "package" ? "جاري التجهيز..." : "تحميل ZIP كامل"}
              </button>
              {scenes.length > 0 ? (
                <button className="ghost-button" onClick={handleDownloadJson}>
                  تحميل scenes.json
                </button>
              ) : (
                <span className="asset-missing">لا توجد مشاهد لتصديرها بعد</span>
              )}
              {audioCount > 0 ? (
                <span className="asset-ready">صوت {audioCount} من {scenes.length} مشهد محفوظ</span>
              ) : (
                <span className="asset-missing">لم يتم توليد صوت المشاهد بعد</span>
              )}
              {projectAudio?.final_story.has_audio && projectAudio.final_story.url ? (
                <a className="ghost-button" href={`${API_BASE_URL}${projectAudio.final_story.url}`} download>
                  تحميل صوت القصة كاملة
                </a>
              ) : (
                <span className="asset-missing">صوت القصة الكاملة يحتاج صوتاً لمشهدين على الأقل</span>
              )}
              {imageCount > 0 ? (
                <span className="asset-ready">صور {imageCount} من {scenes.length} مشهد محفوظة (داخل ZIP)</span>
              ) : (
                <span className="asset-missing">لم يتم توليد الصور بعد</span>
              )}
              {projectVideo?.has_video && projectVideo.url ? (
                <a className="ghost-button" href={`${API_BASE_URL}${projectVideo.url}`} download>
                  تحميل الفيديو MP4
                </a>
              ) : (
                <span className="asset-missing">لم يتم تجميع الفيديو بعد</span>
              )}
              {projectId && scenes.length > 0 ? (
                <>
                  <a className="ghost-button" href={`${API_BASE_URL}/api/projects/${projectId}/subtitles.srt`} download>
                    تحميل SRT
                  </a>
                  <a className="ghost-button" href={`${API_BASE_URL}/api/projects/${projectId}/subtitles.vtt`} download>
                    تحميل VTT
                  </a>
                </>
              ) : (
                <span className="asset-missing">لا توجد مشاهد لتوليد الترجمة بعد</span>
              )}
            </div>
          </section>
          )}
        </div>
        )}
      </section>
    </main>
  );
}

