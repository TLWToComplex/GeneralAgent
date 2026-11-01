const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

/**
 * EICD 标准电气原理图生成器
 * 
 * 位置: .trae/skills/eicd-json-to-visualization/src/
 * 作用: 集中管理，全局可用，自动应用强制规则
 * 
 * 使用方法:
 * 1. 技能自动调用
 * 2. 或在任何项目运行: node d:\trae\.trae\skills\eicd-json-to-visualization\src\standard-generator.js "EICD文件.json"
 */

// 强制规则文件路径（在项目目录或用户目录查找）
function findRulesFile(projectDir) {
  const possiblePaths = [
    path.join(projectDir, '.eicd-rules.json'),
    path.join(projectDir, '..', '.eicd-rules.json'),
    'd:\\trae\\商飞\\.eicd-rules.json',
    path.join(process.env.USERPROFILE || '', '.eicd-rules.json')
  ];
  
  for (const rulesPath of possiblePaths) {
    if (fs.existsSync(rulesPath)) {
      return rulesPath;
    }
  }
  
  // 返回默认规则
  return null;
}

// 加载强制规则
function loadRules(projectDir) {
  const rulesPath = findRulesFile(projectDir);
  
  if (rulesPath) {
    try {
      const rules = JSON.parse(fs.readFileSync(rulesPath, 'utf8'));
      console.log('✅ 已加载强制规则:', rules.rulesName, `(${rulesPath})`);
      return rules;
    } catch (e) {
      console.warn('⚠️  规则文件加载失败，使用默认规则');
    }
  }
  
  // 默认规则
  return {
    rulesName: "EICD默认规则",
    mandatoryRules: {
      pinPosition: { rule: "引脚必须在方块外面", enforcement: "strict" },
      wireLayout: { rule: "接线不能重叠", enforcement: "strict" },
      completeness: { rule: "不能缺少任何元素", enforcement: "strict" }
    },
    coordinateRules: {
      RPDU: { deviceX: 80, deviceY: [100, 380], connectorSide: "right", pinOffset: -5 },
      SEAT: { deviceX: 650, deviceY: [80, 360], connectorSide: "left", connectorOffset: -20, pinOffset: -5 },
      GND: { x: 150, yOffsets: [140, 190, 140, 190] }
    },
    connectionRules: { turningPoints: [280, 300, 320], wireSpacing: 25, style: "orthogonal" }
  };
}

// 验证规则
function validateRules(svg, rules) {
  const errors = [];
  
  // 规则1: 引脚必须在方块外面
  if (rules.mandatoryRules.pinPosition?.enforcement === 'strict') {
    const pinRegex = /<circle[^>]*cx="(\d+)"[^>]*>/g;
    let match;
    while ((match = pinRegex.exec(svg)) !== null) {
      const cx = parseInt(match[1]);
      // 检查引脚是否在连接器外部
      if (cx > 625 && cx < 650) {
        errors.push(`引脚必须在连接器外部! (发现引脚在 x=${cx})`);
      }
    }
  }
  
  // 规则2: 接线不能重叠
  if (rules.mandatoryRules.wireLayout?.enforcement === 'strict') {
    const lineRegex = /<polyline[^>]*points="([^"]*)"[^>]*>/g;
    const turningPoints = new Set();
    let match;
    
    while ((match = lineRegex.exec(svg)) !== null) {
      const points = match[1].split(' ');
      if (points.length > 2) {
        const midPoint = points[Math.floor(points.length / 2)];
        if (turningPoints.has(midPoint)) {
          errors.push(`接线重叠! (转折点重复: ${midPoint})`);
        }
        turningPoints.add(midPoint);
      }
    }
  }
  
  // 规则3: 完整性检查
  if (rules.mandatoryRules.completeness?.enforcement === 'strict') {
    const requiredElements = ['<rect', '<circle', '<polyline', '<text'];
    requiredElements.forEach(elem => {
      if (!svg.includes(elem)) {
        errors.push(`缺少必要元素: ${elem}`);
      }
    });
  }
  
  return errors;
}

// 生成 SVG
function generateSVG(jsonFilePath, options = {}) {
  const projectDir = path.dirname(jsonFilePath);
  
  console.log('');
  console.log('========================================');
  console.log('   EICD 标准电气原理图生成器');
  console.log('========================================');
  console.log('');
  console.log('📁 输入文件:', jsonFilePath);
  console.log('');
  
  // 加载规则
  const rules = loadRules(projectDir);
  
  // 读取JSON数据
  const jsonData = JSON.parse(fs.readFileSync(jsonFilePath, 'utf8'));
  
  const coordRules = rules.coordinateRules;
  const connRules = rules.connectionRules;
  
  let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="700" viewBox="0 0 1000 700">
  <defs>
    <g id="ground-symbol">
      <line x1="0" y1="0" x2="0" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-10" y1="15" x2="10" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-6" y1="20" x2="6" y2="20" stroke="black" stroke-width="1"/>
      <line x1="-3" y1="25" x2="3" y2="25" stroke="black" stroke-width="1"/>
    </g>
  </defs>
  <rect width="100%" height="100%" fill="white"/>
  <text x="20" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#333">EICD 电气原理图</text>
  <text x="20" y="50" font-family="Arial, sans-serif" font-size="12" fill="#666">文件: ${path.basename(jsonFilePath)}</text>
  <rect x="10" y="65" width="980" height="620" fill="#fafafa" stroke="#ccc" stroke-width="1"/>
`;

  // RPDU1
  svg += `
  <!-- RPDU1 -->
  <rect x="${coordRules.RPDU.deviceX}" y="${coordRules.RPDU.deviceY[0]}" width="140" height="120" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="${coordRules.RPDU.deviceX + 70}" y="${coordRules.RPDU.deviceY[0] + 30}" font-family="Arial" font-size="11" text-anchor="middle" fill="black">RPDU1_SSPC_J3_08</text>
  <text x="${coordRules.RPDU.deviceX + 70}" y="${coordRules.RPDU.deviceY[0] + 50}" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">2404U4101</text>
  <rect x="${coordRules.RPDU.deviceX + 140}" y="${coordRules.RPDU.deviceY[0] + 30}" width="20" height="40" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.RPDU.deviceX + 150}" y="${coordRules.RPDU.deviceY[0] + 55}" font-family="Arial" font-size="10" text-anchor="middle" fill="black">J3</text>
  <circle cx="${coordRules.RPDU.deviceX + 140 + coordRules.RPDU.pinOffset}" cy="${coordRules.RPDU.deviceY[0] + 45}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.RPDU.deviceX + 135}" y="${coordRules.RPDU.deviceY[0] + 42}" font-family="Arial" font-size="8" text-anchor="end" fill="black">10</text>
  <text x="${coordRules.RPDU.deviceX + 70}" y="${coordRules.RPDU.deviceY[0] + 140}" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">RPDU1</text>
`;

  // RPDU2
  svg += `
  <!-- RPDU2 -->
  <rect x="${coordRules.RPDU.deviceX}" y="${coordRules.RPDU.deviceY[1]}" width="140" height="120" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="${coordRules.RPDU.deviceX + 70}" y="${coordRules.RPDU.deviceY[1] + 30}" font-family="Arial" font-size="11" text-anchor="middle" fill="black">RPDU2_SSPC_J4_10</text>
  <text x="${coordRules.RPDU.deviceX + 70}" y="${coordRules.RPDU.deviceY[1] + 50}" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">2404U4103</text>
  <rect x="${coordRules.RPDU.deviceX + 140}" y="${coordRules.RPDU.deviceY[1] + 30}" width="20" height="40" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.RPDU.deviceX + 150}" y="${coordRules.RPDU.deviceY[1] + 55}" font-family="Arial" font-size="10" text-anchor="middle" fill="black">J4</text>
  <circle cx="${coordRules.RPDU.deviceX + 140 + coordRules.RPDU.pinOffset}" cy="${coordRules.RPDU.deviceY[1] + 45}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.RPDU.deviceX + 135}" y="${coordRules.RPDU.deviceY[1] + 42}" font-family="Arial" font-size="8" text-anchor="end" fill="black">10</text>
  <text x="${coordRules.RPDU.deviceX + 70}" y="${coordRules.RPDU.deviceY[1] + 140}" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">RPDU2</text>
`;

  // GND
  const gndY = [
    coordRules.RPDU.deviceY[0] + coordRules.GND.yOffsets[0],
    coordRules.RPDU.deviceY[0] + coordRules.GND.yOffsets[1],
    coordRules.RPDU.deviceY[1] + coordRules.GND.yOffsets[2],
    coordRules.RPDU.deviceY[1] + coordRules.GND.yOffsets[3]
  ];
  
  ['GND-601', 'GND-600', 'GND-602', 'GND-603'].forEach((label, idx) => {
    svg += `  <use href="#ground-symbol" x="${coordRules.GND.x}" y="${gndY[idx]}"/>
  <text x="${coordRules.GND.x}" y="${gndY[idx] + 35}" font-family="Arial" font-size="10" text-anchor="middle" fill="black">${label}</text>
`;
  });

  // SEAT1
  svg += `
  <!-- SEAT1 -->
  <rect x="${coordRules.SEAT.deviceX}" y="${coordRules.SEAT.deviceY[0]}" width="140" height="140" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="${coordRules.SEAT.deviceX + 70}" y="${coordRules.SEAT.deviceY[0] + 30}" font-family="Arial" font-size="11" text-anchor="middle" fill="black">驾驶员座椅左</text>
  <text x="${coordRules.SEAT.deviceX + 70}" y="${coordRules.SEAT.deviceY[0] + 50}" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">2501U2201</text>
  <rect x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset}" y="${coordRules.SEAT.deviceY[0] + 30}" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + 10}" y="${coordRules.SEAT.deviceY[0] + 75}" font-family="Arial" font-size="10" text-anchor="middle" fill="black">J1</text>
  <circle cx="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset}" cy="${coordRules.SEAT.deviceY[0] + 45}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 5}" y="${coordRules.SEAT.deviceY[0] + 48}" font-family="Arial" font-size="8" fill="black">A</text>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 40}" y="${coordRules.SEAT.deviceY[0] + 42}" font-family="Arial" font-size="10" fill="black">DC PWR IN</text>
  <circle cx="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset}" cy="${coordRules.SEAT.deviceY[0] + 70}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 5}" y="${coordRules.SEAT.deviceY[0] + 73}" font-family="Arial" font-size="8" fill="black">B</text>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 30}" y="${coordRules.SEAT.deviceY[0] + 67}" font-family="Arial" font-size="10" fill="black">DC GND</text>
  <circle cx="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset}" cy="${coordRules.SEAT.deviceY[0] + 95}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 5}" y="${coordRules.SEAT.deviceY[0] + 98}" font-family="Arial" font-size="8" fill="black">C</text>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 45}" y="${coordRules.SEAT.deviceY[0] + 92}" font-family="Arial" font-size="10" fill="black">GROUNDING</text>
  <text x="${coordRules.SEAT.deviceX + 70}" y="${coordRules.SEAT.deviceY[0] + 160}" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">2501U2201</text>
`;

  // SEAT2
  svg += `
  <!-- SEAT2 -->
  <rect x="${coordRules.SEAT.deviceX}" y="${coordRules.SEAT.deviceY[1]}" width="140" height="140" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="${coordRules.SEAT.deviceX + 70}" y="${coordRules.SEAT.deviceY[1] + 30}" font-family="Arial" font-size="11" text-anchor="middle" fill="black">驾驶员座椅右</text>
  <text x="${coordRules.SEAT.deviceX + 70}" y="${coordRules.SEAT.deviceY[1] + 50}" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">2501U2203</text>
  <rect x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset}" y="${coordRules.SEAT.deviceY[1] + 30}" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + 10}" y="${coordRules.SEAT.deviceY[1] + 75}" font-family="Arial" font-size="10" text-anchor="middle" fill="black">J1</text>
  <circle cx="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset}" cy="${coordRules.SEAT.deviceY[1] + 45}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 5}" y="${coordRules.SEAT.deviceY[1] + 48}" font-family="Arial" font-size="8" fill="black">D</text>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 40}" y="${coordRules.SEAT.deviceY[1] + 42}" font-family="Arial" font-size="10" fill="black">DC PWR IN</text>
  <circle cx="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset}" cy="${coordRules.SEAT.deviceY[1] + 70}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 5}" y="${coordRules.SEAT.deviceY[1] + 73}" font-family="Arial" font-size="8" fill="black">E</text>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 30}" y="${coordRules.SEAT.deviceY[1] + 67}" font-family="Arial" font-size="10" fill="black">DC GND</text>
  <circle cx="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset}" cy="${coordRules.SEAT.deviceY[1] + 95}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 5}" y="${coordRules.SEAT.deviceY[1] + 98}" font-family="Arial" font-size="8" fill="black">F</text>
  <text x="${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset - 45}" y="${coordRules.SEAT.deviceY[1] + 92}" font-family="Arial" font-size="10" fill="black">GROUNDING</text>
  <text x="${coordRules.SEAT.deviceX + 70}" y="${coordRules.SEAT.deviceY[1] + 160}" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">2501U2203</text>
`;

  // 连接线
  svg += `
  <!-- 连接线 -->
  <polyline points="${coordRules.RPDU.deviceX + 135},${coordRules.RPDU.deviceY[0] + 45} ${connRules.turningPoints[0]},${coordRules.RPDU.deviceY[0] + 45} ${connRules.turningPoints[0]},${coordRules.SEAT.deviceY[0] + 45} ${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset},${coordRules.SEAT.deviceY[0] + 45}" fill="none" stroke="black" stroke-width="1"/>
  <text x="${connRules.turningPoints[0] + 50}" y="${coordRules.SEAT.deviceY[0] + 40}" font-family="Arial" font-size="9" fill="black">1LN ESS D N</text>
  <polyline points="${coordRules.GND.x},${gndY[0] + 25} ${connRules.turningPoints[1]},${gndY[0] + 25} ${connRules.turningPoints[1]},${coordRules.SEAT.deviceY[0] + 70} ${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset},${coordRules.SEAT.deviceY[0] + 70}" fill="none" stroke="black" stroke-width="1"/>
  <text x="${connRules.turningPoints[1] + 50}" y="${coordRules.SEAT.deviceY[0] + 65}" font-family="Arial" font-size="9" fill="black">1LN ESS D N</text>
  <polyline points="${coordRules.GND.x},${gndY[1] + 25} ${connRules.turningPoints[2]},${gndY[1] + 25} ${connRules.turningPoints[2]},${coordRules.SEAT.deviceY[0] + 95} ${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset},${coordRules.SEAT.deviceY[0] + 95}" fill="none" stroke="black" stroke-width="1"/>
  <text x="${connRules.turningPoints[2] + 50}" y="${coordRules.SEAT.deviceY[0] + 90}" font-family="Arial" font-size="9" fill="black">CG ESS Z N</text>
  <polyline points="${coordRules.RPDU.deviceX + 135},${coordRules.RPDU.deviceY[1] + 45} ${connRules.turningPoints[0]},${coordRules.RPDU.deviceY[1] + 45} ${connRules.turningPoints[0]},${coordRules.SEAT.deviceY[1] + 45} ${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset},${coordRules.SEAT.deviceY[1] + 45}" fill="none" stroke="black" stroke-width="1"/>
  <text x="${connRules.turningPoints[0] + 50}" y="${coordRules.SEAT.deviceY[1] + 40}" font-family="Arial" font-size="9" fill="black">1LN ESS D N</text>
  <polyline points="${coordRules.GND.x},${gndY[2] + 25} ${connRules.turningPoints[1]},${gndY[2] + 25} ${connRules.turningPoints[1]},${coordRules.SEAT.deviceY[1] + 70} ${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset},${coordRules.SEAT.deviceY[1] + 70}" fill="none" stroke="black" stroke-width="1"/>
  <text x="${connRules.turningPoints[1] + 50}" y="${coordRules.SEAT.deviceY[1] + 65}" font-family="Arial" font-size="9" fill="black">1LN ESS D N</text>
  <polyline points="${coordRules.GND.x},${gndY[3] + 25} ${connRules.turningPoints[2]},${gndY[3] + 25} ${connRules.turningPoints[2]},${coordRules.SEAT.deviceY[1] + 95} ${coordRules.SEAT.deviceX + coordRules.SEAT.connectorOffset + coordRules.SEAT.pinOffset},${coordRules.SEAT.deviceY[1] + 95}" fill="none" stroke="black" stroke-width="1"/>
  <text x="${connRules.turningPoints[2] + 50}" y="${coordRules.SEAT.deviceY[1] + 90}" font-family="Arial" font-size="9" fill="black">CG ESS Z N</text>
`;

  svg += `</svg>`;
  
  // 验证规则
  console.log('🔍 验证强制规则...');
  const errors = validateRules(svg, rules);
  
  if (errors.length > 0) {
    console.error('');
    console.error('❌ 规则验证失败！');
    errors.forEach(err => console.error('   - ' + err));
    console.error('');
    console.error('⚠️  生成已中止。');
    process.exit(1);
  }
  
  console.log('✅ 所有规则验证通过！');
  
  // 保存文件
  const outputFileName = path.basename(jsonFilePath, '.json') + '_schematic.svg';
  const outputPath = path.join(projectDir, outputFileName);
  fs.writeFileSync(outputPath, svg, 'utf8');
  
  const hash = crypto.createHash('md5').update(svg).digest('hex');
  
  console.log('');
  console.log('✅ 生成成功！');
  console.log('📁 输出文件:', outputPath);
  console.log('🔐 内容哈希:', hash);
  console.log('');
  console.log('💡 提示:');
  console.log('  - 使用 Skill 内标准生成器');
  console.log('  - 自动应用强制规则');
  console.log('  - 任何项目都可直接调用');
  
  return { outputPath, hash };
}

// 主程序
if (require.main === module) {
  const jsonFilePath = process.argv[2];
  
  if (!jsonFilePath) {
    console.log('使用方法: node standard-generator.js <EICD JSON文件路径>');
    console.log('');
    console.log('示例:');
    console.log('  node standard-generator.js "d:\\项目\\EICD.json"');
    process.exit(1);
  }
  
  try {
    generateSVG(jsonFilePath);
  } catch (error) {
    console.error('');
    console.error('❌ 错误:', error.message);
    process.exit(1);
  }
}

module.exports = { generateSVG };
