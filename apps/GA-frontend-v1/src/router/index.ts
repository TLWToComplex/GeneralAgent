import { createRouter, createWebHistory } from 'vue-router';
import { ROUTES, PAGE_TITLES, STORAGE_KEYS as APP_STORAGE_KEYS } from '@/config/constants';
import { getSystemName } from '@/utils/RuntimeConfig';
import StorageService, { STORAGE_KEYS as SVC_STORAGE_KEYS } from '@/utils/StorageService';
import { listPlatformModels } from '@/services/aiPlatformModel';
import { listMcpServers } from '@/services/mcpServer';
import { listAiAgents } from '@/services/aiAgent';
import { getUserPreferences } from '@/services/aiUserPreferences';

// 设置页的所有合法子路径（从 ROUTES 推导，新增/删除子页时无需同步维护）
const SETTINGS_SUB_ROUTES = Object.values(ROUTES).filter(
    (path) => path.startsWith(`${ROUTES.SETTINGS}/`)
);

// 读取上次访问的设置子页，非法或已下线的路径回退到模型服务
function getLastSettingsRoute(): string {
    const saved = localStorage.getItem(APP_STORAGE_KEYS.LAST_SETTINGS_SUB_PAGE) || '';
    return SETTINGS_SUB_ROUTES.includes(saved) ? saved : ROUTES.MODEL_SERVICE;
}

function rememberLastSettingsRoute(path: string): void {
    if (SETTINGS_SUB_ROUTES.includes(path)) {
        localStorage.setItem(APP_STORAGE_KEYS.LAST_SETTINGS_SUB_PAGE, path);
    }
}

// 路由配置
const routes = [
    {
        path: ROUTES.HOME,
        name: 'home',
        redirect: ROUTES.CHAT,
        meta: {
            title: PAGE_TITLES.HOME
        }
    },
    {
        path: ROUTES.WELCOME,
        name: 'welcome',
        component: () => import('@/views/WelcomeView.vue'),
        meta: {
            title: PAGE_TITLES.WELCOME,
            hideLayout: true // 标记此页面不显示主布局
        }
    },

    {
        path: ROUTES.LOGIN,
        name: 'login',
        component: () => import('@/views/LoginView.vue'),
        meta: {
            title: PAGE_TITLES.LOGIN,
            hideLayout: true
        }
    },
    {
        path: ROUTES.REGISTER,
        name: 'register',
        component: () => import('@/views/RegisterView.vue'),
        meta: {
            title: PAGE_TITLES.REGISTER,
            hideLayout: true
        }
    },
    {
        path: ROUTES.AUTH,
        name: 'auth',
        redirect: ROUTES.LOGIN,
        meta: {
            title: PAGE_TITLES.AUTH,
            hideLayout: true
        }
    },

    {
        path: ROUTES.CHAT,
        name: 'chat',
        component: () => import('@/views/ChatView.vue'),
        meta: {
            title: PAGE_TITLES.CHAT
        }
    },
    {
        path: ROUTES.SETTINGS,
        name: 'settings',
        component: () => import('@/views/SettingsView.vue'),
        redirect: () => getLastSettingsRoute(),
        meta: {
            title: PAGE_TITLES.SETTINGS
        },
        children: [
            {
                path: 'role-settings',
                name: 'roleSettings',
                component: () => import('@/views/RoleSettingsView.vue'),
                meta: {
                    title: PAGE_TITLES.ROLE_SETTINGS
                }
            },
            {
                path: 'model-service',
                name: 'modelService',
                component: () => import('@/views/ModelServiceView.vue'),
                meta: {
                    title: PAGE_TITLES.MODEL_SERVICE
                }
            },
            {
                path: 'mcp-server',
                name: 'mcpServer',
                component: () => import('@/views/McpServerView.vue'),
                meta: {
                    title: PAGE_TITLES.MCP_SERVER
                }
            },
            {
                path: 'chat-preferences',
                name: 'chatPreferences',
                component: () => import('@/views/ChatPreferencesView.vue'),
                meta: {
                    title: PAGE_TITLES.CHAT_PREFERENCES
                }
            },
            {
                path: 'knowledge-base',
                name: 'knowledgeBase',
                component: () => import('@/views/KnowledgeBaseView.vue'),
                meta: {
                    title: PAGE_TITLES.KNOWLEDGE_BASE
                }
            },
            {
                path: 'rule-skill-settings',
                name: 'ruleSkillSettings',
                component: () => import('@/views/RuleSkillSettingsView.vue'),
                meta: {
                    title: PAGE_TITLES.RULE_SKILL_SETTINGS
                }
            },
            {
                path: 'user-management',
                name: 'userManagement',
                component: () => import('@/views/UserManagementView.vue'),
                meta: {
                    title: PAGE_TITLES.USER_MANAGEMENT,
                    requiresAdmin: true
                }
            }
        ]
    },
    {
        path: ROUTES.ACCOUNT,
        name: 'account',
        component: () => import('@/views/AccountView.vue'),
        redirect: '/account/profile',
        meta: {
            title: PAGE_TITLES.ACCOUNT
        },
        children: [
            {
                path: 'profile',
                name: 'profile',
                component: () => import('@/views/account/ProfileView.vue'),
                meta: {
                    title: PAGE_TITLES.ACCOUNT + ' - 个人资料'
                }
            },
            {
                path: 'security',
                name: 'security',
                component: () => import('@/views/account/SecurityView.vue'),
                meta: {
                    title: PAGE_TITLES.ACCOUNT + ' - 安全'
                }
            }
        ]
    },
    // 404 页面
    {
        path: ROUTES.NOT_FOUND,
        name: 'notFound',
        component: () => import('@/views/NotFoundView.vue'),
        meta: {
            title: PAGE_TITLES.NOT_FOUND,
            hideLayout: true
        }
    },
    // 未匹配的路由跳转到 404
    {
        path: '/:pathMatch(.*)*',
        name: 'notFoundCatchAll',
        redirect: ROUTES.NOT_FOUND
    }
];

// 创建路由实例
const router = createRouter({
    history: createWebHistory('/'),
    routes
});

// 全局前置守卫，更新页面标题、校验认证与权限
router.beforeEach(async (to, _from, next) => {
    const rawTitle = (to.meta.title as string) || '';
    const parts = rawTitle.split(' - ');
    const suffix = parts.length > 1 ? parts.slice(1).join(' - ') : rawTitle;
    const sysName = (getSystemName() || 'MCP客户端').trim();
    document.title = suffix ? `${sysName} - ${suffix}` : sysName;

    // 检查是否需要认证的页面（除了认证相关页面）
    const requiresAuth = ![
        ROUTES.LOGIN, 
        ROUTES.REGISTER, 
        ROUTES.AUTH, 
        ROUTES.WELCOME,
        ROUTES.NOT_FOUND
    ].includes(to.path);

    // 检查是否存在持久化的访问令牌并恢复
    const persistToken = localStorage.getItem('access_token');
    if (persistToken) {
        StorageService.setAccessToken(persistToken, true);
    }

    // 检查用户是否已登录（检查是否存在访问令牌）
    const accessToken = StorageService.getAccessToken();
    const needUpdateMsg = localStorage.getItem(APP_STORAGE_KEYS.NEED_UPDATE_MSG) === 'true';

    // 已登录且仍需补充初始化信息时，除欢迎页和404外统一回到欢迎页
    if (
        accessToken &&
        needUpdateMsg &&
        to.path !== ROUTES.WELCOME &&
        to.path !== ROUTES.NOT_FOUND
    ) {
        next(ROUTES.WELCOME);
        return;
    }

    // 已登录用户不应再次访问登录页，统一回到聊天页
    if (to.path === ROUTES.LOGIN && accessToken) {
        next(ROUTES.CHAT);
        return;
    }

    // 如果页面需要认证但用户未登录，则重定向到登录页面
    if (requiresAuth && !accessToken) {
        next(ROUTES.LOGIN);
        return;
    }

    const requiresAdmin = to.matched.some(record => !!record.meta?.requiresAdmin);
    if (requiresAdmin) {
        let isAdmin = false;
        try {
            const profileRaw = localStorage.getItem('user-profile');
            const profile = profileRaw ? JSON.parse(profileRaw) : null;
            isAdmin = String(profile?.username || '').trim().toLowerCase() === 'admin';
        } catch {
            isAdmin = false;
        }

        if (!isAdmin) {
            next(ROUTES.MODEL_SERVICE);
            return;
        }
    }

    // 如果用户不需要补充初始化信息且尝试访问欢迎页面，则重定向到聊天页面
    if (to.path === ROUTES.WELCOME) {
        if (!needUpdateMsg) {
            next(ROUTES.CHAT);
            return;
        }
    }

    try {
        if (to.path === ROUTES.CHAT) {
            const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();

            // 并行请求模型/服务/智能体/偏好，避免串行等待阻塞导航
            const [modelsResult, serversResult, agentsResult, prefsResult] = await Promise.allSettled([
                listPlatformModels(),
                listMcpServers(),
                listAiAgents(),
                getUserPreferences()
            ]);

            if (modelsResult.status === 'fulfilled') {
                const arr = modelsResult.value;
                const providers = arr.map((item: any) => ({
                    name: item.name,
                    iconClass: 'custom',
                    iconText: (item.name || 'P').charAt(0).toUpperCase(),
                    avatar: item.avatar?.url || '',
                    backgroundColor: item.backgroundColor || undefined,
                    providerIcon: item.providerIcon
                }));
                const modelsMap: Record<string, any> = {};
                arr.forEach((item: any) => {
                    const groupsRecord: Record<string, any> = {};
                    (item.models || []).forEach((g: any) => {
                        groupsRecord[g.id] = {
                            id: g.id,
                            name: g.name || g.id,
                            models: (g.models || []).map((m: any) => ({ id: m.id, name: m.name || m.id, iconText: m.iconText || (m.name || 'M').charAt(0).toUpperCase(), types: m.types || [] }))
                        };
                    });
                    modelsMap[item.name] = {
                        apiKey: item.credentials?.apiKey || (item.noApiKeyRequired ? 'sk-no-key' : ''),
                        apiUrl: sanitizeUrl(item.connection?.apiBaseUrl),
                        models: groupsRecord,
                        avatar: item.avatar?.url || '',
                        backgroundColor: item.backgroundColor || undefined,
                        noApiKeyRequired: !!item.noApiKeyRequired,
                        providerIcon: item.providerIcon,
                        type: item.type || 'OpenAI'
                    };
                });
                localStorage.setItem('mcp-providers', JSON.stringify(providers));
                localStorage.setItem('mcp-models', JSON.stringify(modelsMap));

                try {
                    const existing = StorageService.getApiConfig();
                    const needInit = !existing || !existing.model || !existing.apiKey || !existing.apiBaseUrl;
                    if (needInit) {
                        const firstProvider = Object.keys(modelsMap)[0];
                        const svc = firstProvider ? modelsMap[firstProvider] : null;
                        if (svc && svc.models) {
                            const groupKeys = Object.keys(svc.models);
                            const firstGroup = groupKeys.length > 0 ? svc.models[groupKeys[0]] : null;
                            const firstModel = firstGroup && Array.isArray(firstGroup.models) && firstGroup.models.length > 0 ? firstGroup.models[0] : null;
                            if (firstModel) {
                                const apiCfg = {
                                    apiKey: svc.apiKey || '',
                                    apiBaseUrl: svc.apiUrl || '',
                                    model: firstModel.id
                                };
                                // 清理反引号与空格
                                apiCfg.apiBaseUrl = (apiCfg.apiBaseUrl || '').replace(/`/g, '').trim();
                                StorageService.setApiConfig(apiCfg);
                                window.dispatchEvent(new Event('mcp-models-changed'));
                                
                            }
                        }
                    }
                } catch {}
            }

            if (serversResult.status === 'fulfilled') {
                const res = serversResult.value;
                const arr: any[] = Array.isArray(res?.data) ? res.data : [];
                const serversList = arr.map((item: any) => ({ id: item.id, name: item.name }));
                const serversData: Record<string, any> = {};
                const normalizeHeaders = (headers: unknown) => Array.isArray(headers)
                    ? headers.filter((h: any) => h && typeof h.key === 'string' && typeof h.value === 'string')
                    : (headers && typeof headers === 'object'
                        ? Object.entries(headers as Record<string, unknown>)
                            .filter(([key, value]) => key.trim().length > 0 && typeof value === 'string')
                            .map(([key, value]) => ({ key: key.trim(), value: value as string }))
                        : []);
                arr.forEach((item: any) => {
                    serversData[item.id] = {
                        id: item.id,
                        uuid: item.uuid,
                        name: item.name || '',
                        description: item.description || '',
                        type: item.type || 'sse',
                        url: sanitizeUrl(item.url || ''),
                        timeout: typeof item.timeout === 'number' ? item.timeout : 60,
                        headers: normalizeHeaders(item.headers),
                        tools: Array.isArray(item.tools) ? item.tools.map((t: any) => ({ id: t.id, name: t.name, description: t.description || '' })) : []
                    };
                });
                localStorage.setItem('mcp-servers-list', JSON.stringify(serversList));
                localStorage.setItem('mcp-servers-data', JSON.stringify(serversData));
                document.dispatchEvent(new CustomEvent('mcp-server-config-changed'));
            }

            if (agentsResult.status === 'fulfilled') {
                const res = agentsResult.value;
                const arr: any[] = Array.isArray(res?.data) ? res.data : [];
                const mapped = arr.map((item: any) => {
                    const m = item.config?.model || {};
                    const normalizedModel = {
                        service: m.service,
                        name: m.name,
                        temperature: typeof m.temperature === 'number' ? m.temperature : 0.7,
                        top_p: typeof m.topP === 'number' ? m.topP : (typeof m.top_p === 'number' ? m.top_p : 1.0),
                        presence_penalty: typeof m.presencePenalty === 'number' ? m.presencePenalty : (typeof m.presence_penalty === 'number' ? m.presence_penalty : 0),
                        frequency_penalty: typeof m.frequencyPenalty === 'number' ? m.frequencyPenalty : (typeof m.frequency_penalty === 'number' ? m.frequency_penalty : 0),
                        apiKey: m.apiKey,
                        apiUrl: sanitizeUrl(m.apiUrl)
                    };
                    const resolvedOrchestratorUrl = sanitizeUrl((item.config?.orchestrator?.serviceUrl) || (item.config?.orchestrator?.url) || (item.config?.orchestrator?.endpoint) || (item.config?.orchestrator?.apiUrl));
                    const basicConfig = {
                        ...(item.config?.basic || {}),
                        type: item.config?.basic?.type || item.agent_type || 'assistant',
                        visibility: item.config?.basic?.visibility || item.visibility || 'private'
                    };
                    const skills = Array.isArray(item.skills) ? item.skills : (Array.isArray(item.config?.skills) ? item.config.skills : []);
                    return {
                        id: item.id,
                        name: item.name,
                        description: item.description,
                        themeColor: item.themeColor,
                        uuid: item.uuid,
                        agent_type: item.agent_type || basicConfig.type,
                        visibility: item.visibility || basicConfig.visibility,
                        skills,
                        config: {
                            basic: basicConfig,
                            prompt: { ...(item.config?.prompt || {}) },
                            orchestrator: { serviceUrl: resolvedOrchestratorUrl },
                            model: normalizedModel,
                            knowledge: { ...(item.config?.knowledge || {}) },
                            mcp: { ...(item.config?.mcp || { enabledServerIdentifiers: [] }) },
                            skills,
                            phrases: Array.isArray(item.config?.phrases) ? item.config.phrases : []
                        }
                    } as any;
                });
                StorageService.setAgents(mapped);
                window.dispatchEvent(new Event('agents-updated'));
            }

            if (prefsResult.status === 'fulfilled') {
                const prefRes = prefsResult.value;
                const prefs = (prefRes?.data?.preferences) || {};
                StorageService.set(SVC_STORAGE_KEYS.USER_PREFERENCES, prefs);
                const prompt = typeof prefs.prompt === 'string' ? prefs.prompt.trim() : '';
                if (prompt) {
                    StorageService.setSystemMessage(prompt);
                }
                window.dispatchEvent(new CustomEvent('user-preferences-changed', { detail: { preference: 'all', value: prefs } }));
            }
        }
    } finally {
        next();
    }
});

// 记录最后访问的设置子页，供下次进入 /settings 时还原
router.afterEach((to) => {
    rememberLastSettingsRoute(to.path);
});

export default router;
