/** 让出主线程任务（nextTick/Promise 仅让出微任务，不能保证浏览器处理绘制和输入）。 */
export async function yieldToBrowser(): Promise<void> {
  const scheduler = (globalThis as typeof globalThis & {
    scheduler?: { yield?: () => Promise<void> };
  }).scheduler;
  if (scheduler?.yield) {
    await scheduler.yield();
  } else {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  }
}
