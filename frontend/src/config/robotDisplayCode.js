// The short label is presentation only. API relationships keep the backend ID.
export const robotDisplayCodes = Object.freeze(['C01', 'C02', 'M01', 'M02', 'W01', 'W02', 'W03'])

const codeById = Object.freeze(Object.fromEntries(
  robotDisplayCodes.flatMap((code, index) => {
    const number = String(index + 1)
    const robotNumber = String(index + 1).padStart(2, '0')
    return [
      [`R${robotNumber}`, code],
      [`robot-hospital_robot_${number}`, code],
      [`hospital_robot_${number}`, code],
    ]
  }).concat([['robot-a', 'C01'], ['robot-b', 'C02']]),
))

export const robotDisplayCode = id => {
  const normalizedId = String(id ?? '').replace(/^\/+/, '')
  const match = /^(?:robot-)?hospital_robot_([1-7])$/.exec(normalizedId)
  return codeById[normalizedId] || (match ? robotDisplayCodes[Number(match[1]) - 1] : normalizedId || '—')
}

export const robotDisplayIndex = id => robotDisplayCodes.indexOf(robotDisplayCode(id))
