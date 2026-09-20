export const rmfMapTransform = Object.freeze({
  scale: 1,
  rotation: 0,
  offsetX: -19.860754013061523,
  offsetZ: -13.426342964172363,
  invertX: false,
  invertY: true,
  floorY: 0,
})

export const rmfToThree = (point, transform = rmfMapTransform) => {
  const sourceX = (transform.invertX ? -point.x : point.x) * transform.scale
  const sourceZ = (transform.invertY ? -point.y : point.y) * transform.scale
  const cos = Math.cos(transform.rotation)
  const sin = Math.sin(transform.rotation)

  return {
    x: sourceX * cos - sourceZ * sin + transform.offsetX,
    y: transform.floorY,
    z: sourceX * sin + sourceZ * cos + transform.offsetZ,
  }
}
