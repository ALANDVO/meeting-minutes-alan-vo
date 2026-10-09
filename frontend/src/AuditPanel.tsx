import {useEffect,useState} from 'react'
import {api,errorMessage} from './api'
import type {Audit} from './types'
export function AuditPanel({meetingId}:{meetingId?:string}){
 const [rows,setRows]=useState<Audit[]>([]);const [error,setError]=useState('')
 useEffect(()=>{let alive=true;api<Audit[]>('/audit'+(meetingId?'?meeting_id='+encodeURIComponent(meetingId):'')).then(r=>{if(alive)setRows(r)}).catch(e=>{if(alive)setError(errorMessage(e))});return()=>{alive=false}},[meetingId])
 return <section className="panel"><p className="eyebrow">ACCOUNTABILITY</p><h2>Recent changes</h2><p className="muted">Latest 200 events. The database retains 5,000 events; exports are available per meeting.</p>{error&&<p role="alert" className="error">{error}</p>}<div className="table-scroll"><table><thead><tr><th>When</th><th>Actor</th><th>Change</th><th>Revision</th><th>Details</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{new Date(r.at).toLocaleString()}</td><td>{r.actor}</td><td>{r.action}</td><td>{r.revision}</td><td><code>{JSON.stringify(r.detail)}</code></td></tr>)}</tbody></table></div>{!rows.length&&!error&&<p className="empty">No audit events yet.</p>}</section>
}
