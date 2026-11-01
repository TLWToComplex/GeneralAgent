const TemplateManager = require('./template-manager.js');

// 测试模板选择功能
function testTemplateSelection() {
    console.log('🎯 测试模板选择功能...\n');
    
    const manager = new TemplateManager();
    const templates = manager.getAllTemplates();
    
    console.log('📋 可用模板列表:');
    templates.forEach((template, index) => {
        console.log(`  ${index + 1}. ${template.templateName}`);
        console.log(`     ID: ${template.templateId}`);
        console.log(`     描述: ${template.description}`);
        console.log(`     创建时间: ${template.createdAt}`);
        console.log(`     默认模板: ${template.isDefault ? '是' : '否'}`);
        console.log('');
    });
    
    // 查找用户编辑的模板
    const userTemplates = templates.filter(t => t.templateId.startsWith('user_template_'));
    if (userTemplates.length > 0) {
        console.log('✅ 找到用户编辑的模板！');
        userTemplates.forEach(template => {
            console.log(`   - ${template.templateName} (${template.templateId})`);
        });
    } else {
        console.log('⚠️  未找到用户编辑的模板');
    }
    
    // 测试加载用户模板
    if (userTemplates.length > 0) {
        const latestUserTemplate = userTemplates[userTemplates.length - 1];
        console.log(`\n🔄 正在加载最新用户模板: ${latestUserTemplate.templateName}`);
        
        try {
            const fullTemplate = manager.getTemplate(latestUserTemplate.templateId);
            if (fullTemplate) {
                console.log(`✅ 模板加载成功！`);
                console.log(`   设备数量: ${Object.keys(fullTemplate.positions).length}`);
                console.log(`   连接数量: ${fullTemplate.connections.length}`);
                console.log(`   模板描述: ${fullTemplate.description}`);
                
                // 验证模板位置信息
                console.log('\n📍 设备位置信息:');
                Object.entries(fullTemplate.positions).forEach(([deviceId, pos]) => {
                    console.log(`   ${deviceId}: (${pos.x}, ${pos.y})`);
                });
            } else {
                console.log('❌ 模板加载失败: 模板不存在');
            }
        } catch (error) {
            console.error(`❌ 模板加载失败: ${error.message}`);
        }
    }
    
    console.log('\n✅ 模板选择功能测试完成！');
    console.log('下次可视化时，用户可以在界面中选择这些编辑过的模板。');
}

// 运行测试
if (require.main === module) {
    testTemplateSelection();
}

module.exports = { testTemplateSelection };