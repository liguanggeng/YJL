"""简单的集成测试脚本：创建任务、调用 dispatch 并打印结果/人工队列/任务文件。
运行方式：`python tests/run_dispatch.py`
"""
import os
import json
import uuid
import asyncio
from worker import processor


BASE = os.path.dirname(os.path.dirname(__file__))
UPLOADS = os.path.join(BASE, 'uploads')
os.makedirs(UPLOADS, exist_ok=True)


def create_task():
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOADS, f"{task_id}_test.txt")
    with open(file_path, 'w') as f:
        f.write('hello world')
    tasks_file = os.path.join(BASE, 'tasks.json')
    tasks = {}
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r') as f:
                tasks = json.load(f)
        except Exception:
            tasks = {}
    tasks[task_id] = {'status': 'RECEIVED', 'file': file_path}
    with open(tasks_file, 'w') as f:
        json.dump(tasks, f, indent=2)
    return task_id


async def run(task_id: str):
    await processor.dispatch_task(task_id)


def print_outputs():
    BASE = os.path.dirname(os.path.dirname(__file__))
    for name in ('results.json', 'manual_queue.json', 'tasks.json'):
        path = os.path.join(BASE, name)
        print('\n---', name, '---')
        if os.path.exists(path):
            print(open(path).read())
        else:
            print('not found')


def main():
    task_id = create_task()
    print('created task', task_id)
    asyncio.run(run(task_id))
    print_outputs()


if __name__ == '__main__':
    main()
