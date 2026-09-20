# 機器人狀態固定 HMI 驗收

1. 左側控制面板採 `top:24px; bottom:24px; left:24px`（頁面實際 top 88px），寬度 `clamp(260px,19vw,310px)`，背景 `rgba(247,243,236,.92)`。1536×768 實測為 291.83×656px；1920×1080 為 310×968px。
2. 電量與溫度已整合到左側最上方，使用低彩度陶土色及灰綠色短型儀表，保留 Count-up、能源環與溫度計。
3. 左側已加入搜尋欄與 Robot 01／02／03 清單，顯示名稱、ID、狀態圓點、狀態及電量。選中項以灰綠左側 2px 內陰影顯示，沒有橘色邊框。
4. 中央上一台／下一台箭頭已移除，切換由左側清單完成。
5. 原本巨大標題已改為 24px 的單行舞台狀態，顯示名稱、狀態、型號及位置。
6. 舞台狀態 CSS 使用左右面板實際寬度計算可視中心；Three.js 讀取兩側面板的 DOM bounds 建立同一個 safe rect，Camera Target、ViewOffset、模型及標題使用相同構圖中心。
7. 右側 Inspector 固定在頁面 top 72px、right 0、bottom 0，寬度 `clamp(370px,27vw,440px)`。1536 實測 414.72px，1920 實測 440px。淺色背景 `.93`、深色背景 `.93`。
8. 已移除垂直 Icon Bar、關閉按鈕、縮小狀態與收合流程。Inspector 只讓內容區捲動，頁面本身 `overflow:hidden`。
9. 分類固定為「概況｜結構｜移動｜診斷」，預設概況；已移除重複的能源與溫度分類。
10. 移動頁使用半圓速度表、最大速度標示及最近 30 秒區域。目前 Store 沒有即時速度與時間序列，因此顯示明確 Empty State，沒有產生假指針或 Sparkline。
11. 一般零件選取不再修改材質主色或 Emissive。其他 Mesh 僅向中性灰綠混合 10%，原始 Texture、Opacity 與材質主色保持可恢復。
12. 選取視覺使用同一 Renderer 上的 Three.js `EffectComposer + OutlinePass`：進場、Hover、Selected 外輪廓、Selected 內輪廓四個 pass。Selected 在 520ms 內做一次輪廓強度掃過，不持續閃爍。
13. 色碼：Hover `#aab2ae`；Selected Light `#71817b`；Selected Dark `#c2ccc7`；Dark Glow `#e0e7e3`；Warning `#c96561`。Warning 只在傳入已驗證過熱狀態時使用，現有 demo 溫度不會讓 Mesh 出現紅色警告輪廓。
14. 首次時間軸：0–900ms 旋轉；750–1450ms 八個 Mesh 展開；1200–1750ms 依序描繪結構輪廓；1450–2050ms 顯示五個主要標註；1900–2800ms 組裝；2450–3000ms 面板淡入；3000ms 啟用 OrbitControls 與 Raycaster。切換機器人不重播首次組裝，也不重新載入 GLB。
15. Focus 使用整機 Box3 與 part Box3，target 只向零件移動 18%，距離仍受整機輪廓與 55% 以上上下文約束。底盤小構件實測 Focus 後整機仍完整可辨識。
16. Canvas 始終鋪滿 Navbar 下方內容區。1536 實測 1536×704px、1920 實測 1920×1016px；切換頁籤、零件及面板內容前後 bounding rect 完全相同。整機高度約占可視舞台 70%。Exploded 使用預先計算 bounds 與 25% padding。
17. 修改檔案：`RobotFleetView.vue`、`RobotViewport.vue`、`RobotStructureController.js`、`robotComponentRules.js`、`robotHmi.css`、`robotFleetView.test.js`、`robotStructure.test.js` 與本文件。
18. `npm run build --prefix frontend` 通過；21 個測試檔、82 項測試全部通過。保留既有單一 bundle 大於 500kB 的建置提示。
19. 清理已檢查：四個 OutlinePass、RenderPass、EffectComposer render targets、Renderer、私有 Material／Geometry／Texture、RAF、OrbitControls、ResizeObserver、MutationObserver、Raycaster pointer listeners 均在卸載時釋放。Chromium 離頁後 Canvas 數量為 0，console/page error 為空。
