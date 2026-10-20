<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Search, X } from '@lucide/vue'
import { t } from '@/i18n/index.js'

const emit = defineEmits(['select'])

const searchItems = computed(() => [
  ...['dispatch','history','map','robots'].map(id=>({ id, label:t(`nav.${id}`), type:t('search.page'), section:id })),
  ...[1,2,3].map(number=>({ id:`robot-0${number}`, label:`Robot 0${number}`, type:t('search.robot'), section:'overview' })),
  { id:'today-tasks', label:t('search.todayTasks'), type:t('search.task'), section:'overview' },
])

const typeOrder = computed(()=>[t('search.page'),t('search.robot'),t('search.task')])
const root = ref(null)
const input = ref(null)
const query = ref('')
const expanded = ref(false)
const focused = ref(false)
const activeIndex = ref(-1)

const normalizedQuery = computed(() => query.value.trim().toLocaleLowerCase())
const results = computed(() => {
  if (!normalizedQuery.value) return []
  return searchItems.value.filter(({ label }) => (
    label.toLocaleLowerCase().includes(normalizedQuery.value)
  ))
})
const groupedResults = computed(() => typeOrder.value
  .map((type) => ({ type, items: results.value.filter((item) => item.type === type) }))
  .filter(({ items }) => items.length > 0))
const dropdownVisible = computed(() => focused.value && normalizedQuery.value.length > 0)
const activeDescendant = computed(() => (
  activeIndex.value >= 0 ? `overview-search-result-${results.value[activeIndex.value]?.id}` : undefined
))

const openSearch = async () => {
  expanded.value = true
  await nextTick()
  input.value?.focus()
}

const closeSearch = () => {
  focused.value = false
  activeIndex.value = -1
  expanded.value = false
  input.value?.blur()
}

const clearSearch = async () => {
  query.value = ''
  activeIndex.value = -1
  await nextTick()
  input.value?.focus()
}

const chooseResult = (item) => {
  query.value = item.label
  activeIndex.value = -1
  focused.value = false
  expanded.value = false
  emit('select', item)
  input.value?.blur()
}

const moveActive = (direction) => {
  if (!results.value.length) return
  const nextIndex = activeIndex.value + direction
  activeIndex.value = (nextIndex + results.value.length) % results.value.length
}

const onKeydown = (event) => {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActive(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActive(-1)
  } else if (event.key === 'Enter' && results.value.length > 0) {
    event.preventDefault()
    chooseResult(results.value[activeIndex.value >= 0 ? activeIndex.value : 0])
  } else if (event.key === 'Escape') {
    event.preventDefault()
    closeSearch()
  }
}

const onDocumentPointerDown = (event) => {
  if (!root.value?.contains(event.target)) closeSearch()
}

onMounted(() => document.addEventListener('pointerdown', onDocumentPointerDown))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))
</script>

<template>
  <div ref="root" class="overview-search" :class="{ 'overview-search--expanded': expanded }">
    <button
      type="button"
      class="overview-search__mobile-trigger"
      :aria-label="t('search.open')"
      :aria-expanded="expanded"
      @click="openSearch"
    >
      <Search :size="18" :stroke-width="1.8" />
    </button>

    <div class="overview-search__field">
      <Search class="overview-search__icon" :size="17" :stroke-width="1.8" aria-hidden="true" />
      <input
        ref="input"
        v-model="query"
        type="search"
        role="combobox"
        :aria-label="t('common.search')"
        aria-controls="overview-search-results"
        :aria-expanded="dropdownVisible"
        :aria-activedescendant="activeDescendant"
        autocomplete="off"
        :placeholder="t('common.search')"
        @focus="focused = true; expanded = true"
        @input="activeIndex = -1"
        @keydown="onKeydown"
      />
      <button
        v-if="query"
        type="button"
        class="overview-search__clear"
        :aria-label="t('search.clear')"
        @click="clearSearch"
      >
        <X :size="15" :stroke-width="1.8" />
      </button>
    </div>

    <Transition name="search-results">
      <div
        v-if="dropdownVisible"
        id="overview-search-results"
        class="overview-search__dropdown"
        role="listbox"
      >
        <template v-if="groupedResults.length">
          <section v-for="group in groupedResults" :key="group.type" class="search-result-group">
            <h3>{{ group.type }}</h3>
            <button
              v-for="item in group.items"
              :id="`overview-search-result-${item.id}`"
              :key="item.id"
              type="button"
              role="option"
              :aria-selected="results[activeIndex]?.id === item.id"
              :class="{ 'search-result--active': results[activeIndex]?.id === item.id }"
              @pointermove="activeIndex = results.findIndex((result) => result.id === item.id)"
              @pointerdown.prevent="chooseResult(item)"
            >
              {{ item.label }}
            </button>
          </section>
        </template>
        <p v-else class="overview-search__empty">{{t('search.empty')}}</p>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.overview-search {
  position: relative;
  flex: 0 0 auto;
  width: 210px;
  transition: width 220ms ease;
}

.overview-search:focus-within {
  width: 250px;
}

.overview-search__field {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  height: 38px;
  color: var(--text-secondary);
  background: var(--search-background);
  border: 1px solid var(--search-border);
  border-radius: var(--radius-control);
  box-shadow: var(--control-shadow);
  backdrop-filter: var(--control-backdrop);
  -webkit-backdrop-filter: var(--control-backdrop);
  transition: border-color 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
}

.overview-search__field:hover,
.overview-search__field:focus-within {
  border-color: var(--search-border-active);
  background: var(--search-background-active);
}

.overview-search__field:focus-within {
  box-shadow: 0 0 0 3px var(--search-focus-ring), var(--control-shadow);
}

.overview-search__icon {
  position: absolute;
  left: 12px;
  pointer-events: none;
}

.overview-search input {
  width: 100%;
  min-width: 0;
  height: 100%;
  padding: 0 34px 0 38px;
  color: var(--text-primary);
  font-size: 13px;
  background: transparent;
  border: 0;
  outline: 0;
  appearance: none;
}

.overview-search input::-webkit-search-cancel-button { display: none; }
.overview-search input::placeholder { color: var(--text-secondary); opacity: 0.82; }

.overview-search__clear {
  position: absolute;
  right: 8px;
  display: grid;
  width: 24px;
  height: 24px;
  padding: 0;
  color: var(--text-secondary);
  background: transparent;
  border: 0;
  border-radius: var(--radius-control);
  cursor: pointer;
  place-items: center;
}

.overview-search__clear:hover { color: var(--nav-hover); background: var(--icon-button-hover); }

.overview-search__dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 40;
  width: min(100%, 250px);
  max-height: min(380px, calc(100vh - 82px));
  padding: 8px;
  overflow-y: auto;
  color: var(--text-primary);
  background: var(--dropdown-background);
  border: 1px solid var(--glass-border);
  border-radius: 5px;
  box-shadow: var(--dropdown-shadow);
  backdrop-filter: var(--control-backdrop);
  -webkit-backdrop-filter: var(--control-backdrop);
}

.search-result-group + .search-result-group { margin-top: 5px; padding-top: 5px; border-top: 1px solid var(--glass-divider); }
.search-result-group h3 { margin: 4px 8px 3px; color: var(--text-secondary); font-size: 11px; font-weight: 600; letter-spacing: 0.08em; }
.search-result-group button {
  display: block;
  width: 100%;
  padding: 8px 9px;
  color: var(--text-primary);
  font-size: 13px;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-control);
  cursor: pointer;
}
.search-result-group button:hover,
.search-result-group .search-result--active { color: var(--nav-active); background: var(--search-result-hover); }
.overview-search__empty { margin: 0; padding: 15px 10px; color: var(--text-secondary); font-size: 13px; text-align: center; }

.overview-search__mobile-trigger { display: none; }

.search-results-enter-active,
.search-results-leave-active { transition: opacity 150ms ease, transform 150ms ease; }
.search-results-enter-from,
.search-results-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 900px) {
  .overview-search { width: 36px; }
  .overview-search:focus-within,
  .overview-search--expanded {
    position: absolute;
    top: -1px;
    right: 0;
    z-index: 5;
    width: min(250px, calc(100vw - 28px));
  }
  .overview-search__field { display: none; }
  .overview-search--expanded .overview-search__field { display: flex; }
  .overview-search__mobile-trigger {
    display: grid;
    width: 36px;
    height: 36px;
    padding: 0;
    color: var(--icon-color);
    background: var(--icon-button-background);
    border: 1px solid var(--icon-button-border);
    border-radius: var(--radius-control);
    box-shadow: var(--control-shadow);
    cursor: pointer;
    place-items: center;
    backdrop-filter: var(--control-backdrop);
  }
  .overview-search--expanded .overview-search__mobile-trigger { display: none; }
  .overview-search__dropdown { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .overview-search,
  .search-results-enter-active,
  .search-results-leave-active { transition-duration: 0.01ms; }
}
</style>
