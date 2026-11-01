/**
 * 交互式模板编辑器
 * 支持用户拖拽编辑、保存到模板库、导出Capital XML
 */

const fs = require('fs');
const path = require('path');
const CapitalExporter = require('../../eicd-svg-to-capital/src/capital-exporter.js');

class InteractiveTemplateEditor {
    constructor() {
        this.currentTemplate = null;
        this.selectedDevice = null;
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.moveStep = 10; // 移动步长
    }

    /**
     * 加载SVG文件并创建可编辑模板
     */
    loadSvgAsTemplate(svgPath, jsonPath) {
        console.log(`正在加载SVG文件: ${svgPath}`);
        console.log(`JSON数据文件: ${jsonPath}`);
        
        const svgContent = fs.readFileSync(svgPath, 'utf8');
        const jsonData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
        
        // 创建模板
        this.currentTemplate = this.createTemplateFromSvg(svgContent, jsonData, svgPath);
        
        console.log(`✅ 模板创建成功！`);
        console.log(`   设备数量: ${Object.keys(this.currentTemplate.positions).length}`);
        console.log(`   连接数量: ${this.currentTemplate.connections.length}`);
        
        return this.currentTemplate;
    }

    /**
     * 显示交互式编辑界面
     */
    showInteractiveEditor() {
        console.log('\n=== 交互式模板编辑器 ===');
        console.log('可用命令:');
        console.log('  move <deviceId> <direction> <steps> - 移动设备');
        console.log('  select <deviceId> - 选择设备');
        console.log('  list - 列出所有设备');
        console.log('  save <name> <description> - 保存模板');
        console.log('  export <projectName> - 导出Capital XML');
        console.log('  help - 显示帮助');
        console.log('  exit - 退出编辑器');
        console.log('');
        
        this.showCurrentState();
    }

    /**
     * 处理用户命令
     */
    handleCommand(command) {
        const parts = command.trim().split(/\s+/);
        const cmd = parts[0].toLowerCase();
        
        switch (cmd) {
            case 'move':
                return this.handleMoveCommand(parts.slice(1));
            case 'select':
                return this.handleSelectCommand(parts.slice(1));
            case 'list':
                return this.handleListCommand();
            case 'save':
                return this.handleSaveCommand(parts.slice(1));
            case 'export':
                return this.handleExportCommand(parts.slice(1));
            case 'help':
                return this.showInteractiveEditor();
            case 'exit':
                return { action: 'exit' };
            default:
                console.log(`❌ 未知命令: ${cmd}`);
                return { action: 'continue' };
        }
    }

    /**
     * 处理移动命令
     */
    handleMoveCommand(args) {
        if (args.length < 2) {
            console.log('❌ 用法: move <deviceId> <direction> [steps]');
            return { action: 'continue' };
        }
        
        const deviceId = args[0];
        const direction = args[1];
        const steps = parseInt(args[2]) || this.moveStep;
        
        if (!this.currentTemplate.positions[deviceId]) {
            console.log(`❌ 设备不存在: ${deviceId}`);
            return { action: 'continue' };
        }
        
        const pos = this.currentTemplate.positions[deviceId];
        const oldPos = { ...pos };
        
        switch (direction.toLowerCase()) {
            case 'left':
                pos.x -= steps;
                break;
            case 'right':
                pos.x += steps;
                break;
            case 'up':
                pos.y -= steps;
                break;
            case 'down':
                pos.y += steps;
                break;
            default:
                console.log(`❌ 无效方向: ${direction}`);
                return { action: 'continue' };
        }
        
        console.log(`✅ 设备 ${deviceId} 已移动: (${oldPos.x}, ${oldPos.y}) → (${pos.x}, ${pos.y})`);
        
        // 更新连接线的路径点
        this.updateConnectionWaypoints(deviceId, oldPos, pos);
        
        return { action: 'continue' };
    }

    /**
     * 处理选择命令
     */
    handleSelectCommand(args) {
        if (args.length === 0) {
            console.log('❌ 用法: select <deviceId>');
            return { action: 'continue' };
        }
        
        const deviceId = args[0];
        if (!this.currentTemplate.positions[deviceId]) {
            console.log(`❌ 设备不存在: ${deviceId}`);
            return { action: 'continue' };
        }
        
        this.selectedDevice = deviceId;
        const pos = this.currentTemplate.positions[deviceId];
        console.log(`✅ 已选择设备: ${deviceId} (位置: ${pos.x}, ${pos.y})`);
        
        return { action: 'continue' };
    }

    /**
     * 处理列表命令
     */
    handleListCommand() {
        console.log('\n=== 设备列表 ===');
        for (const [deviceId, pos] of Object.entries(this.currentTemplate.positions)) {
            const selected = deviceId === this.selectedDevice ? ' [选中]' : '';
            console.log(`  ${deviceId}: (${pos.x}, ${pos.y})${selected}`);
        }
        console.log('');
        return { action: 'continue' };
    }

    /**
     * 处理保存命令
     */
    handleSaveCommand(args) {
        if (args.length < 2) {
            console.log('❌ 用法: save <name> <description>');
            return { action: 'continue' };
        }
        
        const name = args[0];
        const description = args.slice(1).join(' ');
        
        // 更新模板信息
        this.currentTemplate.templateName = name;
        this.currentTemplate.description = description;
        this.currentTemplate.templateId = `user_template_${Date.now()}`;
        this.currentTemplate.createdAt = new Date().toISOString();
        this.currentTemplate.metadata = {
            author: 'user',
            isDefault: false,
            lastEdited: new Date().toISOString()
        };
        
        // 保存到模板库
        const TemplateManager = require('./template-manager.js');
        const manager = new TemplateManager();
        const success = manager.saveTemplate(this.currentTemplate);
        
        if (success) {
            console.log(`✅ 模板已保存到模板库: ${this.currentTemplate.templateId}.json`);
            console.log(`   名称: ${name}`);
            console.log(`   描述: ${description}`);
            return { 
                action: 'template_saved',
                templateId: this.currentTemplate.templateId,
                templateName: name
            };
        } else {
            console.log('❌ 保存模板失败');
            return { action: 'continue' };
        }
    }

    /**
     * 处理导出命令
     */
    handleExportCommand(args) {
        if (args.length === 0) {
            console.log('❌ 用法: export <projectName>');
            return { action: 'continue' };
        }
        
        const projectName = args.join(' ');
        
        try {
            // 创建导出器
            const exporter = new CapitalExporter({
                projectName: projectName,
                version: '1.0',
                author: '用户编辑'
            });
            
            // 导出为Capital XML
            const xml = exporter.exportFromTemplate(this.currentTemplate);
            
            // 保存XML文件
            const xmlPath = path.join(
                process.cwd(),
                `${this.currentTemplate.templateId || 'template'}_capital.xml`
            );
            
            fs.writeFileSync(xmlPath, xml, 'utf8');
            
            console.log(`✅ Capital XML 导出成功！`);
            console.log(`   项目: ${projectName}`);
            console.log(`   文件: ${path.basename(xmlPath)}`);
            console.log(`   长度: ${xml.length} 字符`);
            
            return { 
                action: 'xml_exported',
                xmlPath: xmlPath,
                projectName: projectName
            };
        } catch (error) {
            console.log(`❌ 导出失败: ${error.message}`);
            return { action: 'continue' };
        }
    }

    /**
     * 显示当前状态
     */
    showCurrentState() {
        console.log('=== 当前状态 ===');
        console.log(`模板: ${this.currentTemplate.templateName}`);
        console.log(`选中设备: ${this.selectedDevice || '无'}`);
        console.log(`设备总数: ${Object.keys(this.currentTemplate.positions).length}`);
        console.log(`连接总数: ${this.currentTemplate.connections.length}`);
        console.log('');
    }

    /**
     * 从SVG内容创建模板
     */
    createTemplateFromSvg(svgContent, jsonData, sourceFile) {
        const positions = this.extractDevicePositions(svgContent);
        const connections = this.extractConnections(svgContent);
        
        return {
            templateName: `从SVG转换的模板 - ${path.basename(sourceFile, '.svg')}`,
            templateId: `svg_converted_${Date.now()}`,
            description: `从 ${path.basename(sourceFile)} 转换的电气原理图模板`,
            version: "1.0",
            createdAt: new Date().toISOString(),
            canvas: {
                width: 900,
                height: 650,
                backgroundColor: "#ffffff",
                gridSize: 20,
                showGrid: true
            },
            layout: {
                type: "fixed",
                direction: "horizontal",
                deviceSpacing: 100,
                layerSpacing: 200
            },
            styles: {
                device: {
                    fill: "white",
                    stroke: "black",
                    strokeWidth: 1.5,
                    fontFamily: "Arial",
                    fontSize: 11,
                    textColor: "black"
                },
                connector: {
                    fill: "white",
                    stroke: "black",
                    strokeWidth: 1,
                    fontSize: 9,
                    width: 20,
                    height: 40
                },
                pin: {
                    radius: 3,
                    fill: "white",
                    stroke: "black",
                    strokeWidth: 1,
                    fontSize: 8
                },
                ground: {
                    symbolType: "standard",
                    strokeWidth: 1,
                    fontSize: 10
                },
                connection: {
                    stroke: "black",
                    strokeWidth: 1,
                    style: "orthogonal",
                    cornerRadius: 0
                },
                signalLabel: {
                    fontFamily: "Arial",
                    fontSize: 9,
                    fill: "black"
                }
            },
            deviceTypes: {
                RPDU: {
                    width: 140,
                    height: 120,
                    connectorPosition: "right",
                    connectorIds: ["J3", "J4"],
                    pinIds: ["10", "20"]
                },
                SEAT: {
                    width: 140,
                    height: 140,
                    connectorPosition: "left",
                    connectorIds: ["J1"],
                    pinIds: ["A", "B", "C", "D", "E", "F"]
                },
                GND: {
                    symbolType: "ground",
                    labels: ["GND-601", "GND-600", "GND-602", "GND-603"]
                }
            },
            positions: positions,
            connections: connections,
            metadata: {
                author: "svg_converter",
                isDefault: false,
                sourceFile: path.basename(sourceFile),
                conversionDate: new Date().toISOString()
            }
        };
    }

    /**
     * 从SVG内容中提取设备位置
     */
    extractDevicePositions(svgContent) {
        const positions = {};
        
        // 匹配设备组
        const deviceRegex = /<g\s+id="device-([^"]+)"[^>]*>[\s\S]*?<rect[^>]*x="(\d+)"[^>]*y="(\d+)"[^>]*width="(\d+)"[^>]*height="(\d+)"[^>]*>/g;
        let match;
        
        while ((match = deviceRegex.exec(svgContent)) !== null) {
            const deviceId = match[1];
            const x = parseInt(match[2]);
            const y = parseInt(match[3]);
            
            positions[deviceId] = { x, y };
        }

        // 匹配接地符号
        const groundRegex = /<g\s+id="gnd-(\d+)"[^>]*>[\s\S]*?<use[^>]*x="(\d+)"[^>]*y="(\d+)"[^>]*>/g;
        while ((match = groundRegex.exec(svgContent)) !== null) {
            const groundId = `GND-${match[1]}`;
            const x = parseInt(match[2]);
            const y = parseInt(match[3]);
            
            positions[groundId] = { x, y };
        }

        return positions;
    }

    /**
     * 从SVG内容中提取连接信息
     */
    extractConnections(svgContent) {
        const connections = [];
        
        // 从SVG中提取polyline连接
        const polylineRegex = /<polyline[^>]*points="([^"]+)"[^>]*>/g;
        let match;
        let connectionIndex = 1;

        while ((match = polylineRegex.exec(svgContent)) !== null) {
            const pointsStr = match[1];
            const waypoints = this.parsePolylinePoints(pointsStr);
            
            // 查找对应的标签
            const labelRegex = new RegExp(`<text[^>]*x="${waypoints[Math.floor(waypoints.length/2)][0]}"[^>]*y="${waypoints[Math.floor(waypoints.length/2)][1]-5}"[^>]*>([^<]+)</text>`);
            const labelMatch = svgContent.match(labelRegex);
            const label = labelMatch ? labelMatch[1] : '';

            connections.push({
                id: `conn_${connectionIndex++}`,
                waypoints: waypoints,
                label: label
            });
        }

        return connections;
    }

    /**
     * 解析polyline的points属性
     */
    parsePolylinePoints(pointsStr) {
        const points = [];
        const coords = pointsStr.trim().split(/\s+/);
        
        for (let i = 0; i < coords.length; i += 2) {
            const x = parseInt(coords[i]);
            const y = parseInt(coords[i + 1]);
            if (!isNaN(x) && !isNaN(y)) {
                points.push([x, y]);
            }
        }
        
        return points;
    }

    /**
     * 更新连接线路径点
     */
    updateConnectionWaypoints(deviceId, oldPos, newPos) {
        const dx = newPos.x - oldPos.x;
        const dy = newPos.y - oldPos.y;
        
        // 更新所有包含该设备的连接线
        for (const conn of this.currentTemplate.connections) {
            conn.waypoints = conn.waypoints.map(point => {
                // 简化处理：如果路径点接近设备原位置，则移动它
                const distance = Math.sqrt(
                    Math.pow(point[0] - oldPos.x, 2) + 
                    Math.pow(point[1] - oldPos.y, 2)
                );
                
                if (distance < 50) { // 50像素范围内
                    return [point[0] + dx, point[1] + dy];
                }
                return point;
            });
        }
    }
}

module.exports = InteractiveTemplateEditor;
