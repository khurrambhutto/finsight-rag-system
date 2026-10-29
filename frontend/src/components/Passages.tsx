import { useEffect, useState } from 'react';
import { getExtraction, processReport, type Extraction, type Report } from '../services/reports';

type Props = { report: Report; onClose: () => void; onRefresh: () => void };
export function Passages({ report, onClose, onRefresh }: Props) {
  const [data, setData] = useState<Extraction | null>(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  useEffect(() => {
    let active = true;
    async function load() {
      try { const result = await getExtraction(report.id); if (active) { setData(result); setError(''); } }
      catch { if (active) setError('Could not load passages.'); }
    }
    void load();
    const timer = window.setInterval(() => void load(), 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, [report.id]);
  async function start() {
    setStarting(true); setError('');
    try { await processReport(report.id); setData(await getExtraction(report.id)); onRefresh(); }
    catch { setError('Could not start processing. Try again.'); }
    finally { setStarting(false); }
  }
  return <section className="passages" aria-labelledby="passages-heading">
    <div className="passages-title"><div><button className="back-button" onClick={onClose}>← All reports</button><h2 id="passages-heading">{report.company} {report.year}</h2></div><a href={`/documents/${encodeURIComponent(report.id)}/file`} target="_blank" rel="noreferrer">Open PDF ↗</a></div>
    {error && <p role="alert" className="form-error">{error}</p>}
    {!data ? <p>Loading passages…</p> : <>
      <div className="passage-summary"><span>{data.chunks.length} passages</span><span className={`status ${data.document.status}`}>{data.document.status}</span>{data.document.status !== 'processing' && <button className="process-button" disabled={starting} onClick={() => void start()}>{data.document.status === 'pending' ? 'Process report' : 'Process again'}</button>}</div>
      {data.document.error && <p role="alert" className="form-error">{data.document.error}</p>}
      {data.chunks.map(chunk => <article className="passage" key={chunk.id}><div className="passage-meta"><a href={`/documents/${encodeURIComponent(report.id)}/file#page=${chunk.page}`} target="_blank" rel="noreferrer">Page {chunk.page} ↗</a><span>{chunk.content_type}</span>{chunk.section && <span>{chunk.section}</span>}</div><pre>{chunk.text}</pre></article>)}
    </>}
  </section>;
}
