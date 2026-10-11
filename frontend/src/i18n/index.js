import { computed, watch } from 'vue'
import { createI18n } from 'vue-i18n'
import zhTW from './locales/zh-TW.js'
import en from './locales/en.js'

const STORAGE_KEY = 'hospital-rmf-locale'
const readLocale = () => { try { return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'zh-TW' } catch { return 'zh-TW' } }
export const i18n = createI18n({ legacy:false, globalInjection:true, locale:readLocale(), fallbackLocale:'zh-TW', messages:{'zh-TW':zhTW,en} })
export const locale = i18n.global.locale
export const localeTag = computed(() => locale.value === 'en' ? 'en-US' : 'zh-TW')
export const setLocale = (next) => {
  locale.value = next === 'en' ? 'en' : 'zh-TW'
  if (typeof document !== 'undefined') document.documentElement.lang = locale.value
  try { localStorage.setItem(STORAGE_KEY, locale.value) } catch { /* Locale remains active without storage. */ }
}
// Read the reactive locale in the caller's render/computed effect. Vue I18n's
// global `t` wrapper alone does not register that effect as a locale subscriber.
export const t = (key, ...args) => { locale.value; return i18n.global.t(key, ...args) }
export const translateTask = (value) => { const key=`tasks.${value}`; return i18n.global.te(key) ? t(key) : value }
export const translateLocation = (value) => { const key=`locations.${value}`; return i18n.global.te(key) ? t(key) : value }
if (typeof document !== 'undefined') document.documentElement.lang = locale.value

const phraseMap = new Map()
const collectPhrases = (source,target) => {
  for (const [key,value] of Object.entries(source)) {
    const translated=target?.[key]
    if (typeof value==='string' && typeof translated==='string' && value!==translated) phraseMap.set(value,translated)
    else if (value && typeof value==='object' && translated && typeof translated==='object') collectPhrases(value,translated)
  }
}
collectPhrases(zhTW,en)
for (const [source,target] of Object.entries(en.legacy)) phraseMap.set(source,target)
const dynamicPhrases = [
  [/^(\d+)\s*分鐘$/u, match=>`${match[1]} min`],
  [/^(\d+)\s*個$/u, match=>`${match[1]} items`],
  [/^(\d+)\s*任務$/u, match=>`${match[1]} tasks`],
  [/^(\d+)\s*項任務$/u, match=>`${match[1]} tasks`],
  [/^(\d{4})年(\d{1,2})月(\d{1,2})日$/u, match=>new Intl.DateTimeFormat('en-US',{year:'numeric',month:'long',day:'numeric'}).format(new Date(Number(match[1]),Number(match[2])-1,Number(match[3])))],
  [/^週([一二三四五六日])$/u, match=>({一:'Mon',二:'Tue',三:'Wed',四:'Thu',五:'Fri',六:'Sat',日:'Sun'})[match[1]]],
  [/^(\d+)\s*台$/u, match=>`${match[1]} robots`],
  [/^(全部|執行中|待命)\s+(\d+)$/u, match=>`${phraseMap.get(match[1])||match[1]} ${match[2]}`],
  [/^(低|一般|高|緊急)優先級$/u, match=>`${phraseMap.get(match[1])||match[1]} priority`],
  [/^(低|一般|高|緊急)優先級・(去程|回程)$/u, match=>`${phraseMap.get(match[1])||match[1]} priority · ${phraseMap.get(match[2])||match[2]}`],
  [/^([A-Za-z]+\d+)\u3000(.+)$/u, match=>`${match[1]}　${phraseMap.get(match[2])||match[2]}`],
  [/^(Robot \d+)・(可用|離線)・(\d+)%$/u, match=>`${match[1]}・${phraseMap.get(match[2])||match[2]}・${match[3]}%`],
  [/^(Robot \d+)・(執行中|待命|充電中)・(\d+)%$/u, match=>`${match[1]} · ${phraseMap.get(match[2])||match[2]} · ${match[3]}%`],
  [/^(\d{4})年(\d{1,2})月(\d{1,2})日・(星期[一二三四五六日])$/u, match=>`${new Intl.DateTimeFormat('en-US',{year:'numeric',month:'long',day:'numeric'}).format(new Date(Number(match[1]),Number(match[2])-1,Number(match[3])))}・${phraseMap.get(match[4])||match[4]}`],
  [/^滾輪縮放 · ([\d.]+) px\/分鐘 · (\d+) 秒刻度$/u, match=>`Scroll to zoom · ${match[1]} px/min · ${match[2]} sec scale`],
  [/^等待\s*(\d+)\s*項$/u, match=>`Waiting: ${match[1]}`],
  [/^預估\s*(\d+)\s*分鐘$/u, match=>`Estimated ${match[1]} min`],
  [/^電量\s*(\d+)%$/u, match=>`Battery ${match[1]}%`],
  [/^完成\s*(\d+)\s*\/\s*(\d+)$/u, match=>`Completed ${match[1]} / ${match[2]}`],
  [/^最大速度\s*(.+)$/u, match=>`Maximum speed ${match[1]}`],
  [/^預估可運行\s*(.+)$/u, match=>`Estimated runtime ${match[1]}`],
  [/^待處理\s*(\d+)\s*項・預計\s*(.+)\s*可用$/u, match=>`${match[1]} queued · available at ${match[2]}`],
  [/^待處理\s*(\d+)\s*項・尚無預估$/u, match=>`${match[1]} queued · no estimate`],
  [/^目前等待任務：(.+)$/u, match=>`Queued tasks: ${match[1]}`],
  [/^最近機器人：(.+)$/u, match=>`Nearest robot: ${match[1]}`],
  [/^距離：(.+)$/u, match=>`Distance: ${match[1]}`],
  [/^預覽 · (.+)$/u, match=>`Preview · ${match[1]}`],
]

// This bridge translates literal copy in existing Vue views from one central catalogue.
// Task IDs, Robot IDs, and backend values are untouched because only known UI phrases match.
export function installGlobalTranslation(root) {
  if (!root || typeof MutationObserver==='undefined') return () => {}
  const textOriginal=new WeakMap(),attributeOriginal=new WeakMap()
  const englishText=(value) => {
    const trimmed=value.trim(),replacement=phraseMap.get(trimmed)
    if(replacement) return value.replace(trimmed,replacement)
    for(const [pattern,format] of dynamicPhrases) { const match=trimmed.match(pattern); if(match)return value.replace(trimmed,format(match)) }
    if(trimmed.includes(' · ')) {
      const pieces=trimmed.split(' · ')
      const translated=pieces.map(piece=>{
        if(phraseMap.has(piece))return phraseMap.get(piece)
        const date=piece.match(/^(\d{1,2})月(\d{1,2})日$/u)
        return date ? new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric'}).format(new Date(2026,Number(date[1])-1,Number(date[2]))) : piece
      })
      if(translated.some((part,index)=>part!==pieces[index]))return value.replace(trimmed,translated.join(' · '))
    }
    return value
  }
  const translateText=(node) => {
    if (!node.textContent?.trim() || node.parentElement?.closest('script,style,textarea')) return
    let original=textOriginal.get(node)
    const current=node.textContent
    if (original===undefined || (current!==original && current!==englishText(original))) { original=current; textOriginal.set(node,original) }
    const translated=translatedText(original)
    if (current!==translated) node.textContent=translated
  }
  const translatedText=(value) => {
    return locale.value==='en' ? englishText(value) : value
  }
  const translateAttributes=(element) => {
    if (!(element instanceof Element)) return
    const names=['placeholder','aria-label','title']
    const originals=attributeOriginal.get(element)||{}
    for (const name of names) {
      if (!element.hasAttribute(name)) continue
      const current=element.getAttribute(name)
      let original=originals[name]
      if (original===undefined || (current!==original && current!==englishText(original))) { original=current; originals[name]=original }
      const translated=translatedText(original)
      if (current!==translated) element.setAttribute(name,translated)
    }
    attributeOriginal.set(element,originals)
  }
  const scan=(element) => {
    if (element.nodeType===Node.TEXT_NODE) { translateText(element); return }
    if (element.nodeType!==Node.ELEMENT_NODE) return
    translateAttributes(element)
    const walker=document.createTreeWalker(element,NodeFilter.SHOW_TEXT)
    while (walker.nextNode()) translateText(walker.currentNode)
    element.querySelectorAll('[placeholder],[aria-label],[title]').forEach(translateAttributes)
  }
  const observer=new MutationObserver(records=>{for(const record of records){if(record.type==='characterData')scan(record.target);else if(record.type==='attributes')translateAttributes(record.target);else for(const node of record.addedNodes)scan(node)}})
  observer.observe(root,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','aria-label','title']})
  const stop=watch(locale,()=>scan(root),{flush:'post'})
  scan(root)
  return ()=>{stop();observer.disconnect()}
}
