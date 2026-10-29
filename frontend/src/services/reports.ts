import { z } from 'zod';

const reportSchema = z.object({
  id: z.string(), filename: z.string(), company: z.string(), year: z.number(),
  uploaded_at: z.string(), status: z.enum(['pending', 'processing', 'ready', 'failed']),
});
export type Report = z.infer<typeof reportSchema>;

export async function getReports(): Promise<Report[]> {
  const response = await fetch('/documents');
  if (!response.ok) throw new Error('Could not load reports.');
  return z.array(reportSchema).parse(await response.json());
}

export async function uploadReport(form: HTMLFormElement): Promise<Report> {
  const response = await fetch('/documents', { method: 'POST', body: new FormData(form) });
  if (!response.ok) {
    const body: unknown = await response.json();
    const parsed = z.object({ detail: z.string() }).safeParse(body);
    throw new Error(parsed.success ? parsed.data.detail : 'Upload failed. Check the form and try again.');
  }
  return reportSchema.parse(await response.json());
}

const chunkSchema = z.object({ id: z.string(), document_id: z.string(), page: z.number(), section: z.string().nullable(), content_type: z.string(), text: z.string() });
const extractionSchema = z.object({ document: z.object({ status: z.string(), error: z.string().nullable() }), chunks: z.array(chunkSchema) });
export type Extraction = z.infer<typeof extractionSchema>;
export async function getExtraction(id: string): Promise<Extraction> {
  const response = await fetch(`/documents/${encodeURIComponent(id)}/chunks`);
  if (!response.ok) throw new Error('Could not load passages.');
  return extractionSchema.parse(await response.json());
}
export async function processReport(id: string): Promise<void> {
  const response = await fetch(`/documents/${encodeURIComponent(id)}/process`, { method: 'POST' });
  if (!response.ok) throw new Error('Could not start processing.');
}
