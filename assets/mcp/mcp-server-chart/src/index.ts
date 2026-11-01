import express from 'express';
import { render } from '@antv/gpt-vis-ssr';
import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

const app = express();
const port = 8999;

// 添加详细的请求日志中间件
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  console.log('请求头:', JSON.stringify(req.headers, null, 2));
  if (req.method !== 'GET') {
    console.log('请求体:', JSON.stringify(req.body, null, 2));
  }
  next();
});

app.use(express.json());

// 静态文件服务，暴露图片目录
const imageDir = path.join(__dirname, 'images');
console.log(`图片目录路径: ${imageDir}`);
if (!fs.existsSync(imageDir)) {
  console.log('图片目录不存在，创建目录');
  fs.mkdirSync(imageDir, { recursive: true });
}
app.use('/images', express.static(imageDir));

app.post('/render-chart', async (req, res) => {
  try {
    console.log('==================== 接收到渲染请求 ====================');
    console.log('接收到的请求参数:', JSON.stringify(req.body, null, 2));
    const options = req.body;
    
    console.log('开始渲染图表...');
    const vis = await render(options);
    console.log('图表渲染完成，转换为Buffer');
    const buffer = await vis.toBuffer();

    // 生成唯一文件名
    const filename = `${uuidv4()}.png`;
    console.log(`生成的文件名: ${filename}`);

    // 图片存放目录（确保存在）
    if (!fs.existsSync(imageDir)) {
      console.log('图片目录不存在，创建目录');
      fs.mkdirSync(imageDir, { recursive: true });
    }

    // 写入图片文件
    const filePath = path.join(imageDir, filename);
    console.log(`写入图片到: ${filePath}`);
    fs.writeFileSync(filePath, buffer);

    // 返回图片URL
    const hostname = req.hostname || 'localhost';
    const protocol = req.secure ? 'https' : 'http';
    const imageUrl = `${protocol}://${hostname}:${port}/images/${filename}`;
    console.log(`生成的图片URL: ${imageUrl}`);

    res.json({
      success: true,
      resultObj: imageUrl,
    });
    console.log('渲染请求处理完成');
  } catch (error) {
    console.error('渲染错误详情:', error);
    if (error instanceof Error) {
      console.error('错误堆栈:', error.stack);
    }
    res.status(500).json({ 
      success: false, 
      errorMessage: error instanceof Error ? error.message : String(error) 
    });
  }
});

// 添加404处理中间件
app.use((req, res, next) => {
  console.error(`[404] 未找到路由: ${req.method} ${req.url}`);
  res.status(404).json({ success: false, errorMessage: '未找到请求的路由' });
});

// 添加错误处理中间件
app.use((err, req, res, next) => {
  console.error('服务器错误:', err);
  console.error('错误堆栈:', err.stack);
  res.status(500).json({ success: false, errorMessage: err.message });
});

app.listen(port, () => {
  console.log('====================================');
  console.log(`服务器已启动，运行在 http://localhost:${port}`);
  console.log(`渲染API接口: http://localhost:${port}/render-chart`);
  console.log(`图片访问路径: http://localhost:${port}/images/[filename]`);
  console.log(`当前工作目录: ${process.cwd()}`);
  console.log(`环境变量: NODE_ENV=${process.env.NODE_ENV}`);
  console.log('====================================');
});
