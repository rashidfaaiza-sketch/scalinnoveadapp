import React, { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  AudioLines,
  Bell,
  Check,
  ChevronDown,
  CircleHelp,
  Clapperboard,
  Download,
  FileText,
  FolderOpen,
  Grid2X2,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  MoreHorizontal,
  Play,
  Plus,
  Search,
  Settings,
  Sparkles,
  Video,
  WandSparkles,
  X,
} from "lucide-react";

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {}
    const error = new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status}). Check your inputs and try again.`,
    );
    error.status = response.status;
    throw error;
  }
  return response.json();
}
const post = (data) => ({ method: "POST", body: JSON.stringify(data) });
const pictures = {
  ava: "/characters/ava.svg",
  noah: "/characters/noah.svg",
  mia: "/characters/mia.svg",
};
const navItems = [
  ["Overview", LayoutDashboard],
  ["Create video", WandSparkles],
  ["Projects", FolderOpen],
  ["Script library", FileText],
  ["Media library", Grid2X2],
];
const empty = {
  projects: [],
  scripts: [],
  videos: [],
  avatars: [],
  voices: [],
  demo_mode: false,
  generation_mode: "local",
};
function IconButton({ label, children, ...props }) {
  return (
    <button className="icon-button" aria-label={label} title={label} {...props}>
      {children}
    </button>
  );
}
function Portrait({ id, className = "" }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`portrait ${id} ${className}`}>
      {!failed && (
        <img
          src={pictures[id]}
          alt={`${id} illustrated character`}
          onError={() => setFailed(true)}
        />
      )}
      <span className="portrait-fallback" aria-hidden="true">
        {id?.slice(0, 1).toUpperCase()}
      </span>
    </div>
  );
}
function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef();
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement;
    ref.current?.focus();
    function key(e) {
      if (e.key === "Escape") closeRef.current();
      if (e.key === "Tab") {
        const elements = ref.current.querySelectorAll(
          "button,input,select,textarea,a[href]",
        );
        const first = elements[0],
          last = elements[elements.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={ref}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <IconButton label="Close dialog" onClick={onClose}>
            <X size={20} />
          </IconButton>
        </div>
        {children}
      </section>
    </div>
  );
}
export default function App() {
  const [page, setPage] = useState("Overview"),
    [data, setData] = useState(empty),
    [authorized, setAuthorized] = useState(null),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [busy, setBusy] = useState(false),
    [mobile, setMobile] = useState(false),
    [query, setQuery] = useState(""),
    [modal, setModal] = useState(null);
  const [projectId, setProjectId] = useState(""),
    [scriptId, setScriptId] = useState(""),
    [draft, setDraft] = useState({
      hook: "",
      body: "",
      cta: "",
      platform: "Short-form",
    });
  const [tone, setTone] = useState("Confident"),
    [avatar, setAvatar] = useState("ava"),
    [voice, setVoice] = useState("local-neutral"),
    [ratio, setRatio] = useState("9:16"),
    [expression, setExpression] = useState("natural"),
    [videoName, setVideoName] = useState("");
  const [providerSettings, setProviderSettings] = useState(null);
  const local = data.generation_mode === "local";
  useEffect(() => {
    if (data.voices.length && !data.voices.some((v) => v.id === voice))
      setVoice(data.voices[0].id);
  }, [data.voices, voice]);
  const [exportRatio, setExportRatio] = useState("original");
  useEffect(() => setExportRatio("original"), [modal?.video?.id]);
  const mounted = useRef(true);
  async function refresh() {
    try {
      const result = await api("/workspace");
      if (mounted.current) {
        setData(result);
        setAuthorized(true);
      }
      return result;
    } catch (e) {
      if (mounted.current) {
        if (e.status === 401) setAuthorized(false);
        else setError(e.message);
      }
    }
  }
  useEffect(() => {
    mounted.current = true;
    refresh();
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!authorized) return;
    let active = true;
    let timer;
    const tick = async () => {
      try {
        const result = await api("/workspace");
        if (active) setData(result);
      } catch (e) {
        if (active) {
          if (e.status === 401) setAuthorized(false);
          else setError(e.message);
        }
      }
      if (active) timer = setTimeout(tick, 4000);
    };
    timer = setTimeout(tick, 4000);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [authorized]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 5000);
    return () => clearTimeout(timer);
  }, [toast]);
  async function act(fn) {
    setBusy(true);
    setError("");
    try {
      return await fn();
    } catch (e) {
      if (e.status === 401) setAuthorized(false);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function navigate(next) {
    setPage(next);
    setMobile(false);
    setQuery("");
    setError("");
  }
  function selectScript(script) {
    setProjectId(script.project_id);
    setScriptId(script.id);
    setDraft({
      hook: script.hook,
      body: script.body,
      cta: script.cta,
      platform: script.platform,
    });
    navigate("Create video");
  }
  function newProject() {
    setModal({ type: "project" });
  }
  async function openSettings() {
    navigate("Settings");
    await act(async () => setProviderSettings(await api("/settings")));
  }
  const project = data.projects.find((p) => p.id === projectId),
    active = data.videos.filter((v) =>
      ["queued", "rendering"].includes(v.status),
    ),
    completed = data.videos.filter((v) => v.status === "completed");
  const filteredVideos = data.videos.filter((v) =>
    v.name.toLowerCase().includes(query.toLowerCase()),
  );
  const wordCount = [draft.hook, draft.body, draft.cta]
    .join(" ")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
  async function saveDraft() {
    if (!projectId) throw new Error("Create or choose a project first.");
    const saved = await api(
      scriptId ? `/scripts/${scriptId}` : `/projects/${projectId}/scripts`,
      { method: scriptId ? "PUT" : "POST", body: JSON.stringify(draft) },
    );
    setScriptId(saved.id);
    await refresh();
    return saved;
  }
  async function render() {
    const saved = await saveDraft();
    await api(
      "/videos",
      post({
        script_id: saved.id,
        avatar,
        voice,
        ratio,
        expression,
        name: videoName.trim() || `${project?.name || "Untitled"} · ${ratio}`,
      }),
    );
    setToast("Your video is in the queue. We’ll take it from here.");
    navigate("Media library");
    await refresh();
  }
  function VideoCard({ video }) {
    return (
      <article className="video-card">
        <button
          className={`video-thumb ${video.avatar}`}
          onClick={() =>
            video.status === "completed"
              ? setModal({ type: "video", video })
              : setModal({ type: "status", video })
          }
          aria-label={`Open ${video.name}`}
        >
          {video.status === "completed" ? (
            <video
              src={`/api/videos/${video.id}/file#t=0.1`}
              preload="metadata"
              muted
              playsInline
              aria-hidden="true"
            />
          ) : (
            <Portrait id={video.avatar} />
          )}
          <div className="thumb-shade" />
          <span className={`status-pill ${video.status}`}>
            {video.status === "completed" ? (
              <Check size={11} />
            ) : video.status === "failed" ? (
              <X size={11} />
            ) : (
              <LoaderCircle size={11} />
            )}{" "}
            {video.status}
          </span>
          <span className="ratio-tag">{video.ratio}</span>
          {video.status === "completed" ? (
            <span className="play-circle">
              <Play size={18} fill="currentColor" />
            </span>
          ) : (
            <span className="render-label">
              {video.status === "failed"
                ? "Let’s try that again"
                : `${video.progress}%`}{" "}
            </span>
          )}
          <span className="thumb-caption">
            {data.projects.find((p) => p.id === video.project_id)?.product ||
              "Your next big idea"}
            <small>
              {video.engine === "local"
                ? "MADE LOCALLY"
                : video.demo
                  ? "DEMO EXPORT"
                  : "MADE WITH FORMA"}
            </small>
          </span>
        </button>
        <div className="video-meta">
          <div>
            <h3>{video.name}</h3>
            <p>
              {new Date(video.created_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}{" "}
              <span>·</span>{" "}
              {video.engine === "local"
                ? "Narrated character ad"
                : video.demo
                  ? "Sample MP4"
                  : "Avatar video"}
            </p>
          </div>
          <IconButton
            label={`Rename ${video.name}`}
            onClick={() => setModal({ type: "rename", video })}
          >
            <MoreHorizontal size={20} />
          </IconButton>
        </div>
        {["queued", "rendering"].includes(video.status) && (
          <div className="progress-track">
            <i style={{ width: `${video.progress}%` }} />
          </div>
        )}
      </article>
    );
  }
  if (authorized === null)
    return (
      <div className="loading-screen">
        <span className="brand-mark">f</span>
        <LoaderCircle className="spin" />
        <p>{error || "Opening your creative workspace…"}</p>
        {error && (
          <button className="primary" onClick={refresh}>
            Try again
          </button>
        )}
      </div>
    );
  if (!authorized)
    return (
      <main className="login-layout">
        <div className="login-story">
          <div className="brand light">
            <span className="brand-mark">f</span>forma
            <span className="brand-dot">®</span>
          </div>
          <div>
            <span className="eyebrow">YOUR IDEAS. A NEW DIMENSION.</span>
            <h1>
              Small team.
              <br />
              Big creative
              <br />
              <em>energy.</em>
            </h1>
            <p>
              Turn a good idea into your next great ad.
              <br />
              Your local video studio is ready when you are.
            </p>
          </div>
          <span className="login-foot">THE CREATIVE ADVANTAGE, NOW YOURS.</span>
        </div>
        <div className="login-form">
          <span className="eyebrow">WELCOME TO FORMA STUDIO</span>
          <h2>
            Make something
            <br />
            worth watching.
          </h2>
          <p>Sign in to your agency workspace.</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const password = new FormData(e.currentTarget).get("password");
              act(async () => {
                await api("/login", post({ password }));
                await refresh();
              });
            }}
          >
            <label>
              Workspace password
              <input
                name="password"
                type="password"
                minLength={12}
                required
                autoComplete="current-password"
                placeholder="Enter your workspace password"
              />
            </label>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <button className="primary" disabled={busy}>
              {busy ? (
                <LoaderCircle className="spin" size={18} />
              ) : (
                <>
                  Enter studio <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>
          <small>
            Your password is configured by your workspace administrator.
          </small>
        </div>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("Overview");
          }}
        >
          <span className="brand-mark">f</span>forma
          <span className="brand-dot">®</span>
        </a>
        <div className="workspace-switch">
          <span className="workspace-symbol">S</span>
          <div>
            <strong>Scalinnove Studio</strong>
            <small>Agency workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {navItems.map(([name, Icon]) => (
            <button
              key={name}
              className={page === name ? "selected" : ""}
              onClick={() => navigate(name)}
            >
              <Icon size={18} />
              {name}
              {name === "Create video" && <span className="nav-new">NEW</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="inspiration">
            <span className="mini-spark">
              <Sparkles size={18} />
            </span>
            <h4>
              Your next great ad
              <br />
              starts with an idea.
            </h4>
            <p>Bring it to life in minutes.</p>
            <button onClick={() => navigate("Create video")}>
              Let’s create <ArrowUpRight size={15} />
            </button>
          </div>
          <button
            className={
              page === "Settings" ? "bottom-link selected" : "bottom-link"
            }
            onClick={openSettings}
          >
            <Settings size={18} /> Studio settings
          </button>
          <button
            className="bottom-link"
            onClick={() => setModal({ type: "help" })}
          >
            <CircleHelp size={18} /> Help & getting started
          </button>
          <div className="profile">
            <span>FS</span>
            <div>
              <strong>Forma Studio</strong>
              <small>Agency administrator</small>
            </div>
            <IconButton
              label="Sign out"
              onClick={() =>
                act(async () => {
                  await api("/logout", post({}));
                  setAuthorized(false);
                  setData(empty);
                })
              }
            >
              <LogOut size={16} />
            </IconButton>
          </div>
        </div>
      </aside>
      {mobile && (
        <div className="sidebar-scrim" onClick={() => setMobile(false)} />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <IconButton
              label="Open navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </IconButton>
            <span>Workspace</span>
            <span className="slash">/</span>
            <strong>{page}</strong>
          </div>
          <div className="topbar-right">
            <span className="system-status">
              <i /> Studio online
            </span>
            <IconButton
              label="Render activity"
              onClick={() => {
                navigate("Media library");
                setToast(
                  active.length
                    ? `${active.length} video${active.length === 1 ? " is" : "s are"} in progress.`
                    : "You’re all caught up. No active renders.",
                );
              }}
            >
              <Bell size={18} />
              {active.length > 0 && <b className="notification-dot" />}
            </IconButton>
            <span className="top-avatar">FS</span>
          </div>
        </header>
        <main className="content">
          {data.ephemeral_storage && (
            <div className="notice">
              <FolderOpen size={18} />
              <span>
                This free hosted workspace uses temporary storage. Download your
                videos before the service restarts; projects and files can be
                lost on restart or redeploy.
              </span>
            </div>
          )}
          {error && (
            <div className="error global-error" role="alert">
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}
          {page === "Overview" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    A LITTLE INSPIRATION. A LOT OF POSSIBILITY.
                  </div>
                  <h1>
                    Good ideas deserve <em>great ads.</em>
                  </h1>
                  <p>
                    Your creative command center. Let’s make something that
                    connects.
                  </p>
                </div>
                <button
                  className="primary"
                  onClick={() => navigate("Create video")}
                >
                  <Plus size={18} /> Create a video
                </button>
              </div>
              <section className="hero">
                <div className="hero-copy">
                  <span className="hero-kicker">
                    <span /> FROM IDEA TO IMPACT
                  </span>
                  <h2>
                    Your next ad.
                    <br />
                    Minus the production.
                  </h2>
                  <p>
                    Write a script. Pick a face. Make it yours.
                    <br />
                    Create narrated character videos, made locally.
                  </p>
                  <button onClick={() => navigate("Create video")}>
                    Bring your idea to life <ArrowUpRight size={17} />
                  </button>
                  <div className="hero-note">
                    <span className="tiny-avatars">
                      <Portrait id="ava" />
                      <Portrait id="noah" />
                      <Portrait id="mia" />
                    </span>
                    <span>More creativity. Less complexity.</span>
                  </div>
                </div>
                <div
                  className="hero-art"
                  aria-label="Avatar video creation illustration"
                >
                  <div className="orbit orbit-one" />
                  <div className="orbit orbit-two" />
                  <div className="floating-label top">
                    <Sparkles size={15} /> Made for your brand
                  </div>
                  <div className="mock-video">
                    <Portrait id="ava" />
                    <div className="mock-video-shade" />
                    <span className="mock-live">
                      <i /> ANIMATED
                    </span>
                    <div className="mock-caption">
                      A better way
                      <br />
                      to tell your story.<span>YOUR BRAND. YOUR VOICE.</span>
                    </div>
                    <div className="mock-controls">
                      <Play size={11} fill="currentColor" />
                      <i />
                      <span>0:15</span>
                      <AudioLines size={13} />
                    </div>
                  </div>
                  <div className="floating-label voice">
                    <span className="audio-badge">
                      <AudioLines size={22} />
                    </span>
                    <div>
                      <strong>Sounds like you.</strong>
                      <small>A voice for every story.</small>
                    </div>
                    <span className="wave">▂▅▃▇▅▂▆▃</span>
                  </div>
                  <span className="art-star">✳</span>
                  <span className="art-caption">
                    YOUR IDEAS. BROUGHT TO LIFE.
                  </span>
                </div>
              </section>
              <section className="stats">
                <div>
                  <span className="stat-icon">
                    <Video size={20} />
                  </span>
                  <div>
                    <p>Videos created</p>
                    <strong>{data.videos.length}</strong>
                    <small>Your ideas, brought to life</small>
                  </div>
                </div>
                <div>
                  <span className="stat-icon">
                    <FolderOpen size={20} />
                  </span>
                  <div>
                    <p>Active projects</p>
                    <strong>{data.projects.length}</strong>
                    <small>A home for every campaign</small>
                  </div>
                </div>
                <div>
                  <span className="stat-icon">
                    <Clapperboard size={20} />
                  </span>
                  <div>
                    <p>Ready to share</p>
                    <strong>{completed.length}</strong>
                    <small>Export. Publish. Make an impact.</small>
                  </div>
                </div>
                <div>
                  <span className="stat-icon orange">
                    <Sparkles size={20} />
                  </span>
                  <div>
                    <p>In the making</p>
                    <strong>
                      {active.length}
                      <span className="stat-live">
                        {active.length ? "RENDERING" : "ALL CLEAR"}
                      </span>
                    </strong>
                    <small>
                      {active.length
                        ? "We’re working on the good stuff"
                        : "Ready for your next big idea"}
                    </small>
                  </div>
                </div>
              </section>
              <div className="section-heading">
                <div>
                  <h2>
                    Your creative toolkit <span>IDEA → AD</span>
                  </h2>
                  <p>A simple workflow. Extraordinary possibilities.</p>
                </div>
              </div>
              <section className="toolkit">
                {[
                  [
                    FileText,
                    "01",
                    "Find the right words",
                    "Turn product details into hooks, scripts, and scroll-stopping stories.",
                    "Write a script",
                    "Create video",
                  ],
                  [
                    AudioLines,
                    "02",
                    "Give your brand a face",
                    "Choose an avatar and a voice that feel like a natural fit.",
                    "Meet your cast",
                    "Create video",
                  ],
                  [
                    Clapperboard,
                    "03",
                    "Make it a moving story",
                    "Bring it all together. Export for every feed, screen, and platform.",
                    "Explore your videos",
                    "Media library",
                  ],
                ].map(([Icon, n, title, text, link, target]) => (
                  <button
                    className="tool-card"
                    key={n}
                    onClick={() => navigate(target)}
                  >
                    <div className="tool-top">
                      <span>
                        <Icon size={21} />
                      </span>
                      <small>{n}</small>
                    </div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                    <strong>
                      {link}
                      <ArrowUpRight size={16} />
                    </strong>
                  </button>
                ))}
              </section>
              <div className="section-heading recent-heading">
                <div>
                  <h2>Fresh from your studio</h2>
                  <p>Your latest work, all in one place.</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => navigate("Media library")}
                >
                  View all videos <ArrowRight size={15} />
                </button>
              </div>
              {data.videos.length ? (
                <div className="video-grid">
                  {data.videos.slice(0, 3).map((v) => (
                    <VideoCard key={v.id} video={v} />
                  ))}
                </div>
              ) : (
                <div className="empty-state compact">
                  <span className="empty-icon">
                    <Video size={24} />
                  </span>
                  <div>
                    <h3>A blank canvas. Endless possibilities.</h3>
                    <p>
                      Your finished videos will live here. Let’s make your first
                      one.
                    </p>
                  </div>
                  <button
                    className="secondary"
                    onClick={() => navigate("Create video")}
                  >
                    Create your first video <ArrowUpRight size={16} />
                  </button>
                </div>
              )}
            </>
          )}
          {page === "Create video" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">THE NEXT GREAT AD IS YOURS</span>
                  <h1>
                    Let’s bring it <em>to life.</em>
                  </h1>
                  <p>
                    From the first word to the final frame. Make every second
                    count.
                  </p>
                </div>
                <span className="mode-tag">
                  {local
                    ? "FREE LOCAL STUDIO"
                    : data.demo_mode
                      ? "DEMO WORKSPACE"
                      : "LIVE PRODUCTION"}
                </span>
              </div>
              {local && (
                <div className="notice">
                  <AudioLines size={18} />
                  <span>
                    No API keys or GPU needed. Draft an editable template
                    script, then create a video with offline synthetic
                    narration, an illustrated character, and captions. Mouth
                    motion reacts to audio; it is not realistic lip-sync.
                  </span>
                </div>
              )}
              {data.demo_mode && (
                <div className="notice">
                  <Sparkles size={17} />
                  <span>
                    Demo mode is on. Scripts are sample copy; exports are
                    labeled 5-second MP4s without speech or avatars. Set
                    DEMO_MODE=false on the server to use live providers.
                  </span>
                </div>
              )}
              <div className="creator-grid">
                <div className="creator-steps">
                  <section className="panel">
                    <div className="panel-title">
                      <span className="step">01</span>
                      <div>
                        <h2>Start with your story</h2>
                        <p>
                          Choose a campaign and tell us what you have in mind.
                        </p>
                      </div>
                    </div>
                    <div className="inline-field">
                      <label>
                        Project
                        <select
                          value={projectId}
                          onChange={(e) => {
                            setProjectId(e.target.value);
                            setScriptId("");
                            setDraft({
                              hook: "",
                              body: "",
                              cta: "",
                              platform: "Short-form",
                            });
                          }}
                        >
                          <option value="">Choose a project</option>
                          {data.projects.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button className="secondary" onClick={newProject}>
                        <Plus size={16} /> New project
                      </button>
                    </div>
                    {project && (
                      <div className="project-context">
                        <strong>{project.product}</strong>
                        <p>
                          {project.audience} · {project.objective}
                        </p>
                      </div>
                    )}
                    <div className="two-cols">
                      <label>
                        Platform
                        <select
                          value={draft.platform}
                          onChange={(e) =>
                            setDraft({ ...draft, platform: e.target.value })
                          }
                        >
                          <option>Short-form</option>
                          <option>YouTube</option>
                        </select>
                      </label>
                      <label>
                        Tone of voice
                        <select
                          value={tone}
                          onChange={(e) => setTone(e.target.value)}
                        >
                          {["Confident", "Friendly", "Bold", "Educational"].map(
                            (t) => (
                              <option key={t}>{t}</option>
                            ),
                          )}
                        </select>
                      </label>
                    </div>
                    <button
                      className="generate-button"
                      disabled={busy || !projectId}
                      onClick={() =>
                        act(async () => {
                          const script = await api(
                            `/projects/${projectId}/generate`,
                            post({ platform: draft.platform, tone }),
                          );
                          setDraft({
                            hook: script.hook,
                            body: script.body,
                            cta: script.cta,
                            platform: script.platform,
                          });
                          setScriptId(script.id);
                          await refresh();
                          setToast(
                            "Your script is ready. Give it your personal touch.",
                          );
                        })
                      }
                    >
                      {busy ? (
                        <LoaderCircle size={17} className="spin" />
                      ) : (
                        <Sparkles size={17} />
                      )}{" "}
                      Draft ad script
                    </button>
                    <div className="script-editor">
                      {[
                        ["hook", "The hook", "Make them stop scrolling…"],
                        [
                          "body",
                          "The story",
                          "What makes your product worth a closer look?",
                        ],
                        [
                          "cta",
                          "The call to action",
                          "Give them a clear next step…",
                        ],
                      ].map(([key, label, placeholder]) => (
                        <label key={key}>
                          <span>
                            {label}
                            <small>
                              {key === "hook"
                                ? "FIRST IMPRESSIONS MATTER"
                                : key === "body"
                                  ? "MAKE A CONNECTION"
                                  : "INSPIRE ACTION"}
                            </small>
                          </span>
                          <textarea
                            rows={key === "body" ? 4 : 2}
                            value={draft[key]}
                            maxLength={key === "body" ? 5000 : 1000}
                            placeholder={placeholder}
                            onChange={(e) =>
                              setDraft({ ...draft, [key]: e.target.value })
                            }
                          />
                        </label>
                      ))}
                      <div className="script-footer">
                        <span>
                          {wordCount} words · ~{Math.ceil(wordCount / 2.5)}{" "}
                          seconds
                        </span>
                        <button
                          className="text-button"
                          disabled={
                            busy || !draft.hook || !draft.body || !draft.cta
                          }
                          onClick={() =>
                            act(async () => {
                              await saveDraft();
                              setToast("Script saved to your library.");
                            })
                          }
                        >
                          <Check size={15} /> Save script
                        </button>
                      </div>
                    </div>
                  </section>
                  <section className="panel">
                    <div className="panel-title">
                      <span className="step">02</span>
                      <div>
                        <h2>Meet your on-screen talent</h2>
                        <p>Choose a character and a free offline voice.</p>
                      </div>
                    </div>
                    <div className="avatar-grid">
                      {data.avatars.map((a) => (
                        <button
                          className={`avatar-choice ${avatar === a.id ? "chosen" : ""}`}
                          key={a.id}
                          onClick={() => setAvatar(a.id)}
                        >
                          <Portrait id={a.id} />
                          {avatar === a.id && (
                            <span className="avatar-check">
                              <Check size={12} />
                            </span>
                          )}
                          <strong>{a.name}</strong>
                          <small>{a.role}</small>
                        </button>
                      ))}
                    </div>
                    <p className="fine-print">
                      {local
                        ? "Original illustrated characters with audio-reactive mouth movement, simple blinks, and embedded captions."
                        : "Concept illustrations represent each style. Live renders use your configured D-ID presenter."}
                    </p>
                    <div className="two-cols">
                      <label>
                        Voice
                        <select
                          value={voice}
                          onChange={(e) => setVoice(e.target.value)}
                        >
                          {data.voices.map((v) => (
                            <option key={v.id} value={v.id}>
                              {v.name} · {v.description}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Expression intensity
                        <select
                          value={expression}
                          onChange={(e) => setExpression(e.target.value)}
                        >
                          <option value="natural">Natural</option>
                          <option value="lively">Lively</option>
                          <option value="serious">Subtle</option>
                        </select>
                      </label>
                    </div>
                  </section>
                </div>
                <aside className="preview-panel">
                  <section className="panel">
                    <div className="preview-title">
                      <h2>Your creative, at a glance</h2>
                      <span>PREVIEW</span>
                    </div>
                    <div
                      className={`composition ratio-${ratio.replace(":", "-")}`}
                    >
                      <Portrait id={avatar} />
                      <div className="composition-shade" />
                      <span className="composition-label">
                        {data.demo_mode ? "CONCEPT PREVIEW" : "LAYOUT PREVIEW"}
                      </span>
                      <div className="composition-copy">
                        <span>
                          {project?.product || "YOUR BRAND, REIMAGINED"}
                        </span>
                        <h3>{draft.hook || "A good story starts with you."}</h3>
                        <small>{draft.cta || "Make your next move."}</small>
                      </div>
                    </div>
                    <p className="fine-print">
                      {local
                        ? "Local exports contain the illustrated character and embedded captions. Caption timing is estimated from the narration."
                        : "Layout concept only. Provider output uses padding and does not include burned-in captions."}
                    </p>
                    <label>Make it fit</label>
                    <div className="ratio-options">
                      {[
                        ["9:16", "Reels & TikTok"],
                        ["1:1", "Social feed"],
                        ["16:9", "YouTube"],
                      ].map(([r, label]) => (
                        <button
                          key={r}
                          className={ratio === r ? "chosen" : ""}
                          onClick={() => setRatio(r)}
                        >
                          <i
                            className={`ratio-icon r-${r.replace(":", "-")}`}
                          />
                          <strong>{r}</strong>
                          <small>{label}</small>
                        </button>
                      ))}
                    </div>
                    <label>
                      Video name
                      <input
                        value={videoName}
                        maxLength={160}
                        onChange={(e) => setVideoName(e.target.value)}
                        placeholder={
                          project
                            ? `${project.name} · ${ratio}`
                            : "Name your next great ad"
                        }
                      />
                    </label>
                    <button
                      className="primary render-button"
                      disabled={
                        busy ||
                        !projectId ||
                        !draft.hook ||
                        !draft.body ||
                        !draft.cta
                      }
                      onClick={() => act(render)}
                    >
                      {busy ? (
                        <LoaderCircle className="spin" size={18} />
                      ) : (
                        <WandSparkles size={18} />
                      )}{" "}
                      {local
                        ? "Create free video"
                        : data.demo_mode
                          ? "Generate demo video"
                          : "Generate video"}
                      <ArrowRight size={17} />
                    </button>
                    <span className="render-note">
                      {local
                        ? "Generated on your CPU. No paid API calls."
                        : data.demo_mode
                          ? "No credits used in demo mode."
                          : "Submitting a render may incur D-ID charges."}
                    </span>
                  </section>
                  <div className="creative-tip">
                    <Sparkles size={18} />
                    <div>
                      <strong>A little creative direction</strong>
                      <p>
                        Lead with a problem your audience knows. End with one
                        action they can take.
                      </p>
                    </div>
                  </div>
                </aside>
              </div>
            </>
          )}
          {page === "Projects" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">
                    BIG IDEAS, BEAUTIFULLY ORGANIZED
                  </span>
                  <h1>
                    A home for <em>every campaign.</em>
                  </h1>
                  <p>
                    Keep the product, the story, and the final cut together.
                  </p>
                </div>
                <button className="primary" onClick={newProject}>
                  <Plus size={18} /> New project
                </button>
              </div>
              {data.projects.length ? (
                <div className="project-grid">
                  {data.projects.map((p, i) => (
                    <button
                      className="project-card"
                      key={p.id}
                      onClick={() => {
                        setProjectId(p.id);
                        setScriptId("");
                        setDraft({
                          hook: "",
                          body: "",
                          cta: "",
                          platform: "Short-form",
                        });
                        navigate("Create video");
                      }}
                    >
                      <div className={`project-cover cover-${i % 3}`}>
                        <span>{p.product.slice(0, 1).toUpperCase()}</span>
                        <ArrowUpRight size={24} />
                      </div>
                      <div className="project-details">
                        <h2>{p.name}</h2>
                        <p>{p.product}</p>
                        <div>
                          <span>
                            {
                              data.scripts.filter((s) => s.project_id === p.id)
                                .length
                            }{" "}
                            scripts
                          </span>
                          <span>
                            {
                              data.videos.filter((v) => v.project_id === p.id)
                                .length
                            }{" "}
                            videos
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <Empty
                  icon={FolderOpen}
                  title="Every great campaign starts somewhere."
                  text="Create a project with your product, audience, and objective."
                  action="Create a project"
                  onClick={newProject}
                />
              )}
            </>
          )}
          {page === "Script library" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">THE WORDS BEHIND THE WORK</span>
                  <h1>
                    Stories that <em>start something.</em>
                  </h1>
                  <p>Your saved hooks, scripts, and calls to action.</p>
                </div>
                <button
                  className="primary"
                  onClick={() => navigate("Create video")}
                >
                  <Plus size={18} /> Write a script
                </button>
              </div>
              {data.scripts.length ? (
                <div className="script-grid">
                  {data.scripts.map((s) => (
                    <article className="saved-script" key={s.id}>
                      <div>
                        <span className="script-tag">{s.platform}</span>
                        <FileText size={18} />
                      </div>
                      <h2>{s.hook}</h2>
                      <p>{s.body}</p>
                      <strong>{s.cta}</strong>
                      <footer>
                        <span>
                          {
                            data.projects.find((p) => p.id === s.project_id)
                              ?.name
                          }
                        </span>
                        <button
                          className="text-button"
                          onClick={() => selectScript(s)}
                        >
                          Open script <ArrowUpRight size={16} />
                        </button>
                      </footer>
                    </article>
                  ))}
                </div>
              ) : (
                <Empty
                  icon={FileText}
                  title="Your best lines belong here."
                  text="Generate a script or write your own in the video creator."
                  action="Write your first script"
                  onClick={() => navigate("Create video")}
                />
              )}
            </>
          )}
          {page === "Media library" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">FROM YOUR STUDIO TO THE WORLD</span>
                  <h1>
                    Made by you. <em>Ready to move.</em>
                  </h1>
                  <p>
                    Follow your renders, revisit your work, and export your next
                    campaign.
                  </p>
                </div>
                <button
                  className="primary"
                  onClick={() => navigate("Create video")}
                >
                  <Plus size={18} /> Create a video
                </button>
              </div>
              <div className="library-toolbar">
                <div>
                  <strong>
                    All videos <span>{data.videos.length}</span>
                  </strong>
                  <span>{active.length} in progress</span>
                </div>
                <label className="search-field">
                  <Search size={16} />
                  <input
                    aria-label="Search videos"
                    placeholder="Find a video…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </label>
              </div>
              {filteredVideos.length ? (
                <div className="video-grid library">
                  {filteredVideos.map((v) => (
                    <VideoCard key={v.id} video={v} />
                  ))}
                </div>
              ) : (
                <Empty
                  icon={Video}
                  title={
                    query
                      ? "No videos match that search."
                      : "A little idea. A moving story."
                  }
                  text={
                    query
                      ? "Try another name or clear your search."
                      : "Your generated videos will appear here, ready to preview and download."
                  }
                  action={query ? "Clear search" : "Create a video"}
                  onClick={() =>
                    query ? setQuery("") : navigate("Create video")
                  }
                />
              )}
            </>
          )}
          {page === "Settings" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">BEHIND THE CREATIVE</span>
                  <h1>
                    Your studio, <em>connected.</em>
                  </h1>
                  <p>Manage the services that bring your ideas to life.</p>
                </div>
                <span className="mode-tag">
                  {local
                    ? "FREE LOCAL MODE"
                    : data.demo_mode
                      ? "DEMO MODE"
                      : "LIVE MODE"}
                </span>
              </div>
              <div className="notice">
                <CircleHelp size={18} />
                <span>
                  {local
                    ? "Your free studio is ready. Scripts, synthetic voice, animation, and captions are generated locally. No provider accounts or credits are required."
                    : "Optional provider keys are encrypted on the server and never returned to your browser."}
                </span>
              </div>
              {local ? (
                <div className="settings-grid">
                  <section className="panel provider-card">
                    <div className="provider-top">
                      <span className="provider-logo">
                        <FileText />
                      </span>
                      <h2>Script studio</h2>
                      <span className="connection connected">Included</span>
                    </div>
                    <h3>Your brief. A ready-to-edit draft.</h3>
                    <p>
                      Local templates use your product, audience, objective,
                      tone, and platform. Refine every line in the editor. This
                      mode uses no language model or API.
                    </p>
                  </section>
                  <section className="panel provider-card">
                    <div className="provider-top">
                      <span className="provider-logo">
                        <AudioLines />
                      </span>
                      <h2>Offline production</h2>
                      <span className="connection connected">Included</span>
                    </div>
                    <h3>A voice and character for your story.</h3>
                    <p>
                      {data.tts_engine === "loudkit"
                        ? "Optional loudkit neural narration on CPU."
                        : "Bundled eSpeak NG synthetic voices on CPU."}{" "}
                      Original illustrated characters, audio-reactive mouth
                      movement, captions, and three export sizes. No GPU or API
                      keys.
                    </p>
                  </section>
                </div>
              ) : (
                <div className="settings-grid">
                  {[
                    [
                      "openai",
                      "OpenAI",
                      "The words behind the story.",
                      "Generate hooks, spoken scripts, and clear calls to action.",
                      "API key",
                    ],
                    [
                      "did",
                      "D-ID",
                      "A face and voice for your brand.",
                      "Animate a presenter with Microsoft neural voices and automatic lip-sync.",
                      "D-ID API key (Basic auth value)",
                    ],
                  ].map(([id, name, title, description, label]) => (
                    <section className="panel provider-card" key={id}>
                      <div className="provider-top">
                        <span className="provider-logo">
                          {id === "openai" ? <Sparkles /> : <Video />}
                        </span>
                        <h2>{name}</h2>
                        <span
                          className={`connection ${providerSettings?.providers[id] ? "connected" : ""}`}
                        >
                          {providerSettings?.providers[id]
                            ? "Configured"
                            : "Not configured"}
                        </span>
                      </div>
                      <h3>{title}</h3>
                      <p>{description}</p>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          const form = e.currentTarget;
                          const key = new FormData(form).get("key");
                          act(async () => {
                            await api(`/settings/keys/${id}`, {
                              method: "PUT",
                              body: JSON.stringify({ key }),
                            });
                            setProviderSettings(await api("/settings"));
                            form.reset();
                            setToast(`${name} key saved securely.`);
                          });
                        }}
                      >
                        <label>
                          {label}
                          <input
                            name="key"
                            type="password"
                            autoComplete="off"
                            required
                            minLength={5}
                            maxLength={1000}
                            placeholder={
                              providerSettings?.providers[id]
                                ? "Enter a replacement key"
                                : "Paste your API key"
                            }
                          />
                        </label>
                        <div className="key-actions">
                          <button className="primary" disabled={busy}>
                            Save key <Check size={15} />
                          </button>
                          <button
                            type="button"
                            className="text-button"
                            disabled={busy || !providerSettings?.providers[id]}
                            onClick={() =>
                              act(async () => {
                                await api(`/settings/keys/${id}`, {
                                  method: "DELETE",
                                });
                                setProviderSettings(await api("/settings"));
                                setToast(
                                  "Stored key removed. Server environment defaults, if set, still apply.",
                                );
                              })
                            }
                          >
                            Remove stored key
                          </button>
                        </div>
                      </form>
                    </section>
                  ))}
                </div>
              )}
              <section className="panel deployment-note">
                <h2>One workspace. Your whole production flow.</h2>
                <p>
                  This installation uses one administrator login. Project data,
                  saved scripts, and video assets are private to this agency
                  workspace. Set up separate deployments for separate agencies.
                </p>
                <p>
                  {local
                    ? "Free software runs on your own computer; electricity, hardware, and any third-party hosting are separate. The default voices are synthetic and the animation is intentionally illustrated."
                    : "Provider subscriptions, approved presenters, available voices, output rights, and generation costs are managed in your provider accounts."}
                </p>
              </section>
            </>
          )}
          <footer className="page-footer">
            <span>Made for the way you create.</span>
            <span>
              FORMA STUDIO <span className="footer-star">✳</span> MADE LOCALLY.
              MADE BY YOU.
            </span>
          </footer>
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Check size={18} />
          {toast}
          <button
            onClick={() => setToast("")}
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}
      {modal?.type === "project" && (
        <Modal
          title="Every great ad starts with a good brief."
          onClose={() => setModal(null)}
        >
          <p className="modal-description">
            Tell us what you’re making and who you’re making it for.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const values = Object.fromEntries(new FormData(e.currentTarget));
              act(async () => {
                const p = await api("/projects", post(values));
                setProjectId(p.id);
                setScriptId("");
                setDraft({
                  hook: "",
                  body: "",
                  cta: "",
                  platform: "Short-form",
                });
                await refresh();
                setModal(null);
                navigate("Create video");
                setToast("Project created. Let’s find your story.");
              });
            }}
          >
            <label>
              Project name
              <input
                name="name"
                required
                maxLength={160}
                placeholder="e.g. Summer launch campaign"
                autoFocus
              />
            </label>
            <label>
              Product or service
              <input
                name="product"
                required
                maxLength={200}
                placeholder="What are we introducing to the world?"
              />
            </label>
            <label>
              Target audience
              <textarea
                name="audience"
                required
                maxLength={1000}
                rows={2}
                placeholder="Who is this for? Be as specific as you like."
              />
            </label>
            <label>
              Ad objective
              <textarea
                name="objective"
                required
                maxLength={1000}
                rows={2}
                placeholder="Drive signups, introduce a new product, build awareness…"
              />
            </label>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <button className="primary" disabled={busy}>
              Create project <ArrowRight size={17} />
            </button>
          </form>
        </Modal>
      )}
      {modal?.type === "rename" && (
        <Modal title="Give it a name." onClose={() => setModal(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const name = new FormData(e.currentTarget).get("name");
              act(async () => {
                await api(`/videos/${modal.video.id}`, {
                  method: "PATCH",
                  body: JSON.stringify({ name }),
                });
                await refresh();
                setModal(null);
                setToast("Video renamed.");
              });
            }}
          >
            <label>
              Video name
              <input
                name="name"
                required
                maxLength={160}
                defaultValue={modal.video.name}
              />
            </label>
            {error && <div className="error">{error}</div>}
            <button className="primary" disabled={busy}>
              Save name <Check size={16} />
            </button>
          </form>
        </Modal>
      )}
      {modal?.type === "video" && (
        <Modal title={modal.video.name} onClose={() => setModal(null)} wide>
          <video
            className="video-player"
            src={`/api/videos/${modal.video.id}/file`}
            controls
            autoPlay
            playsInline
            onError={() =>
              setError(
                "The video could not be loaded. Check your connection or restore the media file.",
              )
            }
          />
          <div className="player-footer">
            <span>
              {modal.video.ratio} · MP4{" "}
              {modal.video.engine === "local"
                ? "· Local synthetic narration"
                : modal.video.demo
                  ? "· Demo sample"
                  : ""}
            </span>
            <div className="export-actions">
              <select
                aria-label="Export aspect ratio"
                value={exportRatio}
                onChange={(e) => setExportRatio(e.target.value)}
              >
                <option value="original">Original · {modal.video.ratio}</option>
                <option value="9:16">Vertical · 9:16</option>
                <option value="1:1">Square · 1:1</option>
                <option value="16:9">Landscape · 16:9</option>
              </select>
              <button
                className="primary"
                disabled={busy}
                onClick={() =>
                  act(async () => {
                    const result = await api(
                      `/videos/${modal.video.id}/exports`,
                      post({
                        ratio:
                          exportRatio === "original"
                            ? modal.video.ratio
                            : exportRatio,
                      }),
                    );
                    const link = document.createElement("a");
                    link.href = result.url;
                    link.download = "";
                    link.click();
                    setToast("Your MP4 export is ready.");
                  })
                }
              >
                {busy ? (
                  <LoaderCircle size={17} className="spin" />
                ) : (
                  <Download size={17} />
                )}{" "}
                Export MP4
              </button>
            </div>
          </div>
        </Modal>
      )}
      {modal?.type === "status" && (
        <Modal title={modal.video.name} onClose={() => setModal(null)}>
          {(() => {
            const v =
              data.videos.find((v) => v.id === modal.video.id) || modal.video;
            return (
              <div className="status-detail">
                <span className={`status-pill ${v.status}`}>{v.status}</span>
                <h3>
                  {v.status === "failed"
                    ? "This render needs a second look."
                    : v.status === "completed"
                      ? "Your video is ready."
                      : "A little magic is in the making."}
                </h3>
                <p>
                  {v.error ||
                    "Progress updates automatically. You can keep working while your video renders."}
                </p>
                <div className="progress-track">
                  <i style={{ width: `${v.progress}%` }} />
                </div>
                <small>
                  {v.progress}% · {v.ratio}
                </small>
                {v.status === "completed" && (
                  <button
                    className="primary"
                    onClick={() => setModal({ type: "video", video: v })}
                  >
                    Watch video <Play size={17} />
                  </button>
                )}
                {v.status === "failed" && (
                  <button
                    className="secondary"
                    onClick={() => {
                      const script = data.scripts.find(
                        (s) => s.id === v.script_id,
                      );
                      if (script) selectScript(script);
                      setModal(null);
                    }}
                  >
                    Return to creator <ArrowRight size={17} />
                  </button>
                )}
              </div>
            );
          })()}
        </Modal>
      )}
      {modal?.type === "help" && (
        <Modal
          title="A great ad, in three simple steps."
          onClose={() => setModal(null)}
        >
          <div className="help-steps">
            <p>
              <strong>01 · Set the scene.</strong>Create a project with your
              product, audience, and ad objective.
            </p>
            <p>
              <strong>02 · Make it yours.</strong>Generate a script, edit the
              words, and choose your presenter, voice, and format.
            </p>
            <p>
              <strong>03 · Let it move.</strong>Generate your video, follow its
              progress in the media library, then preview and download the MP4.
            </p>
            <div className="notice">
              Local mode creates real narrated videos with illustrated animation
              and embedded captions. No paid keys or GPU are needed. Scripts are
              templates you can edit, and captions use estimated timing.
            </div>
            <button
              className="primary"
              onClick={() => {
                setModal(null);
                navigate("Create video");
              }}
            >
              Let’s create <ArrowRight size={17} />
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
function Empty({ icon: Icon, title, text, action, onClick }) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon size={30} />
      </span>
      <h2>{title}</h2>
      <p>{text}</p>
      <button className="secondary" onClick={onClick}>
        {action}
        <ArrowUpRight size={16} />
      </button>
    </div>
  );
}
