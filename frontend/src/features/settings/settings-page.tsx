import { useAuth } from "@clerk/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchProvider, testProvider } from "../../lib/api";
import { useOllamaModel } from "../../lib/ollama-model-context";

export function SettingsPage() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const {
    models,
    selectedModel,
    setSelectedModel,
    isLoading: modelsLoading,
    listsError,
  } = useOllamaModel();

  const providerQuery = useQuery({
    queryKey: ["provider"],
    queryFn: () => fetchProvider(() => getToken()),
  });

  const providerTest = useMutation({
    mutationFn: () => testProvider(() => getToken()),
  });

  return (
    <section className="settings-page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Configuration</p>
          <h2 className="page-title">Settings</h2>
        </div>
        <button
          className="btn-secondary"
          onClick={() => {
            void providerQuery.refetch();
            void queryClient.invalidateQueries({ queryKey: ["ollama-models"] });
          }}
          disabled={providerQuery.isFetching}
        >
          {providerQuery.isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {/* Provider info */}
      <div className="settings-section">
        <div className="settings-section-title">AI Provider</div>

        <div className="settings-row">
          <span className="settings-key">Provider</span>
          <span className="settings-value">
            {providerQuery.isFetching
              ? "—"
              : (providerQuery.data?.name ?? "Not configured")}
          </span>
        </div>

        <div className="settings-row">
          <span className="settings-key">Type</span>
          <span className="settings-value">
            {providerQuery.isFetching
              ? "—"
              : (providerQuery.data?.provider_type ?? "—")}
          </span>
        </div>

        <div className="settings-row">
          <span className="settings-key">Base URL</span>
          <span className="settings-value">
            {providerQuery.isFetching
              ? "—"
              : (providerQuery.data?.base_url ?? "—")}
          </span>
        </div>

        <div className="settings-field">
          <label className="settings-field-label" htmlFor="ollama-model">
            Ollama model
          </label>
          <p className="settings-field-hint">
            Pulled from <code>{providerQuery.data?.base_url ?? "Ollama"}</code>
            . This choice is saved in your browser.
          </p>
          <select
            id="ollama-model"
            className="settings-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={modelsLoading || models.length === 0}
          >
            {models.length === 0 ? (
              <option value="">No models found</option>
            ) : (
              models.map((m) => (
                <option key={m} value={m}>
                  {m.replace(/^ollama\//, "")}
                </option>
              ))
            )}
          </select>
          {listsError && (
            <p className="settings-field-error">{listsError.message}</p>
          )}
        </div>

        <div className="settings-row">
          <span className="settings-key">Default (env)</span>
          <span className="settings-value">
            {providerQuery.isFetching
              ? "—"
              : (providerQuery.data?.default_model ?? "—")}
          </span>
        </div>
      </div>

      {/* Connectivity test */}
      <div className="settings-section">
        <div className="settings-section-title">Connectivity</div>

        <div className="settings-action-row">
          <div>
            <p className="settings-action-label">Test provider</p>
            <p className="settings-action-hint">
              Run a quick health check against the configured local model
              runtime.
            </p>
          </div>
          <button
            className="btn-primary"
            onClick={() => providerTest.mutate()}
            disabled={providerTest.isPending}
          >
            {providerTest.isPending ? "Testing…" : "Run test"}
          </button>
        </div>

        {providerTest.isSuccess && (
          <div className="settings-result">
            <p className="status-success">✓ {providerTest.data.message}</p>
          </div>
        )}

        {providerTest.isError && (
          <div className="settings-result">
            <p className="status-error">
              {providerTest.error instanceof Error
                ? providerTest.error.message
                : "Provider test failed."}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
