<script setup>
import MediSyncBrand from '@/components/MediSyncBrand.vue'
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, LoaderCircle, ArrowRight, Languages } from '@lucide/vue'
import { authStore } from '@/stores/authStore.js'
import { locale, setLocale, t } from '@/i18n/index.js'

const route = useRoute()
const router = useRouter()
const isDevelopment = import.meta.env.DEV
const mode = ref('login')
const registering = computed(() => mode.value === 'register')
const form = reactive({ name: '', email: '', password: '', confirmation: '', rememberMe: false })
const passwordVisible = ref(false)
const submitting = ref(false)
const errorCode = ref('')
const knownErrors = new Set(['invalid_credentials', 'email_exists', 'invalid_name', 'invalid_input', 'connection_error', 'server_error', 'rate_limited', 'session_expired', 'password_short', 'password_mismatch'])
const errorMessage = computed(() => errorCode.value ? t(`auth.errors.${knownErrors.has(errorCode.value) ? errorCode.value : 'server_error'}`) : '')
const navigateAfterSignIn = async () => {
  form.password = ''
  form.confirmation = ''
  const destination = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  await router.replace(destination.startsWith('/') && !destination.startsWith('//') && !destination.includes('\\') && !destination.startsWith('/login') ? destination : '/')
}
const changeMode = value => {
  if (submitting.value || mode.value === value) return
  mode.value = value
  errorCode.value = ''
  form.password = ''
  form.confirmation = ''
  passwordVisible.value = false
}
const submit = async () => {
  if (submitting.value) return
  errorCode.value = ''
  if (registering.value && form.name.trim().length < 2) { errorCode.value = 'invalid_name'; return }
  if (registering.value && form.password.length < 6) { errorCode.value = 'password_short'; return }
  if (registering.value && form.password !== form.confirmation) { errorCode.value = 'password_mismatch'; return }
  submitting.value = true
  try {
    if (registering.value) await authStore.register({ name: form.name.trim(), email: form.email.trim(), password: form.password })
    else await authStore.login({ email: form.email.trim(), password: form.password, rememberMe: form.rememberMe })
    await navigateAfterSignIn()
  } catch (error) { errorCode.value = error.code || 'server_error' }
  finally { submitting.value = false }
}
const submitDevelopmentLogin = async () => {
  if (submitting.value) return
  errorCode.value = ''
  submitting.value = true
  try {
    await authStore.loginAsDevelopmentUser()
    await navigateAfterSignIn()
  } catch (error) { errorCode.value = error.code || 'server_error' }
  finally { submitting.value = false }
}
</script>

<template>
  <main class="login-view">
    <div class="auth-decoration" aria-hidden="true"><span v-for="n in 6" :key="n" class="auth-cube"><i></i><b></b></span></div>
    <button class="auth-language" type="button" :aria-label="t('user.language')" @click="setLocale(locale === 'en' ? 'zh-TW' : 'en')"><Languages :size="16" />{{ locale === 'en' ? '繁體中文' : 'English' }}</button>
    <section class="auth-card" aria-labelledby="auth-title">
      <div class="auth-brand"><MediSyncBrand /></div>
      <h1 id="auth-title">{{ t(registering ? 'auth.registerTitle' : 'auth.loginTitle') }}</h1>
      <p class="auth-subtitle">{{ t(registering ? 'auth.registerSubtitle' : 'auth.loginSubtitle') }}</p>
      <div class="auth-tabs" role="group" :aria-label="t('auth.mode')">
        <button type="button" :aria-pressed="!registering" :disabled="submitting" @click="changeMode('login')">{{ t('auth.login') }}</button>
        <button type="button" :aria-pressed="registering" :disabled="submitting" @click="changeMode('register')">{{ t('auth.register') }}</button>
      </div>
      <button v-if="isDevelopment && !registering" class="auth-dev-login" type="button" :disabled="submitting" @click="submitDevelopmentLogin">{{ t('auth.devLogin') }}</button>
      <form @submit.prevent="submit" :aria-busy="submitting">
        <fieldset :disabled="submitting">
          <label v-if="registering" for="auth-name">{{ t('auth.name') }}<span aria-hidden="true"> *</span>
            <input id="auth-name" v-model="form.name" name="name" autocomplete="name" required minlength="2" maxlength="40" :placeholder="t('auth.namePlaceholder')">
          </label>
          <label for="auth-email">{{ t('auth.email') }}<span aria-hidden="true"> *</span>
            <input id="auth-email" v-model="form.email" name="email" type="email" inputmode="email" autocomplete="username" required maxlength="254" placeholder="name@hospital.org" autocapitalize="none" spellcheck="false">
          </label>
          <label for="auth-password">{{ t('auth.password') }}<span aria-hidden="true"> *</span></label>
          <div class="auth-password">
            <input id="auth-password" v-model="form.password" name="password" :type="passwordVisible ? 'text' : 'password'" :autocomplete="registering ? 'new-password' : 'current-password'" required :minlength="registering ? 6 : undefined" maxlength="128" :aria-describedby="registering ? 'password-hint' : undefined" :placeholder="t('auth.passwordPlaceholder')">
            <button type="button" :aria-label="t(passwordVisible ? 'auth.hidePassword' : 'auth.showPassword')" :aria-pressed="passwordVisible" @click="passwordVisible = !passwordVisible"><EyeOff v-if="passwordVisible" :size="18" /><Eye v-else :size="18" /></button>
          </div>
          <small v-if="registering" id="password-hint">{{ t('auth.passwordHint') }}</small>
          <label v-if="registering" for="auth-confirmation">{{ t('auth.confirmPassword') }}<span aria-hidden="true"> *</span>
            <input id="auth-confirmation" v-model="form.confirmation" name="confirmation" :type="passwordVisible ? 'text' : 'password'" autocomplete="new-password" required minlength="6" maxlength="128" :placeholder="t('auth.confirmPlaceholder')">
          </label>
          <label v-if="!registering" class="auth-remember"><input v-model="form.rememberMe" name="rememberMe" type="checkbox">{{ t('auth.rememberMe') }}</label>
          <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
          <button class="auth-submit" type="submit"><LoaderCircle v-if="submitting" class="auth-spinner" :size="18" /><span>{{ t(submitting ? 'auth.working' : registering ? 'auth.registerAction' : 'auth.loginAction') }}</span><ArrowRight v-if="!submitting" :size="17" /></button>
        </fieldset>
      </form>
      <p class="auth-switch">{{ t(registering ? 'auth.haveAccount' : 'auth.noAccount') }} <button type="button" :disabled="submitting" @click="changeMode(registering ? 'login' : 'register')">{{ t(registering ? 'auth.login' : 'auth.register') }}</button></p>
    </section>
    <p class="auth-footer">{{ t('auth.footer') }}</p>
  </main>
</template>

<style scoped>
.login-view{position:relative;box-sizing:border-box;display:flex;min-height:100dvh;flex-direction:column;align-items:center;justify-content:center;padding:76px 20px 30px;background:radial-gradient(ellipse at 12% 12%,#e3ecec88,transparent 46%),radial-gradient(ellipse at 85% 83%,#ffe5c95e,transparent 38%),#f4f6f5;color:#343a37}
.auth-language{z-index:2;position:absolute;top:25px;right:30px;display:flex;align-items:center;gap:8px;padding:9px 12px;border:1px solid #ffffffcc;border-radius:10px;background:#ffffff8c;color:#65716c;font:inherit;font-size:12px;cursor:pointer}
.auth-card{position:relative;z-index:1;box-sizing:border-box;width:min(440px,100%);padding:35px 38px 29px;background:#ffffffcf;border:1px solid #fff;border-radius:24px;box-shadow:0 20px 65px #3240380d,0 2px 8px #32403804;backdrop-filter:blur(18px)}
.auth-brand{display:flex;margin-bottom:25px;--medisync-size:1.875rem}
h1{margin:0 0 8px;font-size:28px;line-height:1.3;letter-spacing:-.7px}.auth-subtitle{margin:0 0 25px;font-size:13px;line-height:1.7;color:#7b837e}
.auth-tabs{display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:4px;margin-bottom:25px;background:#eef0ee;border-radius:11px}.auth-tabs button{min-height:37px;border:0;border-radius:8px;background:transparent;color:#818881;font:inherit;font-size:13px;cursor:pointer}.auth-tabs button[aria-pressed=true]{background:#fff;color:#b76132;box-shadow:0 2px 8px #36423a0b}
.auth-dev-login{width:100%;min-height:38px;margin:-12px 0 16px;border:1px dashed #e2a47e;border-radius:9px;background:#fff8f2;color:#a9582f;font:inherit;font-size:12px;font-weight:600;cursor:pointer}.auth-dev-login:disabled{opacity:.55;cursor:wait}
fieldset{display:grid;gap:9px;margin:0;padding:0;border:0;min-width:0}label{font-size:12px;font-weight:600;color:#59635d}label>span{color:#db8254}label:not(.auth-remember)>input{margin-top:8px}input:not([type=checkbox]){box-sizing:border-box;width:100%;min-height:45px;padding:11px 13px;border:1px solid #dfe4df;border-radius:10px;background:#ffffffb0;color:#354039;font:inherit;font-size:14px;outline:none;transition:border-color .15s,box-shadow .15s}input::placeholder{color:#a6ada8;font-size:12px}input:not([type=checkbox]):focus{border-color:#f3a271;box-shadow:0 0 0 3px #ffad7d22}fieldset>label:not(:first-child){margin-top:6px}.auth-password{position:relative;display:flex}.auth-password input{padding-right:47px}.auth-password button{position:absolute;right:5px;top:5px;display:grid;place-items:center;width:35px;height:35px;border:0;border-radius:8px;background:transparent;color:#8a938b;cursor:pointer}.auth-password button:hover{background:#fff1e7;color:#b76c43}small{color:#92998f;font-size:11px;line-height:1.5}.auth-remember{display:flex;align-items:center;gap:8px;font-weight:400;cursor:pointer}.auth-remember input{width:15px;height:15px;margin:0;accent-color:#ef9b6a}
.auth-submit{display:flex;align-items:center;justify-content:center;gap:10px;min-height:46px;margin-top:13px;padding:10px 15px;border:0;border-radius:11px;color:#633d29;background:#ffad7b;font:inherit;font-size:14px;font-weight:600;cursor:pointer;box-shadow:0 5px 15px #e48d4f16;transition:background .15s}.auth-submit:hover{background:#ff9d62}.auth-error{margin:7px 0 0;padding:10px 12px;border:1px solid #f3cfca;border-radius:9px;color:#ad5d57;background:#fff1ef;font-size:12px;line-height:1.6}.auth-switch{margin:23px 0 0;text-align:center;color:#8a928b;font-size:12px}.auth-switch button{padding:0;border:0;background:transparent;color:#c47d50;font:inherit;font-weight:600;cursor:pointer}.auth-footer{margin:20px 0 0;color:#9ca59c;font-size:11px;letter-spacing:.02em}button:focus-visible{outline:2px solid #ec9d70;outline-offset:3px}button:disabled,fieldset:disabled{opacity:.65;cursor:wait}.auth-spinner{animation:auth-spin 1s linear infinite}@keyframes auth-spin{to{transform:rotate(360deg)}}@media(max-width:480px){.auth-card{padding:28px 24px;border-radius:20px}.auth-language{top:19px;right:20px}h1{font-size:25px}}@media(prefers-reduced-motion:reduce){.auth-spinner{animation:none}*{transition:none!important}}

.auth-decoration{position:absolute;inset:0;overflow:hidden;pointer-events:none}.auth-cube{position:absolute;width:110px;height:110px;border-radius:14px;background:linear-gradient(135deg,#f5c9a5,#db9e7f);box-shadow:25px 35px 45px #6e7e7520;transform:rotate(-22deg) skew(8deg,8deg);opacity:.65}.auth-cube i,.auth-cube b{position:absolute;display:block;border-radius:inherit}.auth-cube i{inset:0;background:linear-gradient(145deg,#ffffff88,transparent)}.auth-cube b{top:100%;left:0;width:100%;height:22px;background:#bd907b;transform:skewX(40deg);transform-origin:top}.auth-cube:nth-child(1){left:calc(50% - 360px);top:20%;width:90px;height:90px}.auth-cube:nth-child(2){left:calc(50% + 200px);top:15%;width:160px;height:160px;background:linear-gradient(135deg,#d3e2da,#99b0a3);transform:rotate(24deg) skew(-8deg,-8deg)}.auth-cube:nth-child(3){left:calc(50% - 380px);top:62%;width:135px;height:135px;background:linear-gradient(135deg,#d3e2da,#99b0a3)}.auth-cube:nth-child(4){left:calc(50% + 240px);top:65%;width:85px;height:85px}.auth-cube:nth-child(5){left:calc(50% - 240px);top:9%;width:36px;height:36px;opacity:.45}.auth-cube:nth-child(6){left:calc(50% + 160px);bottom:8%;width:40px;height:40px;opacity:.45}.auth-footer{position:relative}.login-view button{transition:background .18s,color .18s,box-shadow .18s,transform .18s}.login-view button:hover:enabled{box-shadow:0 5px 14px #b87f4920}.auth-submit:hover:enabled,.auth-dev-login:hover:enabled{transform:translateY(-2px)}.auth-language:hover:enabled,.auth-tabs button:hover:enabled{background:#fff1e6;color:#b66b41}.auth-switch button:hover:enabled{color:#a35e34;text-decoration:underline}.auth-submit:active:enabled{transform:translateY(0)}@media(max-width:650px){.auth-cube{opacity:.25}.auth-cube:nth-child(2){left:75%;top:8%}.auth-cube:nth-child(3){left:-50px}}
</style>
