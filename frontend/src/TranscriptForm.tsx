import {useState} from 'react'
import type {MeetingInput} from './types'
export const sample:MeetingInput={title:'Release readiness review',meeting_date:'2026-10-09',participants:['Alex','Sam'],kind:'planning',transcript:'[00:01] Alex: I will write the rollback checklist by tomorrow.\n[00:12] Sam: Decision: keep the current API version until the migration tests pass.\n[00:25] Alex: ACTION: Sam will review the dashboard by Monday.\n[00:42] Sam: Question: Who approves the retention policy?\n[00:55] Alex: The staging build is green.'}
export function TranscriptForm({onCreate,busy}:{onCreate:(input:MeetingInput)=>Promise<void>;busy:boolean}){
 const [form,setForm]=useState<MeetingInput>({...sample,transcript:'',title:''});const [names,setNames]=useState('Alex, Sam')
 function field(key:keyof MeetingInput,value:string){setForm({...form,[key]:value})}
 return <section className="panel"><p className="eyebrow">NEW MEETING</p><h2>Turn a transcript into accountable minutes</h2><p className="muted">Paste text, confirm the roster and review every proposed action. Audio transcription is outside this app.</p>
 <form onSubmit={e=>{e.preventDefault();void onCreate({...form,participants:names.split(',').map(n=>n.trim()).filter(Boolean)})}}>
 <div className="form-grid"><label>Meeting title<input required maxLength={160} value={form.title} onChange={e=>field('title',e.target.value)}/></label><label>Meeting date<input required type="date" value={form.meeting_date} onChange={e=>field('meeting_date',e.target.value)}/></label></div>
 <label>Participants, separated by commas<input required value={names} onChange={e=>setNames(e.target.value)}/></label>
 <label>Meeting type<select aria-label="Meeting type" value={form.kind} onChange={e=>field('kind',e.target.value)}>{['general','standup','design_review','one_on_one','planning','retrospective'].map(k=><option key={k} value={k}>{k.replaceAll('_',' ')}</option>)}</select></label>
 <label>Transcript<textarea required rows={12} maxLength={100000} value={form.transcript} onChange={e=>field('transcript',e.target.value)} placeholder="[00:01] Alex: I will review the migration by Friday."/></label>
 <p className="muted">{form.transcript.length.toLocaleString()} / 100,000 characters · Speaker labels must match the roster. Dates are anchored to the meeting date.</p>
 <div className="actions"><button disabled={busy} type="submit">Create draft</button><button disabled={busy} type="button" className="secondary" onClick={()=>{setForm({...sample});setNames(sample.participants.join(', '))}}>Load sample transcript</button></div>
 </form></section>
}
