"""Rollback is tested with fake commands, not Docker or network access."""

import os
import subprocess
from pathlib import Path


def test_failed_health_check_restores_previous_image(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    docker = fake_bin / "docker"
    docker.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "Path(os.environ['DOCKER_LOG']).open('a').write(' '.join(args) + '\\n')\n"
        "if args[:2] == ['container', 'inspect']:\n"
        "    print('old-image')\n"
    )
    docker.chmod(0o755)
    curl = fake_bin / "curl"
    curl.write_text("#!/bin/sh\nexit 1\n")
    curl.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "PATH": f"{fake_bin}:{env['PATH']}",
        "DOCKER_LOG": str(docker_log),
        "FACTCHAT_API_KEY": "fake-test-key",
        "HEALTH_RETRIES": "2",
        "HEALTH_DELAY_SECONDS": "0",
    })
    script = Path(__file__).resolve().parents[1] / "scripts" / "deploy_local.sh"
    result = subprocess.run(["bash", str(script), "new-image"], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    commands = docker_log.read_text().splitlines()
    runs = [line for line in commands if line.startswith("run ")]
    assert runs[0].endswith("new-image")
    assert runs[1].endswith("old-image")
    assert "fake-test-key" not in "\n".join(commands)
