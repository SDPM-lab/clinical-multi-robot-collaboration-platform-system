export const clinicFloorOptions = Object.freeze([
  Object.freeze({ id: 'all', code: 'ALL', label: '全棟' }),
  Object.freeze({ id: 3, code: '03', label: 'Floor 3' }),
  Object.freeze({ id: 2, code: '02', label: 'Floor 2' }),
  Object.freeze({ id: 1, code: '01', label: 'Floor 1' }),
])

export const completionByFloor = Object.freeze({
  all: Object.freeze([
    Object.freeze({ id: 1, label: 'Floor 1', percentage: 86, completed: 18, total: 21, color: '#e88932' }),
    Object.freeze({ id: 2, label: 'Floor 2', percentage: 72, completed: 13, total: 18, color: '#eea63a' }),
    Object.freeze({ id: 3, label: 'Floor 3', percentage: 64, completed: 9, total: 14, color: '#f2bf52' }),
  ]),
  1: Object.freeze({ id: 1, label: 'Floor 1', completed: 18, total: 21, percentage: 86, color: '#e88932' }),
  2: Object.freeze({ id: 2, label: 'Floor 2', completed: 13, total: 18, percentage: 72, color: '#eea63a' }),
  3: Object.freeze({ id: 3, label: 'Floor 3', completed: 9, total: 14, percentage: 64, color: '#f2bf52' }),
})

export const taskProgressByRobot = Object.freeze({
  robot01: Object.freeze({
    taskId: 'T001', robotId: 'C01', robotState: 'busy', floor: 'Floor 1',
    steps: Object.freeze([
      Object.freeze({ label: '藥局取件', location: '藥局', status: 'completed', statusLabel: '已完成', time: '09:30' }),
      Object.freeze({ label: '前往護理站', location: '一樓護理站', status: 'completed', statusLabel: '已完成', time: '09:38' }),
      Object.freeze({ label: '藥品配送', location: '一樓診療區', status: 'active', statusLabel: '執行中', time: '現在' }),
      Object.freeze({ label: '返回駐點', location: '接待櫃檯', status: 'pending', statusLabel: '等待中', time: '10:05' }),
    ]),
  }),
  robot02: Object.freeze({
    taskId: 'T014', robotId: 'C02', robotState: 'charging', floor: 'Floor 2',
    steps: Object.freeze([
      Object.freeze({ label: '領取檢體', location: '二樓檢驗室', status: 'completed', statusLabel: '已完成', time: '10:42' }),
      Object.freeze({ label: '電梯轉運', location: '中央電梯', status: 'completed', statusLabel: '已完成', time: '10:49' }),
      Object.freeze({ label: '檢體送達', location: '收件櫃檯', status: 'completed', statusLabel: '已完成', time: '11:00' }),
      Object.freeze({ label: '前往充電', location: '充電站 A', status: 'active', statusLabel: '充電中', time: '現在' }),
    ]),
  }),
  robot03: Object.freeze({
    taskId: 'T021', robotId: 'M01', robotState: 'idle', floor: 'Floor 3',
    steps: Object.freeze([
      Object.freeze({ label: '備品裝載', location: '中央庫房', status: 'completed', statusLabel: '已完成', time: '13:58' }),
      Object.freeze({ label: '前往病房', location: '三樓走廊', status: 'completed', statusLabel: '已完成', time: '14:10' }),
      Object.freeze({ label: '物資補充', location: '三樓護理站', status: 'active', statusLabel: '執行中', time: '現在' }),
      Object.freeze({ label: '返回待命', location: '機器人駐點', status: 'pending', statusLabel: '等待中', time: '14:40' }),
    ]),
  }),
})

const scheduleVariants = Object.freeze([
  Object.freeze([
    Object.freeze({ time: '09:30', title: '藥品配送', assignee: 'C01', state: 'active' }),
    Object.freeze({ time: '11:00', title: '檢體運送', assignee: 'C02', state: 'scheduled' }),
    Object.freeze({ time: '14:20', title: '病房物資補充', assignee: '尚未指派', state: 'scheduled' }),
    Object.freeze({ time: '16:00', title: 'M01 充電', assignee: '充電站 A', state: 'scheduled' }),
  ]),
  Object.freeze([
    Object.freeze({ time: '08:50', title: '門診文件配送', assignee: 'C01', state: 'completed' }),
    Object.freeze({ time: '10:40', title: '檢體收件', assignee: 'C02', state: 'active' }),
    Object.freeze({ time: '15:10', title: '護理站補給', assignee: 'M01', state: 'scheduled' }),
  ]),
  Object.freeze([
    Object.freeze({ time: '09:10', title: '藥品盤點配送', assignee: 'C01', state: 'completed' }),
    Object.freeze({ time: '13:30', title: '檢驗報告運送', assignee: 'C02', state: 'scheduled' }),
    Object.freeze({ time: '16:20', title: '清潔用品補充', assignee: 'M01', state: 'scheduled' }),
  ]),
])

const pad = (value) => String(value).padStart(2, '0')
export const toLocalDateKey = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`

export const createClinicDailySchedules = (reference = new Date()) => Object.freeze(
  Array.from({ length: 9 }, (_, index) => {
    const offset = index - 4
    const date = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate() + offset)
    return Object.freeze({
      key: toLocalDateKey(date),
      day: date.getDate(),
      month: date.getMonth() + 1,
      weekday: ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][date.getDay()],
      today: offset === 0,
      items: scheduleVariants[(index + 1) % scheduleVariants.length],
    })
  }),
)

export const clinicOverviewModelUrl = '/models/hospital_overview.glb?v=86b09da6'
