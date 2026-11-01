/** Bounded LRU for generated HTML. Limits count and UTF-16 code units, not heap bytes. */
export class MarkdownRenderCache {
  private entries = new Map<string, string>();
  private characters = 0;

  constructor(private maxEntries = 64, private maxCharacters = 512 * 1024) {}

  get(key: string): string | undefined {
    const value = this.entries.get(key);
    if (value !== undefined) {
      this.entries.delete(key);
      this.entries.set(key, value);
    }
    return value;
  }

  set(key: string, value: string): void {
    const previous = this.entries.get(key);
    if (previous !== undefined) {
      this.characters -= key.length + previous.length;
      this.entries.delete(key);
    }
    const size = key.length + value.length;
    if (size > this.maxCharacters) return;
    this.entries.set(key, value);
    this.characters += size;
    while (this.entries.size > this.maxEntries || this.characters > this.maxCharacters) {
      const oldest = this.entries.keys().next().value!;
      this.characters -= oldest.length + this.entries.get(oldest)!.length;
      this.entries.delete(oldest);
    }
  }

  clear(): void {
    this.entries.clear();
    this.characters = 0;
  }
}
