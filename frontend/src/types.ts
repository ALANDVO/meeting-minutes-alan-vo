export interface User {subject:string;username:string;roles:string[];csrf_token:string}
export interface Evidence {turn_id:string;quote:string;start:number;end:number;speaker:string|null;line:number}
export interface Turn {id:string;line:number;speaker:string|null;raw_speaker:string|null;timestamp:string|null;text:string;start:number;end:number}
export interface Item {id:string;kind:'action'|'decision'|'question';text:string;owner:string|null;due_date:string|null;status:string;evidence:Evidence[];note:string;proposal_id?:string;source:string}
export interface Proposal {id:string;kind:Item['kind'];text:string;owner:string|null;due:{raw:string;date:string|null;rule:string;warning:string|null};evidence:Evidence[];flags:string[];rule:string;source:string}
export interface Digest {counts:Record<string,number>;unassigned_actions:number;undated_actions:number;done_actions:number;open_questions:number}
export interface MeetingSummary {id:string;title:string;meeting_date:string;kind:string;revision:number;status:string;updated_at:string;digest:Digest}
export interface Meeting extends MeetingSummary {participants:string[];document:{text:string;sha256:string;turns:Turn[];unknown_speakers:string[]};items:Item[];proposals:Proposal[];warnings:string[];created_by:string;contributors:string[];approval:{actor:string;revision:number;note:string}|null;review_note:string;review_findings:{severity:string;message:string;item_id?:string}[]}
export interface MeetingInput {title:string;meeting_date:string;participants:string[];transcript:string;kind:string}
export interface Audit {id:number;meeting_id:string;actor:string;action:string;revision:number;detail:Record<string,unknown>;at:string}
export interface Evaluation {cases:number;true_positive:number;false_positive:number;false_negative:number;precision:number;recall:number;f1:number;owner_matches:number;owner_evaluated:number;limitations:string[];rows:{case:string;transcript:string;expected:string;predicted:string;correct:boolean;flags:string[]}[]}
export type Mutation = (path:string,data:Record<string,unknown>,method?:string)=>Promise<boolean>
