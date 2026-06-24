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

type LoadingAction = "test" | "improve" | "split" | "new" | "save" | "load" | "delete" | null;

async function requestJson<T>(path: string, options?: RequestInit): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload?.detail || payload?.errors?.join?.(" ") || "Request failed.";
    throw new Error(detail);
  }
  return payload;
}

function getJson<T>(path: string): Promise<ApiEnvelope<T>> {
  return requestJson<T>(path);
}

function postJson<T>(path: string, payload?: unknown): Promise<ApiEnvelope<T>> {
  return requestJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : "{}",
  });
}

function putJson<T>(path: string, payload: unknown): Promise<ApiEnvelope<T>> {
  return requestJson<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function deleteJson<T>(path: string): Promise<ApiEnvelope<T>> {
  return requestJson<T>(path, { method: "DELETE" });
}

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
  const [rawJsonOpen, setRawJsonOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<LoadingAction>(null);

  const canRun = storyText.trim().length > 0 && loading === null;
  const splitData = useMemo<SplitData | null>(() => {
    if (!scenes.length) return null;
    return { project_id: projectId, story_title: title, scenes };
  }, [projectId, scenes, title]);
  const rawJson = useMemo(() => (splitData ? JSON.stringify(splitData, null, 2) : ""), [splitData]);

  useEffect(() => {
    getJson<ConfigData>("/api/config")
      .then((result) => {
        setConfig(result.data);
        if (result.errors.length) setError(result.errors.join(" "));
      })
      .catch(() => setError("تعذر تحميل إعدادات المزود من backend."));
    refreshProjects();
  }, []);

  async function refreshProjects() {
    try {
      const result = await getJson<ProjectListData>("/api/projects");
      setProjects(result.data.projects || []);
    } catch {
      setError("تعذر تحميل قائمة المشاريع.");
    }
  }

  function showNotice(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 3500);
  }

  function applyProject(project: Project) {
    setProjectId(project.project_id);
    setTitle(project.title);
    setStoryText(project.original_story || "");
    setImprovedText(project.improved_story || "");
    setScenes(project.scenes || []);
    setRawJsonOpen(Boolean(project.scenes?.length));
  }

  async function handleNewProject() {
    setLoading("new");
    setError("");
    try {
      const result = await postJson<Project>("/api/projects", {
        title: "قصة جديدة",
        original_story: "",
        improved_story: "",
        scenes: [],
      });
      applyProject(result.data);
      await refreshProjects();
      showNotice("تم إنشاء مشروع جديد.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر إنشاء مشروع جديد.");
    } finally {
      setLoading(null);
    }
  }

  async function handleLoadProject(selectedProjectId: string) {
    setLoading("load");
    setError("");
    try {
      const result = await getJson<Project>(`/api/projects/${selectedProjectId}`);
      applyProject(result.data);
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
      const result = projectId
        ? await putJson<Project>(`/api/projects/${projectId}`, payload)
        : await postJson<Project>("/api/projects", payload);
      applyProject(result.data);
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
      setRawJsonOpen(false);
      await refreshProjects();
      showNotice("تم حذف المشروع.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "تعذر حذف المشروع.");
    } finally {
      setLoading(null);
    }
  }

  async function handleTestOllama() {
    setLoading("test");
    setError("");
    try {
      const result = await postJson<{ connected: boolean; latency_ms: number | null; model: string }>(
        "/api/ollama/test",
      );
      if (result.errors.length) {
        setProviderMessage("الاتصال غير جاهز");
        setError(result.errors.join(" "));
      } else {
        setProviderMessage(`متصل عبر ${result.data.model} خلال ${result.data.latency_ms}ms`);
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
      const result = await postJson<{ improved_text: string }>("/api/story/improve", {
        story_text: storyText,
        tone,
        language: "ar",
      });
      if (result.errors.length) {
        setError(result.errors.join(" "));
      } else {
        setImprovedText(result.data.improved_text);
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
      const result = await postJson<SplitData>("/api/story/split-scenes", {
        title,
        story_text: improvedText || storyText,
        target_scenes: 6,
        tone,
      });
      if (result.errors.length) {
        setError(result.errors.join(" "));
        setScenes([]);
      } else {
        setScenes(result.data.scenes);
        setRawJsonOpen(true);
        if (result.data.project_id) {
          await saveGeneratedProject(result.data.project_id, result.data.scenes);
        }
        showNotice("تم تقسيم القصة إلى مشاهد وحفظ المشروع.");
      }
    } catch {
      setError("تعذر تقسيم القصة إلى مشاهد. تحقق من استجابة Ollama.");
    } finally {
      setLoading(null);
    }
  }

  async function saveGeneratedProject(generatedProjectId: string, generatedScenes: Scene[]) {
    const result = await putJson<Project>(`/api/projects/${generatedProjectId}`, {
      title,
      original_story: storyText,
      improved_story: improvedText,
      scenes: generatedScenes,
    });
    applyProject(result.data);
    await refreshProjects();
  }

  function updateScene(index: number, field: keyof Scene, value: string | number) {
    setScenes((currentScenes) =>
      currentScenes.map((scene, sceneIndex) =>
        sceneIndex === index ? { ...scene, [field]: value } : scene,
      ),
    );
  }

  async function handleDownloadJson() {
    if (projectId) {
      const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/scenes.json`);
      downloadBlob(await response.blob(), "scenes.json");
      return;
    }
    if (splitData) {
      downloadBlob(
        new Blob([JSON.stringify(splitData, null, 2)], { type: "application/json;charset=utf-8" }),
        "scenes.json",
      );
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

  return (
    <main className="app-shell" dir="rtl">
      <section className="hero-section">
        <div className="hero-copy">
          <span className="phase-pill">Phase 0.2</span>
          <h1>AI Story Studio</h1>
          <p>حوّل قصتك إلى مشروع محفوظ، سكريبت راوي، ومشاهد قابلة للتعديل والتصدير.</p>
        </div>
        <div className={`status-chip ${config?.ollama_configured ? "ready" : "warning"}`}>
          <span>{config?.provider || "ollama"}</span>
          <strong>{config?.model || "qwen2.5:7b"}</strong>
          <small>{providerMessage}</small>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}
      {notice && <div className="notice-banner">{notice}</div>}

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
            <button className="danger-button" onClick={handleDeleteProject} disabled={!projectId || loading !== null}>
              حذف المشروع
            </button>
          </div>
        </div>
        <div className="project-list">
          {projects.length === 0 && <span className="muted-text">لا توجد مشاريع محفوظة بعد.</span>}
          {projects.map((project) => (
            <button
              key={project.project_id}
              className={project.project_id === projectId ? "project-item active" : "project-item"}
              onClick={() => handleLoadProject(project.project_id)}
              disabled={loading !== null}
            >
              <strong>{project.title}</strong>
              <small>
                {project.scene_count} مشاهد · {new Date(project.updated_at).toLocaleString("ar")}
              </small>
            </button>
          ))}
        </div>
      </section>

      <section className="workspace-grid">
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
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>

          <label className="story-label">
            نص القصة الأصلي
            <textarea
              value={storyText}
              onChange={(event) => setStoryText(event.target.value)}
              placeholder="اكتب القصة العربية هنا..."
            />
          </label>

          <label className="story-label">
            سكريبت الراوي المحسن
            <textarea
              className="compact-textarea"
              value={improvedText}
              onChange={(event) => setImprovedText(event.target.value)}
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
            <button className="download-button" onClick={handleDownloadJson} disabled={!scenes.length}>
              تحميل scenes.json
            </button>
          </div>
        </div>

        <div className="glass-panel result-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">Editable Scenes</span>
              <h2>المشاهد</h2>
            </div>
            <span className="project-id-chip">{projectId ? `ID: ${projectId.slice(0, 8)}` : "غير محفوظ"}</span>
          </div>

          {!scenes.length && (
            <div className="empty-state">
              ابدأ بتحسين القصة أو تقسيمها. بعد توليد المشاهد ستستطيع تعديلها وحفظها وإعادة تصدير scenes.json.
            </div>
          )}

          {scenes.length > 0 && (
            <section className="scene-list">
              <div className="scene-list-title">
                <h3>{title}</h3>
                <span>{scenes.length} مشاهد</span>
              </div>
              {scenes.map((scene, index) => (
                <article className="scene-card editable-scene" key={`${scene.scene_id}-${index}`}>
                  <div className="scene-number">{scene.scene_id}</div>
                  <div className="scene-fields">
                    <label>
                      عنوان المشهد
                      <input
                        value={scene.title_ar}
                        onChange={(event) => updateScene(index, "title_ar", event.target.value)}
                      />
                    </label>
                    <label>
                      نص الراوي
                      <textarea
                        className="scene-textarea"
                        value={scene.narration_ar}
                        onChange={(event) => updateScene(index, "narration_ar", event.target.value)}
                      />
                    </label>
                    <label>
                      الوصف البصري
                      <textarea
                        className="scene-textarea"
                        value={scene.visual_description_ar}
                        onChange={(event) => updateScene(index, "visual_description_ar", event.target.value)}
                      />
                    </label>
                    <label>
                      Visual prompt
                      <textarea
                        className="scene-textarea ltr-field"
                        dir="ltr"
                        value={scene.image_prompt_en}
                        onChange={(event) => updateScene(index, "image_prompt_en", event.target.value)}
                      />
                    </label>
                    <label>
                      المدة بالثواني
                      <input
                        type="number"
                        min="3"
                        max="180"
                        value={scene.duration_seconds}
                        onChange={(event) => updateScene(index, "duration_seconds", Number(event.target.value))}
                      />
                    </label>
                  </div>
                </article>
              ))}
            </section>
          )}

          {rawJson && (
            <section className="json-preview">
              <button className="ghost-button" onClick={() => setRawJsonOpen((value) => !value)}>
                {rawJsonOpen ? "إخفاء JSON" : "عرض JSON"}
              </button>
              {rawJsonOpen && <pre dir="ltr">{rawJson}</pre>}
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
