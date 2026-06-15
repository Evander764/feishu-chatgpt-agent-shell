# Feishu Open Platform Setup

Primary docs:

- Custom bot overview: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot?lang=zh-CN
- Developer console: https://open.feishu.cn/app

## Create App

1. Open `https://open.feishu.cn/app`.
2. Click `创建企业自建应用`.
3. Fill app name and description.
4. Keep the default icon or upload your own icon.
5. Create the app.

## Enable Bot Capability

1. Enter the app.
2. Open `添加应用能力`.
3. Add `机器人`.
4. Confirm that the sidebar shows `机器人`.

## Credentials

Open `凭证与基础信息` and copy:

- App ID
- App Secret

Put them in `.env`:

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_DOMAIN=https://open.feishu.cn
```

Do not commit `.env`.

## Event Callback

For local development you need an HTTPS tunnel. Configure:

```text
POST https://your-public-url/lark/events
```

The endpoint supports Feishu URL verification challenge.

Set your verification token in `.env`:

```env
FEISHU_VERIFICATION_TOKEN=xxx
```

## Event Subscription

Subscribe to message-received events so the bot receives user text.

For v1 this template supports ordinary text messages. Image feedback such as `第 2 张最好` can be added as a follow-up handler using `memory.record_selection_feedback`.

## Permissions

Grant the app permissions needed to:

- receive messages
- send messages as bot
- upload message images

After permissions/callback changes, create and publish a new app version.

## External Chats

Some Feishu tenants disable:

- allowing bots in external groups
- allowing external users to DM bots

If those switches are disabled in the publish page, it is a tenant/platform policy issue, not a local code issue.

