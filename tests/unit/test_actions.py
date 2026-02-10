"""
Unit tests for the unified Actions system (before/after hooks).

Tests cover:
- Pydantic model parsing (ActionsConfig, ActionConfig, ActionWhen, ActionCopy)
- Variable substitution
- When-condition evaluation
- ignore_error behavior
- LocalActionExecutor
- SSHActionExecutor
- BaseDeployer._execute_actions()
"""

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from provisioning_station.models.device import (
    ActionConfig,
    ActionCopy,
    ActionsConfig,
    ActionWhen,
    DeviceConfig,
)


def _import_action_executor():
    """Import action_executor module without triggering deployers/__init__.py."""
    mod_name = "provisioning_station.deployers.action_executor"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    # Temporarily prevent deployers __init__ from running by pre-registering
    # the parent package if it hasn't been imported yet
    parent = "provisioning_station.deployers"
    parent_was_missing = parent not in sys.modules
    if parent_was_missing:
        import types

        pkg = types.ModuleType(parent)
        pkg.__path__ = [
            str(
                importlib.import_module("provisioning_station").__path__[0]
            )
            + "/deployers"
        ]
        pkg.__package__ = parent
        sys.modules[parent] = pkg
    try:
        mod = importlib.import_module(mod_name)
    finally:
        if parent_was_missing and parent in sys.modules:
            # Clean up only if we were the ones who injected it
            pass  # keep it — other imports may depend on it now
    return mod


def _import_base_deployer():
    """Import base module without triggering deployers/__init__.py."""
    mod_name = "provisioning_station.deployers.base"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    parent = "provisioning_station.deployers"
    parent_was_missing = parent not in sys.modules
    if parent_was_missing:
        import types

        pkg = types.ModuleType(parent)
        pkg.__path__ = [
            str(
                importlib.import_module("provisioning_station").__path__[0]
            )
            + "/deployers"
        ]
        pkg.__package__ = parent
        sys.modules[parent] = pkg
    mod = importlib.import_module(mod_name)
    return mod


# ---------------------------------------------------------------------------
# Model parsing
# ---------------------------------------------------------------------------
class TestActionsConfigParsing:
    """Test ActionsConfig Pydantic model parsing."""

    def test_empty_actions(self):
        cfg = ActionsConfig()
        assert cfg.before == []
        assert cfg.after == []

    def test_before_after_lists(self):
        cfg = ActionsConfig(
            before=[ActionConfig(name="a", run="echo hi")],
            after=[ActionConfig(name="b", run="echo bye")],
        )
        assert len(cfg.before) == 1
        assert len(cfg.after) == 1
        assert cfg.before[0].name == "a"
        assert cfg.after[0].name == "b"

    def test_action_defaults(self):
        a = ActionConfig(name="test")
        assert a.run is None
        assert a.copy is None
        assert a.sudo is False
        assert a.when is None
        assert a.env == {}
        assert a.timeout == 300
        assert a.ignore_error is False
        assert a.name_zh is None

    def test_action_all_fields(self):
        a = ActionConfig(
            name="full",
            name_zh="完整",
            run="echo hello",
            sudo=True,
            when=ActionWhen(field="mode", value="offline"),
            env={"FOO": "bar"},
            timeout=60,
            ignore_error=True,
        )
        assert a.name == "full"
        assert a.name_zh == "完整"
        assert a.run == "echo hello"
        assert a.sudo is True
        assert a.when.field == "mode"
        assert a.when.value == "offline"
        assert a.env == {"FOO": "bar"}
        assert a.timeout == 60
        assert a.ignore_error is True

    def test_action_copy_model(self):
        c = ActionCopy(src="conf/app.cfg", dest="/etc/app.cfg")
        assert c.src == "conf/app.cfg"
        assert c.dest == "/etc/app.cfg"
        assert c.mode == "0644"

    def test_action_copy_custom_mode(self):
        c = ActionCopy(src="bin/run.sh", dest="/usr/local/bin/run.sh", mode="0755")
        assert c.mode == "0755"

    def test_action_when_value(self):
        w = ActionWhen(field="deploy_method", value="offline")
        assert w.field == "deploy_method"
        assert w.value == "offline"
        assert w.not_value is None

    def test_action_when_not_value(self):
        w = ActionWhen(field="skip_mqtt", not_value="true")
        assert w.not_value == "true"
        assert w.value is None

    def test_device_config_with_actions(self):
        cfg = DeviceConfig(
            id="test",
            name="Test",
            type="docker_local",
            actions=ActionsConfig(
                before=[ActionConfig(name="prep", run="mkdir -p /tmp/test")]
            ),
        )
        assert cfg.actions is not None
        assert len(cfg.actions.before) == 1
        assert cfg.actions.after == []

    def test_device_config_without_actions(self):
        cfg = DeviceConfig(id="test", name="Test", type="docker_local")
        assert cfg.actions is None


# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------
class TestVariableSubstitution:
    """Test {{var}} substitution in action_executor."""

    def test_simple_substitution(self):
        from provisioning_station.utils.template import substitute as _substitute

        result = _substitute("echo {{name}}", {"name": "world"})
        assert result == "echo world"

    def test_multiple_vars(self):
        from provisioning_station.utils.template import substitute as _substitute

        result = _substitute(
            "{{host}}:{{port}}", {"host": "192.168.1.1", "port": "8080"}
        )
        assert result == "192.168.1.1:8080"

    def test_missing_var_returns_empty(self):
        from provisioning_station.utils.template import substitute as _substitute

        result = _substitute("echo {{missing}}", {})
        assert result == "echo "

    def test_no_vars_in_template(self):
        from provisioning_station.utils.template import substitute as _substitute

        result = _substitute("echo hello", {"name": "world"})
        assert result == "echo hello"

    def test_empty_template(self):
        from provisioning_station.utils.template import substitute as _substitute

        result = _substitute("", {"name": "world"})
        assert result == ""

    def test_none_template(self):
        from provisioning_station.utils.template import substitute as _substitute

        result = _substitute(None, {"name": "world"})
        assert result is None

    def test_nested_in_multiline(self):
        from provisioning_station.utils.template import substitute as _substitute

        template = "docker run --name {{container}}\n  -e MODEL={{model}}"
        result = _substitute(template, {"container": "app1", "model": "qwen3"})
        assert "docker run --name app1" in result
        assert "-e MODEL=qwen3" in result


# ---------------------------------------------------------------------------
# When-condition evaluation (tested through _execute_actions)
# ---------------------------------------------------------------------------
class TestWhenCondition:
    """Test when-condition filtering in _execute_actions."""

    @pytest.mark.asyncio
    async def test_when_value_match_executes(self):
        """Action runs when field value matches."""
        ae_mod = _import_action_executor()
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                before=[
                    ActionConfig(
                        name="only_offline",
                        run="echo offline",
                        when=ActionWhen(field="mode", value="offline"),
                    )
                ]
            ),
        )

        executor = MagicMock()
        executor.execute_run = AsyncMock(return_value=True)

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "before", config, {"mode": "offline"}, None, executor
        )

        assert result is True
        executor.execute_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_when_value_no_match_skips(self):
        """Action skipped when field value doesn't match."""
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                before=[
                    ActionConfig(
                        name="only_offline",
                        run="echo offline",
                        when=ActionWhen(field="mode", value="offline"),
                    )
                ]
            ),
        )

        executor = MagicMock()
        executor.execute_run = AsyncMock(return_value=True)

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "before", config, {"mode": "online"}, None, executor
        )

        assert result is True
        executor.execute_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_when_not_value_match_skips(self):
        """Action skipped when field equals not_value."""
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                before=[
                    ActionConfig(
                        name="skip_if_true",
                        run="echo run",
                        when=ActionWhen(field="skip", not_value="true"),
                    )
                ]
            ),
        )

        executor = MagicMock()
        executor.execute_run = AsyncMock(return_value=True)

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "before", config, {"skip": "true"}, None, executor
        )

        assert result is True
        executor.execute_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_when_field_missing_treated_as_none(self):
        """When field is missing from context, str(None) is used."""
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                before=[
                    ActionConfig(
                        name="needs_field",
                        run="echo run",
                        when=ActionWhen(field="missing_field", value="something"),
                    )
                ]
            ),
        )

        executor = MagicMock()
        executor.execute_run = AsyncMock(return_value=True)

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "before", config, {}, None, executor
        )

        assert result is True
        executor.execute_run.assert_not_called()


# ---------------------------------------------------------------------------
# ignore_error behavior
# ---------------------------------------------------------------------------
class TestIgnoreError:
    """Test ignore_error flag."""

    @pytest.mark.asyncio
    async def test_ignore_error_true_continues(self):
        """When action fails but ignore_error=True, continue."""
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                before=[
                    ActionConfig(
                        name="may_fail",
                        run="false",
                        ignore_error=True,
                    ),
                    ActionConfig(
                        name="should_run",
                        run="echo ok",
                    ),
                ]
            ),
        )

        executor = MagicMock()
        executor.execute_run = AsyncMock(side_effect=[False, True])

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "before", config, {}, None, executor
        )

        assert result is True
        assert executor.execute_run.call_count == 2

    @pytest.mark.asyncio
    async def test_ignore_error_false_aborts(self):
        """When action fails and ignore_error=False, abort."""
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                before=[
                    ActionConfig(
                        name="must_succeed",
                        run="false",
                        ignore_error=False,
                    ),
                    ActionConfig(
                        name="never_runs",
                        run="echo ok",
                    ),
                ]
            ),
        )

        executor = MagicMock()
        executor.execute_run = AsyncMock(return_value=False)

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "before", config, {}, None, executor
        )

        assert result is False
        assert executor.execute_run.call_count == 1


# ---------------------------------------------------------------------------
# LocalActionExecutor
# ---------------------------------------------------------------------------
class TestLocalActionExecutor:
    """Test LocalActionExecutor."""

    @pytest.mark.asyncio
    async def test_execute_run_success(self):
        ae_mod = _import_action_executor()
        executor = ae_mod.LocalActionExecutor()
        action = ActionConfig(name="test", run="echo hello", timeout=10)
        result = await executor.execute_run(action, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_run_failure(self):
        ae_mod = _import_action_executor()
        executor = ae_mod.LocalActionExecutor()
        action = ActionConfig(name="test", run="exit 1", timeout=10)
        result = await executor.execute_run(action, {})
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_run_with_env(self):
        ae_mod = _import_action_executor()
        executor = ae_mod.LocalActionExecutor()
        action = ActionConfig(
            name="test",
            run='test "$MY_VAR" = "hello"',
            env={"MY_VAR": "hello"},
            timeout=10,
        )
        result = await executor.execute_run(action, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_run_with_substitution(self):
        ae_mod = _import_action_executor()
        executor = ae_mod.LocalActionExecutor()
        action = ActionConfig(
            name="test",
            run='test "{{val}}" = "world"',
            timeout=10,
        )
        result = await executor.execute_run(action, {"val": "world"})
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_run_empty_command(self):
        ae_mod = _import_action_executor()
        executor = ae_mod.LocalActionExecutor()
        action = ActionConfig(name="test", run="", timeout=10)
        result = await executor.execute_run(action, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_copy(self, tmp_path):
        ae_mod = _import_action_executor()

        # Create source file
        src = tmp_path / "source.txt"
        src.write_text("content")

        dest = tmp_path / "dest" / "output.txt"

        executor = ae_mod.LocalActionExecutor()
        copy = ActionCopy(src=str(src), dest=str(dest))
        result = await executor.execute_copy(copy, {})

        assert result is True
        assert dest.exists()
        assert dest.read_text() == "content"


# ---------------------------------------------------------------------------
# SSHActionExecutor
# ---------------------------------------------------------------------------
class TestSSHActionExecutor:
    """Test SSHActionExecutor with mocked paramiko."""

    @pytest.mark.asyncio
    async def test_execute_run_success(self):
        ae_mod = _import_action_executor()

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.channel.settimeout = MagicMock()
        mock_stderr.channel.settimeout = MagicMock()
        mock_stdout.read.return_value = b"ok"
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        executor = ae_mod.SSHActionExecutor(mock_client, password="pass")
        action = ActionConfig(name="test", run="echo hello", timeout=30)
        result = await executor.execute_run(action, {})

        assert result is True
        mock_client.exec_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_run_with_sudo(self):
        ae_mod = _import_action_executor()

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.channel.settimeout = MagicMock()
        mock_stderr.channel.settimeout = MagicMock()
        mock_stdout.read.return_value = b"ok"
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        executor = ae_mod.SSHActionExecutor(mock_client, password="mypass")
        action = ActionConfig(name="test", run="systemctl restart mqtt", sudo=True, timeout=30)
        result = await executor.execute_run(action, {})

        assert result is True
        # Verify the command includes sudo
        called_cmd = mock_client.exec_command.call_args[0][0]
        assert "sudo" in called_cmd
        assert "printf" in called_cmd

    @pytest.mark.asyncio
    async def test_execute_run_failure(self):
        ae_mod = _import_action_executor()

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 1
        mock_stdout.channel.settimeout = MagicMock()
        mock_stderr.channel.settimeout = MagicMock()
        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"error"
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        executor = ae_mod.SSHActionExecutor(mock_client, password="pass")
        action = ActionConfig(name="test", run="exit 1", timeout=30)
        result = await executor.execute_run(action, {})

        assert result is False


# ---------------------------------------------------------------------------
# BaseDeployer._execute_actions integration
# ---------------------------------------------------------------------------
class TestExecuteActions:
    """Test BaseDeployer._execute_actions with mocked executor."""

    @pytest.mark.asyncio
    async def test_no_actions_returns_true(self):
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        config = DeviceConfig(id="test", name="Test", type="manual")
        deployer = TestDeployer()
        result = await deployer._execute_actions("before", config, {}, None, None)
        assert result is True

    @pytest.mark.asyncio
    async def test_empty_phase_returns_true(self):
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(before=[], after=[]),
        )
        deployer = TestDeployer()
        result = await deployer._execute_actions("before", config, {}, None, None)
        assert result is True

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                before=[ActionConfig(name="step1", run="echo ok")]
            ),
        )

        executor = MagicMock()
        executor.execute_run = AsyncMock(return_value=True)

        callback = AsyncMock()

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "before", config, {}, callback, executor
        )

        assert result is True
        assert callback.call_count >= 2  # at least start + end

    @pytest.mark.asyncio
    async def test_copy_action_dispatched(self):
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            actions=ActionsConfig(
                after=[
                    ActionConfig(
                        name="copy_cfg",
                        copy=ActionCopy(src="app.cfg", dest="/etc/app.cfg"),
                    )
                ]
            ),
        )

        executor = MagicMock()
        executor.execute_copy = AsyncMock(return_value=True)

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        deployer = TestDeployer()
        result = await deployer._execute_actions(
            "after", config, {}, None, executor
        )

        assert result is True
        executor.execute_copy.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_includes_user_input_defaults(self):
        """_build_action_context merges user_input defaults with connection."""
        base_mod = _import_base_deployer()
        BaseDeployer = base_mod.BaseDeployer
        from provisioning_station.models.device import UserInputConfig

        class TestDeployer(BaseDeployer):
            async def deploy(self, config, connection, progress_callback=None):
                return True

        config = DeviceConfig(
            id="test",
            name="Test",
            type="manual",
            user_inputs=[
                UserInputConfig(id="host", name="Host", default="192.168.1.1"),
                UserInputConfig(id="port", name="Port", default="22"),
            ],
        )

        deployer = TestDeployer()
        ctx = deployer._build_action_context(config, {"host": "10.0.0.1"})

        # Connection overrides default
        assert ctx["host"] == "10.0.0.1"
        # Default preserved when not in connection
        assert ctx["port"] == "22"


# ---------------------------------------------------------------------------
# Model cleanup: MqttExternalConfig removed, disable removed
# ---------------------------------------------------------------------------
class TestModelCleanup:
    """Verify removed fields are no longer accessible."""

    def test_mqtt_external_config_removed(self):
        """MqttExternalConfig should no longer exist."""
        import provisioning_station.models.device as device_mod

        assert not hasattr(device_mod, "MqttExternalConfig")

    def test_binary_config_no_mqtt_config(self):
        """BinaryConfig should not have mqtt_config field."""
        from provisioning_station.models.device import BinaryConfig

        bc = BinaryConfig()
        assert not hasattr(bc, "mqtt_config")

    def test_conflict_service_no_disable(self):
        """ConflictServiceConfig should not have disable field."""
        from provisioning_station.models.device import ConflictServiceConfig

        cs = ConflictServiceConfig(stop=["S03node-red"])
        assert not hasattr(cs, "disable")
        assert cs.stop == ["S03node-red"]
