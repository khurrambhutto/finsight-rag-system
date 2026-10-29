import { useEffect, useState } from 'react';
import { FREE_ROUTER, GEMINI_MODEL, getModels, type CloudConfig, type ModelCatalog } from '../services/models';

type CatalogState = { kind: 'loading' } | { kind: 'ready'; data: ModelCatalog } | { kind: 'error' };
type Props = { value: CloudConfig; onChange: (value: CloudConfig) => void };

export function CloudModelFields({ value, onChange }: Props) {
  const [catalog, setCatalog] = useState<CatalogState>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const provider = value.provider;
  useEffect(() => {
    const controller = new AbortController();
    setCatalog({ kind: 'loading' });
    void getModels({ provider, signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) setCatalog({ kind: 'ready', data });
    }).catch(() => {
      if (!controller.signal.aborted) setCatalog({ kind: 'error' });
    });
    return () => controller.abort();
  }, [provider, attempt]);

  const fallback = provider === 'gemini' ? { id: GEMINI_MODEL, name: 'Gemini 3.5 Flash-Lite' }
    : { id: FREE_ROUTER, name: 'Auto · Free models' };
  const availableModels = catalog.kind === 'ready' ? catalog.data.models : [fallback];
  const models = availableModels.some(model => model.id === value.model) ? availableModels
    : [...availableModels, { id: value.model, name: value.model }];
  const serverKey = catalog.kind === 'ready' && catalog.data.api_key_configured;
  const providerName = provider === 'gemini' ? 'Gemini' : 'OpenRouter';
  const keyUrl = provider === 'gemini' ? 'https://aistudio.google.com/apikey' : 'https://openrouter.ai/settings/keys';

  return <>
    <div className="field"><div className="field-label"><label htmlFor="model-select">{provider === 'openrouter' ? 'Free model' : 'Model'}</label>{provider === 'openrouter' && <button type="button" className="retry" onClick={() => setAttempt(current => current + 1)} disabled={catalog.kind === 'loading'} aria-label="Refresh free models">↻</button>}</div><select id="model-select" value={value.model} onChange={event => onChange({ ...value, model: event.target.value })}>{models.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}</select></div>
    <div className="field"><div className="field-label"><label htmlFor="provider-key">API key</label><a href={keyUrl} target="_blank" rel="noreferrer">Get key ↗</a></div><input id="provider-key" type="password" autoComplete="off" spellCheck={false} value={value.api_key} onChange={event => onChange({ ...value, api_key: event.target.value })} required={catalog.kind === 'ready' && !serverKey} placeholder={serverKey ? 'Using server key' : `Paste ${providerName} key`} /></div>
    {catalog.kind === 'loading' && <p className="model-catalog-state" role="status">Loading models…</p>}
    {catalog.kind === 'error' && <p className="form-error model-catalog-state" role="alert">Could not load the model list. You can still use the selected model. <button type="button" className="retry" onClick={() => setAttempt(current => current + 1)}>Try again</button></p>}
  </>;
}
