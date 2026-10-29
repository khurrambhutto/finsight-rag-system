import { useEffect, useState } from 'react';
import { AskQuestion } from './components/AskQuestion';
import { Passages } from './components/Passages';
import { UploadForm } from './components/UploadForm';
import { ReportLibrary } from './components/ReportLibrary';
import { getReports, type Report } from './services/reports';

export function App() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<Report | null>(null);

  async function loadReports() {
    setLoading(true);
    try { setReports(await getReports()); setError(false); }
    catch { setError(true); }
    finally { setLoading(false); }
  }
  useEffect(() => { void loadReports(); }, []);
  useEffect(() => { const timer = window.setInterval(() => { void getReports().then(setReports).catch(() => {}); }, 3000); return () => window.clearInterval(timer); }, []);

  return <div className="app-shell">
    <header className="sidebar"><div className="brand"><span className="brand-mark" aria-hidden="true"><span></span><span></span><span></span></span><span>FinSight<span className="brand-ai"> AI</span></span></div><div className="nav-current"><span className="nav-icon" aria-hidden="true">▤</span> Reports</div><div className="sidebar-bottom"><span className="sidebar-dot"></span> Research workspace</div></header>
    <main className="main-content"><div className="topline"><span>Workspace</span><span className="topline-divider">/</span><span>Reports</span></div>
      <div className="page-heading"><div><h1>Reports</h1></div><span className="report-count">{reports.length} {reports.length === 1 ? 'report' : 'reports'}</span></div>
      <AskQuestion reports={reports} />
      <div className="workspace">{selected ? <Passages report={selected} onClose={() => setSelected(null)} onRefresh={() => void loadReports()} /> : <ReportLibrary reports={reports} loading={loading} error={error} onRetry={() => void loadReports()} onSelect={setSelected} />}<UploadForm onUploaded={report => setReports(previous => [report, ...previous])} /></div>
    </main>
  </div>;
}
