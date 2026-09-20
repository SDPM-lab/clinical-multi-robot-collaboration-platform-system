<template>
  <main class="login-view">
    <section>
      <strong>Hospital RMF</strong>
      <h1>已登出</h1>
      <p>目前專案尚未連接正式身分驗證服務。</p>
      <RouterLink to="/">返回系統</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.login-view { display:grid; min-height:100dvh; place-items:center; color:var(--text-primary); background:transparent; }
section { width:min(320px,calc(100vw - 40px)); padding:28px; text-align:center; background:rgba(255,255,255,.72); border:1px solid rgba(84,88,86,.13); border-radius:12px; box-shadow:0 14px 35px rgba(45,42,38,.09); }
strong { color:var(--accent-orange); font-size:13px; letter-spacing:.06em; }
h1 { margin:9px 0 7px; font-size:24px; }
p { margin:0 0 20px; color:#77716b; font-size:13px; }
a { display:inline-flex; padding:8px 14px; color:#fff; text-decoration:none; background:var(--accent-orange); border-radius:6px; }
</style>
