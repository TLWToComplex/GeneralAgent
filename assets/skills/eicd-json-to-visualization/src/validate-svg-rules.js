#!/usr/bin/env node

/**
 * EICD SVG 规则验证器
 *
 * 作用: 在生成SVG前检查是否符合.eicd-rules.json中的强制规则
 *
 * 使用方法:
 *   node validate-svg-rules.js <SVG文件路径>
 *
 * 示例:
 *   node validate-svg-rules.js "d:\项目\输出\schematic.svg"
 *
 * 退出码:
 *   0 = 验证通过
 *   1 = 验证失败（违反规则）
 */

const fs = require('fs');
const path = require('path');

const RULES_FILE = 'd:\\trae\\商飞\\.eicd-rules.json';

function loadRules() {
    if (!fs.existsSync(RULES_FILE)) {
        console.error(`❌ 规则文件不存在: ${RULES_FILE}`);
        return null;
    }
    return JSON.parse(fs.readFileSync(RULES_FILE, 'utf8'));
}

function validateSVG(svgContent, rules) {
    const errors = [];
    const warnings = [];

    // ========== 规则1: 引脚必须在连接器外部 ==========
    if (rules.mandatoryRules.pinPosition?.enforcement === 'strict') {
        console.log('🔍 检查规则1: 引脚必须在连接器外部...');

        const pinRegex = /<circle[^>]*cx="(\d+)"[^>]*cy="(\d+)"[^>]*>/g;
        const rectRegex = /<rect[^>]*x="(\d+)"[^>]*y="(\d+)"[^>]*width="(\d+)"[^>]*height="(\d+)"[^>]*>/g;

        const pins = [];
        const rects = [];

        let match;
        while ((match = pinRegex.exec(svgContent)) !== null) {
            pins.push({ cx: parseInt(match[1]), cy: parseInt(match[2]) });
        }
        while ((match = rectRegex.exec(svgContent)) !== null) {
            rects.push({
                x: parseInt(match[1]),
                y: parseInt(match[2]),
                width: parseInt(match[3]),
                height: parseInt(match[4])
            });
        }

        for (const pin of pins) {
            for (const rect of rects) {
                const rectRight = rect.x + rect.width;
                const rectBottom = rect.y + rect.height;

                if (pin.cx >= rect.x && pin.cx <= rectRight &&
                    pin.cy >= rect.y && pin.cy <= rectBottom) {

                    // 连接器的宽度通常<=25
                    if (rect.width <= 25) {
                        // 引脚应该在连接器外侧（左侧连接器：引脚x < rect.x; 右侧连接器：引脚x > rectRight）
                        const isLeftConnector = rect.x < 400; // 假设x<400是左侧设备
                        if (isLeftConnector) {
                            // 左侧连接器（SEAT）：引脚应该在rect左侧
                            if (pin.cx > rect.x + 2) {
                                errors.push(`❌ 规则违反: 引脚(cx=${pin.cx})在左侧连接器(左边界=${rect.x})内部！应在外侧（cx <= ${rect.x}）`);
                            }
                        } else {
                            // 右侧连接器（RPDU）：引脚应该在rect右侧
                            if (pin.cx < rectRight - 2) {
                                errors.push(`❌ 规则违反: 引脚(cx=${pin.cx})在右侧连接器(右边界=${rectRight})内部！应在外侧（cx >= ${rectRight}）`);
                            }
                        }
                    }
                }
            }
        }
        console.log(`   检查完成 (发现 ${pins.length} 个引脚, ${rects.length} 个矩形)`);
    }

    // ========== 规则2: 接线不能重叠（转折点不能相同）==========
    if (rules.mandatoryRules.wireLayout?.enforcement === 'strict') {
        console.log('🔍 检查规则2: 接线不能重叠...');

        const turningPoints = new Set();
        const lineRegex = /<polyline[^>]*points="([^"]*)"[^>]*>/g;
        let match;

        while ((match = lineRegex.exec(svgContent)) !== null) {
            const pointsStr = match[1];
            const points = pointsStr.split(' ').map(p => {
                const [x, y] = p.split(',').map(Number);
                return { x, y };
            });

            // 检查转折点（除了起点和终点）是否重复
            for (let i = 1; i < points.length - 1; i++) {
                const key = `${points[i].x},${points[i].y}`;
                if (turningPoints.has(key)) {
                    errors.push(`❌ 规则违反: 接线重叠！转折点重复: (${points[i].x}, ${points[i].y})`);
                }
                turningPoints.add(key);
            }
        }

        // 检查水平线是否平行且间距足够（仅警告，因为SVG两侧设备的线可能接近）
        const horizontalLines = [];
        const polylineRegex = /<polyline[^>]*points="([^"]*)"[^>]*>/g;

        while ((match = polylineRegex.exec(svgContent)) !== null) {
            const pointsStr = match[1];
            const points = pointsStr.split(' ').map(p => {
                const [x, y] = p.split(',').map(Number);
                return { x, y };
            });

            for (let i = 0; i < points.length - 1; i++) {
                if (points[i].y === points[i + 1].y) {
                    horizontalLines.push({
                        y: points[i].y,
                        x1: Math.min(points[i].x, points[i + 1].x),
                        x2: Math.max(points[i].x, points[i + 1].x)
                    });
                }
            }
        }

        // 按y坐标排序，检查同y坐标或相近y坐标的线段是否重叠
        horizontalLines.sort((a, b) => a.y - b.y);
        const minSpacing = rules.connectionRules?.wireSpacing || 25;

        for (let i = 0; i < horizontalLines.length; i++) {
            for (let j = i + 1; j < horizontalLines.length; j++) {
                const yDiff = Math.abs(horizontalLines[i].y - horizontalLines[j].y);

                // 如果y坐标完全相同或非常接近（<=5），检查x范围是否重叠
                if (yDiff <= 5) {
                    // 检查x范围是否有重叠
                    if (!(horizontalLines[i].x2 < horizontalLines[j].x1 ||
                          horizontalLines[j].x2 < horizontalLines[i].x1)) {
                        // x范围重叠了，这才是真正的错误
                        errors.push(`❌ 规则违反: 接线重叠！水平线段重叠: y=${horizontalLines[i].y} 和 y=${horizontalLines[j].y}`);
                    }
                } else if (yDiff < minSpacing) {
                    // y间距不足但不是完全重叠，只给警告
                    warnings.push(`⚠️  警告: 接线间距可能不足！y=${horizontalLines[i].y} 和 y=${horizontalLines[j].y} 间距=${yDiff}px < ${minSpacing}px`);
                }
            }
        }

        console.log(`   检查完成 (发现 ${turningPoints.size} 个转折点)`);
    }

    // ========== 规则3: 不能缺少任何元素 ==========
    if (rules.mandatoryRules.completeness?.enforcement === 'strict') {
        console.log('🔍 检查规则3: 不能缺少任何元素...');

        const requiredElements = [
            { pattern: '<defs>', desc: 'SVG定义' },
            { pattern: '<rect', desc: '设备框/连接器' },
            { pattern: '<circle', desc: '引脚' },
            { pattern: '<polyline', desc: '连接线' },
            { pattern: '<text', desc: '文本标签' },
            { pattern: 'id="ground-symbol"', desc: '接地符号' }
        ];

        for (const elem of requiredElements) {
            if (!svgContent.includes(elem.pattern)) {
                errors.push(`❌ 规则违反: 缺少必要元素: ${elem.desc} (${elem.pattern})`);
            }
        }

        // 检查设备数量
        const deviceCount = (svgContent.match(/<rect[^>]*width="140"[^>]*height="120"[^>]*>/g) || []).length +
                           (svgContent.match(/<rect[^>]*width="140"[^>]*height="140"[^>]*>/g) || []).length;
        if (deviceCount < 4) {
            errors.push(`❌ 规则违反: 设备数量不足！期望4个（RPDU×2 + SEAT×2），实际${deviceCount}个`);
        }

        console.log(`   检查完成 (设备数量: ${deviceCount})`);
    }

    // ========== 坐标规则检查 ==========
    if (rules.coordinateRules) {
        console.log('🔍 检查坐标规则...');

        const rpduX = rules.coordinateRules.RPDU?.deviceX;
        const seatX = rules.coordinateRules.SEAT?.deviceX;
        const gndX = rules.coordinateRules.GND?.x;

        // 检查RPDU设备x坐标
        if (rpduX) {
            const rpduRegex = /<rect[^>]*x="(\d+)"[^>]*width="140"[^>]*height="120"[^>]*>/g;
            let match;
            while ((match = rpduRegex.exec(svgContent)) !== null) {
                const x = parseInt(match[1]);
                if (x !== rpduX) {
                    warnings.push(`⚠️  警告: RPDU设备x坐标=${x}，规则要求=${rpduX}`);
                }
            }
        }

        // 检查SEAT设备x坐标
        if (seatX) {
            const seatRegex = /<rect[^>]*x="(\d+)"[^>]*width="140"[^>]*height="140"[^>]*>/g;
            let match;
            while ((match = seatRegex.exec(svgContent)) !== null) {
                const x = parseInt(match[1]);
                if (x !== seatX) {
                    warnings.push(`⚠️  警告: SEAT设备x坐标=${x}，规则要求=${seatX}`);
                }
            }
        }

        // 检查转折点是否使用规则规定的值
        const turningPoints = rules.connectionRules?.turningPoints || [280, 300, 320];
        const polylineRegex = /<polyline[^>]*points="([^"]*)"[^>]*>/g;
        let match;

        while ((match = polylineRegex.exec(svgContent)) !== null) {
            const pointsStr = match[1];
            const points = pointsStr.split(' ').map(p => {
                const [x, y] = p.split(',').map(Number);
                return { x, y };
            });

            for (let i = 1; i < points.length - 1; i++) {
                const tp = points[i].x;
                // 只检查水平转折点（y与前后不同）
                if (points[i].y !== points[i-1].y && points[i].y !== points[i+1].y) {
                    if (!turningPoints.includes(tp)) {
                        warnings.push(`⚠️  警告: 转折点x=${tp}，规则建议使用=${turningPoints.join(',')}`);
                    }
                }
            }
        }

        console.log(`   检查完成`);
    }

    return { errors, warnings };
}

function main() {
    const svgFilePath = process.argv[2];

    if (!svgFilePath) {
        console.log('');
        console.log('========================================');
        console.log('   EICD SVG 规则验证器');
        console.log('========================================');
        console.log('');
        console.log('使用方法: node validate-svg-rules.js <SVG文件路径>');
        console.log('');
        console.log('示例:');
        console.log('  node validate-svg-rules.js "d:\\项目\\schematic.svg"');
        console.log('');
        console.log('前提条件:');
        console.log('  规则文件必须存在于: d:\\trae\\商飞\\.eicd-rules.json');
        console.log('');
        process.exit(1);
    }

    console.log('');
    console.log('========================================');
    console.log('   EICD SVG 规则验证器');
    console.log('========================================');
    console.log('');
    console.log(`📁 SVG文件: ${svgFilePath}`);

    if (!fs.existsSync(svgFilePath)) {
        console.error(`❌ SVG文件不存在: ${svgFilePath}`);
        process.exit(1);
    }

    console.log(`📋 规则文件: ${RULES_FILE}`);
    const rules = loadRules();
    if (!rules) {
        process.exit(1);
    }
    console.log(`✅ 规则: ${rules.rulesName}`);
    console.log('');

    const svgContent = fs.readFileSync(svgFilePath, 'utf8');
    console.log(`📊 文件大小: ${svgContent.length} 字节`);
    console.log('');

    const { errors, warnings } = validateSVG(svgContent, rules);

    console.log('========================================');
    console.log('   验证结果');
    console.log('========================================');
    console.log('');

    if (warnings.length > 0) {
        console.log('⚠️  警告:');
        warnings.forEach(w => console.log(`   ${w}`));
        console.log('');
    }

    if (errors.length > 0) {
        console.log('❌ 错误:');
        errors.forEach(e => console.log(`   ${e}`));
        console.log('');
        console.log('========================================');
        console.log('   验证失败 ❌');
        console.log('========================================');
        process.exit(1);
    }

    console.log('✅ 所有规则验证通过！');
    console.log('');
    console.log('========================================');
    console.log('   验证成功 ✅');
    console.log('========================================');
    process.exit(0);
}

if (require.main === module) {
    main();
}

module.exports = { validateSVG, loadRules };
