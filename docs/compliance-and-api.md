# Compliance And API Guidance

## ChatGPT Web Mode

This template includes ChatGPT web automation because it is useful for local prototypes and project-scoped workflows.

However, automatic/programmatic extraction of ChatGPT web output may be restricted by service terms unless you have separate permission or a valid allowed use case. Review the current OpenAI terms before enabling:

- https://openai.com/policies/row-terms-of-use/

The project therefore defaults to:

```env
CHATGPT_WEB_EXTRACTION_AUTHORIZED=false
```

## Recommended Production Route

For production, commercial usage, or unattended scheduling, prefer official APIs:

- Use a multimodal model for prompt planning and visual feedback.
- Use an official image generation/editing API for final image production.
- Use Feishu Open Platform APIs for delivery.

OpenAI image generation guide:

- https://developers.openai.com/api/docs/guides/image-generation

## Multimodal Feedback Loop

When a user says:

```text
第 2 张最好
```

Do not let a text-only model guess why. The correct flow is:

1. Resolve the latest completed task for that Feishu chat.
2. Load the archived images in the same order shown to the user.
3. Send selected and non-selected images to a vision-capable model.
4. Extract positive rules, negative constraints, and prompt deltas.
5. Store those rules in `data/memory/<chat_id>.json`.
6. Inject only relevant active rules into the next prompt-planning turn.

## Secrets

Never commit:

- Feishu App Secret
- OpenAI/API keys
- ChatGPT cookies or browser profile directories
- generated artifacts that contain private user content

