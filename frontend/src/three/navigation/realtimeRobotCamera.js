import * as THREE from 'three'

export const REALTIME_CAMERA_MODES = Object.freeze(['global', 'thirdPerson', 'firstPerson', 'localFollow'])

export const getRobotCameraPose = (mode, position, forward) => {
  if (!position?.isVector3 || !forward?.isVector3 || !REALTIME_CAMERA_MODES.includes(mode) || mode === 'global') return null
  const heading = forward.clone().setY(0)
  if (heading.lengthSq() < 0.000001) return null
  heading.normalize()
  if (mode === 'firstPerson') {
    const cameraPosition = position.clone().addScaledVector(heading, 0.38).add(new THREE.Vector3(0, 1.02, 0))
    return {
      position: cameraPosition,
      target: cameraPosition.clone().addScaledVector(heading, 4).add(new THREE.Vector3(0, -0.08, 0)),
    }
  }
  if (mode === 'localFollow') {
    return {
      position: position.clone().add(new THREE.Vector3(0, 6.4, 4.8)),
      target: position.clone().add(new THREE.Vector3(0, 0.2, 0)),
    }
  }
  return {
    position: position.clone().addScaledVector(heading, -2.4).add(new THREE.Vector3(0, 1.75, 0)),
    target: position.clone().addScaledVector(heading, 1.45).add(new THREE.Vector3(0, 0.45, 0)),
  }
}
