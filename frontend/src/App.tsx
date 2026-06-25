import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8810";

const TONES = ["عسكري هادئ", "وثائقي مؤثر", "قصصي دافئ", "تشويقي"];

const SAMPLE_STORY = `في ليلة هادئة، جلس الراوي أمام نافذة قديمة يتأمل المدينة التي تغيّرت كثيراً. كانت الذكريات تعود إليه مثل موج البحر، تحمل وجوهاً وأصواتاً ومواقف لم تغب عن قلبه. وفي تلك اللحظة، أدرك أن الحكاية لم تكن عن الماضي وحده، بل عن الشجاعة التي يحتاجها الإنسان كي يبدأ من جديد.`;

type Scene = {
  scene_id: string;
  title_ar: string;
  narration_ar: string;
  visual_description_ar: string;
  image_prompt_en: string;
  duration_seconds: number;
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
};

type SplitData = {
  project_id: string | null;
  story_title: string;
  scenes: Scene[];
};

type Project = {
  project_id: string;
  title: string;
  original_story: string;
  improved_story: string;
  scenes: Scene[];
  created_at: string;
  updated_at: string;
};

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

type TtsJobFile = {
  url?: string;
  format?: string;
};

type TtsJobData = {
  job_id?: string;
  status?: string;
  files?: TtsJobFile[];
  [key: string]: unknown;
};

type TtsVoice = {
  voice_id: string;
  label: string;
  language: string;
  engine: string;
  default: boolean;
};

type TtsLanguage = {
  language: string;
  label: string;
  default: boolean;
};

type TtsVoicesData = {
  voices: TtsVoice[];
  languages: TtsLanguage[];
};

type SceneAudioInfo = {
  scene_id: string;
  has_audio: boolean;
  audio_format: string | null;
  audio_bytes: number | null;
  audio_generated_at: string | null;
  url: string | null;
};

type ProjectAudioData = {
  project_id: string;
  scenes: SceneAudioInfo[];
  final_story: { has_audio: boolean; url: string | null };
};

const FALLBACK_TTS_VOICES: TtsVoicesData = {
  voices: [
    { voice_id: "ar_JO-kareem-medium", label: "Arabic Kareem", language: "ar", engine: "piper", default: true },
  ],
  languages: [{ language: "ar", label: "العربية", default: true }],
};

type TtsBusyAction = "health" | "scene" | "project" | "refresh" | null;

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

// ── Helpers ───────────────────────────────────────────────────────────────────

function getSceneWarnings(scene: Scene): string[] {
  const w: string[] = [];
  if (!scene.title_ar.trim()) w.push("العنوان فارغ");
  if (!scene.narration_ar.trim()) w.push("نص الراوي فارغ");
  if (!scene.duration_seconds || scene.duration_seconds <= 0) w.push("المدة غير صالحة");
  return w;
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

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [title, setTitle] = useState("المسرح لي");
  const [storyText, setStoryText] = useState("");
  const [tone, setTone] = useState(TONES[0]);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [providerMessage, setProviderMessage] = useState("لم يتم الاختبار بعد");
  const [improvedText, setImprovedText] = useState("");
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(new Set([0]));
  const [rawJsonOpen, setRawJsonOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<LoadingAction>(null);

  const [ttsHealth, setTtsHealth] = useState<TtsHealthData | null>(null);
  const [ttsMessage, setTtsMessage] = useState("");
  const [ttsJob, setTtsJob] = useState<TtsJobData | null>(null);
  const [ttsBusy, setTtsBusy] = useState<TtsBusyAction>(null);
  const [ttsVoices, setTtsVoices] = useState<TtsVoicesData>(FALLBACK_TTS_VOICES);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(
    FALLBACK_TTS_VOICES.voices[0].voice_id,
  );
  const [projectAudio, setProjectAudio] = useState<ProjectAudioData | null>(null);

  const canRun = storyText.trim().length > 0 && loading === null;

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
  }, []);

  async function fetchTtsVoices() {
    try {
      const r = await getJson<TtsVoicesData>("/api/tts/voices");
      if (r.data.voices.length) {
        setTtsVoices(r.data);
        setSelectedVoiceId(r.data.voices.find((v) => v.default)?.voice_id ?? r.data.voices[0].voice_id);
      }
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
    setProjectId(project.project_id);
    setTitle(project.title);
    setStoryText(project.original_story || "");
    setImprovedText(project.improved_story || "");
    setScenes(project.scenes || []);
    setExpandedIndices(new Set([0]));
    setRawJsonOpen(Boolean(project.scenes?.length));
    setProjectAudio(null);
    setTtsJob(null);
    void refreshProjectAudio(project.project_id);
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
    const payload = { title, original_story: storyText, improved_story: improvedText, scenes };
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
      setProjectId(null);
      setTitle("قصة جديدة");
      setStoryText("");
      setImprovedText("");
      setScenes([]);
      setExpandedIndices(new Set());
      setRawJsonOpen(false);
      setProjectAudio(null);
      setTtsJob(null);
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

  async function handleImproveStory() {
    setLoading("improve");
    setError("");
    try {
      const r = await postJson<{ improved_text: string }>("/api/story/improve", {
        story_text: storyText,
        tone,
        language: "ar",
      });
      if (r.errors.length) {
        setError(r.errors.join(" "));
      } else {
        setImprovedText(r.data.improved_text);
        showNotice("تم تحسين القصة. لا تنس حفظ المشروع.");
      }
    } catch {
      setError("تعذر تحسين القصة. تحقق من backend وOllama.");
    } finally {
      setLoading(null);
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
        setRawJsonOpen(true);
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
    setTtsBusy(mode);
    setTtsMessage("جاري توليد صوت المشهد...");
    setTtsJob(null);
    try {
      const body = { mode, scene_id: scenes[0].scene_id, format: "wav", voice_id: selectedVoiceId };
      const r = await postJson<TtsJobData>(`/api/projects/${projectId}/tts/jobs`, body);
      setTtsJob(r.data);
      if (r.errors.length) setTtsMessage(r.errors.join(" "));
      else setTtsMessage("تم توليد صوت المشهد.");
    } catch (exc) {
      setTtsMessage(exc instanceof Error ? exc.message : "تعذر إرسال طلب توليد الصوت.");
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
    setTtsBusy("project");
    setTtsMessage("جاري توليد صوت المشروع، قد يستغرق دقائق...");
    setTtsJob(null);
    try {
      const r = await postJson<{ generated: string[]; failed: { scene_id: string; error: string }[]; total_scenes: number }>(
        `/api/projects/${projectId}/tts/generate-all`,
      );
      if (r.errors.length) {
        setTtsMessage(r.errors.join(" "));
      } else {
        const { generated, failed, total_scenes } = r.data;
        let msg = `تم توليد صوت المشروع (${generated.length} من ${total_scenes} مشهد). استمع للمشاهد أدناه.`;
        if (failed.length) msg += ` فشل: ${failed.map((f) => f.scene_id).join(", ")}.`;
        setTtsMessage(msg);
        await refreshProjectAudio(projectId);
      }
    } catch (exc) {
      setTtsMessage(exc instanceof Error ? exc.message : "تعذر توليد صوت المشروع.");
    } finally {
      setTtsBusy(null);
    }
  }

  async function handleRefreshTtsJob() {
    if (!ttsJob?.job_id) return;
    setTtsBusy("refresh");
    setTtsMessage("");
    try {
      const r = await getJson<TtsJobData>(`/api/tts/jobs/${ttsJob.job_id}`);
      setTtsJob(r.data);
      if (r.errors.length) setTtsMessage(r.errors.join(" "));
    } catch (exc) {
      setTtsMessage(exc instanceof Error ? exc.message : "تعذر تحديث حالة المهمة.");
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

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <main className="app-shell" dir="rtl">
      {/* Hero */}
      <section className="hero-section">
        <div className="hero-copy">
          <span className="phase-pill">Phase 1.5 — استوديو الصوت</span>
          <h1>AI Story Studio</h1>
          <p>حوّل قصتك إلى مشروع محفوظ، سكريبت راوي، مشاهد قابلة للتعديل، وصوت حقيقي تستمع إليه مباشرة.</p>
        </div>
        <div className={`status-chip ${config?.ollama_configured ? "ready" : "warning"}`}>
          <span>{config?.provider || "ollama"}</span>
          <strong>{config?.model || "qwen2.5:7b"}</strong>
          <small>{providerMessage}</small>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}
      {notice && <div className="notice-banner">{notice}</div>}

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
        <div className="glass-panel editor-panel">
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
              >
                {item}
              </button>
            ))}
          </div>

          <div className="action-bar">
            <button onClick={handleTestOllama} disabled={loading !== null}>
              {loading === "test" ? "جاري الاختبار..." : "اختبار Ollama"}
            </button>
            <button onClick={handleImproveStory} disabled={!canRun}>
              {loading === "improve" ? "جاري التحسين..." : "تحسين القصة"}
            </button>
            <button onClick={handleSplitScenes} disabled={!canRun}>
              {loading === "split" ? "جاري التقسيم..." : "تقسيم إلى مشاهد"}
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
        </div>

        {/* Right: Scene editor */}
        <div className="glass-panel result-panel">
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
                          المدة بالثواني
                          <input
                            type="number"
                            min="1"
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
                {rawJsonOpen ? "إخفاء JSON" : "عرض JSON"}
              </button>
              {rawJsonOpen && <pre dir="ltr">{rawJson}</pre>}
            </section>
          )}

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

            <div className="tts-selectors">
              <label>
                الصوت
                <select
                  value={selectedVoiceId ?? ""}
                  onChange={(e) => setSelectedVoiceId(e.target.value)}
                  disabled={ttsVoices.voices.length <= 1}
                >
                  {ttsVoices.voices.map((v) => (
                    <option key={v.voice_id} value={v.voice_id}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                اللغة
                <select value={ttsVoices.languages[0]?.language ?? "ar"} disabled>
                  {ttsVoices.languages.map((l) => (
                    <option key={l.language} value={l.language}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="muted-text">
              الصوت الحالي الوحيد المتاح: {ttsVoices.voices[0]?.label ?? "—"}. اختيار اللغة غير
              متاح حالياً إلا للعربية.
            </p>

            {ttsMessage && <div className="notice-banner">{ttsMessage}</div>}

            <div className="action-bar">
              <button onClick={checkTtsHealth} disabled={ttsBusy !== null}>
                {ttsBusy === "health" ? "جاري الفحص..." : "فحص خدمة الصوت"}
              </button>
              <button
                onClick={() => handleGenerateAudio("scene")}
                disabled={!projectId || !scenes.length || !ttsHealth?.configured || ttsBusy !== null}
                title={!ttsHealth?.configured ? "خدمة الصوت غير مفعّلة" : undefined}
              >
                {ttsBusy === "scene" ? "جاري توليد صوت المشهد..." : "توليد صوت للمشهد الأول"}
              </button>
              <button
                onClick={handleGenerateAllAudio}
                disabled={!projectId || !scenes.length || !ttsHealth?.configured || ttsBusy !== null}
                title={!ttsHealth?.configured ? "خدمة الصوت غير مفعّلة" : undefined}
              >
                {ttsBusy === "project" ? "جاري توليد صوت المشروع..." : "توليد صوت للمشروع"}
              </button>
            </div>

            {ttsJob && (
              <div className="tts-job-card">
                {ttsJob.job_id && (
                  <span>
                    Job ID: <code dir="ltr">{ttsJob.job_id}</code>
                  </span>
                )}
                {ttsJob.status && <span>الحالة: {ttsStatusText(ttsJob.status)}</span>}
                {ttsJob.job_id && (
                  <button className="ghost-button" onClick={handleRefreshTtsJob} disabled={ttsBusy !== null}>
                    {ttsBusy === "refresh" ? "جاري التحديث..." : "تحديث الحالة"}
                  </button>
                )}
                {ttsJob.status === "done" &&
                  ttsJob.job_id &&
                  ttsJob.files?.map((file, idx) => {
                    const fileUrl = `${API_BASE_URL}/api/tts/jobs/${ttsJob.job_id}/download/${file.format}`;
                    return (
                      <span key={idx} className="tts-audio-result">
                        <p className="muted-text">استمع إلى صوت المشهد</p>
                        <audio controls src={fileUrl} className="tts-audio-player" />
                        <a className="ghost-button" href={fileUrl} download>
                          تحميل صوت المشهد ({file.format})
                        </a>
                      </span>
                    );
                  })}
              </div>
            )}

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
        </div>
      </section>
    </main>
  );
}
