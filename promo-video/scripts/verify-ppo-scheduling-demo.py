"""Verify the film scenario using the production encoder and action mask, without ROS."""
import ast
from datetime import datetime
import json
from pathlib import Path
import sys

project = Path(__file__).resolve().parents[2]
video = project / "promo-video"
sys.path.insert(0, str(project))
sys.path.insert(0, str(project / "experiments/fleet_sizing"))

from experiments.fleet_sizing.models import RobotState, TaskState
from experiments.fleet_sizing.nav_graph import NavGraph
from experiments.fleet_sizing.rl.action_mask import ActionMaskBuilder
from experiments.fleet_sizing.rl.observation import ObservationEncoder, BATTERY_LAYOUT

scheduler = project / "ros2_ws/src/my_hospital_rmf/scripts/hospital_ppo_scheduler.py"
tree = ast.parse(scheduler.read_text())
names = {"LOGICAL_ROBOT_IDS", "ROBOT_TYPES", "ROBOT_CAPABILITIES"}
defs = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names}
capture = json.loads((video/"src/task-creation-v6-capture.json").read_text())["task"]
assert capture["taskCode"] == "T0002" and capture["status"] == "pending" and not capture["assignedRobot"]
assert capture["priority"] == "high"
clock = datetime.fromisoformat(capture["scheduledAt"].replace("Z","+00:00")).timestamp()
task = TaskState(capture["id"], capture["taskType"], capture["source"], capture["destination"], 2, clock, 0.0)
ids = defs["LOGICAL_ROBOT_IDS"]
locations = ["pharmacy", "ward_a_2", "pharmacy", "ward_a_2", "ward_a_2", "ward_a_2", "ward_a_2"]
batteries = [.72, .59, .86, .72, .51, .64, .69]
robots = [RobotState(key, defs["ROBOT_TYPES"][key], defs["ROBOT_CAPABILITIES"][defs["ROBOT_TYPES"][key]],
                     locations[i], status="charging" if key.startswith("W") else "idle",
                     battery_soc=batteries[i]) for i,key in enumerate(ids)]
graph = NavGraph()
def travel(source, destination):
    return graph.shortest_path_distance(source, destination) / 0.5
inputs = dict(robots=robots,task=task,tasks_by_id={task.task_id:task},current_time_s=clock,travel_time_fn=travel)
mask = ActionMaskBuilder(ids).build(**inputs, enable_battery_model=True)
observation = ObservationEncoder(ids, layout=BATTERY_LAYOUT).encode(**inputs)
eligible = [r.robot_id for r,m in zip(robots,mask) if m]
assert observation.shape == (98,) and mask.shape == (7,) and eligible == ["M01","M02"]
model = project/"experiments/fleet_sizing/results_rl/models/reward_confirm_sweep27_w50_a30_q15_i05_seed7104_200k/final_model.zip"
assert not model.exists(), "Run deterministic inference and review the resulting film assignment when the checkpoint becomes available."
result = {
    "taskCode": capture["taskCode"], "taskId": capture["id"], "taskType": task.task_type,
    "source": task.source, "destination": task.destination, "priority": capture["priority"],
    "scheduledAt": capture["scheduledAt"], "states": ["pending", "assigned", "executing"],
    "eligible": eligible, "robotId": "M01", "illustrative": True,
    "robots": [{"id":r.robot_id,"type":r.robot_type,"status":r.status,
                "battery":round(r.battery_soc*100),"eligible":bool(ok),
                "capabilityMatch":task.task_type in r.capabilities} for r,ok in zip(robots,mask)],
    "observationSize":int(observation.size), "actionMask":mask.tolist(),
}
(video/"src/ppo-scheduling-demo.json").write_text(json.dumps(result,indent=2)+"\n")
print(result)
