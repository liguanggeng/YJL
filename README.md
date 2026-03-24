# 文档摄取系统 示例项目

快速启动：

1. 建议创建并激活虚拟环境：

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

2. 运行 API 服务（开发模式）：

```bash
uvicorn app.main:app --reload --port 8000
```

3. 上传文件测试：

```bash
curl -F "file=@/path/to/file.pdf" http://localhost:8000/upload
```

说明：这是最小可运行示例，包含上传 API、任务调度、并行分支 runner（mock LLM）。用于快速验证处理流程。
# YJL
異常連処理システム
