## Deploy Voice Services

This step automatically deploys three Docker containers to the reRouter:

| Service | Description |
|---------|-------------|
| sensecraft-asr-server | Local ASR (Automatic Speech Recognition) engine |
| sensecraft-voice-client | Voice capture and web interface |
| watchtower | Automatic container updates |

### Prerequisites

Before proceeding, ensure:

- reSpeaker XVF3800 is connected to reRouter USB port
- reRouter has internet access (verify with `ping google.com` or `ping openwrt.org` in SSH)

### Automatic Deployment

Enter the SSH credentials below. The deployment will:

1. Connect to reRouter via SSH
2. Create necessary data directories
3. Download ASR models (~500MB)
4. Pull Docker images
5. Start all services

### Model Download

The ASR model package is approximately 500MB. Download time depends on your network speed.

### Verify Deployment

After deployment, check container status via SSH:

```bash
docker ps
```

All three containers should show `Status: Up`.

### Access Web Interface

Navigate to http://192.168.49.1:8090 to access the edge client interface for:

- Real-time ASR transcription
- Voiceprint recognition
- Device configuration
