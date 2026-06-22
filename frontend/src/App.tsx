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

type LoadingAction = "test" | "improve" | "split" | null;

async function postJson<T>(path: string, payload?: unknown): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : "{}",
  });
  return response.json();
}

async function getJson<T>(path: string): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  return response.json();
}

export default function App() {
  const [title, setTitle] = useState("المسرح لي");
  const [storyText, setStoryText] = useState("");
  const [tone, setTone] = useState(TONES[0]);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [providerMessage, setProviderMessage] = useState("لم يتم الاختبار بعد");
  const [improvedText, setImprovedText] = useState("");
  const [splitData, setSplitData] = useState<SplitData | null>(null);
  const [rawJsonOpen, setRawJsonOpen] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<LoadingAction>(null);

  const canRun = storyText.trim().length > 0 && loading === null;
  const rawJson = useMemo(() => {
    if (!splitData) return "";
    return JSON.stringify(splitData, null, 2);
  }, [splitData]);

  useEffect(() => {
    getJson<ConfigData>("/api/config")
      .then((result) => {
        setConfig(result.data);
        if (result.errors.length) setError(result.errors.join(" "));
      })
      .catch(() => setError("تعذر تحميل إعدادات المزود من backend."));
  }, []);

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
        setSplitData(null);
      } else {
        setSplitData(result.data);
        setRawJsonOpen(true);
      }
    } catch {
      setError("تعذر تقسيم القصة إلى مشاهد. تحقق من استجابة Ollama.");
    } finally {
      setLoading(null);
    }
  }

  async function handleDownloadJson() {
    if (!splitData?.project_id) return;
    const response = await fetch(`${API_BASE_URL}/api/projects/${splitData.project_id}/scenes.json`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "scenes.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell" dir="rtl">
      <section className="hero-section">
        <div className="hero-copy">
          <span className="phase-pill">Phase 0.1</span>
          <h1>AI Story Studio</h1>
          <p>حوّل قصتك إلى سكريبت راوي ومشاهد منظمة.</p>
        </div>
        <div className={`status-chip ${config?.ollama_configured ? "ready" : "warning"}`}>
          <span>{config?.provider || "ollama"}</span>
          <strong>{config?.model || "qwen2.5:7b"}</strong>
          <small>{providerMessage}</small>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

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
            عنوان القصة
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>

          <label className="story-label">
            نص القصة
            <textarea
              value={storyText}
              onChange={(event) => setStoryText(event.target.value)}
              placeholder="اكتب القصة العربية هنا..."
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
              {loading === "test" ? "جار الاختبار..." : "اختبار Ollama"}
            </button>
            <button onClick={handleImproveStory} disabled={!canRun}>
              {loading === "improve" ? "جار التحسين..." : "تحسين القصة"}
            </button>
            <button onClick={handleSplitScenes} disabled={!canRun}>
              {loading === "split" ? "جار التقسيم..." : "تقسيم إلى مشاهد"}
            </button>
            <button className="download-button" onClick={handleDownloadJson} disabled={!splitData?.project_id}>
              تحميل scenes.json
            </button>
          </div>
        </div>

        <div className="glass-panel result-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">Output</span>
              <h2>المخرجات</h2>
            </div>
          </div>

          {!improvedText && !splitData && (
            <div className="empty-state">
              ابدأ باختبار Ollama، ثم حسّن القصة أو قسّمها إلى مشاهد قابلة للمراجعة.
            </div>
          )}

          {improvedText && (
            <section className="output-card">
              <h3>سكريبت الراوي المحسن</h3>
              <p>{improvedText}</p>
            </section>
          )}

          {splitData && (
            <section className="scene-list">
              <div className="scene-list-title">
                <h3>{splitData.story_title}</h3>
                <span>{splitData.scenes.length} مشاهد</span>
              </div>
              {splitData.scenes.map((scene) => (
                <article className="scene-card" key={scene.scene_id}>
                  <div className="scene-number">{scene.scene_id}</div>
                  <div>
                    <h4>{scene.title_ar}</h4>
                    <p>{scene.narration_ar}</p>
                    <small>{scene.visual_description_ar}</small>
                    <code>{scene.image_prompt_en}</code>
                    <span className="duration">{scene.duration_seconds} ثانية</span>
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
