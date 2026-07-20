const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

export async function createHospitalTask(task) {
  const response = await fetch(`${API_BASE_URL}/api/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(task)
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(data?.message || '任務送出失敗')
  }

  return data
}

export async function checkBackendHealth() {
  const response = await fetch(`${API_BASE_URL}/api/tasks/health`)
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error('後端健康檢查失敗')
  }

  return data
}
