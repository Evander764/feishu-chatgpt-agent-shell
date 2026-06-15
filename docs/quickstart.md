# Quick Start

## 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## 2. Create Feishu App

Open [Feishu Open Platform](https://open.feishu.cn/app), create an enterprise self-built app, and enable the bot capability.

Write credentials into `.env`:

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
```

## 3. Prepare ChatGPT Project

```bash
feishu-chatgpt-agent setup-chatgpt
```

In the isolated Chrome profile:

1. Log in to ChatGPT.
2. Create a new Project.
3. Pin the Project.
4. Copy the Project URL.

Then set:

```env
CHATGPT_PROJECT_URL=https://chatgpt.com/g/xxx/project
CHATGPT_WEB_EXTRACTION_AUTHORIZED=true
```

## 4. Run

```bash
feishu-chatgpt-agent run
```

Check:

```bash
curl http://127.0.0.1:18080/health
```

## 5. Expose Local Callback

Use any tunnel that provides HTTPS to your Mac, such as Cloudflare Tunnel or ngrok.

Set the public callback URL in Feishu:

```text
https://your-domain.example.com/lark/events
```

## 6. Test

Add the bot to a test chat and send:

```text
生成一张小红书风格的极简咖啡杯图片，自然光，高级干净，不要文字
```

The bot should return one gallery card with generated images.

