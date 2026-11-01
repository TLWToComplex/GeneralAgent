const TAB_SCOPE_ID_KEY = 'mcp-tab-scope-id';
const TAB_FRESH_WORKSPACE_KEY = 'mcp-tab-fresh-workspace';
const TAB_SYNC_CHANNEL = 'aisix-tab-sync';
const TAB_WORKSPACE_PREFIX = 'mcp-tab::';
const LOGOUT_BROADCAST_KEY = 'mcp-auth-logout-broadcast';
const TAB_SCOPE_OWNER_PREFIX = 'mcp-tab-scope-owner::';
const TAB_SCOPE_HEARTBEAT_MS = 5000;
const TAB_SCOPE_OWNER_TTL_MS = 15000;

export const GLOBAL_LOGOUT_EVENT = 'mcp-global-auth-logout';

type TabSyncMessage =
  | { type: 'scope:probe'; scopeId: string; probeId: string; bootId: string }
  | { type: 'scope:occupied'; scopeId: string; probeId: string; bootId: string }
  | { type: 'auth:logout'; id: string; reason?: string; ts: number };

const createId = (): string => {
  const uuid = (globalThis as any)?.crypto?.randomUUID?.();
  if (typeof uuid === 'string' && uuid) {
    return uuid;
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

class TabScopeService {
  private bootId = createId();
  private currentScopeId = '';
  private initPromise: Promise<string> | null = null;
  private initialized = false;
  private channel: BroadcastChannel | null = null;
  private pendingScopeProbes = new Map<string, (occupied: boolean) => void>();
  private heartbeatTimer: number | null = null;
  private freshWorkspace = true;

  private getNavigationType(): string {
    try {
      const entry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
      if (entry?.type) {
        return entry.type;
      }
    } catch {}

    const legacyNavigation = (performance as any)?.navigation;
    if (legacyNavigation?.type === 1) {
      return 'reload';
    }
    return 'navigate';
  }

  private getScopeOwnerKey(scopeId: string): string {
    return `${TAB_SCOPE_OWNER_PREFIX}${scopeId}`;
  }

  private readScopeOwner(scopeId: string): { bootId: string; ts: number } | null {
    try {
      const raw = localStorage.getItem(this.getScopeOwnerKey(scopeId));
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw) as { bootId?: string; ts?: number };
      if (!parsed?.bootId || typeof parsed.ts !== 'number') {
        return null;
      }
      return { bootId: parsed.bootId, ts: parsed.ts };
    } catch {
      return null;
    }
  }

  private isOwnerAlive(owner: { bootId: string; ts: number } | null): boolean {
    if (!owner) {
      return false;
    }
    return Date.now() - owner.ts <= TAB_SCOPE_OWNER_TTL_MS;
  }

  private writeScopeOwner(scopeId: string): void {
    try {
      localStorage.setItem(this.getScopeOwnerKey(scopeId), JSON.stringify({ bootId: this.bootId, ts: Date.now() }));
    } catch {}
  }

  private cleanupScopeOwner = () => {
    const scopeId = this.currentScopeId || sessionStorage.getItem(TAB_SCOPE_ID_KEY) || '';
    if (!scopeId) {
      return;
    }
    try {
      const owner = this.readScopeOwner(scopeId);
      if (owner?.bootId === this.bootId) {
        localStorage.removeItem(this.getScopeOwnerKey(scopeId));
      }
    } catch {}
  };

  private startHeartbeat(scopeId: string): void {
    if (this.heartbeatTimer !== null) {
      window.clearInterval(this.heartbeatTimer);
    }
    this.writeScopeOwner(scopeId);
    this.heartbeatTimer = window.setInterval(() => {
      this.writeScopeOwner(scopeId);
    }, TAB_SCOPE_HEARTBEAT_MS);
  }

  private setupListeners(): void {
    if (this.initialized) {
      return;
    }
    this.initialized = true;

    if (typeof BroadcastChannel !== 'undefined') {
      this.channel = new BroadcastChannel(TAB_SYNC_CHANNEL);
      this.channel.addEventListener('message', this.handleChannelMessage);
    }

    window.addEventListener('storage', this.handleStorageEvent);
    window.addEventListener('pagehide', this.cleanupScopeOwner);
    window.addEventListener('beforeunload', this.cleanupScopeOwner);
  }

  private handleChannelMessage = (event: MessageEvent<TabSyncMessage>) => {
    const message = event.data;
    if (!message || typeof message !== 'object') {
      return;
    }

    if (message.type === 'scope:probe') {
      if (message.scopeId && message.scopeId === this.getScopeId()) {
        this.channel?.postMessage({
          type: 'scope:occupied',
          scopeId: message.scopeId,
          probeId: message.probeId,
          bootId: this.bootId
        } satisfies TabSyncMessage);
      }
      return;
    }

    if (message.type === 'scope:occupied') {
      const resolve = this.pendingScopeProbes.get(message.probeId);
      if (resolve) {
        this.pendingScopeProbes.delete(message.probeId);
        resolve(true);
      }
      return;
    }

    if (message.type === 'auth:logout') {
      this.dispatchGlobalLogout(message.reason);
    }
  };

  private handleStorageEvent = (event: StorageEvent) => {
    if (event.key !== LOGOUT_BROADCAST_KEY || !event.newValue) {
      return;
    }
    this.dispatchGlobalLogout();
  };

  private dispatchGlobalLogout(reason?: string): void {
    window.dispatchEvent(new CustomEvent(GLOBAL_LOGOUT_EVENT, { detail: { reason: reason || 'remote' } }));
  }

  private removeWorkspaceKeysExcept(scopeId: string): void {
    const toRemove: string[] = [];
    for (let i = 0; i < sessionStorage.length; i += 1) {
      const key = sessionStorage.key(i);
      if (!key || !key.startsWith(TAB_WORKSPACE_PREFIX)) {
        continue;
      }
      if (!key.startsWith(`${TAB_WORKSPACE_PREFIX}${scopeId}::`)) {
        toRemove.push(key);
      }
    }
    toRemove.forEach((key) => sessionStorage.removeItem(key));
  }

  private async detectDuplicatedScope(scopeId: string): Promise<boolean> {
    if (!scopeId) {
      return false;
    }

    const existingOwner = this.readScopeOwner(scopeId);
    if (this.isOwnerAlive(existingOwner) && existingOwner?.bootId !== this.bootId) {
      return true;
    }

    if (!this.channel) {
      return false;
    }

    const probeId = createId();
    const duplicated = await new Promise<boolean>((resolve) => {
      const done = (occupied: boolean) => resolve(occupied);
      this.pendingScopeProbes.set(probeId, done);
      this.channel?.postMessage({
        type: 'scope:probe',
        scopeId,
        probeId,
        bootId: this.bootId
      } satisfies TabSyncMessage);

      window.setTimeout(() => {
        if (this.pendingScopeProbes.has(probeId)) {
          this.pendingScopeProbes.delete(probeId);
          resolve(false);
        }
      }, 250);
    });

    return duplicated;
  }

  async init(): Promise<string> {
    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = (async () => {
      this.setupListeners();

      const existingScopeId = sessionStorage.getItem(TAB_SCOPE_ID_KEY);
      const navigationType = this.getNavigationType();
      let scopeId = existingScopeId || createId();
      const duplicated = await this.detectDuplicatedScope(scopeId);
      if (duplicated) {
        scopeId = createId();
      }

      sessionStorage.setItem(TAB_SCOPE_ID_KEY, scopeId);
      this.freshWorkspace = !existingScopeId && navigationType !== 'reload';
      if (duplicated) {
        this.freshWorkspace = true;
      }
      sessionStorage.setItem(TAB_FRESH_WORKSPACE_KEY, this.freshWorkspace ? '1' : '0');
      this.currentScopeId = scopeId;
      this.removeWorkspaceKeysExcept(scopeId);
      this.startHeartbeat(scopeId);
      return scopeId;
    })();

    return this.initPromise;
  }

  getScopeId(): string {
    if (this.currentScopeId) {
      return this.currentScopeId;
    }
    const scopeId = sessionStorage.getItem(TAB_SCOPE_ID_KEY) || '';
    if (scopeId) {
      this.currentScopeId = scopeId;
      return scopeId;
    }
    const next = createId();
    sessionStorage.setItem(TAB_SCOPE_ID_KEY, next);
    this.currentScopeId = next;
    return next;
  }

  getWorkspaceKey(name: string): string {
    return `${TAB_WORKSPACE_PREFIX}${this.getScopeId()}::${name}`;
  }

  shouldHydrateLegacyWorkspace(): boolean {
    const stored = sessionStorage.getItem(TAB_FRESH_WORKSPACE_KEY);
    if (stored === '1') {
      return false;
    }
    if (stored === '0') {
      return true;
    }
    return !this.freshWorkspace;
  }

  broadcastLogout(reason?: string): void {
    const payload = { type: 'auth:logout', id: createId(), reason, ts: Date.now() } satisfies TabSyncMessage;
    this.channel?.postMessage(payload);
    try {
      localStorage.setItem(LOGOUT_BROADCAST_KEY, JSON.stringify(payload));
    } catch (error) {
      console.warn('写入登出广播失败:', error);
    }
    this.dispatchGlobalLogout(reason || 'local');
  }
}

const tabScopeService = new TabScopeService();

export const initTabScope = () => tabScopeService.init();
export const getTabScopeId = () => tabScopeService.getScopeId();
export const getTabWorkspaceKey = (name: string) => tabScopeService.getWorkspaceKey(name);
export const shouldHydrateLegacyWorkspace = () => tabScopeService.shouldHydrateLegacyWorkspace();
export const broadcastGlobalLogout = (reason?: string) => tabScopeService.broadcastLogout(reason);

export default tabScopeService;
