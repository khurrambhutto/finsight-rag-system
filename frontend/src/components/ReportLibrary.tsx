import type { Report } from '../services/reports';

type Props = { reports: Report[]; loading: boolean; error: boolean; onRetry: () => void; onSelect: (report: Report) => void };

export function ReportLibrary({ reports, loading, error, onRetry, onSelect }: Props) {
  return <section className="library" aria-label="Reports">
    <div className="library-heading"><h2>All reports</h2><span>{reports.length}</span></div>
    {loading ? <div className="library-message">Loading reports…</div> : error ? <div className="library-message"><p>Could not load reports. Check that the backend is running.</p><button className="retry" onClick={onRetry}>Try again</button></div> : reports.length === 0 ? <div className="library-message empty-state"><div className="empty-document" aria-hidden="true"><span></span><span></span><span></span></div><h3>No reports yet</h3></div> : <div className="report-list">
      <div className="list-heading" aria-hidden="true"><span>Report</span><span>Added</span><span>Status</span></div>
      {reports.map(report => <article className="report" key={report.id}>
        <div className="report-main"><span className="document-icon" aria-hidden="true">PDF</span><div className="report-name"><h3><button className="report-link" onClick={() => onSelect(report)}>{report.company} <span>{report.year}</span></button></h3><p>{report.filename}</p></div></div>
        <time dateTime={report.uploaded_at}>{new Date(report.uploaded_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</time>
        <span className={`status ${report.status}`}><span aria-hidden="true" className="status-dot"></span>{report.status}</span>
      </article>)}
    </div>}
  </section>;
}
