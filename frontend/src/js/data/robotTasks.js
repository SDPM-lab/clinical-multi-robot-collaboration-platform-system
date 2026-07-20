export const robotTaskDefinitions = {
  'env-mapping': {
    id: 'env-mapping',
    code: 'TASK-ENV-MAP',
    name: '環境自動辨識與建圖',
    steps: [
      '前往建圖起始位置',
      '啟動環境建圖',
      '自動探索環境',
      '辨識障礙物與環境特徵',
      '產生環境地圖',
      '儲存與回傳地圖位置',
    ],
  },
  'clean-waste': {
    id: 'clean-waste',
    code: 'TASK-CLN-WST',
    name: '終期清消-清物',
    steps: [
      '確認需清消位置及安排清消路線',
      '執行各區域汙染物與垃圾清理',
      '各區域清理狀態確認',
      '完成清物',
      '返回待命任務',
      '重新檢測各區域清理情況',
    ],
  },
  'clean-sanitize': {
    id: 'clean-sanitize',
    code: 'TASK-CLN-SAN',
    name: '終期清消-清汙',
    steps: [
      '確認清消物品數量及機器人狀態',
      '確認需清消位置及安排清消路線',
      '執行環境清消',
      '各區域清理狀態確認',
      '完成並停止清消設備',
      '計算此次清消消耗量',
      '返回待命位置',
    ],
  },
  'coating-sterilize': {
    id: 'coating-sterilize',
    code: 'TASK-COT-STR',
    name: '環境鍍膜殺菌',
    steps: [
      '確認鍍膜殺菌功能是否正常',
      '掃描環境各區域',
      '安排鍍膜殺菌路線',
      '執行鍍膜殺菌',
      '完成鍍膜殺菌',
      '返回待命位置',
    ],
  },
  'self-charge': {
    id: 'self-charge',
    code: 'TASK-CHARGE',
    name: '自我充電',
    steps: [
      '確認目前電量',
      '與充電座進行對接',
      '開始充電',
      '確認充電狀態',
      '完成充電',
      '離開充電座並返回待命',
    ],
  },
}

export const robotTaskAssignments = {
  'robot-a': [
    { ...robotTaskDefinitions['self-charge'], currentStep: 2, status: '執行中' },
  ],
  'robot-b': [
    { ...robotTaskDefinitions['env-mapping'], currentStep: 6, status: '已完成', completedAt: '2026-07-10 09:42' },
    { ...robotTaskDefinitions['clean-waste'], currentStep: 4, status: '執行中' },
    { ...robotTaskDefinitions['clean-sanitize'], currentStep: 0, status: '待執行' },
    { ...robotTaskDefinitions['coating-sterilize'], currentStep: 0, status: '待執行' },
  ],
}

export function getRobotTasks(robotId) {
  return robotTaskAssignments[robotId] || []
}

export function getRobotTask(robotId, taskId) {
  const tasks = getRobotTasks(robotId)
  return tasks.find(t => t.id === taskId) || null
}
