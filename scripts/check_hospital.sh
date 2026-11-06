#!/usr/bin/env bash

PROJECT_ROOT="$HOME/clinical-multi-robot-collaboration-platform-system"

source "$PROJECT_ROOT/scripts/hospital_env.sh" >/dev/null

echo "========================================"
echo " Hospital RMF Health Check"
echo "========================================"

PASS=0
FAIL=0
WARN=0

pass() {
    echo "[OK]   $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "[FAIL] $1"
    FAIL=$((FAIL + 1))
}

warn() {
    echo "[WARN] $1"
    WARN=$((WARN + 1))
}

check_node() {
    local node="$1"

    if echo "$NODE_LIST" | grep -Fxq "$node"; then
        pass "Node: $node"
    else
        fail "Node: $node"
    fi
}

check_topic() {
    local topic="$1"

    if echo "$TOPIC_LIST" | grep -Fxq "$topic"; then
        pass "Topic: $topic"
    else
        fail "Topic: $topic"
    fi
}

check_process_count() {
    local label="$1"
    local pattern="$2"
    local expected="$3"

    local count
    count=$(pgrep -af "$pattern" 2>/dev/null | wc -l)

    if [ "$count" -eq "$expected" ]; then
        pass "$label process count = $count"
    else
        fail "$label process count = $count (expected $expected)"
    fi
}

echo
echo "Collecting ROS graph..."

NODE_LIST=$(ros2 node list --no-daemon --spin-time 3 2>/dev/null || true)
TOPIC_LIST=$(ros2 topic list --no-daemon --spin-time 3 2>/dev/null || true)

# --------------------------------------------------
# 1. Core RMF Nodes
# --------------------------------------------------
echo
echo "---- Core RMF Nodes ----"

check_node "/hospital_fleet_command_handle"
check_node "/hospital_fleet_fleet_adapter"
check_node "/hospital_fleet_fleet_manager"
check_node "/rmf_dispatcher_node"
check_node "/rmf_traffic_blockade_node"
check_node "/hospital_g1_navigation_bridge"

# Traffic schedule node has random suffix
if echo "$NODE_LIST" | grep -q "^/rmf_traffic_schedule_node_"; then
    pass "Node: /rmf_traffic_schedule_node_*"
else
    fail "Node: /rmf_traffic_schedule_node_*"
fi


# --------------------------------------------------
# 2. Core Topics
# --------------------------------------------------
echo
echo "---- Core Topics ----"

check_topic "/fleet_states"
check_topic "/robot_state"
check_topic "/robot_path_requests"
check_topic "/rmf_task/bid_notice"
check_topic "/rmf_task/bid_response"
check_topic "/dispatch_states"


# --------------------------------------------------
# 3. Robot Odometry
# --------------------------------------------------
echo
echo "---- Robot Odometry ----"

for i in {1..7}; do
    check_topic "/hospital_robot_${i}/diff_drive_controller/odom"
done


# --------------------------------------------------
# 4. Duplicate Core Nodes
# --------------------------------------------------
echo
echo "---- Duplicate Core Nodes ----"

for node in \
    "/hospital_fleet_command_handle" \
    "/hospital_fleet_fleet_adapter" \
    "/hospital_fleet_fleet_manager" \
    "/rmf_dispatcher_node" \
    "/hospital_g1_navigation_bridge"
do
    COUNT=$(echo "$NODE_LIST" | grep -Fx "$node" | wc -l)

    if [ "$COUNT" -eq 1 ]; then
        pass "$node count = 1"
    elif [ "$COUNT" -eq 0 ]; then
        fail "$node count = 0"
    else
        fail "$node count = $COUNT (duplicate)"
    fi
done


# --------------------------------------------------
# 5. Core Processes
# --------------------------------------------------
echo
echo "---- Core Processes ----"

check_process_count \
    "hospital.launch.py" \
    "ros2 launch my_hospital_rmf hospital.launch.py" \
    1

check_process_count \
    "Fleet Manager" \
    "rmf_demos_fleet_adapter/fleet_manager" \
    1

check_process_count \
    "Fleet Adapter" \
    "/my_hospital_rmf/hospital_fleet_adapter" \
    1

check_process_count \
    "Task Dispatcher" \
    "rmf_task_ros2/rmf_task_dispatcher" \
    1

check_process_count \
    "Navigation Bridge" \
    "/my_hospital_rmf/hospital_g1_navigation_bridge" \
    1


# --------------------------------------------------
# 6. Network Ports
# --------------------------------------------------
echo
echo "---- Network Ports ----"

if ss -ltnp 2>/dev/null | grep -q ":22013 "; then
    pass "Fleet Manager API port 22013 listening"
else
    fail "Fleet Manager API port 22013 not listening"
fi

if ss -ltnp 2>/dev/null | grep -q ":9091 "; then
    pass "Rosbridge port 9091 listening"
else
    fail "Rosbridge port 9091 not listening"
fi

# Port 9090 should not have an orphaned old adapter
if ss -ltnp 2>/dev/null | grep -q ":9090 "; then
    warn "Port 9090 is listening. Check for orphan hospital_rosbridge_ws_adapter."
else
    pass "No orphan service on port 9090"
fi


# --------------------------------------------------
# 7. Fleet Manager API
# --------------------------------------------------
echo
echo "---- Fleet Manager API ----"

API_BASE="http://127.0.0.1:22013/open-rmf/rmf_demos_fm/status/"

for i in {1..7}; do
    ROBOT="hospital_robot_${i}"

    RESPONSE=$(curl \
        --connect-timeout 2 \
        --max-time 4 \
        -s \
        "${API_BASE}?robot_name=${ROBOT}" \
        2>/dev/null || true)

    if [ -z "$RESPONSE" ]; then
        fail "$ROBOT API: no response"
        continue
    fi

    if echo "$RESPONSE" | grep -q '"success":true'; then
        pass "$ROBOT API: success=true"
    else
        fail "$ROBOT API: invalid response"
        echo "       $RESPONSE"
    fi
done


# --------------------------------------------------
# 8. Gazebo
# --------------------------------------------------
echo
echo "---- Gazebo ----"

if pgrep -af "gz sim server" >/dev/null 2>&1; then
    pass "Gazebo server running"
else
    fail "Gazebo server not running"
fi

if pgrep -af "gz sim gui" >/dev/null 2>&1; then
    pass "Gazebo GUI running"
else
    warn "Gazebo GUI not detected"
fi


# --------------------------------------------------
# Result
# --------------------------------------------------
echo
echo "========================================"
echo " Result"
echo "========================================"

echo "PASS = $PASS"
echo "WARN = $WARN"
echo "FAIL = $FAIL"

if [ "$FAIL" -eq 0 ]; then
    echo
    if [ "$WARN" -eq 0 ]; then
        echo "SYSTEM STATUS: HEALTHY"
    else
        echo "SYSTEM STATUS: HEALTHY WITH WARNINGS"
    fi
    exit 0
else
    echo
    echo "SYSTEM STATUS: CHECK REQUIRED"
    exit 1
fi