import React, { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../api";
import {
  RefreshCw, AlertTriangle, CheckCircle, Clock, XCircle,
  RotateCcw, Ban, Layers, Upload, FileText, Send, Info,
  ChevronRight, Filter, Zap, Users
} from "lucide-react";

interface Job {
  id:string; category:string; status:string; to_email:string; to_name:string;
  subject:string; scheduled_at:string|null; sent_at:string|null; created_at:string;
  attempt_count:number; last_error:string|null; is_simulated:boolean;
}

// Status → color/badge mapping
const SC:Record<string,string> = {accepted:"#16a34a",simulated:"#7c3aed",queued:"#2563eb",pending:"#d97706",failed:"#dc2626",retrying:"#d97706",cancelled:"#64748b"};
const SBADGE:Record<string,string> = {accepted:"badge-green",simulated:"badge-violet",queued:"badge-blue",pending:"badge-warn",failed:"badge-danger",retrying:"badge-warn",cancelled:"badge-gray"};
const SICON:Record<string,React.ElementType> = {accepted:CheckCircle,simulated:Zap,queued:Clock,pending:Clock,failed:XCircle,retrying:RotateCcw,cancelled:Ban};

// Light-theme helper styles
const LT = {
  input: {
    background:"#fff",border:"1px solid #e2e5ed",borderRadius:8,color:"#0f172a",
    padding:"9px 12px",fontSize:13,fontFamily:"inherit",boxSizing:"border-box" as const,
    width:"100%",
  } as React.CSSProperties,
  select: {
    background:"#fff",border:"1px solid #e2e5ed",borderRadius:8,color:"#0f172a",
    padding:"9px 12px",fontSize:13,fontFamily:"inherit",width:"100%",
    appearance:"none" as const,
    backgroundImage:"url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\")",
    backgroundRepeat:"no-repeat",backgroundPosition:"right 12px center",paddingRight:34,
  } as React.CSSProperties,
  label: { fontSize:12,fontWeight:600,color:"#475569",textTransform:"uppercase",letterSpacing:"0.05em",display:"block",marginBottom:4 } as React.CSSProperties,
  card: { background:"#fff",border:"1px solid #e2e5ed",borderRadius:14,padding:"18px 20px",boxShadow:"0 1px 3px rgba(15,23,42,0.06)" } as React.CSSProperties,
};

function Alert({type,children}:{type:"error"|"info"|"success"|"warn";children:React.ReactNode}){
  const cfg = {
    error:  {bg:"#fef2f2",color:"#dc2626",border:"#fecaca",Icon:AlertTriangle},
    success:{bg:"#f0fdf4",color:"#16a34a",border:"#bbf7d0",Icon:CheckCircle},
    info:   {bg:"#f0f9ff",color:"#0284c7",border:"#bae6fd",Icon:Info},
    warn:   {bg:"#fffbeb",color:"#d97706",border:"#fde68a",Icon:AlertTriangle},
  }[type];
  return(
    <div style={{display:"flex",gap:9,alignItems:"flex-start",background:cfg.bg,color:cfg.color,border:`1px solid ${cfg.border}`,borderRadius:10,padding:"11px 14px",fontSize:13,fontWeight:500,marginBottom:12}}>
      <cfg.Icon size={14} style={{flexShrink:0,marginTop:1}}/>{children}
    </div>
  );
}

function PrimaryBtn({onClick,disabled,children,style}:{onClick?:()=>void;disabled?:boolean;children:React.ReactNode;style?:React.CSSProperties}){
  return(
    <button onClick={onClick} disabled={disabled}
      style={{background:"#2563eb",color:"#fff",border:"none",borderRadius:9,padding:"10px 20px",fontSize:13,fontWeight:700,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:6,boxShadow:"0 2px 6px rgba(37,99,235,0.3)",opacity:disabled?0.5:1,transition:"all 0.15s",...style}}>
      {children}
    </button>
  );
}

// ── Main EmailCenter ──────────────────────────────────────────────────────────
export default function EmailCenter({token}:{token:string}){
  const [stats,setStats]   = useState<Record<string,number>|null>(null);
  const [jobs,setJobs]     = useState<Job[]>([]);
  const [total,setTotal]   = useState(0);
  const [fs,setFs]         = useState("");
  const [loading,setLoading] = useState(false);
  const [err,setErr]       = useState("");
  const [smtpInfo,setSmtpInfo] = useState<any>(null);
  const [tab,setTab]       = useState<"jobs"|"import"|"pipeline"|"templates"|"bulk">("jobs");

  const load = useCallback(async()=>{
    setLoading(true);setErr("");
    try{
      const [s,j,cfg] = await Promise.all([
        apiFetch("/api/emails/jobs/stats",token),
        apiFetch(`/api/emails/jobs?limit=50${fs?`&status=${fs}`:""}`,token),
        apiFetch("/api/emails/config",token),
      ]);
      setStats(s);setJobs(j.jobs);setTotal(j.total);setSmtpInfo(cfg);
    }catch(e:any){setErr(e.message);}
    finally{setLoading(false);}
  },[token,fs]);

  useEffect(()=>{load();},[load]);

  const TABS = [
    {id:"jobs"      as const, label:"Job Queue",           Icon:Layers},
    {id:"import"    as const, label:"Import Candidates",   Icon:Upload},
    {id:"pipeline"  as const, label:"Pipeline Automation", Icon:Zap},
    {id:"templates" as const, label:"Templates",           Icon:FileText},
    {id:"bulk"      as const, label:"Bulk Send",           Icon:Send},
  ];

  return(
    <div style={{paddingBottom:40}}>
      {/* Sub-header */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:20,flexWrap:"wrap",gap:10}}>
        <div>
          <p style={{margin:0,color:"#64748b",fontSize:13}}>
            Manage email delivery queues, candidate invitations, and batch campaigns.
          </p>
        </div>
        <button onClick={load} disabled={loading}
          style={{background:"#fff",border:"1px solid #e2e5ed",color:"#475569",borderRadius:9,padding:"8px 16px",fontSize:13,fontWeight:600,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:6,boxShadow:"0 1px 3px rgba(15,23,42,0.05)"}}>
          <RefreshCw size={13} style={{animation:loading?"spin 1s linear infinite":"none"}}/>{loading?"Refreshing…":"Refresh"}
        </button>
      </div>

      {err && <Alert type="error">{err}</Alert>}

      {/* Stats cards */}
      {stats && (
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(120px,1fr))",gap:10,marginBottom:20}}>
          {Object.entries(stats).map(([k,v])=>{
            const color = SC[k]||"#475569";
            const active = fs===k;
            return(
              <div key={k} onClick={()=>setFs(fs===k?"":k)}
                style={{...LT.card,cursor:"pointer",padding:"14px 16px",
                  borderColor:active?color:"#e2e5ed",
                  boxShadow:active?`0 0 0 3px ${color}22, 0 1px 3px rgba(15,23,42,0.06)`:"0 1px 3px rgba(15,23,42,0.06)",
                  transform:active?"translateY(-1px)":"none",transition:"all 0.15s",
                }}>
                <div style={{fontSize:24,fontWeight:800,color,lineHeight:1}}>{v}</div>
                <div style={{fontSize:11,fontWeight:600,color:"#64748b",textTransform:"capitalize",marginTop:5}}>{k}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tabs */}
      <div style={{display:"flex",gap:2,background:"#f1f5f9",border:"1px solid #e2e5ed",borderRadius:10,padding:4,marginBottom:20,flexWrap:"wrap"}}>
        {TABS.map(({id,label,Icon})=>(
          <button key={id} onClick={()=>setTab(id)}
            style={{display:"inline-flex",alignItems:"center",gap:6,padding:"7px 14px",borderRadius:7,fontSize:13,fontWeight:tab===id?700:500,cursor:"pointer",border:"none",fontFamily:"inherit",transition:"all 0.15s",
              background:tab===id?"#fff":"transparent",
              color:tab===id?"#2563eb":"#64748b",
              boxShadow:tab===id?"0 1px 3px rgba(15,23,42,0.08)":"none",
            }}>
            <Icon size={13}/>{label}
          </button>
        ))}
      </div>

      {tab==="jobs"      && <JobsTab jobs={jobs} total={total} fs={fs} setFs={setFs} token={token} reload={load}/>}
      {tab==="import"    && <ImportTab token={token} onDone={()=>setTab("pipeline")}/>}
      {tab==="pipeline"  && <PipelineTab token={token} reloadQueue={load}/>}
      {tab==="templates" && <TemplatesTab token={token}/>}
      {tab==="bulk"      && <BulkTab token={token}/>}

      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

// ── Email Preview Modal ───────────────────────────────────────────────────────
function PreviewModal({jobId,token,onClose}:{jobId:string;token:string;onClose:()=>void}){
  const [data,setData]=useState<any>(null);
  const [loading,setLoading]=useState(true);
  useEffect(()=>{
    apiFetch(`/api/emails/jobs/${jobId}/preview`,token)
      .then(setData)
      .catch((e)=>setData({error:e.message}))
      .finally(()=>setLoading(false));
  },[jobId,token]);

  return(
    <div style={{position:"fixed",inset:0,background:"rgba(15,23,42,0.6)",zIndex:999,display:"flex",alignItems:"center",justifyContent:"center",padding:20}}>
      <div style={{background:"#fff",borderRadius:16,maxWidth:680,width:"100%",maxHeight:"90vh",display:"flex",flexDirection:"column",boxShadow:"0 20px 40px rgba(0,0,0,0.2)",overflow:"hidden"}}>
        <div style={{padding:"16px 20px",borderBottom:"1px solid #e2e5ed",display:"flex",alignItems:"center",justifyContent:"space-between",background:"#f8f9fc"}}>
          <div>
            <div style={{fontWeight:700,fontSize:15,color:"#0f172a"}}>{data?.subject||"Email Preview"}</div>
            <div style={{fontSize:12,color:"#64748b"}}>To: {data?.to_name} &lt;{data?.to_email}&gt;</div>
          </div>
          <button onClick={onClose} style={{background:"#f1f5f9",border:"none",borderRadius:8,padding:"6px 12px",fontSize:13,fontWeight:700,cursor:"pointer",color:"#64748b"}}>
            Close
          </button>
        </div>
        <div style={{flex:1,overflowY:"auto",padding:20,background:"#fff"}}>
          {loading ? (
            <div style={{padding:40,textAlign:"center",color:"#64748b"}}>Rendering email preview…</div>
          ) : data?.error ? (
            <div style={{color:"#dc2626"}}>{data.error}</div>
          ) : (
            <div dangerouslySetInnerHTML={{__html:data.html_body}}/>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Job Queue ─────────────────────────────────────────────────────────────────
function JobsTab({jobs,total,fs,setFs,token,reload}:any){
  const [previewJobId,setPreviewJobId]=useState<string|null>(null);

  async function retry(id:string){
    try{await apiFetch(`/api/emails/jobs/${id}/retry`,token,{method:"POST"});reload();}
    catch(e:any){alert(e.message);}
  }

  return(
    <div>
      {previewJobId && <PreviewModal jobId={previewJobId} token={token} onClose={()=>setPreviewJobId(null)}/>}

      <div style={{display:"flex",gap:10,marginBottom:14,flexWrap:"wrap",alignItems:"center"}}>
        <Filter size={13} style={{color:"#94a3b8"}}/>
        <select value={fs} onChange={e=>setFs(e.target.value)} style={{...LT.select,width:"auto",minWidth:150}}>
          <option value="">All statuses</option>
          {["queued","simulated","accepted","failed","retrying","cancelled","pending"].map(s=><option key={s} value={s}>{s}</option>)}
        </select>
        <span style={{color:"#94a3b8",fontSize:12,marginLeft:"auto"}}>{total} total jobs</span>
      </div>

      {jobs.length===0 && <Alert type="info">No email jobs yet. Upload candidates or use Quick Send to create jobs.</Alert>}

      <div style={{background:"#fff",border:"1px solid #e2e5ed",borderRadius:14,overflow:"hidden",boxShadow:"0 1px 3px rgba(15,23,42,0.06)"}}>
        {jobs.length>0 && (
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead>
              <tr style={{background:"#f8f9fc"}}>
                {["Status","Recipient","Subject","Category","Date","Actions"].map(h=>(
                  <th key={h} style={{textAlign:"left",fontSize:11,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.06em",color:"#94a3b8",padding:"10px 14px",borderBottom:"1px solid #e2e5ed"}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map((j:Job)=>{
                const Icon = SICON[j.status]||Clock;
                return(
                  <tr key={j.id} style={{borderBottom:"1px solid #f1f5f9",transition:"background 0.1s"}}
                    onMouseEnter={e=>(e.currentTarget.style.background="#f8f9fc")}
                    onMouseLeave={e=>(e.currentTarget.style.background="transparent")}>
                    <td style={{padding:"12px 14px",verticalAlign:"middle"}}>
                      <span className={`badge ${SBADGE[j.status]||"badge-gray"}`} style={{fontSize:11}}>
                        <Icon size={10}/>{j.status}{j.is_simulated?" ·sim":""}
                      </span>
                    </td>
                    <td style={{padding:"12px 14px",verticalAlign:"middle"}}>
                      <div style={{fontWeight:600,fontSize:13,color:"#0f172a"}}>{j.to_name||j.to_email}</div>
                      <div style={{color:"#94a3b8",fontSize:11}}>{j.to_email}</div>
                    </td>
                    <td style={{padding:"12px 14px",verticalAlign:"middle",maxWidth:260}}>
                      <div style={{fontWeight:500,fontSize:13,color:"#0f172a",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{j.subject}</div>
                      {j.last_error&&<div style={{color:"#dc2626",fontSize:11,marginTop:2}}>{j.last_error}</div>}
                    </td>
                    <td style={{padding:"12px 14px",verticalAlign:"middle"}}>
                      <span style={{fontSize:12,color:"#64748b"}}>{j.category.replaceAll("_"," ")}</span>
                    </td>
                    <td style={{padding:"12px 14px",verticalAlign:"middle",whiteSpace:"nowrap",color:"#64748b",fontSize:12}}>
                      {new Date(j.created_at).toLocaleDateString()}
                    </td>
                    <td style={{padding:"12px 14px",verticalAlign:"middle",whiteSpace:"nowrap",display:"flex",gap:6}}>
                      <button onClick={()=>setPreviewJobId(j.id)}
                        style={{background:"#eff4ff",border:"1px solid #bfdbfe",color:"#2563eb",borderRadius:7,padding:"5px 10px",fontSize:12,fontWeight:600,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:4}}>
                        👁 View Email
                      </button>
                      {j.status==="failed"&&(
                        <button onClick={()=>retry(j.id)}
                          style={{background:"#fff",border:"1px solid #e2e5ed",color:"#475569",borderRadius:7,padding:"5px 10px",fontSize:12,fontWeight:600,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:4}}>
                          <RotateCcw size={11}/>Retry
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Import Tab ────────────────────────────────────────────────────────────────
function ImportTab({token,onDone}:{token:string;onDone?:()=>void}){
  const [result,setResult]   = useState<any>(null);
  const [uploading,setUploading] = useState(false);
  const [err,setErr]         = useState("");
  const [selected,setSelected] = useState<Set<string>>(new Set());
  const [jobRole,setJobRole] = useState("Full Stack Engineer");
  const [title,setTitle]     = useState("Voice AI & Full-Stack System Design");
  const [meetLink,setMeetLink] = useState("https://meet.google.com/xyz-voice-hire");
  const [deadline,setDeadline] = useState("48 hours");
  const [link,setLink]       = useState("https://portal.voicehire.ai/submit");
  const [sendInv,setSendInv] = useState(true);
  const [confirming,setConfirming] = useState(false);
  const [done,setDone]       = useState<any>(null);

  async function upload(e:React.ChangeEvent<HTMLInputElement>){
    const file=e.target.files?.[0]; if(!file) return;
    setUploading(true);setErr("");setResult(null);setDone(null);setSelected(new Set());
    try{
      const fd=new FormData();fd.append("file",file);
      const data=await apiFetch("/api/emails/import/upload",token,{method:"POST",body:fd});
      setResult(data);
      setSelected(new Set(data.candidates.map((c:any)=>c.id)));
    }catch(e:any){setErr(e.message);}
    finally{setUploading(false);}
  }

  async function loadSample(){
    setUploading(true);setErr("");setResult(null);setDone(null);
    try{
      const data=await apiFetch("/api/emails/import/sample",token,{method:"POST"});
      setResult(data);
      setSelected(new Set(data.candidates.map((c:any)=>c.id)));
    }catch(e:any){setErr(e.message);}
    finally{setUploading(false);}
  }

  function toggle(id:string){setSelected(s=>{const n=new Set(s);n.has(id)?n.delete(id):n.add(id);return n;});}
  function toggleAll(){
    if(!result) return;
    if(selected.size===result.candidates.length) setSelected(new Set());
    else setSelected(new Set(result.candidates.map((c:any)=>c.id)));
  }

  async function confirm(){
    if(!result||selected.size===0) return;
    setConfirming(true);
    try{
      const data=await apiFetch("/api/emails/import/confirm",token,{method:"POST",
        body:JSON.stringify({
          import_id:result.import_id,
          send_invitations:sendInv,
          job_role:jobRole,
          assessment_title:title,
          deadline,
          assessment_link:link,
          meeting_link:meetLink,
          candidate_ids:Array.from(selected)
        })});
      setDone(data);
      if(onDone) onDone();
    }catch(e:any){setErr(e.message);}
    finally{setConfirming(false);}
  }

  return(
    <div style={LT.card}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:6,flexWrap:"wrap",gap:8}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <Upload size={16} style={{color:"#2563eb"}}/>
          <h3 style={{margin:0,fontSize:15,fontWeight:700,color:"#0f172a"}}>Import Candidates &amp; Assign Tasks</h3>
        </div>
        <button onClick={loadSample} disabled={uploading}
          style={{background:"#eff4ff",border:"1px solid #bfdbfe",color:"#2563eb",borderRadius:8,padding:"7px 14px",fontSize:12,fontWeight:700,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:6}}>
          <Zap size={13}/>{uploading?"Loading…":"⚡ 1-Click Load Sample Excel"}
        </button>
      </div>
      <p style={{color:"#64748b",fontSize:13,marginBottom:18}}>
        Upload your candidates Excel/CSV or load sample candidates. Each candidate receives an invitation email with their assigned task, Google Meet link, and submission portal link.
      </p>

      <div style={{display:"flex",gap:10,marginBottom:18,flexWrap:"wrap"}}>
        <label style={{display:"inline-flex",alignItems:"center",gap:8,background:"#2563eb",color:"#fff",borderRadius:9,padding:"10px 20px",cursor:"pointer",fontSize:13,fontWeight:700,boxShadow:"0 2px 6px rgba(37,99,235,0.3)"}}>
          <Upload size={14}/>{uploading?"Uploading…":"Choose Excel / CSV File"}
          <input type="file" accept=".csv,.xlsx,.xls" onChange={upload} style={{display:"none"}} disabled={uploading}/>
        </label>
      </div>

      {err && <Alert type="error">{err}</Alert>}

      {result && !done && (
        <div>
          {/* Summary pills */}
          <div style={{display:"flex",gap:10,flexWrap:"wrap",marginBottom:18}}>
            {[
              {label:"Valid Candidates",val:result.valid_count,color:"#16a34a",bg:"#f0fdf4",border:"#bbf7d0"},
              {label:"Invalid Rows",val:result.invalid_count,color:"#dc2626",bg:"#fef2f2",border:"#fecaca"},
              {label:"Duplicates",val:result.duplicate_count,color:"#d97706",bg:"#fffbeb",border:"#fde68a"},
            ].map(({label,val,color,bg,border})=>(
              <div key={label} style={{background:bg,border:`1px solid ${border}`,borderRadius:10,padding:"12px 18px",textAlign:"center"}}>
                <div style={{fontSize:22,fontWeight:800,color}}>{val}</div>
                <div style={{fontSize:11,fontWeight:600,color:"#64748b",marginTop:3}}>{label}</div>
              </div>
            ))}
          </div>

          {/* Candidate selection table */}
          {result.candidates.length>0 && (
            <div style={{background:"#f8f9fc",border:"1px solid #e2e5ed",borderRadius:12,overflow:"hidden",marginBottom:18}}>
              <div style={{padding:"10px 16px",borderBottom:"1px solid #e2e5ed",display:"flex",alignItems:"center",gap:10,background:"#fff"}}>
                <input type="checkbox" checked={selected.size===result.candidates.length} onChange={toggleAll} style={{width:15,height:15,cursor:"pointer",accentColor:"#2563eb"}}/>
                <span style={{fontWeight:700,fontSize:13,color:"#0f172a"}}>
                  <Users size={13} style={{display:"inline",marginRight:5}}/>
                  Select Candidates to Assign &amp; Email ({selected.size}/{result.candidates.length})
                </span>
              </div>
              {result.candidates.map((c:any)=>(
                <div key={c.id} onClick={()=>toggle(c.id)}
                  style={{display:"flex",alignItems:"center",gap:12,padding:"10px 16px",borderBottom:"1px solid #f1f5f9",cursor:"pointer",
                    background:selected.has(c.id)?"#eff4ff":"transparent",transition:"background 0.12s"}}>
                  <input type="checkbox" checked={selected.has(c.id)} onChange={()=>toggle(c.id)} onClick={e=>e.stopPropagation()} style={{width:15,height:15,cursor:"pointer",flexShrink:0,accentColor:"#2563eb"}}/>
                  <div style={{width:34,height:34,borderRadius:"50%",background:"#eff4ff",display:"flex",alignItems:"center",justifyContent:"center",color:"#2563eb",fontWeight:700,fontSize:13,flexShrink:0}}>
                    {c.name.charAt(0).toUpperCase()}
                  </div>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontWeight:600,fontSize:13,color:"#0f172a"}}>{c.name}</div>
                    <div style={{color:"#64748b",fontSize:12}}>{c.email}</div>
                  </div>
                  <div style={{textAlign:"right",flexShrink:0}}>
                    <div style={{color:"#2563eb",fontSize:12,fontWeight:500}}>{c.role||"—"}</div>
                    <div style={{color:"#94a3b8",fontSize:11}}>{c.skills?.split(",")[0]||""}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Email settings & Google Meet Configuration */}
          <div style={{background:"#f8f9fc",border:"1px solid #e2e5ed",borderRadius:12,padding:18,marginBottom:18}}>
            <label style={{display:"flex",alignItems:"center",gap:8,fontSize:13,color:"#0f172a",cursor:"pointer",fontWeight:700,marginBottom:14}}>
              <input type="checkbox" checked={sendInv} onChange={e=>setSendInv(e.target.checked)} style={{width:15,height:15,accentColor:"#2563eb"}}/>
              Send Stage 1 Task Assignment &amp; Google Meet Email to selected candidates ({selected.size})
            </label>
            {sendInv&&(
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
                <div>
                  <label style={LT.label}>Target Job Role</label>
                  <input value={jobRole} onChange={e=>setJobRole(e.target.value)} style={LT.input}/>
                </div>
                <div>
                  <label style={LT.label}>Assigned Task / Assessment Title</label>
                  <input value={title} onChange={e=>setTitle(e.target.value)} style={LT.input}/>
                </div>
                <div>
                  <label style={LT.label}>📹 Google Meet Link</label>
                  <input value={meetLink} onChange={e=>setMeetLink(e.target.value)} placeholder="https://meet.google.com/..." style={{...LT.input,borderColor:"#2563eb",fontWeight:600}}/>
                </div>
                <div>
                  <label style={LT.label}>🚀 Submission Portal Link</label>
                  <input value={link} onChange={e=>setLink(e.target.value)} style={LT.input}/>
                </div>
                <div>
                  <label style={LT.label}>⏰ Task Submission Deadline</label>
                  <input value={deadline} onChange={e=>setDeadline(e.target.value)} style={LT.input}/>
                </div>
              </div>
            )}
          </div>

          <PrimaryBtn onClick={confirm} disabled={confirming||selected.size===0}>
            <CheckCircle size={15}/>
            {confirming?"Sending Emails…":`Launch Workflow & Send Emails to ${selected.size} Candidates`}
          </PrimaryBtn>
        </div>
      )}

      {done && (
        <Alert type="success">
          <div>
            <strong style={{display:"block",marginBottom:6}}>Workflow Launched Successfully!</strong>
            <div>✅ {done.candidates_imported} candidates imported</div>
            <div>📧 {done.emails_sent||done.emails_queued} invitation emails dispatched with Google Meet link: <code>{done.meeting_link}</code></div>
            <div style={{marginTop:12,display:"flex",gap:8}}>
              <button onClick={()=>{setResult(null);setDone(null);}}
                style={{background:"#16a34a",color:"#fff",border:"none",borderRadius:8,padding:"7px 16px",fontSize:12,fontWeight:700,cursor:"pointer",fontFamily:"inherit"}}>
                Import More Candidates
              </button>
            </div>
          </div>
        </Alert>
      )}
    </div>
  );
}

// ── Pipeline Automation Tab ──────────────────────────────────────────────────
function PipelineTab({token,reloadQueue}:{token:string;reloadQueue:()=>void}){
  const [candidates,setCandidates]=useState<any[]>([
    {id:"c-rahul",name:"Rahul Sharma",email:"rahul.sharma@gmail.com",role:"Backend Developer",stage:"task_assigned",task:"Python & FastAPI Platform",meet:"https://meet.google.com/xyz-voice-hire"},
    {id:"c-priya",name:"Priya Patel",email:"priya.patel@outlook.com",role:"Frontend Developer",stage:"task_assigned",task:"React UI & Voice Metering",meet:"https://meet.google.com/xyz-voice-hire"},
    {id:"c-arjun",name:"Arjun Mehta",email:"arjun.mehta@yahoo.com",role:"Full Stack Engineer",stage:"day2_sent",task:"Full-Stack System Design",meet:"https://meet.google.com/xyz-voice-hire"},
    {id:"c-sneha",name:"Sneha Reddy",email:"sneha.reddy@gmail.com",role:"ML Engineer",stage:"interview_scheduled",task:"Voice STT & TTS Pipeline",meet:"https://meet.google.com/xyz-voice-hire"},
    {id:"c-kiran",name:"Kiran Kumar",email:"kiran.kumar@techmail.com",role:"DevOps Engineer",stage:"feedback_sent",task:"Docker & Cloud Deployments",meet:"https://meet.google.com/xyz-voice-hire"},
  ]);
  const [acting,setActing]=useState<string|null>(null);
  const [notice,setNotice]=useState<string|null>(null);

  async function triggerStage(cand:any,stage:string){
    setActing(cand.id);setNotice(null);
    try{
      const res=await apiFetch("/api/emails/pipeline/trigger-stage",token,{
        method:"POST",
        body:JSON.stringify({
          candidate_id:cand.id,
          stage,
          candidate_name:cand.name,
          candidate_email:cand.email,
          job_role:cand.role,
          assessment_title:cand.task,
          deadline:"48 hours",
          assessment_link:"https://portal.voicehire.ai/submit",
          meeting_link:cand.meet||"https://meet.google.com/xyz-voice-hire",
          decision:"We are delighted to extend a job offer for the position!",
          feedback_notes:"Strong technical performance and architecture demonstration."
        })
      });
      setNotice(`Stage "${stage}" triggered for ${cand.name}! Email dispatched (Status: ${res.status}).`);
      setCandidates(prev=>prev.map(c=>c.id===cand.id?{...c,stage:stage==="day2_reminder"?"day2_sent":stage==="interview"?"interview_scheduled":stage==="feedback"?"feedback_sent":"offer_sent"}:c));
      reloadQueue();
    }catch(e:any){setNotice(`Error: ${e.message}`);}
    finally{setActing(null);}
  }

  const STAGE_LABELS:Record<string,{label:string;bg:string;color:string;border:string}> = {
    task_assigned:      {label:"Stage 1: Task & GMeet Sent", bg:"#eff4ff", color:"#2563eb", border:"#bfdbfe"},
    day2_sent:          {label:"Stage 2: Day 2 Reminder Sent", bg:"#fffbeb", color:"#d97706", border:"#fde68a"},
    interview_scheduled:{label:"Stage 3: Interview Scheduled", bg:"#f0fdf4", color:"#16a34a", border:"#bbf7d0"},
    feedback_sent:      {label:"Stage 3: Feedback Released", bg:"#f5f3ff", color:"#7c3aed", border:"#ddd6fe"},
    offer_sent:         {label:"Stage 4: Offer Extended", bg:"#ecfdf5", color:"#059669", border:"#a7f3d0"},
  };

  return(
    <div style={LT.card}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16,flexWrap:"wrap",gap:8}}>
        <div>
          <h3 style={{margin:0,fontSize:15,fontWeight:700,color:"#0f172a",display:"flex",alignItems:"center",gap:8}}>
            <Zap size={16} style={{color:"#2563eb"}}/> Recruitment Pipeline Automation Loop
          </h3>
          <p style={{margin:"4px 0 0",color:"#64748b",fontSize:13}}>
            Track candidates across stages: <strong>Task &amp; GMeet Invite → Day 2 Submission Reminder → Technical Interview → Feedback &amp; Decision</strong>.
          </p>
        </div>
      </div>

      {notice && <Alert type="info">{notice}</Alert>}

      <div style={{display:"flex",flexDirection:"column",gap:12}}>
        {candidates.map(c=>{
          const st=STAGE_LABELS[c.stage]||STAGE_LABELS.task_assigned;
          const isBusy=acting===c.id;
          return(
            <div key={c.id} style={{background:"#f8f9fc",border:"1px solid #e2e5ed",borderRadius:12,padding:"16px 20px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:14}}>
              <div style={{minWidth:220}}>
                <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:4}}>
                  <strong style={{color:"#0f172a",fontSize:14}}>{c.name}</strong>
                  <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:99,background:st.bg,color:st.color,border:`1px solid ${st.border}`}}>
                    {st.label}
                  </span>
                </div>
                <div style={{color:"#64748b",fontSize:12}}>{c.email} · <span style={{color:"#2563eb",fontWeight:500}}>{c.role}</span></div>
                <div style={{color:"#475569",fontSize:12,marginTop:4}}>Task: <strong>{c.task}</strong></div>
                <div style={{color:"#16a34a",fontSize:11,marginTop:2}}>GMeet: <code>{c.meet}</code></div>
              </div>

              {/* Action Buttons */}
              <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
                <button onClick={()=>triggerStage(c,"day2_reminder")} disabled={isBusy}
                  title="Trigger Day 2 submission reminder email with submission link"
                  style={{background:"#fff",border:"1px solid #fde68a",color:"#b45309",borderRadius:8,padding:"6px 12px",fontSize:12,fontWeight:600,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:5}}>
                  <Clock size={12}/>{isBusy?"Sending…":"⚡ Day 2 Reminder"}
                </button>
                <button onClick={()=>triggerStage(c,"interview")} disabled={isBusy}
                  title="Advance to tech interview and send GMeet invitation"
                  style={{background:"#fff",border:"1px solid #bfdbfe",color:"#1d4ed8",borderRadius:8,padding:"6px 12px",fontSize:12,fontWeight:600,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:5}}>
                  <Users size={12}/>{isBusy?"Sending…":"🎙 Schedule Interview"}
                </button>
                <button onClick={()=>triggerStage(c,"feedback")} disabled={isBusy}
                  title="Send constructive evaluation feedback"
                  style={{background:"#fff",border:"1px solid #ddd6fe",color:"#6d28d9",borderRadius:8,padding:"6px 12px",fontSize:12,fontWeight:600,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:5}}>
                  <FileText size={12}/>{isBusy?"Sending…":"📝 Send Feedback"}
                </button>
                <button onClick={()=>triggerStage(c,"decision")} disabled={isBusy}
                  title="Send final job offer decision email"
                  style={{background:"#16a34a",color:"#fff",border:"none",borderRadius:8,padding:"6px 12px",fontSize:12,fontWeight:700,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:5}}>
                  <CheckCircle size={12}/>{isBusy?"Sending…":"🏆 Extend Offer"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Templates Tab ─────────────────────────────────────────────────────────────
function TemplatesTab({token}:{token:string}){
  const [templates,setTemplates] = useState<any[]>([]);
  const [sel,setSel]   = useState<any>(null);
  const [editing,setEditing] = useState(false);
  const [saving,setSaving]   = useState(false);

  useEffect(()=>{apiFetch("/api/emails/templates",token).then(setTemplates).catch(()=>{});},[token]);

  async function pick(id:string){
    const t=await apiFetch(`/api/emails/templates/${id}`,token);
    setSel(t);setEditing(false);
  }
  async function save(){
    setSaving(true);
    try{
      await apiFetch(`/api/emails/templates/${sel.id}`,token,{method:"PATCH",
        body:JSON.stringify({name:sel.name,subject:sel.subject,html_body:sel.html_body,text_body:sel.text_body,enabled:sel.enabled})});
      setEditing(false);
    }catch(e:any){alert(e.message);}
    finally{setSaving(false);}
  }

  return(
    <div style={{display:"flex",gap:16,flexWrap:"wrap",alignItems:"flex-start"}}>
      {/* List */}
      <div style={{...LT.card,width:210,flexShrink:0}}>
        <h4 style={{margin:"0 0 12px",fontSize:13,fontWeight:700,color:"#0f172a"}}>Email Templates</h4>
        {templates.length===0 && <p style={{color:"#94a3b8",fontSize:12}}>No templates found.</p>}
        <div style={{display:"flex",flexDirection:"column",gap:4}}>
          {templates.map(t=>(
            <button key={t.id} onClick={()=>pick(t.id)}
              style={{padding:"9px 12px",borderRadius:8,cursor:"pointer",textAlign:"left",fontFamily:"inherit",border:sel?.id===t.id?"1px solid #bfdbfe":"1px solid transparent",background:sel?.id===t.id?"#eff4ff":"transparent",transition:"all 0.15s"}}>
              <div style={{fontSize:12,fontWeight:600,color:sel?.id===t.id?"#2563eb":"#0f172a"}}>{t.name}</div>
              <span style={{fontSize:10,fontWeight:700,padding:"1px 7px",borderRadius:99,background:t.enabled?"#f0fdf4":"#f1f5f9",color:t.enabled?"#16a34a":"#64748b",border:`1px solid ${t.enabled?"#bbf7d0":"#e2e8f0"}`}}>
                {t.enabled?"Enabled":"Disabled"}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Editor */}
      {sel && (
        <div style={{...LT.card,flex:1,minWidth:300}}>
          <div style={{display:"flex",gap:8,marginBottom:18,alignItems:"center"}}>
            <h4 style={{margin:0,flex:1,fontSize:15,fontWeight:700,color:"#0f172a"}}>{sel.name}</h4>
            <button onClick={()=>setEditing(!editing)}
              style={{background:editing?"#fff":"#2563eb",color:editing?"#475569":"#fff",border:editing?"1px solid #e2e5ed":"none",borderRadius:8,padding:"7px 14px",fontSize:12,fontWeight:700,cursor:"pointer",fontFamily:"inherit"}}>
              {editing?"Cancel":"Edit"}
            </button>
            {editing&&(
              <button onClick={save} disabled={saving}
                style={{background:"#16a34a",color:"#fff",border:"none",borderRadius:8,padding:"7px 14px",fontSize:12,fontWeight:700,cursor:"pointer",fontFamily:"inherit"}}>
                {saving?"Saving…":"Save Changes"}
              </button>
            )}
          </div>

          <div style={{marginBottom:14}}>
            <label style={LT.label}>Subject</label>
            {editing
              ? <input value={sel.subject} onChange={e=>setSel({...sel,subject:e.target.value})} style={LT.input}/>
              : <div style={{padding:"9px 12px",background:"#f8f9fc",border:"1px solid #e2e5ed",borderRadius:8,fontSize:13,color:"#0f172a"}}>{sel.subject}</div>
            }
          </div>

          <div style={{marginBottom:14}}>
            <label style={LT.label}>Variables</label>
            <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
              {(sel.variables||[]).map((v:string)=>(
                <span key={v} style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:99,background:"#eff4ff",color:"#2563eb",border:"1px solid #bfdbfe"}}>{`{{${v}}}`}</span>
              ))}
            </div>
          </div>

          <div>
            <label style={LT.label}>Plain Text Body</label>
            {editing
              ? <textarea value={sel.text_body} onChange={e=>setSel({...sel,text_body:e.target.value})} style={{...LT.input,minHeight:180,resize:"vertical"}}/>
              : <pre style={{fontSize:12,background:"#f8f9fc",border:"1px solid #e2e5ed",borderRadius:8,padding:12,overflow:"auto",whiteSpace:"pre-wrap",color:"#475569",fontFamily:"monospace",maxHeight:240}}>{sel.text_body}</pre>
            }
          </div>

          {editing && (
            <label style={{display:"flex",alignItems:"center",gap:8,fontSize:13,color:"#475569",cursor:"pointer",marginTop:12,fontWeight:600}}>
              <input type="checkbox" checked={sel.enabled} onChange={e=>setSel({...sel,enabled:e.target.checked})} style={{width:15,height:15,accentColor:"#2563eb"}}/>
              Template enabled
            </label>
          )}
        </div>
      )}
    </div>
  );
}

// ── Bulk Send Tab ─────────────────────────────────────────────────────────────
function BulkTab({token}:{token:string}){
  const [emails,setEmails]   = useState("");
  const [category,setCategory] = useState("assessment_invitation");
  const [jobRole,setJobRole] = useState("Software Engineer");
  const [title,setTitle]     = useState("Technical Assessment");
  const [deadline,setDeadline] = useState("2026-11-30");
  const [link,setLink]       = useState("https://portal.voicehire.ai/assess");
  const [preview,setPreview] = useState<any>(null);
  const [confirmed,setConfirmed] = useState(false);
  const [sending,setSending] = useState(false);
  const [result,setResult]   = useState<any>(null);

  const list = emails.split(/[\n,]+/).map(e=>e.trim()).filter(Boolean);

  async function doPreview(){
    try{
      const d=await apiFetch("/api/emails/bulk/preview",token,{method:"POST",
        body:JSON.stringify({candidate_emails:list,category,context_vars:{job_role:jobRole,assessment_title:title,deadline,assessment_link:link,candidate_name:"[Name]"}})});
      setPreview(d);setConfirmed(false);setResult(null);
    }catch(e:any){alert(e.message);}
  }
  async function send(){
    setSending(true);
    try{
      const d=await apiFetch("/api/emails/bulk/send",token,{method:"POST",
        body:JSON.stringify({candidate_emails:list,category,context_vars:{job_role:jobRole,assessment_title:title,deadline,assessment_link:link},confirmed:true})});
      setResult(d);
    }catch(e:any){alert(e.message);}
    finally{setSending(false);}
  }

  return(
    <div style={LT.card}>
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:18}}>
        <Send size={16} style={{color:"#2563eb"}}/>
        <h3 style={{margin:0,fontSize:15,fontWeight:700,color:"#0f172a"}}>Bulk Email Send</h3>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,maxWidth:680}}>
        <div style={{gridColumn:"1 / -1"}}>
          <label style={LT.label}>Recipient Emails</label>
          <textarea value={emails} onChange={e=>setEmails(e.target.value)}
            placeholder={"alice@example.com\nbob@company.com"}
            style={{...LT.input,minHeight:90,resize:"vertical"}}/>
          <span style={{fontSize:11,color:"#94a3b8"}}>One per line or comma-separated</span>
        </div>

        <div style={{gridColumn:"1 / -1"}}>
          <label style={LT.label}>Email Category</label>
          <select value={category} onChange={e=>setCategory(e.target.value)} style={LT.select}>
            {["assessment_invitation","assessment_reminder","interview_invitation","decision_notification"].map(c=><option key={c} value={c}>{c.replaceAll("_"," ")}</option>)}
          </select>
        </div>

        {[["Job Role",jobRole,setJobRole],["Assessment Title",title,setTitle],["Deadline",deadline,setDeadline],["Assessment Link",link,setLink]].map(([l,v,s])=>(
          <div key={String(l)}>
            <label style={LT.label}>{String(l)}</label>
            <input value={String(v)} onChange={e=>(s as any)(e.target.value)} style={LT.input}/>
          </div>
        ))}
      </div>

      <button onClick={doPreview}
        style={{marginTop:16,background:"#fff",border:"1px solid #e2e5ed",color:"#0f172a",borderRadius:9,padding:"9px 18px",fontSize:13,fontWeight:700,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:6}}>
        Preview ({list.length} recipients) <ChevronRight size={13}/>
      </button>

      {preview && (
        <div style={{...LT.card,marginTop:16,background:"#f8f9fc"}}>
          <div style={{display:"flex",gap:10,flexWrap:"wrap",marginBottom:12}}>
            <span className="badge badge-green"><CheckCircle size={10}/>{preview.valid_count} valid</span>
            {preview.invalid_count>0 && <span className="badge badge-danger"><XCircle size={10}/>{preview.invalid_count} invalid</span>}
          </div>
          <div style={{fontSize:13,color:"#475569",marginBottom:10}}>
            Subject: <strong style={{color:"#0f172a"}}>{preview.subject_preview}</strong>
          </div>
          {preview.invalid_emails?.length>0 && (
            <div style={{color:"#dc2626",fontSize:12,marginBottom:10}}>Invalid: {preview.invalid_emails.join(", ")}</div>
          )}
          <label style={{display:"flex",alignItems:"center",gap:8,fontSize:13,color:"#475569",cursor:"pointer",fontWeight:600,marginBottom:14}}>
            <input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} style={{width:15,height:15,accentColor:"#2563eb"}}/>
            I confirm sending to <strong>{preview.valid_count}</strong> recipients. This cannot be undone.
          </label>
          <button onClick={send} disabled={sending||!confirmed}
            style={{background:"#dc2626",color:"#fff",border:"none",borderRadius:9,padding:"10px 20px",fontSize:13,fontWeight:700,cursor:"pointer",fontFamily:"inherit",display:"inline-flex",alignItems:"center",gap:6,opacity:!confirmed?0.5:1}}>
            <Send size={13}/>{sending?"Sending…":`Send to ${preview.valid_count} recipients`}
          </button>
        </div>
      )}

      {result && <Alert type="success">Queued: {result.queued} · Skipped: {result.skipped}</Alert>}
    </div>
  );
}
