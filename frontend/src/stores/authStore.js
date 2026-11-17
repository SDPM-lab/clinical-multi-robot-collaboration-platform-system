import { notificationStore } from '@/stores/notificationStore.js'
import { readonly, ref } from 'vue'
import { authRequest, developmentLogin, jsonOptions, resetCsrf } from '@/services/sessionApi.js'

const emptyUser = () => ({ id: null, name: '', email: '', avatarUrl: null })
const authenticated = ref(false)
const currentUser = ref(emptyUser())
let initialized = false
let initialization = null

const setUser = user => { if (currentUser.value.id !== user?.id) notificationStore.clear(); currentUser.value = user || emptyUser(); authenticated.value = !!user }
window.addEventListener('auth:expired', () => setUser(null))

const initialize = async () => {
  if (initialized) return
  if (!initialization) initialization = (async () => {
    try { setUser(await authRequest('/me')) }
    catch { setUser(null) }
    finally { initialized = true; initialization = null }
  })()
  return initialization
}

const login = async credentials => {
  const user = await authRequest('/login', jsonOptions('POST', credentials))
  resetCsrf() // 登入後身分已改變，必須重新取得防偽權杖。
  setUser(user)
  initialized = true
  return user
}

const loginAsDevelopmentUser = async () => {
  const user = await developmentLogin()
  resetCsrf()
  setUser(user)
  initialized = true
  return user
}

const register = async fields => {
  const user = await authRequest('/register', jsonOptions('POST', fields))
  resetCsrf()
  setUser(user)
  initialized = true
  return user
}

const logout = async () => {
  try { await authRequest('/logout', { method: 'POST' }) }
  catch (error) { if (error.status !== 401) throw error }
  resetCsrf()
  setUser(null)
}

const updateProfile = async ({ name, avatarUrl = null }) => {
  const user = await authRequest('/profile', jsonOptions('PATCH', { name: name.trim(), avatarUrl }))
  setUser(user)
  return user
}

export const authStore = Object.freeze({ authenticated: readonly(authenticated), currentUser: readonly(currentUser),
  initialize, login, loginAsDevelopmentUser, register, updateProfile, logout })
