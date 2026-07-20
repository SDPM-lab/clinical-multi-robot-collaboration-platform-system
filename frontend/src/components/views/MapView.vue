<script setup lang="ts">
import { ref } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

defineProps<{
  robots: Array<Record<string, any>>
  rosBridgeUrl: string
  rosBridgeStatus: string
}>()

const emit = defineEmits<{
  reconnect: []
  'register-canvas': [el: HTMLCanvasElement | null]
}>()

const activeTab = ref('2d')

function statusKey(status: string) {
  if (status.startsWith('未連線')) return 'offline'
  if (status === '連線中...') return 'connecting'
  return 'online'
}

function robotStatusKey(s: string) {
  return s === '在線' ? 'online' : s === '忙碌' ? 'busy' : 'idle'
}

function onCanvasMounted(el: any) {
  emit('register-canvas', el)
}
</script>

<template>
  <div class="map-view">
    <aside class="anim-fade-in-left">
      <Card class="map-controls">
        <CardContent class="grid gap-4 p-4">
          <h2 class="font-bold">地圖控制</h2>

          <div class="flex gap-2 items-center p-3 rounded-lg border bg-muted">
            <span class="map-status__dot" :class="`map-status--${statusKey(rosBridgeStatus)}`"></span>
            <div>
              <strong class="block text-sm">{{ rosBridgeStatus }}</strong>
              <p class="text-muted-foreground text-sm mb-0">{{ rosBridgeUrl }}</p>
            </div>
          </div>

          <Button
            class="font-bold"
            :disabled="rosBridgeStatus === '連線中...'"
            @click="emit('reconnect')"
          >{{ rosBridgeStatus === '連線中...' ? '連線中…' : '重新連線' }}</Button>

          <section>
            <h3 class="font-bold text-sm border-b pb-2">機器人位置</h3>
            <ul class="list-none grid gap-2 mt-2 p-0">
              <li v-for="(robot, idx) in robots" :key="robot.id" class="flex items-center gap-2 p-2 rounded-lg border bg-muted anim-fade-in-up" :style="{ animationDelay: (idx * 0.07) + 's' }">
                <span class="position-dot" :class="`position-dot--${robotStatusKey(robot.status)}`"></span>
                <div>
                  <strong class="block text-sm">{{ robot.name }}</strong>
                  <span class="text-muted-foreground" style="font-size: 0.8rem;">{{ robot.location }}</span>
                </div>
              </li>
            </ul>
          </section>
        </CardContent>
      </Card>
    </aside>

    <section class="anim-fade-in-right anim-delay-1">
      <Card class="map-canvas-panel">
        <CardContent class="grid gap-3 p-4" style="grid-template-rows: auto 1fr;">
          <header class="flex justify-between items-center flex-wrap gap-2">
            <div>
              <h2 class="font-bold mb-0">即時地圖</h2>
              <p class="text-muted-foreground text-sm mb-0">ROS2 RViz 視圖 — 等待 rosbridge 整合</p>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <div class="flex rounded-lg border overflow-hidden">
                <Button
                  size="sm"
                  :variant="activeTab === '2d' ? 'default' : 'ghost'"
                  class="rounded-none"
                  @click="activeTab = '2d'"
                >2D 地圖</Button>
                <Button
                  size="sm"
                  :variant="activeTab === '3d' ? 'default' : 'ghost'"
                  class="rounded-none"
                  @click="activeTab = '3d'"
                >3D 地圖</Button>
              </div>
              <div class="flex rounded-lg border overflow-hidden">
                <Button size="sm" variant="ghost" class="rounded-none">縮小</Button>
                <Button size="sm" variant="ghost" class="rounded-none">置中</Button>
                <Button size="sm" variant="ghost" class="rounded-none">放大</Button>
              </div>
            </div>
          </header>

          <div v-show="activeTab === '2d'" class="map-canvas-wrap">
            <canvas :ref="onCanvasMounted" class="map-canvas" width="1200" height="800"></canvas>
            <div class="map-placeholder">
              <p class="map-placeholder__eyebrow">尚未連線到 ROS2</p>
              <p class="map-placeholder__title">2D 地圖將顯示在此區域</p>
              <ul class="map-placeholder__steps">
                <li>1. 啟動 ROS2 與 rosbridge_suite (<code>ros2 launch rosbridge_server rosbridge_websocket_launch.xml</code>)</li>
                <li>2. 安裝前端套件 <code>npm install roslib</code></li>
                <li>3. 在 composable mounted 時透過 <code>ROSLIB.Ros</code> 連線到 <code>{{ rosBridgeUrl }}</code></li>
                <li>4. 訂閱 <code>/map</code> 並將 OccupancyGrid 繪製到 canvas</li>
              </ul>
            </div>
          </div>

          <div v-show="activeTab === '3d'" class="map-canvas-wrap">
            <div class="map-placeholder">
              <p class="map-placeholder__eyebrow">尚未連線到 ROS2</p>
              <p class="map-placeholder__title">3D 地圖將顯示在此區域</p>
              <ul class="map-placeholder__steps">
                <li>1. 啟動 ROS2 與 rosbridge_suite</li>
                <li>2. 安裝 3D 渲染套件 <code>npm install three</code></li>
                <li>3. 透過 <code>ROSLIB.Ros</code> 連線並訂閱 3D 點雲與模型資料</li>
                <li>4. 使用 Three.js 繪製 3D 場景</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  </div>
</template>

<style scoped>
.map-view {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: stretch;
}

.map-status__dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.map-status--offline { background: #94a3b8; }
.map-status--connecting { background: #f59e0b; animation: pulse 1.2s ease-in-out infinite; }
.map-status--online { background: #10b981; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.position-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.position-dot--online { background: #10b981; }
.position-dot--busy { background: #f59e0b; }
.position-dot--idle { background: #94a3b8; }

.map-canvas-panel {
  min-height: 540px;
}

.map-canvas-wrap {
  position: relative;
  border-radius: var(--radius);
  overflow: hidden;
  background:
    linear-gradient(#0b1220 1px, transparent 1px) 0 0 / 24px 24px,
    linear-gradient(90deg, #0b1220 1px, transparent 1px) 0 0 / 24px 24px,
    radial-gradient(circle at center, #1e293b 0%, #0f172a 70%);
  border: 1px solid #1e293b;
  min-height: 480px;
}

.map-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.map-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 2rem;
  color: #cbd5e1;
  pointer-events: none;
}

.map-placeholder__eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  color: #fbbf24;
  font-weight: 700;
  margin: 0 0 0.3rem;
}

.map-placeholder__title {
  font-size: 1.3rem;
  font-weight: 700;
  margin: 0 0 1rem;
  color: #f8fafc;
}

.map-placeholder__steps {
  list-style: none;
  padding: 0;
  margin: 0;
  max-width: 560px;
  display: grid;
  gap: 0.45rem;
  text-align: left;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #e2e8f0;
}

.map-placeholder__steps code {
  background: rgba(59, 130, 246, 0.18);
  color: #93c5fd;
  padding: 0.1rem 0.45rem;
  border-radius: 0.35rem;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.85rem;
}

@media (max-width: 1024px) {
  .map-view {
    grid-template-columns: 1fr;
  }

  .map-canvas-wrap {
    min-height: 320px;
  }
}

@media (max-width: 768px) {
  .map-canvas-panel {
    min-height: 300px;
  }

  .map-canvas-wrap {
    min-height: 240px;
  }
}

@media (max-width: 480px) {
  .map-canvas-wrap {
    min-height: 200px;
  }
}
</style>
