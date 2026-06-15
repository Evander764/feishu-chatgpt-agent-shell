# ChatGPT Project Setup

This template uses an isolated Chrome profile so the agent does not reuse or pollute your normal Chrome profile.

## First Login

```bash
feishu-chatgpt-agent setup-chatgpt
```

This opens Chrome with:

```text
--user-data-dir=<CHATGPT_BROWSER_PROFILE_DIR>
--remote-debugging-port=<CHATGPT_CDP_PORT>
```

In that browser:

1. Log in to ChatGPT.
2. Create a new Project.
3. Pin the Project.
4. Copy the Project URL.

Set:

```env
CHATGPT_PROJECT_URL=https://chatgpt.com/g/xxx/project
CHATGPT_PROJECT_NAME=Your project name
```

## Run Modes

```env
CHATGPT_RUN_MODE=visible
```

Use for first login and debugging.

```env
CHATGPT_RUN_MODE=silent
```

Use for daily work on macOS. It opens Chrome off-screen/minimized and restores the previous foreground app after launch and tab creation.

```env
CHATGPT_RUN_MODE=headless
```

No visible window. Some sites may not render authenticated inputs correctly in headless mode, so test before relying on it.

## Foreground Restore

By default, the template switches focus back to the app you were using after it opens ChatGPT:

```env
CHATGPT_RESTORE_FRONT_APP=true
```

This also applies to `setup-chatgpt`, so the login window can open without taking over your desktop. If you want the browser to stay in front while debugging, set it to `false`.

## Authorization Gate

Web output extraction is disabled by default:

```env
CHATGPT_WEB_EXTRACTION_AUTHORIZED=false
```

Only set it to `true` when you have confirmed you are allowed to programmatically download your own ChatGPT web output.
