# Blender 醫院場景

此目錄保存醫院一樓的 Blender 主場景，以及建立、同步和匯出場景所需的腳本。

## 目錄結構

```text
blender/
├── README.md
├── scenes/
│   └── floor_L1.blend
└── scripts/
    ├── export_hospital_l1_glb.py
    ├── furniture/
    ├── equipment/
    ├── characters/
    ├── robots/
    └── materials/
```

- `scenes/floor_L1.blend`：一樓唯一的 Blender 主檔。
- `scripts/furniture/`：家具與房間設施製作腳本。
- `scripts/equipment/`：醫療設備製作腳本。
- `scripts/characters/`：護理師與訪客製作腳本。
- `scripts/robots/`：Blender 機器人製作腳本。
- `scripts/materials/`：只調整既有材質的工具。
- `scripts/export_hospital_l1_glb.py`：將一樓主場景匯出成前端環境流程使用的 GLB。

## 開啟主場景

在專案根目錄執行：

```bash
blender blender/scenes/floor_L1.blend
```

## 執行物件製作腳本

```bash
blender blender/scenes/floor_L1.blend \
  --python blender/scripts/<分類>/<腳本>.py
```

製作腳本會修改目前開啟的場景。請先檢查物件的位置、縮放、方向及材質，再從 Blender 儲存主檔。

## 從 Gazebo 場景同步

```bash
blender --background blender/scenes/floor_L1.blend \
  --python ros2_ws/src/my_hospital_rmf/tools/blender/sync_l1_world_to_blender.py \
  -- --apply
```

同步工具會更新 Gazebo 模型、門與牆壁，同時保留 Blender 裝飾物件。重新匯入的牆壁固定使用 `Z scale = 0.45`。

## 匯出前端模型

```bash
cd frontend
npm run models:update
```

此命令會從 `floor_L1.blend` 匯出 `hospital_L1.glb`，再產生前端載入的 `hospital_L1_environment.glb`。
