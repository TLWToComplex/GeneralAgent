/** 页面内的初始化记录；短期复用，刷新页面后重新向服务端确认。 */
export class AgentInitializationRegistry {
  private releases = new Map<string, Promise<unknown>>();
  private entries = new Map<string, {
    identity: string;
    readyAt: number;
    pending: boolean;
    promise: Promise<string>;
  }>();

  constructor(private ttl = 5 * 60 * 1000, private now = () => Date.now()) {}

  get(sessionId: string) {
    const entry = this.entries.get(sessionId);
    if (!entry || (!entry.pending && this.now() - entry.readyAt >= this.ttl)) return undefined;
    return {
      identity: entry.identity, promise: entry.promise,
      expiresAt: entry.pending ? undefined : entry.readyAt + this.ttl
    };
  }

  ensure(sessionId: string, identity: string, initialize: () => Promise<string>) {
    const previous = this.entries.get(sessionId);
    if (previous?.identity === identity &&
        (previous.pending || this.now() - previous.readyAt < this.ttl)) {
      return { ready: !previous.pending, promise: previous.promise };
    }

    const entry = { identity, readyAt: 0, pending: true, promise: null as unknown as Promise<string> };
    // 同一沙盒切换配置时按顺序绑定，避免旧初始化晚完成覆盖新配置。
    const before = previous?.pending ? previous.promise.catch(() => {}) :
      (this.releases.get(sessionId) ?? Promise.resolve());
    entry.promise = before.then(initialize).then((id) => {
      entry.pending = false;
      entry.readyAt = this.now();
      return id;
    }, (error) => {
      if (this.entries.get(sessionId) === entry) this.entries.delete(sessionId);
      throw error;
    });
    this.entries.set(sessionId, entry);
    return { ready: false, promise: entry.promise };
  }

  invalidate(sessionId: string, release: () => Promise<unknown> = () => Promise.resolve()): Promise<unknown> {
    const releasing = this.releases.get(sessionId);
    if (releasing && !this.entries.has(sessionId)) return releasing;
    const entry = this.entries.get(sessionId);
    this.entries.delete(sessionId);
    // 释放应等待该会话的创建结束，避免先释放、后创建遗留容器。
    const promise = (entry?.promise.catch(() => {}) ?? releasing ?? Promise.resolve())
      .then(release).finally(() => {
        if (this.releases.get(sessionId) === promise) this.releases.delete(sessionId);
      });
    this.releases.set(sessionId, promise);
    return promise;
  }
}
