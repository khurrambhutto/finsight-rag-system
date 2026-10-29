import { useState, type FormEvent } from 'react';
import { uploadReport, type Report } from '../services/reports';

type Props = { onUploaded: (report: Report) => void };

export function UploadForm({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState('');
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setUploading(true);
    setError('');
    try {
      const report = await uploadReport(form);
      onUploaded(report);
      form.reset();
      setFilename('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Upload failed. Try again.');
    } finally { setUploading(false); }
  }

  return <section className="upload-panel" aria-labelledby="upload-heading">
    <div className="panel-heading"><span className="panel-icon" aria-hidden="true">↥</span><h2 id="upload-heading">Add a report</h2></div>
    <form onSubmit={event => void submit(event)}>
      <div className="field"><label htmlFor="company">Company</label><input id="company" name="company" required maxLength={200} placeholder="Microsoft" /></div>
      <div className="field"><label htmlFor="year">Report year</label><input id="year" name="year" type="number" min="1900" max={new Date().getFullYear() + 1} required placeholder="2024" /></div>
      <div className="field"><label htmlFor="file">PDF file</label><div className="file-picker"><input id="file" name="file" type="file" accept=".pdf,application/pdf" required onChange={event => setFilename(event.target.files?.[0]?.name ?? '')} /><span aria-hidden="true" className="file-button">Choose file</span><span className="chosen-file">{filename || 'No file selected'}</span></div></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="upload-button" disabled={uploading}>{uploading ? 'Uploading…' : 'Upload report'} <span aria-hidden="true">↗</span></button>
    </form>
  </section>;
}
