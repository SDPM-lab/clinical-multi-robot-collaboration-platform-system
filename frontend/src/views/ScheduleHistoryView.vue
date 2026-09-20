<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { Activity, AlertCircle, ArrowRight, Ban, CalendarDays, Check, ChevronLeft, ChevronRight, Clock, Filter, Maximize2, Minimize2, Search } from '@lucide/vue'
import SharedLoading from '@/components/SharedLoading.vue'
import HistorySummary from '@/components/history/HistorySummary.vue'
import HospitalMiniMap from '@/components/dispatch/HospitalMiniMap.vue'
import { addDays, dayKey, eventsOnDay, filterHistory, historyRange, monthDays, parseDay, weekStart } from '@/data/scheduleHistory.js'
import { isHistoryEventOverdue } from '@/data/historyPresentation.js'
import { localeTag, t, translateLocation, translateTask } from '@/i18n/index.js'

const today=dayKey(new Date())
const selectedDate=ref(today)
const calendarMonth=ref(today)
const view=ref('weekly')
const statusFilter=ref('all')
const query=ref('')
const filterOpen=ref(false)
const mapExpanded=ref(false)
const filters=reactive({priority:[],robotId:[]})
const source=shallowRef(null)
const loading=ref(true)
const loadError=ref('')
let loadGeneration=0
const loadHistory=async()=>{
  const generation=++loadGeneration
  loading.value=true
  loadError.value=''
  try {
    const module=await import('@/data/scheduleHistorySource.js')
    if(generation===loadGeneration)source.value=module.createHistorySource()
  } catch {
    if(generation===loadGeneration)loadError.value='load-error'
  } finally {
    if(generation===loadGeneration)loading.value=false
  }
}
const events=computed(()=>source.value?.value.events||[])
const error=computed(()=>loadError.value||source.value?.value.error?t('history.loadError'):'')
let initialDateResolved=false
watch(events,items=>{
  if(initialDateResolved||!items.length)return
  initialDateResolved=true
  if(!eventsOnDay(items,today).length){
    const latest=[...items].sort((a,b)=>Date.parse(b.start)-Date.parse(a.start))[0]
    selectedDate.value=dayKey(new Date(latest.start))
    calendarMonth.value=selectedDate.value
  }
},{immediate:true})

const range=computed(()=>historyRange(selectedDate.value,view.value))
const previousRange=computed(()=>{
  if(view.value==='daily')return [addDays(range.value[0],-1),range.value[0]]
  if(view.value==='weekly')return [addDays(range.value[0],-7),range.value[0]]
  const previousMonth=parseDay(range.value[0])
  previousMonth.setMonth(previousMonth.getMonth()-1)
  return [dayKey(previousMonth),range.value[0]]
})
const matches=computed(()=>{
  const search=query.value.trim().toLocaleLowerCase()
  return filterHistory(events.value,filters).filter(event=>{
    if(!search)return true
    return [event.taskId,event.title,translateTask(event.title),event.robotId,event.robotName,event.startLocation,translateLocation(event.startLocation),event.endLocation,translateLocation(event.endLocation)]
      .join(' ').toLocaleLowerCase().includes(search)
  })
})
const overlaps=(event,period)=>Date.parse(event.start)<parseDay(period[1]).getTime()&&Date.parse(event.end)>parseDay(period[0]).getTime()
const rangeEvents=computed(()=>matches.value.filter(event=>overlaps(event,range.value)).sort((a,b)=>Date.parse(b.start)-Date.parse(a.start)||a.taskId.localeCompare(b.taskId)))
const previousEvents=computed(()=>matches.value.filter(event=>overlaps(event,previousRange.value)))
const inRange=computed(()=>rangeEvents.value.filter(event=>statusFilter.value==='all'||(statusFilter.value==='overdue'?isHistoryEventOverdue(event):event.status===statusFilter.value)))
const selectedId=ref(null)
watch(inRange,items=>{if(!items.some(item=>item.id===selectedId.value))selectedId.value=items[0]?.id||null},{immediate:true})
const selectedEvent=computed(()=>inRange.value.find(item=>item.id===selectedId.value)||null)
const groups=computed(()=>[...new Set(inRange.value.map(event=>dayKey(new Date(event.start))))].map(key=>({key,events:inRange.value.filter(event=>dayKey(new Date(event.start))===key)})))

const monthKeys=computed(()=>monthDays(calendarMonth.value))
const monthTitle=computed(()=>parseDay(calendarMonth.value).toLocaleDateString(localeTag.value,{year:'numeric',month:'long'}))
const formatDate=key=>parseDay(key).toLocaleDateString(localeTag.value,{year:'numeric',month:'long',day:'numeric',weekday:'short'})
const weekdays=computed(()=>Array.from({length:7},(_,i)=>{
 const label=parseDay(addDays('2026-09-14',i)).toLocaleDateString(localeTag.value,{weekday:'short'})
 return localeTag.value.startsWith('zh')?label.replace(/^週/,''):label
}))
const time=value=>new Date(value).toLocaleTimeString(localeTag.value,{hour:'2-digit',minute:'2-digit',hour12:false})
const duration=event=>Math.max(0,Math.round((Date.parse(event.end)-Date.parse(event.start))/60000))
const displayStatus=event=>isHistoryEventOverdue(event)?'overdue':event.status
const eventCount=key=>eventsOnDay(events.value,key).length
const getDateIntensity=count=>count<=0?'none':count===1?'low':count<=3?'medium':count<=5?'high':'very-high'
const dateTooltip=key=>`${formatDate(key)}・${eventCount(key)} ${t('common.tasks')}`
const selectedWeekStart=computed(()=>weekStart(selectedDate.value))
const selectedWeekEnd=computed(()=>addDays(selectedWeekStart.value,7))
const calendarClasses=key=>{
 const outside=key.slice(0,7)!==calendarMonth.value.slice(0,7)
 const intensity=outside?'none':getDateIntensity(eventCount(key))
 const inWeek=view.value==='weekly'&&key>=selectedWeekStart.value&&key<selectedWeekEnd.value
 const selected=key===selectedDate.value
 const current=key===today
 const weeklyOutside=view.value==='weekly'&&!inWeek
 const dailyOutside=view.value==='daily'&&!selected
 const visibleIntensity=weeklyOutside||dailyOutside?'none':intensity
 const tone=selected
  ?'calendar-selected'
  :view.value==='weekly'&&inWeek
    ?`calendar-week-${visibleIntensity}`
    :view.value==='monthly'&&current
      ?'calendar-today'
      :view.value==='monthly'&&visibleIntensity!=='none'
        ?`calendar-density-${visibleIntensity}`
        :'calendar-default'
 return {
  'is-anchor':selected,
  'is-today':current,
  'is-outside':outside,
  'is-in-week':inWeek,
  'is-week-start':inWeek&&key===selectedWeekStart.value,
  'is-week-end':inWeek&&key===addDays(selectedWeekEnd.value,-1),
  [`intensity-${visibleIntensity}`]:true,
  [tone]:true,
 }}
const selectDay=async key=>{
  selectedDate.value=key
  calendarMonth.value=key
  selectedId.value=null
  await nextTick()
  selectedId.value=inRange.value[0]?.id||null
}
const selectMode=mode=>{view.value=mode;calendarMonth.value=selectedDate.value}
const moveCalendarMonth=amount=>{
  const date=parseDay(calendarMonth.value)
  date.setDate(1)
  date.setMonth(date.getMonth()+amount)
  calendarMonth.value=dayKey(date)
  if(view.value==='monthly')selectedDate.value=calendarMonth.value
}
const moveDate=amount=>{
  if(view.value==='monthly'){
    const date=parseDay(selectedDate.value)
    date.setDate(1)
    date.setMonth(date.getMonth()+amount)
    selectedDate.value=dayKey(date)
  }else selectedDate.value=addDays(selectedDate.value,amount*(view.value==='weekly'?7:1))
  calendarMonth.value=selectedDate.value
}
const resetFilters=()=>{filters.priority=[];filters.robotId=[];statusFilter.value='all';query.value='';filterOpen.value=false}
const activeFilterCount=computed(()=>filters.priority.length+filters.robotId.length)
const robots=computed(()=>[...new Set(events.value.map(event=>event.robotId).filter(Boolean))])
const priorityOptions=['urgent','high','normal','low']
const statusIcons={completed:Check,running:Activity,failed:AlertCircle,waiting:Clock,cancelled:Ban}

const timelineKeys=['created','received','toOrigin','pickedUp','toDestination','completed']
const stageProgress=event=>event.timelineProgress??({completed:6,running:4,waiting:1,failed:5,cancelled:2}[event.status]||6)
const timeline=computed(()=>{
  const event=selectedEvent.value
  if(!event)return []
  const start=Date.parse(event.start),end=Date.parse(event.end),span=Math.max(1,end-start)
  const fractions=[-.05,0,.18,.4,.57,1]
  const notes=[event.startLocation,event.robotName,event.startLocation,event.startLocation,event.endLocation,event.endLocation]
  const step=(key,index,state)=>({key,state,time:event.timeline?.[index]?.time||new Date(start+span*fractions[index]).toISOString(),note:event.timeline?.[index]?.note||notes[index]})
  if(event.status==='completed')return timelineKeys.map((key,index)=>step(key,index,'done'))
  const reached=Math.max(1,Math.min(5,stageProgress(event)))
  if(event.status==='cancelled'||event.status==='failed'){
    return [...timelineKeys.slice(0,reached).map((key,index)=>step(key,index,'done')),
      {key:event.status,state:'terminal',time:event.end,note:event.timeline?.[reached-1]?.note||event.startLocation}]
  }
  return timelineKeys.slice(0,reached).map((key,index)=>step(key,index,index===reached-1?'current':'done'))
})
onMounted(loadHistory)
onBeforeUnmount(()=>{loadGeneration++})
</script>

<template>
  <section class="schedule-history-page" :aria-label="t('history.title')">
    <div class="history-main-column">
      <HistorySummary
        class="history-stats"
        :events="rangeEvents"
        :previous-events="previousEvents"
        :period="view"
        :selected-status="statusFilter"
        @select="statusFilter=$event"
      />
      <main class="history-list-panel schedule-history-panel">
        <header class="list-header">
          <div class="heading-copy"><h1>{{t('history.title')}}</h1><span>{{inRange.length}} {{t('common.tasks')}}</span></div>
          <div class="header-controls">
            <label class="history-search"><Search :size="17"/><input v-model="query" type="search" :placeholder="t('history.search')" :aria-label="t('history.search')"/></label>
            <div class="filter-root">
              <button type="button" class="icon-control" :class="{'is-active':filterOpen||activeFilterCount}" :aria-expanded="filterOpen" :aria-label="t('common.filter')" @click="filterOpen=!filterOpen"><Filter :size="17"/><i v-if="activeFilterCount">{{activeFilterCount}}</i></button>
              <div v-if="filterOpen" class="filter-popover">
                <strong>{{t('common.filter')}}</strong>
                <small>{{t('history.robot')}}</small>
                <div class="filter-choice"><button v-for="robot in robots" :key="robot" type="button" :aria-pressed="filters.robotId.includes(robot)" @click="filters.robotId=filters.robotId.includes(robot)?filters.robotId.filter(id=>id!==robot):[...filters.robotId,robot]">{{robot}}</button></div>
                <small>{{t('history.priority')}}</small>
                <div class="filter-choice"><button v-for="priority in priorityOptions" :key="priority" type="button" :aria-pressed="filters.priority.includes(priority)" @click="filters.priority=filters.priority.includes(priority)?filters.priority.filter(id=>id!==priority):[...filters.priority,priority]">{{t(`priority.${priority}`)}}</button></div>
                <footer><button type="button" @click="resetFilters">{{t('common.clear')}}</button><button type="button" @click="filterOpen=false">{{t('common.apply')}}</button></footer>
              </div>
            </div>
            <div class="range-controls">
              <button type="button" :aria-label="t('common.previous')" @click="moveDate(-1)"><ChevronLeft :size="17"/></button>
              <button type="button" :aria-label="t('common.next')" @click="moveDate(1)"><ChevronRight :size="17"/></button>
            </div>
            <nav class="view-switch" :aria-label="t('history.timeMode')"><button v-for="mode in ['daily','weekly','monthly']" :key="mode" type="button" :aria-pressed="view===mode" @click="selectMode(mode)">{{t(`history.${mode}`)}}</button></nav>
          </div>
        </header>
        <div class="list-content" :aria-busy="loading">
          <SharedLoading :loading="loading" :detail="t('common.loading')" :error="error" :error-title="t('history.title')"><template #error-action><button type="button" @click="loadHistory">{{t('common.retry')}}</button></template></SharedLoading>
          <div v-if="!loading&&!error&&!inRange.length" class="history-empty" role="status"><CalendarDays :size="27"/><strong>{{t('common.noData')}}</strong><p>{{t('common.noDataHint')}}</p><button type="button" @click="resetFilters">{{t('common.clear')}}</button></div>
          <div v-if="!loading&&!error&&inRange.length" class="history-list-scroll themed-scroll">
            <section v-for="group in groups" :key="group.key" class="date-group">
              <h2>{{formatDate(group.key)}} <small>{{group.events.length}} {{t('common.tasks')}}</small></h2>
              <div class="rows-scroll">
                <div class="history-column-head"><span>{{t('history.name')}}</span><span>{{t('history.id')}}</span><span>{{t('history.start')}}</span><span>{{t('history.end')}}</span><span>{{t('history.robot')}}</span><span>{{t('history.origin')}} → {{t('history.destination')}}</span><span>{{t('history.priority')}}</span><span>{{t('history.status')}}</span><span>{{t('history.duration')}}</span></div>
                <button v-for="event in group.events" :key="event.id" type="button" class="history-row" :class="{'is-selected':event.id===selectedId}" :aria-pressed="event.id===selectedId" @click="selectedId=event.id;mapExpanded=false">
                  <span class="row-identity"><strong>{{translateTask(event.title)}}</strong></span>
                  <span class="row-task-id">{{event.taskId}}</span>
                  <span class="row-start"><small class="field-label">{{t('history.start')}}</small>{{time(event.start)}}</span>
                  <span class="row-end"><small class="field-label">{{t('history.end')}}</small>{{time(event.end)}}</span>
                  <span class="robot-label">{{event.robotName}}</span>
                  <span class="route-label"><span :title="translateLocation(event.startLocation)">{{translateLocation(event.startLocation)}}</span><ArrowRight :size="15"/><span :title="translateLocation(event.endLocation)">{{translateLocation(event.endLocation)}}</span></span>
                  <span class="priority-chip" :data-priority="event.priority">{{t(`priority.${event.priority}`)}}</span>
                  <span class="status-label" :data-status="displayStatus(event)">{{t(`status.${displayStatus(event)}`)}}</span>
                  <span class="duration-label"><span class="duration-value">{{duration(event)}}</span><span class="duration-unit">{{t('common.minutes')}}</span></span>
                </button>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
    <div class="history-side-column">
      <aside class="history-calendar schedule-history-panel" :aria-label="t('history.calendar')">
        <header class="calendar-header"><button type="button" :aria-label="t('common.previous')" @click="moveCalendarMonth(-1)"><ChevronLeft :size="17"/></button><h2>{{monthTitle}}</h2><button type="button" :aria-label="t('common.next')" @click="moveCalendarMonth(1)"><ChevronRight :size="17"/></button></header>
        <div class="mini-grid"><span v-for="day in weekdays" :key="day">{{day}}</span><button v-for="key in monthKeys" :key="key" type="button" :data-date="key" :title="dateTooltip(key)" :aria-label="dateTooltip(key)" :aria-current="key===today?'date':undefined" :aria-pressed="key===selectedDate" :class="calendarClasses(key)" @click="selectDay(key)">{{parseDay(key).getDate()}}</button></div>
      </aside>
      <aside class="history-detail schedule-history-panel" :aria-label="t('history.details')">
        <div class="detail-scroll">
        <template v-if="selectedEvent">
          <header class="detail-header"><h2>{{t('history.routeHeader')}} <span>· {{selectedEvent.taskId}}</span></h2><div class="detail-header-actions"><span class="floor-label">1F</span><button type="button" :aria-label="t('common.expand')" @click="mapExpanded=!mapExpanded"><Minimize2 v-if="mapExpanded" :size="15"/><Maximize2 v-else :size="15"/></button></div></header>
          <div class="route-map" :class="{'is-expanded':mapExpanded}"><HospitalMiniMap :key="selectedEvent.id" :robots="[]" :robot-id="selectedEvent.robotId" :origin="selectedEvent.startLocation" :destination="selectedEvent.endLocation" :route-coordinates="selectedEvent.routeCoordinates||[]" :route-progress="1" :history-status="selectedEvent.status" compact historical read-only /></div>
          <div class="detail-section-heading"><h3>{{t('history.timeline')}}</h3></div>
          <ol class="task-timeline" :data-status="selectedEvent.status"><li v-for="step in timeline" :key="step.key" :data-state="step.state"><span class="timeline-marker"><Check v-if="step.state==='done'" :size="12"/><component v-else-if="step.state==='terminal'" :is="statusIcons[selectedEvent.status]" :size="12"/></span><div><strong>{{t(`stages.${step.key}`)}}</strong><small>{{translateLocation(step.note)}}</small></div><time>{{time(step.time)}}</time></li></ol>
        </template>
        <div v-else class="detail-empty"><CalendarDays :size="26"/><strong>{{t('common.noData')}}</strong><p>{{t('common.noDataHint')}}</p></div>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.schedule-history-page{--history-tool-bg:rgba(255,255,255,.9);--history-tool-hover:rgba(255,255,255,.98);--history-tool-border:rgba(91,98,94,.17);--history-tool-shadow:0 1px 4px rgba(32,38,35,.055);position:absolute;z-index:3;top:76px;right:20px;bottom:18px;left:32px;display:grid;grid-template-columns:minmax(0,3fr) minmax(280px,1fr);gap:3px;height:calc(100dvh - 94px);min-width:0;min-height:0;overflow:hidden;color:var(--text-primary);font-size:var(--font-body)}
.history-main-column,.history-side-column{display:flex;flex-direction:column;gap:3px;height:100%;min-width:0;min-height:0;overflow:hidden}.history-list-panel,.history-detail{flex:1;min-height:0}
.schedule-history-panel{position:relative;isolation:isolate;box-sizing:border-box;min-width:0;min-height:0;padding:20px 22px;color:var(--text-primary);background:rgba(255,255,255,.88);border:1px solid rgba(255,255,255,.72);border-radius:var(--radius-panel);box-shadow:0 1px 0 rgba(255,255,255,.82) inset,0 8px 24px rgba(45,52,58,.055);backdrop-filter:blur(18px) saturate(115%);-webkit-backdrop-filter:blur(18px) saturate(115%)}
.history-list-panel{display:flex;flex-direction:column;padding-top:10px;overflow:hidden}.history-detail{overflow:hidden}.detail-scroll{height:100%;min-height:0;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:var(--glass-divider) transparent}
button,input{font:inherit}button{cursor:pointer;transition:color 180ms ease,background-color 180ms ease,border-color 180ms ease,box-shadow 180ms ease}button:focus-visible,input:focus-visible{outline:2px solid var(--theme-primary);outline-offset:2px}
.list-header,.calendar-header,.detail-header{display:flex;align-items:center;justify-content:space-between;gap:12px;min-width:0}.list-header{flex:none;padding-bottom:9px;border-bottom:1px solid var(--glass-divider)}.heading-copy{display:flex;flex:none;align-items:baseline;gap:9px;min-width:0}.heading-copy h1{margin:0;color:var(--text-primary);font-size:16px;font-weight:600;letter-spacing:.025em;white-space:nowrap}.heading-copy>span{color:var(--text-secondary);font-size:11px;font-weight:400;white-space:nowrap}.header-controls{display:flex;flex:1;align-items:center;justify-content:flex-end;gap:7px;min-width:0}.history-search{display:flex;align-items:center;gap:8px;width:clamp(110px,16vw,210px);height:31px;padding:0 9px;color:var(--text-secondary);background:var(--history-tool-bg);border:1px solid var(--history-tool-border);border-radius:var(--radius-control);box-shadow:var(--history-tool-shadow)}.history-search input{width:100%;min-width:0;color:var(--text-primary);background:transparent;border:0;outline:0;font-size:11.5px}.history-search:focus-within{background:var(--history-tool-hover);border-color:var(--theme-primary-border);box-shadow:var(--history-tool-shadow),0 0 0 2px var(--focus-ring)}
.filter-root{position:relative}.icon-control,.range-controls button,.detail-header-actions button{display:grid;width:30px;height:30px;place-items:center;padding:0;color:var(--text-secondary);background:var(--history-tool-bg);border:1px solid var(--history-tool-border);border-radius:var(--radius-control);box-shadow:var(--history-tool-shadow)}.icon-control:hover,.range-controls button:hover,.detail-header-actions button:hover{color:var(--theme-primary);background:var(--history-tool-hover);border-color:color-mix(in srgb,var(--theme-primary) 22%,var(--history-tool-border));box-shadow:var(--history-tool-shadow)}.icon-control.is-active{color:var(--theme-primary);border-color:var(--theme-primary-border)}.icon-control i{position:absolute;top:-5px;right:-5px;display:grid;width:15px;height:15px;place-items:center;color:#fff;font-size:9px;font-style:normal;background:var(--theme-primary);border-radius:50%}
.filter-popover{position:absolute;z-index:15;top:36px;right:0;display:grid;width:245px;gap:8px;padding:13px;color:var(--text-primary);background:var(--panel-background-strong);border:1px solid var(--panel-border);border-radius:var(--radius-panel);box-shadow:var(--dropdown-shadow);backdrop-filter:blur(var(--panel-blur))}.filter-popover strong{font-size:13px;font-weight:600}.filter-popover small{color:var(--text-secondary);font-size:10.5px}.filter-choice{display:flex;flex-wrap:wrap;gap:5px}.filter-choice button{padding:4px 7px;color:var(--text-secondary);background:var(--surface-2);border:1px solid var(--panel-border);border-radius:var(--radius-control);font-size:10.5px}.filter-choice button[aria-pressed=true]{color:var(--theme-primary);background:var(--theme-primary-soft);border-color:var(--theme-primary-border)}.filter-popover footer{display:flex;justify-content:space-between;padding-top:8px;border-top:1px solid var(--glass-divider)}.filter-popover footer button{padding:5px 8px;color:var(--text-secondary);background:transparent;border:1px solid var(--panel-border);border-radius:var(--radius-control)}.filter-popover footer button:last-child{color:#fff;background:var(--theme-primary);border-color:transparent}
.range-controls{display:flex;flex:none;gap:4px}.view-switch{display:flex;flex:none;gap:0;overflow:hidden;background:var(--history-tool-bg);border:1px solid var(--history-tool-border);border-radius:var(--radius-control);box-shadow:var(--history-tool-shadow)}.view-switch button{min-width:34px;height:30px;padding:0 8px;color:var(--text-secondary);background:transparent;border:0;border-right:1px solid var(--history-tool-border);border-radius:0;box-shadow:none;font-size:11px}.view-switch button:last-child{border-right:0}.view-switch button:hover{color:var(--text-primary);background:rgba(244,122,42,.035)}.view-switch button[aria-pressed=true]{color:var(--theme-primary);background:rgba(244,122,42,.09);box-shadow:inset 0 -2px 0 rgba(244,122,42,.62)}
.list-content{position:relative;flex:1;min-height:0;overflow:hidden}.history-list-scroll{height:100%;overflow-y:auto;overflow-x:hidden;padding:0 2px 18px;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:var(--glass-divider) transparent}.date-group h2{display:flex;align-items:center;gap:9px;margin:0;padding:10px 0 7px;color:var(--text-primary);font-size:12.5px;font-weight:600}.date-group h2 small{color:var(--text-secondary);font-size:10.5px;font-weight:400}.rows-scroll{overflow:hidden}.history-column-head,.history-row{display:grid;grid-template-columns:minmax(150px,1.5fr) minmax(84px,.72fr) 68px 68px 88px minmax(210px,1.8fr) 70px 96px 72px;align-items:center;column-gap:12px;min-width:0}.history-column-head{padding:9px 16px;color:#50565a;background:transparent;border:0;border-bottom:1px solid rgba(82,91,87,.12);border-radius:0;font-size:12.5px;font-weight:600}.history-column-head>span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.history-column-head>span{color:#56615d}.history-row{position:relative;box-sizing:border-box;width:100%;min-height:58px;margin:0;padding:12px 16px;text-align:left;color:var(--text-primary);background:transparent;border:0;border-bottom:1px solid rgba(82,91,87,.09);border-radius:0;box-shadow:none;cursor:pointer}.history-row::before{position:absolute;top:10px;bottom:10px;left:0;width:3px;background:transparent;border-radius:0 2px 2px 0;content:''}.history-row:hover{background:rgba(244,122,42,.035);border-color:rgba(82,91,87,.09);box-shadow:none;transform:none}.history-row.is-selected{background:rgba(244,122,42,.065);border-color:rgba(82,91,87,.09);box-shadow:none}.history-row.is-selected::before{background:var(--theme-primary)}
.row-identity{min-width:0}.row-identity strong{display:block;min-width:0;overflow:hidden;color:#2f3437;font-size:10.8px;font-weight:400;text-overflow:ellipsis;white-space:nowrap;text-shadow:none}.row-task-id{min-width:0;overflow:hidden;color:var(--text-secondary);font-size:10.5px;font-weight:400;text-overflow:ellipsis;white-space:nowrap}.row-start,.row-end{min-width:0;font-size:10.5px;font-weight:400;font-variant-numeric:tabular-nums;white-space:nowrap}.field-label{display:none}.robot-label{justify-self:start;max-width:100%;overflow:hidden;padding:2px 4px;color:var(--text-secondary);background:rgba(245,247,246,.7);border:0;border-radius:var(--radius-small);font-size:10.5px;font-weight:400;white-space:nowrap;text-overflow:ellipsis}.route-label{display:flex;align-items:center;gap:5px;min-width:0;color:var(--text-secondary);font-size:10.5px;font-weight:400}.route-label svg{flex:none;color:var(--theme-primary)}.route-label span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.route-label span:first-child{max-width:47%}.priority-chip{justify-self:start;padding:2px 4px;border:1px solid currentColor;border-radius:var(--radius-small);font-size:10.5px;font-weight:500;white-space:nowrap}.priority-chip[data-priority=urgent]{color:#b6433f;background:rgba(230,102,88,.07)}.priority-chip[data-priority=high]{color:var(--theme-primary);background:var(--theme-primary-soft)}.priority-chip[data-priority=normal]{color:#90712f;background:rgba(239,198,90,.09)}.priority-chip[data-priority=low]{color:#288068;background:rgba(92,181,141,.08)}.status-label{display:inline-flex;align-items:center;min-width:0;color:#5c6460;font-size:10.5px;font-weight:500;white-space:nowrap}.duration-label{display:inline-flex;align-items:baseline;gap:3px;white-space:nowrap;font-variant-numeric:tabular-nums}.duration-value{color:var(--text-primary);font-size:12.5px;font-weight:500}.duration-unit{color:var(--text-secondary);font-size:9.5px;font-weight:400}
.history-empty,.detail-empty{display:grid;justify-items:center;align-content:center;gap:8px;height:100%;padding:20px;text-align:center;color:var(--text-secondary)}.history-empty strong,.detail-empty strong{color:var(--text-primary);font-size:14px;font-weight:600}.history-empty p,.detail-empty p{max-width:300px;margin:0;font-size:11px}.history-empty button{padding:6px 9px;color:var(--theme-primary);background:var(--theme-primary-soft);border:1px solid var(--theme-primary-border);border-radius:var(--radius-control)}
.history-calendar{--calendar-yellow:#F4C542;--calendar-yellow-strong:#EFBF2F;display:flex;flex:none;flex-direction:column;height:clamp(200px,26%,255px);padding:12px 14px}.calendar-header{justify-content:center;gap:10px}.calendar-header h2,.detail-header h2{margin:0;color:var(--text-primary);font-size:15px;font-weight:600;letter-spacing:.025em}.calendar-header button{display:grid;width:22px;height:22px;place-items:center;padding:0;color:#74776f;background:transparent;border:0;border-radius:50%;box-shadow:none}.calendar-header button:hover{color:var(--calendar-yellow-strong);background:rgba(244,197,66,.08)}.mini-grid{display:grid;flex:1;min-height:0;grid-template-columns:repeat(7,minmax(0,1fr));grid-template-rows:15px repeat(6,minmax(20px,1fr));column-gap:0;row-gap:0;margin-top:5px}.mini-grid>span{display:grid;place-items:center;color:var(--text-secondary);font-size:9.5px;font-weight:500}.mini-grid button{display:grid;place-items:center;min-width:0;min-height:20px;padding:0;color:var(--text-primary);font-size:11px;font-weight:500;background:transparent;border:0;border-radius:0;box-shadow:none;transition:color 180ms ease,background-color 180ms ease}.mini-grid button:hover{background:rgba(244,197,66,.09)}.mini-grid button.intensity-low{background:rgba(244,197,66,.08)}.mini-grid button.intensity-medium{background:rgba(244,197,66,.14)}.mini-grid button.intensity-high{background:rgba(244,197,66,.22)}.mini-grid button.intensity-very-high{background:rgba(244,197,66,.32)}.mini-grid button.is-outside{color:var(--text-muted);background:transparent}.mini-grid button.is-in-week{color:#4A4024;background:rgba(244,197,66,.12);border-radius:0}.mini-grid button.is-in-week.intensity-low{background:rgba(244,197,66,.16)}.mini-grid button.is-in-week.intensity-medium{background:rgba(244,197,66,.22)}.mini-grid button.is-in-week.intensity-high{background:rgba(244,197,66,.28)}.mini-grid button.is-in-week.intensity-very-high{background:rgba(244,197,66,.34)}.mini-grid button.is-week-start{border-radius:5px 0 0 5px}.mini-grid button.is-week-end{border-radius:0 5px 5px 0}.mini-grid button.is-in-month{background:rgba(244,197,66,.08)}.mini-grid button.is-anchor,.mini-grid button.is-today{color:#4A4024;font-weight:650;background:rgba(244,197,66,.36);box-shadow:inset 0 0 0 1px rgba(239,191,47,.5);border-radius:5px}.mini-grid button.is-anchor.is-today{box-shadow:inset 0 0 0 1px rgba(239,191,47,.55)}
.history-detail{padding:14px 16px}.detail-header{padding-bottom:8px;border-bottom:1px solid var(--glass-divider)}.detail-header h2 span{color:var(--text-secondary);font-size:11.5px;font-weight:500;letter-spacing:0}.detail-header-actions{display:flex;align-items:center;gap:8px}.detail-header-actions button{width:25px;height:25px}.floor-label{color:var(--text-secondary);font-size:11px;font-weight:500}.route-map{height:clamp(165px,22vh,210px);margin-top:9px;overflow:hidden;border-radius:var(--radius-panel);transition:height 180ms ease}.route-map.is-expanded{height:300px}.detail-section-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:10px 0 8px}.detail-section-heading h3{margin:0;color:var(--text-primary);font-size:14px;font-weight:600}.route-map :deep(.mini-map){border:0;box-shadow:none}.route-map :deep(.map-controls button){background:var(--history-tool-bg);border-color:var(--history-tool-border);border-radius:var(--radius-control);box-shadow:none}.route-map :deep(.map-controls button:hover){color:var(--theme-primary);background:var(--history-tool-hover);border-color:color-mix(in srgb,var(--theme-primary) 22%,var(--history-tool-border));box-shadow:none}
.task-timeline{display:grid;gap:0;margin:0;padding:0;list-style:none}.task-timeline li{position:relative;display:grid;grid-template-columns:18px minmax(0,1fr) auto;gap:7px;min-height:34px;color:var(--text-secondary)}.task-timeline li:not(:last-child)::before{position:absolute;top:18px;bottom:0;left:8px;width:1.5px;background:#2FA58F;content:''}.timeline-marker{position:relative;z-index:1;display:grid;width:17px;height:17px;place-items:center;box-sizing:border-box;color:#fff;background:#2FA58F;border:1px solid #2FA58F;border-radius:50%}.task-timeline li[data-state=terminal] .timeline-marker{background:var(--terminal-color);border-color:var(--terminal-color)}.task-timeline[data-status=cancelled]{--terminal-color:#4F7DF3}.task-timeline[data-status=failed]{--terminal-color:#E45D63}.task-timeline li[data-state=current] .timeline-marker{background:var(--panel-background-strong);border-color:var(--theme-primary);box-shadow:none}.task-timeline li[data-state=terminal] strong{color:var(--terminal-color)}.task-timeline li>div{display:grid;align-content:start;gap:2px;min-width:0}.task-timeline strong{color:var(--text-primary);font-size:11.5px;font-weight:600}.task-timeline small{overflow:hidden;color:var(--text-secondary);font-size:10px;text-overflow:ellipsis;white-space:nowrap}.task-timeline time{color:var(--text-secondary);font-size:10.5px;font-variant-numeric:tabular-nums}
@media(max-width:1450px) and (min-width:1181px){.history-column-head,.history-row{grid-template-columns:minmax(132px,1.4fr) 74px 62px 62px 76px minmax(160px,1.65fr) 60px 90px 66px;column-gap:8px}}
@media(max-width:1180px){.schedule-history-page{display:flex;flex-direction:column;overflow-y:auto}.history-main-column,.history-side-column{height:auto;overflow:visible;flex:none}.history-list-panel{height:520px;flex:none}.history-detail{min-height:430px;flex:none;overflow-y:auto}.history-calendar{height:220px}.history-stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:900px){.schedule-history-page{top:94px;height:calc(100dvh - 112px)}}
@media(max-width:850px){.list-header{gap:8px}.history-search{flex:1;width:auto;min-width:90px}.history-column-head{display:none}.history-row{grid-template-columns:repeat(4,minmax(0,1fr));grid-template-rows:auto auto auto;gap:8px;min-height:100px;padding:9px}.history-row>.row-identity{grid-column:1;grid-row:1;padding-left:8px}.row-task-id{grid-column:2;grid-row:1}.priority-chip{grid-column:3;grid-row:1}.status-label{grid-column:4;grid-row:1;justify-self:end}.row-start{grid-column:1;grid-row:2}.row-end{grid-column:2;grid-row:2}.robot-label{grid-column:3;grid-row:2}.duration-label{grid-column:4;grid-row:2;justify-self:end}.route-label{grid-column:1/5;grid-row:3;max-width:100%}.field-label{display:block;margin-bottom:2px;color:var(--text-secondary);font-size:9px;font-weight:400}.history-list-panel{height:520px}}
@media(max-width:650px){.list-header{gap:5px}.heading-copy{gap:5px}.heading-copy h1{font-size:14px}.heading-copy>span{font-size:10px}.header-controls{gap:4px}.history-search{width:76px;min-width:76px;padding:0 6px}.range-controls{gap:3px}.view-switch{gap:0}.view-switch button{min-width:26px;padding:0 5px}}
@media(max-width:520px){.schedule-history-page{top:90px;right:8px;bottom:8px;left:8px;height:calc(100dvh - 98px);gap:10px}.history-main-column,.history-side-column{gap:10px}.schedule-history-panel{padding:14px 15px}.history-calendar{height:214px;padding:11px 12px}.history-detail{padding:14px 15px}.history-row{grid-template-columns:repeat(4,minmax(0,1fr));grid-template-rows:auto auto auto auto;gap:6px}.history-row>.row-identity{grid-column:1/3;grid-row:1;padding-left:8px}.row-task-id{grid-column:3/5;grid-row:1}.row-start{grid-column:1;grid-row:2}.row-end{grid-column:2;grid-row:2}.priority-chip{grid-column:3;grid-row:2}.status-label{grid-column:4;grid-row:2;justify-self:end}.robot-label{grid-column:1/2;grid-row:3}.duration-label{grid-column:2/3;grid-row:3}.route-label{grid-column:1/5;grid-row:4}.mini-grid button{min-height:19px}}
.calendar-header{position:relative;display:grid;grid-template-columns:1fr auto 1fr;justify-content:stretch;gap:0}.calendar-header h2{grid-column:2;text-align:center}.calendar-header button{position:absolute;top:50%;width:28px;height:28px;transform:translateY(-50%)}.calendar-header button:first-child{left:0}.calendar-header button:last-child{right:0}.mini-grid button{background:transparent!important;border:0!important;box-shadow:none!important}.mini-grid button.calendar-density-low{background:rgba(244,197,66,.08)!important}.mini-grid button.calendar-density-medium{background:rgba(244,197,66,.14)!important}.mini-grid button.calendar-density-high{background:rgba(244,197,66,.22)!important}.mini-grid button.calendar-density-very-high{background:rgba(244,197,66,.32)!important}.mini-grid button.calendar-week-none{background:rgba(244,197,66,.12)!important}.mini-grid button.calendar-week-low{background:rgba(244,197,66,.16)!important}.mini-grid button.calendar-week-medium{background:rgba(244,197,66,.22)!important}.mini-grid button.calendar-week-high{background:rgba(244,197,66,.28)!important}.mini-grid button.calendar-week-very-high{background:rgba(244,197,66,.34)!important}.mini-grid button[class*=calendar-month-]{background:rgba(244,197,66,.08)!important}.mini-grid button.calendar-month-medium{background:rgba(244,197,66,.14)!important}.mini-grid button.calendar-month-high{background:rgba(244,197,66,.22)!important}.mini-grid button.calendar-month-very-high{background:rgba(244,197,66,.32)!important}.mini-grid button.calendar-today{color:#4A4024!important;font-weight:600;background:rgba(244,197,66,.2)!important;border:0!important;border-radius:5px;box-shadow:none!important}.mini-grid button.calendar-selected{color:#4A4024!important;font-weight:650;background:rgba(244,197,66,.4)!important;border:0!important;border-radius:5px;box-shadow:none!important}.mini-grid button.calendar-default:hover,.mini-grid button.is-outside:hover{background:rgba(244,197,66,.08)!important}.history-calendar{overflow:hidden}
.history-calendar .calendar-header{position:relative;display:grid;width:calc(100% + 28px);min-height:36px;grid-template-columns:32px minmax(0,1fr) 32px;align-items:center;box-sizing:border-box;margin:-12px -14px 5px;padding:7px 12px;background:rgba(250,222,112,.24);border-bottom:1px solid rgba(221,185,55,.16);border-radius:var(--radius-panel) var(--radius-panel) 0 0;box-shadow:none}.history-calendar .calendar-header h2{grid-column:2;justify-self:center;text-align:center}.history-calendar .calendar-header button{position:static;top:auto;width:32px;height:24px;color:#74776f;background:transparent;border:0;box-shadow:none;transform:none}.history-calendar .calendar-header button:first-child{grid-column:1;justify-self:start}.history-calendar .calendar-header button:last-child{grid-column:3;justify-self:end}.history-calendar .calendar-header button:hover{color:var(--calendar-yellow-strong);background:transparent}
.date-group h2{font-size:13.5px}.date-group h2 small{font-size:11.5px}.history-column-head{font-size:13px}.history-row{min-height:64px;padding-block:14px}.row-identity strong,.row-task-id,.row-start,.row-end,.robot-label,.route-label{font-size:12px}.priority-chip{padding:0;color:var(--text-secondary);background:transparent!important;border:0;border-radius:0;font-size:11.8px;font-weight:500}.priority-chip[data-priority=urgent]{color:#b6433f}.priority-chip[data-priority=high]{color:var(--theme-primary)}.priority-chip[data-priority=normal]{color:#90712f}.priority-chip[data-priority=low]{color:#288068}.status-label{font-size:11.8px}.duration-value{font-size:13.5px}.duration-unit{font-size:10px}
@media(max-width:520px){.history-main-column,.history-side-column{gap:3px}}
</style>
