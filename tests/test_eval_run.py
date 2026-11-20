import subprocess
import sys
from pathlib import Path


def test_scripted_evaluation_preserves_existing_result(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "existing.json"
    output.write_text("original evidence", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(root / "eval" / "run.py"),
            "--archive",
            str(tmp_path / "unused.zip"),
            "--output",
            str(output),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "output already exists" in result.stderr
    assert output.read_text(encoding="utf-8") == "original evidence"
