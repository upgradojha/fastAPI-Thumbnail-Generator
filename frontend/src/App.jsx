import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Aperture, ArrowDownToLine, ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronRight,
  CircleHelp, Clock3, CloudUpload, ExternalLink, FileImage, GalleryVerticalEnd,
  Image, Layers3, LoaderCircle, Menu, Plus, Radio, RotateCcw,
  Sparkles, UploadCloud, WandSparkles, X, Zap
} from 'lucide-react';
import { api, media } from './api';

const presets = [
  { id:'bold', name:'Bold & dramatic', eyebrow:'01 / HIGH IMPACT', desc:'Loud type. Cinematic contrast.', cls:'style-bold' },
  { id:'minimal', name:'Clean & minimal', eyebrow:'02 / REFINED', desc:'Editorial and effortless.', cls:'style-minimal' },
  { id:'vibrant', name:'Vibrant & energetic', eyebrow:'03 / PLAYFUL', desc:'Punchy colour. Big energy.', cls:'style-vibrant' },
];
const formats = [
  { id:'youtube', name:'YouTube', aspect:'16:9', size:'1280 × 720' },
  { id:'shorts', name:'Shorts', aspect:'9:16', size:'1080 × 1920' },
  { id:'square', name:'Square', aspect:'1:1', size:'1080 × 1080' },
];
const terminal = (status) => status === 'completed' || status === 'failed';

function Logo() {
  return <div className="brand"><div className="brand-symbol"><Aperture size={23} strokeWidth={2.4}/></div><div className="brand-name">framecraft<span className="brand-dot">.</span></div><span className="brand-suffix">studio</span></div>;
}
function Status({ status }) {
  const isActive = ['processing','pending'].includes(status);
  return <span className={`status status-${status || 'pending'}`}>{isActive ? <LoaderCircle size={12} className="spin"/> : <span className="tiny-status-dot"/>}{status === 'done' ? 'Ready' : status === 'completed' ? 'Complete' : status === 'failed' ? 'Failed' : status === 'processing' ? 'Creating' : 'Queued'}</span>;
}
function ThumbArt({ preset }) {
  return <div className={`style-art ${preset.cls}`}><div className="fake-orbit"/><div className="fake-card"><span>{preset.id === 'bold' ? 'MAKE IT' : preset.id === 'minimal' ? 'LESS IS' : 'GO BIG'}</span><strong>{preset.id === 'bold' ? 'POP!' : preset.id === 'minimal' ? 'MORE.' : 'TODAY'}</strong></div></div>;
}
function IntroIllustration() {
  return <div className="intro-graphic" aria-hidden="true"><div className="intro-glow"/><div className="floating-frame"><span className="frame-kicker">THE CREATOR EDIT</span><span className="frame-headline">MAKE<br/>THEM<br/><i>LOOK.</i></span><span className="frame-detail">NEW EPISODE / 001</span><div className="frame-ring"/></div><div className="floating-mark mark-one">✦</div><div className="floating-mark mark-two">✳</div></div>;
}
function EmptyState() {
  return <div className="empty-gallery"><div className="empty-icon"><Layers3 size={23}/></div><h3>Your next great thumbnail starts here.</h3><p>Upload a photo, describe the idea and choose a style. Your designs will appear here in real time.</p><div className="empty-steps"><span>01 &nbsp; Upload</span><ChevronRight size={14}/><span>02 &nbsp; Describe</span><ChevronRight size={14}/><span>03 &nbsp; Create</span></div></div>;
}

function DownloadLinks({ thumb, activeFormat, onFormat }) {
  return <div className="format-area"><div className="format-tabs">{formats.map(f => <button type="button" key={f.id} className={`format-pill ${activeFormat===f.id?'active':''}`} onClick={()=>onFormat(f.id)}>{f.name}<span>{f.aspect}</span></button>)}</div><div className="file-row"><span>{formats.find(f=>f.id===activeFormat)?.size} px • {activeFormat==='youtube'?'wide':activeFormat}</span><a href={media(thumb.variants?.[activeFormat])} target="_blank" rel="noreferrer" download={`framecraft-${thumb.style}-${activeFormat}.jpg`} className="download-link"><ArrowDownToLine size={16}/> Download <ExternalLink size={13}/></a></div></div>;
}
function ResultCard({ thumb }) {
  const [format, setFormat] = useState('youtube');
  const ready = thumb.status === 'done';
  return <article className="result-card"><div className="result-head"><div><span className="result-eyebrow">STYLE / {String(Math.max(1,presets.findIndex(p=>p.id===thumb.style)+1)).padStart(2,'0')}</span><h3>{thumb.style_label}</h3></div><Status status={thumb.status}/></div><div className={`result-image ${!ready ? 'pending-image':''} ${format}`}>
    {ready ? <img src={media(thumb.variants?.[format] || thumb.image_url)} alt={`${thumb.style_label} ${format} thumbnail`} loading="lazy"/> : <div className="pending-placeholder">{thumb.status==='failed' ? <X size={25}/> : <LoaderCircle size={24} className="spin"/>}<strong>{thumb.status==='failed' ? 'Generation failed' : 'Working on the details…'}</strong><span>{thumb.status==='failed' ? 'This style did not complete' : 'Composing your design'}</span></div>}
    {ready && <span className="preview-corner">{format.toUpperCase()} PREVIEW</span>}
  </div>{ready ? <DownloadLinks thumb={thumb} activeFormat={format} onFormat={setFormat}/> : thumb.error_message ? <p className="card-error">{thumb.error_message}</p> : <p className="render-note"><span className="skeleton-line"/>The studio is creating your design.</p>}</article>;
}
function UploadArea({ file, setFile, preview, disabled }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const choose = (next) => {
    if (!next) return;
    if (!['image/jpeg','image/png','image/webp'].includes(next.type)) { window.alert('Please select a JPG, PNG or WebP image.'); return; }
    if (next.size > 8*1024*1024) { window.alert('Please choose an image smaller than 8 MB.'); return; }
    setFile(next);
  };
  return <div className="upload-block"><input type="file" hidden ref={inputRef} accept="image/jpeg,image/png,image/webp" onChange={e=>choose(e.target.files?.[0])}/>
    <div role="button" tabIndex={0} className={`upload-box ${drag?'dragged':''} ${preview?'has-image':''}`} onClick={()=>!disabled&&inputRef.current?.click()} onKeyDown={e=>{if((e.key==='Enter'||e.key===' ')&&!disabled)inputRef.current?.click();}} onDragOver={e=>{e.preventDefault();setDrag(true);}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);if(!disabled)choose(e.dataTransfer.files?.[0]);}}>
      {preview ? <><img className="uploaded-picture" src={preview} alt="Uploaded reference"/><div className="uploaded-overlay"><RotateCcw size={18}/> Replace photo</div></> : <><div className="upload-circle"><UploadCloud size={25}/></div><div className="upload-title">Drop your reference photo here</div><div className="upload-description">or <span>browse files</span> from your computer</div><div className="upload-hint">JPEG, PNG, WEBP • MAX 8 MB</div></>}
    </div>{file && <div className="selected-file"><div className="file-chip"><FileImage size={16}/><span>{file.name}</span><span className="file-size">{(file.size/1024/1024).toFixed(2)} MB</span></div><button type="button" aria-label="Remove image" onClick={()=>{setFile(null);if(inputRef.current)inputRef.current.value='';}} disabled={disabled}><X size={16}/></button></div>}
  </div>;
}

export default function App() {
  const [view, setView] = useState('create');
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [selected, setSelected] = useState(['bold','minimal']);
  const [jobs, setJobs] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('demo');
  const [apiReady, setApiReady] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const preview = useMemo(()=>file ? URL.createObjectURL(file) : '',[file]);
  useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview);},[preview]);
  const active = jobs.find(job=>job.id===activeId) || null;
  const activeProcessing = active && !terminal(active.status);
  useEffect(()=>{
    api.health().then(h=>{setMode(h.generator);setApiReady(true);}).catch(()=>setApiReady(false));
    api.jobs().then(data=>{setJobs(data);if(data.length)setActiveId(data[0].id);}).catch(()=>{});
  }, []);
  useEffect(()=>{
    if(!activeId||!activeProcessing)return;
    return api.subscribe(activeId, (data)=>setJobs(prev=>[data,...prev.filter(x=>x.id!==data.id)]), (data)=>setJobs(prev=>[data,...prev.filter(x=>x.id!==data.id)]), ()=>{});
  },[activeId,activeProcessing]);

  const toggleStyle = id => setSelected(current=>current.includes(id) ? current.filter(x=>x!==id) : current.length < 3 ? [...current,id] : current);
  const generate = async (e) => {
    e.preventDefault();setError('');
    if(!file){setError('Please upload a reference photo first.');return;}
    if(description.trim().length < 5){setError('Describe your video in at least 5 characters.');return;}
    if(!selected.length){setError('Select at least one visual style.');return;}
    setLoading(true);
    try{
      const upload = await api.upload(file);
      const created = await api.create({reference_id:upload.reference_id,prompt:description.trim(),styles:selected});
      const job = await api.job(created.job_id);
      setJobs(prev=>[job,...prev.filter(j=>j.id!==job.id)]);
      setActiveId(job.id);setView('create');
    }catch(err){setError(err.message || 'Something went wrong');}
    finally{setLoading(false);}
  };
  const reset = () => {setFile(null);setDescription('');setSelected(['bold','minimal']);setError('');setView('create');window.scrollTo({top:0,behavior:'smooth'});};
  const history = jobs.filter(j=>j.status==='completed').length;
  const allThumbs = jobs.reduce((n,j)=>n+j.thumbnails.filter(t=>t.status==='done').length,0);

  return <div className="layout"><aside className={`sidebar ${menuOpen?'mobile-open':''}`}><div className="sidebar-top"><Logo/><button className="close-menu" onClick={()=>setMenuOpen(false)}><X size={20}/></button></div><div className="sidebar-label">WORKSPACE</div><nav className="nav"><button className={`nav-link ${view==='create'?'active':''}`} onClick={()=>{setView('create');setMenuOpen(false);}}><WandSparkles size={18}/>Create studio<ChevronRight size={16} className="nav-arrow"/></button><button className={`nav-link ${view==='library'?'active':''}`} onClick={()=>{setView('library');setMenuOpen(false);}}><GalleryVerticalEnd size={18}/>My creations<span className="nav-count">{jobs.length}</span></button></nav>
    <div className="sidebar-divider"/><div className="sidebar-label">STUDIO INSIGHTS</div><div className="sidebar-stat"><span>Completed projects</span><strong>{history.toString().padStart(2,'0')}</strong></div><div className="sidebar-stat"><span>Images generated</span><strong>{allThumbs.toString().padStart(2,'0')}</strong></div>
    <div className="sidebar-bottom"><div className="mini-promo"><div className="promo-stars">✳ <span>✦</span></div><strong>Better ideas.<br/>Better clicks.</strong><p>Let your visuals tell the story.</p><div className="promo-art">↗</div></div><div className="side-note"><CircleHelp size={17}/><span>Built for creators</span><span className="version">v1.0</span></div></div>
  </aside><div className="mobile-backdrop" onClick={()=>setMenuOpen(false)}/><div className="app-main"><header className="topbar"><div className="topbar-path"><button className="mobile-toggle" onClick={()=>setMenuOpen(true)}><Menu size={22}/></button>Workspace <ChevronRight size={14}/> <strong>{view==='create'?'Create studio':'My creations'}</strong></div><div className="topbar-right"><span className={`health-indicator ${apiReady?'':'offline'}`}><span/>{apiReady?'API connected':'API offline'}</span><div className="top-avatar">FC</div></div></header><main className="content">
    {view==='create' ? <>
      <section className="hero"><div className="hero-copy"><div className="small-intro"><span className="small-intro-star">✳</span> YOUR CREATIVE SIDEKICK <span className="tiny-line"/></div><h1>Make every<br/>frame <em>count.</em></h1><p>Turn your ideas into scroll-stopping thumbnails, in your signature style. Less editing, more creating.</p><div className="hero-facts"><span><Zap size={15}/> 3 creative directions</span><span><Layers3 size={15}/> 3 export formats</span></div></div><IntroIllustration/></section>
      <div className="section-heading"><div><span className="overline">THE CREATIVE PROCESS</span><h2>Let's make something <i>great.</i></h2></div><div className="section-ordinal">01 — 03</div></div>
      <form onSubmit={generate} className="studio-grid"><div className="form-left"><section className="panel upload-panel"><div className="step-heading"><div className="step-number">01</div><div><h3>Start with a face</h3><p>Add a reference image to make your thumbnail personal.</p></div><div className="panel-side-icon"><Image size={18}/></div></div><UploadArea file={file} setFile={setFile} preview={preview} disabled={loading}/></section>
      <section className="panel prompt-panel"><div className="step-heading"><div className="step-number">02</div><div><h3>Tell us your vision</h3><p>What is your video about? A little detail goes a long way.</p></div><div className="panel-side-icon"><Sparkles size={18}/></div></div><label htmlFor="prompt" className="input-label">YOUR CREATIVE BRIEF</label><textarea id="prompt" maxLength={1500} placeholder="e.g. Teaching FastAPI from scratch! Show a bold FASTAPI headline, a futuristic coding environment and a confident expression." value={description} onChange={e=>setDescription(e.target.value)} disabled={loading}/><div className="prompt-footer"><span><Sparkles size={14}/> Be specific to get better results</span><span>{description.length}/1500</span></div></section></div>
      <section className="panel styles-panel"><div className="step-heading"><div className="step-number">03</div><div><h3>Pick your aesthetic</h3><p>Choose up to three directions. Each one is uniquely generated.</p></div><div className="panel-side-icon"><Layers3 size={18}/></div></div><div className="style-choices">{presets.map(p=><button type="button" key={p.id} className={`style-choice ${selected.includes(p.id)?'selected':''}`} onClick={()=>toggleStyle(p.id)} disabled={loading} aria-pressed={selected.includes(p.id)}><ThumbArt preset={p}/><div className="style-text"><span className="style-eyebrow">{p.eyebrow}</span><strong>{p.name}</strong><span className="style-description">{p.desc}</span></div><span className="style-check">{selected.includes(p.id)&&<Check size={13} strokeWidth={3}/>}</span></button>)}</div><div className="styles-footer"><span><CheckCircle2 size={16}/> <strong>{selected.length} of 3</strong> styles selected</span><span>{selected.length * 3} export-ready formats</span></div>
      <div className="create-action">{error&&<div role="alert" className="error-alert"><X size={16}/>{error}</div>}<button className="generate-button" type="submit" disabled={loading}>{loading ? <><LoaderCircle size={19} className="spin"/> Uploading and preparing…</> : <><WandSparkles size={20}/> Generate {selected.length} thumbnail{selected.length===1?'':'s'} <ArrowRight size={19}/></>}</button><p className="below-action"><Sparkles size={13}/>{mode==='demo'?'Demo mode: local templates, no AI charges. Enable OpenAI in .env for real generation.':'AI mode enabled. Image generation may incur API charges.'}</p></div>
      </section></form>
      <section className="results-section" id="results"><div className="section-heading"><div><span className="overline">YOUR RESULTS</span><h2>Fresh off the <i>press.</i></h2></div>{active&&<Status status={active.status}/>}</div>{!active ? <EmptyState/> : <><div className="active-job-detail"><span className="job-title">{active.prompt}</span><span className="job-date">{new Date(active.created_at).toLocaleString()}</span></div><div className="results-grid">{active.thumbnails.map(t=><ResultCard thumb={t} key={t.id}/>)}</div><div className="results-bottom"><span>{terminal(active.status)?'Your creative round is complete.':'Your designs will appear one by one as they finish.'}</span><button type="button" onClick={reset}><Plus size={16}/> New creation</button></div></>}</section>
      </> : <section className="library-view"><button className="back-link" onClick={()=>setView('create')}><ArrowLeft size={17}/> Back to studio</button><span className="overline">YOUR CREATIVE LIBRARY</span><h1>Everything you've <em>made.</em></h1><p className="library-lead">Your projects are saved in the local database and stay available after a page refresh.</p>{jobs.length===0 ? <EmptyState/> : <div className="library-grid">{jobs.map(j=><button key={j.id} className="library-card" onClick={()=>{setActiveId(j.id);setView('create');setTimeout(()=>document.getElementById('results')?.scrollIntoView({behavior:'smooth'}),70);}}><div className="library-preview">{j.thumbnails.find(t=>t.status==='done') ? <img src={media(j.thumbnails.find(t=>t.status==='done').variants?.youtube)} alt="Thumbnail"/> : <div className="library-wait"><WandSparkles size={24}/></div>}</div><div className="library-description"><strong>{j.prompt}</strong><div className="library-meta"><Status status={j.status}/><span>{new Date(j.created_at).toLocaleDateString()}</span></div></div></button>)}</div>}</section>}
  </main><footer className="footer"><span>© 2026 Framecraft Studio</span><span>Made for the ideas worth clicking. <span className="footer-spark">✳</span></span></footer></div></div>;
}
