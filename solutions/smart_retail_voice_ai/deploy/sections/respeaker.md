### Configure Microphone Array

1. Connect reSpeaker XVF3800 via USB to **your computer** (not reRouter)
2. Clone repo: `git clone https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git`
3. Navigate to your OS folder and run:
   ```bash
   sudo ./xvf_host clear_configuration 1
   sudo ./xvf_host audio_mgr_op_r 8 0
   sudo ./xvf_host save_configuration 1
   ```
4. Disconnect from computer, connect reSpeaker to **reRouter USB port**
