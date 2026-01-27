# Local LLM & TTS Deployment

Deploy Qwen3-8B LLM and TTS service on the reComputer J4012 (Jetson Orin NX 16GB) for fully local AI inference.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Ollama (Qwen3-8B) | 11434 | LLM inference with OpenAI-compatible API |

## Hardware Requirements

- reComputer J4012 (Jetson Orin NX 16GB)
- JetPack 6.x installed
- NVIDIA container runtime configured
- At least 15GB free disk space
- Network connection to R1100

## Model Details

| Item | Specification |
|------|---------------|
| Model | Qwen3-8B (4-bit quantized) |
| VRAM | ~5GB model + 1-2GB KV cache |
| Speed | ~13 tokens/sec generation |
| Variants | `qwen3:8b` (reasoning) / `qwen3:8b-chat` (dialog) |

## After Deployment

1. LLM API available at `http://<j4012-ip>:11434/v1/chat/completions`
2. Update xiaozhi-server config to point LLM/TTS to J4012's IP address
3. First startup downloads the model (~5GB), subsequent starts are fast
4. Use `qwen3:8b-chat` variant for voice dialog (no reasoning tokens)
