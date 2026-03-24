import asyncio
import json
import os
import time
from typing import Dict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
RESULTS_FILE = os.path.join(BASE_DIR, "results.json")
MANUAL_QUEUE_FILE = os.path.join(BASE_DIR, "manual_queue.json")
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


def read_results():
    if not os.path.exists(RESULTS_FILE):
        return []
    with open(RESULTS_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def enqueue_manual(item: Dict):
    queue = []
    if os.path.exists(MANUAL_QUEUE_FILE):
        with open(MANUAL_QUEUE_FILE, "r") as f:
            try:
                queue = json.load(f)
            except Exception:
                queue = []
    item_id = str(int(time.time() * 1000))
    item["id"] = item_id
    queue.append(item)
    with open(MANUAL_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)
    return item_id


def read_manual_queue(limit: int = 100):
    if not os.path.exists(MANUAL_QUEUE_FILE):
        return []
    with open(MANUAL_QUEUE_FILE, "r") as f:
        try:
            queue = json.load(f)
        except Exception:
            queue = []
    return queue[:limit]


def resolve_manual_item(item_id: str, resolution: Dict):
    if not os.path.exists(MANUAL_QUEUE_FILE):
        return False
    with open(MANUAL_QUEUE_FILE, "r") as f:
        try:
            queue = json.load(f)
        except Exception:
            queue = []
    new_q = [it for it in queue if it.get("id") != item_id]
    found = len(queue) != len(new_q)
    with open(MANUAL_QUEUE_FILE, "w") as f:
        json.dump(new_q, f, indent=2)
    if found:
        # write resolution back to results
        append_result({**resolution, "resolved_from_manual": item_id, "ts": int(time.time())})
    return found

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
                error_item = {"task_id": task_id, "branch": branch, "status": "FAILED", "error": str(e), "attempts": attempts, "ts": int(time.time())}
                append_result(error_item)
                # enqueue for manual review
                enqueue_manual(error_item)
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
