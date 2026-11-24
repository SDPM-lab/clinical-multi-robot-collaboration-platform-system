<script setup>
import MediSyncBrand from '@/components/MediSyncBrand.vue'
import { overviewThemeVars } from '@/styles/overviewTheme.js'
import { computed, defineAsyncComponent, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Maximize,
  Minimize,
  Moon,
  Sun,
  LogOut,
  UserRoundPen,
  Languages,
  X,
} from '@lucide/vue'
import NotificationCenter from '@/components/NotificationCenter.vue'
import SharedLoading from '@/components/SharedLoading.vue'
import BackendReconnectOverlay from '@/components/BackendReconnectOverlay.vue'
import { SCENE_ASSETS } from '@/config/sceneAssets.js'
import { authStore } from '@/stores/authStore.js'
import { notificationStore } from '@/stores/notificationStore.js'
import { locale, setLocale, t } from '@/i18n/index.js'

const viewLoading = defineComponent({ inheritAttrs: false, render: () => h(SharedLoading, { loading: true }) })
const viewError = defineComponent({ inheritAttrs: false, render: () => h(SharedLoading, { error: t('common.pageLoadError') }) })
const asyncView = loader => defineAsyncComponent({
  loader,
  loadingComponent: viewLoading,
  errorComponent: viewError,
  onError(error, _retry, fail) {
    console.error('Failed to load view:', error)
    fail()
  },
})
const ClinicOverviewView = asyncView(() => import('@/views/ClinicOverviewView.vue'))
const HospitalScene = asyncView(() => import('@/components/scene/HospitalScene.vue'))
const TaskDispatchView = asyncView(() => import('@/views/TaskDispatchView.vue'))
const RobotFleetView = asyncView(() => import('@/views/RobotFleetView.vue'))
const ScheduleHistoryView = asyncView(() => import('@/views/ScheduleHistoryView.vue'))

const THEME_STORAGE_KEY = 'hospital-rmf-color-theme'
const FONT_SIZE_STORAGE_KEY = 'hospital-rmf-font-size'
const fontSizeOptions = ['small', 'medium', 'large']

const readStoredFontSize = () => {
  try {
    const stored = localStorage.getItem(FONT_SIZE_STORAGE_KEY)
    return fontSizeOptions.includes(stored) ? stored : 'small'
  } catch {
    return 'small'
  }
}

const readStoredTheme = () => {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

const darkMode = ref(readStoredTheme() === 'dark')
const fontSize = ref(readStoredFontSize())
const isFullscreen = ref(Boolean(document.fullscreenElement))
const router = useRouter()
const route = useRoute()
const userMenuRoot = ref(null)
const userMenuOpen = ref(false)
const languageMenuOpen = ref(false)
const profileDialogOpen = ref(false)
const profileName = ref('')
const profileAvatarPreview = ref(null)
const profileError = ref('')
const profileFileInput = ref(null)
const sessionError = ref('')
const loggingOut = ref(false)
const savingProfile = ref(false)
watch(() => authStore.authenticated.value, authenticated => {
  if (!authenticated) router.replace({ name: 'login', query: { redirect: route.fullPath } })
})
let userMenuCloseTimer
const openUserMenu = () => { clearTimeout(userMenuCloseTimer); userMenuOpen.value = true }
const closeUserMenuSoon = () => {
  clearTimeout(userMenuCloseTimer)
  userMenuCloseTimer = window.setTimeout(() => { userMenuOpen.value = false }, 150)
}
const onUserMenuFocusOut = (event) => {
  if (!userMenuRoot.value?.contains(event.relatedTarget)) closeUserMenuSoon()
}
const onDocumentPointerDown = (event) => {
  if (!userMenuRoot.value?.contains(event.target)) { userMenuOpen.value = false; languageMenuOpen.value = false }
}
const chooseLanguage = (next) => { setLocale(next); languageMenuOpen.value=false; userMenuOpen.value=false }
const chooseFontSize = (size) => {
  if (fontSizeOptions.includes(size)) fontSize.value = size
}
const handleLogout = async () => {
  if (loggingOut.value) return
  loggingOut.value = true
  sessionError.value = ''
  try {
    await authStore.logout()
    userMenuOpen.value = false
    await router.replace('/login')
  } catch { sessionError.value = t('user.logoutError'); notificationStore.add({ key: 'user.logoutError', type: 'error' }) }
  finally { loggingOut.value = false }
}
const openProfileDialog = () => {
  profileName.value = authStore.currentUser.value.name
  profileAvatarPreview.value = authStore.currentUser.value.avatarUrl || null
  profileError.value = ''
  profileDialogOpen.value = true
  userMenuOpen.value = false
}
const selectProfileAvatar = () => profileFileInput.value?.click()
const showProfileFileError = (key) => {
  profileError.value = key
  notificationStore.add({ key: `user.${key}`, type: 'error' })
}
const previewProfileAvatar = (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!['image/jpeg','image/png','image/webp'].includes(file.type)) { showProfileFileError('invalidImage'); return }
  if (file.size > 3 * 1024 * 1024) { showProfileFileError('imageTooLarge'); return }
  const reader = new FileReader()
  reader.onload = () => { profileAvatarPreview.value = reader.result; profileError.value = '' }
  reader.onerror = () => showProfileFileError('imageReadError')
  reader.readAsDataURL(file)
}
const saveProfile = async () => {
  if (savingProfile.value) return
  savingProfile.value = true
  try {
    await authStore.updateProfile({ name:profileName.value, avatarUrl:profileAvatarPreview.value })
    profileDialogOpen.value = false
    notificationStore.add({ key: 'notifications.profileSaved', type: 'success' })
  } catch (error) { profileError.value = error.code === 'invalid_name' ? 'invalidName' : 'saveError'; notificationStore.add({ key: `user.${profileError.value}`, type: 'error' }) }
  finally { savingProfile.value = false }
}
const currentTheme = computed(() => darkMode.value ? 'dark' : 'light')
const themeToggleLabel = computed(() => (
  darkMode.value ? t('common.lightMode') : t('common.darkMode')
))
const searchParams = new URLSearchParams(window.location.search)
const activeSection = ref(
  searchParams.get('robotDebug') === '1'
    ? 'robots'
    : searchParams.get('dispatchDebug') === '1'
    ? 'dispatch'
    : searchParams.get('mapCameraDebug') === '1'
    ? 'map'
    : 'overview',
)
const dispatchInitialPanel = ref('create')
const navItems = Object.freeze([
  { id: 'overview' },
  { id: 'dispatch' },
  { id: 'history' },
  { id: 'map' },
  { id: 'robots' },
])

const selectSection = (sectionId, panel = 'create') => {
  if (!['overview', 'map', 'dispatch', 'robots', 'history'].includes(sectionId)) return
  dispatchInitialPanel.value = sectionId === 'dispatch' && panel === 'schedule' ? 'schedule' : 'create'
  activeSection.value = sectionId
  if (route.name !== 'overview') router.push('/')
}

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.()
  } else {
    document.exitFullscreen?.()
  }
}
const handleFullscreenChange = () => {
  isFullscreen.value = Boolean(document.fullscreenElement)
  requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))
}

const toggleColorMode = () => {
  darkMode.value = !darkMode.value
}

watch(
  currentTheme,
  (theme) => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme)
    } catch {
      // The visual theme still works when browser storage is unavailable.
    }
  },
  { immediate: true, flush: 'sync' },
)
watch(fontSize, size => {
  document.documentElement.dataset.uiFontSize = size
  try {
    localStorage.setItem(FONT_SIZE_STORAGE_KEY, size)
  } catch {
    // The preference remains active for the current page when browser storage is unavailable.
  }
}, { immediate: true, flush: 'sync' })
onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})
onBeforeUnmount(() => {
  clearTimeout(userMenuCloseTimer)
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})
</script>

<template>
  <main
    class="overview-page app-shell"
    :class="{ 'app-shell--overview': activeSection === 'overview', 'app-shell--dispatch': activeSection === 'dispatch' }"
    :style="['overview', 'dispatch'].includes(activeSection) ? overviewThemeVars : undefined"
    :aria-label="t('common.appShell')"
  >
    <BackendReconnectOverlay />
    <ScheduleHistoryView v-if="activeSection === 'history'" />
    <TaskDispatchView v-else-if="activeSection === 'dispatch'" :initial-panel="dispatchInitialPanel" />
    <RobotFleetView v-else-if="activeSection === 'robots'" />
    <HospitalScene
      v-else-if="activeSection === 'map'"
      :model-url="SCENE_ASSETS.environment"
      mode="original"
      :theme="currentTheme"
    />

    <ClinicOverviewView
      v-if="activeSection === 'overview'"
      :theme="currentTheme"
      @open-dispatch="panel => selectSection('dispatch', panel)"
    />
    <div class="overview-overlay">
      <header class="overview-navbar top-navbar" :class="{'history-navbar':activeSection==='history'}">
        <button type="button" class="brand" :aria-label="t('common.returnHome')" @click="selectSection('overview')"><MediSyncBrand /></button>
        <nav class="overview-nav" :aria-label="t('common.navigation')">
          <button
            v-for="item in navItems"
            :key="item.id"
            type="button"
            class="overview-nav__link"
            :class="{ 'overview-nav__link--active': activeSection === item.id }"
            :aria-current="activeSection === item.id ? 'page' : undefined"
            @click="selectSection(item.id)"
          >{{ t(`nav.${item.id}`) }}</button>
        </nav>
        <div class="overview-actions">
          <NotificationCenter />
          <button
            type="button"
            class="overview-action theme-toggle"
            :title="themeToggleLabel"
            :aria-label="themeToggleLabel"
            :data-tooltip="themeToggleLabel"
            @click="toggleColorMode"
          >
            <Transition name="theme-icon" mode="out-in">
              <Sun v-if="darkMode" key="sun" class="theme-icon" :size="17" :stroke-width="1.8" />
              <Moon v-else key="moon" class="theme-icon" :size="17" :stroke-width="1.8" />
            </Transition>
          </button>
          <button type="button" class="overview-action fullscreen-action" :title="t(isFullscreen ? 'common.exitFullscreen' : 'common.fullscreen')" :aria-label="t(isFullscreen ? 'common.exitFullscreen' : 'common.fullscreen')" :aria-pressed="isFullscreen" @click="toggleFullscreen">
            <component :is="isFullscreen ? Minimize : Maximize" :size="17" :stroke-width="1.8" />
          </button>
          <div ref="userMenuRoot" class="user-menu-root" @mouseenter="openUserMenu" @mouseleave="closeUserMenuSoon" @focusin="openUserMenu" @focusout="onUserMenuFocusOut" @keydown.esc="userMenuOpen = false">
            <button type="button" class="overview-action user-menu-trigger" :aria-label="t('user.menu')" :aria-expanded="userMenuOpen" aria-haspopup="menu" @click="userMenuOpen = !userMenuOpen">
              <img v-if="authStore.currentUser.value.avatarUrl" class="navbar-user-avatar" :src="authStore.currentUser.value.avatarUrl" alt="">
              <span v-else class="navbar-user-initial">{{ authStore.currentUser.value.name.charAt(0).toUpperCase() }}</span>
            </button>
            <Transition name="user-menu-pop">
              <div v-if="userMenuOpen" class="user-menu" role="menu">
                <button type="button" role="menuitem" @click="openProfileDialog"><UserRoundPen :size="14" />{{t('user.profile')}}</button>
                <button type="button" role="menuitem" :aria-expanded="languageMenuOpen" @click="languageMenuOpen=!languageMenuOpen"><Languages :size="14" />{{t('user.language')}}：{{locale==='en'?'English':'中文'}}</button>
                <div v-if="languageMenuOpen" class="language-options" role="group" :aria-label="t('user.language')"><button type="button" :aria-pressed="locale==='zh-TW'" @click="chooseLanguage('zh-TW')">中文</button><button type="button" :aria-pressed="locale==='en'" @click="chooseLanguage('en')">English</button></div>
                <div class="font-size-setting" role="group" :aria-label="t('user.fontSize')">
                  <span>{{ t('user.fontSize') }}</span>
                  <div class="font-size-options">
                    <button v-for="size in fontSizeOptions" :key="size" type="button" :aria-pressed="fontSize===size" @click="chooseFontSize(size)">{{ t(`user.fontSizeOptions.${size}`) }}</button>
                  </div>
                </div>
                <button type="button" role="menuitem" :disabled="loggingOut" @click="handleLogout"><LogOut :size="14" />{{t('user.logout')}}</button>
              </div>
            </Transition>
          </div>
        </div>
      </header>
    </div>
    <Teleport to="body">
      <p v-if="sessionError" class="session-error" role="alert">{{ sessionError }}</p>
      <div v-if="profileDialogOpen" class="profile-dialog-backdrop" @click.self="profileDialogOpen=false">
        <section class="profile-dialog" role="dialog" aria-modal="true" aria-labelledby="profile-dialog-title">
          <header><h2 id="profile-dialog-title">{{t('user.profile')}}</h2><button type="button" :aria-label="t('user.close')" @click="profileDialogOpen=false"><X :size="17"/></button></header>
          <div class="profile-edit-row">
            <div class="profile-avatar-control">
              <button type="button" class="profile-avatar-edit" :aria-label="t('user.avatar')" @click="selectProfileAvatar">
                <span v-if="!profileAvatarPreview">{{ (profileName.trim() || authStore.currentUser.value.name).charAt(0).toUpperCase() }}</span>
                <img v-if="profileAvatarPreview" :src="profileAvatarPreview" alt="">
                <span class="profile-avatar-edit__badge" aria-hidden="true"><UserRoundPen :size="16" /></span>
              </button>
              <small>{{t('user.avatarHint')}}</small>
            </div>
            <label class="profile-name-field" for="profile-display-name">{{t('user.displayName')}}<input id="profile-display-name" v-model="profileName" maxlength="40" autocomplete="name"></label>
          </div>
          <input ref="profileFileInput" class="sr-only" type="file" accept="image/jpeg,image/png,image/webp" aria-hidden="true" tabindex="-1" @change="previewProfileAvatar">
          <p v-if="profileError" role="alert">{{ t(`user.${profileError}`) }}</p>
          <footer><button type="button" @click="profileDialogOpen=false">{{t('user.cancel')}}</button><button type="button" class="profile-save" :disabled="savingProfile || profileName.trim().length < 2" @click="saveProfile">{{t('user.save')}}</button></footer>
        </section>
      </div>
    </Teleport>
  </main>
</template>

<style scoped>
.overview-page {
  position: relative;
  --overview-content-left: 18px;
  --overview-content-right: 18px;
  --overview-calendar-width: 292px;
  --overview-column-gap: 18px;
  --overview-main-right: calc(var(--overview-calendar-width) + var(--overview-column-gap) + var(--overview-content-right));
  --overview-top-row: 124px;
  --overview-calendar-bottom: 416px;
  --overview-task-progress-top: 250px;
  --overview-task-progress-height: calc(var(--overview-calendar-bottom) - var(--overview-task-progress-top));
  --overview-top-bottom-offset: calc(100% - var(--overview-calendar-bottom));
  width: 100%;
  height: 100%;
  overflow: hidden;
  color: var(--text-primary);
  background: transparent;
  transition:
    color 300ms ease,
    background-color 300ms ease;
}

.overview-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  pointer-events: none;
}


.overview-navbar {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  z-index: 50;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  min-height: 62px;
  padding: 0 var(--app-page-gutter);
  color: var(--text-primary);
  background: transparent;
  border: 0;
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  pointer-events: none;
  transition:
    color 300ms ease,
    color 300ms ease;
}

.top-navbar {
  background: transparent;
  border: 0;
  box-shadow: none;
}

:global([data-theme='dark']) .overview-navbar,
:global([data-theme='dark']) .top-navbar {
  background: transparent;
  border: 0;
  box-shadow: none;
}

.overview-action {
  background-color: var(--icon-button-background);
  border-color: var(--icon-button-border);
}

:global([data-theme='dark']) .overview-action {
  background-color: var(--icon-button-background);
  border-color: var(--icon-button-border);
}

.brand {
  --medisync-size: 1.25rem;
  cursor: pointer;
  font-family: inherit;
  flex: 0 0 auto;
  display: flex;
  height: 36px;
  align-items: center;
  justify-self: start;
  padding: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.02em;
  background: transparent;
  border: 0;
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  pointer-events: auto;
}

:global([data-theme='dark']) .brand {
  --medisync-ink: #f4f1ed;
  background: transparent;
  border-color: transparent;
}

.overview-nav {
  display: flex;
  justify-self: center;
  min-width: 0;
  justify-content: center;
  gap: 30px;
  margin: 0;
  pointer-events: auto;
}

.overview-nav__link {
  position: relative;
  padding: 9px 2px;
  color: var(--text-secondary);
  font-size: var(--navbar-font-size);
  font-weight: 500;
  background: transparent;
  border: 0;
  cursor: pointer;
  transition: color 220ms ease;
}

.overview-nav__link::after {
  position: absolute;
  right: 2px;
  bottom: 2px;
  left: 2px;
  height: 2px;
  background: var(--nav-hover);
  border-radius: 999px;
  content: '';
  transform: scaleX(0);
  transform-origin: center;
  transition: transform 200ms ease;
}

.overview-nav__link:hover,
.overview-nav__link:focus-visible {
  color: var(--nav-hover);
}

.overview-nav__link:hover::after,
.overview-nav__link:focus-visible::after,
.overview-nav__link--active::after {
  transform: scaleX(1);
}

.overview-nav__link--active {
  color: var(--nav-active);
}

.overview-nav__link--active::after {
  background: var(--nav-active);
}

.overview-actions {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  justify-self: end;
  pointer-events: auto;
}

.overview-action {
  width: 36px;
  height: 36px;
  padding: 0;
  position: relative;
  display: inline-grid;
  place-items: center;
  color: var(--icon-color);
  font-size: 1.2rem;
  line-height: 1;
  background: var(--icon-button-background);
  border: 1px solid var(--icon-button-border);
  border-radius: 9px;
  box-shadow: var(--control-shadow);
  backdrop-filter: var(--control-backdrop);
  -webkit-backdrop-filter: var(--control-backdrop);
  cursor: pointer;
  transition:
    color 220ms ease,
    background-color 220ms ease,
    border-color 220ms ease,
    transform 180ms ease;
}

.overview-action:hover {
  color: var(--wood-accent);
  background: var(--icon-button-hover);
}

.overview-action:active {
  transform: scale(0.94);
}

.overview-action:focus-visible {
  outline: 2px solid var(--wood-accent);
  outline-offset: 3px;
}
.fullscreen-action,
.fullscreen-action:hover {
  border-color: transparent;
  box-shadow: none;
}
.fullscreen-action:focus-visible {
  outline: 2px solid var(--theme-primary);
  outline-offset: 2px;
}
.user-menu-root { position:relative; }
.navbar-user-avatar{width:24px;height:24px;object-fit:cover;border-radius:50%}.navbar-user-initial{display:grid;width:24px;height:24px;place-items:center;color:#271c19;font-size:10px;font-weight:700;background:var(--theme-primary);border-radius:50%}
.user-menu { position:absolute; top:calc(100% + 8px); right:0; z-index:70; width:218px; padding:5px; background:var(--dropdown-background); border:1px solid var(--glass-border); border-radius:8px; box-shadow:var(--navbar-shadow); }
.user-menu button { display:flex; width:100%; min-height:32px; align-items:center; gap:7px; padding:0 9px; color:var(--text-primary); font-size:12px; background:transparent; border:0; border-radius:5px; cursor:pointer; }
.user-menu button:hover,.user-menu button:focus-visible { color:var(--accent-orange); background:var(--icon-button-hover); outline:none; }
.language-options{display:flex;gap:4px;padding:3px 4px 6px 24px}.language-options button{justify-content:center;min-height:27px;padding:0 6px;font-size:11px}.language-options button[aria-pressed=true]{color:var(--accent-orange);background:var(--theme-primary-soft);font-weight:700}
.font-size-setting{display:grid;gap:4px;padding:5px 7px 7px;color:var(--text-secondary);font-size:11px}.font-size-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px}.user-menu .font-size-options button{justify-content:center;min-height:27px;padding:0 3px;font-size:11px;white-space:nowrap}.user-menu .font-size-options button[aria-pressed=true]{color:var(--accent-orange);background:var(--theme-primary-soft);font-weight:700}
.user-menu-pop-enter-active,.user-menu-pop-leave-active { transition:opacity 140ms ease,transform 140ms ease; }
.user-menu-pop-enter-from,.user-menu-pop-leave-to { opacity:0; transform:translateY(-3px); }

.theme-icon {
  transition:
    transform 420ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease;
}

.theme-toggle:hover .theme-icon {
  transform: rotate(180deg) scale(1.08);
}

.theme-toggle::after {
  position: absolute;
  top: calc(100% + 9px);
  right: -5px;
  z-index: 30;
  padding: 6px 9px;
  color: var(--text-primary);
  font-size: 0.7rem;
  line-height: 1;
  white-space: nowrap;
  background: var(--dropdown-background);
  border: 1px solid var(--glass-border);
  border-radius: 7px;
  box-shadow: var(--navbar-shadow);
  opacity: 0;
  pointer-events: none;
  content: attr(data-tooltip);
  transform: translateY(-3px);
  transition:
    opacity 160ms ease,
    transform 160ms ease;
}

.theme-toggle:hover::after,
.theme-toggle:focus-visible::after {
  opacity: 1;
  transform: translateY(0);
}

:global(.profile-dialog-backdrop){position:fixed;z-index:2000;inset:0;display:grid;place-items:center;padding:20px;background:rgba(11,11,10,.52);backdrop-filter:blur(4px)}:global(.profile-dialog){display:grid;box-sizing:border-box;width:min(460px,calc(100vw - 32px));gap:18px;padding:22px;color:var(--text-primary);background:var(--panel-background-strong);border:1px solid var(--panel-border);border-radius:var(--radius-panel);box-shadow:var(--dropdown-shadow)}:global(.profile-dialog>header){display:flex;align-items:center;justify-content:space-between}:global(.profile-dialog h2){margin:0;font-size:18px}:global(.profile-dialog header button){display:grid;width:32px;height:32px;place-items:center;padding:0;color:var(--text-muted);background:transparent;border:0;border-radius:var(--radius-control);cursor:pointer;transition:color 160ms ease,background 160ms ease}:global(.profile-dialog header button:hover){color:var(--text-primary);background:var(--surface-2)}:global(.profile-edit-row){display:grid;grid-template-columns:112px minmax(0,1fr);align-items:center;gap:18px}:global(.profile-avatar-control){display:grid;justify-items:center;gap:8px}:global(.profile-avatar-edit){position:relative;display:grid;width:78px;height:78px;place-items:center;overflow:visible;padding:0;color:#271c19;font-size:26px;font-weight:600;background:var(--theme-primary);border:2px solid color-mix(in srgb,var(--theme-primary) 50%,var(--panel-border));border-radius:50%;cursor:pointer;transition:transform 180ms ease,border-color 180ms ease,box-shadow 180ms ease}:global(.profile-avatar-edit img){position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:50%}:global(.profile-avatar-edit__badge){position:absolute;right:-3px;bottom:-1px;z-index:1;display:grid;width:29px;height:29px;place-items:center;color:var(--accent-foreground);background:var(--panel-background-strong);border:1px solid var(--panel-border);border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,.12);transition:color 180ms ease,background 180ms ease,transform 180ms ease}:global(.profile-avatar-edit:hover){transform:translateY(-2px);border-color:var(--theme-primary);box-shadow:0 7px 18px color-mix(in srgb,var(--theme-primary) 24%,transparent)}:global(.profile-avatar-edit:hover .profile-avatar-edit__badge){color:#271c19;background:var(--theme-primary);transform:scale(1.06)}:global(.profile-avatar-edit:focus-visible){outline:2px solid var(--theme-primary);outline-offset:4px}:global(.profile-avatar-control small){max-width:112px;color:var(--text-muted);font-size:10px;line-height:1.4;text-align:center}:global(.profile-name-field){display:grid;gap:8px;color:var(--text-secondary);font-size:12px}:global(.profile-name-field input){box-sizing:border-box;width:100%;height:42px;padding:0 12px;color:var(--text-primary);background:var(--surface-2);border:1px solid var(--panel-border);border-radius:var(--radius-control);outline:none;transition:border-color 160ms ease,box-shadow 160ms ease,background 160ms ease}:global(.profile-name-field input:focus){background:var(--panel-background-strong);border-color:var(--theme-primary-border);box-shadow:0 0 0 3px var(--focus-ring)}:global(.profile-dialog>p){margin:0;color:var(--semantic-error);font-size:12px;line-height:1.5}:global(.profile-dialog>footer){display:flex;justify-content:flex-end;gap:9px;padding-top:4px}:global(.profile-dialog footer button){min-width:78px;height:36px;padding:0 12px;color:var(--text-secondary);background:transparent;border:1px solid var(--panel-border);border-radius:var(--radius-control);cursor:pointer;transition:color 160ms ease,background 160ms ease,border-color 160ms ease,transform 160ms ease}:global(.profile-dialog footer button:hover){color:var(--text-primary);background:var(--surface-2);border-color:var(--theme-primary-border)}:global(.profile-dialog footer .profile-save){color:#271c19;background:var(--theme-primary);border-color:transparent}:global(.profile-dialog footer .profile-save:hover){background:var(--theme-primary-hover);transform:translateY(-1px)}:global(.profile-dialog footer .profile-save:disabled){color:var(--text-disabled);background:var(--surface-3);cursor:not-allowed;transform:none}:global(.profile-dialog .sr-only){position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:480px){:global(.profile-edit-row){grid-template-columns:1fr;justify-items:center}:global(.profile-name-field){width:100%}}
@media(prefers-reduced-motion:reduce){:global(.profile-dialog button),:global(.profile-name-field input){transition:none!important}}

.theme-icon-enter-active,
.theme-icon-leave-active {
  transition:
    opacity 240ms ease,
    transform 300ms cubic-bezier(0.22, 1, 0.36, 1);
}

.theme-icon-enter-from {
  opacity: 0;
  transform: rotate(-90deg) scale(0.8);
}

.theme-icon-leave-to {
  opacity: 0;
  transform: rotate(90deg) scale(0.8);
}

@media (max-width: 720px) {
  .overview-navbar {
    top: 0;
    right: 0;
    left: 0;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 6px;
    min-height: 58px;
    padding: 0 14px;
  }

  .overview-nav {
    justify-content: flex-start;
    justify-self: stretch;
    width: 100%;
    min-width: 0;
    gap: 12px;
    margin: 0;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .overview-nav::-webkit-scrollbar { display: none; }

  .brand { padding: 8px 0; --medisync-size: 1rem; }

  .overview-actions { justify-content: flex-end; }

  .overview-nav__link {
    padding: 8px 2px;
    white-space: nowrap;
  }

}

@media (max-width: 900px) {
  .overview-navbar.history-navbar {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: 42px 32px;
    min-height: 80px;
    padding: 0 12px;
  }
  .history-navbar .brand { grid-column: 1; grid-row: 1; white-space: nowrap; }
  .history-navbar .overview-actions { grid-column: 2; grid-row: 1; }
  .history-navbar .overview-nav {
    grid-column: 1 / -1;
    grid-row: 2;
    justify-self: stretch;
    justify-content: flex-start;
    width: 100%;
    gap: 18px;
    margin: 0;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .history-navbar .overview-nav::-webkit-scrollbar { display: none; }
  .history-navbar .overview-nav__link { padding: 5px 2px; white-space: nowrap; }
}

@media (prefers-reduced-motion: reduce) {
  .overview-page,
  .overview-navbar,
  .overview-action,
  .theme-icon,
  .theme-icon-enter-active,
  .theme-icon-leave-active {
    transition-duration: 0.01ms;
  }
  .glass-switch,.glass-switch span { transition:none; }
}
.overview-page:is(.app-shell--overview,.app-shell--dispatch){
  --bg-page:#F2F5F7;
  --bg-map:#E8EDF2;
  --surface-glass:rgba(255,255,255,.52);
  --surface-glass-strong:rgba(255,255,255,.68);
  --glass-border:rgba(255,255,255,.72);
  --overview-stage-background:radial-gradient(circle at 52% 38%,rgba(255,255,255,.5),transparent 48%),linear-gradient(145deg,#eef2f5 0%,var(--bg-map,#E8EDF2) 54%,#e3e9ee 100%);
  --overview-completion-background:linear-gradient(160deg,#fff8df 0%,#fff1bd 58%,#f7e7a5 100%);
  --primary-blue:var(--overview-accent);
  --primary-blue-soft:var(--overview-accent-soft);
  --success-teal:var(--overview-yellow-text);
  --warning-amber:var(--overview-yellow-text);
  --danger-coral:#DD6B62;
  --neutral-slate:#7A8794;
  --nav-hover:var(--theme-primary);
  --nav-active:var(--theme-primary);
  --focus-ring:rgba(var(--overview-accent-rgb),.18);
  --search-background:var(--info-background);
  --search-background-active:var(--info-background);
  --search-border:rgba(255,255,255,.72);
  --search-border-active:rgba(var(--overview-accent-rgb),.4);
  --search-focus-ring:rgba(var(--overview-accent-rgb),.14);
  --dropdown-background:var(--info-background);
  --search-result-hover:rgba(var(--overview-accent-rgb),.09);
  --icon-color:var(--text-secondary);
  --icon-button-background:rgba(255,255,255,.52);
  --icon-button-border:rgba(255,255,255,.72);
  --icon-button-hover:var(--theme-primary-soft);
  --control-shadow:var(--info-shadow);
  background:var(--overview-stage-background)
}
:global(html[data-theme='dark']) .overview-page:is(.app-shell--overview,.app-shell--dispatch){
  --bg-page:var(--app-bg);
  --bg-map:#493833;
  --surface-glass:rgba(85,66,61,.94);
  --surface-glass-strong:rgba(73,56,51,.98);
  --glass-border:rgba(255,243,236,.10);
  --overview-stage-background:var(--app-background-image);
  --overview-completion-background:linear-gradient(160deg,#654d46 0%,#5b453f 68%,#55423d 100%);
  --search-border:rgba(255,243,236,.12);
  --search-border-active:var(--theme-primary-border);
  --icon-button-background:rgba(73,56,51,.96);
  --icon-button-border:rgba(255,243,236,.12);
  background:var(--overview-stage-background)
}
:global(html[data-theme='dark']) .overview-page .overview-navbar .brand,
:global(html[data-theme='dark']) .overview-page .overview-navbar .overview-nav__link,
:global(html[data-theme='dark']) .overview-page .overview-navbar .overview-nav__link:hover,
:global(html[data-theme='dark']) .overview-page .overview-navbar .overview-nav__link:focus-visible{color:#fffffe}
:global(html[data-theme='light']) .overview-page .overview-navbar .overview-nav__link{color:var(--text-secondary)}
:global(html[data-theme='light']) .overview-page .overview-navbar .overview-nav__link:hover,
:global(html[data-theme='light']) .overview-page .overview-navbar .overview-nav__link:focus-visible,
:global(html[data-theme='light']) .overview-page .overview-navbar .overview-nav__link--active{color:var(--color-primary)}
:is(.app-shell--overview,.app-shell--dispatch) .overview-action{background-color:var(--surface-glass);border-color:var(--glass-border);box-shadow:var(--control-shadow);backdrop-filter:var(--control-backdrop);-webkit-backdrop-filter:var(--control-backdrop)}
:global(html[data-theme='dark']) :is(.app-shell--overview,.app-shell--dispatch) .overview-action{background-color:var(--surface-glass);border-color:var(--glass-border)}
:is(.app-shell--overview,.app-shell--dispatch) .overview-action:hover{color:var(--theme-primary);background:var(--overview-accent-soft)}
:is(.app-shell--overview,.app-shell--dispatch) .overview-action:focus-visible{outline-color:var(--theme-primary)}
.overview-action.fullscreen-action,.overview-action.fullscreen-action:hover{border-color:transparent;box-shadow:none}
.overview-action.fullscreen-action[aria-pressed=false],.overview-action.fullscreen-action[aria-pressed=false]:hover{color:var(--icon-color)}
.overview-action.fullscreen-action[aria-pressed=true]{color:var(--theme-primary)}
</style>

<style scoped>
.session-error{position:fixed;z-index:2100;top:85px;right:24px;max-width:340px;padding:13px 18px;border:1px solid #f0c6c1;border-radius:10px;background:#fff1ef;color:#a85851;font-size:13px;box-shadow:0 8px 25px #0001}
</style>
