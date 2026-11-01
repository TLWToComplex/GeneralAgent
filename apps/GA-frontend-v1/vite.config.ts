import fs from 'node:fs';
import path, { resolve } from 'node:path';
import { execSync } from 'node:child_process';
import { defineConfig, type Plugin } from 'vite';
import vue from '@vitejs/plugin-vue';

const vendorPptRoute = '/vendors/vue-ppt/';
const vendorPptDist = resolve(__dirname, 'src/vendors/vue-ppt/dist');

const vendorMimeTypes: Record<string, string> = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2'
};

const copyDirectoryContents = (sourceDir: string, targetDir: string) => {
  fs.rmSync(targetDir, { recursive: true, force: true });
  fs.mkdirSync(targetDir, { recursive: true });
  for (const entry of fs.readdirSync(sourceDir)) {
    fs.cpSync(path.join(sourceDir, entry), path.join(targetDir, entry), { recursive: true, force: true });
  }
};

const ensureVendorPptDist = () => {
  if (!fs.existsSync(vendorPptDist)) {
    console.log('⚠️  vue-ppt dist 不存在,正在构建...');
    try {
      execSync('npm run build --workspace=pptist', { stdio: 'inherit', cwd: __dirname });
      console.log('✅ vue-ppt 构建完成');
    } catch (error) {
      console.error('❌ vue-ppt 构建失败:', error);
    }
  }
};

const createVendorPptPlugin = (): Plugin => ({
  name: 'vendor-ppt-runtime',
  configResolved() {
    ensureVendorPptDist();
  },
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const requestPath = req.url?.split('?')[0] || '';
      if (!requestPath.startsWith(vendorPptRoute)) {
        next();
        return;
      }

      const relativePath = requestPath.slice(vendorPptRoute.length) || 'embedded.html';
      const normalizedPath = path.posix.normalize(`/${relativePath}`).replace(/^\/+/, '');
      if (normalizedPath.startsWith('..')) {
        res.statusCode = 403;
        res.end('Forbidden');
        return;
      }

      const filePath = path.join(vendorPptDist, normalizedPath);
      if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
        res.statusCode = 404;
        res.end('Not Found');
        return;
      }

      const ext = path.extname(filePath).toLowerCase();
      const contentType = vendorMimeTypes[ext] || 'application/octet-stream';
      res.setHeader('Content-Type', contentType);
      fs.createReadStream(filePath).pipe(res);
    });
  },
  closeBundle() {
    const outDir = resolve(__dirname, 'dist/vendors/vue-ppt');
    if (!fs.existsSync(vendorPptDist)) return;
    copyDirectoryContents(vendorPptDist, outDir);
  }
});

export default defineConfig({
  plugins: [vue(), createVendorPptPlugin()],
  optimizeDeps: {
    entries: ['index.html'],
    include: ['@ai-sdk/vue'],
    force: true
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@vue-word': resolve(__dirname, 'src/vendors/vue-word/wordsbeat'),
      '@vue-excel': resolve(__dirname, 'src/vendors/vue-excel')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return;
          if (id.includes('monaco-editor')) return 'monaco';
          if (id.includes('echarts') || id.includes('zrender')) return 'echarts';
          if (id.includes('mermaid')) return 'mermaid';
          if (id.includes('leaflet') || id.includes('@supermapgis')) return 'map';
          return 'vendor';
        }
      }
    }
  }
});
