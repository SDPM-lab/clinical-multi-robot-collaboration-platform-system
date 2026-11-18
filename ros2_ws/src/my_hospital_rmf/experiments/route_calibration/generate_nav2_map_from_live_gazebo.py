from pathlib import Path
import xml.etree.ElementTree as ET
import math
import yaml

from PIL import Image, ImageDraw

import rclpy
from rclpy.node import Node
from simulation_interfaces.srv import GetEntityState


ROOT = Path(
    "ros2_ws/src/my_hospital_rmf"
)

SDF = ROOT / "maps/L1.sdf"
OLD_MAP_YAML = ROOT / "maps/L1.yaml"
OLD_MAP_IMAGE = ROOT / "maps/L1.png"

OUT_IMAGE = ROOT / "maps/L1_nav2_live.png"
OUT_YAML = ROOT / "maps/L1_nav2_live.yaml"

MODELS_ROOT = ROOT / "models"

ROBOT_Z_MIN = 0.0
ROBOT_Z_MAX = 2.0


# ============================================================
# Pose helpers
# ============================================================

def parse_pose(text):
    values = [
        float(v)
        for v in (
            text
            or "0 0 0 0 0 0"
        ).split()
    ]

    while len(values) < 6:
        values.append(0.0)

    return values[:6]


def compose_2d(parent, child):

    px, py, pz, _, _, pyaw = parent
    cx, cy, cz, _, _, cyaw = child

    c = math.cos(pyaw)
    s = math.sin(pyaw)

    x = px + c * cx - s * cy
    y = py + s * cx + c * cy
    z = pz + cz

    return [
        x,
        y,
        z,
        0.0,
        0.0,
        pyaw + cyaw,
    ]


def transform_xy(x, y, pose):

    tx, ty, _, _, _, yaw = pose

    c = math.cos(yaw)
    s = math.sin(yaw)

    return (
        tx + c * x - s * y,
        ty + s * x + c * y,
    )


def intersects_robot_height(zmin, zmax):

    return (
        zmax >= ROBOT_Z_MIN
        and zmin <= ROBOT_Z_MAX
    )


# ============================================================
# Map metadata
# ============================================================

with OLD_MAP_YAML.open(
    "r",
    encoding="utf-8",
) as f:
    map_info = yaml.safe_load(f)

resolution = float(
    map_info["resolution"]
)

origin_x = float(
    map_info["origin"][0]
)

origin_y = float(
    map_info["origin"][1]
)

old_img = Image.open(
    OLD_MAP_IMAGE
)

width, height = old_img.size


def world_to_pixel(x, y):

    px = (
        x - origin_x
    ) / resolution

    map_y = (
        y - origin_y
    ) / resolution

    py = (
        height - 1
        - map_y
    )

    return (
        round(px),
        round(py),
    )


# ============================================================
# OBJ reader
# ============================================================

obj_cache = {}


def read_obj(path):

    path = Path(path)

    if path in obj_cache:
        return obj_cache[path]

    vertices = []
    faces = []

    with path.open(
        "r",
        encoding="utf-8",
        errors="ignore",
    ) as f:

        for line in f:

            if line.startswith("v "):

                p = line.split()

                if len(p) >= 4:
                    vertices.append(
                        (
                            float(p[1]),
                            float(p[2]),
                            float(p[3]),
                        )
                    )

            elif line.startswith("f "):

                ids = []

                for token in line.split()[1:]:

                    index = int(
                        token.split("/")[0]
                    )

                    if index < 0:
                        index = (
                            len(vertices)
                            + index
                        )
                    else:
                        index -= 1

                    ids.append(index)

                if len(ids) >= 3:
                    faces.append(ids)

    obj_cache[path] = (
        vertices,
        faces,
    )

    return vertices, faces


# ============================================================
# Mesh URI resolver
# ============================================================

basename_cache = {}


def resolve_mesh(uri):

    if not uri:
        return None

    uri = uri.strip()

    candidates = []

    if uri.startswith("file://"):

        raw = Path(
            uri[len("file://"):]
        )

        # Original absolute path
        candidates.append(raw)

        text = str(raw)

        # Project model copied from another machine
        marker = "/models/"

        if marker in text:

            suffix = text.split(
                marker,
                1,
            )[1]

            candidates.append(
                MODELS_ROOT
                / suffix
            )

        # Gazebo Fuel cache copied from another username
        fuel_marker = "/.gz/fuel/"

        if fuel_marker in text:

            suffix = text.split(
                fuel_marker,
                1,
            )[1]

            candidates.append(
                Path.home()
                / ".gz"
                / "fuel"
                / suffix
            )

    elif uri.startswith("model://"):

        suffix = uri[
            len("model://"):
        ]

        candidates.append(
            MODELS_ROOT
            / suffix
        )

    else:

        candidates.append(
            Path(uri)
        )

    for path in candidates:

        if path.exists():
            return path

    # Fallback search by basename
    basename = Path(uri).name

    if basename not in basename_cache:

        matches = []

        matches.extend(
            MODELS_ROOT.rglob(
                basename
            )
        )

        fuel_root = (
            Path.home()
            / ".gz"
            / "fuel"
        )

        if fuel_root.exists():

            matches.extend(
                fuel_root.rglob(
                    basename
                )
            )

        basename_cache[
            basename
        ] = matches

    matches = basename_cache[
        basename
    ]

    if len(matches) >= 1:
        return matches[0]

    return None


# ============================================================
# Drawing functions
# ============================================================

img = Image.new(
    "L",
    (
        width,
        height,
    ),
    255,
)

draw = ImageDraw.Draw(
    img
)


stats = {
    "models": 0,
    "collisions": 0,
    "mesh": 0,
    "box": 0,
    "cylinder": 0,
    "height_skipped": 0,
    "dynamic_skipped": 0,
    "floor_skipped": 0,
    "unresolved_mesh": 0,
    "live_exists": 0,
    "live_missing": 0,
}

unresolved = []


def draw_box(
    size,
    world_pose,
):

    sx, sy, sz = size

    zc = world_pose[2]

    zmin = zc - sz / 2
    zmax = zc + sz / 2

    if not intersects_robot_height(
        zmin,
        zmax,
    ):
        stats[
            "height_skipped"
        ] += 1
        return

    corners = [
        (-sx/2, -sy/2),
        (+sx/2, -sy/2),
        (+sx/2, +sy/2),
        (-sx/2, +sy/2),
    ]

    pixels = []

    for x, y in corners:

        wx, wy = transform_xy(
            x,
            y,
            world_pose,
        )

        pixels.append(
            world_to_pixel(
                wx,
                wy,
            )
        )

    draw.polygon(
        pixels,
        fill=0,
    )


def draw_cylinder(
    radius,
    length,
    world_pose,
):

    zc = world_pose[2]

    zmin = (
        zc - length/2
    )

    zmax = (
        zc + length/2
    )

    if not intersects_robot_height(
        zmin,
        zmax,
    ):
        stats[
            "height_skipped"
        ] += 1
        return

    points = []

    for i in range(32):

        angle = (
            2.0
            * math.pi
            * i
            / 32
        )

        x = (
            radius
            * math.cos(angle)
        )

        y = (
            radius
            * math.sin(angle)
        )

        wx, wy = transform_xy(
            x,
            y,
            world_pose,
        )

        points.append(
            world_to_pixel(
                wx,
                wy,
            )
        )

    draw.polygon(
        points,
        fill=0,
    )


def draw_mesh(
    mesh_path,
    mesh_scale,
    world_pose,
):

    vertices, faces = read_obj(
        mesh_path
    )

    sx, sy, sz = mesh_scale

    transformed = []

    for x, y, z in vertices:

        x *= sx
        y *= sy
        z *= sz

        wx, wy = transform_xy(
            x,
            y,
            world_pose,
        )

        wz = (
            world_pose[2]
            + z
        )

        transformed.append(
            (
                wx,
                wy,
                wz,
            )
        )

    if not transformed:
        return

    z_values = [
        p[2]
        for p in transformed
    ]

    if not intersects_robot_height(
        min(z_values),
        max(z_values),
    ):
        stats[
            "height_skipped"
        ] += 1
        return

    for face in faces:

        face_z = [
            transformed[i][2]
            for i in face
        ]

        if not intersects_robot_height(
            min(face_z),
            max(face_z),
        ):
            continue

        points = []

        for i in face:

            wx, wy, _ = (
                transformed[i]
            )

            points.append(
                world_to_pixel(
                    wx,
                    wy,
                )
            )

        if len(set(points)) >= 3:

            draw.polygon(
                points,
                fill=0,
            )

        if len(points) >= 2:

            draw.line(
                points
                + [points[0]],
                fill=0,
                width=2,
            )


# ============================================================
# Parse SDF
# ============================================================

tree = ET.parse(SDF)
root = tree.getroot()


# ============================================================
# Live Gazebo model poses
# ============================================================

rclpy.init()

ros_node = Node(
    "generate_nav2_map_from_live_gazebo"
)

state_client = ros_node.create_client(
    GetEntityState,
    "/gz_server/get_entity_state",
)

print(
    "Waiting for "
    "/gz_server/get_entity_state ..."
)

if not state_client.wait_for_service(
    timeout_sec=10.0
):
    raise RuntimeError(
        "/gz_server/get_entity_state "
        "is unavailable"
    )


def get_live_model_pose(name):

    req = GetEntityState.Request()
    req.entity = name

    future = state_client.call_async(
        req
    )

    rclpy.spin_until_future_complete(
        ros_node,
        future,
        timeout_sec=3.0,
    )

    res = future.result()

    if (
        res is None
        or res.result.result != 1
    ):
        return None

    p = res.state.pose.position
    q = res.state.pose.orientation

    yaw = math.atan2(
        2.0 * (
            q.w * q.z
            + q.x * q.y
        ),
        1.0 - 2.0 * (
            q.y * q.y
            + q.z * q.z
        ),
    )

    return [
        float(p.x),
        float(p.y),
        float(p.z),
        0.0,
        0.0,
        float(yaw),
    ]


for model in root.iter("model"):

    model_name = (
        model.get("name")
        or "<unnamed>"
    )

    static = (
        model.findtext("static")
        or "false"
    ).strip().lower()

    if static != "true":

        stats[
            "dynamic_skipped"
        ] += 1

        continue

    lower_name = (
        model_name.lower()
    )

    if (
        "physics_floor"
        in lower_name
        or lower_name
        == "ground_plane"
    ):

        stats[
            "floor_skipped"
        ] += 1

        continue

    stats[
        "models"
    ] += 1

    model_pose = get_live_model_pose(
        model_name
    )

    if model_pose is None:

        stats[
            "live_missing"
        ] += 1

        continue

    stats[
        "live_exists"
    ] += 1

    for link in model.findall(
        "link"
    ):

        link_pose = parse_pose(
            link.findtext("pose")
        )

        world_link_pose = compose_2d(
            model_pose,
            link_pose,
        )

        for collision in link.findall(
            "collision"
        ):

            stats[
                "collisions"
            ] += 1

            collision_pose = parse_pose(
                collision.findtext(
                    "pose"
                )
            )

            world_pose = compose_2d(
                world_link_pose,
                collision_pose,
            )

            geometry = collision.find(
                "geometry"
            )

            if geometry is None:
                continue


            # ----------------------------
            # Box
            # ----------------------------

            box = geometry.find(
                "box"
            )

            if box is not None:

                size_text = box.findtext(
                    "size"
                )

                if size_text:

                    size = [
                        float(v)
                        for v
                        in size_text.split()
                    ]

                    if len(size) >= 3:

                        stats[
                            "box"
                        ] += 1

                        draw_box(
                            size[:3],
                            world_pose,
                        )

                continue


            # ----------------------------
            # Cylinder
            # ----------------------------

            cylinder = geometry.find(
                "cylinder"
            )

            if cylinder is not None:

                radius = float(
                    cylinder.findtext(
                        "radius",
                        "0",
                    )
                )

                length = float(
                    cylinder.findtext(
                        "length",
                        "0",
                    )
                )

                stats[
                    "cylinder"
                ] += 1

                draw_cylinder(
                    radius,
                    length,
                    world_pose,
                )

                continue


            # ----------------------------
            # Mesh
            # ----------------------------

            mesh = geometry.find(
                "mesh"
            )

            if mesh is not None:

                stats[
                    "mesh"
                ] += 1

                uri = mesh.findtext(
                    "uri"
                )

                scale_text = (
                    mesh.findtext(
                        "scale"
                    )
                    or "1 1 1"
                )

                scale = [
                    float(v)
                    for v
                    in scale_text.split()
                ]

                while len(scale) < 3:
                    scale.append(1.0)

                path = resolve_mesh(
                    uri
                )

                if path is None:

                    stats[
                        "unresolved_mesh"
                    ] += 1

                    unresolved.append(
                        (
                            model_name,
                            uri,
                        )
                    )

                    continue

                draw_mesh(
                    path,
                    scale[:3],
                    world_pose,
                )


# ============================================================
# Save
# ============================================================

img.save(
    OUT_IMAGE
)

new_info = dict(
    map_info
)

new_info[
    "image"
] = OUT_IMAGE.name

with OUT_YAML.open(
    "w",
    encoding="utf-8",
) as f:

    yaml.safe_dump(
        new_info,
        f,
        sort_keys=False,
    )


# ============================================================
# Close ROS
# ============================================================

ros_node.destroy_node()
rclpy.shutdown()


# ============================================================
# Report
# ============================================================

print("=" * 90)
print("NAV2 STATIC MAP GENERATED")
print("=" * 90)

for key, value in stats.items():

    print(
        f"{key:20s}: "
        f"{value}"
    )

print()

print(
    f"Image : {OUT_IMAGE}"
)

print(
    f"YAML  : {OUT_YAML}"
)

if unresolved:

    print()
    print("=" * 90)
    print(
        f"UNRESOLVED MESHES "
        f"({len(unresolved)})"
    )
    print("=" * 90)

    for model_name, uri in unresolved[:30]:

        print(
            model_name
        )

        print(
            f"  {uri}"
        )

    if len(unresolved) > 30:

        print(
            f"... and "
            f"{len(unresolved)-30} more"
        )

print("=" * 90)
