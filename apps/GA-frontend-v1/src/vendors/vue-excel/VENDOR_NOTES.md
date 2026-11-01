# Luckysheet Vendor Notes

This project uses Luckysheet as the Excel canvas editor.

## Runtime Entry

The app imports Luckysheet runtime files from:

- `src/vendors/vue-excel/dist/plugins/css/pluginsCss.css`
- `src/vendors/vue-excel/dist/plugins/plugins.css`
- `src/vendors/vue-excel/dist/css/luckysheet.css`
- `src/vendors/vue-excel/dist/assets/iconfont/iconfont.css`
- `src/vendors/vue-excel/dist/plugins/js/plugin.js`
- `src/vendors/vue-excel/dist/luckysheet.umd.js`

These files are imported by `src/components/chat/ExcelCanvasFullUI.vue`.

## Source Entry

The editable upstream source is kept under `src/vendors/vue-excel`:

- `src/vendors/vue-excel/src/controllers/constant.js`
  Creates the main Luckysheet DOM. `#luckysheet-wa-editor` is defined here.
- `src/vendors/vue-excel/src/controllers/resize.js`
  Moves overflowing toolbar items into the "more" menu during resize.
- `src/vendors/vue-excel/src/css/luckysheet-core.css`
  Defines the main toolbar layout styles, including `.luckysheet-wa-editor`.

## Important

The browser currently receives the built files through Vite imports from `src/vendors/vue-excel/dist`.
If you edit files under `src/vendors/vue-excel/src`, rebuild Luckysheet and copy the new `dist` output into `src/vendors/vue-excel/dist`.

For quick runtime experiments, edit `src/vendors/vue-excel/dist/css/luckysheet.css` or `src/vendors/vue-excel/dist/luckysheet.umd.js` directly.
