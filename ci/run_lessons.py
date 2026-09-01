"""Run every lesson check against the mock server.

This is the same script a learner can run to prove the whole course still
works on their machine, and the one CI runs on every push. Having one script
for both means CI cannot drift away from what learners experience.
"""
import os
import subprocess
import sys
from pathlib import Path

from agentpath.testing.mock_server import serve

ROOT = Path(__file__).resolve().parents[1]


def main():
    base_url, shutdown = serve()
    environment = dict(os.environ)
    environment["AGENTPATH_BASE_URL"] = f"{base_url}/v1"
    environment["AGENTPATH_MODEL"] = "mock"
    environment["AGENTPATH_API_KEY"] = "mock-key"
    environment["AGENTPATH_AUTO_APPROVE"] = "1"

    failures = []
    lessons = sorted(p for p in (ROOT / "lessons").iterdir() if (p / "check.py").exists())
    for lesson in lessons:
        print(f"\n=== {lesson.name} ===", flush=True)
        completed = subprocess.run(
            [sys.executable, "check.py"], cwd=lesson, env=environment, timeout=120
        )
        if completed.returncode != 0:
            failures.append(lesson.name)

    shutdown()

    print("\n" + "=" * 40)
    if failures:
        print(f"FAILED {len(failures)} of {len(lessons)} lessons")
        for name in failures:
            print(f"  {name}")
        return 1
    print(f"All {len(lessons)} lesson checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
