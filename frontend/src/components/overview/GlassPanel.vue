<script setup>
defineProps({
  title: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <section class="glass-panel">
    <header v-if="title" class="glass-panel__header">
      <h2>{{ title }}</h2>
      <slot name="header-meta" />
    </header>
    <div class="glass-panel__content">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.glass-panel {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  padding: 20px 22px;
  color: var(--text-primary);
  background: var(--panel-background);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-panel);
  box-shadow: var(--panel-shadow);
  backdrop-filter: blur(var(--panel-blur));
  -webkit-backdrop-filter: blur(var(--panel-blur));
  transition:
    color 300ms ease,
    background-color 300ms ease,
    border-color 300ms ease,
    box-shadow 300ms ease;
}

.glass-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 13px;
  border-bottom: 1px solid var(--glass-divider);
  transition: border-color 300ms ease;
}

.glass-panel__header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.025em;
}

.glass-panel__content {
  min-width: 0;
  padding-top: 10px;
  transition: color 300ms ease;
}

:global([data-theme='dark']) .glass-panel {
  background: var(--panel-background);
  border-color: var(--panel-border);
  box-shadow: var(--panel-shadow);
  backdrop-filter: blur(var(--panel-blur));
  -webkit-backdrop-filter: blur(var(--panel-blur));
}
</style>
