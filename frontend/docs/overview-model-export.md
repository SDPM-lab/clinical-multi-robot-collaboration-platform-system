# 更新總覽頁的 Blender 模型

把新的場景儲存或複製到 `blender/scenes/hospital_overview.blend`，然後在專案根目錄執行：

```bash
npm --prefix frontend run models:overview:update
```

指令使用 Blender 匯出可見的 `Scene` 物件，驗證 GLB，替換 `frontend/public/models/hospital_overview.glb`，依新檔案的 SHA-256 更新總覽模型網址，並執行前端建置。匯出失敗時不會替換目前的模型。開著的瀏覽器頁面需要重新整理，才會重新載入已在記憶體中的模型。

在目前的 WSL 環境，指令會自動尋找 Windows 上的 Blender 5.2 或更新版本。其他環境可設定 `BLENDER_BIN` 指向相容的 Blender 執行檔；未設定時會嘗試 `blender`。這個指令只更新總覽頁模型；`models:update` 是一樓即時地圖的另一條流程。
