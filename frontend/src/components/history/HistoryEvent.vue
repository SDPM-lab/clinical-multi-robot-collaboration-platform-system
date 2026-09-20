<script setup>
import { computed } from 'vue'
import { historyTaskStyle } from '@/data/historyPresentation.js'
import { statusOptions } from '@/data/scheduleHistory.js'
const props=defineProps({event:{type:Object,required:true},compact:Boolean,index:{type:Number,default:0}})
const emit=defineEmits(['select'])
const color=computed(()=>historyTaskStyle(props.event.title))
const time=value=>new Date(value).toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:false})
const status=computed(()=>statusOptions.find(item=>item.id===props.event.status)?.label)
</script>
<template><button class="calendar-event" type="button" :class="{'is-compact':compact}" :style="{...color,'--event-index':Math.min(index,20)}" :title="`${event.taskId} ${event.title}\n${time(event.start)}–${time(event.end)} · ${event.robotName}\n${event.startLocation} → ${event.endLocation}\n${status}`" @click="emit('select',event)"><strong>{{event.title}}</strong><span>{{time(event.start)}}–{{time(event.end)}} · {{event.robotName}}</span><small v-if="!compact">{{event.endLocation}} · {{status}}</small></button></template>
<style scoped>
.calendar-event{display:flex;flex-direction:column;gap:3px;box-sizing:border-box;overflow:hidden;width:100%;padding:6px 7px;text-align:left;color:var(--task-ink);background:linear-gradient(135deg,color-mix(in srgb,var(--task-from) 60%,transparent),color-mix(in srgb,var(--task-to) 60%,transparent));border:0;border-radius:5px;cursor:pointer;transition:filter 160ms ease,box-shadow 160ms ease,translate 160ms ease;animation:history-event-enter 360ms ease calc(var(--event-index)*55ms) both}.calendar-event:hover{filter:brightness(1.025);box-shadow:0 3px 9px #766d5810;translate:0 -1px}.calendar-event:focus-visible{outline:2px solid var(--task-ink);outline-offset:1px}.calendar-event strong{font-size:11.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}.calendar-event span{font-size:10px;white-space:nowrap}.calendar-event small{font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.is-compact{padding:3px 5px;gap:1px}.is-compact strong{font-size:10px}.is-compact span{font-size:9px}
@keyframes history-event-enter{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:none}}
</style>
