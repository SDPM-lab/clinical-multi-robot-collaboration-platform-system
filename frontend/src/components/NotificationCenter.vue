<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Bell, CheckCircle2, CircleAlert, Info, Trash2 } from '@lucide/vue'
import { notificationStore } from '@/stores/notificationStore.js'
import { localeTag, t, translateTask } from '@/i18n/index.js'

const root = ref(null)
const open = ref(false)
const items = notificationStore.items
const unread = computed(() => items.value.filter(item => !item.read).length)
let closeTimer
const show = () => { clearTimeout(closeTimer); open.value = true; notificationStore.markAllRead() }
const hide = () => { clearTimeout(closeTimer); open.value = false }
const hideSoon = () => { clearTimeout(closeTimer); closeTimer = setTimeout(hide, 150) }
const outside = event => { if (!root.value?.contains(event.target)) hide() }
watch(() => items.value.length ? items.value[0].id : null, () => { if (open.value) notificationStore.markAllRead() })
const message = item => item.key ? t(item.key, { ...item.params, ...(item.taskTitle ? { title: translateTask(item.taskTitle) } : {}) }) : item.text
const time = item => new Intl.DateTimeFormat(localeTag.value, { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(item.timestamp)
onMounted(() => document.addEventListener('pointerdown', outside))
onBeforeUnmount(() => { clearTimeout(closeTimer); document.removeEventListener('pointerdown', outside) })
</script>

<template>
  <div ref="root" class="notification-root" @mouseenter="show" @mouseleave="hideSoon" @focusout="event => { if (!root?.contains(event.relatedTarget)) hideSoon() }" @keydown.esc.stop.prevent="hide">
    <button class="notification-bell" type="button" :aria-label="t('notifications.title')" :aria-expanded="open" aria-controls="notification-panel" @click="show" @keydown.down.prevent="show">
      <Bell :size="20" :stroke-width="1.7" /><span v-if="unread" class="notification-badge">{{ unread > 99 ? '99+' : unread }}</span>
    </button>
    <Transition name="notification-panel">
    <section v-if="open" id="notification-panel" class="notification-panel" :aria-label="t('notifications.title')">
      <header><strong>{{ t('notifications.title') }}</strong><button type="button" :disabled="!items.length" @click="notificationStore.clear()"><Trash2 :size="14" />{{ t('notifications.clear') }}</button></header>
      <p v-if="!items.length" class="notification-empty">{{ t('notifications.empty') }}</p>
      <ul v-else><li v-for="item in items" :key="item.id" :class="item.type">
        <component :is="item.type === 'success' ? CheckCircle2 : item.type === 'error' ? CircleAlert : Info" :size="18" />
        <div><p>{{ message(item) }}</p><time :datetime="new Date(item.timestamp).toISOString()">{{ time(item) }}</time></div>
      </li></ul>
      <footer>{{ t('notifications.session') }}</footer>
    </section>
    </Transition>
  </div>
</template>

<style scoped>
.notification-root{position:relative;flex-shrink:0;--bell-active-bg:#fff0e5;--bell-active-color:#bc642f;--bell-active-border:#efc7aa}
.notification-bell{position:relative;display:grid;place-items:center;width:40px;height:40px;border:1px solid var(--icon-button-border,#ffffffb3);border-radius:12px;background:var(--icon-button-background,#ffffffb3);color:var(--text-muted,#838780);cursor:pointer;transition:background-color .18s ease,color .18s ease,border-color .18s ease,box-shadow .18s ease}
.notification-bell:hover,.notification-bell[aria-expanded=true]{color:var(--bell-active-color);background:var(--bell-active-bg);border-color:var(--bell-active-border)}
.notification-badge{position:absolute;right:-4px;top:-5px;min-width:17px;height:17px;padding:0 3px;border-radius:10px;background:#ed976b;color:white;font-size:10px;line-height:17px;text-align:center;box-sizing:border-box}
.notification-panel{position:absolute;top:calc(100% + 9px);right:0;width:min(320px,calc(100vw - 32px));border:1px solid var(--icon-button-border,#e5e7e5);border-radius:12px;background:var(--panel-bg-strong,#fff);color:var(--text-primary,#3c413e);box-shadow:0 12px 36px #25352a24;backdrop-filter:blur(24px);z-index:200;transform-origin:top right}
.notification-panel::before{content:'';position:absolute;top:-11px;left:0;right:0;height:11px}
header{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 13px;border-bottom:1px solid var(--panel-border,#89968a20)}header strong{font-size:12px;font-weight:600}
header button{display:flex;align-items:center;gap:4px;border:0;border-radius:6px;padding:5px;background:transparent;color:var(--text-muted,#818982);font:inherit;font-size:10px;cursor:pointer;transition:background-color .18s ease,color .18s ease}
header button:hover:enabled{background:var(--bell-active-bg);color:var(--bell-active-color)}header button:disabled{opacity:.4;cursor:default}
ul{list-style:none;padding:0;margin:0;max-height:300px;overflow:auto}li{display:flex;gap:8px;padding:10px 13px;border-bottom:1px solid var(--panel-border,#89968a15)}li>svg{flex-shrink:0;width:16px;height:16px;margin-top:1px;color:#7199be}li.success>svg{color:#69a183}li.error>svg{color:#ce7d76}li p{margin:0 0 3px;font-size:11.5px;line-height:1.5;overflow-wrap:anywhere}time,footer{font-size:10px;color:var(--text-muted,#929992)}footer{padding:8px 13px;line-height:1.5}.notification-empty{padding:18px 13px;text-align:center;font-size:11.5px;color:var(--text-muted,#929992)}
button:focus-visible{outline:2px solid #eea175;outline-offset:3px}
.notification-panel-enter-active,.notification-panel-leave-active{transition:opacity .18s ease,transform .18s ease}.notification-panel-enter-from,.notification-panel-leave-to{opacity:0;transform:translateY(-4px)}
:global([data-theme='dark']) .notification-root{--bell-active-bg:#514032;--bell-active-color:#ffc294;--bell-active-border:#846046}
@media(prefers-reduced-motion:reduce){.notification-bell,header button,.notification-panel-enter-active,.notification-panel-leave-active{transition:none}}
</style>
