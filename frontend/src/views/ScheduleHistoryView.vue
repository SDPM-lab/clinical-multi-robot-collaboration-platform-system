<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { Activity, AlertCircle, ArrowRight, Ban, CalendarDays, Check, ChevronLeft, ChevronRight, Clock, Filter, RefreshCw, Search } from '@lucide/vue'
import SharedLoading from '@/components/SharedLoading.vue'
import HistorySummary from '@/components/history/HistorySummary.vue'
import HospitalMiniMap from '@/components/dispatch/HospitalMiniMap.vue'
import { addDays, dayKey, eventsOnDay, filterHistory, historyRange, monthDays, parseDay } from '@/data/scheduleHistory.js'
import { notificationStore } from '@/stores/notificationStore.js'
import { localeTag, t, translateLocation, translateTask } from '@/i18n/index.js'
import { robotDisplayCode } from '@/config/robotDisplayCode.js'

const today=dayKey(new Date())
const selectedDate=ref(today)
const calendarMonth=ref(today)
const calendarOpen=ref(false)
const calendarRoot=ref(null)
const view=ref('weekly')
const statusFilter=ref('all')
const query=ref('')
const filterOpen=ref(false)
const filterRoot=ref(null)
const lastUpdated=ref(null)
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
    const result=await module.createHistorySource()
    if(generation===loadGeneration){source.value=result;lastUpdated.value=new Date()}
  } catch {
    if(generation===loadGeneration){loadError.value='load-error';notificationStore.add({key:'history.loadError',type:'error'})}
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
const overlaps=(event,period)=>Date.parse(event.start)<parseDay(period[1]).getTime()&&(Date.parse(event.end)>parseDay(period[0]).getTime() || (event.end===event.start && Date.parse(event.start)>=parseDay(period[0]).getTime()))
const rangeEvents=computed(()=>matches.value.filter(event=>overlaps(event,range.value)).sort((a,b)=>Date.parse(b.start)-Date.parse(a.start)||a.taskId.localeCompare(b.taskId)))
const previousEvents=computed(()=>matches.value.filter(event=>overlaps(event,previousRange.value)))
const inRange=computed(()=>rangeEvents.value.filter(event=>statusFilter.value==='all'||event.status===statusFilter.value))
const selectedId=ref(null)
watch(inRange,items=>{if(!items.some(item=>item.id===selectedId.value))selectedId.value=items[0]?.id||null},{immediate:true})
const selectedEvent=computed(()=>inRange.value.find(item=>item.id===selectedId.value)||null)
const groups=computed(()=>[...new Set(inRange.value.map(event=>dayKey(new Date(event.start))))].map(key=>({key,events:inRange.value.filter(event=>dayKey(new Date(event.start))===key)})))

const formatDate=key=>parseDay(key).toLocaleDateString(localeTag.value,{year:'numeric',month:'long',day:'numeric',weekday:'short'})
const calendarTitle=computed(()=>parseDay(calendarMonth.value).toLocaleDateString(localeTag.value,{year:'numeric',month:'long'}))
const calendarDays=computed(()=>monthDays(calendarMonth.value))
const calendarWeekdays=computed(()=>Array.from({length:7},(_,index)=>parseDay(addDays('2026-09-14',index)).toLocaleDateString(localeTag.value,{weekday:'short'}).replace(/^週/,'') ))
const time=value=>!value||!Number.isFinite(Date.parse(value)) ? '—' : new Date(value).toLocaleTimeString(localeTag.value,{hour:'2-digit',minute:'2-digit',hour12:false})
const duration=event=>event.backendRecord ? (event.durationMinutes == null ? '—' : Math.round(event.durationMinutes)) : Math.max(0,Math.round((Date.parse(event.end)-Date.parse(event.start))/60000))
const delay=event=>event.delayMinutes == null ? '—' : `${Math.ceil(event.delayMinutes)} ${t('common.minutes')}`
const createdAt=value=>{
  if(!value||!Number.isFinite(Date.parse(value)))return t('robotStatus.noValue')
  return new Date(value).toLocaleString(localeTag.value,{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'})
}
const selectMode=mode=>{view.value=mode}
const chooseDate=key=>{selectedDate.value=key;calendarMonth.value=key;calendarOpen.value=false}
const shiftCalendarMonth=amount=>{
  const date=parseDay(calendarMonth.value)
  date.setDate(1)
  date.setMonth(date.getMonth()+amount)
  calendarMonth.value=dayKey(date)
}
const toggleCalendar=()=>{calendarMonth.value=selectedDate.value;calendarOpen.value=!calendarOpen.value}
const closeCalendarOnOutside=event=>{if(!calendarRoot.value?.contains(event.target))calendarOpen.value=false;if(!filterRoot.value?.contains(event.target))filterOpen.value=false}
const moveDate=amount=>{
  if(view.value==='monthly'){
    const date=parseDay(selectedDate.value)
    date.setDate(1)
    date.setMonth(date.getMonth()+amount)
    selectedDate.value=dayKey(date)
  }else selectedDate.value=addDays(selectedDate.value,amount*(view.value==='weekly'?7:1))
}
const resetFilters=()=>{filters.priority=[];filters.robotId=[];statusFilter.value='all';query.value='';filterOpen.value=false}
const hasFilters=computed(()=>filters.priority.length>0||filters.robotId.length>0||statusFilter.value!=='all'||!!query.value.trim())
const rangeLabel=computed(()=>`${formatDate(range.value[0])} – ${formatDate(addDays(range.value[1],-1))}`)
const activeFilterCount=computed(()=>filters.priority.length+filters.robotId.length)
const robots=computed(()=>{
  const registered=source.value?.value.robots||[]
  const knownIds=new Set(registered.map(robot=>robot.id))
  const recorded=events.value.filter(event=>event.robotId&&!knownIds.has(event.robotId)).map(event=>({id:event.robotId,robotType:''}))
  return [...registered,...new Map(recorded.map(robot=>[robot.id,robot])).values()]
})
const robotFilterLabel=robot=>{
  const code=robotDisplayCode(robot.id)
  const type=robot.robotType||({C:'clean',M:'medical',W:'ward'}[code[0]]||'unknown')
  return `${code} · ${t(`history.robotTypes.${type}`)}`
}
const priorityOptions=['urgent','high','normal','low']
const statusIcons={completed:Check,running:Activity,failed:AlertCircle,waiting:Clock,cancelled:Ban}

const timelineKeys=['created','received','toSource','pickedUp','toDestination','completed']
const stageProgress=event=>event.timelineProgress??({completed:6,running:4,waiting:1,failed:5,cancelled:2}[event.status]||6)
const timeline=computed(()=>{
  const event=selectedEvent.value
  if(!event)return []
  if(event.backendRecord){
    return [
      event.createdAt && {key:'created',state:'done',time:event.createdAt,note:''},
      event.startedAt && {key:'started',state:'done',time:event.startedAt,note:event.startLocation},
      event.finishedAt && {key:event.status,state:event.status==='completed'?'done':'terminal',time:event.finishedAt,note:event.endLocation},
    ].filter(Boolean)
  }
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
onMounted(()=>{loadHistory();document.addEventListener('pointerdown',closeCalendarOnOutside)})
onBeforeUnmount(()=>{loadGeneration++;document.removeEventListener('pointerdown',closeCalendarOnOutside)})
</script>

<template>
  <section class="schedule-history-page" :aria-label="t('history.title')">
    <div class="history-main-column">
      <HistorySummary
        class="history-stats"
        :events="rangeEvents"
        :range-start="range[0]"
        :previous-events="previousEvents"
        :period="view"
        :selected-status="statusFilter"
        @select="statusFilter=$event"
      />
      <main class="history-list-panel schedule-history-panel">
        <header class="list-header">
          <label class="history-search"><Search :size="17"/><input v-model="query" type="search" :placeholder="t('history.search')" :aria-label="t('history.search')"/></label>
          <div class="header-controls">
            <div ref="filterRoot" class="filter-root" @keydown.esc.stop="filterOpen=false">
              <button type="button" class="icon-control" :class="{'is-active':filterOpen||activeFilterCount}" :aria-expanded="filterOpen" :aria-label="t('common.filter')" @click="filterOpen=!filterOpen"><Filter :size="17"/><i v-if="activeFilterCount">{{activeFilterCount}}</i></button>
              <div v-if="filterOpen" class="filter-popover" role="group" :aria-label="t('common.filter')">
                <strong>{{t('common.filter')}}</strong>
                <small>{{t('history.robot')}}</small>
                <div class="filter-choice"><button v-for="robot in robots" :key="robot.id" type="button" :title="robot.id" :aria-label="`${robotFilterLabel(robot)} (${robot.id})`" :aria-pressed="filters.robotId.includes(robot.id)" @click="filters.robotId=filters.robotId.includes(robot.id)?filters.robotId.filter(id=>id!==robot.id):[...filters.robotId,robot.id]">{{robotFilterLabel(robot)}}</button></div>
                <small>{{t('history.priority')}}</small>
                <div class="filter-choice"><button v-for="priority in priorityOptions" :key="priority" type="button" :aria-pressed="filters.priority.includes(priority)" @click="filters.priority=filters.priority.includes(priority)?filters.priority.filter(id=>id!==priority):[...filters.priority,priority]">{{t(`priority.${priority}`)}}</button></div>
                <footer><button type="button" @click="filterOpen=false">{{t('common.apply')}}</button></footer>
              </div>
            </div>
            <div class="range-controls date-navigation">
              <button type="button" :aria-label="t('common.previous')" @click="moveDate(-1)"><ChevronLeft :size="17"/></button>
              <div ref="calendarRoot" class="date-picker-root" @keydown.esc.stop="calendarOpen=false" @focusout="!$event.currentTarget.contains($event.relatedTarget)&&(calendarOpen=false)">
                <button type="button" class="history-date-picker" :aria-label="t('history.dateRange')" :aria-expanded="calendarOpen" aria-haspopup="dialog" @click="toggleCalendar"><CalendarDays :size="15"/><span>{{selectedDate.replaceAll('-', '/')}}</span></button>
                <div v-if="calendarOpen" class="calendar-popover" role="dialog" :aria-label="t('history.calendar')">
                  <div class="calendar-header"><button type="button" :aria-label="t('common.previous')" @click="shiftCalendarMonth(-1)"><ChevronLeft :size="16"/></button><strong>{{calendarTitle}}</strong><button type="button" :aria-label="t('common.next')" @click="shiftCalendarMonth(1)"><ChevronRight :size="16"/></button></div>
                  <div class="calendar-grid"><span v-for="(weekday,index) in calendarWeekdays" :key="index" class="calendar-weekday">{{weekday}}</span><button v-for="day in calendarDays" :key="day" type="button" class="calendar-day" :data-date="day" :class="{'is-outside':day.slice(0,7)!==calendarMonth.slice(0,7),'is-today':day===today}" :aria-label="formatDate(day)" :aria-pressed="day===selectedDate" @click="chooseDate(day)">{{Number(day.slice(-2))}}</button></div>
                  <footer><button type="button" @click="chooseDate(today)">{{t('common.today')}}</button></footer>
                </div>
              </div>
              <button type="button" :aria-label="t('common.next')" @click="moveDate(1)"><ChevronRight :size="17"/></button>
            </div>
            <button type="button" class="history-refresh" :disabled="loading" :aria-label="t('historyUx.refresh')" :title="t('historyUx.refresh')" @click="loadHistory"><RefreshCw :size="16"/></button>
            <nav class="view-switch" :aria-label="t('history.timeMode')"><button v-for="mode in ['daily','weekly','monthly']" :key="mode" type="button" :aria-pressed="view===mode" @click="selectMode(mode)">{{t(`history.${mode}`)}}</button></nav>
          </div>
        </header>
        <div class="history-list-context">
          <div><span>{{ rangeLabel }}</span></div>
          <small v-if="lastUpdated">{{ t('historyUx.updated', { time: time(lastUpdated) }) }}</small>
        </div>
        <p v-if="source?.value.robotLookupFailed" class="history-notice" role="status">{{ t('historyUx.robotLookupFailed') }}</p>
        <p v-if="error && events.length" class="history-notice is-error" role="alert">{{ error }} <button type="button" :disabled="loading" @click="loadHistory">{{ t('common.retry') }}</button></p>
        <div class="list-content" :aria-busy="loading">
          <SharedLoading :loading="loading && !events.length" :detail="t('common.loading')" :error="!events.length ? error : ''" :error-title="t('history.title')"><template #error-action><button type="button" @click="loadHistory">{{t('common.retry')}}</button></template></SharedLoading>
          <div v-if="!loading&&!error&&!inRange.length" class="history-empty" role="status"><CalendarDays :size="27"/><strong>{{t(hasFilters ? 'historyUx.noMatches' : 'historyUx.noRecords')}}</strong><p>{{t(hasFilters ? 'historyUx.noMatchesHint' : 'historyUx.noRecordsHint')}}</p><button v-if="hasFilters" type="button" @click="resetFilters">{{t('historyUx.resetFilters')}}</button></div>
          <div v-if="inRange.length && (!error || events.length)" class="history-column-head"><span>{{t('history.name')}}</span><span>{{t('history.actualTime')}}</span><span>{{t('history.delay')}}</span><span>{{t('history.robot')}}</span><span>{{t('history.source')}} → {{t('history.destination')}}</span><span>{{t('history.priority')}}</span><span>{{t('history.status')}}</span><span>{{t('history.duration')}}</span></div>
          <div v-if="inRange.length && (!error || events.length)" class="history-list-scroll themed-scroll">
            <section v-for="group in groups" :key="group.key" class="date-group">
              <h2>{{formatDate(group.key)}} <small>{{group.events.length}} {{t('common.tasks')}}</small></h2>
              <div class="rows-scroll">
                <button v-for="event in group.events" :key="event.id" type="button" class="history-row" :class="{'is-selected':event.id===selectedId}" :aria-pressed="event.id===selectedId" @click="selectedId=event.id">
                  <span class="row-identity"><strong>{{translateTask(event.title)}}</strong><small class="row-task-id">{{event.taskId}}</small></span>
                  <span class="row-time"><span class="row-start">{{time(event.backendRecord ? event.startedAt : event.start)}}</span><span class="time-arrow">–</span><span class="row-end">{{time(event.backendRecord ? event.finishedAt : event.end)}}</span></span>
                  <span class="delay-label">{{delay(event)}}</span>
                  <span class="robot-label">{{event.robotId?robotDisplayCode(event.robotId):t('dispatch.unassigned')}}<small v-if="event.robotName && event.robotName!==robotDisplayCode(event.robotId)">{{event.robotName}}</small></span>
                  <span class="route-label"><span :title="translateLocation(event.startLocation)">{{translateLocation(event.startLocation)}}</span><ArrowRight :size="14"/><span :title="translateLocation(event.endLocation)">{{translateLocation(event.endLocation)}}</span></span>
                  <span class="priority-chip" :data-priority="event.priority">{{t(`priority.${event.priority}`)}}</span>
                  <span class="status-label" :data-status="event.status">{{t(`status.${event.status}`)}}</span>
                  <span class="duration-label"><span class="duration-value">{{duration(event)}}</span><span v-if="duration(event)!=='—'" class="duration-unit">{{t('common.minutes')}}</span></span>
                </button>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
    <div class="history-side-column">
      <aside class="task-record-panel" :aria-label="t('history.details')">
        <h2>{{t('history.details')}} <span v-if="selectedEvent">· {{selectedEvent.taskId}}</span></h2>
        <dl v-if="selectedEvent" class="task-record">
          <div><dt>{{t('history.robot')}}</dt><dd>{{selectedEvent.robotId?robotDisplayCode(selectedEvent.robotId):t('dispatch.unassigned')}}</dd></div>
          <div><dt>{{t('history.note')}}</dt><dd>{{selectedEvent.note?.trim()||t('robotStatus.noValue')}}</dd></div>
          <div><dt>{{t('history.requiredCapabilities')}}</dt><dd class="capability-list"><template v-if="selectedEvent.requiredCapabilities?.length"><span v-for="capability in selectedEvent.requiredCapabilities" :key="capability">{{t(`dispatchForm.capabilities.${capability}`)}}</span></template><template v-else>{{t('robotStatus.noValue')}}</template></dd></div>
          <div><dt>{{t('history.createdAt')}}</dt><dd>{{createdAt(selectedEvent.createdAt)}}</dd></div>
          <div><dt>{{t('history.scheduledAt')}}</dt><dd>{{createdAt(selectedEvent.scheduledAt)}}</dd></div>
        </dl>
        <p v-else class="task-record-empty">{{t('common.noData')}}</p>
      </aside>
      <aside class="history-detail" :aria-label="t('history.routeHeader')">
        <div class="detail-scroll">
        <template v-if="selectedEvent">
          <header class="detail-header"><h2>{{t('history.routeHeader')}} <span>· {{selectedEvent.taskId}}</span></h2><span class="floor-label">1F</span></header>
          <div class="route-map"><HospitalMiniMap :key="selectedEvent.id" :robots="[]" :robot-id="selectedEvent.robotId" :source="selectedEvent.startLocation" :destination="selectedEvent.endLocation" :route-coordinates="selectedEvent.routeCoordinates||[]" :route-progress="1" :history-status="selectedEvent.status" compact historical read-only /></div>
          <p class="history-route-hint">{{t('historyUx.routeHint')}}</p>
          <div class="detail-section-heading"><h3>{{t('history.timeline')}}</h3></div>
          <ol class="task-timeline" :data-status="selectedEvent.status"><li v-for="step in timeline" :key="step.key" :data-state="step.state"><span class="timeline-marker"><Check v-if="step.state==='done'" :size="12"/><component v-else-if="step.state==='terminal'" :is="statusIcons[selectedEvent.status]" :size="12"/></span><div><strong>{{t(`stages.${step.key}`)}}</strong><small>{{translateLocation(step.note)}}</small></div><time :title="createdAt(step.time)">{{time(step.time)}}</time></li></ol>
        </template>
        <div v-else class="detail-empty"><CalendarDays :size="26"/><strong>{{t('common.noData')}}</strong><p>{{t('common.noDataHint')}}</p></div>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped src="./scheduleHistory.css"></style>
