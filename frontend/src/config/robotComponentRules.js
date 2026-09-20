// Exact GLTFLoader object names. Physical descriptions do not imply sensor functions.
export const robotComponents = [
  {id:'shell', name:'Layer_01001', label:'外殼', note:'整體外殼與底座環，共用一個 Mesh'},
  {id:'display', name:'Layer_02001', label:'上方前側面板', note:'前側上方面板；電子功能尚未確認'},
  {id:'frontPanel', name:'Layer_02002', label:'中央前側面板', note:'中央長形面板；電子功能尚未確認'},
  {id:'chassis', name:'Layer_03001', label:'底盤前側構件', note:'底部前側獨立構件'},
  {id:'baseCenter', name:'Layer_03002', label:'底盤中央構件', note:'底部中央獨立構件，非已確認馬達'},
  {id:'baseRear', name:'Layer_03003', label:'底盤後側構件', note:'底部後側獨立構件'},
  {id:'lowerFront', name:'Default002', label:'下部前側構件', note:'實際可分離 Mesh；功能尚未確認'},
  {id:'lowerInner', name:'Default003', label:'下部內側構件', note:'實際可分離 Mesh；功能尚未確認'},
]
export const robotComponentRules = Object.fromEntries(robotComponents.map(p => [p.id, [p.name]]))
Object.assign(robotComponentRules, {controller:[],battery:[],leftMotor:[],rightMotor:[],lidar:[]})
export const componentIdForMesh = name => robotComponents.find(p => p.name === name)?.id || null
// Direction fallback for the shell whose center nearly coincides with the whole model.
export const robotExplodedOffsets = {Layer_01001: [-1, .2, -.25]}
export const robotSubsystems = {
  enclosure: {label:'外殼區域', meshNames:['Layer_01001']},
  front: {label:'前側面板區域', meshNames:['Layer_02001','Layer_02002']},
  base: {label:'底盤區域', meshNames:['Layer_03001','Layer_03002','Layer_03003','Default002','Default003']},
}
export const primaryHotspots = ['shell','display','frontPanel','chassis','lowerInner']

export const componentSelectionPalette = Object.freeze({
  hover: 0xaab2ae,
  selectedLight: 0x71817b,
  selectedDark: 0xc2ccc7,
  selectedGlowLight: 0xaebbb5,
  selectedGlowDark: 0xe0e7e3,
  warning: 0xc96561,
})
