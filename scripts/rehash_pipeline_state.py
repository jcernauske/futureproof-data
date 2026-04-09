"""Rehash pipeline state output files that have been modified by subsequent pipeline runs."""

import hashlib
import json
from pathlib import Path


def hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def main() -> None:
    state_dir = Path("governance/pipeline-state")
    for pf in sorted(state_dir.glob("*-pipeline.json")):
        state = json.loads(pf.read_text())
        modified = False
        for step_name, step_info in state.get("steps", {}).items():
            output = step_info.get("output", "")
            if output and Path(output).exists():
                current = hash_file(Path(output))
                recorded = step_info.get("output_hash", "")
                if recorded and current != recorded:
                    print(f"{pf.name}: {step_name} rehash {output}")
                    step_info["output_hash"] = current
                    modified = True
        if modified:
            pf.write_text(json.dumps(state, indent=2) + "\n")
            print(f"  Updated {pf.name}")


if __name__ == "__main__":
    main()
