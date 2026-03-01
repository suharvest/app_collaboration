"""
Tests for the ResourceResolver service.
"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from provisioning_station.services.resource_resolver import ResourceResolver


@pytest.fixture
def tmp_cache(tmp_path):
    """Create a temporary cache directory."""
    return tmp_path / "cache"


@pytest.fixture
def resolver(tmp_cache):
    """Create a ResourceResolver with a temp cache dir."""
    return ResourceResolver(tmp_cache)


# ------------------------------------------------------------------
# is_url
# ------------------------------------------------------------------


class TestIsUrl:
    def test_https_url(self, resolver):
        assert resolver.is_url("https://cdn.example.com/file.bin") is True

    def test_http_url(self, resolver):
        assert resolver.is_url("http://cdn.example.com/file.bin") is True

    def test_local_relative_path(self, resolver):
        assert resolver.is_url("assets/firmware/file.bin") is False

    def test_local_absolute_path(self, resolver):
        assert resolver.is_url("/tmp/file.bin") is False

    def test_empty_string(self, resolver):
        assert resolver.is_url("") is False

    def test_non_string(self, resolver):
        assert resolver.is_url(None) is False
        assert resolver.is_url(123) is False


# ------------------------------------------------------------------
# resolve — local paths
# ------------------------------------------------------------------


class TestResolveLocalPath:
    @pytest.mark.asyncio
    async def test_relative_path_with_base(self, resolver):
        result = await resolver.resolve("assets/fw.bin", base_path="/opt/solutions/abc")
        assert result == "/opt/solutions/abc/assets/fw.bin"

    @pytest.mark.asyncio
    async def test_absolute_path_unchanged(self, resolver):
        result = await resolver.resolve("/tmp/fw.bin", base_path="/opt/solutions/abc")
        assert result == "/tmp/fw.bin"

    @pytest.mark.asyncio
    async def test_relative_path_no_base(self, resolver):
        result = await resolver.resolve("assets/fw.bin")
        assert result == "assets/fw.bin"


# ------------------------------------------------------------------
# resolve — URL download
# ------------------------------------------------------------------


class TestResolveUrl:
    @pytest.mark.asyncio
    async def test_download_creates_cached_file(self, resolver, tmp_cache):
        """Downloading a URL creates a cached file and returns its path."""
        url = "https://cdn.example.com/firmware/app.bin"
        content = b"fake firmware content"

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            # Simulate writing the file during download
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)

            mock_dl.side_effect = fake_download

            result = await resolver.resolve(url)

            assert Path(result).exists()
            assert Path(result).read_bytes() == content
            assert Path(result).name == "app.bin"
            mock_dl.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_file_skips_download(self, resolver, tmp_cache):
        """A cached file should not trigger a re-download."""
        url = "https://cdn.example.com/packages/detector.deb"
        content = b"deb package"

        # Pre-populate cache
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_dir = tmp_cache / "downloads" / url_hash
        cache_dir.mkdir(parents=True)
        cached_file = cache_dir / "detector.deb"
        cached_file.write_bytes(content)

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            result = await resolver.resolve(url)

            assert result == str(cached_file)
            mock_dl.assert_not_called()

    @pytest.mark.asyncio
    async def test_checksum_match_skips_download(self, resolver, tmp_cache):
        """Cached file with matching checksum should not re-download."""
        url = "https://cdn.example.com/model.cvimodel"
        content = b"model data"
        sha = hashlib.sha256(content).hexdigest()

        # Pre-populate cache
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_dir = tmp_cache / "downloads" / url_hash
        cache_dir.mkdir(parents=True)
        cached_file = cache_dir / "model.cvimodel"
        cached_file.write_bytes(content)

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            result = await resolver.resolve(url, checksum={"sha256": sha})

            assert result == str(cached_file)
            mock_dl.assert_not_called()

    @pytest.mark.asyncio
    async def test_checksum_mismatch_redownloads(self, resolver, tmp_cache):
        """Cached file with wrong checksum should trigger re-download."""
        url = "https://cdn.example.com/model.cvimodel"
        old_content = b"old data"
        new_content = b"new data"
        correct_sha = hashlib.sha256(new_content).hexdigest()

        # Pre-populate cache with old content
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_dir = tmp_cache / "downloads" / url_hash
        cache_dir.mkdir(parents=True)
        cached_file = cache_dir / "model.cvimodel"
        cached_file.write_bytes(old_content)

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.write_bytes(new_content)

            mock_dl.side_effect = fake_download

            result = await resolver.resolve(url, checksum={"sha256": correct_sha})

            assert Path(result).read_bytes() == new_content
            mock_dl.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_failure_raises(self, resolver):
        """Download failure should raise RuntimeError."""
        url = "https://cdn.example.com/missing.bin"

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            mock_dl.side_effect = Exception("Connection refused")

            with pytest.raises(RuntimeError, match="Download failed"):
                await resolver.resolve(url)


# ------------------------------------------------------------------
# _filename_from_url
# ------------------------------------------------------------------


class TestFilenameFromUrl:
    def test_simple_url(self):
        assert ResourceResolver._filename_from_url(
            "https://cdn.example.com/firmware/app.bin"
        ) == "app.bin"

    def test_url_with_query(self):
        assert ResourceResolver._filename_from_url(
            "https://cdn.example.com/file.deb?v=2"
        ) == "file.deb"

    def test_url_encoded(self):
        assert ResourceResolver._filename_from_url(
            "https://cdn.example.com/my%20file.bin"
        ) == "my file.bin"

    def test_url_no_filename(self):
        assert ResourceResolver._filename_from_url("https://cdn.example.com/") == "download"


# ------------------------------------------------------------------
# _verify_checksum
# ------------------------------------------------------------------


class TestVerifyChecksum:
    def test_sha256_match(self, tmp_path):
        f = tmp_path / "test.bin"
        content = b"hello world"
        f.write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()

        assert ResourceResolver._verify_checksum(f, {"sha256": sha}) is True

    def test_sha256_mismatch(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")

        assert ResourceResolver._verify_checksum(f, {"sha256": "bad"}) is False

    def test_md5_match(self, tmp_path):
        f = tmp_path / "test.bin"
        content = b"hello world"
        f.write_bytes(content)
        md5 = hashlib.md5(content).hexdigest()

        assert ResourceResolver._verify_checksum(f, {"md5": md5}) is True

    def test_empty_checksums_passes(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"data")
        assert ResourceResolver._verify_checksum(f, {}) is True


# ------------------------------------------------------------------
# DeviceConfig.resolve_remote_assets
# ------------------------------------------------------------------


class TestResolveRemoteAssets:
    @pytest.mark.asyncio
    async def test_local_paths_resolved_to_absolute(self, resolver):
        """Local paths should be resolved to absolute paths via base_path."""
        from provisioning_station.models.device import (
            DeviceConfig,
            FirmwareConfig,
            FirmwareSource,
            FlashConfig,
        )

        config = DeviceConfig(
            id="test",
            name="Test",
            type="esp32_usb",
            base_path="/opt/solutions/test",
            firmware=FirmwareConfig(
                source=FirmwareSource(path="assets/fw.bin"),
                flash_config=FlashConfig(),
            ),
        )

        await config.resolve_remote_assets(resolver)

        # Local path gets resolved to absolute via base_path
        assert config.firmware.source.path == "/opt/solutions/test/assets/fw.bin"

    @pytest.mark.asyncio
    async def test_firmware_url_resolved(self, resolver, tmp_cache):
        """URL in firmware.source.path should be downloaded and replaced."""
        from provisioning_station.models.device import (
            DeviceConfig,
            FirmwareConfig,
            FirmwareSource,
            FlashConfig,
        )

        url = "https://cdn.example.com/firmware/app.bin"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="esp32_usb",
            firmware=FirmwareConfig(
                source=FirmwareSource(path=url),
                flash_config=FlashConfig(),
            ),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"firmware")

            mock_dl.side_effect = fake_download

            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.firmware.source.path)
            assert Path(config.firmware.source.path).name == "app.bin"

    @pytest.mark.asyncio
    async def test_binary_deb_url_resolved(self, resolver, tmp_cache):
        """URL in binary.deb_package.path should be downloaded and replaced."""
        from provisioning_station.models.device import (
            BinaryConfig,
            DebPackageConfig,
            DeviceConfig,
        )

        url = "https://cdn.example.com/packages/detector.deb"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="recamera_cpp",
            binary=BinaryConfig(
                deb_package=DebPackageConfig(path=url),
            ),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"deb package")

            mock_dl.side_effect = fake_download

            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.binary.deb_package.path)
            assert Path(config.binary.deb_package.path).name == "detector.deb"

    @pytest.mark.asyncio
    async def test_action_script_resolved(self, resolver, tmp_cache):
        """script field in ActionConfig should be downloaded and read into run."""
        from provisioning_station.models.device import (
            ActionConfig,
            ActionsConfig,
            DeviceConfig,
        )

        script_url = "https://cdn.example.com/scripts/configure.sh"
        script_content = "#!/bin/bash\necho hello"

        config = DeviceConfig(
            id="test",
            name="Test",
            type="recamera_cpp",
            actions=ActionsConfig(
                after=[
                    ActionConfig(
                        name="Configure",
                        script=script_url,
                    )
                ]
            ),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(script_content)

            mock_dl.side_effect = fake_download

            await config.resolve_remote_assets(resolver)

            action = config.actions.after[0]
            assert action.run == script_content
            assert action.script is None  # consumed

    @pytest.mark.asyncio
    async def test_mixed_local_and_url(self, resolver, tmp_cache):
        """Config with both local paths and URLs should handle both correctly."""
        from provisioning_station.models.device import (
            BinaryConfig,
            DebPackageConfig,
            DeviceConfig,
            ModelFileConfig,
        )

        model_url = "https://cdn.example.com/models/large.cvimodel"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="recamera_cpp",
            base_path="/opt/solutions/test",
            binary=BinaryConfig(
                deb_package=DebPackageConfig(path="packages/detector.deb"),  # local
                models=[
                    ModelFileConfig(path=model_url, target_path="/models"),  # URL
                ],
            ),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"model data")

            mock_dl.side_effect = fake_download

            await config.resolve_remote_assets(resolver)

            # Local path resolved to absolute via base_path
            assert config.binary.deb_package.path == "/opt/solutions/test/packages/detector.deb"
            # URL resolved to local cache
            assert not resolver.is_url(config.binary.models[0].path)
            mock_dl.assert_called_once()


# ------------------------------------------------------------------
# Model simplification tests
# ------------------------------------------------------------------


class TestModelSimplification:
    def test_firmware_source_no_type_field(self):
        """FirmwareSource should not have type or url fields."""
        from provisioning_station.models.device import FirmwareSource

        src = FirmwareSource(path="firmware.bin")
        assert src.path == "firmware.bin"
        assert "type" not in FirmwareSource.model_fields
        assert "url" not in FirmwareSource.model_fields

    def test_package_source_no_type_field(self):
        """PackageSource should not have type or url fields."""
        from provisioning_station.models.device import PackageSource

        src = PackageSource(path="package.deb")
        assert src.path == "package.deb"
        assert "type" not in PackageSource.model_fields
        assert "url" not in PackageSource.model_fields

    def test_himax_model_no_url_field(self):
        """HimaxModelConfig should not have url field."""
        from provisioning_station.models.device import HimaxModelConfig

        model = HimaxModelConfig(
            id="test",
            name="Test",
            path="model.tflite",
            flash_address="0x400000",
        )
        assert model.path == "model.tflite"
        assert "url" not in HimaxModelConfig.model_fields

    def test_action_config_has_script_field(self):
        """ActionConfig should have a script field."""
        from provisioning_station.models.device import ActionConfig

        action = ActionConfig(
            name="Test",
            script="https://cdn.example.com/script.sh",
        )
        assert action.script == "https://cdn.example.com/script.sh"
        assert action.run is None

    def test_deb_package_has_checksum(self):
        """DebPackageConfig should have optional checksum field."""
        from provisioning_station.models.device import DebPackageConfig

        pkg = DebPackageConfig(
            path="package.deb",
            checksum={"sha256": "abc123"},
        )
        assert pkg.checksum == {"sha256": "abc123"}

    def test_model_file_has_checksum(self):
        """ModelFileConfig should have optional checksum field."""
        from provisioning_station.models.device import ModelFileConfig

        model = ModelFileConfig(
            path="model.cvimodel",
            target_path="/models",
            checksum={"sha256": "abc123"},
        )
        assert model.checksum == {"sha256": "abc123"}


# ------------------------------------------------------------------
# resolve_remote_assets — additional branch coverage
# ------------------------------------------------------------------


class TestResolveRemoteAssetsBranches:
    """Cover resolve_remote_assets branches not tested above."""

    @pytest.mark.asyncio
    async def test_package_source_url_resolved(self, resolver, tmp_cache):
        """URL in package.source.path (ssh_deb) should be downloaded."""
        from provisioning_station.models.device import (
            DeviceConfig,
            PackageConfig,
            PackageSource,
        )

        url = "https://cdn.example.com/packages/app.deb"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="ssh_deb",
            package=PackageConfig(
                source=PackageSource(path=url),
            ),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"deb content")

            mock_dl.side_effect = fake_download
            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.package.source.path)
            assert Path(config.package.source.path).name == "app.deb"
            mock_dl.assert_called_once()

    @pytest.mark.asyncio
    async def test_docker_compose_url_resolved(self, resolver, tmp_cache):
        """URL in docker.compose_file should be downloaded."""
        from provisioning_station.models.device import (
            DeviceConfig,
            DockerConfig,
        )

        url = "https://cdn.example.com/compose/docker-compose.yml"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="docker_local",
            docker=DockerConfig(compose_file=url),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("version: '3'\nservices: {}")

            mock_dl.side_effect = fake_download
            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.docker.compose_file)
            assert Path(config.docker.compose_file).name == "docker-compose.yml"

    @pytest.mark.asyncio
    async def test_docker_remote_compose_url_resolved(self, resolver, tmp_cache):
        """URL in docker_remote.compose_file should be downloaded."""
        from provisioning_station.models.device import (
            DeviceConfig,
            DockerRemoteConfig,
        )

        url = "https://cdn.example.com/compose/remote-compose.yml"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="docker_remote",
            docker_remote=DockerRemoteConfig(compose_file=url),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("version: '3'\nservices: {}")

            mock_dl.side_effect = fake_download
            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.docker_remote.compose_file)
            assert Path(config.docker_remote.compose_file).name == "remote-compose.yml"

    @pytest.mark.asyncio
    async def test_nodered_flow_url_resolved(self, resolver, tmp_cache):
        """URL in nodered.flow_file should be downloaded."""
        from provisioning_station.models.device import (
            DeviceConfig,
            NodeRedConfig,
        )

        url = "https://cdn.example.com/flows/flow.json"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="recamera_nodered",
            nodered=NodeRedConfig(flow_file=url),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text('[{"id":"node1"}]')

            mock_dl.side_effect = fake_download
            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.nodered.flow_file)
            assert Path(config.nodered.flow_file).name == "flow.json"

    @pytest.mark.asyncio
    async def test_partition_file_url_resolved(self, resolver, tmp_cache):
        """URL in firmware.flash_config.partitions[].file should be downloaded."""
        from provisioning_station.models.device import (
            DeviceConfig,
            FirmwareConfig,
            FirmwareSource,
            FlashConfig,
            PartitionConfig,
        )

        part_url = "https://cdn.example.com/partitions/bootloader.bin"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="esp32_usb",
            firmware=FirmwareConfig(
                source=FirmwareSource(path="assets/fw.bin"),
                flash_config=FlashConfig(
                    partitions=[
                        PartitionConfig(
                            name="bootloader",
                            offset="0x0",
                            file=part_url,
                        ),
                    ],
                ),
            ),
            base_path="/opt/solutions/test",
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"bootloader binary")

            mock_dl.side_effect = fake_download
            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.firmware.flash_config.partitions[0].file)
            assert Path(config.firmware.flash_config.partitions[0].file).name == "bootloader.bin"

    @pytest.mark.asyncio
    async def test_action_copy_src_url_resolved(self, resolver, tmp_cache):
        """URL in action.copy_files.src should be downloaded."""
        from provisioning_station.models.device import (
            ActionConfig,
            ActionCopy,
            ActionsConfig,
            DeviceConfig,
        )

        copy_url = "https://cdn.example.com/configs/settings.json"
        config = DeviceConfig(
            id="test",
            name="Test",
            type="recamera_cpp",
            actions=ActionsConfig(
                after=[
                    ActionConfig(
                        name="Copy config",
                        copy_files=ActionCopy(
                            src=copy_url,
                            dest="/etc/app/settings.json",
                        ),
                    )
                ]
            ),
        )

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text('{"key": "value"}')

            mock_dl.side_effect = fake_download
            await config.resolve_remote_assets(resolver)

            assert not resolver.is_url(config.actions.after[0].copy_files.src)


# ------------------------------------------------------------------
# ResourceResolver error paths
# ------------------------------------------------------------------


class TestResourceResolverErrorPaths:
    @pytest.mark.asyncio
    async def test_download_failure_cleans_up_partial_file(self, resolver, tmp_cache):
        """Failed download should remove any partial file."""
        url = "https://cdn.example.com/large.bin"

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def failing_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"partial data")
                raise ConnectionError("Connection lost")

            mock_dl.side_effect = failing_download

            with pytest.raises(RuntimeError, match="Download failed"):
                await resolver.resolve(url)

            # Verify partial file was cleaned up
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            cache_dir = tmp_cache / "downloads" / url_hash
            assert not (cache_dir / "large.bin").exists()

    @pytest.mark.asyncio
    async def test_post_download_checksum_failure_deletes_file(self, resolver, tmp_cache):
        """File that fails checksum after download should be deleted."""
        url = "https://cdn.example.com/firmware.bin"
        content = b"downloaded content"

        with patch.object(resolver, "_stream_download", new_callable=AsyncMock) as mock_dl:
            async def fake_download(u, dest, cb=None):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)

            mock_dl.side_effect = fake_download

            with pytest.raises(RuntimeError, match="Checksum verification failed"):
                await resolver.resolve(url, checksum={"sha256": "wrong_hash"})

            # File should be deleted after checksum failure
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            cache_dir = tmp_cache / "downloads" / url_hash
            assert not (cache_dir / "firmware.bin").exists()
