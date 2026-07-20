<script setup lang="ts">
import { computed } from 'vue'
import { PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent } from 'reka-ui'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const props = defineProps<{
  alerts: Array<Record<string, any>>
  unreadCount: number
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'mark-all-read': []
  'open-detail': [alert: Record<string, any>]
  'view-all': []
}>()

const recentAlerts = computed(() => props.alerts.slice(0, 5))

function alertTypeBadgeClass(type: string) {
  const map: Record<string, string> = {
    '異常': 'bg-red-50 text-red-600 border-red-200',
    '警告': 'bg-amber-50 text-amber-600 border-amber-200',
    '完成': 'bg-emerald-50 text-emerald-600 border-emerald-200',
    '進行中': 'bg-blue-50 text-blue-600 border-blue-200',
    '資訊': 'bg-indigo-50 text-indigo-600 border-indigo-200',
  }
  return map[type] || 'bg-slate-100 text-slate-500 border-slate-200'
}

function handleOpenDetail(alert: Record<string, any>) {
  emit('open-detail', alert)
  emit('update:open', false)
}

function handleViewAll() {
  emit('view-all')
  emit('update:open', false)
}
</script>

<template>
  <PopoverRoot :open="open" @update:open="emit('update:open', $event)">
    <PopoverTrigger as-child>
      <Button variant="ghost" size="sm" class="relative p-1" title="通知">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <Badge v-if="unreadCount > 0" variant="destructive" class="absolute -top-1 -right-1 h-4 min-w-4 text-[0.65rem] px-1">{{ unreadCount }}</Badge>
      </Button>
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent align="end" :side-offset="8" class="bell-popover">
        <header class="flex items-center justify-between px-4 py-3 border-b">
          <div class="flex items-center gap-2">
            <span class="font-bold text-sm">通知</span>
            <Badge v-if="unreadCount > 0" variant="destructive" class="h-4 min-w-4 text-[0.65rem] px-1">{{ unreadCount }}</Badge>
          </div>
          <Button
            size="sm"
            variant="ghost"
            class="text-xs text-muted-foreground h-6 px-2"
            :disabled="unreadCount === 0"
            @click="emit('mark-all-read')"
          >全部已讀</Button>
        </header>
        <div class="bell-popover__list">
          <div
            v-for="alert in recentAlerts"
            :key="alert.id"
            class="bell-popover__item"
            :class="{ 'bell-popover__item--unread': !alert.read }"
            @click="handleOpenDetail(alert)"
          >
            <div class="flex items-center gap-1.5 mb-0.5">
              <Badge variant="outline" class="text-[0.65rem] px-1 py-0" :class="alertTypeBadgeClass(alert.type)">{{ alert.type }}</Badge>
              <span class="text-muted-foreground text-xs ml-auto tabular-nums">{{ alert.time }}</span>
            </div>
            <p class="font-semibold text-sm leading-tight">{{ alert.title }}</p>
            <p class="text-muted-foreground text-xs leading-snug line-clamp-2">{{ alert.detail }}</p>
          </div>
          <div v-if="recentAlerts.length === 0" class="text-center text-muted-foreground text-sm py-6">沒有通知</div>
        </div>
        <footer class="border-t px-4 py-2">
          <Button
            variant="ghost"
            size="sm"
            class="w-full text-sm font-semibold"
            @click="handleViewAll"
          >查看全部通知</Button>
        </footer>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>

<style>
.bell-popover {
  width: 360px;
  max-height: 480px;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.15);
  z-index: 200;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: bell-popover-in 0.15s ease-out;
}

@keyframes bell-popover-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.bell-popover__list {
  overflow-y: auto;
  flex: 1;
}

.bell-popover__item {
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background 0.15s ease;
}

.bell-popover__item:last-child {
  border-bottom: none;
}

.bell-popover__item:hover {
  background: var(--color-muted);
}

.bell-popover__item--unread {
  background: #f8fbff;
  border-left: 3px solid var(--color-primary);
}

@media (max-width: 480px) {
  .bell-popover {
    width: 300px;
  }
}
</style>
