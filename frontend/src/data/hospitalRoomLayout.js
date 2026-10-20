// Source vertex indices refer to L1.building.yaml, never to navigation graph IDs.
// Keep this declaration JSON-compatible: the Python generator reads the same data.
export const hospitalRoomLayout = {
  "schemaVersion": 1,
  "level": "L1",
  "source": "ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml",
  "labelPolicy": "current-navigation-and-frontend-names",
  "isDemo": false,
  "boundaryToleranceMeters": 0.12,
  "footprintVertexIndices": [
    38,
    39,
    40,
    41
  ],
  "rooms": [
    {
      "id": "ward-a",
      "label": "病房 A",
      "category": "ward",
      "boundaryVertexIndices": [
        38,
        42,
        45,
        44
      ],
      "waypointNames": [
        "ward_a_1",
        "ward_a_2"
      ]
    },
    {
      "id": "ward-b",
      "label": "病房 B",
      "category": "ward",
      "boundaryVertexIndices": [
        44,
        45,
        49,
        48
      ],
      "waypointNames": [
        "ward_b_1",
        "ward_b_2"
      ]
    },
    {
      "id": "consultation-3",
      "label": "診間 3",
      "category": "consultation",
      "boundaryVertexIndices": [
        48,
        49,
        53,
        52
      ],
      "waypointNames": [
        "consult_3_1",
        "consult_3_2"
      ]
    },
    {
      "id": "consultation-2",
      "label": "診間 2",
      "category": "consultation",
      "boundaryVertexIndices": [
        52,
        53,
        57,
        56
      ],
      "waypointNames": [
        "consult_2_1",
        "consult_2_2"
      ]
    },
    {
      "id": "consultation-1",
      "label": "診間 1",
      "category": "consultation",
      "boundaryVertexIndices": [
        56,
        57,
        61,
        60
      ],
      "waypointNames": [
        "consult_1_1",
        "consult_1_2"
      ]
    },
    {
      "id": "laboratory",
      "label": "檢驗室",
      "category": "examination",
      "boundaryVertexIndices": [
        95,
        91,
        92,
        94
      ],
      "waypointNames": [
        "lab"
      ]
    },
    {
      "id": "blood-draw",
      "label": "抽血區",
      "category": "examination",
      "boundaryVertexIndices": [
        91,
        87,
        88,
        92
      ],
      "waypointNames": [
        "blood_draw"
      ],
      "sourceNote": "候選邊界僅引用原始頂點；入口若缺少門段，不視為已驗證閉合區域。"
    },
    {
      "id": "x-ray",
      "label": "X 光檢查區",
      "category": "examination",
      "boundaryVertexIndices": [
        84,
        41,
        80,
        85
      ],
      "waypointNames": [
        "x-ray"
      ]
    },
    {
      "id": "ultrasound",
      "label": "超音波室",
      "category": "examination",
      "boundaryVertexIndices": [
        79,
        80,
        76,
        75
      ],
      "waypointNames": [
        "ultrasound_1",
        "ultrasound_2"
      ]
    },
    {
      "id": "ecg",
      "label": "心電圖室",
      "category": "examination",
      "boundaryVertexIndices": [
        75,
        76,
        72,
        71
      ],
      "waypointNames": [
        "ecg_1",
        "ecg_2"
      ]
    },
    {
      "id": "therapy",
      "label": "治療室",
      "category": "examination",
      "boundaryVertexIndices": [
        71,
        72,
        67,
        68
      ],
      "waypointNames": [
        "therapy_room"
      ]
    },
    {
      "id": "charging",
      "label": "充電區",
      "category": "charging",
      "boundaryVertexIndices": [
        108,
        107,
        112,
        113
      ],
      "waypointNames": [
        "charging_station_1",
        "charging_station_2"
      ]
    },
    {
      "id": "waste-return",
      "label": "廢棄物回收區",
      "category": "support",
      "boundaryVertexIndices": [
        113,
        112,
        110,
        109
      ],
      "waypointNames": [
        "waste_return_1",
        "waste_return_2"
      ]
    },
    {
      "id": "pantry",
      "label": "茶水間",
      "category": "support",
      "boundaryVertexIndices": [
        115,
        108,
        117,
        118
      ],
      "waypointNames": [
        "pantry"
      ]
    },
    {
      "id": "clothes-return",
      "label": "衣物回收區",
      "category": "support",
      "boundaryVertexIndices": [
        118,
        117,
        120,
        121
      ],
      "waypointNames": [
        "clothes_return_1",
        "clothes_return_2"
      ]
    },
    {
      "id": "nurse-station",
      "label": "護理站",
      "category": "nursing",
      "boundaryVertexIndices": [],
      "waypointNames": [
        "nurse_station"
      ],
      "sourceNote": "頂點 96–106 附近有外形參考，但缺少對應 walls 閉合邊界；不自動連成房間。"
    },
    {
      "id": "reception",
      "label": "護理接待處",
      "category": "nursing",
      "boundaryVertexIndices": [],
      "waypointNames": [
        "reception_back"
      ],
      "sourceNote": "開放式櫃檯，沒有經確認的房間邊界。"
    },
    {
      "id": "pharmacy",
      "label": "藥局",
      "category": "support",
      "boundaryVertexIndices": [],
      "waypointNames": [
        "pharmacy"
      ],
      "sourceNote": "依目前 pharmacy 導航節點位置；缺少包含該節點且可由現有牆線確認的房間邊界。"
    }
  ],
  "nameSources": [
    "frontend/public/generated/rmf-navigation.json",
    "frontend/src/three/navigation/RoomLabelLayer.js",
    "frontend/src/data/demoActiveRoutes.js"
  ]
}
