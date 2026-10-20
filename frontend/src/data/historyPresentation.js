// History-only presentation; existing dispatch and other page palettes stay unchanged.
const palettes = {
 medicine:{from:'#f4bb8c',to:'#fff0dc',ink:'#ab5420'},
 specimen:{from:'#d6b4e7',to:'#f3e9fa',ink:'#765194'},
 supplies:{from:'#a6dccd',to:'#e9f7f2',ink:'#287e70'},
 documents:{from:'#aed2f0',to:'#e7f3ff',ink:'#386ea3'},
 waste:{from:'#f4b0a9',to:'#fceae7',ink:'#b64d49'},
 cleaning:{from:'#f3d282',to:'#fff5d8',ink:'#9e7625'},
 inspection:{from:'#f6dfcf',to:'#fff2e6',ink:'#997255'},
 charging:{from:'#f2e3b8',to:'#fff8df',ink:'#96803f'},
 other:{from:'#e5e1db',to:'#f8f6f2',ink:'#7d7469'},
}
const taskNames = {
 '藥品配送':'medicine','藥品盤點配送':'medicine',
 '檢體配送':'specimen','檢體運送':'specimen','檢驗報告運送':'specimen',
 '一般配送':'supplies','病房物資補充':'supplies','物資補充':'supplies',
 '門診文件配送':'documents','文件配送':'documents',
 '廢棄物收集':'waste','醫療廢棄物運送':'waste',
 '清潔用品補充':'cleaning',
 '前往護理站':'inspection','前往護理站／巡檢':'inspection','巡檢':'inspection',
 '充電':'charging','前往充電':'charging','返回充電站':'charging',
}
export const taskColorMap = Object.freeze(Object.fromEntries(Object.entries(taskNames).map(([name,key])=>[name,palettes[key]])))
// The theme orange is resolved from the same token used by Hospital RMF Overview.
export const historyStatusColors=Object.freeze({
 all:'var(--theme-primary)',
 completed:'#679A7B',
 cancelled:'#6489C7',
 failed:'#C47C70',
})
export const getHistoryTaskColor = name => taskColorMap[String(name||'').trim()] || palettes.other
export const historyTaskStyle = name => {
 const color=getHistoryTaskColor(name)
 return {'--task-from':color.from,'--task-to':color.to,'--task-ink':color.ink}
}
export const historyStatusPresentation = {
 completed:{label:'已完成',icon:'CircleCheck',color:'#6e9878'},
 running:{label:'執行中',icon:'Activity',color:'#c78d4a'},
 waiting:{label:'等待中',icon:'Clock',color:'#a59168'},
 failed:{label:'失敗',icon:'CircleAlert',color:'#c67870'},
 cancelled:{label:'已取消',icon:'CircleMinus',color:'#6489C7'},
}
export function summarizeHistory(events) {
 return {
 total:events.length,
 completed:events.filter(event=>event.status==='completed').length,
 cancelled:events.filter(event=>event.status==='cancelled').length,
 failed:events.filter(event=>event.status==='failed').length,
 }
}
