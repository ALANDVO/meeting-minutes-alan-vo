import {useState} from 'react'
import type {Meeting,Item,Mutation,User} from './types'
import {ItemEditor} from './ItemEditor'
export function MinutesPanel({meeting,mutate,busy,user,onSource}:{meeting:Meeting;mutate:Mutation;busy:boolean;user:User;onSource:(id:string)=>void}){
 const [editor,setEditor]=useState<Item|'new'|null>(null);const [note,setNote]=useState('');const [transition,setTransition]=useState<{item:Item;status:string}|null>(null)
 const canEdit=user.roles.some(r=>['admin','reviewer'].includes(r));const draft=meeting.status==='draft';const independent=!meeting.contributors.includes(user.subject)
 async function review(decision:string){if(await mutate('/review',{decision,note}))setNote('')}
 return <>
 <section className="panel"><div className="section-heading"><div><p className="eyebrow">REVIEWED CONTENT</p><h2>Minutes & actions</h2></div><button className="secondary" disabled={!canEdit||!draft||busy} onClick={()=>setEditor('new')}>Add sourced item</button></div>
 {!meeting.items.length&&<p className="empty">Adopt a proposal or add an item with a source citation to begin.</p>}
 {meeting.items.map(item=><article className="minute-item" key={item.id}><div className="section-heading"><span className="badge">{item.kind} · {item.status.replaceAll('_',' ')}</span><div className="actions"><button className="text-button" disabled={!canEdit||!draft||busy} onClick={()=>setEditor(item)}>Edit</button><button className="text-button danger" disabled={!canEdit||!draft||busy} onClick={()=>{if(confirm('Remove this item from the draft? The audit event remains.'))void mutate('/items/'+item.id,{},'DELETE')}}>Remove</button></div></div><h3>{item.text}</h3>
 {item.kind==='action'&&<p>Owner: <strong>{item.owner??'Unassigned'}</strong> · Due: {item.due_date??'Unconfirmed'}</p>}
 {item.evidence.map((ref,n)=><blockquote key={n}><p>{ref.quote}</p><button className="text-button" onClick={()=>onSource(ref.turn_id)}>{ref.turn_id} · line {ref.line} · {ref.speaker??'Unattributed'}</button></blockquote>)}
 {item.note&&<p className="muted">{item.note}</p>}
 {item.kind==='action'&&meeting.status==='approved'&&canEdit&&<div className="actions">{(item.status==='done'||item.status==='cancelled'?['open']:['in_progress','blocked','done','cancelled'].filter(s=>s!==item.status)).map(s=><button key={s} className="secondary" disabled={busy} onClick={()=>{setTransition({item,status:s});setNote('')}}>{s.replaceAll('_',' ')}</button>)}</div>}
 </article>)}
 </section>
 {editor&&<ItemEditor key={editor==='new'?'new':editor.id} meeting={meeting} item={editor==='new'?undefined:editor} mutate={mutate} onClose={()=>setEditor(null)} busy={busy}/>}
 <section className="panel"><p className="eyebrow">APPROVAL GATE</p><h2>Confirm the record</h2>{meeting.review_findings?.map((f,n)=><p className="warning" key={n}>{f.message}</p>)}
 {meeting.review_note&&<blockquote>{meeting.review_note}</blockquote>}
 {draft&&<><p className="muted">Submission freezes content until an independent account approves it or requests changes. Missing owners and dates remain visible warnings.</p><button disabled={!canEdit||busy||!meeting.items.length} onClick={()=>void mutate('/submit',{})}>Submit for review</button></>}
 {meeting.status==='submitted'&&<><label>Review note<textarea required value={note} onChange={e=>setNote(e.target.value)} maxLength={2000}/></label>{!independent&&<p className="warning">You contributed to these minutes. Another signed-in account must review them.</p>}<div className="actions"><button disabled={!canEdit||!independent||busy||!note.trim()} onClick={()=>void review('approve')}>Approve minutes</button><button className="secondary" disabled={!canEdit||!independent||busy||!note.trim()} onClick={()=>void review('request_changes')}>Request changes</button></div></>}
 {meeting.status==='approved'&&<p>Approved by <strong>{meeting.approval?.actor}</strong> at revision {meeting.approval?.revision}. Subsequent action-status changes do not alter that approved snapshot.</p>}
 {!draft&&<div className="reopen"><label>Reason to reopen as a draft<input value={note} onChange={e=>setNote(e.target.value)} maxLength={1000}/></label><button className="secondary" disabled={!canEdit||busy||!note.trim()} onClick={()=>void mutate('/reopen',{reason:note})}>Reopen draft</button></div>}
 </section>
 {transition&&<section className="panel editor"><h2>Mark action {transition.status.replaceAll('_',' ')}</h2><p>{transition.item.text}</p><label>Reason / completion evidence<textarea value={note} onChange={e=>setNote(e.target.value)} maxLength={1000}/></label><div className="actions"><button disabled={busy||!note.trim()} onClick={async()=>{try{if(await mutate('/items/'+transition.item.id+'/transition',{status:transition.status,reason:note})){setTransition(null);setNote('')}}catch{/* Keep the form available to correct the error. */}}}>Confirm status change</button><button className="secondary" onClick={()=>setTransition(null)}>Cancel</button></div></section>}
 </>
}
