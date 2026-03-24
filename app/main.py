import asyncio
import uuid
import os
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body

import worker.processor as processor

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")


def read_tasks():
    if not os.path.exists(TASKS_FILE):
        return {}
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def write_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    dest = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)

    tasks = read_tasks()
    tasks[task_id] = {"status": "RECEIVED", "file": dest}
    write_tasks(tasks)

    # enqueue dispatch in background
    asyncio.create_task(processor.dispatch_task(task_id))
    return {"task_id": task_id, "status": "received"}


@app.post("/tasks/{task_id}/dispatch")
async def dispatch(task_id: str):
    tasks = read_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="task not found")
    await processor.dispatch_task(task_id)
    return {"task_id": task_id, "status": "dispatched"}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    tasks = read_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="task not found")
    t = tasks[task_id].copy()
    # don't leak full path
    if "file" in t:
        t["file"] = os.path.basename(t["file"])
    return {"task_id": task_id, "task": t}


@app.get("/results")
async def get_results(task_id: Optional[str] = None):
    results = processor.read_results()
    if task_id:
        results = [r for r in results if r.get("task_id") == task_id]
    return {"count": len(results), "results": results}


@app.get("/manual-queue")
async def get_manual_queue(limit: int = 20):
    queue = processor.read_manual_queue(limit=limit)
    return {"count": len(queue), "items": queue}


@app.post("/manual-queue/{item_id}/resolve")
async def resolve_manual(item_id: str, resolution: dict = Body(...)):
    ok = processor.resolve_manual_item(item_id, resolution)
    if not ok:
        raise HTTPException(status_code=404, detail="manual item not found")
    return {"id": item_id, "status": "resolved"}

