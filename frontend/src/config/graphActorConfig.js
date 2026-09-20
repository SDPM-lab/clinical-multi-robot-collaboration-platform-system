import { NAVIGATION_ASSETS } from '@/config/sceneAssets.js'

export const graphActorConfig = Object.freeze({
  graphUrl: NAVIGATION_ASSETS.graph1,
  graphIndex: 1,
  actorCount: 5,
  seeds: Object.freeze([101, 202, 303, 404, 505]),
  animationOffsets: Object.freeze([0, 0.7, 1.4, 2.1, 2.8]),
  walkSpeed: Object.freeze([0.45, 0.7]),
  idleDuration: Object.freeze([1.5, 5]),
  minActorDistance: 0.75,
})
