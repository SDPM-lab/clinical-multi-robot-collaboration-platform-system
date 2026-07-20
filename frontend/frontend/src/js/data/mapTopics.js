export const mapTopics = [
  { layer: 'occupancy', topic: '/map', type: 'nav_msgs/OccupancyGrid' },
  { layer: 'pose', topic: '/amcl_pose', type: 'geometry_msgs/PoseWithCovarianceStamped' },
  { layer: 'path', topic: '/plan', type: 'nav_msgs/Path' },
  { layer: 'laser', topic: '/scan', type: 'sensor_msgs/LaserScan' },
  { layer: 'costmap', topic: '/global_costmap/costmap', type: 'nav_msgs/OccupancyGrid' },
]

export const defaultRosBridgeUrl = 'ws://localhost:9090'
