import type {Meeting,Mutation} from './types'
export function ProposalPanel({meeting,mutate,busy,editable,onSource}:{meeting:Meeting;mutate:Mutation;busy:boolean;editable:boolean;onSource:(id:string)=>void}){
 const used=new Set(meeting.items.map(i=>i.proposal_id));const pending=meeting.proposals.filter(p=>!used.has(p.id))
 return <section className="panel"><div className="section-heading"><div><p className="eyebrow">SOURCE-LINKED CANDIDATES</p><h2>Review proposals <span className="count">{pending.length}</span></h2></div><button className="secondary" disabled={!editable||busy||!pending.length} onClick={()=>void mutate('/adopt',{proposal_ids:pending.map(p=>p.id)})}>Adopt all into draft</button></div>
 <p className="muted">Adopting a proposal does not approve it. Confirm wording, owners and deadlines before submitting the minutes.</p>
 {!pending.length?<p className="empty">No remaining proposals. You can add a sourced item manually.</p>:pending.map(p=><article className="proposal" key={p.id}><span className="badge">{p.kind}</span><h3>{p.text}</h3><p>{p.owner??'Owner unresolved'} {p.kind==='action'&&<>· {p.due.date??'Deadline unconfirmed'}</>}</p>
 {!!p.flags.length&&<p className="warning">{p.flags.join(' · ').replaceAll('_',' ')}</p>}
 <div className="actions"><button disabled={!editable||busy} onClick={()=>void mutate('/adopt',{proposal_ids:[p.id]})}>Adopt proposal</button><button className="text-button" onClick={()=>onSource(p.evidence[0].turn_id)}>Inspect source {p.evidence[0].turn_id}</button></div></article>)}
 </section>
}
