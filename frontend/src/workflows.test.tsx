import {render,screen,fireEvent,waitFor} from '@testing-library/react'
import {describe,it,expect,vi,afterEach} from 'vitest'
import {cleanup} from '@testing-library/react'
import {TranscriptForm} from './TranscriptForm'
import {ProposalPanel} from './ProposalPanel'
import {ItemEditor} from './ItemEditor'
import {AdvicePanel} from './AdvicePanel'
import {MinutesPanel} from './MinutesPanel'
import type {Meeting,User} from './types'
const quote='I will write tests by tomorrow.'
const evidence={turn_id:'t0001',quote,start:0,end:quote.length,speaker:'Alex',line:1}
const meeting={id:'m1',title:'Release',meeting_date:'2026-10-09',kind:'planning',revision:3,status:'draft',participants:['Alex','Sam'],items:[],proposals:[{id:'p1',kind:'action',text:'write tests by tomorrow.',owner:'Alex',due:{date:'2026-10-10',raw:'tomorrow',rule:'relative_day',warning:null},evidence:[evidence],flags:[],rule:'speaker_commitment',source:'rules'}],document:{text:quote,sha256:'example-digest',turns:[{id:'t0001',text:quote,speaker:'Alex',line:1,start:0,end:quote.length,raw_speaker:'Alex',timestamp:null}],unknown_speakers:[]},contributors:['author'],created_by:'author',approval:null,review_note:'',review_findings:[],warnings:[],updated_at:'2026-10-09',digest:{counts:{action:0},unassigned_actions:0,undated_actions:0,done_actions:0,open_questions:0}} satisfies Meeting
const user:User={subject:'author',username:'Alex',roles:['reviewer'],csrf_token:'test'}
afterEach(cleanup)

describe('review workflows',()=>{
 it('loads a realistic sample and submits the roster with the transcript',async()=>{const save=vi.fn().mockResolvedValue(undefined);render(<TranscriptForm onCreate={save} busy={false}/>);fireEvent.click(screen.getByText('Load sample transcript'));fireEvent.click(screen.getByText('Create draft'));await waitFor(()=>expect(save).toHaveBeenCalled());expect(save.mock.calls[0][0].participants).toEqual(['Alex','Sam']);expect(save.mock.calls[0][0].transcript).toContain('rollback checklist')})
 it('adopts a proposal separately from approval and exposes its source',()=>{const change=vi.fn().mockResolvedValue(true);const source=vi.fn();render(<ProposalPanel meeting={meeting} mutate={change} onSource={source} busy={false} editable/>);fireEvent.click(screen.getByText('Adopt proposal'));expect(change).toHaveBeenCalledWith('/adopt',{proposal_ids:['p1']});fireEvent.click(screen.getByText('Inspect source t0001'));expect(source).toHaveBeenCalledWith('t0001')})
 it('keeps an unsaved item open on a revision conflict',async()=>{const change=vi.fn().mockResolvedValue(false);const close=vi.fn();render(<ItemEditor meeting={meeting} mutate={change} onClose={close} busy={false}/>);fireEvent.change(screen.getByLabelText('Item text'),{target:{value:'Write tests'}});fireEvent.click(screen.getByText('Save item'));await waitFor(()=>expect(change).toHaveBeenCalled());expect(close).not.toHaveBeenCalled();expect(change.mock.calls[0][1].item.evidence[0].quote).toBe(quote)})
 it('requires explicit consent before requesting model assistance',()=>{render(<AdvicePanel meeting={meeting} mutate={vi.fn()} busy={false} editable/>);expect(screen.getByText('Request suggestions')).toBeDisabled();fireEvent.click(screen.getByRole('checkbox'));expect(screen.getByText('Request suggestions')).toBeEnabled()})
 it('prevents the author from approving their own minutes',()=>{render(<MinutesPanel meeting={{...meeting,status:'submitted'}} mutate={vi.fn()} busy={false} user={user} onSource={vi.fn()}/>);fireEvent.change(screen.getByLabelText('Review note'),{target:{value:'Looks correct'}});expect(screen.getByText('Approve minutes')).toBeDisabled();expect(screen.getByText(/Another signed-in account must review/)).toBeInTheDocument()})
})
