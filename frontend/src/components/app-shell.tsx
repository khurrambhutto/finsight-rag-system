import {
  Show,
  SignInButton,
  SignUpButton,
  UserButton,
  useAuth,
  useUser,
} from "@clerk/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { fetchChatThreads } from "../lib/api";
import { OllamaModelProvider } from "../lib/ollama-model-context";

const navItems = [{ to: "/app/chat", label: "Chat" }];

function hamburgerIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden
    >
      <path
        d="M3 5h12M3 9h12M3 13h12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function settingsMenuIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden
    >
      <path
        d="M8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <path
        d="M12.78 10a.76.76 0 0 1 .15.8l-.18.62a.76.76 0 0 1-.93.5l-.59-.15a.76.76 0 0 0-.8.32l-.32.55a.76.76 0 0 1-1.32 0l-.32-.55a.76.76 0 0 0-.8-.32l-.59.15a.76.76 0 0 1-.93-.5l-.18-.62a.76.76 0 0 1 .15-.8l.39-.45a.76.76 0 0 0 0-.99l-.39-.45a.76.76 0 0 1-.15-.8l.18-.62a.76.76 0 0 1 .93-.5l.59.15c.27.07.57 0 .8-.32l.32-.55a.76.76 0 0 1 1.32 0l.32.55c.22.32.52.39.8.32l.59-.15a.76.76 0 0 1 .93.5l.18.62a.76.76 0 0 1-.15.8l-.39.45a.76.76 0 0 0 0 .99l.39.45Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AppShell() {
  return <AppShellLayout />;
}

function AppShellLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { getToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useUser();
  const threadsQuery = useQuery({
    queryKey: ["chatThreads"],
    queryFn: () => fetchChatThreads(() => getToken()),
  });
  const displayName =
    user?.firstName ||
    user?.primaryEmailAddress?.emailAddress?.split("@")[0] ||
    "Account";

  function handleNewChat() {
    void navigate("/app/chat");
  }

  return (
    <div className="app-shell">
      <aside
        className={`sidebar${sidebarCollapsed ? " sidebar--collapsed" : ""}`}
        aria-label="Main navigation"
      >
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-icon">R</div>
            <span className="brand-name">RAG System</span>
          </div>
          <button
            type="button"
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed((c) => !c)}
            aria-expanded={!sidebarCollapsed}
            aria-controls="sidebar-primary"
            aria-label={
              sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
            }
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {hamburgerIcon()}
          </button>
        </div>

        <div className="sidebar-body" id="sidebar-primary">
          <button
            className="new-chat-btn"
            type="button"
            onClick={handleNewChat}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M7 2.5V11.5M2.5 7H11.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            New chat
          </button>

          <div className="nav-section-label">Navigation</div>
          <nav>
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `nav-link${isActive ? " active" : ""}`
                }
              >
                <span className="nav-dot" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="nav-section-label">Recent chats</div>
          <div className="thread-list" aria-label="Saved chats">
            {threadsQuery.isLoading ? (
              <p className="thread-list-empty">Loading chats...</p>
            ) : threadsQuery.data?.length ? (
              threadsQuery.data.map((thread) => (
                <button
                  key={thread.id}
                  type="button"
                  className={`thread-link${location.pathname === `/app/chat/${thread.id}` ? " active" : ""}`}
                  onClick={() => void navigate(`/app/chat/${thread.id}`)}
                  title={thread.title}
                >
                  <span className="thread-link-title">{thread.title}</span>
                  <span className="thread-link-preview">
                    {thread.preview ?? "No messages yet"}
                  </span>
                </button>
              ))
            ) : (
              <p className="thread-list-empty">No saved chats yet.</p>
            )}
          </div>
        </div>

        <div className="sidebar-footer">
          <Show when="signed-out">
            <div className="auth-actions">
              <SignInButton mode="modal">
                <button className="ghost-button" type="button">
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button className="ghost-button" type="button">
                  Sign up
                </button>
              </SignUpButton>
            </div>
          </Show>

          <Show when="signed-in">
            <div className="user-row">
              <div className="user-info">
                <p className="user-label">Signed in as</p>
                <p className="user-name">{displayName}</p>
              </div>
              <UserButton>
                <UserButton.MenuItems>
                  <UserButton.Action
                    label="App settings"
                    labelIcon={settingsMenuIcon()}
                    onClick={() => navigate("/app/settings")}
                  />
                </UserButton.MenuItems>
              </UserButton>
            </div>
          </Show>
        </div>
      </aside>

      <main className="main-content">
        <OllamaModelProvider>
          <Outlet />
        </OllamaModelProvider>
      </main>
    </div>
  );
}
