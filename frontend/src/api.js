// All API calls live in one file. Vite proxies /api -> FastAPI in development.
const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
export const media = (url) => !url ? '' : (url.startsWith('/') ? BASE + url : url);

async function request(path, options = {}) {
  let response;
  try { response = await fetch(BASE + path, options); }
  catch { throw new Error('Cannot reach the API. Is the backend running on port 8000?'); }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = result.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(x=>x.msg).join(', ') : `Request failed (${response.status})`);
  }
  return result;
}

export const api = {
  health: () => request('/api/health'),
  styles: () => request('/api/styles'),
  jobs: () => request('/api/jobs'),
  job: (id) => request(`/api/jobs/${id}`),
  async upload(file) {
    const data = new FormData();
    data.append('image', file);
    return request('/api/upload-headshot', { method:'POST', body:data });
  },
  create: (payload) => request('/api/jobs', {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload),
  }),
  subscribe(id, onUpdate, onDone, onError) {
    const events = new EventSource(BASE + `/api/jobs/${id}/events`);
    events.addEventListener('job_update', e => { try { onUpdate(JSON.parse(e.data)); } catch {} });
    events.addEventListener('job_completed', e => {
      try { onDone(JSON.parse(e.data)); } catch {}
      events.close();
    });
    events.onerror = () => { if(events.readyState !== EventSource.CLOSED) onError?.(); };
    return () => events.close();
  },
};
