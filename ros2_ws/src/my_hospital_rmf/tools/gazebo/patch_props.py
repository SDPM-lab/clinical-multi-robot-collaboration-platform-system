"""
Step +: Add or override props from config/props.yaml in L1.world.

The building map generator may already have emitted an include with the same
name. Model-only replacements preserve the generated pose and other fields.
Legacy entries with an explicit pose may still add or override whole includes.
"""
import re
import shutil
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

import yaml
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2]
world_path = PKG_ROOT / "maps/L1.world"
props_path = PKG_ROOT / "config/props.yaml"
models_path = PKG_ROOT / "models"

# These are coordinate-system infrastructure, not scene props. Scaling them
# would misalign the building, navigation graph, and robot poses.
GLOBAL_SCALE_EXCLUDED_URIS = {
    "model://hospital_L1",
    "model://hospital_nav_overlay",
}


def _numbers(element, count):
    values = [float(value) for value in (element.text or "").split()]
    if len(values) != count:
        raise ValueError(
            f"Expected {count} numbers in <{element.tag}>, got {element.text!r}"
        )
    return values


def _set_numbers(element, values):
    element.text = " ".join(f"{value:.12g}" for value in values)


def _fuel_source(uri):
    parsed = urlparse(uri)
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    try:
        model_index = [part.lower() for part in parts].index("models")
        owner = parts[model_index - 1]
        model = parts[model_index + 1]
    except (ValueError, IndexError) as error:
        raise ValueError(f"Unsupported Fuel model URI: {uri}") from error

    cache_dir = (
        Path.home() / ".gz/fuel" / parsed.netloc.lower() / owner.lower()
        / "models" / model.lower()
    )
    versions = [path for path in cache_dir.iterdir() if path.is_dir()] if cache_dir.exists() else []
    versions.sort(key=lambda path: int(path.name) if path.name.isdigit() else -1, reverse=True)
    for version_dir in versions:
        sdf_path = version_dir / "model.sdf"
        if sdf_path.exists():
            files_base = f"{uri.rstrip('/')}/{version_dir.name}/files"
            return sdf_path, files_base

    raise FileNotFoundError(
        f"Fuel model is not cached: {uri}\n"
        "Open the original model in Gazebo once, then run rebuild-hospital again."
    )


def _model_source(uri):
    if uri.startswith("model://"):
        model_name = uri[len("model://"):].strip("/")
        sdf_path = models_path / model_name / "model.sdf"
        if not sdf_path.exists():
            raise FileNotFoundError(f"Local model not found: {sdf_path}")
        return sdf_path, f"model://{model_name}"
    if uri.startswith("http://") or uri.startswith("https://"):
        return _fuel_source(uri)
    raise ValueError(f"Scaling is only supported for model:// and Fuel URIs: {uri}")


def _source_name(uri):
    if uri.startswith("model://"):
        return uri[len("model://"):].strip("/").split("/")[-1]
    parts = [unquote(part) for part in urlparse(uri).path.split("/") if part]
    try:
        return parts[[part.lower() for part in parts].index("models") + 1]
    except (ValueError, IndexError) as error:
        raise ValueError(f"Cannot determine model name from URI: {uri}") from error


def _original_generated_source(uri):
    if not uri.startswith("model://"):
        return uri
    config_path = models_path / uri[len("model://"):].strip("/") / "model.config"
    if not config_path.exists():
        return uri
    match = re.search(
        r"<description>Generated from (.+?) at scale \[.*?\]\.</description>",
        config_path.read_text(encoding="utf-8"),
    )
    return match.group(1) if match else uri


def _cleanup_unreferenced_generated_models(world_text):
    referenced = set(re.findall(r"<uri>model://([^<]+)</uri>", world_text))
    removed = 0
    for model_dir in models_path.iterdir():
        if not model_dir.is_dir() or model_dir.name in referenced:
            continue
        config_path = model_dir / "model.config"
        if not config_path.exists():
            continue
        config_text = config_path.read_text(encoding="utf-8", errors="replace")
        if "<description>Generated from " not in config_text:
            continue
        shutil.rmtree(model_dir)
        removed += 1
    return removed


def _scale_model(source_uri, scale):
    source_uri = _original_generated_source(source_uri)
    if not isinstance(scale, list) or len(scale) != 3:
        raise ValueError(f"scale must contain exactly three numbers: {scale!r}")
    factors = [float(value) for value in scale]
    if any(value <= 0 for value in factors):
        raise ValueError(f"scale values must be positive: {scale!r}")

    source_sdf, asset_base = _model_source(source_uri)
    tree = ET.parse(source_sdf)
    root = tree.getroot()
    model = root.find("model")
    if model is None:
        raise ValueError(f"No <model> found in {source_sdf}")

    # Stable name: every rebuild overwrites the same generated directory.
    # Use the URI name instead of the SDF model name because some Fuel models
    # contain incorrect or duplicated internal names.
    source_name = re.sub(r"[^A-Za-z0-9_]+", "_", _source_name(source_uri)).strip("_")
    generated_name = f"{source_name}_real"
    model.set("name", generated_name)

    # Scale every internal translation so multi-link models keep their layout.
    for pose_element in model.iter("pose"):
        values = _numbers(pose_element, 6)
        values[:3] = [values[i] * factors[i] for i in range(3)]
        _set_numbers(pose_element, values)

    for mesh in model.iter("mesh"):
        mesh_scale = mesh.find("scale")
        if mesh_scale is None:
            mesh_scale = ET.SubElement(mesh, "scale")
            base_scale = [1.0, 1.0, 1.0]
        else:
            base_scale = _numbers(mesh_scale, 3)
        _set_numbers(mesh_scale, [base_scale[i] * factors[i] for i in range(3)])

        mesh_uri = mesh.find("uri")
        if mesh_uri is not None and mesh_uri.text:
            value = mesh_uri.text.strip()
            if "://" not in value and not value.startswith("/"):
                mesh_uri.text = f"{asset_base.rstrip('/')}/{value.lstrip('/')}"

    for box in model.iter("box"):
        size = box.find("size")
        if size is not None:
            values = _numbers(size, 3)
            _set_numbers(size, [values[i] * factors[i] for i in range(3)])

    for cylinder in model.iter("cylinder"):
        if abs(factors[0] - factors[1]) > 1e-9:
            raise ValueError("Cylinder models require equal X and Y scale values")
        radius = cylinder.find("radius")
        length = cylinder.find("length")
        if radius is not None:
            _set_numbers(radius, [_numbers(radius, 1)[0] * factors[0]])
        if length is not None:
            _set_numbers(length, [_numbers(length, 1)[0] * factors[2]])

    for sphere in model.iter("sphere"):
        if max(factors) - min(factors) > 1e-9:
            raise ValueError("Sphere models require uniform scale values")
        radius = sphere.find("radius")
        if radius is not None:
            _set_numbers(radius, [_numbers(radius, 1)[0] * factors[0]])

    output_dir = models_path / generated_name
    output_dir.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(output_dir / "model.sdf", encoding="utf-8", xml_declaration=True)
    (output_dir / "model.config").write_text(
        f'''<?xml version="1.0"?>
<model>
  <name>{generated_name}</name>
  <version>1.0</version>
  <sdf version="1.7">model.sdf</sdf>
  <author><name>hospital_rmf</name></author>
  <description>Generated from {source_uri} at scale {factors}.</description>
</model>
''',
        encoding="utf-8",
    )
    return f"model://{generated_name}"


def _apply_scene_scale(world_text, scale):
    if not scale:
        return world_text, 0

    include_pattern = re.compile(r"    <include>[\s\S]*?    </include>")
    scaled_count = 0

    def replace_include(match):
        nonlocal scaled_count
        block = match.group(0)
        uri_match = re.search(r"      <uri>([^<]+)</uri>", block)
        if not uri_match:
            return block
        source_uri = uri_match.group(1)
        if source_uri in GLOBAL_SCALE_EXCLUDED_URIS:
            return block
        scaled_uri = _scale_model(source_uri, scale)
        scaled_count += 1
        return block[:uri_match.start(1)] + scaled_uri + block[uri_match.end(1):]

    return include_pattern.sub(replace_include, world_text), scaled_count

def replace_model_only(world_text, prop, scene_scale):
    """Replace an existing include URI without changing its pose or properties."""
    if "pose" in prop:
        raise ValueError("replace_model_only cannot specify pose")
    pattern = re.compile(r"<include\b[^>]*>[\s\S]*?</include>")
    matches = [m for m in pattern.finditer(world_text)
               if ET.fromstring(m.group()).findtext("name") == prop["name"]]
    if len(matches) > 1:
        raise ValueError(f"Duplicate world model name: {prop['name']}")
    if not matches:
        return world_text, False
    match = matches[0]
    element = ET.fromstring(match.group())
    uri_element = element.find("uri")
    if uri_element is None:
        raise ValueError(f"Missing URI for model: {prop['name']}")
    scale = prop.get("scale", scene_scale)
    uri_element.text = _scale_model(prop["uri"], scale) if scale else prop["uri"]
    replacement = ET.tostring(element, encoding="unicode")
    return world_text[:match.start()] + replacement + world_text[match.end():], True


if not props_path.exists():
    print("props.yaml not found, skipping")
    raise SystemExit(0)

text = world_path.read_text(encoding="utf-8")

with open(props_path) as f:
    cfg = yaml.safe_load(f)

props = cfg.get("props", []) or []
scene_scale = cfg.get("scene_scale")
text, scene_scaled_count = _apply_scene_scale(text, scene_scale)
added = []

for prop in props:
    name = prop["name"]
    source_uri = prop["uri"]
    if prop.get("replace_model_only", False):
        text, replaced = replace_model_only(text, prop, scene_scale)
        if replaced:
            added.append(f"{name} (model replaced, generated pose preserved)")
        else:
            print(f"Skipped {name}: not present in generated world")
        continue
    pose = prop.get("pose", [0, 0, 0, 0, 0, 0])
    pose_str = " ".join(str(v) for v in pose)
    # Per-prop scale overrides the global scene scale.
    scale = prop.get("scale", scene_scale)
    uri = _scale_model(source_uri, scale) if scale else source_uri
    static = str(prop.get("static", True)).lower()
    block = f"""    <include>
      <name>{name}</name>
      <uri>{uri}</uri>
      <pose>{pose_str}</pose>
      <static>{static}</static>
    </include>"""

    # Replace an existing include emitted by building_map_generator. This
    # makes props.yaml an override layer instead of silently ignoring it.
    include_pattern = re.compile(
        rf"    <include>\s*\n"
        rf"(?:(?!    </include>)[\s\S])*?"
        rf"      <name>{re.escape(name)}</name>\s*\n"
        rf"(?:(?!    </include>)[\s\S])*?"
        rf"    </include>"
    )
    text, replaced = include_pattern.subn(lambda _: block, text, count=1)
    if replaced:
        added.append(f"{name} (overridden)")
    else:
        text = text.replace("  </world>", block + "\n  </world>")
        added.append(f"{name} (added)")

stale_removed_count = _cleanup_unreferenced_generated_models(text)
world_path.write_text(text, encoding="utf-8")
if added:
    print(f"Applied {len(added)} prop(s): {', '.join(added)}")
else:
    print("No props to apply")
if scene_scale:
    print(f"Applied scene scale {scene_scale} to {scene_scaled_count} include(s)")
if stale_removed_count:
    print(f"Removed {stale_removed_count} unreferenced generated model directorie(s)")
