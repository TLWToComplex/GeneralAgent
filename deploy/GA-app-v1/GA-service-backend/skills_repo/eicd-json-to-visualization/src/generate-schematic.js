#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const jsonFile = 'd:\\trae\\商飞\\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json';
const jsonData = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));

const svgWidth = 900;
const svgHeight = 650;

let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${svgWidth}" height="${svgHeight}" viewBox="0 0 ${svgWidth} ${svgHeight}">
  <defs>
    <g id="ground-symbol">
      <line x1="0" y1="0" x2="0" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-10" y1="15" x2="10" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-6" y1="20" x2="6" y2="20" stroke="black" stroke-width="1"/>
      <line x1="-3" y1="25" x2="3" y2="25" stroke="black" stroke-width="1"/>
    </g>
  </defs>

  <rect width="100%" height="100%" fill="white"/>
  <text x="20" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#333">Layout Result</text>
  <rect x="10" y="45" width="880" height="590" fill="#fafafa" stroke="#ccc" stroke-width="1"/>
`;

const interfaces = jsonData.interfaces;
const equipment2501U2201 = jsonData.equipments.find(e => e.devId === '2501U2201');
const equipment2501U2203 = jsonData.equipments.find(e => e.devId === '2501U2203');

svg += `
  <!-- 2501U2201 设备框 -->
  <rect x="550" y="80" width="140" height="160" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="620" y="100" font-family="Arial" font-size="10" text-anchor="middle" fill="black">${equipment2501U2201.devNameCn}</text>
  <text x="620" y="115" font-family="Arial" font-size="9" text-anchor="middle" fill="black">${equipment2501U2201.devId}</text>

  <!-- 2501U2201 连接器 J1 (左侧) -->
  <rect x="530" y="120" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="540" y="165" font-family="Arial" font-size="9" text-anchor="middle" fill="black" transform="rotate(-90 540 165)">J1</text>

  <circle cx="550" cy="130" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="555" y="128" font-family="Arial" font-size="8" fill="black">A</text>
  <text x="700" y="133" font-family="Arial" font-size="8" fill="black">DC PWR IN</text>

  <circle cx="550" cy="150" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="555" y="148" font-family="Arial" font-size="8" fill="black">B</text>
  <text x="700" y="153" font-family="Arial" font-size="8" fill="black">DC GND</text>

  <circle cx="550" cy="170" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="555" y="168" font-family="Arial" font-size="8" fill="black">C</text>
  <text x="700" y="173" font-family="Arial" font-size="8" fill="black">GROUNDING</text>

  <text x="620" y="255" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">${equipment2501U2201.devId}</text>
`;

svg += `
  <!-- 2501U2203 设备框 -->
  <rect x="550" y="350" width="140" height="160" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="620" y="370" font-family="Arial" font-size="10" text-anchor="middle" fill="black">${equipment2501U2203.devNameCn}</text>
  <text x="620" y="385" font-family="Arial" font-size="9" text-anchor="middle" fill="black">${equipment2501U2203.devId}</text>

  <!-- 2501U2203 连接器 J1 (左侧) -->
  <rect x="530" y="390" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="540" y="435" font-family="Arial" font-size="9" text-anchor="middle" fill="black" transform="rotate(-90 540 435)">J1</text>

  <circle cx="550" cy="400" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="555" y="398" font-family="Arial" font-size="8" fill="black">A</text>
  <text x="700" y="403" font-family="Arial" font-size="8" fill="black">DC PWR IN</text>

  <circle cx="550" cy="420" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="555" y="418" font-family="Arial" font-size="8" fill="black">B</text>
  <text x="700" y="423" font-family="Arial" font-size="8" fill="black">DC GND</text>

  <circle cx="550" cy="440" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="555" y="438" font-family="Arial" font-size="8" fill="black">C</text>
  <text x="700" y="443" font-family="Arial" font-size="8" fill="black">GROUNDING</text>

  <text x="620" y="525" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">${equipment2501U2203.devId}</text>
`;

svg += `
  <!-- RPDU1 设备框 -->
  <rect x="60" y="80" width="140" height="160" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="130" y="110" font-family="Arial" font-size="10" text-anchor="middle" fill="black">RPDU1_SSPC_J3_08</text>

  <!-- RPDU1 连接器 J3 (右侧) -->
  <rect x="200" y="120" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="210" y="165" font-family="Arial" font-size="9" text-anchor="middle" fill="black" transform="rotate(-90 210 165)">J3</text>

  <circle cx="220" cy="145" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="195" y="142" font-family="Arial" font-size="8" text-anchor="end" fill="black">10</text>

  <text x="130" y="255" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">RPDU1</text>
`;

svg += `
  <!-- RPDU2 设备框 -->
  <rect x="60" y="350" width="140" height="160" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="130" y="380" font-family="Arial" font-size="10" text-anchor="middle" fill="black">RPDU2_SSPC_J4_10</text>

  <!-- RPDU2 连接器 J4 (右侧) -->
  <rect x="200" y="390" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="210" y="435" font-family="Arial" font-size="9" text-anchor="middle" fill="black" transform="rotate(-90 210 435)">J4</text>

  <circle cx="220" cy="415" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="195" y="412" font-family="Arial" font-size="8" text-anchor="end" fill="black">10</text>

  <text x="130" y="525" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">RPDU2</text>
`;

svg += `
  <!-- GND 符号 - RPDU1 下方 -->
  <use href="#ground-symbol" x="130" y="240"/>
  <text x="130" y="275" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-601</text>

  <use href="#ground-symbol" x="130" y="300"/>
  <text x="130" y="335" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-600</text>

  <!-- GND 符号 - RPDU2 下方 -->
  <use href="#ground-symbol" x="130" y="540"/>
  <text x="130" y="575" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-602</text>

  <use href="#ground-symbol" x="130" y="600"/>
  <text x="130" y="635" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-603</text>
`;

svg += `
  <!-- 电源连接线: RPDU1 J3-10 -> 2501U2201 J1-A -->
  <polyline points="220,145 280,145 280,130 530,130" fill="none" stroke="black" stroke-width="1"/>
  <text x="320" y="140" font-family="Arial" font-size="9" fill="black">1LN ESS D N</text>

  <!-- GND-601 -> 2501U2201 J1-B (DC GND) -->
  <polyline points="130,255 130,300 400,300 400,150 530,150" fill="none" stroke="black" stroke-width="1"/>
  <text x="250" y="295" font-family="Arial" font-size="9" fill="black">CG ESS Z N</text>

  <!-- GND-600 -> 2501U2201 J1-C (GROUNDING) -->
  <polyline points="130,315 130,330 440,330 440,170 530,170" fill="none" stroke="black" stroke-width="1"/>
  <text x="300" y="325" font-family="Arial" font-size="9" fill="black">CG A</text>

  <!-- 电源连接线: RPDU2 J4-10 -> 2501U2203 J1-A -->
  <polyline points="220,415 280,415 280,400 530,400" fill="none" stroke="black" stroke-width="1"/>
  <text x="320" y="410" font-family="Arial" font-size="9" fill="black">1LN ESS D N</text>

  <!-- GND-602 -> 2501U2203 J1-B (DC GND) -->
  <polyline points="130,555 130,600 400,600 400,420 530,420" fill="none" stroke="black" stroke-width="1"/>
  <text x="250" y="595" font-family="Arial" font-size="9" fill="black">CG ESS Z N</text>

  <!-- GND-603 -> 2501U2203 J1-C (GROUNDING) -->
  <polyline points="130,615 130,630 440,630 440,440 530,440" fill="none" stroke="black" stroke-width="1"/>
  <text x="300" y="625" font-family="Arial" font-size="9" fill="black">CG A</text>
`;

svg += '</svg>';

const baseName = path.basename(jsonFile, path.extname(jsonFile));
const svgFile = path.join(path.dirname(jsonFile), `${baseName}_schematic.svg`);
fs.writeFileSync(svgFile, svg, 'utf8');

console.log('SVG已保存:', svgFile);
console.log('文件大小:', fs.statSync(svgFile).size, '字节');
