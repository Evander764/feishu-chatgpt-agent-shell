# Feishu ChatGPT Agent Shell

把 ChatGPT 网页项目套到飞书机器人后面运行的本地 Mac 模板。

这个项目面向想做“飞书 Agent / GPT 套壳 / 图片生成机器人”的开发者：

1. 首次运行时，用隔离 Chrome profile 登录 ChatGPT 网页端，创建并置顶一个 ChatGPT Project。
2. 日常使用时，用户在飞书里给机器人发需求。
3. 本地服务在 Mac 上打开配置好的 ChatGPT Project URL，提交用户需求，等待网页生成图片。
4. 图片出现后，本地下载、归档、打包，再通过飞书应用 API 回传到来源会话。
5. 可选接入支持多模态的 API，用于提示词规划、审美记忆、选图反馈分析。

> 合规边界：ChatGPT 网页输出自动下载默认关闭。只有在你确认自己有权对自己的 ChatGPT 网页会话做程序化提取时，才把 `CHATGPT_WEB_EXTRACTION_AUTHORIZED=true` 打开。生产级自动生图更推荐走官方图片/多模态 API。参考：[OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use/) 和 [OpenAI Image API Guide](https://developers.openai.com/api/docs/guides/image-generation)。

## Features

- Feishu/Lark bot HTTP callback endpoint: `/lark/events`
- ChatGPT Project web wrapper with isolated Chrome profile
- `visible` login mode, `silent` off-screen mode, `headless` mode
- One profile lock to prevent concurrent browser-session corruption
- Prompt groups separated from images per group
- Local artifact storage and ZIP packaging
- Feishu image upload and one-card gallery response
- Aesthetic memory for “第 N 张最好” style feedback
- OpenAI-compatible planner and multimodal vision interfaces
- Health endpoint that reports configuration without exposing secrets

## Repository Layout

```text
src/feishu_chatgpt_agent_shell/
  config.py          env parser and settings
  browser_runner.py  isolated Chrome/CDP runner
  planner.py         prompt group planner, OpenAI-compatible fallback
  memory.py          lightweight aesthetic memory
  artifacts.py       task archive and zip packaging
  lark.py            Feishu token, upload, card send, event parsing
  service.py         end-to-end task orchestration
  main.py            FastAPI app
  cli.py             setup and run commands
docs/
  quickstart.md
  feishu-open-platform.md
  chatgpt-project.md
  architecture.md
  compliance-and-api.md
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env`:

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
CHATGPT_PROJECT_URL=https://chatgpt.com/g/xxx/project
CHATGPT_WEB_EXTRACTION_AUTHORIZED=true
```

Open the isolated browser profile for first login:

```bash
feishu-chatgpt-agent setup-chatgpt
```

Run the local server:

```bash
feishu-chatgpt-agent run
```

Open:

```text
http://127.0.0.1:18080/health
```

For Feishu HTTP event callbacks, expose the local service with a tunnel, then set:

```text
https://your-public-tunnel.example.com/lark/events
```

as the Feishu event callback URL.

## Feishu Setup Summary

1. Go to [Feishu Open Platform](https://open.feishu.cn/app).
2. Create an enterprise self-built app.
3. Enable the `机器人` capability.
4. Copy App ID, App Secret, and Verification Token into `.env`.
5. Configure event callback `/lark/events`.
6. Subscribe to message receive events.
7. Grant message and image permissions.
8. Create and publish a version.
9. Add the bot to a test chat and send a text prompt.

Detailed guide: [docs/feishu-open-platform.md](docs/feishu-open-platform.md)

## ChatGPT Project Setup Summary

1. Run `feishu-chatgpt-agent setup-chatgpt`.
2. Log in to ChatGPT in the opened isolated Chrome profile.
3. Create a new ChatGPT Project and pin it.
4. Copy the Project URL into `.env` as `CHATGPT_PROJECT_URL`.
5. Use `CHATGPT_RUN_MODE=silent` for daily work.

Detailed guide: [docs/chatgpt-project.md](docs/chatgpt-project.md)

## API Recommendation

This template keeps the ChatGPT web wrapper because many developers want to prototype around a project-scoped ChatGPT workflow. For commercial or unattended production usage, prefer official APIs:

- Use a multimodal text model for prompt planning and aesthetic feedback.
- Use an official image generation/editing API for final images.
- Keep ChatGPT web mode only for preview or explicitly authorized personal workflows.

See [docs/compliance-and-api.md](docs/compliance-and-api.md).

## Development

```bash
pytest -q
ruff check .
```

## License

MIT

