# Hermes 本地变更说明

本文记录 `fix/custom-provider-reasoning` 分支相对
`NousResearch/hermes-agent@057dcdf236` 的本地功能提交。变更集中在命名自定义
Provider 的推理参数格式、请求配置应用和 Desktop 会话身份恢复。

## 提交概览

| 提交 | 类型 | 目的 |
| --- | --- | --- |
| `d505305e88` | 功能修复 | 为自定义 Provider 增加可配置的推理参数格式 |
| `56f5ecdaa2` | 诊断与文档 | 明确提示 `reasoning_format: none` 会抑制显式关闭推理 |
| `d957c176d4` | 功能修复 | 让命名自定义 Provider 实际使用 custom 请求配置 |
| `5faa5b7952` | Desktop 修复 | 保留命名 Provider 身份，使旧会话档位修改命中实时会话 |
| 本文档提交 | 文档 | 汇总上述提交的原因、行为、兼容性和验证结果，不修改运行时代码 |

## `d505305e88`：自定义 Provider 推理参数格式

提交标题：`fix(custom): add providers.<name>.reasoning_format to control the reasoning wire shape`

### 问题

不同 OpenAI 兼容端点接收推理参数的方式并不统一：

- 部分端点接收顶层 `reasoning_effort`。
- 部分网关接收 `reasoning: { enabled, effort }` 对象。
- 严格代理会拒绝任何未知推理字段。

原实现固定发送顶层 `reasoning_effort`，导致使用其他格式的端点返回 HTTP 400。

### 变更

在 `providers.<name>` 中增加 `reasoning_format`：

- `top_level`：发送顶层 `reasoning_effort`，也是兼容旧配置的默认值。
- `reasoning_object`：发送嵌套 `reasoning` 对象。
- `none`：不发送推理字段，由上游端点采用自身默认行为。

配置示例：

```yaml
providers:
  command:
    api: http://127.0.0.1:20128/v1
    reasoning_format: top_level
```

同时补充配置校验、示例配置、Provider 文档和行为测试。未配置该字段时保持原有
`top_level` 行为，不改变已有用户的请求格式。

### 主要文件

- `plugins/model-providers/custom/__init__.py`
- `hermes_cli/config.py`
- `cli-config.yaml.example`
- `website/docs/integrations/providers.md`
- `tests/hermes_cli/test_custom_provider_reasoning_format.py`
- `tests/plugins/model_providers/test_custom_profile.py`

## `56f5ecdaa2`：抑制显式关闭推理时给出提示

提交标题：`docs(custom): surface suppressed reasoning disable intent`

### 问题

当配置为 `reasoning_format: none` 且用户选择关闭推理时，Hermes 必须省略所有
推理字段。此时 Hermes 无法要求上游明确关闭推理，上游可能仍按自己的默认值启用
推理。此前这个限制没有任何运行时提示。

### 变更

- 在省略显式关闭请求时记录 warning。
- 文档说明相同路由出现多条兼容配置时，首个有效 `reasoning_format` 生效。
- 增加 warning 行为测试。

### 主要文件

- `plugins/model-providers/custom/__init__.py`
- `hermes_cli/config.py`
- `tests/plugins/model_providers/test_custom_profile.py`

## `d957c176d4`：命名 Provider 应用 custom 请求配置

提交标题：`fix(custom): apply request profile to named providers`

### 问题

通过 `providers.command` 这类名称配置的自定义端点，其运行时 provider 名称是
`command`，而请求构造器只会直接查找同名内置 ProviderProfile。查找失败后会跳过
custom profile，导致上一提交配置的 `reasoning_format` 没有进入实际请求。

### 变更

- 增加统一的请求 Profile 解析：先查内置 profile，再识别命名自定义 Provider。
- 命名自定义 Provider 命中后复用现有 `custom` profile。
- 正常请求和达到最大迭代次数后的收尾请求共用同一解析逻辑。
- 增加真实临时配置测试，确认 `providers.command` 解析为 custom profile。

### 主要文件

- `agent/chat_completion_helpers.py`
- `tests/agent/test_named_custom_provider_profile.py`

## `5faa5b7952`：修复 Desktop 旧会话档位不生效

提交标题：`fix(desktop): preserve named provider identity in sessions`

### 问题

命名自定义 Provider 在代理对象内部会解析成裸 `custom`。Desktop 的模型目录使用
`command` 或 `custom:command` 识别该 Provider。旧会话的 `session.info` 返回裸
`custom` 后，Desktop 会把当前模型行误判为非活动行：修改 `Max` 等推理档位只会保存
为新会话预设，不会调用当前会话的 `config.set`。因此新会话可以生效，旧会话仍发送
原来的 `medium`。

### 变更

- `session.info` 在报告命名自定义 Provider 前，根据 endpoint 和模型恢复规范身份。
- 当前本机配置现在报告 `custom:command`，不再报告裸 `custom`。
- Desktop 无需修改即可把模型行识别为当前活动模型，并将档位更新发送给实时会话。
- 增加会话信息身份恢复测试。

### 主要文件

- `tui_gateway/server.py`
- `tests/tui_gateway/test_custom_provider_session_persistence.py`

## 验证

在 Windows 本机通过项目标准测试包装脚本执行：

```text
tests/hermes_cli/test_custom_provider_reasoning_format.py
tests/plugins/model_providers/test_custom_profile.py
tests/agent/test_named_custom_provider_profile.py
tests/tui_gateway/test_custom_provider_session_persistence.py
tests/tui_gateway/test_reasoning_session_scope.py
```

结果：`5 files, 68 tests passed, 0 failed`。

实际链路验证：

- 本机 Hermes CLI 显式选择 `max` 后，9Router 记录的 `received` 和 `forwarded`
  均为 `reasoning_effort: max`。
- 修复会话身份后，Desktop 旧会话重新选择 `Max` 可以正确更新实时会话。

## 更新与维护

这些提交位于独立分支，不修改上游 `main`。同步上游更新时，先检查上述功能是否已经
被官方实现；若已实现，应删除或跳过对应提交，避免重复逻辑。若仍需保留，可按本表
顺序重新应用提交。
