import { useState, type FormEvent } from 'react';
import { askQuestion, type Answer } from '../services/questions';
import type { Report } from '../services/reports';
import { FREE_ROUTER, type GenerationConfig } from '../services/models';
import { ModelSettings } from './ModelSettings';

type Props = { reports: Report[] };
export function AskQuestion({ reports }: Props) {
  const [question, setQuestion] = useState('');
  const [reportId, setReportId] = useState('');
  const [result, setResult] = useState<Answer | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [generation, setGeneration] = useState<GenerationConfig>({ provider: 'openrouter', model: FREE_ROUTER, api_key: '' });
  const ready = reports.filter(report => report.status === 'ready');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true); setError(''); setResult(null);
    try { setResult(await askQuestion({ question, documentId: reportId, generation })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not answer the question.'); }
    finally { setLoading(false); }
  }
  return <section className="questions" aria-labelledby="question-heading">
    <h2 id="question-heading">Ask a question</h2>
    <form onSubmit={event => void submit(event)}>
      <ModelSettings value={generation} onChange={setGeneration} disabled={loading} />
      <div className="field"><label htmlFor="report-select">Report</label><select id="report-select" required value={reportId} onChange={event => setReportId(event.target.value)}><option value="">Select a report</option>{ready.map(report => <option key={report.id} value={report.id}>{report.company} {report.year} — {report.filename}</option>)}</select></div>
      <div className="field"><label htmlFor="question">Question</label><textarea id="question" required maxLength={2000} value={question} onChange={event => setQuestion(event.target.value)} placeholder="What was revenue in 2024?" /></div>
      <button className="upload-button ask-button" disabled={loading || !ready.length}>{loading ? 'Searching…' : 'Ask question'}</button>
    </form>
    {error && <p className="form-error" role="alert">{error}</p>}
    {result && <div className="answer" aria-live="polite"><h3>Answer</h3><p>{result.answer}</p>{result.citations.length > 0 && <><h3>Sources</h3>{result.citations.map((citation, index) => <article className="source" key={`${citation.document_id}-${citation.page}-${index}`}><a href={`/documents/${encodeURIComponent(citation.document_id)}/file#page=${citation.page}`} target="_blank" rel="noreferrer">Page {citation.page} ↗</a><pre>{citation.text}</pre></article>)}</>}
      <details><summary>Retrieved passages ({result.retrieved_passages.length})</summary>{result.retrieved_passages.map((passage, index) => <article className="source" key={`${passage.page}-${index}`}><a href={`/documents/${encodeURIComponent(passage.document_id)}/file#page=${passage.page}`} target="_blank" rel="noreferrer">Page {passage.page} ↗</a><pre>{passage.text}</pre></article>)}</details><p className="answer-model">Model: {result.model}</p></div>}
  </section>;
}
