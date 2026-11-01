/** Per-view source identity without hashing/copying potentially large binary files. */
export function createOfficeSourceKey() {
  const identities = new WeakMap<object, number>();
  let nextId = 0;
  return (source: string | ArrayBuffer | ArrayBufferView | null | undefined): string => {
    if (!source) return '';
    if (typeof source === 'string') return `url:${source.trim()}`;
    let id = identities.get(source);
    if (id === undefined) {
      id = ++nextId;
      identities.set(source, id);
    }
    return `binary:${id}:${source.byteLength}`;
  };
}
