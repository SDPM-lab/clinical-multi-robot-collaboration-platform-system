import { expect,it } from 'vitest'
import {getRobotVisualTheme} from '@/config/robotVisualThemes.js'
import {robotRouteColors,routeLayerY} from '@/data/demoActiveRoutes.js'
it('gives all seven registered robot IDs distinct consistent route and card colors',()=>{
 const ids=['robot-a','robot-b',...Array.from({length:5},(_,i)=>`robot-hospital_robot_${i+3}`)]
 expect(new Set(ids.map(id=>robotRouteColors[id].main)).size).toBe(7)
 expect(new Set(ids.map(id=>routeLayerY[id])).size).toBe(7)
 ids.forEach((id,i)=>{
  expect(robotRouteColors[id].main).toBe(getRobotVisualTheme(id).mainHex)
  expect(getRobotVisualTheme(id).main).toBe(getRobotVisualTheme(`R0${i+1}`).main)
 })
})
