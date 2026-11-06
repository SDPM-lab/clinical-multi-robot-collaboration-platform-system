# L1 派遣路線：Traffic Editor 與 GLB 顯示對應

## 來源與重產生

網頁載入 `frontend/public/models/L1__flat.glb` 的預設場景 `L1_Solid_Block_Map_v5`。`blender/` 沒有另一份同名 GLB。導覽來源依序為 `ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml`、`nav_graphs_generated/0.yaml`、`frontend/public/generated/rmf-navigation.json`（Graph 0）。不需要另備 `L1_route_graph.json`。

`frontend/scripts/generate-dispatch-route-mapping.py` 直接解析 GLB 的 glTF JSON：每個 `Route_*` 是獨立 mesh，每個端點、轉角和分岔為 `RouteNode_*`；腳本並檢查 103 個路段網格的幾何範圍涵蓋其端點。產物 `frontend/public/generated/dispatch-route-mapping.json` 包含來源檔 SHA-256、樓層與圖索引、TE 節點 ID／名稱／原座標、GLB 顯示節點／座標，以及每條有向導航邊對應的顯示節點折線。原 GLB 沒有 `extras` 或 TE ID，故這份獨立資料是必要的對應契約；不修改 `.blend` 或 GLB。節點狀態 `candidate` 表示這是經來源拓撲核對的示意顯示錨點，並非經測量的 ROS 座標校正點。

```sh
cd frontend
npm run navigation:dispatch-map   # 來源有意變更後重產生
npm run navigation:dispatch-check # 唯讀檢查來源與產物是否一致
```

前端載入時核對導航 JSON 與 GLB 的雜湊，再檢查節點和 lane 對應。版本不符時停止畫路線並顯示錯誤，避免用舊對應資料畫新圖。模型仍可顯示。Blender 物件只提供顯示幾何；**唯一可行走關係與方向由 Graph 0 的 lanes 決定**。線段交叉但不共享 TE 節點時，不能轉彎。修正用的美術轉角也不會成為 ROS 節點。

## 已核對的差異與顯示修正

- GLB 左側 `ward_b_door` 原本與主幹斷開，Graph 0 的 Ward B 卻可達。依已確認的處理方式，在對應資料加入 `ward_b_junction` 及進入 Ward B 的短折線；原 GLB 路線物件仍保留，網頁隱藏後以對應折線呈現。
- GLB 右側 `right_therapy`／`right_waste` 的沿走廊順序與 TE 的 `right_bottom → waste_return → therapy → ecg` 不同。對應資料只調整這段**畫面顯示**的交會位置和兩條通往房間的折線，不改導航 YAML 或房間方塊。
- GLB 接待區的支線在主幹上共用一小段，會讓兩條不同 TE 邊共用同一顯示路段。將接待區入口的顯示支線改為從 `center_mid` 向下折入，保留接待區端點，避免任務高亮在非共用邊上重疊。

上述修正列於產物的 `displayNodes`、`displayEdges` 與 `suppressedGlbRoutes`，可逐項檢查。`audit` 列出未對應節點、有歧義的共用路段、純視覺分支及孤立 GLB 節點。目前 51/51 TE 節點及 104/104 有向邊有顯示對應，無重複節點錨點或非預期共用路段；13 段為純視覺線，不參與導航。兩個電梯顯示節點孤立，沒有對應的 Graph 0 目的站點。

`Room_director`、`Room_men_restroom`、`Room_women_restroom`、`Room_lift_1`、`Room_lift_2` 沒有可確認的 Graph 0 房間目的站點。不能僅因房間有展示線就讓機器人接單。`reception_back` 對應接待區入口，但其精確房內停靠點尚未經 ROS／GLB 座標驗證。

## 網頁顯示與位置限制

派遣地圖隱藏 GLB 原有 `Route_*`／`RouteNode_*` 網格，依對應資料以 `#DAC9A6` 重畫路線；導航路線高亮使用**相同顯示折線**與 `#F75C2F`，起終點使用同一顯示節點上的 `#EEA9A9` 圖釘。圓點代表目前 18 個可在派遣表單選取的具名房間站點；沒有圓點的走廊若對應 Graph 0 lane，仍可通行。這 18 個站點的 TE 節點 ID 由 `src/config/dispatchDestinations.js` 明列，並經測試確認可雙向連到接待處。其他同房間的中繼節點仍可通行，但不重複列成任務目的地。`charging_station_2` 的「B 站」語意與單一 GLB 充電室尚有歧義，因此未加入任務選單。GLB 中未被任何導航邊使用的 13 段，以較淡的視覺線顯示，絕不送進尋路。舊的 TE 座標整體相似變換不再用於此派遣畫面。

目前派遣頁讀取 `demoFleetStore` 的 `currentWaypoint`，所以機器人標記只代表示範資料的具名站點。沒有已確認的即時導航邊與邊上進度；純 ROS 座標不可在分岔或平行走廊僅靠最近距離猜路段。本修改不宣稱完成 ROS／GLB 精準校正或即時機器人折線動畫。

## 驗證案例

以下路徑均由 Graph 0 的有向邊搜尋，未添加導航邊：

| 案例 | Graph 0 路段 | 截圖 |
| --- | --- | --- |
| 診間 2 → 護理站 | `v18 → v15 → v49 → v50`；`l30, l101, l102` | `screenshots/dispatch-route-consult2-nurse-1536x864.png` |
| Reception → Charging Station A | `v2 → v1 → v3 → v4 → v5 → v6 → v7 → v28` | `screenshots/dispatch-route-reception-charging-1536x864.png` |
| Reception → Pharmacy | `v2 → v1 → v3 → v33 → v34` | `screenshots/dispatch-route-reception-pharmacy-1536x864.png` |

檢查命令：`npm run navigation:dispatch-check`、`npm test -- test/dispatchRouteMapping.test.js`、`npm run build`。上列三張截圖為完成對應修正後的實際頁面擷取。
