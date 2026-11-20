import { afterEach, describe, expect, it, vi } from 'vitest'
import { setLocale } from '@/i18n/index.js'
import { taskApi } from '@/services/taskApi.js'
import { resetCsrf } from '@/services/sessionApi.js'
import { PPO_TASK_WAYPOINT_IDS } from '@/config/dispatchDestinations.js'
afterEach(()=>{vi.unstubAllGlobals();resetCsrf();setLocale('zh-TW')})
describe('task API',()=>{
  it('explains an empty 403 response in the selected language',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:403,text:async()=>''}))
    setLocale('en')
    await expect(taskApi.getTasks()).rejects.toThrow('The server refused this request.')
    setLocale('zh-TW')
    await expect(taskApi.getTasks()).rejects.toThrow('伺服器拒絕此操作')
  })
  it('explains network failures without exposing fetch errors',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    setLocale('en')
    await expect(taskApi.getTasks()).rejects.toThrow('Cannot connect to the task server.')
  })
  it('loads the ordered PPO place contract',async()=>{
    const places=PPO_TASK_WAYPOINT_IDS.map((id,index)=>({id,index,name:id,type:'waypoint'}))
    const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>places})
    vi.stubGlobal('fetch',fetch)
    await expect(taskApi.getPlaces()).resolves.toEqual(places)
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/place')
  })
  it('patches the priority of an existing backend task',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce({ok:true,json:async()=>({token:'test-csrf'})}).mockResolvedValue({ok:true,status:204})
    vi.stubGlobal('fetch',fetch)
    await taskApi.updatePriority('backend-id','high')
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/task/backend-id/priority')
    expect(fetch.mock.calls[1][1].method).toBe('PATCH')
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({priority:'high'})
  })
  it('posts waypoint IDs and nullable optional fields to the real endpoint',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce({ok:true,json:async()=>({token:'test-csrf'})}).mockResolvedValue({ok:true,status:201,json:async()=>({id:'backend-id'})})
    vi.stubGlobal('fetch',fetch)
    const task=await taskApi.createTask({taskType:'medication_delivery',source:'pharmacy',destination:'ward_a_2',priority:'normal',robotId:null,scheduledAt:'2026-10-26T08:11:00+08:00',note:''})
    expect(task.id).toBe('backend-id')
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/task')
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({taskType:'medication_delivery',source:'pharmacy',destination:'ward_a_2',priority:'normal',robotId:null,scheduledAt:'2026-10-26T08:11:00+08:00',note:null})
  })
  it('rejects API validation failures instead of reporting success',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:400,text:async()=>JSON.stringify({errors:{ScheduledAt:['Choose a future time.']}})}))
    await expect(taskApi.getTasks()).rejects.toThrow('Choose a future time.')
  })
})
