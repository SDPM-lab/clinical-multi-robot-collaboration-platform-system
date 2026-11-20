// Keep Retina resolution while avoiding multisampled render targets on Safari.
export function webglProfile(userAgent = globalThis.navigator?.userAgent || '') {
  const safari = /AppleWebKit/.test(userAgent) && /Safari/.test(userAgent) && !/Chrome|Chromium|Edg|OPR|Android/.test(userAgent)
  return { antialias: !safari, powerPreference: safari ? 'default' : 'high-performance', maxPixelRatio: 2 }
}
