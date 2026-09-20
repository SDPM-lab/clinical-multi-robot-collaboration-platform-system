<script setup>
defineProps({ selected: { type: Boolean, default: false } })
</script>

<template><span class="task-duration-range" :class="{ 'is-selected': selected }"><i></i><i></i></span></template>

<style scoped>
.task-duration-range{position:absolute;z-index:3;height:2px;background:color-mix(in srgb,var(--task-main) 54%,transparent);transform:translateY(-50%);pointer-events:none}.task-duration-range::before,.task-duration-range::after{position:absolute;top:50%;width:1px;height:8px;background:color-mix(in srgb,var(--task-main) 72%,transparent);content:'';transform:translateY(-50%)}.task-duration-range::before{left:0}.task-duration-range::after{right:0}.task-duration-range.is-selected{height:3px;background:color-mix(in srgb,var(--task-main) 72%,transparent)}
</style>
