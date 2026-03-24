import asyncio
import json
import os
import time
from typing import Dict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
RESULTS_FILE = os.path.join(BASE_DIR, "results.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config", "config.yaml")

async def mock_llm_call(file_path: str, branch_name: str):
    await asyncio.sleep(0.5)
    # return a fake parsed result
    return {"branch": branch_name, "file": os.path.basename(file_path), "parsed": {"text": "example"}}

def read_tasks() -> Dict:
    if not os.path.exists(TASKS_FILE):
        return {}
    with open(TASKS_FILE, "r") as f:
        return json.load(f)

def write_tasks(tasks: Dict):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)

def append_result(result: Dict):
    results = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            try:
                results = json.load(f)
            except Exception:
                results = []
    results.append(result)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

async def run_branch(task_id: str, file_path: str, branch_conf: Dict):
    branch = branch_conf.get("name")
    retries = branch_conf.get("retries", 0)
    attempts = 0
    while True:
        attempts += 1
        try:
            resp = await mock_llm_call(file_path, branch)
            # naive validation: ensure resp contains parsed
            if "parsed" in resp:
                append_result({"task_id": task_id, "branch": branch, "status": "SUCCESS", "output": resp, "attempts": attempts, "ts": int(time.time())})
                return
            else:
                raise ValueError("validation failed")
        except Exception as e:
            if attempts > retries:
                append_result({"task_id": task_id, "branch": branch, "status": "FAILED", "error": str(e), "attempts": attempts, "ts": int(time.time())})
                return
            await asyncio.sleep(0.2)

async def dispatch_task(task_id: str):
    tasks = read_tasks()
    if task_id not in tasks:
        return
    file_path = tasks[task_id]["file"]
    # load config inline (simple)
    try:
        import yaml
        with open(CONFIG_FILE, "r") as f:
            conf = yaml.safe_load(f)
    except Exception:
        conf = {"branches": []}

    branches = conf.get("branches", [])
    tasks[task_id]["status"] = "PROCESSING"
    write_tasks(tasks)

    branch_tasks = [run_branch(task_id, file_path, b) for b in branches]
    if branch_tasks:
        await asyncio.gather(*branch_tasks)

    tasks = read_tasks()
    tasks[task_id]["status"] = "DONE"
    write_tasks(tasks)
