# 等待、偶发失败与重试测试

四个 workflow 可以分别手动或通过 API 触发，默认等待 15 秒，再以 30% 概率失败：

| 节点 | workflow 文件 |
| --- | --- |
| A | `test_workflow_a.yml` |
| B | `test_workflow_b.yml` |
| C | `test_workflow_c.yml` |
| D | `test_workflow_d.yml` |

共同执行脚本为 `.github/scripts/simulate_workflow.py`，不调用业务 API、不构建镜像。

## 参数

- `wait_seconds`：整数 0..600。
- `failure_rate`：整数 0..100，仅 random 模式使用。
- `result_mode`：`random` 随机失败；`success` 固定成功；`failure` 固定失败；`fail_first_attempt` 首次失败，GitHub 原运行重跑后成功。
- `correlation_id`：可选测试标识，显示在运行标题中；真实运行关联仍应使用 dispatch 返回的 run_id。

测试文件目前只创建在本地，需自行提交、推送到 GitHub。workflow_dispatch 工作流要先存在于默认分支，GitHub 才能正常提供手动触发入口。之后进入 Actions，选择 Test Workflow A/B/C/D，点击 Run workflow。

## DolphinScheduler 节点调用

上传并选择公共资源 `github_actions.py`。下面代码用于 Python 节点，`repo` 替换成当前仓库的 owner/repo，`ref` 选择已提交测试文件的分支：

```python
import os
import sys
sys.path.insert(0, os.getcwd())
from github_actions import GitHubActionsClient

client = GitHubActionsClient(
    token=os.environ.get("GITHUB_TOKEN"),
    repo="你的账号/workflow_learn",
    poll_interval=5,
    timeout=1800,
    max_retries=1,
    retry_interval=5,
    retry_mode="failed_jobs",
    log=lambda message: print(message, flush=True),
)
record = client.dispatch(
    workflow="test_workflow_a.yml",
    ref="main",
    inputs={
        "wait_seconds": 15,
        "failure_rate": 30,
        "result_mode": "fail_first_attempt",
        "correlation_id": "ds-test-a",
    },
)
print(record["html_url"], flush=True)
result = client.wait(record)
if result["conclusion"] != "success":
    raise RuntimeError(f"Workflow failed: {result['conclusion']}")
```

节点 B/C/D 分别修改 workflow 文件名即可。依赖连线在 DolphinScheduler 中配置，例如 A → B/C → D；这四个 GitHub workflow 自身互不触发。

## 建议实验顺序

1. success + 等待 15 秒：确认节点一直等待到 GitHub 成功。
2. failure + max_retries=0：确认节点失败、下游不执行。
3. fail_first_attempt + max_retries=1：确认相同 run_id 的 run_attempt 从 1 变为 2，最终成功。
4. random + failure_rate=30：测试不确定结果，重跑可能继续失败。

fail_first_attempt 依赖 GitHub 重跑原运行的 attempt 递增。如果重新 dispatch，属于新的 run，第一次仍会失败。排队和 runner 初始化耗时不包含在 wait_seconds 内，实际运行时间可能更长。GitHub 托管 runner 按账号和仓库的 Actions 配额计费/扣减用量。
