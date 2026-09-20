<template>
  <div class="app-ambient-background" aria-hidden="true">
    <span class="ambient-beam ambient-beam--dawn"></span>
    <span class="ambient-beam ambient-beam--middle"></span>
    <span class="ambient-beam ambient-beam--reflection"></span>
    <span class="ambient-ripple ambient-ripple--pearl"></span>
    <span class="ambient-ripple ambient-ripple--gold"></span>
    <span class="ambient-sparkles"></span>
  </div>
</template>

<style scoped>
.app-ambient-background{position:fixed;z-index:0;inset:0;overflow:hidden;background:linear-gradient(180deg,rgba(255,247,232,.13),transparent 44%),linear-gradient(128deg,rgba(201,107,53,.065),transparent 35%,rgba(213,173,78,.04) 54%,transparent 68%,rgba(211,137,82,.065));pointer-events:none}
.ambient-beam{position:absolute;display:block;inset:-18%;will-change:transform,opacity;animation:ambient-light-shimmer 16s ease-in-out infinite alternate}
.ambient-beam--dawn{background:linear-gradient(116deg,transparent 23%,rgba(255,224,150,.03) 32%,rgba(255,235,185,.14) 45%,rgba(255,248,220,.10) 51%,rgba(232,200,150,.03) 59%,transparent 70%);transform:translate3d(-1.5%,-2%,0)}
.ambient-beam--middle{background:linear-gradient(146deg,transparent 30%,rgba(224,169,126,.045) 40%,rgba(255,245,225,.13) 51%,rgba(236,196,153,.06) 61%,transparent 72%);opacity:.8;animation-delay:-5s}
.ambient-beam--reflection{inset:8% -22% -28% 12%;background:linear-gradient(128deg,transparent 42%,rgba(239,219,184,.045) 52%,rgba(239,191,147,.12) 68%,rgba(214,139,84,.06) 76%,transparent 91%);animation-delay:-9s}
.ambient-ripple{position:absolute;display:block;width:62vw;height:48vw;min-width:640px;min-height:480px;border-radius:50%;filter:blur(34px);mix-blend-mode:screen;will-change:transform,opacity;animation:ambient-water-glint 23s ease-in-out infinite}
.ambient-ripple--pearl{top:-28%;left:9%;background:radial-gradient(ellipse at center,rgba(255,248,220,.32) 0,rgba(255,235,185,.14) 24%,rgba(242,210,160,.045) 43%,transparent 68%);opacity:.52;animation-delay:-7s}
.ambient-ripple--gold{right:-20%;bottom:-36%;background:radial-gradient(ellipse at center,rgba(255,230,140,.18) 0,rgba(255,210,100,.09) 25%,rgba(246,180,100,.035) 47%,transparent 70%);opacity:.48;animation-duration:29s;animation-delay:-17s}
.ambient-sparkles{position:absolute;inset:-12%;display:block;background:radial-gradient(circle at 14% 34%,rgba(255,249,218,.38) 0 1.2px,transparent 5px),radial-gradient(circle at 31% 71%,rgba(255,255,240,.3) 0 1px,transparent 6px),radial-gradient(circle at 54% 24%,rgba(255,237,174,.26) 0 1.5px,transparent 7px),radial-gradient(circle at 73% 58%,rgba(255,255,242,.36) 0 1.2px,transparent 5px),radial-gradient(circle at 89% 18%,rgba(255,229,154,.28) 0 1px,transparent 6px),radial-gradient(circle at 22% 12%,rgba(255,250,220,.32) 0 1px,transparent 5px),radial-gradient(circle at 45% 68%,rgba(255,245,200,.26) 0 1.5px,transparent 7px),radial-gradient(circle at 67% 38%,rgba(255,252,230,.34) 0 1px,transparent 5px),radial-gradient(circle at 83% 74%,rgba(255,240,180,.24) 0 1.2px,transparent 6px),radial-gradient(circle at 38% 45%,rgba(255,255,235,.28) 0 1px,transparent 5px),radial-gradient(circle at 9% 55%,rgba(255,248,210,.22) 0 1px,transparent 4px),radial-gradient(circle at 61% 82%,rgba(255,235,170,.22) 0 1.5px,transparent 7px),radial-gradient(circle at 76% 8%,rgba(255,253,230,.3) 0 1px,transparent 4px),radial-gradient(circle at 4% 82%,rgba(255,242,190,.2) 0 1.2px,transparent 6px);filter:blur(.2px);mix-blend-mode:screen;opacity:.52;transform-origin:center;animation:ambient-sparkle-drift 17s ease-in-out infinite alternate}
:global([data-theme='dark']) .app-ambient-background{background:linear-gradient(180deg,rgba(98,64,38,.075),transparent 45%),linear-gradient(128deg,rgba(201,107,53,.095),transparent 35%,rgba(184,132,78,.045) 54%,transparent 68%,rgba(176,91,48,.09))}
:global([data-theme='dark']) .ambient-beam--dawn{background:linear-gradient(116deg,transparent 23%,rgba(180,99,54,.025) 32%,rgba(218,139,84,.16) 45%,rgba(241,205,151,.1) 51%,rgba(151,100,62,.035) 59%,transparent 70%)}
:global([data-theme='dark']) .ambient-beam--middle{background:linear-gradient(146deg,transparent 30%,rgba(155,89,52,.045) 40%,rgba(202,151,94,.11) 51%,rgba(167,103,61,.06) 61%,transparent 72%)}
:global([data-theme='dark']) .ambient-beam--reflection{background:linear-gradient(128deg,transparent 42%,rgba(161,116,69,.045) 52%,rgba(197,112,63,.13) 68%,rgba(145,73,39,.07) 76%,transparent 91%)}
:global([data-theme='dark']) .ambient-ripple{mix-blend-mode:screen;opacity:.16}
:global([data-theme='dark']) .ambient-sparkles{opacity:.12}
@keyframes ambient-light-shimmer{from{opacity:.72;transform:translate3d(-1.5%,-1%,0)}to{opacity:1;transform:translate3d(1.25%,1%,0)}}
@keyframes ambient-water-glint{0%,100%{transform:translate3d(-7%,-3%,0) scale(.96);opacity:.34}31%{transform:translate3d(7%,4%,0) scale(1.04);opacity:.62}67%{transform:translate3d(-2%,9%,0) scale(1);opacity:.46}}
@keyframes ambient-sparkle-drift{0%{transform:translate3d(-1%,1%,0) scale(.98);opacity:.2}37%{opacity:.5}100%{transform:translate3d(2%,-2%,0) scale(1.03);opacity:.32}}
@media(prefers-reduced-motion:reduce){.ambient-beam,.ambient-ripple,.ambient-sparkles{animation:none}}
</style>
