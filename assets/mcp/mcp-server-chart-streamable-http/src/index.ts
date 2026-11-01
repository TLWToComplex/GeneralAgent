import express from 'express';
import { render } from '@antv/gpt-vis-ssr';
import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

const app = express();
const port = Number(process.env.RENDER_PORT || 8999);

app.use(express.json());

const imageDir = path.join(__dirname, 'images');
if (!fs.existsSync(imageDir)) {
  fs.mkdirSync(imageDir, { recursive: true });
}
app.use('/images', express.static(imageDir));

app.post('/render-chart', async (req, res) => {
  try {
    const options = req.body;
    const vis = await render(options);
    const buffer = await vis.toBuffer();

    const filename = `${uuidv4()}.png`;
    const filePath = path.join(imageDir, filename);
    fs.writeFileSync(filePath, buffer);

    const hostname = req.hostname || 'localhost';
    const protocol = req.secure ? 'https' : 'http';
    const imageUrl = `${protocol}://${hostname}:${port}/images/${filename}`;

    res.json({
      success: true,
      resultObj: imageUrl,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      errorMessage: error instanceof Error ? error.message : String(error),
    });
  }
});

app.listen(port, () => {
  console.log(`render API: http://localhost:${port}/render-chart`);
  console.log(`image URL: http://localhost:${port}/images/[filename]`);
});
