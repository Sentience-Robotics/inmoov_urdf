# Copyright 2025 Sentience Robotics Team
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import shutil
import subprocess
from typing import Sequence

import pytest


def run_xacro(args: Sequence[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run xacro via standalone binary or ``ros2 run xacro xacro``.

    Skips the calling test (instead of erroring) when neither is on PATH —
    lets host-side ``pytest`` runs pass with only the pure-Python tests, while
    Docker / colcon runs exercise the full xacro expansion.
    """
    if shutil.which("xacro"):
        cmd = ["xacro", *args]
    elif shutil.which("ros2"):
        cmd = ["ros2", "run", "xacro", "xacro", *args]
    else:
        pytest.skip("xacro not on PATH (run inside lucy_ros2:humble image)")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
