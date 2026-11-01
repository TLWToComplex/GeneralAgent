#!/usr/bin/env node

/**
 * 交互式模板编辑器命令行界面
 * 支持用户拖拽编辑、保存到模板库、导出Capital XML
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const InteractiveTemplateEditor = require('./interactive-template-editor.js');

class CLITemplateEditor {
    constructor() {
        this.editor = new InteractiveTemplateEditor();
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            prompt: 'editor> '
        });
        this.isRunning = false;
    }

    /**
     * 启动编辑器
     */
    async start(svgPath, jsonPath) {
        try {
            // 加载SVG文件
            this.editor.loadSvgAsTemplate(svgPath, jsonPath);
            
            // 显示欢迎信息
            console.log('\n🎨 欢迎使用 EICD 交互式模板编辑器！');
            console.log('这是一个真正的交互式编辑器，您可以通过命令控制设备位置。');
            console.log('输入 "help" 查看可用命令，输入 "exit" 退出编辑器。\n');
            
            // 显示编辑器界面
            this.editor.showInteractiveEditor();
            
            // 启动命令行交互
            this.isRunning = true;
            this.startCommandLoop();
            
        } catch (error) {
            console.error('❌ 启动编辑器失败:', error.message);
            process.exit(1);
        }
    }

    /**
     * 启动命令循环
     */
    startCommandLoop() {
        this.rl.prompt();
        
        this.rl.on('line', (input) => {
            const command = input.trim();
            
            if (!command) {
                this.rl.prompt();
                return;
            }
            
            if (command === 'exit') {
                this.exit();
                return;
            }
            
            try {
                const result = this.editor.handleCommand(command);
                
                if (result.action === 'exit') {
                    this.exit();
                    return;
                }
                
                if (result.action === 'template_saved') {
                    console.log(`\n🎉 模板已保存成功！`);
                    console.log(`   下次使用时可以在可视化界面中选择此模板。`);
                    console.log(`   模板ID: ${result.templateId}`);
                    console.log(`   模板名称: ${result.templateName}`);
                }
                
                if (result.action === 'xml_exported') {
                    console.log(`\n🎉 Capital XML 导出成功！`);
                    console.log(`   项目: ${result.projectName}`);
                    console.log(`   文件: ${result.xmlPath}`);
                }
                
            } catch (error) {
                console.error(`❌ 命令执行失败: ${error.message}`);
            }
            
            this.rl.prompt();
        });
        
        this.rl.on('close', () => {
            this.exit();
        });
    }

    /**
     * 退出编辑器
     */
    exit() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        console.log('\n👋 感谢使用交互式模板编辑器！');
        console.log('您的编辑已保存，下次可以继续使用。\n');
        
        this.rl.close();
        process.exit(0);
    }
}

/**
 * 主函数
 */
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 2) {
        console.log('用法: node cli-editor.js <svg文件路径> <json文件路径>');
        console.log('示例: node cli-editor.js "d:\\trae\\商飞\\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1)_from_template.svg" "d:\\trae\\商飞\\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json"');
        process.exit(1);
    }
    
    const svgPath = args[0];
    const jsonPath = args[1];
    
    // 检查文件是否存在
    if (!fs.existsSync(svgPath)) {
        console.error(`❌ SVG文件不存在: ${svgPath}`);
        process.exit(1);
    }
    
    if (!fs.existsSync(jsonPath)) {
        console.error(`❌ JSON文件不存在: ${jsonPath}`);
        process.exit(1);
    }
    
    const cliEditor = new CLITemplateEditor();
    await cliEditor.start(svgPath, jsonPath);
}

// 如果直接运行此文件
if (require.main === module) {
    main().catch(error => {
        console.error('❌ 程序运行失败:', error);
        process.exit(1);
    });
}

module.exports = CLITemplateEditor;