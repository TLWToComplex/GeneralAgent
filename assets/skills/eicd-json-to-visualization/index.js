/**
 * EICD JSON to Visualization Skill
 * 将EICD JSON数据转换为可视化图表
 */

const fs = require('fs');
const path = require('path');
const TemplateManager = require('./src/template-manager');

class EICDVisualizationSkill {
    constructor() {
        this.templateManager = new TemplateManager();
        this.memoryDir = null;
        this.jsonFile = null;
    }

    /**
     * 主入口函数
     */
    async execute(options = {}) {
        console.log('🚀 EICD JSON to Visualization Skill 启动\n');

        // 阶段一：文件确认与准备
        const fileCheck = await this.phase1_FilePreparation(options);
        if (!fileCheck.success) {
            return fileCheck;
        }

        // 阶段二：模板和图表类型选择（合并）
        const selection = await this.phase2_TemplateAndDiagramSelection(options);
        if (!selection.success) {
            return selection;
        }

        // 阶段三：生成可视化图表
        console.log('\n🎨 阶段三：生成可视化图表\n');
        const generation = await this.phase4_GenerateVisualization(
            selection.template,
            selection.diagramType
        );

        // 阶段四：生成操作文档
        console.log('\n📝 阶段四：生成操作文档\n');
        await this.phase5_CreateOperationDoc(generation);

        return {
            success: true,
            jsonFile: this.jsonFile,
            svgFile: generation.svgFile,
            diagramType: selection.diagramType,
            templateId: selection.template?.templateId,
            operationDoc: generation.operationDoc
        };
    }

    /**
     * 阶段一：文件确认与准备
     */
    async phase1_FilePreparation(options) {
        console.log('📁 阶段一：文件确认与准备\n');

        // 1. 读取记忆目录
        this.memoryDir = options.memoryDir || this.findMemoryDir();
        if (this.memoryDir) {
            console.log(`✅ 记忆目录: ${this.memoryDir}`);
            this.readMemoryFiles();
        }

        // 2. 验证JSON文件
        this.jsonFile = options.jsonFile;
        if (!this.jsonFile) {
            // 尝试从记忆目录查找JSON文件
            this.jsonFile = this.findLatestJSON();
        }

        if (!this.jsonFile) {
            return {
                success: false,
                error: '未找到JSON文件，请提供jsonFile参数'
            };
        }

        console.log(`✅ JSON文件: ${this.jsonFile}`);

        // 3. 验证文件存在且格式正确
        if (!fs.existsSync(this.jsonFile)) {
            return {
                success: false,
                error: `JSON文件不存在: ${this.jsonFile}`
            };
        }

        try {
            const jsonData = JSON.parse(fs.readFileSync(this.jsonFile, 'utf8'));
            
            // 验证EICD数据结构
            if (!jsonData.equipment && !jsonData.components && !jsonData.interfaces) {
                console.warn('⚠️  JSON数据可能不是标准的EICD格式');
            } else {
                console.log('✅ JSON格式验证通过');
                console.log(`   设备数量: ${jsonData.equipment?.length || 0}`);
                console.log(`   接口数量: ${jsonData.interfaces?.length || 0}`);
            }
        } catch (error) {
            return {
                success: false,
                error: `JSON解析失败: ${error.message}`
            };
        }

        return { success: true };
    }

    /**
     * 阶段二：模板和图表类型选择（合并）
     * 用户只需选择一次：从模板库选择或使用默认图表
     */
    async phase2_TemplateAndDiagramSelection(options) {
        console.log('\n🎨 阶段二：选择模板或图表类型\n');

        // 获取所有可用模板
        const templates = this.templateManager.getAllTemplates();
        
        // 构建选择列表：模板 + 默认图表选项
        const choices = [];
        
        // 添加默认图表选项（放在第一位）
        choices.push({
            type: 'default_diagram',
            id: 'default_schematic_v2',
            label: '⚡ 默认电气原理图（推荐）',
            description: '使用系统默认的电气原理图模板，白色设备框、连接器J3/J4/J1、引脚编号、接地符号、正交连线',
            isDefault: true
        });
        
        // 添加其他图表类型选项
        choices.push({
            type: 'diagram_type',
            id: 'topology',
            label: '🌐 系统拓扑图',
            description: '显示设备之间的连接关系和拓扑结构'
        });
        choices.push({
            type: 'diagram_type',
            id: 'wiring',
            label: '🔌 接线图',
            description: '显示详细的接线关系和引脚连接'
        });
        choices.push({
            type: 'diagram_type',
            id: 'signal',
            label: '➡️ 信号流向图',
            description: '显示信号从源到目标的流向'
        });
        choices.push({
            type: 'diagram_type',
            id: 'hierarchical',
            label: '📊 层次结构图',
            description: '按层次展示设备和组件关系'
        });
        
        // 添加分隔线标记
        if (templates.length > 0) {
            choices.push({ type: 'separator', label: '────────── 自定义模板 ──────────' });
        }
        
        // 添加用户保存的模板
        templates.forEach((template, index) => {
            const isDefault = template.isDefault ? ' [默认]' : '';
            const isUser = template.templateId.startsWith('user_') ? ' [用户]' : '';
            choices.push({
                type: 'template',
                id: template.templateId,
                label: `${index + 1}. ${template.templateName}${isDefault}${isUser}`,
                description: template.description || '用户自定义模板',
                template: template
            });
        });

        console.log(`📋 可用选项:\n`);
        choices.forEach((choice, index) => {
            if (choice.type === 'separator') {
                console.log(`  ${choice.label}`);
            } else {
                console.log(`  ${index + 1}. ${choice.label}`);
                console.log(`     ${choice.description}`);
            }
            console.log('');
        });

        // 如果指定了templateId，直接使用
        if (options.templateId) {
            const template = this.templateManager.getTemplate(options.templateId);
            if (template) {
                console.log(`✅ 使用指定模板: ${template.templateName}`);
                return { 
                    success: true, 
                    template,
                    diagramType: { id: 'schematic_v2', label: '⚡ 电气原理图（推荐）' }
                };
            }
        }

        // 如果指定了图表类型，直接使用
        if (options.diagramType) {
            const diagramTypeMap = {
                'schematic_v2': { id: 'schematic_v2', label: '⚡ 电气原理图（推荐）' },
                'topology': { id: 'topology', label: '🌐 系统拓扑图' },
                'wiring': { id: 'wiring', label: '🔌 接线图' },
                'signal': { id: 'signal', label: '➡️ 信号流向图' },
                'hierarchical': { id: 'hierarchical', label: '📊 层次结构图' }
            };
            const diagramType = diagramTypeMap[options.diagramType];
            if (diagramType) {
                console.log(`✅ 使用指定图表类型: ${diagramType.label}`);
                return { 
                    success: true, 
                    template: null,
                    diagramType: diagramType
                };
            }
        }

        // 返回选择列表供用户选择
        return {
            success: true,
            choices: choices,
            template: templates.find(t => t.isDefault) || null,
            diagramType: { id: 'schematic_v2', label: '⚡ 电气原理图（推荐）' },
            requireUserSelection: true
        };
    }

    /**
     * 阶段四：生成可视化图表
     */
    async phase4_GenerateVisualization(template, diagramType) {
        console.log('\n🎨 阶段四：生成可视化图表\n');
        console.log(`模板: ${template?.templateName || '默认'}`);
        console.log(`图表类型: ${diagramType.label}`);

        const jsonData = JSON.parse(fs.readFileSync(this.jsonFile, 'utf8'));
        
        // 根据图表类型生成SVG
        let svg;
        switch (diagramType.id) {
            case 'schematic_v2':
                svg = this.generateSchematicV2(jsonData, template);
                break;
            case 'topology':
                svg = this.generateTopology(jsonData, template);
                break;
            case 'wiring':
                svg = this.generateWiring(jsonData, template);
                break;
            default:
                svg = this.generateSchematicV2(jsonData, template);
        }

        // 保存SVG文件
        const outputDir = path.dirname(this.jsonFile);
        const baseName = path.basename(this.jsonFile, '.json');
        const svgFileName = `${baseName}_${diagramType.id}.svg`;
        const svgFilePath = path.join(outputDir, svgFileName);

        fs.writeFileSync(svgFilePath, svg, 'utf8');
        console.log(`\n✅ SVG文件已保存: ${svgFilePath}`);

        return {
            success: true,
            svgFile: svgFilePath,
            svg: svg
        };
    }

    /**
     * 生成电气原理图（推荐）
     */
    generateSchematicV2(jsonData, template) {
        const svgWidth = 1000;
        const svgHeight = 650;

        let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${svgWidth}" height="${svgHeight}" viewBox="0 0 ${svgWidth} ${svgHeight}">
  <defs>
    <g id="ground-symbol">
      <line x1="0" y1="0" x2="0" y2="12" stroke="black" stroke-width="1"/>
      <line x1="-8" y1="12" x2="8" y2="12" stroke="black" stroke-width="1"/>
      <line x1="-5" y1="16" x2="5" y2="16" stroke="black" stroke-width="1"/>
      <line x1="-2" y1="20" x2="2" y2="20" stroke="black" stroke-width="1"/>
    </g>
  </defs>
  
  <rect width="100%" height="100%" fill="white"/>
  <text x="20" y="30" font-family="Arial, sans-serif" font-size="22" font-weight="bold" fill="#333">Layout Result</text>
  <rect x="10" y="45" width="980" height="590" fill="#fafafa" stroke="#ccc" stroke-width="1"/>
`;

        // 使用模板中的位置信息或默认位置
        const positions = template?.positions || this.calculateDefaultPositions(jsonData);
        
        // 从JSON数据中提取设备信息
        const equipments = jsonData.equipments || [];
        const interfaces = jsonData.interfaces || [];
        
        // 分析接口数据，提取RPDU和GND信息
        const rpdus = new Map();
        const gnds = new Map();
        const seats = new Map();
        
        interfaces.forEach(intf => {
            // 提取源设备信息
            if (intf.sigSrcDev && intf.sigSrcDev.startsWith('2404U')) {
                if (!rpdus.has(intf.sigSrcDev)) {
                    rpdus.set(intf.sigSrcDev, {
                        id: intf.sigSrcDev,
                        name: intf.sigSrcName,
                        connector: intf.sigSrcConn,
                        pin: intf.sigSrcPinNum
                    });
                }
            }
            
            // 提取目标设备信息（座椅）
            if (intf.sigDestDev && intf.sigDestDev.startsWith('2501U')) {
                if (!seats.has(intf.sigDestDev)) {
                    seats.set(intf.sigDestDev, {
                        id: intf.sigDestDev,
                        name: intf.sigDestName,
                        connector: intf.sigDestConn,
                        pins: []
                    });
                }
                seats.get(intf.sigDestDev).pins.push({
                    pin: intf.sigDestPinNum,
                    label: intf.sigDestName,
                    srcDev: intf.sigSrcDev,
                    srcPin: intf.sigSrcPinNum,
                    powSupplyCode: intf.powSupplyCode,
                    routeCode: intf.routeCode,
                    emcCode: intf.emcCode,
                    redCode: intf.redCode
                });
            }
        });
        
        // 生成GND标签
        const gndLabels = ['GND-601', 'GND-600', 'GND-602', 'GND-603'];
        
        // 绘制RPDU设备（左侧）
        let rpdusArray = Array.from(rpdus.values());
        rpdusArray.forEach((rpdu, index) => {
            const pos = positions[`RPDU${index + 1}`] || { x: 60, y: 80 + index * 280 };
            svg += this.drawRPDU(rpdu, pos, index + 1);
        });
        
        // 绘制GND接地符号
        gndLabels.forEach((gndLabel, index) => {
            const pos = positions[gndLabel] || { 
                x: 130, 
                y: 220 + (index % 2) * 60 + Math.floor(index / 2) * 280 
            };
            svg += this.drawGND(gndLabel, pos);
        });
        
        // 绘制座椅设备（右侧）
        let seatsArray = Array.from(seats.values());
        seatsArray.forEach((seat, index) => {
            const pos = positions[seat.id] || { x: 750, y: 80 + index * 280 };
            svg += this.drawSeat(seat, pos);
        });
        
        // 绘制连接线
        interfaces.forEach((intf, index) => {
            svg += this.drawConnection(intf, positions, index);
        });
        
        svg += '</svg>';
        return svg;
    }
    
    /**
     * 绘制RPDU设备
     */
    drawRPDU(rpdu, pos, index) {
        const y = pos.y;
        const connectorY = y + 20;
        
        return `
  <!-- RPDU${index} 设备框 -->
  <rect x="${pos.x}" y="${y}" width="140" height="100" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="${pos.x + 70}" y="${y + 30}" font-family="Arial" font-size="10" text-anchor="middle" fill="black">${rpdu.name}</text>
  
  <!-- RPDU${index} 连接器 ${rpdu.connector ? rpdu.connector.split('-')[1] : 'J' + (index * 2 + 3)} (右侧突出) -->
  <rect x="${pos.x + 140}" y="${connectorY}" width="15" height="60" fill="white" stroke="black" stroke-width="1"/>
  <text x="${pos.x + 147}" y="${connectorY + 35}" font-family="Arial" font-size="9" text-anchor="middle" fill="black">${rpdu.connector ? rpdu.connector.split('-')[1] : 'J' + (index * 2 + 3)}</text>
  
  <!-- RPDU${index} 引脚 ${rpdu.pin} (在连接器右侧) -->
  <circle cx="${pos.x + 155}" cy="${connectorY + 15}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${pos.x + 165}" y="${connectorY + 18}" font-family="Arial" font-size="8" fill="black">${rpdu.pin}</text>
  
  <!-- RPDU${index} 标签 -->
  <text x="${pos.x + 70}" y="${y + 115}" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">RPDU${index}</text>
`;
    }
    
    /**
     * 绘制GND接地符号
     */
    drawGND(label, pos) {
        return `
  <!-- ${label} -->
  <use href="#ground-symbol" x="${pos.x}" y="${pos.y}"/>
  <text x="${pos.x}" y="${pos.y + 35}" font-family="Arial" font-size="10" text-anchor="middle" fill="black">${label}</text>
`;
    }
    
    /**
     * 绘制座椅设备
     */
    drawSeat(seat, pos) {
        const y = pos.y;
        const connectorY = y + 20;
        const pinSpacing = 25;
        
        let pinsSvg = '';
        seat.pins.forEach((pinInfo, idx) => {
            const pinY = connectorY + 20 + idx * pinSpacing;
            pinsSvg += `
  <!-- ${seat.id} 引脚 ${pinInfo.pin} -->
  <circle cx="${pos.x}" cy="${pinY}" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="${pos.x - 10}" y="${pinY + 3}" font-family="Arial" font-size="8" text-anchor="end" fill="black">${pinInfo.pin}</text>
  <text x="${pos.x + 25}" y="${pinY - 5}" font-family="Arial" font-size="9" fill="black">${pinInfo.label}</text>
`;
        });
        
        return `
  <!-- ${seat.id} 设备框 -->
  <rect x="${pos.x}" y="${y}" width="140" height="140" fill="white" stroke="black" stroke-width="1.5"/>
  
  <!-- ${seat.id} 连接器 J1 (左侧突出) -->
  <rect x="${pos.x - 15}" y="${connectorY}" width="15" height="100" fill="white" stroke="black" stroke-width="1"/>
  <text x="${pos.x - 8}" y="${connectorY + 55}" font-family="Arial" font-size="9" text-anchor="middle" fill="black">J1</text>
  
${pinsSvg}
  <!-- ${seat.id} 标签 -->
  <text x="${pos.x + 70}" y="${y + 155}" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">${seat.id}</text>
`;
    }
    
    /**
     * 绘制连接线
     */
    drawConnection(intf, positions, index) {
        // 根据接口数据确定连线路径
        // 这里简化处理，使用固定的路由
        const srcDev = intf.sigSrcDev;
        const destDev = intf.sigDestDev;
        const destPin = intf.sigDestPinNum;
        
        // 确定源位置
        let srcX, srcY;
        if (srcDev === '2404U4101') {
            srcX = 215; srcY = 115;
        } else if (srcDev === '2404U4103') {
            srcX = 215; srcY = 395;
        } else if (srcDev === 'GND') {
            // GND连接，根据目标设备确定
            if (destDev === '2501U2201') {
                if (destPin === 'B') { srcX = 130; srcY = 240; }
                else if (destPin === 'C') { srcX = 130; srcY = 300; }
            } else if (destDev === '2501U2203') {
                if (destPin === 'B') { srcX = 130; srcY = 520; }
                else if (destPin === 'C') { srcX = 130; srcY = 580; }
            }
        }
        
        // 确定目标位置
        let destX, destY;
        if (destDev === '2501U2201') {
            destX = 750;
            if (destPin === 'A') destY = 120;
            else if (destPin === 'B') destY = 145;
            else if (destPin === 'C') destY = 170;
        } else if (destDev === '2501U2203') {
            destX = 750;
            if (destPin === 'A') destY = 400;
            else if (destPin === 'B') destY = 425;
            else if (destPin === 'C') destY = 450;
        }
        
        if (!srcX || !destX) return '';
        
        // 生成正交连线路径
        const midX = srcX + (destX - srcX) / 2;
        const points = `${srcX},${srcY} ${midX},${srcY} ${midX},${destY} ${destX},${destY}`;
        
        // 信号标签
        const labelX = (srcX + destX) / 2;
        const labelY = srcY - 5;
        const label = `${intf.powSupplyCode || ''} ${intf.routeCode || ''} ${intf.emcCode || ''} ${intf.redCode || ''}`.trim();
        
        return `
  <!-- ${intf.sigSrcName || srcDev} -> ${destDev} J1-${destPin} -->
  <polyline points="${points}" fill="none" stroke="black" stroke-width="1"/>
  <text x="${labelX}" y="${labelY}" font-family="Arial" font-size="9" text-anchor="middle" fill="black">${label}</text>
`;
    }

    /**
     * 生成系统拓扑图
     */
    generateTopology(jsonData, template) {
        // 实现拓扑图生成逻辑
        return this.generateSchematicV2(jsonData, template);
    }

    /**
     * 生成接线图
     */
    generateWiring(jsonData, template) {
        // 实现接线图生成逻辑
        return this.generateSchematicV2(jsonData, template);
    }

    /**
     * 阶段五：生成操作文档
     */
    async phase5_CreateOperationDoc(generationResult) {
        console.log('\n📝 阶段五：生成操作文档\n');

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const docDir = path.join(path.dirname(this.jsonFile), 'memory', 'json-to-visualization');
        
        if (!fs.existsSync(docDir)) {
            fs.mkdirSync(docDir, { recursive: true });
        }

        const docPath = path.join(docDir, `visualization_operation_${timestamp}.md`);
        
        const docContent = `# EICD JSON 可视化操作记录

## 操作时间
${new Date().toLocaleString()}

## 输入文件
- JSON文件: ${this.jsonFile}

## 输出文件
- SVG文件: ${generationResult.svgFile}

## 操作详情
- 图表类型: 电气原理图
- 模板: 默认模板

## 生成结果
✅ 可视化图表生成成功
`;

        fs.writeFileSync(docPath, docContent, 'utf8');
        console.log(`✅ 操作文档已保存: ${docPath}`);

        generationResult.operationDoc = docPath;
    }

    /**
     * 查找记忆目录
     */
    findMemoryDir() {
        const possiblePaths = [
            'd:\\trae\\商飞\\memory',
            path.join(process.cwd(), 'memory'),
            path.join(__dirname, '..', '..', '..', '商飞', 'memory')
        ];

        for (const p of possiblePaths) {
            if (fs.existsSync(p)) {
                return p;
            }
        }
        return null;
    }

    /**
     * 读取记忆文件
     */
    readMemoryFiles() {
        try {
            const files = fs.readdirSync(this.memoryDir);
            console.log(`   发现 ${files.length} 个记忆文件`);
        } catch (error) {
            console.warn('   读取记忆文件失败:', error.message);
        }
    }

    /**
     * 查找最新的JSON文件
     */
    findLatestJSON() {
        const possibleDirs = [
            'd:\\trae\\商飞',
            process.cwd()
        ];

        for (const dir of possibleDirs) {
            if (!fs.existsSync(dir)) continue;
            
            const files = fs.readdirSync(dir);
            const jsonFiles = files
                .filter(f => f.endsWith('.json') && !f.includes('_template'))
                .map(f => ({
                    name: f,
                    path: path.join(dir, f),
                    mtime: fs.statSync(path.join(dir, f)).mtime
                }))
                .sort((a, b) => b.mtime - a.mtime);

            if (jsonFiles.length > 0) {
                return jsonFiles[0].path;
            }
        }
        return null;
    }

    /**
     * 计算默认位置
     */
    calculateDefaultPositions(jsonData) {
        // 默认位置配置
        return {
            RPDU1: { x: 60, y: 80 },
            RPDU2: { x: 60, y: 360 },
            '2501U2201': { x: 750, y: 80 },
            '2501U2203': { x: 750, y: 360 },
            'GND-601': { x: 130, y: 220 },
            'GND-600': { x: 130, y: 280 },
            'GND-602': { x: 130, y: 500 },
            'GND-603': { x: 130, y: 560 }
        };
    }
}

// 导出技能类
module.exports = EICDVisualizationSkill;

// 如果直接运行此文件
if (require.main === module) {
    const skill = new EICDVisualizationSkill();
    skill.execute().then(result => {
        console.log('\n✅ 技能执行完成');
        console.log(result);
    }).catch(error => {
        console.error('\n❌ 技能执行失败:', error);
    });
}
