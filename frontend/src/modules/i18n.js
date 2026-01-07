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
      purchase: 'Purchase',
      deploymentPartners: 'Deployment Partners',
      partnersDescription: 'The following partners can provide on-site deployment services for this solution.',
      contactPartner: 'Contact',
      visitWebsite: 'Website',
      becomePartner: 'Become a Partner',
      partnerRegisterHint: 'Registered partners will be featured on Seeed Studio solution pages',
    },
    deploy: {
      title: 'Deploy',
      back: 'Back to Solutions',
      devices: 'Devices',
      viewWiki: 'View Full Wiki Documentation',
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
      },
      postInstructions: 'After Deployment',
      wiring: {
        title: 'Wiring Instructions',
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
    settings: {
      title: 'Settings',
      language: 'Language',
      theme: 'Theme',
      about: 'About',
      version: 'Version',
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
      purchase: '购买',
      deploymentPartners: '部署合作伙伴',
      partnersDescription: '以下合作伙伴可为本方案提供现场部署服务。',
      contactPartner: '联系方式',
      visitWebsite: '访问官网',
      becomePartner: '成为合作伙伴',
      partnerRegisterHint: '已注册合作伙伴将有机会显示在矽递解决方案宣传页',
    },
    deploy: {
      title: '部署',
      back: '返回方案列表',
      devices: '设备',
      viewWiki: '查看完整Wiki文档',
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
      },
      postInstructions: '部署后操作',
      wiring: {
        title: '接线说明',
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
    settings: {
      title: '设置',
      language: '语言',
      theme: '主题',
      about: '关于',
      version: '版本',
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
