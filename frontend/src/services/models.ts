import { z } from 'zod';

export const FREE_ROUTER = 'openrouter/free';
export const GEMINI_MODEL = 'gemini-3.5-flash-lite';
const generationConfig = z.discriminatedUnion('provider', [
  z.object({ provider: z.literal('ollama') }),
  z.object({ provider: z.literal('openrouter'), model: z.string(), api_key: z.string() }),
  z.object({ provider: z.literal('gemini'), model: z.string(), api_key: z.string() }),
]);
export type GenerationConfig = z.infer<typeof generationConfig>;
export type CloudConfig = Exclude<GenerationConfig, { provider: 'ollama' }>;

const catalog = z.object({
  models: z.array(z.object({ id: z.string(), name: z.string() })),
  api_key_configured: z.boolean(),
});
export type ModelCatalog = z.infer<typeof catalog>;

export async function getModels({ provider, signal }: { provider: CloudConfig['provider']; signal: AbortSignal }): Promise<ModelCatalog> {
  const response = await fetch(`/models/${provider}`, { signal });
  if (!response.ok) throw new Error('Could not load models.');
  return catalog.parse(await response.json());
}
