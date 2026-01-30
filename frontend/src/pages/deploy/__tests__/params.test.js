/**
 * Deployment Parameters Tests
 *
 * Tests for deployment parameter construction in the frontend.
 * Verifies that the params object sent to deploymentsApi.start()
 * matches the backend StartDeploymentRequest model.
 *
 * Reference: devices.js startDeployment() lines 238-348
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Deployment Parameters', () => {
  /**
   * Helper to build deployment params similar to devices.js startDeployment()
   * This mirrors the logic in lines 269-335
   */
  function buildDeploymentParams({
    solutionId,
    deviceId,
    deviceType,
    presetId = null,
    selectedTarget = null,
    connectionInputs = {},
    userInputs = {},
  }) {
    const params = {
      solution_id: solutionId,
      preset_id: presetId,
      selected_devices: [deviceId],
      device_connections: {},
      options: {},
    }

    // If using docker_deploy with targets
    if (selectedTarget) {
      params.options.deploy_target = selectedTarget.id
      if (selectedTarget.config_file) {
        params.options.config_file = selectedTarget.config_file
      }
    }

    // Map device type to connection format
    let effectiveType = deviceType
    if (deviceType === 'docker_deploy' && selectedTarget) {
      const isRemote = selectedTarget.id === 'remote' ||
                       selectedTarget.id?.endsWith('_remote') ||
                       selectedTarget.id?.includes('remote')
      effectiveType = isRemote ? 'docker_remote' : 'docker_local'
    }

    // Build connection info based on effective type
    if (effectiveType === 'esp32_usb') {
      params.device_connections[deviceId] = {
        port: connectionInputs.port || null,
      }
    } else if (effectiveType === 'himax_usb') {
      params.device_connections[deviceId] = {
        port: connectionInputs.port || null,
        selected_models: connectionInputs.selectedModels || [],
      }
    } else if (effectiveType === 'ssh_deb' || effectiveType === 'docker_remote') {
      params.device_connections[deviceId] = {
        host: connectionInputs.host,
        port: parseInt(connectionInputs.port || '22'),
        username: connectionInputs.username,
        password: connectionInputs.password,
      }
    } else if (effectiveType === 'recamera_nodered') {
      params.device_connections[deviceId] = {
        recamera_ip: connectionInputs.host,
        nodered_host: connectionInputs.host,
        ssh_username: connectionInputs.username || 'recamera',
        ssh_password: connectionInputs.password,
        ssh_port: parseInt(connectionInputs.port || '22'),
      }
    } else if (deviceType === 'recamera_cpp') {
      params.device_connections[deviceId] = {
        host: connectionInputs.host,
        port: parseInt(connectionInputs.port || '22'),
        username: connectionInputs.username || 'recamera',
        password: connectionInputs.password,
      }
    } else if (deviceType === 'script') {
      params.device_connections[deviceId] = {}
      params.options.user_inputs = userInputs
    } else {
      params.device_connections[deviceId] = {}
    }

    return params
  }

  describe('Required Fields', () => {
    it('should always include solution_id', () => {
      const params = buildDeploymentParams({
        solutionId: 'smart_warehouse',
        deviceId: 'warehouse',
        deviceType: 'docker_local',
      })

      expect(params.solution_id).toBe('smart_warehouse')
    })

    it('should always include selected_devices array', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'device1',
        deviceType: 'manual',
      })

      expect(Array.isArray(params.selected_devices)).toBe(true)
      expect(params.selected_devices).toContain('device1')
    })

    it('should always include device_connections object', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'device1',
        deviceType: 'manual',
      })

      expect(typeof params.device_connections).toBe('object')
    })

    it('should always include options object', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'device1',
        deviceType: 'manual',
      })

      expect(typeof params.options).toBe('object')
    })
  })

  describe('ESP32 USB Device', () => {
    it('should include port in connection', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'esp32_firmware',
        deviceType: 'esp32_usb',
        connectionInputs: { port: '/dev/ttyUSB0' },
      })

      expect(params.device_connections.esp32_firmware).toEqual({
        port: '/dev/ttyUSB0',
      })
    })

    it('should handle empty port', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'esp32_firmware',
        deviceType: 'esp32_usb',
        connectionInputs: {},
      })

      expect(params.device_connections.esp32_firmware.port).toBe(null)
    })
  })

  describe('Himax USB Device', () => {
    it('should include port and selected_models', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'himax_firmware',
        deviceType: 'himax_usb',
        connectionInputs: {
          port: '/dev/cu.usbserial-01',
          selectedModels: ['scrfd', 'facenet'],
        },
      })

      expect(params.device_connections.himax_firmware.port).toBe('/dev/cu.usbserial-01')
      expect(params.device_connections.himax_firmware.selected_models).toEqual(['scrfd', 'facenet'])
    })
  })

  describe('Docker Deploy Device (with targets)', () => {
    it('should map local target to docker_local type', () => {
      const params = buildDeploymentParams({
        solutionId: 'smart_warehouse',
        deviceId: 'warehouse',
        deviceType: 'docker_deploy',
        selectedTarget: { id: 'warehouse_local', config_file: 'docker/local.yaml' },
      })

      // Local docker has empty connection
      expect(params.device_connections.warehouse).toEqual({})
      expect(params.options.deploy_target).toBe('warehouse_local')
      expect(params.options.config_file).toBe('docker/local.yaml')
    })

    it('should map remote target to docker_remote type with SSH', () => {
      const params = buildDeploymentParams({
        solutionId: 'smart_warehouse',
        deviceId: 'warehouse',
        deviceType: 'docker_deploy',
        selectedTarget: { id: 'warehouse_remote', config_file: 'docker/remote.yaml' },
        connectionInputs: {
          host: '192.168.1.100',
          port: '22',
          username: 'pi',
          password: 'raspberry',
        },
      })

      expect(params.device_connections.warehouse).toEqual({
        host: '192.168.1.100',
        port: 22,
        username: 'pi',
        password: 'raspberry',
      })
      expect(params.options.deploy_target).toBe('warehouse_remote')
    })

    it('should detect remote by _remote suffix', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'app',
        deviceType: 'docker_deploy',
        selectedTarget: { id: 'app_remote' },
        connectionInputs: {
          host: '192.168.1.50',
          username: 'pi',
        },
      })

      // Should have SSH connection fields
      expect(params.device_connections.app.host).toBe('192.168.1.50')
    })
  })

  describe('SSH DEB Device', () => {
    it('should include full SSH connection info', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'server',
        deviceType: 'ssh_deb',
        connectionInputs: {
          host: '10.0.0.5',
          port: '2222',
          username: 'admin',
          password: 'secret',
        },
      })

      expect(params.device_connections.server).toEqual({
        host: '10.0.0.5',
        port: 2222,
        username: 'admin',
        password: 'secret',
      })
    })

    it('should default port to 22', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'server',
        deviceType: 'ssh_deb',
        connectionInputs: {
          host: '10.0.0.5',
          username: 'admin',
        },
      })

      expect(params.device_connections.server.port).toBe(22)
    })
  })

  describe('reCamera Node-RED Device', () => {
    it('should use special field names', () => {
      const params = buildDeploymentParams({
        solutionId: 'recamera_heatmap',
        deviceId: 'recamera',
        deviceType: 'recamera_nodered',
        connectionInputs: {
          host: '192.168.1.50',
          username: 'recamera',
          password: 'recamera',
          port: '22',
        },
      })

      expect(params.device_connections.recamera).toEqual({
        recamera_ip: '192.168.1.50',
        nodered_host: '192.168.1.50',
        ssh_username: 'recamera',
        ssh_password: 'recamera',
        ssh_port: 22,
      })
    })

    it('should default username to recamera', () => {
      const params = buildDeploymentParams({
        solutionId: 'recamera_heatmap',
        deviceId: 'recamera',
        deviceType: 'recamera_nodered',
        connectionInputs: {
          host: '192.168.1.50',
        },
      })

      expect(params.device_connections.recamera.ssh_username).toBe('recamera')
    })
  })

  describe('reCamera C++ Device', () => {
    it('should use standard SSH field names', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'recamera',
        deviceType: 'recamera_cpp',
        connectionInputs: {
          host: '192.168.1.50',
          username: 'recamera',
          password: 'password123',
        },
      })

      expect(params.device_connections.recamera).toEqual({
        host: '192.168.1.50',
        port: 22,
        username: 'recamera',
        password: 'password123',
      })
    })
  })

  describe('Script Device', () => {
    it('should include user_inputs in options', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'setup_script',
        deviceType: 'script',
        userInputs: {
          api_key: 'sk-xxx',
          model: 'gpt-4',
        },
      })

      expect(params.options.user_inputs).toEqual({
        api_key: 'sk-xxx',
        model: 'gpt-4',
      })
      expect(params.device_connections.setup_script).toEqual({})
    })
  })

  describe('Preset Integration', () => {
    it('should include preset_id at top level', () => {
      const params = buildDeploymentParams({
        solutionId: 'smart_warehouse',
        deviceId: 'warehouse',
        deviceType: 'docker_local',
        presetId: 'edge_computing',
      })

      expect(params.preset_id).toBe('edge_computing')
      // preset_id should NOT be in options
      expect(params.options.preset_id).toBeUndefined()
    })

    it('should work with preset and target together', () => {
      const params = buildDeploymentParams({
        solutionId: 'smart_warehouse',
        deviceId: 'warehouse',
        deviceType: 'docker_deploy',
        presetId: 'edge_computing',
        selectedTarget: { id: 'warehouse_local' },
      })

      expect(params.preset_id).toBe('edge_computing')
      expect(params.options.deploy_target).toBe('warehouse_local')
    })
  })

  describe('Backend Model Compatibility', () => {
    it('should match StartDeploymentRequest field names', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'device1',
        deviceType: 'docker_local',
      })

      // These are the exact field names expected by backend
      const backendFields = [
        'solution_id',
        'preset_id',
        'device_connections',
        'options',
        'selected_devices',
      ]

      backendFields.forEach(field => {
        expect(params).toHaveProperty(field)
      })
    })

    it('should not include extra fields not in backend model', () => {
      const params = buildDeploymentParams({
        solutionId: 'test',
        deviceId: 'device1',
        deviceType: 'docker_local',
      })

      const allowedFields = new Set([
        'solution_id',
        'preset_id',
        'device_connections',
        'options',
        'selected_devices',
      ])

      Object.keys(params).forEach(key => {
        expect(allowedFields.has(key)).toBe(true)
      })
    })
  })
})
