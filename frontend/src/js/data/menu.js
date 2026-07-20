export const menuItems = [
  { id: 'dispatch', label: '任務派遣', description: '指派任務給機器人' },
  { id: 'robots', label: '機器人狀態', description: '查看機器人狀態與電量' },
  { id: 'schedule', label: '排程歷史', description: '檢視任務歷史與進度' },
  { id: 'map', label: '即時地圖', description: 'ROS2 RViz 2D 即時檢視' },
  { id: 'alerts', label: '通知中心', description: '即時提醒與異常訊息' },
]

export const sectionMap = {
  dispatch: { title: '任務派遣', description: '快速指派與追蹤醫療機器人任務', badge: '派遣中心' },
  robots: { title: '機器人狀態', description: '了解每台機器人的即時狀態與電量', badge: '機器人監控' },
  schedule: { title: '排程歷史', description: '檢視任務歷史與排程完成情況', badge: '歷史記錄' },
  map: { title: '即時地圖', description: '透過 ROS2 取得地圖、定位與路徑資訊', badge: 'RViz 2D' },
  alerts: { title: '通知中心', description: '查看重要提醒與異常訊息', badge: '即時通知' },
}
