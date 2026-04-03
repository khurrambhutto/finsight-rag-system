import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

const FAVORITES_KEY = "rag-system.model-favorites";

type SidebarMode = "all" | "favorites";

function loadFavoriteIds(): string[] {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === "string")
      : [];
  } catch {
    return [];
  }
}

function saveFavoriteIds(ids: string[]) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(ids));
}

export function displayModelId(modelId: string) {
  return modelId.replace(/^ollama\//, "");
}

function modelSubtitle(modelId: string): string {
  const short = displayModelId(modelId);
  const s = short.toLowerCase();
  if (/llava|bakllava|moondream|vision/i.test(s)) {
    return "Multimodal / vision-style model (typical usage)";
  }
  if (/coder|code|starcoder|deepseek-coder/i.test(s)) {
    return "Often strong on code and technical prompts";
  }
  if (/tiny|mini|1b|3b/i.test(s)) {
    return "Smaller model — fast responses, lighter footprint";
  }
  return "Runs locally through your Ollama server";
}

function modelCapabilities(modelId: string): {
  vision: boolean;
  reasoning: boolean;
  longContext: boolean;
} {
  const s = modelId.toLowerCase();
  return {
    vision: /llava|bakllava|moondream|vision|qwen.*vl|gemma.*it/i.test(s),
    reasoning:
      /r1|qwq|think|reason|o1|opus|sonnet|haiku|logic|math/i.test(s),
    longContext:
      /\b(32b|70b|72b|405b|large|128k|200k|1m)\b|long|mixtral|405b/i.test(s),
  };
}

type ModelPickerProps = {
  models: string[];
  selectedModel: string;
  onSelect: (modelId: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
  listError?: Error | null;
};

export function ModelPicker({
  models,
  selectedModel,
  onSelect,
  disabled = false,
  isLoading = false,
  listError = null,
}: ModelPickerProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [popoverBox, setPopoverBox] = useState<{
    bottom: number;
    right: number;
    width: number;
    maxHeight: number;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [sidebar, setSidebar] = useState<SidebarMode>("all");
  const [favoriteIds, setFavoriteIds] = useState<string[]>(loadFavoriteIds);

  const syncFavorites = useCallback((next: string[]) => {
    setFavoriteIds(next);
    saveFavoriteIds(next);
  }, []);

  const toggleFavorite = useCallback(
    (modelId: string, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const set = new Set(favoriteIds);
      if (set.has(modelId)) set.delete(modelId);
      else set.add(modelId);
      syncFavorites([...set]);
    },
    [favoriteIds, syncFavorites],
  );

  useEffect(() => {
    if (!open) return;
    setSearch("");
    const t = window.setTimeout(() => searchInputRef.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }, [open]);

  const updatePopoverPosition = useCallback(() => {
    const el = rootRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const gap = 10;
    setPopoverBox({
      bottom: window.innerHeight - r.top + gap,
      right: window.innerWidth - r.right,
      width: Math.min(440, window.innerWidth - 24),
      maxHeight: Math.min(520, window.innerHeight * 0.58),
    });
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      setPopoverBox(null);
      return;
    }
    updatePopoverPosition();
    window.addEventListener("resize", updatePopoverPosition);
    document.addEventListener("scroll", updatePopoverPosition, true);
    return () => {
      window.removeEventListener("resize", updatePopoverPosition);
      document.removeEventListener("scroll", updatePopoverPosition, true);
    };
  }, [open, updatePopoverPosition]);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      const t = e.target as Node;
      if (rootRef.current?.contains(t) || popoverRef.current?.contains(t)) {
        return;
      }
      setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const filteredModels = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = models;
    if (sidebar === "favorites") {
      const fav = new Set(favoriteIds);
      list = models.filter((m) => fav.has(m));
    }
    if (!q) return list;
    return list.filter((m) =>
      displayModelId(m).toLowerCase().includes(q),
    );
  }, [models, search, sidebar, favoriteIds]);

  const buttonLabel = useMemo(() => {
    if (isLoading) return "Loading models…";
    if (listError) return "Models unavailable";
    if (models.length === 0) return "No models";
    if (selectedModel) return displayModelId(selectedModel);
    return "Choose model";
  }, [isLoading, listError, models.length, selectedModel]);

  const isTriggerDisabled =
    disabled || isLoading || (!listError && models.length === 0);

  function pick(modelId: string) {
    onSelect(modelId);
    setOpen(false);
  }

  function toggleFilterFavorites() {
    setSidebar((s) => (s === "favorites" ? "all" : "favorites"));
  }

  return (
    <div
      ref={rootRef}
      className={`model-picker-wrap${open ? " model-picker-wrap--open" : ""}`}
    >
      <button
        type="button"
        className={`composer-model-pill${open ? " composer-model-pill--open" : ""}`}
        disabled={isTriggerDisabled}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => {
          if (!isTriggerDisabled) setOpen((o) => !o);
        }}
      >
        <span className="composer-model-pill-label">{buttonLabel}</span>
        <span className="composer-model-chevron" aria-hidden>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path
              d="M2.5 4.25L6 7.75l3.5-3.5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </button>

      {open &&
        !isTriggerDisabled &&
        popoverBox &&
        createPortal(
          <div
            ref={popoverRef}
            className="model-picker-popover"
            style={{
              position: "fixed",
              bottom: popoverBox.bottom,
              right: popoverBox.right,
              width: popoverBox.width,
              maxHeight: popoverBox.maxHeight,
              zIndex: 2000,
            }}
            role="listbox"
            aria-label="Models"
          >
            <div className="model-picker-search-row">
            <div className="model-picker-search">
              <svg
                className="model-picker-search-icon"
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden
              >
                <path
                  d="M7 12.5a5.5 5.5 0 100-11 5.5 5.5 0 000 11zM14 14l-3-3"
                  stroke="currentColor"
                  strokeWidth="1.3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <input
                ref={searchInputRef}
                type="search"
                className="model-picker-search-input"
                placeholder="Search models…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoComplete="off"
                spellCheck={false}
              />
            </div>
            <button
              type="button"
              className={`model-picker-filter-btn${sidebar === "favorites" ? " model-picker-filter-btn--on" : ""}`}
              onClick={toggleFilterFavorites}
              aria-pressed={sidebar === "favorites"}
              title="Filter to favorites"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path
                  d="M3.25 4.5h11.5v1.2L10 10.2V14l-2 .75v-4.55L3.25 5.7V4.5z"
                  stroke="currentColor"
                  strokeWidth="1.25"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>

          <div className="model-picker-body">
            <div className="model-picker-sidebar">
              <button
                type="button"
                className={`model-picker-nav-btn${sidebar === "all" ? " model-picker-nav-btn--active" : ""}`}
                onClick={() => setSidebar("all")}
                title="All Ollama models"
                aria-label="All Ollama models"
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M9.4 5.05 8.45 2.05 7.45 4.5c-1.55.8-2.6 2.45-2.85 4.25-.4 2.85.95 5.6 3.45 7.15A5.35 5.35 0 0 0 12 17c1.4 0 2.75-.45 4-1.25 2.5-1.55 3.85-4.3 3.45-7.15-.25-1.8-1.3-3.45-2.85-4.25L14.55 2.05 13.6 5.05c-.85-.35-1.75-.55-2.6-.55-.9 0-1.8.2-2.6.55Z"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                  <circle cx="9.35" cy="10.2" r="1.05" fill="currentColor" />
                  <circle cx="14.65" cy="10.2" r="1.05" fill="currentColor" />
                  <circle
                    cx="12"
                    cy="14.85"
                    r="3"
                    stroke="currentColor"
                    strokeWidth="1.2"
                  />
                  <path
                    d="M12 12.9v1.25m-1.6 1.45L12 14.4l1.6 1.2"
                    stroke="currentColor"
                    strokeWidth="1"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <button
                type="button"
                className={`model-picker-nav-btn${sidebar === "favorites" ? " model-picker-nav-btn--active" : ""}`}
                onClick={() => setSidebar("favorites")}
                title="Favorites"
                aria-label="Favorites"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path
                    d="M9 2.5l2 4.2 4.8.7-3.5 3.4.8 4.8L9 13.9 4.9 15.6l.8-4.8L2.2 7.4 7 6.7 9 2.5z"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>

            <div className="model-picker-list" role="presentation">
              {listError && (
                <p className="model-picker-empty">{listError.message}</p>
              )}
              {!listError && filteredModels.length === 0 && (
                <p className="model-picker-empty">
                  {sidebar === "favorites"
                    ? "No favorites yet. Star a model to add it here."
                    : search.trim()
                      ? "No models match your search."
                      : "No models available from Ollama."}
                </p>
              )}
              {!listError &&
                filteredModels.map((id) => {
                  const caps = modelCapabilities(id);
                  const fav = favoriteIds.includes(id);
                  const selected = id === selectedModel;
                  const initial = displayModelId(id).charAt(0).toUpperCase();
                  return (
                    <div
                      key={id}
                      role="option"
                      aria-selected={selected}
                      className={`model-picker-row${selected ? " model-picker-row--selected" : ""}`}
                      onClick={() => pick(id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          pick(id);
                        }
                      }}
                      tabIndex={0}
                    >
                      <div className="model-picker-row-avatar" aria-hidden>
                        {initial}
                      </div>
                      <div className="model-picker-row-main">
                        <div className="model-picker-row-title-line">
                          <span className="model-picker-row-name">
                            {displayModelId(id)}
                          </span>
                          <button
                            type="button"
                            className={`model-picker-fav${fav ? " model-picker-fav--on" : ""}`}
                            aria-label={
                              fav ? "Remove from favorites" : "Add to favorites"
                            }
                            onClick={(e) => toggleFavorite(id, e)}
                          >
                            <svg
                              width="16"
                              height="16"
                              viewBox="0 0 16 16"
                              fill="none"
                            >
                              <path
                                d="M8 1.5l2 4.2 4.2.6-3 2.9.7 2.8L8 10.6 3.1 12l.7-2.8-3-2.9 4.2-.6L8 1.5z"
                                stroke="currentColor"
                                strokeWidth="1.2"
                                strokeLinejoin="round"
                                fill={fav ? "currentColor" : "none"}
                              />
                            </svg>
                          </button>
                        </div>
                        <p className="model-picker-row-desc">
                          {modelSubtitle(id)}
                        </p>
                      </div>
                      <div className="model-picker-row-tools">
                        <span className="model-picker-caps" aria-hidden>
                          {caps.vision && (
                            <span className="model-picker-cap" title="Vision">
                              <svg
                                width="14"
                                height="14"
                                viewBox="0 0 14 14"
                                fill="none"
                              >
                                <path
                                  d="M1.5 7s2-4 5.5-4 5.5 4 5.5 4-2 4-5.5 4S1.5 7 1.5 7z"
                                  stroke="currentColor"
                                  strokeWidth="1.2"
                                  strokeLinejoin="round"
                                />
                                <circle
                                  cx="7"
                                  cy="7"
                                  r="1.8"
                                  stroke="currentColor"
                                  strokeWidth="1.2"
                                />
                              </svg>
                            </span>
                          )}
                          {caps.reasoning && (
                            <span className="model-picker-cap" title="Reasoning">
                              <svg
                                width="14"
                                height="14"
                                viewBox="0 0 14 14"
                                fill="none"
                              >
                                <path
                                  d="M4 9c1.5 1 4.5 1 6-1M4 5c1.5-1 4.5-1 6 1M7 2v2M7 10v2M3 7H1m12 0h-2"
                                  stroke="currentColor"
                                  strokeWidth="1.2"
                                  strokeLinecap="round"
                                />
                              </svg>
                            </span>
                          )}
                          {caps.longContext && (
                            <span className="model-picker-cap" title="Long context">
                              <svg
                                width="14"
                                height="14"
                                viewBox="0 0 14 14"
                                fill="none"
                              >
                                <path
                                  d="M3.5 2.5h7v9h-7v-9zM5 5h4M5 7.5h4M5 10h2.5"
                                  stroke="currentColor"
                                  strokeWidth="1.2"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                />
                              </svg>
                            </span>
                          )}
                        </span>
                        <button
                          type="button"
                          className="model-picker-info"
                          title={id}
                          aria-label={`Full model id: ${id}`}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <svg width="14" height="14" viewBox="0 0 14 14">
                            <circle
                              cx="7"
                              cy="7"
                              r="6"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.2"
                            />
                            <path
                              d="M7 6.2V10M7 4.1v.02"
                              stroke="currentColor"
                              strokeWidth="1.3"
                              strokeLinecap="round"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
