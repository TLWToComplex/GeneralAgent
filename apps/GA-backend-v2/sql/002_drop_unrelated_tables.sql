-- ============================================================================
-- GeneralAgent V2 · 清理与「用户登录」无关的表
-- ============================================================================
-- 用途：V2 后端当前只迁移了用户登录能力，只依赖下面两张表，其余表可以删除。
--
--   ✅ 保留：
--        ai_user                用户账号（登录、锁定、密码哈希、扩展字段）
--        ai_password_history    密码历史（禁止复用近 5 次历史密码）
--        ai_dsh_instance        「新建会话进 dsh」的用户→实例映射（由 003 新建，不在老库 dump 里，
--                               本脚本的待删清单里没有它，因此不受影响）
--
--   ❌ 删除（16 张，全部不在 V2 代码里被引用）：
--        ai_agent                    AI 智能体
--        ai_chat_record              对话记录
--        ai_chat_session_summary     会话摘要
--        ai_kb_chat                  知识库对话
--        ai_mcp_server               MCP 服务
--        ai_models                   模型配置
--        ai_permissions              权限
--        ai_physical_node            物理节点
--        ai_platform                 平台
--        ai_prompt                   提示词
--        ai_skill                    技能
--        ai_system_config            系统配置
--        ai_thinking_chain           思维链
--        ai_user_feedback            用户反馈
--        ai_user_group               用户组
--        ai_user_group_relation      用户组关系
--
-- ⚠️ 破坏性且不可回滚：MySQL 的 DDL 会隐式提交，写进事务里也回滚不了。
--    执行前务必先备份，确认没有别的服务（老项目后台、前端其它模块、定时任务）
--    还在读写这些表。
--
-- 备份（在服务器上、进 mysql 客户端之前执行）：
--     mysqldump -h127.0.0.1 -uroot -p \
--       --single-transaction --routines --triggers --default-character-set=utf8mb4 \
--       ai_service > ai_service_backup_$(date +%Y%m%d_%H%M%S).sql
--
-- 执行：
--     mysql -h127.0.0.1 -uroot -p ai_service < 002_drop_unrelated_tables.sql
--
-- 回滚：只能从上面的备份里恢复被删的表（或整库恢复）。
-- ============================================================================

SET NAMES utf8mb4;

-- ============================================================================
-- 第一步：先核对（只读，不改任何数据）
-- 建议先把这一段单独执行一遍，确认「将被删除的表」与预期一致再往下走。
-- ============================================================================

-- 1.1 当前库里都有哪些表（判断有没有保留清单之外的"意外表"）
SELECT TABLE_NAME AS `现有表`, TABLE_ROWS AS `约行数`, TABLE_COMMENT AS `注释`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;

-- 1.2 本次会被删除的表（必须正好 16 张；TABLE_ROWS 对 InnoDB 是估算值）
SELECT TABLE_NAME AS `将被删除的表`, TABLE_ROWS AS `约行数`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_TYPE = 'BASE TABLE'
  AND TABLE_NAME IN (
    'ai_agent', 'ai_chat_record', 'ai_chat_session_summary', 'ai_kb_chat',
    'ai_mcp_server', 'ai_models', 'ai_permissions', 'ai_physical_node',
    'ai_platform', 'ai_prompt', 'ai_skill', 'ai_system_config',
    'ai_thinking_chain', 'ai_user_feedback', 'ai_user_group', 'ai_user_group_relation'
  )
ORDER BY TABLE_NAME;

-- 1.3 删除后仍然保留的表（应该只剩 ai_user / ai_password_history；若已执行 003，还会看到 ai_dsh_instance）
SELECT TABLE_NAME AS `保留表`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
  AND TABLE_NAME NOT IN (
    'ai_agent', 'ai_chat_record', 'ai_chat_session_summary', 'ai_kb_chat',
    'ai_mcp_server', 'ai_models', 'ai_permissions', 'ai_physical_node',
    'ai_platform', 'ai_prompt', 'ai_skill', 'ai_system_config',
    'ai_thinking_chain', 'ai_user_feedback', 'ai_user_group', 'ai_user_group_relation'
  )
ORDER BY TABLE_NAME;

-- 1.4 兜底：待删表的行数合计（数据量心里有数）
SELECT SUM(TABLE_ROWS) AS `将被删除的约数据行数`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
    'ai_agent', 'ai_chat_record', 'ai_chat_session_summary', 'ai_kb_chat',
    'ai_mcp_server', 'ai_models', 'ai_permissions', 'ai_physical_node',
    'ai_platform', 'ai_prompt', 'ai_skill', 'ai_system_config',
    'ai_thinking_chain', 'ai_user_feedback', 'ai_user_group', 'ai_user_group_relation'
  );

-- ============================================================================
-- 第二步：执行删除
-- 从这一行往下都是真正的删除动作，确认备份完成、第一步核对通过后再执行。
-- ============================================================================

-- 关掉外键检查：即使这些表之间有外键约束也按顺序删除不会报错
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------- AI 能力相关 ----------------------------
DROP TABLE IF EXISTS `ai_agent`;                  -- AI 智能体
DROP TABLE IF EXISTS `ai_prompt`;                 -- 提示词
DROP TABLE IF EXISTS `ai_skill`;                  -- 技能
DROP TABLE IF EXISTS `ai_thinking_chain`;         -- 思维链
DROP TABLE IF EXISTS `ai_models`;                 -- 模型配置
DROP TABLE IF EXISTS `ai_mcp_server`;             -- MCP 服务
DROP TABLE IF EXISTS `ai_platform`;               -- 平台
DROP TABLE IF EXISTS `ai_physical_node`;          -- 物理节点

-- ---------------------------- 对话与知识库 ----------------------------
DROP TABLE IF EXISTS `ai_chat_record`;            -- 对话记录（数据量最大的一张）
DROP TABLE IF EXISTS `ai_chat_session_summary`;   -- 会话摘要
DROP TABLE IF EXISTS `ai_kb_chat`;                -- 知识库对话

-- ---------------------------- 权限与用户组 ----------------------------
DROP TABLE IF EXISTS `ai_permissions`;            -- 权限
DROP TABLE IF EXISTS `ai_user_group`;             -- 用户组
DROP TABLE IF EXISTS `ai_user_group_relation`;    -- 用户组关系

-- ---------------------------- 其它 ----------------------------
DROP TABLE IF EXISTS `ai_system_config`;          -- 系统配置
DROP TABLE IF EXISTS `ai_user_feedback`;          -- 用户反馈

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 第三步：后置校验
-- ============================================================================

-- 3.1 剩下的表（ai_user / ai_password_history，若已执行 003 还会有 ai_dsh_instance）
SHOW TABLES;

-- 3.2 保留的表必须还能用（能查出行数/结构）
SELECT COUNT(*) AS `ai_user 行数` FROM `ai_user`;
SELECT COUNT(*) AS `ai_password_history 行数` FROM `ai_password_history`;

-- 3.3 结构完好性抽查（列数应为 16 / 4）
SELECT COUNT(*) AS `ai_user 列数`
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_user';

SELECT COUNT(*) AS `ai_password_history 列数`
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_password_history';

-- 3.4 确认待删表已全部不存在（应为 0 行）
SELECT TABLE_NAME AS `残留的待删表`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
    'ai_agent', 'ai_chat_record', 'ai_chat_session_summary', 'ai_kb_chat',
    'ai_mcp_server', 'ai_models', 'ai_permissions', 'ai_physical_node',
    'ai_platform', 'ai_prompt', 'ai_skill', 'ai_system_config',
    'ai_thinking_chain', 'ai_user_feedback', 'ai_user_group', 'ai_user_group_relation'
  );

-- 说明：库里还有两个存储过程（sp_cleanup_etl_logs、sp_generate_monthly_attendance），
-- 它们操作的是 etl_job_log / attendance_summary 等本库中并不存在的表，与本脚本无关，
-- 因此这里不删除。若确认无用，可另外执行：
--     DROP PROCEDURE IF EXISTS `sp_cleanup_etl_logs`;
--     DROP PROCEDURE IF EXISTS `sp_generate_monthly_attendance`;