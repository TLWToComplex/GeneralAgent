type Standby = {
  agent: string;
  identity: string;
  session: string;
  ready: boolean;
  expiresAt: number;
  promise: Promise<void>;
  timer?: ReturnType<typeof setTimeout>;
};

/** 只持有未交给用户的空白会话，按智能体隔离并限制后台资源。 */
export class AgentStandbyPool {
  private entries = new Map<string, Standby>();
  private active = '';
  private failures = new Map<string, number>();

  constructor(private options: {
    createId: () => string;
    initialize: (session: string, agent: string, identity: string) => Promise<string>;
    release: (session: string) => void;
    identity: (agent: string) => string;
    capacity?: number;
    ttl?: number;
  }) {}

  activate(agent: string) { this.active = agent; }

  warm(agent: string): Promise<void> {
    if (!agent) return Promise.resolve();
    const identity = this.options.identity(agent);
    const existing = this.entries.get(agent);
    if (existing?.identity === identity && (!existing.ready || existing.expiresAt > Date.now())) return existing.promise;
    if (existing) this.remove(existing);
    if ((this.failures.get(identity) || 0) > Date.now()) return Promise.resolve();
    const session = this.options.createId();
    return this.add(agent, identity, session, this.options.initialize(session, agent, identity));
  }

  /** 收回切走的空白会话，保留其原请求；它优先于另建的备用会话。 */
  retain(agent: string, session: string, initialization: {
    identity: string; promise: Promise<string>; expiresAt?: number;
  }) {
    const existing = this.entries.get(agent);
    if (existing?.session === session) return;
    if (existing) this.remove(existing);
    void this.add(agent, initialization.identity, session, initialization.promise, initialization.expiresAt);
  }

  private add(agent: string, identity: string, session: string,
      initialization: Promise<string>, expiresAt?: number): Promise<void> {
    while (this.entries.size >= (this.options.capacity ?? 3)) {
      const oldest = this.entries.values().next().value as Standby;
      this.remove(oldest);
    }
    const entry: Standby = {
      agent, identity, session, ready: false, expiresAt: 0,
      promise: Promise.resolve()
    };
    this.entries.set(agent, entry);
    entry.promise = initialization.then(() => {
      if (this.entries.get(agent) !== entry) return;
      entry.ready = true;
      entry.expiresAt = Math.min(expiresAt ?? Infinity, Date.now() + (this.options.ttl ?? 4 * 60 * 1000));
      entry.timer = setTimeout(() => {
        if (this.entries.get(agent) !== entry) return;
        this.remove(entry);
        if (this.active === agent) void this.warm(agent);
      }, Math.max(0, entry.expiresAt - Date.now()));
      entry.timer.unref?.();
    }).catch(() => {
      if (this.entries.get(agent) !== entry) return;
      this.failures.set(identity, Date.now() + 30_000);
      this.remove(entry);
      // 暂时失败只退避当前智能体，不永久关闭整个池。
      if (this.active === agent) {
        const timer = setTimeout(() => {
          if (this.active === agent) void this.warm(agent);
        }, 30_000);
        timer.unref?.();
      }
    });
    return entry.promise;
  }

  take(agent: string): string {
    const entry = this.entries.get(agent);
    if (!entry) return '';
    if (entry.identity !== this.options.identity(agent) || (entry.ready && entry.expiresAt <= Date.now())) {
      this.remove(entry);
      return '';
    }
    this.entries.delete(agent);
    clearTimeout(entry.timer);
    // 初始化中的条目也可接管；调用方通过同一个 registry 等待，不重复请求。
    this.active = agent;
    void this.warm(agent);
    return entry.session;
  }

  discard() {
    this.active = '';
    for (const entry of this.entries.values()) this.remove(entry);
    this.failures.clear();
  }

  private remove(entry: Standby) {
    this.entries.delete(entry.agent);
    clearTimeout(entry.timer);
    this.options.release(entry.session);
  }
}
