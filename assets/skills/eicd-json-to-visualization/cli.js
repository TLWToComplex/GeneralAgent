#!/usr/bin/env node
/**
 * EICD JSON to Visualization Skill - CLI 交互式版本
 * 支持用户交互选择模板和图表类型（合并为一次选择）
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const EICDVisualizationSkill = require('./index.js');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function askQuestion(question) {
    return new Promise((resolve) => {
        rl.question(question, (answer) => {
            resolve(answer.trim());
        });
    });
}

async function main() {
    console.log('🚀 EICD JSON to Visualization Skill 启动\n');
    
    const skill = new EICDVisualizationSkill();
    
    // 获取命令行参数
    const args = process.argv.slice(2);
    const jsonFile = args[0] || 'd:\\trae\\商飞\\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json';
    
    // 阶段一：文件确认与准备
    console.log('📁 阶段一：文件确认与准备\n');
    const fileCheck = await skill.phase1_FilePreparation({ jsonFile });
    if (!fileCheck.success) {
        console.error('❌', fileCheck.error);
        rl.close();
        return;
    }
    
    // 阶段二：模板和图表类型选择（合并，交互式）
    console.log('\n🎨 阶段二：选择模板或图表类型\n');
    const selection = await skill.phase2_TemplateAndDiagramSelection({});
    
    if (!selection.success || !selection.requireUserSelection) {
        console.log('✅ 使用默认选项');
        rl.close();
        return;
    }
    
    // 显示选项列表
    console.log(`📋 可用选项:\n`);
    let validChoices = [];
    selection.choices.forEach((choice, index) => {
        if (choice.type !== 'separator') {
            validChoices.push(choice);
            console.log(`  ${validChoices.length}. ${choice.label}`);
            console.log(`     ${choice.description}`);
            console.log('');
        } else {
            console.log(`  ${choice.label}`);
            console.log('');
        }
    });
    
    // 让用户选择
    const answer = await askQuestion(`请选择选项编号 (1-${validChoices.length}, 默认1): `);
    const choiceIndex = parseInt(answer) || 1;
    const selectedChoice = validChoices[choiceIndex - 1] || validChoices[0];
    
    console.log(`✅ 已选择: ${selectedChoice.label}\n`);
    
    // 准备生成参数
    let template = null;
    let diagramType = { id: 'schematic_v2', label: '⚡ 电气原理图（推荐）' };
    
    if (selectedChoice.type === 'template') {
        template = selectedChoice.template;
        console.log(`   使用模板: ${template.templateName}`);
    } else if (selectedChoice.type === 'diagram_type') {
        diagramType = { id: selectedChoice.id, label: selectedChoice.label };
        console.log(`   图表类型: ${diagramType.label}`);
    } else if (selectedChoice.type === 'default_diagram') {
        console.log(`   使用默认电气原理图`);
    }
    
    // 阶段三：生成图表
    console.log('\n🎨 阶段三：生成可视化图表\n');
    const generation = await skill.phase4_GenerateVisualization(template, diagramType);
    
    // 阶段四：生成操作文档
    console.log('\n📝 阶段四：生成操作文档\n');
    await skill.phase5_CreateOperationDoc(generation);
    
    console.log('\n✅ 技能执行完成！');
    console.log('===================');
    console.log('SVG文件:', generation.svgFile);
    console.log('操作文档:', generation.operationDoc);
    
    rl.close();
}

main().catch(error => {
    console.error('❌ 执行失败:', error);
    process.exit(1);
});
