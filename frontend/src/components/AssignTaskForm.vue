<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PLACE_LABEL } from '@/js/data/taskMeta.js'

const props = defineProps<{
  robots: Array<Record<string, any>>
}>()

const emit = defineEmits<{
  'assign-task': [payload: Record<string, any>]
}>()

const submitted = ref(false)

const form = reactive({
  title: '',
  robot: 'auto',
  startTime: '',
  place: '',
  actions: [] as string[],
  description: '',
})

const cleanObjectChecked = computed(() => form.actions.includes('clean-object'))

const cleanAllChecked = computed(
  () => form.actions.includes('clean-object') || form.actions.includes('clean-stain')
)

function toggleCleanAll() {
  if (cleanAllChecked.value) {
    form.actions = form.actions.filter(a => a !== 'clean-object' && a !== 'clean-stain')
  } else {
    if (!form.actions.includes('clean-object')) form.actions.push('clean-object')
    if (!form.actions.includes('clean-stain'))  form.actions.push('clean-stain')
  }
}

watch(cleanObjectChecked, (val) => {
  if (!val) form.actions = form.actions.filter(a => a !== 'clean-stain')
})

function toggleAction(value: string) {
  const idx = form.actions.indexOf(value)
  if (idx >= 0) form.actions.splice(idx, 1)
  else form.actions.push(value)
}

function submit() {
  submitted.value = true
  if (!form.title.trim() || !form.place || form.actions.length === 0) return
  emit('assign-task', {
    title: form.title.trim(),
    robot: form.robot,
    startTime: form.startTime || '',
    place: form.place,
    items: form.actions.slice(),
    description: form.description.trim(),
  })
  submitted.value = false
  form.title = ''
  form.description = ''
  form.startTime = ''
  form.place = ''
  form.actions = []
}
</script>

<template>
  <Card class="anim-slide-up bg-muted">
    <CardContent class="grid gap-4 p-4">
      <h3 class="font-bold text-lg">新增任務</h3>

      <div class="grid gap-2">
        <Label>任務標題<span class="text-red-500 ml-0.5">*</span></Label>
        <Input v-model="form.title" placeholder="例如：配送樣本到 4A" />
        <p v-if="submitted && !form.title.trim()" class="text-sm text-red-500">此欄位為必填</p>
      </div>

      <div class="grid gap-2">
        <Label>指派機器人</Label>
        <Select v-model="form.robot">
          <SelectTrigger>
            <SelectValue placeholder="選擇機器人" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">由系統安排</SelectItem>
            <SelectItem v-for="robot in robots" :key="robot.id" :value="robot.id">{{ robot.name }}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div class="grid gap-2">
        <Label>任務地點<span class="text-red-500 ml-0.5">*</span></Label>
        <Select v-model="form.place">
          <SelectTrigger>
            <SelectValue placeholder="選擇任務地點" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="(label, id) in PLACE_LABEL" :key="id" :value="id">{{ label }}</SelectItem>
          </SelectContent>
        </Select>
        <p v-if="submitted && !form.place" class="text-sm text-red-500">此欄位為必填</p>
      </div>

      <div class="grid gap-2">
        <Label>預計開始時間</Label>
        <Input type="time" v-model="form.startTime" />
      </div>

      <Card class="bg-background">
        <CardContent class="p-4 grid gap-3">
          <span class="font-bold text-base">處理事項<span class="text-red-500 ml-0.5">*</span></span>
          <p v-if="submitted && form.actions.length === 0" class="text-sm text-red-500">請至少選擇一項處理事項</p>
          <div class="grid gap-2">
            <div class="flex items-center gap-2">
              <Checkbox
                id="action-clean-all"
                :model-value="cleanAllChecked"
                @update:model-value="toggleCleanAll"
              />
              <Label for="action-clean-all" class="cursor-pointer text-sm font-medium">清理消毒</Label>
            </div>
            <div class="pl-3 grid gap-2 border-l-2 border-muted">
              <div class="flex items-start gap-2">
                <Checkbox
                  id="action-clean-object"
                  class="mt-0.5"
                  :model-value="form.actions.includes('clean-object')"
                  @update:model-value="toggleAction('clean-object')"
                />
                <div>
                  <Label for="action-clean-object" class="cursor-pointer">① 清物</Label>
                  <p class="text-xs text-muted-foreground">清理汙染物和垃圾</p>
                </div>
              </div>
              <div class="flex items-start gap-2">
                <Checkbox
                  id="action-clean-stain"
                  class="mt-0.5"
                  :disabled="!cleanObjectChecked"
                  :model-value="form.actions.includes('clean-stain')"
                  @update:model-value="toggleAction('clean-stain')"
                />
                <div>
                  <Label
                    for="action-clean-stain"
                    class="cursor-pointer"
                    :class="!cleanObjectChecked && 'opacity-40'"
                  >② 清汙</Label>
                  <p class="text-xs text-muted-foreground" :class="!cleanObjectChecked && 'opacity-40'">消毒及清潔汙漬</p>
                </div>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox
              id="action-coat"
              :model-value="form.actions.includes('coat-sterilize')"
              @update:model-value="toggleAction('coat-sterilize')"
            />
            <Label for="action-coat" class="cursor-pointer">鍍膜殺菌</Label>
          </div>
        </CardContent>
      </Card>

      <div class="grid gap-2">
        <Label>任務內容</Label>
        <Textarea v-model="form.description" :rows="3" placeholder="補充備註，例如：需優先使用無菌包裝" />
      </div>

      <Button class="w-full font-bold py-5" @click="submit">指派任務</Button>
    </CardContent>
  </Card>
</template>
