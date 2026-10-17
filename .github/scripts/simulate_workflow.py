"""Simulate an asynchronous workflow with delay and controlled failures."""
import os
from pathlib import Path
import secrets
import time


def main():
    try:
        seconds = int(os.environ.get("WAIT_SECONDS", "15"))
        rate = int(os.environ.get("FAILURE_RATE", "30"))
        attempt = int(os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
        if not 0 <= seconds <= 600 or not 0 <= rate <= 100 or attempt < 1:
            raise ValueError("wait_seconds must be 0..600; failure_rate 0..100; attempt >= 1")
        mode = os.environ.get("RESULT_MODE", "random")
        if mode not in {"random", "success", "failure", "fail_first_attempt"}:
            raise ValueError("Unsupported result_mode")
    except ValueError as error:
        print(f"Invalid input: {error}", flush=True)
        return 2

    label = os.environ.get("WORKFLOW_LABEL", "test")
    print(f"Workflow {label}: waiting {seconds}s, attempt={attempt}, mode={mode}", flush=True)
    remaining = seconds
    while remaining:
        tick = min(5, remaining)
        time.sleep(tick)
        remaining -= tick
        print(f"Workflow {label}: {remaining}s remaining", flush=True)

    roll = secrets.randbelow(100)
    failed = mode == "failure" or (mode == "random" and roll < rate) or (mode == "fail_first_attempt" and attempt == 1)
    result = "failure" if failed else "success"
    print(f"Workflow {label}: result={result}, roll={roll}, failure_rate={rate}%, attempt={attempt}", flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"## Simulated workflow {label}\n\nResult: **{result}**\n\nWait: {seconds}s; attempt: {attempt}; mode: {mode}; failure rate: {rate}%.\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
