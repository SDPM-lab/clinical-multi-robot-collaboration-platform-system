import { expect, it } from 'vitest'
import { webglProfile } from '@/three/webglProfile.js'
it('keeps Retina resolution on Safari while disabling multisampling', () => {
  expect(webglProfile('Mozilla/5.0 AppleWebKit/605.1.15 Version/26.6 Safari/605.1.15')).toMatchObject({antialias:false,powerPreference:'default',maxPixelRatio:2})
  expect(webglProfile('Mozilla/5.0 AppleWebKit/537.36 Chrome/140 Safari/537.36')).toMatchObject({antialias:true,powerPreference:'high-performance',maxPixelRatio:2})
})
