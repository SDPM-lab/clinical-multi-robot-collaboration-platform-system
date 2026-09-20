export default {
  nav: { overview:'面板', dispatch:'任務派遣', history:'排程歷史', map:'即時地圖', robots:'機器人狀態' },
  user: { menu:'使用者選單', profile:'編輯個人資料', language:'語言', logout:'登出', displayName:'顯示名稱', avatar:'更換頭像', cancel:'取消', save:'儲存', close:'關閉', chooseImage:'選擇圖片', invalidImage:'頭像僅支援 JPG、PNG 或 WebP。', imageTooLarge:'頭像檔案不可超過 3 MB。', imageReadError:'無法讀取這張圖片。', invalidName:'請輸入顯示名稱。' },
  common: { search:'搜尋任務、機器人或區域', today:'今天', previous:'上一個', next:'下一個', all:'全部', clear:'清除篩選', loading:'載入中…', retry:'重新載入', minutes:'分鐘', tasks:'筆任務', demo:'展示資料 · 唯讀', records:'歷史紀錄', noData:'沒有符合條件的任務', noDataHint:'請選擇其他日期、時間模式或清除篩選條件。', filter:'篩選', apply:'套用', expand:'展開地圖', fullscreen:'切換全螢幕', lightMode:'切換至淺色模式', darkMode:'切換至深色模式', navigation:'主要導覽' },
  history: { title:'排程歷史', timeMode:'時間模式', daily:'日', weekly:'週', monthly:'月', search:'搜尋任務、機器人或地點', dateRange:'日期範圍', time:'時間', id:'任務編號', name:'任務名稱', robot:'機器人', origin:'起點', destination:'終點', priority:'優先級', status:'狀態', duration:'任務時長', details:'任務細節', route:'樓層路線', routeHeader:'任務路線', timeline:'任務歷程', start:'開始時間', end:'結束時間', floor:'1F · 導航路網', floorField:'樓層', viewDetails:'查看細節', taskCount:'目前範圍', calendar:'月份日曆', loadError:'無法載入排程歷史，請重試。' },
  metrics: { total:'任務總數', completed:'已完成', cancelled:'已取消', overdue:'已超時', failed:'失敗／異常', vsDay:'與昨日相比', vsWeek:'與上週相比', vsMonth:'與上月相比', noChange:'無變化' },
  status: { completed:'已完成', running:'執行中', failed:'失敗／異常', waiting:'待執行', cancelled:'已取消', overdue:'已超時' },
  priority: { urgent:'緊急', high:'高', normal:'一般', low:'低' },
  stages: { created:'任務建立', received:'機器人接收任務', toOrigin:'前往起點', pickedUp:'完成取件', toDestination:'前往終點', completed:'任務完成', cancelled:'任務已取消', failed:'任務失敗' },
  tasks: { '藥品配送':'藥品配送', '檢體運送':'檢體運送', '病房物資補充':'病房物資補充', '門診文件配送':'門診文件配送', '醫療廢棄物運送':'醫療廢棄物運送', '清潔用品補充':'清潔用品補充', '文件配送':'文件配送', '前往充電':'前往充電' },
  locations: { 'Pharmacy':'藥局', 'Nurse Reception':'護理接待處', 'Nurse Station':'護理站', 'Consultation Room 2':'門診 2 室', 'Ward A':'病房 A', 'Charging Station A':'充電站 A', 'Laboratory':'檢驗室' },
  map: { title:'醫院平面地圖', origin:'起點', destination:'終點', robot:'機器人', zoomIn:'放大地圖', zoomOut:'縮小地圖', reset:'重設', loading:'正在載入 RMF 地圖…' },
  search: { page:'頁面', robot:'機器人', task:'任務', todayTasks:'今日任務', empty:'找不到符合的結果', open:'開啟搜尋', clear:'清除搜尋' },
}
