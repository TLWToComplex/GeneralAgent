/** Ignore input handled by a nested scroll container, including at its edges. */
export function isNestedScrollTarget(event: Event, container: HTMLElement): boolean {
  let target = event.target instanceof Element ? event.target : null;
  while (target && target !== container) {
    const style = getComputedStyle(target);
    if (
      (/auto|scroll/.test(style.overflowY) && target.scrollHeight > target.clientHeight) ||
      (/auto|scroll/.test(style.overflowX) && target.scrollWidth > target.clientWidth)
    ) return true;
    target = target.parentElement;
  }
  return false;
}
