# MediSync｜Live Map & Robot Tracking

`LiveMapTrackingPrototype` · 14 秒 · 1920 × 1080 · 30 fps · 420 幀

| 片段 | 時間與幀 | 鏡頭與 Shotcraft 對應 |
|---|---|---|
| A | 0–2 秒，0–59 | `crane-rise-reveal` 改成從正式 Live Map 的全域高角度做小幅推進，保留室內走廊與區域。 |
| B | 2–5 秒，60–149 | `scanline-annotate-focus` 借用順序導視。先標出 Pharmacy、Ward A，再由產品的逐段路線物件揭露參考線。 |
| C | 5–9 秒，150–269 | 從全域位置過渡到第三人稱；借 `depth-layer-moves` 的近遠層次，以同一套 WebGL 透視呈現機器人及走廊。 |
| D | 9–12 秒，270–359 | 跟隨鏡頭拉回全域，恢復原始 Active Tasks。影片層提示 M01 的模擬任務進度，抵達 Ward A 才完成最後節點。 |
| E | 12–14 秒，360–419 | 從地圖同一個 M01 拉出圖示與標頭。以 `circle-match-iris` 的共用錨點概念設計片尾，停在完整追蹤畫面。 |

## 實際產品與模擬資料

- 原始 Vue 頁面為 `frontend/src/components/scene/HospitalScene.vue`，使用 Three.js 渲染 F1，房間標籤與 Active Tasks 來自原生 DOM。輸出保留原始 Navbar。Phase 4 的位置與進度字卡為影片圖層。
- 場景來自 `frontend/public/models/hospital_L1_environment.glb`，跟拍角色為 `frontend/public/models/AGIBOT_A2D.glb`。沿用原頁面材質、實際 M01 資產載入與停駐臂姿。擷取環境關閉陰影計算與其他角色的顯示以確保離線渲染；頁面的檔案與資產本體未改動。
- 場景沿用 Phase 2、3 的 T0002（film-task-t0002）、Medication Delivery、High、Pharmacy → Ward A、M01。M01 由 API 身分 robot-hospital_robot_3 映射為產品顯示碼。
- `buildLiveMapRoutes` 使用正式 `rmf-navigation.json` 的有向 lanes 搜尋路徑。這筆路線的節點是 v34 → v33 → v3 → v1 → v0 → v15 → v49 → v20 → v14 → v13 → v23 → v22 → v44，約 48.26 場景單位。顯示的是參考路線，任務速度為影片壓縮後的模擬演示。
- 影片以已指派的模擬任務開始。第 139 幀之後推進，至第 340 幀時進度為 1 並驗證 M01 與 Ward A 路線端點一致。擷取只攔截瀏覽器請求並回傳本機 Demo；關閉外部 WebSocket、阻擋未列出的 API 及寫入，未呼叫正式後端或控制機器人。
- 正式相機支援 Global、Third person、First person、Local follow，第三人稱原始設定向後 2.4、向上 1.75、目標沿前方 1.45。此片使用同一姿勢函式並增加 0.5 高度以留出模型空間，按 30 fps 固定時間軸做指數阻尼。影片捨棄第一人稱插鏡，整段第三人稱皆為虛擬相機。
- 擷取程序為 `scripts/capture-live-map-tracking.mjs`，以正式頁面在隔離 DOM 中設定相機和模擬進度。離線 WebGL 樣本由 `scripts/assemble-live-map-tracking.py` 以光流補間至 30 fps，段落切點保留實際擷取幀。擷取素材為 1280×720，1080p MP4 疊加原生解析度字卡與繁中字幕。
