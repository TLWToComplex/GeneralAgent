/**
 * 模板管理器
 * 负责管理所有可用的可视化模板
 */

const fs = require('fs');
const path = require('path');

class TemplateManager {
    constructor() {
        this.templatesDir = path.join(__dirname, '..', 'templates');
        this.templates = new Map();
        this.loadAllTemplates();
    }

    /**
     * 加载所有模板
     */
    loadAllTemplates() {
        this.templates.clear();
        
        try {
            if (!fs.existsSync(this.templatesDir)) {
                fs.mkdirSync(this.templatesDir, { recursive: true });
                return;
            }

            const files = fs.readdirSync(this.templatesDir);
            
            for (const file of files) {
                if (file.endsWith('.json')) {
                    try {
                        const templatePath = path.join(this.templatesDir, file);
                        const templateData = JSON.parse(fs.readFileSync(templatePath, 'utf8'));
                        
                        // 确保模板有基本结构
                        if (templateData.templateId) {
                            this.templates.set(templateData.templateId, templateData);
                        }
                    } catch (error) {
                        console.warn(`⚠️  加载模板文件失败: ${file}`, error.message);
                    }
                }
            }
            
            console.log(`✅ 已加载 ${this.templates.size} 个模板`);
        } catch (error) {
            console.error('❌ 加载模板目录失败:', error.message);
        }
    }

    /**
     * 获取所有模板列表
     */
    getAllTemplates() {
        const templates = [];
        
        for (const [id, template] of this.templates) {
            templates.push({
                templateId: template.templateId,
                templateName: template.templateName || '未命名模板',
                description: template.description || '',
                createdAt: template.createdAt || new Date().toISOString(),
                isDefault: template.metadata?.isDefault || false,
                tags: template.metadata?.tags || [],
                // 包含完整的模板数据
                positions: template.positions || {},
                connections: template.connections || [],
                styles: template.styles || {},
                canvas: template.canvas || {},
                layout: template.layout || {},
                deviceTypes: template.deviceTypes || {}
            });
        }
        
        // 按创建时间排序，最新的在前
        return templates.sort((a, b) => {
            return new Date(b.createdAt) - new Date(a.createdAt);
        });
    }

    /**
     * 获取指定模板
     */
    getTemplate(templateId) {
        return this.templates.get(templateId);
    }

    /**
     * 保存模板
     */
    saveTemplate(templateData) {
        try {
            if (!templateData.templateId) {
                templateData.templateId = `user_template_${Date.now()}`;
            }
            
            const fileName = `${templateData.templateId}.json`;
            const filePath = path.join(this.templatesDir, fileName);
            
            fs.writeFileSync(filePath, JSON.stringify(templateData, null, 2), 'utf8');
            
            // 更新内存中的模板
            this.templates.set(templateData.templateId, templateData);
            
            console.log(`✅ 模板已保存: ${fileName}`);
            return true;
        } catch (error) {
            console.error('❌ 保存模板失败:', error.message);
            return false;
        }
    }

    /**
     * 删除模板
     */
    deleteTemplate(templateId) {
        try {
            const fileName = `${templateId}.json`;
            const filePath = path.join(this.templatesDir, fileName);
            
            if (fs.existsSync(filePath)) {
                fs.unlinkSync(filePath);
            }
            
            this.templates.delete(templateId);
            
            console.log(`✅ 模板已删除: ${templateId}`);
            return true;
        } catch (error) {
            console.error('❌ 删除模板失败:', error.message);
            return false;
        }
    }

    /**
     * 复制模板
     */
    copyTemplate(sourceId, newName) {
        const sourceTemplate = this.templates.get(sourceId);
        if (!sourceTemplate) {
            console.error(`❌ 源模板不存在: ${sourceId}`);
            return null;
        }
        
        const newTemplate = {
            ...sourceTemplate,
            templateId: `user_template_${Date.now()}`,
            templateName: newName,
            description: `从 "${sourceTemplate.templateName}" 复制的模板`,
            createdAt: new Date().toISOString(),
            metadata: {
                ...sourceTemplate.metadata,
                isDefault: false,
                copiedFrom: sourceId
            }
        };
        
        this.saveTemplate(newTemplate);
        return newTemplate;
    }

    /**
     * 应用模板生成SVG
     */
    applyTemplate(templateId, eicdData) {
        const template = this.templates.get(templateId);
        if (!template) {
            console.error(`❌ 模板不存在: ${templateId}`);
            return null;
        }
        
        // 根据模板和EICD数据生成SVG
        // 这里需要根据具体的图表类型调用相应的生成器
        console.log(`🎨 应用模板: ${template.templateName}`);
        console.log(`   设备数量: ${Object.keys(template.positions || {}).length}`);
        console.log(`   连接数量: ${template.connections?.length || 0}`);
        
        return template;
    }

    /**
     * 获取默认模板
     */
    getDefaultTemplate() {
        // 查找标记为默认的模板
        for (const [id, template] of this.templates) {
            if (template.metadata?.isDefault) {
                return template;
            }
        }
        
        // 如果没有默认模板，返回第一个
        const firstTemplate = this.templates.values().next().value;
        return firstTemplate || null;
    }

    /**
     * 获取用户自定义模板
     */
    getUserTemplates() {
        const userTemplates = [];
        
        for (const [id, template] of this.templates) {
            // 用户模板通常以 user_ 开头或不是默认模板
            if (id.startsWith('user_') || !template.metadata?.isDefault) {
                userTemplates.push({
                    templateId: template.templateId,
                    templateName: template.templateName,
                    description: template.description,
                    createdAt: template.createdAt
                });
            }
        }
        
        return userTemplates;
    }

    /**
     * 刷新模板列表
     */
    refresh() {
        this.loadAllTemplates();
    }
}

module.exports = TemplateManager;
