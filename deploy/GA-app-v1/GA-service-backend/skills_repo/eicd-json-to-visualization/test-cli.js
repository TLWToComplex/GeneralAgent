#!/usr/bin/env node
/**
 * 测试 CLI 交互版本
 */

const { spawn } = require('child_process');
const path = require('path');

const cliPath = path.join(__dirname, 'cli.js');
const jsonFile = 'd:\\trae\\商飞\\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json';

const child = spawn('node', [cliPath, jsonFile], {
    stdio: ['pipe', 'pipe', 'pipe']
});

let output = '';

child.stdout.on('data', (data) => {
    const text = data.toString();
    output += text;
    console.log(text);
    
    // 根据输出内容自动回复
    if (text.includes('请选择模板编号')) {
        console.log('[自动回复: 1]');
        child.stdin.write('1\n');
    } else if (text.includes('请选择图表类型编号')) {
        console.log('[自动回复: 1]');
        child.stdin.write('1\n');
    }
});

child.stderr.on('data', (data) => {
    console.error(data.toString());
});

child.on('close', (code) => {
    console.log(`\n子进程退出，退出码: ${code}`);
});
