import { useAuth } from "@clerk/react";
import { useQuery } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { fetchOllamaModels, fetchProvider } from "./api";

const STORAGE_KEY = "rag-system.selected-ollama-model";
const EMPTY_MODELS: string[] = [];

export type OllamaModelContextValue = {
  models: string[];
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  isLoading: boolean;
  listsError: Error | null;
};

const OllamaModelContext = createContext<OllamaModelContextValue | null>(null);

export function OllamaModelProvider({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  const getTokenFn = useCallback(() => getToken(), [getToken]);

  const modelsQuery = useQuery({
    queryKey: ["ollama-models"],
    queryFn: () => fetchOllamaModels(getTokenFn),
  });

  const providerQuery = useQuery({
    queryKey: ["provider"],
    queryFn: () => fetchProvider(getTokenFn),
  });

  const models = modelsQuery.data?.models ?? EMPTY_MODELS;
  const defaultModel = providerQuery.data?.default_model ?? "";

  const [selectedModel, setSelectedState] = useState(
    () => localStorage.getItem(STORAGE_KEY) ?? "",
  );

  useEffect(() => {
    if (!models.length) {
      return;
    }
    const fallback =
      defaultModel && models.includes(defaultModel) ? defaultModel : models[0];
    const stored = localStorage.getItem(STORAGE_KEY);
    const next = stored && models.includes(stored) ? stored : fallback;
    setSelectedState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, [models, defaultModel]);

  const setSelectedModel = useCallback((model: string) => {
    setSelectedState(model);
    localStorage.setItem(STORAGE_KEY, model);
  }, []);

  const listsError =
    (modelsQuery.error as Error | null) ??
    (providerQuery.error as Error | null);

  const value = useMemo(
    (): OllamaModelContextValue => ({
      models,
      selectedModel,
      setSelectedModel,
      isLoading: modelsQuery.isLoading || providerQuery.isLoading,
      listsError,
    }),
    [
      models,
      selectedModel,
      setSelectedModel,
      modelsQuery.isLoading,
      providerQuery.isLoading,
      listsError,
    ],
  );

  return (
    <OllamaModelContext.Provider value={value}>
      {children}
    </OllamaModelContext.Provider>
  );
}

export function useOllamaModel() {
  const ctx = useContext(OllamaModelContext);
  if (!ctx) {
    throw new Error("useOllamaModel must be used within OllamaModelProvider");
  }
  return ctx;
}
