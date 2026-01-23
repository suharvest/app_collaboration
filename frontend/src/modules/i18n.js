/**
 * i18n - Internationalization Module
 * Supports Chinese (zh) and English (en)
 */

const translations = {
  en: {
    app: {
      title: 'SenseCraft Solution',
    },
    nav: {
      solutions: 'Solutions',
      devices: 'Devices',
      deployments: 'Deployments',
      settings: 'Settings',
    },
    solutions: {
      title: 'Available Solutions',
      empty: 'No solutions available',
      emptyDescription: 'Add solution configurations to the solutions directory',
      difficulty: {
        beginner: 'Beginner',
        intermediate: 'Intermediate',
        advanced: 'Advanced',
      },
      estimatedTime: 'Est. time',
      deployedCount: 'Deployed',
      viewDetails: 'View Details',
      startDeploy: 'Start Deployment',
      requiredDevices: 'Required Devices',
      productDetails: 'Product Details',
      deploymentPartners: 'Deployment Partners',
      partnersDescription: 'The following partners can provide on-site deployment services for this solution.',
      contactPartner: 'Contact',
      visitWebsite: 'Website',
      becomePartner: 'Become a Partner',
      partnerRegisterHint: 'Registered partners will be featured on Seeed Studio solution pages',
      // Device Configurator
      quickStart: 'Solution Description',
      orCustomize: 'or customize',
      selectedDevices: 'Selected Devices',
      productDetails: 'Product Details',
    },
    deploy: {
      title: 'Deploy',
      back: 'Back to Solutions',
      devices: 'Devices',
      viewWiki: 'View Full Wiki Documentation',
      selectMode: 'Select Deployment Mode',
      selectModeDesc: 'Choose one of the following deployment options',
      deviceStatus: {
        detected: 'Detected',
        notDetected: 'Not Detected',
        manualRequired: 'Manual Config',
        deploying: 'Deploying...',
        completed: 'Completed',
        failed: 'Failed',
      },
      status: {
        pending: 'Pending',
        ready: 'Ready',
        running: 'Deploying...',
        completed: 'Completed',
        failed: 'Failed',
      },
      actions: {
        detect: 'Detect Device',
        deploy: 'Deploy Now',
        retry: 'Retry',
        viewLogs: 'View Logs',
        markDone: 'Mark as Done',
        manual: 'Manual Step',
        auto: 'Automated Deployment',
        manualDesc: 'Complete the steps above, then click the button to mark as done.',
        autoDesc: 'Click the button below to automatically deploy this component.',
      },
      connection: {
        title: 'Connection Settings',
        host: 'Host / IP Address',
        port: 'Port',
        username: 'Username',
        password: 'Password',
        connect: 'Connect',
        test: 'Test Connection',
        selectPort: 'Select Port',
        refreshPorts: 'Refresh',
      },
      progress: {
        title: 'Deployment Progress',
        pending: 'Pending',
        running: 'Running',
        completed: 'Completed',
        failed: 'Failed',
      },
      logs: {
        title: 'Logs',
        clear: 'Clear',
        download: 'Download',
        empty: 'No logs yet',
        starting: 'Starting deployment...',
        detailed: 'Detailed',
      },
      postInstructions: 'After Deployment',
      wiring: {
        title: 'Wiring Instructions',
      },
      docker: {
        notInstalled: 'Docker Not Installed',
        installHint: 'This will automatically install Docker on the remote device. The process may take a few minutes.',
        installAction: 'Install Docker',
        fixPermissionAction: 'Fix Permission',
        startAction: 'Start Docker',
        fixAction: 'Fix Issue',
        installing: 'Installing Docker on remote device...',
        installCancelled: 'Docker installation cancelled by user',
      },
      warnings: {
        serviceSwitch: 'Deploying this application will stop any currently running applications on the device.',
        recameraSwitch: 'Deploying will stop the currently running application on reCamera to free up resources.',
        confirmDeploy: 'The current application will be stopped. Continue?',
      },
    },
    deployments: {
      title: 'Deployment History',
      empty: 'No deployments yet',
      emptyDescription: 'Deploy a solution to see deployment history',
      stats: {
        total: 'Total',
        success: 'Success',
        failed: 'Failed',
      },
    },
    devices: {
      title: 'Device Management',
      subtitle: 'Manage deployed applications',
      empty: 'No deployed applications',
      emptyDescription: 'Deploy a solution first to manage it here',
      status: {
        running: 'Running',
        stopped: 'Stopped',
        unknown: 'Unknown',
      },
      actions: {
        update: 'Update',
        restart: 'Restart',
        start: 'Start',
        stop: 'Stop',
        delete: 'Delete',
        confirmDelete: 'Are you sure you want to delete this deployment record?',
        deleted: 'Deployment record deleted',
      },
      kiosk: {
        title: 'Kiosk Mode',
        enabled: 'Kiosk Enabled',
        disabled: 'Kiosk Disabled',
        enable: 'Enable Kiosk',
        disable: 'Disable Kiosk',
        user: 'Kiosk User',
        configuring: 'Configuring...',
        rebootRequired: 'Reboot required to apply',
      },
      update: {
        updating: 'Updating...',
        success: 'Update successful',
        failed: 'Update failed',
      },
      password: {
        title: 'SSH Password Required',
        description: 'Enter SSH password for remote device',
        submit: 'Submit',
      },
      openApp: 'Open App',
    },
    settings: {
      title: 'Settings',
      language: 'Language',
      theme: 'Theme',
      about: 'About',
      version: 'Version',
    },
    preview: {
      title: 'Live Preview',
      description: 'View live video stream with inference results overlay.',
      status: {
        disconnected: 'Disconnected',
        connecting: 'Connecting...',
        connected: 'Connected',
        error: 'Connection Error',
      },
      actions: {
        connect: 'Start Preview',
        disconnect: 'Stop Preview',
      },
      connected: 'Preview connected',
      connectionFailed: 'Preview connection failed',
      inputs: {
        rtspUrl: 'RTSP Stream URL',
        rtspUrlDesc: 'URL of the RTSP video stream',
        mqttBroker: 'MQTT Broker',
        mqttBrokerDesc: 'MQTT broker hostname or IP address',
        mqttPort: 'MQTT Port',
        mqttTopic: 'MQTT Topic',
        mqttTopicDesc: 'Topic to subscribe for inference results',
      },
    },
    common: {
      loading: 'Loading...',
      error: 'Error',
      success: 'Success',
      cancel: 'Cancel',
      confirm: 'Confirm',
      save: 'Save',
      close: 'Close',
      retry: 'Retry',
      next: 'Next',
      previous: 'Previous',
    },
  },
  zh: {
    app: {
      title: 'SenseCraft 解决方案',
    },
    nav: {
      solutions: '解决方案',
      devices: '设备管理',
      deployments: '部署记录',
      settings: '设置',
    },
    solutions: {
      title: '可用方案',
      empty: '暂无可用方案',
      emptyDescription: '请在 solutions 目录中添加方案配置',
      difficulty: {
        beginner: '入门',
        intermediate: '中级',
        advanced: '高级',
      },
      estimatedTime: '预计时间',
      deployedCount: '已部署',
      viewDetails: '查看详情',
      startDeploy: '开始部署',
      requiredDevices: '所需设备',
      productDetails: '产品详情',
      deploymentPartners: '部署合作伙伴',
      partnersDescription: '以下合作伙伴可为本方案提供现场部署服务。',
      contactPartner: '联系方式',
      visitWebsite: '访问官网',
      becomePartner: '成为合作伙伴',
      partnerRegisterHint: '已注册合作伙伴将有机会显示在矽递解决方案宣传页',
      // Device Configurator
      quickStart: '方案说明',
      orCustomize: '或自定义选择',
      selectedDevices: '已选设备',
      productDetails: '产品详情',
    },
    deploy: {
      title: '部署',
      back: '返回方案列表',
      devices: '设备',
      viewWiki: '查看完整Wiki文档',
      selectMode: '选择部署方式',
      selectModeDesc: '请选择以下一种部署方式',
      deviceStatus: {
        detected: '已检测',
        notDetected: '未检测到',
        manualRequired: '需手动配置',
        deploying: '部署中...',
        completed: '已完成',
        failed: '失败',
      },
      status: {
        pending: '待处理',
        ready: '就绪',
        running: '部署中...',
        completed: '已完成',
        failed: '失败',
      },
      actions: {
        detect: '检测设备',
        deploy: '立即部署',
        retry: '重试',
        viewLogs: '查看日志',
        markDone: '标记完成',
        manual: '手动步骤',
        auto: '自动部署',
        manualDesc: '完成上述步骤后，点击按钮标记为完成。',
        autoDesc: '点击下方按钮自动部署此组件。',
      },
      connection: {
        title: '连接设置',
        host: '主机 / IP 地址',
        port: '端口',
        username: '用户名',
        password: '密码',
        connect: '连接',
        test: '测试连接',
        selectPort: '选择端口',
        refreshPorts: '刷新',
      },
      progress: {
        title: '部署进度',
        pending: '等待中',
        running: '进行中',
        completed: '已完成',
        failed: '失败',
      },
      logs: {
        title: '日志',
        clear: '清空',
        download: '下载',
        empty: '暂无日志',
        starting: '开始部署...',
        detailed: '详细',
      },
      postInstructions: '部署后操作',
      wiring: {
        title: '接线说明',
      },
      docker: {
        notInstalled: '未检测到 Docker',
        installHint: '将自动在远程设备上安装 Docker，此过程可能需要几分钟。',
        installAction: '安装 Docker',
        fixPermissionAction: '修复权限',
        startAction: '启动 Docker',
        fixAction: '修复问题',
        installing: '正在远程设备上安装 Docker...',
        installCancelled: '用户取消了 Docker 安装',
      },
      warnings: {
        serviceSwitch: '部署此应用将会停止设备上当前正在运行的应用。',
        recameraSwitch: '部署新应用将停止 reCamera 上当前运行的应用以释放资源。',
        confirmDeploy: '当前应用将被停止。是否继续？',
      },
    },
    deployments: {
      title: '部署历史',
      empty: '暂无部署记录',
      emptyDescription: '部署一个方案后将在此显示历史记录',
      stats: {
        total: '总计',
        success: '成功',
        failed: '失败',
      },
    },
    devices: {
      title: '设备管理',
      subtitle: '管理已部署的应用',
      empty: '暂无已部署应用',
      emptyDescription: '请先部署一个方案，然后在此管理',
      status: {
        running: '运行中',
        stopped: '已停止',
        unknown: '未知',
      },
      actions: {
        update: '更新',
        restart: '重启',
        start: '启动',
        stop: '停止',
        delete: '删除',
        confirmDelete: '确定删除此部署记录？',
        deleted: '已删除部署记录',
      },
      kiosk: {
        title: 'Kiosk 模式',
        enabled: 'Kiosk 已启用',
        disabled: 'Kiosk 已禁用',
        enable: '启用 Kiosk',
        disable: '禁用 Kiosk',
        user: 'Kiosk 用户',
        configuring: '配置中...',
        rebootRequired: '需要重启生效',
      },
      update: {
        updating: '更新中...',
        success: '更新成功',
        failed: '更新失败',
      },
      password: {
        title: '需要 SSH 密码',
        description: '请输入远程设备的 SSH 密码',
        submit: '提交',
      },
      openApp: '打开应用',
    },
    settings: {
      title: '设置',
      language: '语言',
      theme: '主题',
      about: '关于',
      version: '版本',
    },
    preview: {
      title: '实时预览',
      description: '查看实时视频流及推理结果叠加显示。',
      status: {
        disconnected: '未连接',
        connecting: '连接中...',
        connected: '已连接',
        error: '连接错误',
      },
      actions: {
        connect: '开始预览',
        disconnect: '停止预览',
      },
      connected: '预览已连接',
      connectionFailed: '预览连接失败',
      inputs: {
        rtspUrl: 'RTSP 视频流地址',
        rtspUrlDesc: 'RTSP 视频流的 URL 地址',
        mqttBroker: 'MQTT 服务器',
        mqttBrokerDesc: 'MQTT 服务器主机名或 IP 地址',
        mqttPort: 'MQTT 端口',
        mqttTopic: 'MQTT 主题',
        mqttTopicDesc: '订阅推理结果的主题',
      },
    },
    common: {
      loading: '加载中...',
      error: '错误',
      success: '成功',
      cancel: '取消',
      confirm: '确认',
      save: '保存',
      close: '关闭',
      retry: '重试',
      next: '下一步',
      previous: '上一步',
    },
  },
};

class I18n {
  constructor() {
    this.currentLocale = this.getSavedLocale() || this.detectLocale();
    this.listeners = [];
  }

  getSavedLocale() {
    return localStorage.getItem('locale');
  }

  detectLocale() {
    const browserLang = navigator.language.split('-')[0];
    return browserLang === 'zh' ? 'zh' : 'en';
  }

  get locale() {
    return this.currentLocale;
  }

  set locale(newLocale) {
    if (newLocale !== this.currentLocale && translations[newLocale]) {
      this.currentLocale = newLocale;
      localStorage.setItem('locale', newLocale);
      this.notifyListeners();
      this.updateDOM();
    }
  }

  toggle() {
    this.locale = this.currentLocale === 'en' ? 'zh' : 'en';
  }

  t(key, params = {}) {
    const keys = key.split('.');
    let value = translations[this.currentLocale];

    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k];
      } else {
        return key; // Return key if translation not found
      }
    }

    if (typeof value === 'string' && Object.keys(params).length > 0) {
      return value.replace(/\{(\w+)\}/g, (_, paramKey) => params[paramKey] || '');
    }

    return value || key;
  }

  // Get localized field from an object (e.g., name vs name_zh)
  getLocalizedField(obj, field) {
    if (!obj) return '';
    const localizedKey = this.currentLocale === 'zh' ? `${field}_zh` : field;
    return obj[localizedKey] || obj[field] || '';
  }

  onLocaleChange(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  notifyListeners() {
    this.listeners.forEach(cb => cb(this.currentLocale));
  }

  updateDOM() {
    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      el.textContent = this.t(key);
    });

    // Update all elements with data-i18n-placeholder attribute
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.placeholder = this.t(key);
    });

    // Update all elements with data-i18n-title attribute
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      el.title = this.t(key);
    });

    // Update HTML lang attribute
    document.documentElement.lang = this.currentLocale;
  }
}

// Export singleton instance
export const i18n = new I18n();
export const t = (key, params) => i18n.t(key, params);
export const getLocalizedField = (obj, field) => i18n.getLocalizedField(obj, field);
