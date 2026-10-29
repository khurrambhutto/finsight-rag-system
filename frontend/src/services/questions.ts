import { z } from 'zod';
import type { GenerationConfig } from './models';

const passage = z.object({ document_id: z.string(), page: z.number(), text: z.string(), section: z.string().nullable(), content_type: z.string(), score: z.number() });
const answer = z.object({ answer: z.string(), citations: z.array(passage), retrieved_passages: z.array(passage), model: z.string() });
export type Answer = z.infer<typeof answer>;
export async function askQuestion({ question, documentId, generation }: { question: string; documentId: string; generation: GenerationConfig }): Promise<Answer> {
  const response = await fetch('/questions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, document_id: documentId, generation }) });
  if (!response.ok) {
    const body: unknown = await response.json();
    const detail = z.object({ detail: z.string() }).safeParse(body);
    throw new Error(detail.success ? detail.data.detail : 'Could not answer the question.');
  }
  return answer.parse(await response.json());
}
