"""
Stream Proxy Service - RTSP to HLS conversion

Uses FFmpeg to convert RTSP streams to HLS format for browser playback.
"""

import asyncio
import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamInfo:
    """Information about an active stream"""
    stream_id: str
    rtsp_url: str
    hls_dir: Path
    process: Optional[asyncio.subprocess.Process] = None
    started_at: float = 0
    last_accessed: float = 0
    error: Optional[str] = None
    status: str = "starting"  # starting | running | stopped | error


class StreamProxy:
    """
    Manages RTSP to HLS stream conversion using FFmpeg.

    Each stream gets a unique ID and output directory.
    HLS files are served via the preview router.
    """

    def __init__(self, output_base_dir: Optional[str] = None):
        """
        Initialize the stream proxy.

        Args:
            output_base_dir: Base directory for HLS output files.
                           Defaults to a temp directory.
        """
        if output_base_dir:
            self.output_base_dir = Path(output_base_dir)
        else:
            self.output_base_dir = Path(tempfile.gettempdir()) / "stream_proxy"

        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        self.streams: Dict[str, StreamInfo] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable"""
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            logger.info(f"Found FFmpeg at: {ffmpeg}")
        else:
            logger.warning("FFmpeg not found in PATH")
        return ffmpeg

    async def start_stream(self, rtsp_url: str, stream_id: Optional[str] = None) -> str:
        """
        Start converting an RTSP stream to HLS.

        Args:
            rtsp_url: The RTSP URL to convert
            stream_id: Optional stream ID (auto-generated if not provided)

        Returns:
            The stream ID

        Raises:
            RuntimeError: If FFmpeg is not available or stream fails to start
        """
        if not self._ffmpeg_path:
            raise RuntimeError("FFmpeg is not installed. Please install FFmpeg to use RTSP streaming.")

        # Generate or validate stream ID
        if stream_id is None:
            stream_id = str(uuid.uuid4())[:8]

        # Check if stream already exists
        if stream_id in self.streams:
            existing = self.streams[stream_id]
            if existing.status == "running":
                logger.info(f"Stream {stream_id} already running")
                return stream_id
            else:
                # Clean up old stream
                await self.stop_stream(stream_id)

        # Create output directory
        hls_dir = self.output_base_dir / stream_id
        hls_dir.mkdir(parents=True, exist_ok=True)

        # Create stream info
        import time
        stream_info = StreamInfo(
            stream_id=stream_id,
            rtsp_url=rtsp_url,
            hls_dir=hls_dir,
            started_at=time.time(),
            last_accessed=time.time(),
        )
        self.streams[stream_id] = stream_info

        # Start FFmpeg process
        try:
            await self._start_ffmpeg(stream_info)
            logger.info(f"Started stream {stream_id} from {rtsp_url}")
        except Exception as e:
            stream_info.status = "error"
            stream_info.error = str(e)
            logger.error(f"Failed to start stream {stream_id}: {e}")
            raise

        return stream_id

    async def _start_ffmpeg(self, stream_info: StreamInfo):
        """Start the FFmpeg process for HLS conversion"""
        hls_output = stream_info.hls_dir / "index.m3u8"

        # FFmpeg command for RTSP to HLS conversion
        # -rtsp_transport tcp: Use TCP for more reliable RTSP
        # -fflags nobuffer: Reduce buffering for lower latency
        # -flags low_delay: Low delay mode
        # -hls_time 1: 1 second segments
        # -hls_list_size 3: Keep only 3 segments in playlist
        # -hls_flags delete_segments: Delete old segments
        # -start_number 0: Start segment numbering from 0
        cmd = [
            self._ffmpeg_path,
            "-rtsp_transport", "tcp",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-i", stream_info.rtsp_url,
            "-c:v", "copy",  # Copy video codec (no re-encoding for speed)
            "-c:a", "aac",   # Convert audio to AAC
            "-f", "hls",
            "-hls_time", "1",
            "-hls_list_size", "3",
            "-hls_flags", "delete_segments+append_list",
            "-start_number", "0",
            str(hls_output),
        ]

        logger.debug(f"Starting FFmpeg: {' '.join(cmd)}")

        stream_info.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Monitor the process in the background
        asyncio.create_task(self._monitor_process(stream_info))

        # Wait a bit for the stream to start
        await asyncio.sleep(2)

        # Check if process is still running
        if stream_info.process.returncode is not None:
            stderr = await stream_info.process.stderr.read()
            raise RuntimeError(f"FFmpeg exited immediately: {stderr.decode()}")

        stream_info.status = "running"

    async def _monitor_process(self, stream_info: StreamInfo):
        """Monitor FFmpeg process and handle exit"""
        if not stream_info.process:
            return

        stdout, stderr = await stream_info.process.communicate()

        if stream_info.process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Stream {stream_info.stream_id} FFmpeg error: {error_msg}")
            stream_info.status = "error"
            stream_info.error = error_msg
        else:
            logger.info(f"Stream {stream_info.stream_id} stopped normally")
            stream_info.status = "stopped"

    async def stop_stream(self, stream_id: str) -> bool:
        """
        Stop a running stream.

        Args:
            stream_id: The stream ID to stop

        Returns:
            True if stream was stopped, False if not found
        """
        if stream_id not in self.streams:
            return False

        stream_info = self.streams[stream_id]

        # Terminate FFmpeg process
        if stream_info.process and stream_info.process.returncode is None:
            stream_info.process.terminate()
            try:
                await asyncio.wait_for(stream_info.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                stream_info.process.kill()
                await stream_info.process.wait()

        # Clean up HLS files
        if stream_info.hls_dir.exists():
            shutil.rmtree(stream_info.hls_dir, ignore_errors=True)

        # Remove from tracking
        del self.streams[stream_id]

        logger.info(f"Stopped stream {stream_id}")
        return True

    def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """Get information about a stream"""
        return self.streams.get(stream_id)

    def get_hls_path(self, stream_id: str) -> Optional[Path]:
        """Get the HLS playlist path for a stream"""
        stream_info = self.streams.get(stream_id)
        if stream_info and stream_info.status == "running":
            return stream_info.hls_dir / "index.m3u8"
        return None

    def get_stream_file(self, stream_id: str, filename: str) -> Optional[Path]:
        """Get the path to a stream file (playlist or segment)"""
        stream_info = self.streams.get(stream_id)
        if stream_info:
            file_path = stream_info.hls_dir / filename
            if file_path.exists():
                return file_path
        return None

    def list_streams(self) -> Dict[str, dict]:
        """List all active streams"""
        return {
            sid: {
                "stream_id": info.stream_id,
                "rtsp_url": info.rtsp_url,
                "status": info.status,
                "error": info.error,
            }
            for sid, info in self.streams.items()
        }

    async def cleanup_idle_streams(self, max_idle_seconds: int = 300):
        """Clean up streams that haven't been accessed recently"""
        import time
        now = time.time()

        to_stop = []
        for stream_id, info in self.streams.items():
            if now - info.last_accessed > max_idle_seconds:
                to_stop.append(stream_id)

        for stream_id in to_stop:
            logger.info(f"Cleaning up idle stream: {stream_id}")
            await self.stop_stream(stream_id)

    async def stop_all(self):
        """Stop all active streams"""
        stream_ids = list(self.streams.keys())
        for stream_id in stream_ids:
            await self.stop_stream(stream_id)

        logger.info("All streams stopped")


# Global instance
_stream_proxy: Optional[StreamProxy] = None


def get_stream_proxy() -> StreamProxy:
    """Get the global stream proxy instance"""
    global _stream_proxy
    if _stream_proxy is None:
        _stream_proxy = StreamProxy()
    return _stream_proxy
