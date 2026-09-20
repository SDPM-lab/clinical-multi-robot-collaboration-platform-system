// POST /api/v1/task cannot target these fleet IDs or acknowledge a charging
// command. A ROS socket connection alone does not imply control availability.
// Keep dispatch unavailable until a real charging transport and telemetry exist.
export const chargingCommandAdapter = Object.freeze({
  available: false,
  unavailableReason: '控制服務未連線',
  async dispatch() {
    throw new Error('控制服務未連線，目前無法派遣')
  },
})
