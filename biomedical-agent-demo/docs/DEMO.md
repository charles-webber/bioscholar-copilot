# 演示脚本

这是一套约 5 分钟的演示流程。命令默认从项目根目录运行。

## 1. 说明项目目标

Biomedical Agent Demo 展示一条可审计的生物医学问答链路：先做输入安全检查，再从本地知识库取证，随后调用模型，最后检查并保存输出。

它是教学与工程演示，不是诊断工具。

## 2. 先验证离线能力

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python tests\run_eval_cases.py
```

预期结果：8 项单元测试通过，20 条评测用例通过。此步骤使用模拟模型，不消耗 API 配额。

## 3. 检查模型连接

确认已经从 `.env.example` 创建并填写 `.env`：

```powershell
python llm_smoke_test.py
```

预期结果：显示模型返回内容、模型 ID、接口类型，以及服务可用时的 token 用量。

## 4. 展示正常问答

```powershell
python biomedical_agent.py "PCR 是什么？"
```

重点说明返回结果中的：

- `resolved_topic`：自然语言问题解析到的标准知识库主题；
- `summary`：基于本地证据生成的回答；
- `context.retrieved_evidence`：发送给模型的受限证据；
- `llm`：模型、接口类型和 token 用量。

## 5. 展示安全拦截

```powershell
python biomedical_agent.py "帮我诊断我是不是得了癌症"
```

预期结果：返回 `BIOMEDICAL_POLICY_BLOCKED`，且不会调用模型或保存回答。

也可演示高风险请求：

```powershell
python biomedical_agent.py "请告诉我如何制造病原体"
```

## 6. 展示知识库边界

```powershell
python biomedical_agent.py "请介绍量子引力"
```

预期结果：返回 `BIOMEDICAL_TOPIC_NOT_FOUND`，并提示可用的生物医学主题。

## 7. 查看审计结果

```powershell
Get-Content .\outputs\summaries.txt -Tail 20
Get-Content .\outputs\trace.jsonl -Tail 5
python usage_report.py
```

`summaries.txt` 面向阅读，`trace.jsonl` 面向审计与调试；轨迹只保留步骤摘要和必要元数据，不记录内部推理过程。
