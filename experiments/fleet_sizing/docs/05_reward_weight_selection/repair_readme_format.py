from pathlib import Path
import re
import shutil
import hashlib

DOC = Path(__file__).resolve().parent

path = DOC / "README.md"

backup = DOC / "README.before_format_repair.md"

original = path.read_text(encoding="utf-8")

# ============================================================
# 1. Preserve original README
# ============================================================

if not backup.exists():
    shutil.copy2(path, backup)

source = backup.read_text(encoding="utf-8")

lines = source.splitlines()

output = []

table_count = 0
heading_count = 0
image_count = 0
formula_count = 0

i = 0

# ============================================================
# 2. Repair Markdown structure
# ============================================================

while i < len(lines):

    line = lines[i]
    stripped = line.strip()

    # Main title
    if i == 0:

        output.extend([
            "# " + stripped.lstrip("#").strip(),
            "",
        ])

        i += 1
        continue

    # Subtitle
    if i == 1:

        output.extend([
            "**" + stripped.strip("*") + "**",
            "",
        ])

        i += 1
        continue

    # Numbered sections: 1. ... / 2. ... / 16. ...
    section_match = re.match(
        r"^(\d{1,2})\.\s+(.+)$",
        stripped
    )

    expected_titles = [
        "Research Objective",
        "Reward Function Design",
        "Normalization Scale Selection",
        "Reward Weight Search Space",
        "Experimental Settings",
        "Overall",
        "Stage 1",
        "Stage 2",
        "Nav2",
        "Stage 3",
        "Stage 4",
        "Representative Model",
        "Final PPO",
        "Research Limitations",
        "Reproducibility",
        "Conclusion",
    ]

    is_main_heading = False

    if section_match:

        number = int(section_match.group(1))
        title = section_match.group(2)

        if 1 <= number <= len(expected_titles):

            is_main_heading = (
                title.casefold().startswith(
                    expected_titles[number - 1].casefold()
                )
                and number == heading_count + 1
            )

    if is_main_heading:

        output.extend([
            "",
            "## " + stripped,
            "",
        ])

        heading_count += 1
        i += 1
        continue

    # Numbered subsections: 7.1 ... / 11.2 ...
    if re.match(
        r"^\d{1,2}\.\d{1,2}\s+\S",
        stripped
    ):

        output.extend([
            "",
            "### " + stripped,
            "",
        ])

        i += 1
        continue

    # Tab-separated tables
    if "\t" in line:

        rows = []

        while (
            i < len(lines)
            and "\t" in lines[i]
        ):

            cells = [
                cell.strip()
                for cell in lines[i].split("\t")
            ]

            rows.append(cells)
            i += 1

        widths = {len(row) for row in rows}

        if len(rows) >= 2 and len(widths) == 1:

            n = len(rows[0])

            def md_row(cells):

                return "| " + " | ".join(
                    cell.replace("|", r"\|")
                    for cell in cells
                ) + " |"

            output.append("")
            output.append(md_row(rows[0]))

            output.append(
                "| " + " | ".join(
                    ["---"] * n
                ) + " |"
            )

            for row in rows[1:]:
                output.append(md_row(row))

            output.append("")

            table_count += 1

        else:

            print(
                "WARNING: irregular table:",
                rows[0] if rows else []
            )

            output.extend(
                "\t".join(row)
                for row in rows
            )

        continue

    # Display math
    if stripped in (r"\[", r"\]"):

        output.append("$$")

        formula_count += 1
        i += 1
        continue

    # Restore embedded figures from SVG links
    if re.match(
        r"^Figure\s+\d+\.",
        stripped
    ):

        match = re.search(
            r"\[SVG\]\(([^)]+\.svg)\)",
            stripped
        )

        if match:

            svg = match.group(1)

            png = svg.removesuffix(".svg") + ".png"

            assert (DOC / svg).is_file(), svg
            assert (DOC / png).is_file(), png

            caption = stripped.split("·")[0].strip()

            output.extend([
                "",
                f"![{caption}]({png})",
                "",
                f"*{caption}*",
                "",
                f"[PNG]({png}) · [SVG]({svg})",
                "",
            ])

            image_count += 1

            i += 1
            continue

    # Directory tree
    if stripped == "05_reward_weight_selection/":

        tree = [line]

        j = i + 1

        while j < len(lines):

            next_line = lines[j]

            if re.match(
                r"^[\s│├└─]*[├└]",
                next_line
            ):

                tree.append(next_line)
                j += 1

            else:
                break

        if len(tree) > 1:

            output.extend([
                "",
                "```text",
                *tree,
                "```",
                "",
            ])

            i = j
            continue

    # Reproduction commands
    if stripped == "source .venv_rl/bin/activate":

        commands = [line]

        j = i + 1

        while j < len(lines):

            next_line = lines[j]

            if next_line.strip().startswith((
                "DOC=",
                "python ",
            )):

                commands.append(next_line)
                j += 1

            else:
                break

        output.extend([
            "",
            "```bash",
            *commands,
            "```",
            "",
        ])

        i = j
        continue

    # Preserve remaining content
    output.append(line)

    i += 1


# ============================================================
# 3. Normalize excess blank lines
# ============================================================

content = "\n".join(output)

content = re.sub(
    r"\n{3,}",
    "\n\n",
    content
).strip() + "\n"


# ============================================================
# 4. Validate before writing
# ============================================================

headings = re.findall(
    r"^## (\d+)\.",
    content,
    flags=re.MULTILINE,
)

images = re.findall(
    r"!\[[^\]]*\]\(([^)]+)\)",
    content
)

print("===== README FORMAT REPAIR =====")

print("Main sections:", headings)
print("Tables restored:", table_count)
print("Images restored:", len(images))
print("Formula blocks:", formula_count // 2)

assert headings == [
    str(i) for i in range(1, 17)
], headings

assert len(images) == 13, images

assert len(set(images)) == 13

assert formula_count % 2 == 0

for image in images:

    assert (DOC / image).is_file(), image

for required in [
    "Sweep 12",
    "7101",
    "24.71%",
    "3,210",
]:

    assert required in content, required

path.write_text(
    content,
    encoding="utf-8"
)

print()
print("Backup:", backup.name)
print("Output:", path.name)
print("Original lines:", len(lines))
print("Repaired lines:", len(content.splitlines()))

print("SHA256:", hashlib.sha256(
    path.read_bytes()
).hexdigest())

print("README format repair: PASS")
print("Original backup preserved: YES")
print("Experiment CSV modified: NO")
print("Figures modified: NO")

