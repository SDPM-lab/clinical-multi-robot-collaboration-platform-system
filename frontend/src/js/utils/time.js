export const parseTaskTime = (time) => {
  if (!time || time === '未設定') return Number.MAX_SAFE_INTEGER
  const [hours = '0', minutes = '0'] = time.split(':')
  const h = Number(hours)
  const m = Number(minutes)
  return Number.isNaN(h) || Number.isNaN(m) ? Number.MAX_SAFE_INTEGER : h * 60 + m
}
