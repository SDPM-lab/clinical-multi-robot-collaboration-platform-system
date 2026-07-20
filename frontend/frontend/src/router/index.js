import { createRouter, createWebHistory } from 'vue-router'

import DispatchView from '@/components/views/DispatchView.vue'
import RobotsStatusView from '@/components/views/RobotsStatusView.vue'
import ScheduleGanttView from '@/components/views/ScheduleGanttView.vue'
import MapView from '@/components/views/MapView.vue'
import AlertsView from '@/components/views/AlertsView.vue'
import RobotDetailView from '@/components/views/RobotDetailView.vue'
import RobotTaskDetailView from '@/components/views/RobotTaskDetailView.vue'

const routes = [
  { path: '/', redirect: '/dispatch' },
  { path: '/dispatch', name: 'dispatch', component: DispatchView },
  { path: '/robots', name: 'robots', component: RobotsStatusView },
  { path: '/robots/:id', name: 'robot-detail', component: RobotDetailView },
  { path: '/robots/:id/tasks/:taskId', name: 'robot-task-detail', component: RobotTaskDetailView },
  { path: '/schedule', name: 'schedule', component: ScheduleGanttView },
  { path: '/map', name: 'map', component: MapView },
  { path: '/alerts', name: 'alerts', component: AlertsView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
