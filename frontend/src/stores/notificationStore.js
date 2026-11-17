import { readonly, ref } from 'vue'

const items = ref([])
let nextId = 0
// 保留本次登入期間的最近 100 則訊息；關閉提示不會刪除通知紀錄。
export const notificationStore = {
  items: readonly(items),
  add({ key, params = {}, text = '', type = 'info', taskTitle = null }) {
    items.value.unshift({ id: ++nextId, key, params, text, type, taskTitle, timestamp: Date.now(), read: false })
    items.value = items.value.slice(0, 100)
  },
  markAllRead() { items.value.forEach(item => { item.read = true }) },
  clear() { items.value = [] },
}
