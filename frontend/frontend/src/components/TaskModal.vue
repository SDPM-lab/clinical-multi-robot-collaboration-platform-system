<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const props = defineProps<{
  modelValue: boolean
  title?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function onOpenChange(open: boolean) {
  emit('update:modelValue', open)
}
</script>

<template>
  <Dialog :open="modelValue" @update:open="onOpenChange">
    <DialogContent class="max-w-[560px] max-h-[85vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
      </DialogHeader>
      <slot />
    </DialogContent>
  </Dialog>
</template>
