## What This Solution Does

Want to use AI chatbots on WeChat, Telegram, or Discord — but don't want to juggle multiple integrations or worry about data privacy? OpenClaw connects 20+ messaging apps to any AI model through one simple gateway, running entirely on your own reComputer device.

## Core Value

| Benefit | Details |
|---------|---------|
| One gateway, 20+ platforms | WeChat, Telegram, Discord, Slack, DingTalk, Feishu, and more — manage all from one place |
| Switch AI models freely | Use OpenAI, DeepSeek, or any compatible AI service — switch anytime without reconfiguration |
| Your data stays with you | Everything runs on your own device — no conversations sent to third-party services |
| Optional local AI | Use device GPU to run AI models locally — fully offline conversations with zero privacy concerns |

## Use Cases

| Scenario | How It Works |
|----------|-------------|
| Personal AI assistant | Connect your WeChat or Telegram to ChatGPT/DeepSeek — chat with AI right in your messaging app |
| Team chatbot | Set up a shared AI assistant in your Slack or Discord workspace for the whole team |
| Privacy-first AI | Run AI models locally on your device so conversations never leave your network |
| Edge AI on Jetson | Deploy on reComputer Jetson for GPU-accelerated local AI with messaging integration |

## What You Need

### Hardware

| Device | Notes | Required |
|--------|-------|----------|
| reComputer R1100 / R2000 | Runs OpenClaw gateway services | ✓ Either one |
| reComputer Jetson Series | GPU-accelerated local AI model | ✓ Either one |

### Network

- Internet access needed for first-time setup (downloading container images)
- After setup, can run fully offline with local AI models (no cloud AI needed)
- For Jetson: NVIDIA container runtime must be pre-configured
