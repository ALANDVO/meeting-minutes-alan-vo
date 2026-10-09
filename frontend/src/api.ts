let csrf=''
export function setCsrf(token:string){csrf=token}
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
  const response=await fetch('/api'+path,{credentials:'include',...options,headers:{'Content-Type':'application/json',...(csrf?{'X-CSRF-Token':csrf}:{}),...options.headers}})
  if(!response.ok){
    let message=`Request failed (${response.status})`
    try{const data=await response.json();message=data.error?.message??(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)??message)}catch{/* An empty HTTP error response still has a useful status. */}
    throw new Error(message)
  }
  return response.status===204?undefined as T:await response.json() as T
}
export function write<T>(path:string,data:unknown,method='POST'){return api<T>(path,{method,body:JSON.stringify(data)})}
export function errorMessage(error:unknown){return error instanceof Error?error.message:'Unexpected request failure'}
