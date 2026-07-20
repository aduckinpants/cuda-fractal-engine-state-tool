from __future__ import annotations

import csv
import io
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence


@dataclass
class ProcessResult:
    command: list[str]
    cwd: str
    pid: int
    exit_code: Optional[int]
    timed_out: bool
    elapsed_seconds: float
    stdout: str
    stderr: str
    observed_process_tree: list[dict[str, str]]


def _powershell(command: str) -> list[str]:
    return [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]


def file_version(path: Path) -> str:
    script = (
        "$item = Get-Item -LiteralPath \"%s\";"
        "$version = $item.VersionInfo.FileVersion;"
        "if ($version) { $version }"
    ) % str(path)
    completed = subprocess.run(_powershell(script), capture_output=True, text=True, check=False)
    return completed.stdout.strip()


def process_exists(pid: int) -> bool:
    completed = subprocess.run(
        _powershell(f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; if ($p) {{ 'True' }} else {{ 'False' }}"),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip().lower() == "true"


def find_processes_by_name(image_name: str) -> list[dict[str, str]]:
    completed = subprocess.run(
        _powershell(
            "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq '%s' };"
            "$procs | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Csv -NoTypeInformation"
            % image_name
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(completed.stdout))
    for row in reader:
        rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def kill_process_tree(pid: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )


def list_process_tree(root_pid: int) -> list[dict[str, str]]:
    script = rf"""
function Get-Children([int]$Pid) {{
  $children = Get-CimInstance Win32_Process | Where-Object {{ $_.ParentProcessId -eq $Pid }}
  foreach ($child in $children) {{
    [PSCustomObject]@{{
      ProcessId = [string]$child.ProcessId
      ParentProcessId = [string]$child.ParentProcessId
      Name = [string]$child.Name
      CommandLine = [string]$child.CommandLine
    }}
    Get-Children -Pid $child.ProcessId
  }}
}}
$root = Get-CimInstance Win32_Process | Where-Object {{ $_.ProcessId -eq {root_pid} }}
if ($root) {{
  [PSCustomObject]@{{
    ProcessId = [string]$root.ProcessId
    ParentProcessId = [string]$root.ParentProcessId
    Name = [string]$root.Name
    CommandLine = [string]$root.CommandLine
  }}
  Get-Children -Pid {root_pid}
}}
"""
    completed = subprocess.run(_powershell(script), capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(completed.stdout), fieldnames=["ProcessId", "ParentProcessId", "Name", "CommandLine"])
    for row in reader:
        if not any(row.values()):
            continue
        rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def run_command(
    command: Sequence[str],
    cwd: Path,
    timeout_seconds: Optional[float] = None,
    env: Optional[Mapping[str, str]] = None,
) -> ProcessResult:
    start = time.monotonic()
    process = subprocess.Popen(
        list(command),
        cwd=str(cwd),
        env=dict(env) if env is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(0.05)
    observed_process_tree = list_process_tree(process.pid)
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        kill_process_tree(process.pid)
        stdout, stderr = process.communicate()
        timed_out = True
    elapsed = time.monotonic() - start
    return ProcessResult(
        command=list(command),
        cwd=str(cwd),
        pid=process.pid,
        exit_code=process.returncode,
        timed_out=timed_out,
        elapsed_seconds=elapsed,
        stdout=stdout,
        stderr=stderr,
        observed_process_tree=observed_process_tree,
    )
