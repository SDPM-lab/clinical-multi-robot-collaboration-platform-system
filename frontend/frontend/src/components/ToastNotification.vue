<script setup lang="ts">
import { Badge } from '@/components/ui/badge'

defineProps<{
  toasts: Array<Record<string, any>>
}>()

const emit = defineEmits<{
  dismiss: [id: string]
}>()

function typeClass(type: string) {
  const map: Record<string, string> = {
    '異常': 'toast--error',
    '警告': 'toast--warn',
    '完成': 'toast--success',
    '進行中': 'toast--info',
    '資訊': 'toast--info',
  }
  return map[type] || 'toast--info'
}

function typeBadgeClass(type: string) {
  const map: Record<string, string> = {
    '異常': 'bg-red-50 text-red-600 border-red-200',
    '警告': 'bg-amber-50 text-amber-600 border-amber-200',
    '完成': 'bg-emerald-50 text-emerald-600 border-emerald-200',
    '進行中': 'bg-blue-50 text-blue-600 border-blue-200',
    '資訊': 'bg-indigo-50 text-indigo-600 border-indigo-200',
  }
  return map[type] || 'bg-slate-100 text-slate-500 border-slate-200'
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          :class="typeClass(toast.type)"
        >
          <div class="flex items-start gap-2">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5 mb-1">
                <Badge variant="outline" class="text-[0.65rem] px-1 py-0" :class="typeBadgeClass(toast.type)">{{ toast.type }}</Badge>
                <span class="text-muted-foreground text-xs tabular-nums">{{ toast.time }}</span>
              </div>
              <p class="font-semibold text-sm leading-tight">{{ toast.title }}</p>
              <p class="text-muted-foreground text-xs leading-snug line-clamp-2 mt-0.5">{{ toast.detail }}</p>
            </div>
            <button class="toast-close" @click="emit('dismiss', toast.id)" aria-label="關閉">&times;</button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 1.25rem;
  right: 1.25rem;
  z-index: 9999;
  display: flex;
  flex-direction: column-reverse;
  gap: 0.5rem;
  max-width: 380px;
  pointer-events: none;
}

.toast-item {
  pointer-events: auto;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.18);
}

.toast--error { border-left: 4px solid #ef4444; }
.toast--warn  { border-left: 4px solid #f59e0b; }
.toast--success { border-left: 4px solid #22c55e; }
.toast--info  { border-left: 4px solid #3b82f6; }

.toast-close {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--color-muted-foreground);
  font-size: 1.1rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.toast-close:hover {
  background: var(--color-muted);
  color: var(--color-foreground);
}

.toast-enter-active {
  animation: toast-in 0.3s ease-out;
}
.toast-leave-active {
  animation: toast-out 0.25s ease-in forwards;
}

@keyframes toast-in {
  from { opacity: 0; transform: translateX(100%); }
  to   { opacity: 1; transform: translateX(0); }
}
@keyframes toast-out {
  from { opacity: 1; transform: translateX(0); }
  to   { opacity: 0; transform: translateX(100%); }
}

@media (max-width: 480px) {
  .toast-container {
    left: 0.75rem;
    right: 0.75rem;
    max-width: none;
  }
}
</style>
