import React, { useEffect, useState, useRef, FormEvent } from "react";
import { useAuth } from "./AuthContext";
import EmailCenter from "./email/EmailCenter";
import QuickSend from "./email/QuickSend";
import {
  Mic, Mail, Send, LogOut,
  Briefcase, User, Zap,
  AlertTriangle, Square, Volume2
} from "lucide-react";

// ── Error Boundary ─────────────────────────────────────────────────────────────
class ErrBound extends React.Component<{children:React.ReactNode;name:string},{err:string|null}> {
  state={err:null};
  static getDerivedStateFromError(e:Error){return{err:e?.message||String(e)};}
  componentDidCatch(e:Error){console.error("[ErrBound]",e);}
  render(){
    if(this.state.err) return(
      <div className="alert alert-error" style={{margin:0}}>
        <AlertTriangle size={15}/>
        <div>
          <strong>{this.props.name}</strong>
          <pre style={{marginTop:6,fontSize:12,whiteSpace:"pre-wrap",opacity:0.75}}>{this.state.err}</pre>
          <button onClick={()=>this.setState({err:null})} className="btn btn-secondary btn-sm" style={{marginTop:10}}>
            Retry
          </button>
        </div>
      </div>
    );
    return this.props.children;
  }
}

// ── Full Voice Panel with mic + TTS (all logic unchanged) ─────────────────────
function VoiceAssistant({getToken,role,apiBase}:{getToken:()=>string;role:string;apiBase:string}) {
  type Msg={id:number;who:"user"|"ai";text:string;tag?:string};
  type St="idle"|"recording"|"transcribing"|"thinking"|"speaking";

  const [status, setStatus] = useState<St>("idle");
  const [msgs, setMsgs]     = useState<Msg[]>([{id:0,who:"ai",text:
    role==="recruiter"
      ? "Hi! I'm your VoiceHire AI assistant. Click the mic or type to ask me anything. Try: \"How many candidates registered?\" or \"Show overdue candidates\"."
      : "Hi! I'm your VoiceHire AI assistant. Ask me about your assignment, deadline or interview schedule."}]);
  const [input, setInput]   = useState("");
  const [health, setHealth] = useState<any>(null);
  const [err, setErr]       = useState("");
  const [vol, setVol]       = useState(0);

  const idRef    = useRef(1);
  const bottomRef= useRef<HTMLDivElement>(null);
  const recRef   = useRef<MediaRecorder|null>(null);
  const chunksRef= useRef<Blob[]>([]);
  const analyser = useRef<AnalyserNode|null>(null);
  const rafRef   = useRef<number>(0);
  const audioRef = useRef<HTMLAudioElement|null>(null);

  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:"smooth"}); },[msgs]);

  useEffect(()=>{
    const t=getToken(); if(!t) return;
    fetch(`${apiBase}/voice/health`,{headers:{Authorization:`Bearer ${t}`}})
      .then(r=>r.ok?r.json():null).then(d=>{if(d) setHealth(d);}).catch(()=>{});
  },[]);

  function addMsg(who:"user"|"ai",text:string,tag?:string){
    setMsgs(m=>[...m,{id:idRef.current++,who,text,tag}]);
  }

  async function sendText(text:string){
    if(!text.trim()||status!=="idle") return;
    addMsg("user",text);
    setStatus("thinking"); setErr("");
    try{
      const t=getToken();
      const r=await fetch(`${apiBase}/voice/chat`,{method:"POST",
        headers:{Authorization:`Bearer ${t}`,"Content-Type":"application/json"},
        body:JSON.stringify({text})});
      if(!r.ok) throw new Error(`Backend ${r.status}`);
      const d=await r.json();
      const reply:string=d.reply||"(no reply)";
      addMsg("ai",reply,"Local AI");
      await speakText(reply);
    }catch(e:any){ setErr(e.message); addMsg("ai","Error: "+e.message); setStatus("idle"); }
  }

  async function speakText(text:string){
    setStatus("speaking");
    let played = false;
    try{
      const t=getToken();
      const r=await fetch(`${apiBase}/voice/tts`,{method:"POST",
        headers:{Authorization:`Bearer ${t}`,"Content-Type":"application/json"},
        body:JSON.stringify({text})});
      if(r.ok){
        const blob=await r.blob();
        const url=URL.createObjectURL(blob);
        if(audioRef.current) audioRef.current.pause();
        const audio=new Audio(url);
        audioRef.current=audio;
        audio.onended=()=>{ URL.revokeObjectURL(url); setStatus("idle"); };
        audio.onerror=()=>{ if(!played && 'speechSynthesis' in window) playSpeechSynthesis(text); else setStatus("idle"); };
        await audio.play();
        played = true;
      } else {
        throw new Error("TTS status " + r.status);
      }
    }catch(e:any){
      console.warn("Backend TTS:", e.message, "Using browser SpeechSynthesis fallback");
      playSpeechSynthesis(text);
    }
  }

  function playSpeechSynthesis(text: string) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const ut = new SpeechSynthesisUtterance(text);
      ut.rate = 1.0;
      ut.pitch = 1.0;
      ut.onend = () => setStatus("idle");
      ut.onerror = () => setStatus("idle");
      window.speechSynthesis.speak(ut);
    } else {
      setStatus("idle");
    }
  }

  const srRef = useRef<any>(null);

  async function startRecording(){
    setErr("");
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const sr = new SpeechRecognition();
        sr.continuous = false;
        sr.interimResults = false;
        sr.lang = "en-US";
        sr.onstart = () => { setStatus("recording"); };
        sr.onresult = (evt: any) => {
          const transcript = evt.results?.[0]?.[0]?.transcript;
          if (transcript) {
            void sendText(transcript);
          } else {
            setStatus("idle");
          }
        };
        sr.onerror = (e: any) => {
          console.warn("SpeechRecognition error:", e);
          startMediaRecorder();
        };
        sr.onend = () => {
          if (status === "recording") setStatus("idle");
        };
        srRef.current = sr;
        sr.start();
        return;
      } catch (e) {
        console.warn("SpeechRecognition failed, falling back to MediaRecorder");
      }
    }
    startMediaRecorder();
  }

  async function startMediaRecorder(){
    if(!navigator.mediaDevices?.getUserMedia){setErr("Microphone not available in this browser.");return;}
    try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
      const ctx=new AudioContext();
      const src=ctx.createMediaStreamSource(stream);
      const an=ctx.createAnalyser(); an.fftSize=256;
      src.connect(an); analyser.current=an;
      const data=new Uint8Array(an.frequencyBinCount);
      function tick(){
        an.getByteFrequencyData(data);
        const avg=data.reduce((a,b)=>a+b,0)/data.length;
        setVol(Math.min(100,avg*2));
        rafRef.current=requestAnimationFrame(tick);
      }
      tick();
      const mime=["audio/webm;codecs=opus","audio/webm","audio/mp4","audio/ogg"].find(m=>MediaRecorder.isTypeSupported(m));
      const mr=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);
      chunksRef.current=[];
      mr.ondataavailable=e=>e.data.size&&chunksRef.current.push(e.data);
      mr.onstop=async()=>{
        cancelAnimationFrame(rafRef.current); setVol(0);
        stream.getTracks().forEach(t=>t.stop());
        ctx.close();
        const blob=new Blob(chunksRef.current,{type:mr.mimeType||"audio/webm"});
        if(blob.size<1500){setErr("Recording too short. Speak clearly and try again.");setStatus("idle");return;}
        setStatus("transcribing");
        try{
          const t=getToken();
          const fd=new FormData(); fd.append("audio",blob,"voice.webm");
          const r=await fetch(`${apiBase}/voice/stt`,{method:"POST",headers:{Authorization:`Bearer ${t}`},body:fd});
          if(!r.ok) throw new Error("STT failed "+r.status);
          const d=await r.json();
          if(!d.text){setErr("No speech detected. Try again.");setStatus("idle");return;}
          await sendText(d.text);
        }catch(e:any){setErr(e.message);setStatus("idle");}
      };
      mr.start(); recRef.current=mr;
      setStatus("recording");
    }catch(e:any){
      if(e.name==="NotAllowedError") setErr("Microphone access denied. Allow it in browser settings or use the text box.");
      else setErr(e.message);
    }
  }

  function stopRecording(){
    if(srRef.current){ try{srRef.current.stop();}catch{} srRef.current=null; }
    if(recRef.current?.state==="recording") recRef.current.stop();
    recRef.current=null;
  }

  function toggleMic(){
    if(status==="recording"){stopRecording();}
    else if(status==="idle"){startRecording();}
    else if(status==="speaking"){ audioRef.current?.pause(); setStatus("idle"); }
  }

  function onSubmit(e:FormEvent){e.preventDefault();const t=input.trim();if(t){sendText(t);setInput("");}}

  // ── Status config ────────────────────────────────────────────────────────────
  const stCfg:{[k in St]:{label:string;color:string;bg:string;border:string}} = {
    idle:         {label:"Ready",         color:"#16a34a", bg:"#f0fdf4", border:"#bbf7d0"},
    recording:    {label:"Recording…",    color:"#dc2626", bg:"#fef2f2", border:"#fecaca"},
    transcribing: {label:"Transcribing…", color:"#7c3aed", bg:"#f5f3ff", border:"#ddd6fe"},
    thinking:     {label:"Thinking…",     color:"#d97706", bg:"#fffbeb", border:"#fde68a"},
    speaking:     {label:"Speaking…",     color:"#2563eb", bg:"#eff4ff", border:"#bfdbfe"},
  };
  const st = stCfg[status];

  const micStyle:{[k in St]:React.CSSProperties} = {
    idle:         {background:"#2563eb", boxShadow:"0 4px 14px rgba(37,99,235,0.35)"},
    recording:    {background:"#dc2626", boxShadow:"0 0 0 8px rgba(220,38,38,0.15), 0 4px 14px rgba(220,38,38,0.4)"},
    transcribing: {background:"#7c3aed", boxShadow:"0 4px 14px rgba(124,58,237,0.35)"},
    thinking:     {background:"#d97706", boxShadow:"0 4px 14px rgba(217,119,6,0.35)"},
    speaking:     {background:"#2563eb", boxShadow:"0 0 0 8px rgba(37,99,235,0.12), 0 4px 14px rgba(37,99,235,0.4)"},
  };

  const examples=role==="recruiter"
    ?["How many candidates registered?","Show overdue candidates","Assign Python assessment to pending candidates","Schedule interviews for top performers"]
    :["What is my assignment?","What is my submission deadline?","Show my interview schedule","What is my current status?"];

  return(
    <div style={{display:"flex",flexDirection:"column",height:"calc(100vh - 200px)",maxWidth:820}}>

      {/* ── Service health + status ─────────────────────────────────────────── */}
      <div style={{display:"flex",gap:8,marginBottom:16,flexWrap:"wrap",alignItems:"center"}}>
        {health&&[
          ["LLM", health.llm?.ok],
          ["STT", health.stt?.ok],
          ["TTS", health.tts?.ok],
        ].map(([n,ok])=>(
          <span key={String(n)} style={{
            fontSize:11,fontWeight:600,padding:"3px 10px",borderRadius:99,
            background:ok?"#f0fdf4":"#fef2f2",
            color:ok?"#16a34a":"#dc2626",
            border:`1px solid ${ok?"#bbf7d0":"#fecaca"}`,
            display:"inline-flex",alignItems:"center",gap:4,
          }}>
            <span style={{width:6,height:6,borderRadius:"50%",background:ok?"#16a34a":"#dc2626",display:"inline-block"}}/>
            {String(n)}
          </span>
        ))}
        <span style={{
          fontSize:11,fontWeight:700,padding:"3px 12px",borderRadius:99,
          background:st.bg, color:st.color, border:`1px solid ${st.border}`,
        }}>
          {st.label}
        </span>
      </div>

      {/* ── Chat messages ───────────────────────────────────────────────────── */}
      <div style={{
        flex:1,overflowY:"auto",display:"flex",flexDirection:"column",gap:10,
        padding:"16px",background:"#f8f9fc",borderRadius:14,
        border:"1px solid #e2e5ed",marginBottom:12,
      }}>
        {msgs.map(m=>(
          <div key={m.id} style={{display:"flex",justifyContent:m.who==="user"?"flex-end":"flex-start"}}>
            <div style={{
              maxWidth:"78%",
              padding:"10px 14px",
              borderRadius:m.who==="user"?"16px 16px 4px 16px":"16px 16px 16px 4px",
              fontSize:13.5,lineHeight:1.65,
              background:m.who==="user"?"#2563eb":"#ffffff",
              border:m.who==="user"?"none":"1px solid #e2e5ed",
              color:m.who==="user"?"#ffffff":"#0f172a",
              boxShadow:m.who==="user"?"0 2px 8px rgba(37,99,235,0.25)":"0 1px 3px rgba(15,23,42,0.06)",
            }}>
              {m.who==="ai"&&(
                <div style={{fontSize:10,fontWeight:700,color:"#94a3b8",marginBottom:5,textTransform:"uppercase",letterSpacing:"0.06em"}}>
                  VoiceHire AI {m.tag&&`· ${m.tag}`}
                </div>
              )}
              {m.text}
            </div>
          </div>
        ))}
        {status==="thinking"&&(
          <div style={{display:"flex",alignItems:"center",gap:8,color:"#d97706",fontSize:13,padding:"4px 0"}}>
            <Dots color="#d97706"/> Thinking…
          </div>
        )}
        {status==="transcribing"&&(
          <div style={{display:"flex",alignItems:"center",gap:8,color:"#7c3aed",fontSize:13,padding:"4px 0"}}>
            <Dots color="#7c3aed"/> Transcribing speech…
          </div>
        )}
        <div ref={bottomRef}/>
      </div>

      {/* ── Volume bar when recording ───────────────────────────────────────── */}
      {status==="recording"&&(
        <div style={{marginBottom:10,height:5,borderRadius:3,background:"#e2e5ed",overflow:"hidden"}}>
          <div style={{
            width:`${vol}%`,height:"100%",
            background:"linear-gradient(90deg,#2563eb,#dc2626)",
            borderRadius:3,transition:"width 0.05s",
          }}/>
        </div>
      )}

      {/* ── Input row ──────────────────────────────────────────────────────── */}
      <form onSubmit={onSubmit} style={{display:"flex",gap:10,alignItems:"center",borderTop:"1px solid #e2e5ed",paddingTop:14}}>
        {/* Mic button */}
        <button type="button" onClick={toggleMic}
          style={{
            flexShrink:0,width:48,height:48,borderRadius:"50%",border:"none",cursor:"pointer",
            color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",
            transition:"all 0.2s",
            ...micStyle[status],
          }}
          title={status==="recording"?"Stop recording":status==="speaking"?"Stop speaking":"Start speaking"}>
          {status==="recording"
            ? <Square size={18} fill="#fff"/>
            : status==="speaking"
            ? <Volume2 size={20}/>
            : <Mic size={22}/>}
        </button>

        <input
          value={input}
          onChange={e=>setInput(e.target.value)}
          disabled={status!=="idle"}
          placeholder="Type or click mic to speak…"
          style={{
            flex:1,background:"#ffffff",border:"1px solid #e2e5ed",borderRadius:12,
            color:"#0f172a",padding:"12px 16px",fontSize:13.5,fontFamily:"inherit",
            outline:"none",transition:"border-color 0.15s, box-shadow 0.15s",
          }}
          onFocus={e=>{e.target.style.borderColor="#2563eb";e.target.style.boxShadow="0 0 0 3px rgba(37,99,235,0.12)";}}
          onBlur={e=>{e.target.style.borderColor="#e2e5ed";e.target.style.boxShadow="none";}}
        />
        <button type="submit" disabled={!input.trim()||status!=="idle"}
          style={{
            background:"#2563eb",color:"#fff",border:"none",borderRadius:12,
            padding:"12px 22px",fontSize:13.5,fontWeight:700,cursor:"pointer",
            fontFamily:"inherit",display:"flex",alignItems:"center",gap:6,
            opacity:(!input.trim()||status!=="idle")?0.5:1,
            boxShadow:"0 2px 8px rgba(37,99,235,0.3)",transition:"all 0.15s",
          }}>
          <Send size={14}/> Send
        </button>
      </form>

      {err&&(
        <div className="alert alert-error" style={{marginTop:10}}>
          <AlertTriangle size={13}/> {err}
        </div>
      )}

      {/* ── Example prompts ─────────────────────────────────────────────────── */}
      <div style={{display:"flex",gap:6,marginTop:10,flexWrap:"wrap"}}>
        {examples.map(q=>(
          <button key={q}
            onClick={()=>{if(status==="idle") setInput(q);}}
            style={{
              fontSize:11,fontWeight:500,padding:"5px 12px",borderRadius:99,
              background:"#f1f5f9",border:"1px solid #e2e5ed",
              color:"#475569",cursor:"pointer",fontFamily:"inherit",transition:"all 0.15s",
            }}
            onMouseEnter={e=>{(e.target as HTMLElement).style.background="#eff4ff";(e.target as HTMLElement).style.color="#2563eb";(e.target as HTMLElement).style.borderColor="#bfdbfe";}}
            onMouseLeave={e=>{(e.target as HTMLElement).style.background="#f1f5f9";(e.target as HTMLElement).style.color="#475569";(e.target as HTMLElement).style.borderColor="#e2e5ed";}}>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function Dots({color="#d97706"}:{color?:string}){
  return(
    <div style={{display:"flex",gap:3}}>
      {[0,1,2].map(i=>(
        <div key={i} style={{width:6,height:6,borderRadius:"50%",background:color,animation:`bounce 1.2s ease-in-out ${i*0.2}s infinite`}}/>
      ))}
      <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0.55)}40%{transform:scale(1)}}`}</style>
    </div>
  );
}

// ── Login ─────────────────────────────────────────────────────────────────────
function Login({onLogin}:{onLogin:(t:string,r:string)=>void}){
  const [loading,setLoading]=useState("");
  const [err,setErr]=useState("");

  async function go(role:string){
    setLoading(role);setErr("");
    try{
      const r=await fetch(`http://localhost:8000/token?role=${role}`);
      if(!r.ok) throw new Error(`Backend returned ${r.status} — is it running on :8000?`);
      const d=await r.json(); onLogin(d.token,role);
    }catch(e:any){setErr(e.message);}
    finally{setLoading("");}
  }

  return(
    <div style={{
      minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",
      background:"linear-gradient(135deg,#f0f4ff 0%,#e8f0fe 50%,#f5f8ff 100%)",
      fontFamily:"inherit",padding:24,
    }}>
      {/* Decorative blobs */}
      <div style={{position:"fixed",top:"-20%",right:"-10%",width:500,height:500,borderRadius:"50%",background:"radial-gradient(circle,rgba(37,99,235,0.08) 0%,transparent 70%)",pointerEvents:"none"}}/>
      <div style={{position:"fixed",bottom:"-20%",left:"-10%",width:600,height:600,borderRadius:"50%",background:"radial-gradient(circle,rgba(13,148,136,0.07) 0%,transparent 70%)",pointerEvents:"none"}}/>

      <div style={{
        background:"#ffffff",border:"1px solid #e2e5ed",borderRadius:22,
        padding:"48px 44px",maxWidth:440,width:"100%",textAlign:"center",
        boxShadow:"0 20px 40px rgba(15,23,42,0.1),0 4px 8px rgba(15,23,42,0.06)",
        position:"relative",zIndex:1,
      }}>
        {/* Logo mark */}
        <div style={{
          width:60,height:60,
          background:"linear-gradient(135deg,#2563eb,#1d4ed8)",
          borderRadius:16,display:"flex",alignItems:"center",justifyContent:"center",
          margin:"0 auto 20px",boxShadow:"0 8px 20px rgba(37,99,235,0.35)",
        }}>
          <Mic size={28} color="#fff"/>
        </div>

        <h1 style={{color:"#0f172a",fontSize:26,fontWeight:800,margin:"0 0 6px",letterSpacing:"-0.02em"}}>
          VoiceHire AI
        </h1>
        <p style={{color:"#64748b",fontSize:14,margin:"0 0 28px"}}>
          Local-first AI recruitment platform
        </p>

        {/* Feature badges */}
        <div style={{display:"flex",flexWrap:"wrap",gap:6,justifyContent:"center",marginBottom:36}}>
          {[
            {Icon:Mic,  label:"Voice AI"},
            {Icon:Mail, label:"Email Automation"},
            {Icon:Zap,  label:"Local Inference"},
          ].map(({Icon,label})=>(
            <span key={label} style={{
              fontSize:12,fontWeight:500,background:"#eff4ff",color:"#2563eb",
              borderRadius:99,padding:"4px 12px",border:"1px solid #bfdbfe",
              display:"inline-flex",alignItems:"center",gap:5,
            }}>
              <Icon size={11}/>{label}
            </span>
          ))}
        </div>

        {err&&(
          <div className="alert alert-error" style={{textAlign:"left",marginBottom:20}}>
            <AlertTriangle size={14}/>{err}
          </div>
        )}

        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          <button onClick={()=>go("recruiter")} disabled={!!loading}
            style={{
              background:loading==="recruiter"?"#1d4ed8":"#2563eb",color:"#fff",
              border:"none",borderRadius:12,padding:"14px 24px",fontSize:14,fontWeight:700,
              cursor:"pointer",fontFamily:"inherit",opacity:loading&&loading!=="recruiter"?0.6:1,
              transition:"all 0.2s",display:"flex",alignItems:"center",justifyContent:"center",gap:8,
              boxShadow:"0 2px 8px rgba(37,99,235,0.35)",
            }}>
            <Briefcase size={16}/>
            {loading==="recruiter"?"Connecting…":"Enter as Recruiter"}
          </button>
          <button onClick={()=>go("candidate")} disabled={!!loading}
            style={{
              background:"#fff",color:"#0f172a",border:"1px solid #e2e5ed",
              borderRadius:12,padding:"14px 24px",fontSize:14,fontWeight:600,
              cursor:"pointer",fontFamily:"inherit",opacity:loading&&loading!=="candidate"?0.6:1,
              transition:"all 0.2s",display:"flex",alignItems:"center",justifyContent:"center",gap:8,
              boxShadow:"0 1px 3px rgba(15,23,42,0.06)",
            }}>
            <User size={16}/>
            {loading==="candidate"?"Connecting…":"Enter as Candidate"}
          </button>
        </div>

        <p style={{color:"#94a3b8",fontSize:11,marginTop:24}}>
          Dev mode · tokens from{" "}
          <code style={{color:"#64748b",background:"#f1f5f9",padding:"1px 5px",borderRadius:4}}>/token</code>
        </p>
      </div>
    </div>
  );
}

// ── App Shell ─────────────────────────────────────────────────────────────────
type Page="voice"|"email-center"|"quick-send";

const NAV_ICONS:{[id:string]:React.ElementType} = {
  voice: Mic, "email-center": Mail, "quick-send": Send,
};

const PAGE_TITLES:{[k in Page]:string} = {
  voice: "Voice Assistant",
  "email-center": "Email Center",
  "quick-send": "Quick Send",
};

export default function App(){
  const {token,role,getToken,login}=useAuth();
  const [page,setPage]=useState<Page>("voice");

  if(!token) return <Login onLogin={login}/>;

  const isRec=role==="recruiter";
  const nav=isRec
    ?[{s:"AI TOOLS",    items:[{id:"voice",         l:"Voice Assistant"}]},
      {s:"EMAIL",       items:[{id:"email-center",   l:"Email Center"},{id:"quick-send",l:"Quick Send"}]}]
    :[{s:"AI TOOLS",    items:[{id:"voice",         l:"Voice Assistant"}]}];

  const TitleIcon = NAV_ICONS[page] || Mic;

  return(
    <div style={{display:"flex",height:"100vh",overflow:"hidden",background:"#f5f6fa",fontFamily:"Inter,system-ui,sans-serif",color:"#0f172a"}}>
      <style>{`
        @keyframes bounce{0%,80%,100%{transform:scale(0.55)}40%{transform:scale(1)}}
        * { box-sizing: border-box; }
        .sidebar-nav-btn:hover {
          background: rgba(255,255,255,0.15) !important;
          color: #ffffff !important;
        }
        .sidebar-nav-btn.active:hover {
          background: #ffffff !important;
          color: #1d4ed8 !important;
        }
        .sidebar-signout-btn:hover {
          background: rgba(255,255,255,0.24) !important;
        }
      `}</style>

      {/* ── Sidebar (vibrant blue matching icon) ─────────────── */}
      <aside style={{
        width:224,flexShrink:0,display:"flex",flexDirection:"column",
        background:"linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%)",
        borderRight:"1px solid #1d4ed8",overflowY:"auto",
      }}>
        {/* Logo */}
        <div style={{padding:"18px 16px 14px",borderBottom:"1px solid rgba(255,255,255,0.15)",display:"flex",alignItems:"center",gap:10}}>
          <div style={{width:32,height:32,background:"#ffffff",borderRadius:8,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,boxShadow:"0 2px 6px rgba(0,0,0,0.15)"}}>
            <Mic size={16} color="#2563eb"/>
          </div>
          <div>
            <div style={{color:"#ffffff",fontWeight:700,fontSize:15,letterSpacing:"-0.3px"}}>VoiceHire</div>
            <div style={{color:"rgba(255,255,255,0.75)",fontSize:10,marginTop:1}}>AI Platform · v2.0</div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{padding:"10px 10px",flex:1}}>
          {nav.map(s=>(
            <div key={s.s}>
              <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.08em",color:"rgba(255,255,255,0.65)",padding:"10px 10px 4px",textTransform:"uppercase"}}>
                {s.s}
              </div>
              {s.items.map(it=>{
                const Icon=NAV_ICONS[it.id]||Mic;
                const active=page===it.id;
                return(
                  <button key={it.id} onClick={()=>setPage(it.id as Page)}
                    className={`sidebar-nav-btn ${active?"active":""}`}
                    style={{
                      display:"flex",alignItems:"center",gap:9,padding:"8px 10px",borderRadius:8,
                      cursor:"pointer",fontSize:13,fontWeight:active?600:500,
                      color:active?"#1d4ed8":"rgba(255,255,255,0.88)",
                      background:active?"#ffffff":"transparent",
                      border:active?"1px solid #ffffff":"1px solid transparent",
                      boxShadow:active?"0 2px 8px rgba(0,0,0,0.12)":"none",
                      width:"100%",textAlign:"left",fontFamily:"inherit",
                      transition:"all 0.15s",marginBottom:2,
                    }}>
                    <Icon size={15} color={active?"#1d4ed8":"rgba(255,255,255,0.88)"}/>
                    {it.l}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div style={{padding:"12px 14px",borderTop:"1px solid rgba(255,255,255,0.15)"}}>
          <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10}}>
            <div style={{width:30,height:30,borderRadius:"50%",background:"rgba(255,255,255,0.2)",border:"1px solid rgba(255,255,255,0.3)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:12,fontWeight:700,color:"#ffffff",flexShrink:0}}>
              {role[0].toUpperCase()}
            </div>
            <div>
              <div style={{color:"#ffffff",fontSize:13,fontWeight:600,textTransform:"capitalize"}}>{role}</div>
              <div style={{color:"rgba(255,255,255,0.7)",fontSize:10}}>Ollama · Whisper · Piper</div>
            </div>
          </div>
          <button onClick={()=>login("","")}
            className="sidebar-signout-btn"
            style={{
              width:"100%",background:"rgba(255,255,255,0.14)",border:"1px solid rgba(255,255,255,0.22)",
              color:"#ffffff",borderRadius:8,padding:"6px 10px",fontSize:12,
              cursor:"pointer",fontFamily:"inherit",display:"flex",alignItems:"center",gap:6,justifyContent:"center",
              transition:"all 0.15s",fontWeight:500,
            }}>
            <LogOut size={12} color="#ffffff"/>Sign out
          </button>
        </div>
      </aside>

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <main style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>
        {/* Topbar */}
        <div style={{
          padding:"0 28px",borderBottom:"1px solid #e2e5ed",height:56,
          display:"flex",alignItems:"center",justifyContent:"space-between",
          flexShrink:0,background:"#ffffff",boxShadow:"0 1px 3px rgba(15,23,42,0.05)",
        }}>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <TitleIcon size={18} style={{color:"#2563eb"}}/>
            <h2 style={{margin:0,fontSize:16,fontWeight:700,color:"#0f172a"}}>{PAGE_TITLES[page]}</h2>
          </div>
          <span style={{
            fontSize:11,fontWeight:700,textTransform:"capitalize",
            background:"#eff4ff",color:"#2563eb",border:"1px solid #bfdbfe",
            padding:"3px 12px",borderRadius:99,
          }}>
            {isRec?"Recruiter":"Candidate"}
          </span>
        </div>

        {/* Content */}
        <div style={{flex:1,overflowY:"auto",padding:"24px 28px",background:"#eef0f6"}}>
          <ErrBound name={PAGE_TITLES[page]}>
            {page==="voice"        && (
              <div className="card">
                <VoiceAssistant role={role} getToken={getToken} apiBase="http://localhost:8000/api"/>
              </div>
            )}
            {page==="email-center" && isRec && <EmailCenter token={token}/>}
            {page==="quick-send"   && isRec && <QuickSend token={token}/>}
          </ErrBound>
        </div>
      </main>
    </div>
  );
}
