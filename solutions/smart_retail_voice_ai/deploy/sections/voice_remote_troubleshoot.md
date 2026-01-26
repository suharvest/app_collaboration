### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection refused | Make sure the cable is plugged into the LAN port and the IP is correct |
| Authentication failed | OpenWrt default password is empty, just press Enter |
| Image download timeout | Check the WAN port network connection, make sure you can access the internet |
| Container startup failed | SSH in and run `docker logs` to view error messages |
| Microphone not found | Run `arecord -l` to verify reSpeaker is recognized |
