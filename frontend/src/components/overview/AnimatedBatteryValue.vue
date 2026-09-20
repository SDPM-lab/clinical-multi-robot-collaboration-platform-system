<script setup>
import { computed, onMounted } from 'vue'
import { useCountUp } from '@/composables/useCountUp.js'
const props = defineProps({ value: { type: Number, default: 0 }, delay: { type: Number, default: 0 } })
const { displayed, restart } = useCountUp(computed(() => props.value), { duration: 2000, delay: props.delay })
onMounted(restart)
</script>
<template><span>{{ displayed }}</span></template>
