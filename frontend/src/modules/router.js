/**
 * Simple Client-side Router
 */

class Router {
  constructor() {
    this.routes = new Map();
    this.currentRoute = null;
    this.currentParams = {};
    this.beforeHooks = [];
    this.afterHooks = [];
  }

  register(name, handler) {
    this.routes.set(name, handler);
    return this;
  }

  beforeEach(hook) {
    this.beforeHooks.push(hook);
    return this;
  }

  afterEach(hook) {
    this.afterHooks.push(hook);
    return this;
  }

  async navigate(name, params = {}) {
    // Run before hooks
    for (const hook of this.beforeHooks) {
      const result = await hook(name, params, this.currentRoute, this.currentParams);
      if (result === false) {
        return false;
      }
    }

    const handler = this.routes.get(name);
    if (!handler) {
      console.error(`Route not found: ${name}`);
      return false;
    }

    const previousRoute = this.currentRoute;
    const previousParams = this.currentParams;

    this.currentRoute = name;
    this.currentParams = params;

    // Update URL hash
    this.updateHash(name, params);

    // Execute route handler
    try {
      await handler(params);
    } catch (error) {
      console.error(`Error navigating to ${name}:`, error);
    }

    // Run after hooks
    for (const hook of this.afterHooks) {
      await hook(name, params, previousRoute, previousParams);
    }

    return true;
  }

  updateHash(name, params) {
    let hash = `#/${name}`;
    if (params.id) {
      hash += `/${params.id}`;
    }
    if (params.subpage) {
      hash += `/${params.subpage}`;
    }
    window.history.pushState({ route: name, params }, '', hash);
  }

  parseHash(hash) {
    // Remove leading #/
    const path = hash.replace(/^#\/?/, '');
    const parts = path.split('/').filter(Boolean);

    if (parts.length === 0) {
      return { name: 'solutions', params: {} };
    }

    const name = parts[0];
    const params = {};

    if (parts.length > 1) {
      params.id = parts[1];
    }
    if (parts.length > 2) {
      params.subpage = parts[2];
    }

    return { name, params };
  }

  init() {
    // Handle browser back/forward buttons
    window.addEventListener('popstate', (event) => {
      if (event.state) {
        this.navigate(event.state.route, event.state.params);
      } else {
        const { name, params } = this.parseHash(window.location.hash);
        this.navigate(name, params);
      }
    });

    // Handle initial route
    const { name, params } = this.parseHash(window.location.hash);
    this.navigate(name, params);
  }
}

export const router = new Router();
