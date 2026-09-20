import { readonly, ref } from 'vue'

const authenticated = ref(true)
const readCurrentUser = () => {
  try {
    const stored = JSON.parse(localStorage.getItem('hospital-rmf-user') || 'null')
    if (stored?.id && stored?.name) return { id: stored.id, name: stored.name, avatarUrl: stored.avatarUrl || null }
  } catch { /* Fall back to the demo operator when auth storage is unavailable. */ }
  return { id: 'operator-01', name: 'Hospital Operator', avatarUrl: null }
}
const currentUser = ref(readCurrentUser())
const AUTH_STORAGE_KEYS = ['authToken', 'access_token', 'hospital-rmf-user']

const logout = async () => {
  AUTH_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key))
  authenticated.value = false
}

const updateProfile = async ({ name, avatarUrl = null }) => {
  const trimmedName = name?.trim()
  if (!trimmedName) throw new Error('Display name is required')
  const updated = { ...currentUser.value, name: trimmedName, avatarUrl }
  localStorage.setItem('hospital-rmf-user', JSON.stringify(updated))
  currentUser.value = updated
  return updated
}

export const authStore = Object.freeze({ authenticated: readonly(authenticated), currentUser: readonly(currentUser), updateProfile, logout })
