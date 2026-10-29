import { FREE_ROUTER, GEMINI_MODEL, type GenerationConfig } from '../services/models';
import { CloudModelFields } from './CloudModelFields';

type Props = { value: GenerationConfig; onChange: (value: GenerationConfig) => void; disabled: boolean };

export function ModelSettings({ value, onChange, disabled }: Props) {
  return <fieldset className="generation-settings" disabled={disabled} aria-label="Answer model">
    <div className="field"><label htmlFor="provider-select">Provider</label><select id="provider-select" value={value.provider} onChange={event => {
      switch (event.target.value) {
        case 'openrouter': onChange({ provider: 'openrouter', model: FREE_ROUTER, api_key: '' }); break;
        case 'gemini': onChange({ provider: 'gemini', model: GEMINI_MODEL, api_key: '' }); break;
        case 'ollama': onChange({ provider: 'ollama' }); break;
      }
    }}><option value="openrouter">OpenRouter · Free</option><option value="gemini">Gemini · Google</option><option value="ollama">Ollama · Local</option></select></div>
    {value.provider !== 'ollama' && <CloudModelFields key={value.provider} value={value} onChange={onChange} />}
  </fieldset>;
}
