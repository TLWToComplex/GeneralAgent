<!--
  图标精灵本体 —— 挂在 App 根部一次，全站靠 <use href="#i-xxx"> 引用。
  等价迁移自原型 console.html 第 15–43 行，symbol 内容一字未改。
  位置：直接放在 body 下（不走 .shell 布局），由 console.css 的 .sprite 规则隐藏。
-->
<template>
  <svg class="sprite" aria-hidden="true" focusable="false">
    <symbol id="i-grid" viewBox="0 0 24 24"><rect x="3" y="3" width="7.6" height="7.6" rx="2.2" /><rect x="13.4" y="3" width="7.6" height="7.6" rx="2.2" /><rect x="3" y="13.4" width="7.6" height="7.6" rx="2.2" /><rect x="13.4" y="13.4" width="7.6" height="7.6" rx="2.2" /></symbol>
    <symbol id="i-term" viewBox="0 0 24 24"><rect x="2.6" y="4" width="18.8" height="16" rx="3.2" /><path d="M6.6 9.4l3 2.9-3 2.9" /><path d="M12.6 15.4h5" /></symbol>
    <symbol id="i-agent" viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.4" /><path d="M4.9 20a7.1 7.1 0 0 1 14.2 0" /></symbol>
    <symbol id="i-model" viewBox="0 0 24 24"><path d="M12 2.9l8.1 4.5v9.2L12 21.1 3.9 16.6V7.4z" /><path d="M12 12l8.1-4.6M12 12v9.1M12 12L3.9 7.4" /></symbol>
    <symbol id="i-mirror" viewBox="0 0 24 24"><path d="M3.5 7.7L12 3.2l8.5 4.5v8.6L12 20.8 3.5 16.3z" /><path d="M3.5 7.7L12 12.2l8.5-4.5M12 12.2v8.6" /><path d="M12 12.2V3.2" /></symbol>
    <symbol id="i-spark" viewBox="0 0 24 24"><path d="M11 3.2l1.8 4.9 4.9 1.8-4.9 1.8L11 16.6 9.2 11.7 4.3 9.9l4.9-1.8z" /><path d="M18 15.4l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z" /></symbol>
    <symbol id="i-book" viewBox="0 0 24 24"><path d="M4.2 5.4A2.2 2.2 0 0 1 6.4 3.2H19v15.5H6.4a2.2 2.2 0 0 0-2.2 2.2z" /><path d="M4.2 5.4v15.5" /></symbol>
    <symbol id="i-plug" viewBox="0 0 24 24"><path d="M9 3.2v5.2M15 3.2v5.2" /><path d="M6.5 8.4h11v2.9a5.5 5.5 0 0 1-11 0z" /><path d="M12 16.6V20.8" /></symbol>
    <symbol id="i-tool" viewBox="0 0 24 24"><path d="M14.6 3.4a4.6 4.6 0 0 0-4.2 7.5L3.6 17.7l2.7 2.7 6.8-6.8a4.6 4.6 0 0 0 5.5-7.4l-2.6 2.6-2.6-.6-.6-2.6z" /></symbol>
    <symbol id="i-learn" viewBox="0 0 24 24"><path d="M12 3.8l9 4.5-9 4.5-9-4.5z" /><path d="M6.6 10.9v4.5c0 1.4 2.4 2.6 5.4 2.6s5.4-1.2 5.4-2.6v-4.5" /></symbol>
    <symbol id="i-pulse" viewBox="0 0 24 24"><path d="M2.8 12.6h3.9l2.2-6.2 3.4 12.2 2.4-8.2 1.8 4h4.7" /></symbol>
    <symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 2.9l7.3 2.9v6.4c0 4.4-3 7.6-7.3 9.1-4.3-1.5-7.3-4.7-7.3-9.1V5.8z" /><path d="M8.9 12.2l2.2 2.2 4.1-4.4" /></symbol>
    <symbol id="i-search" viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="6.5" /><path d="M15.7 15.7l4.7 4.7" /></symbol>
    <symbol id="i-bell" viewBox="0 0 24 24"><path d="M6.5 10.5a5.5 5.5 0 0 1 11 0c0 3.3.9 4.9 1.8 5.8H4.7c.9-.9 1.8-2.5 1.8-5.8z" /><path d="M10.4 19.3a1.9 1.9 0 0 0 3.2 0" /></symbol>
    <symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5.3v13.4M5.3 12h13.4" /></symbol>
    <symbol id="i-minus" viewBox="0 0 24 24"><path d="M5.3 12h13.4" /></symbol>
    <symbol id="i-chev" viewBox="0 0 24 24"><path d="M14.5 5.5L8 12l6.5 6.5" /></symbol>
    <symbol id="i-list" viewBox="0 0 24 24"><path d="M4 6.6h16M4 12h16M4 17.4h16" /></symbol>
    <symbol id="i-cards" viewBox="0 0 24 24"><rect x="3" y="4.2" width="18" height="6.2" rx="2.2" /><rect x="3" y="13.6" width="18" height="6.2" rx="2.2" /></symbol>
    <symbol id="i-cube" viewBox="0 0 24 24"><path d="M12 3.2l9 5v7.6l-9 5-9-5V8.2z" /><path d="M12 12.2l9-5M12 12.2v8.6M12 12.2L3 7.2" /></symbol>
    <symbol id="i-eye" viewBox="0 0 24 24"><path d="M2.7 12S6.1 6.5 12 6.5 21.3 12 21.3 12 17.9 17.5 12 17.5 2.7 12 2.7 12z" /><circle cx="12" cy="12" r="2.7" /></symbol>
    <symbol id="i-pause" viewBox="0 0 24 24"><path d="M9.4 5.6v12.8M14.6 5.6v12.8" /></symbol>
    <symbol id="i-play" viewBox="0 0 24 24"><path d="M8.2 5.4l9.8 6.6-9.8 6.6z" /></symbol>
    <symbol id="i-restart" viewBox="0 0 24 24"><path d="M20.2 12a8.2 8.2 0 1 1-2.7-6.1" /><path d="M20.2 4.4V10h-5.5" /></symbol>
    <symbol id="i-x" viewBox="0 0 24 24"><path d="M6.5 6.5l11 11M17.5 6.5l-11 11" /></symbol>
    <symbol id="i-gauge" viewBox="0 0 24 24"><path d="M4 17.5a8 8 0 1 1 16 0" /><path d="M12 17.5l4.2-5.6" /></symbol>
    <symbol id="i-download" viewBox="0 0 24 24"><path d="M12 3.4v11.2" /><path d="M7.6 10.6L12 15l4.4-4.4" /><path d="M4.6 19.6h14.8" /></symbol>
  </svg>
</template>