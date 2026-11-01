-- ============================================================================
-- GeneralAgent V2 · 用户 ↔ dsh 实例映射表
-- ============================================================================
-- 用途：前置代理（apps/proxy）需要知道「登录用户该被反代到哪个 dsh 容器」。
--       本表是这条映射关系的唯一权威来源，替代 proxy/server.js 里硬编码的 ROUTES 常量。
--
-- 与部署脚本的契约（apps/proxy/server.js + dsh/docker/dsh-new.sh）：
--
--   container_name   dsh-new.sh 的第一个参数 <Name>，如 dsh-web-a
--   proxy_user       dsh-new.sh 的第三个参数 <ProxyUser>，如 a
--                    —— 它同时是 tokens.d 下启动令牌文件的文件名（dsh-new.sh 写入
--                       $TOKENS_DIR/<ProxyUser>），proxy 用它换取 dsh 会话 cookie
--   host + port      dsh 自己的监听地址（dsh-new.sh 写死 127.0.0.1 + 指定端口，
--                    容器 --network host，端口不进 docker 映射，外部无法直达）
--   token_file       启动令牌文件的完整路径；可为空，为空时由 proxy 按
--                    「<它自己的 TOKENS_DIR>/<proxy_user>」推导（就是现在的行为）
--
-- 为什么用 status 而不是 is_del：
--   ai_user 用 is_del 软删除，但映射关系与账号不同 —— 停用一个用户的工作台时，
--   端口与容器仍然真实占用着，proxy 需要区分「没登记」和「登记了但已停用」并给出
--   不同提示；同时保留行也便于审计与恢复。因此这里用 status（1 启用 / 0 停用）表达
--   生命周期，不引入 is_del，也避免「唯一索引 + 软删除」导致无法重建的问题。
--
-- 唯一性约束是刻意的：
--   uk_user_uuid / uk_container_name / uk_proxy_user / uk_host_port
--   —— 一个用户只能有一个实例、一个容器名与一个代理令牌文件不能复用、
--      同一地址端口不能被两个用户抢占（端口冲突会让后起的容器静默绑定失败）。
--
-- ⚠️ 本脚本是**新增表**（IF NOT EXISTS），不删除、不修改任何已有表与数据。
--    但它会创建唯一索引；若库里已存在同名表，本脚本不会改动它，需要手工核对结构。
--
-- 执行：
--     mysql -h127.0.0.1 -uroot -p GA-v2 < 003_init_dsh_instance.sql
--   （库名以 config/config.yaml 的 database.url 为准）
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================================
-- 第一步：先核对（只读，不改任何数据）
-- 建议先把这一段单独执行一遍，确认库里状态符合预期再往下走。
-- ============================================================================

-- 1.1 该表是否已存在（已存在则应停止并人工检查，不要盲目往下执行）
SELECT TABLE_NAME AS `已存在的表`, TABLE_ROWS AS `约行数`, TABLE_COMMENT AS `注释`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_TYPE = 'BASE TABLE'
  AND TABLE_NAME = 'ai_dsh_instance';

-- 1.2 ai_user 现状（映射表要引用其中的 uuid / username）
SELECT COUNT(*) AS `用户总数`,
       SUM(CASE WHEN is_del = 0 THEN 1 ELSE 0 END) AS `未删除用户数`
FROM `ai_user`;

-- 1.3 现库全部表（判断有没有与本次新增同名的"意外表"）
SELECT TABLE_NAME AS `现有表`, TABLE_ROWS AS `约行数`
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;

-- ============================================================================
-- 第二步：建表
-- ============================================================================

CREATE TABLE IF NOT EXISTS `ai_dsh_instance` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户UUID（对应 ai_user.uuid）',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户名（冗余存放，供代理按用户名直接查询）',
  `container_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'dsh 容器名（dsh-new.sh 的 Name 参数）',
  `proxy_user` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '代理用户键（dsh-new.sh 的 ProxyUser 参数，决定 tokens.d 下的令牌文件名）',
  `host` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '127.0.0.1' COMMENT 'dsh 监听地址（容器 host 网络，默认仅本机）',
  `port` int NOT NULL COMMENT 'dsh 监听端口（dsh-new.sh 的 Port 参数）',
  `token_file` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '启动令牌文件路径，可为空；为空时由 proxy 按 TOKENS_DIR/proxy_user 推导',
  `status` int NOT NULL DEFAULT 1 COMMENT '状态（1：启用 0：停用；停用后 proxy 拒绝转发并给出明确提示）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '备注',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_user_uuid`(`user_uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_container_name`(`container_name` ASC) USING BTREE,
  UNIQUE INDEX `uk_proxy_user`(`proxy_user` ASC) USING BTREE,
  UNIQUE INDEX `uk_host_port`(`host` ASC, `port` ASC) USING BTREE,
  INDEX `idx_username`(`username` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户与 dsh 实例映射表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 第三步：后置校验 + 登记示例
-- ============================================================================

-- 3.1 表结构（列、类型、可空性、注释）
SELECT COLUMN_NAME AS `列名`, COLUMN_TYPE AS `类型`, IS_NULLABLE AS `可空`,
       COLUMN_DEFAULT AS `默认值`, COLUMN_COMMENT AS `注释`
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_dsh_instance'
ORDER BY ORDINAL_POSITION;

-- 3.2 索引（应看到 4 个唯一索引 uk_* 与 1 个普通索引 idx_username）
SELECT INDEX_NAME AS `索引名`, NON_UNIQUE AS `非唯一`, COLUMN_NAME AS `列名`, SEQ_IN_INDEX AS `列序`
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_dsh_instance'
ORDER BY INDEX_NAME, SEQ_IN_INDEX;

-- 3.3 现有映射（刚建表时应为空）
SELECT m.`id`, m.`username`, m.`container_name`, m.`proxy_user`,
       CONCAT(m.`host`, ':', m.`port`) AS `目标地址`, m.`status`, m.`remark`
FROM `ai_dsh_instance` m
ORDER BY m.`id`;

-- ----------------------------------------------------------------------------
-- 3.4 登记一条映射（模板，去掉注释按需改成真实值后再执行）
--
--   前提：先在服务器上把容器拉起来，端口与参数必须与下面完全一致：
--     ./dsh-new.sh <container_name> <port> <proxy_user>
--   例：
--     ./dsh-new.sh dsh-web-a 8083 a
--     ./dsh-new.sh dsh-web-demo 8083 demo
--
--   port 冲突说明：dsh-new.sh 会检查端口占用并直接退出，同一 host+port 也受
--   uk_host_port 唯一索引约束 —— 两处都在挡「两个用户抢同一个端口」。
-- ----------------------------------------------------------------------------
-- INSERT INTO `ai_dsh_instance`
--   (`user_uuid`, `username`, `container_name`, `proxy_user`, `host`, `port`,
--    `token_file`, `status`, `remark`, `create_time`, `create_by`)
-- SELECT u.`uuid`, u.`username`, 'dsh-web-demo', 'demo', '127.0.0.1', 8083,
--        NULL, 1, '初次登记', NOW(), 'manual'
-- FROM `ai_user` u
-- WHERE u.`username` = 'demo' AND u.`is_del` = 0;

-- ----------------------------------------------------------------------------
-- 3.5 常用运维语句
-- ----------------------------------------------------------------------------
-- 停用（proxy 会拒绝转发并提示"实例已停用"）：
--   UPDATE `ai_dsh_instance` SET `status` = 0, `update_time` = NOW(), `update_by` = 'manual'
--   WHERE `username` = 'demo';
--
-- 容器重建后端口/容器名变了，改映射（同时必须在服务器上执行
-- `./dsh-new.sh refresh <容器名> <proxy_user>` 刷新启动令牌，否则代理会一直 401）：
--   UPDATE `ai_dsh_instance`
--   SET `container_name` = 'dsh-web-demo2', `port` = 8090,
--       `update_time` = NOW(), `update_by` = 'manual'
--   WHERE `username` = 'demo';

-- ----------------------------------------------------------------------------
-- 3.6 一致性巡检：找出「映射指向的用户已不存在 / 已被删除」的脏数据
--      （这类行会让 proxy 把请求转发到一个不该存在的用户实例上）
-- ----------------------------------------------------------------------------
SELECT m.`id`, m.`username`, m.`user_uuid`, m.`container_name`, m.`status`,
       CASE WHEN u.`id` IS NULL THEN '用户不存在'
            WHEN u.`is_del` = 1 THEN '用户已软删除'
            ELSE 'OK' END AS `巡检结果`
FROM `ai_dsh_instance` m
LEFT JOIN `ai_user` u ON u.`uuid` = m.`user_uuid`
WHERE u.`id` IS NULL OR u.`is_del` = 1;

-- ----------------------------------------------------------------------------
-- 3.7 一致性巡检：端口重复/越界（正常应为 0 行；端口重复由唯一索引挡住，
--      这里兜的是历史数据或索引被误删的情况）
-- ----------------------------------------------------------------------------
SELECT `host`, `port`, COUNT(*) AS `占用数`, GROUP_CONCAT(`username`) AS `涉及用户`
FROM `ai_dsh_instance`
GROUP BY `host`, `port`
HAVING COUNT(*) > 1;

SELECT `id`, `username`, `port`
FROM `ai_dsh_instance`
WHERE `port` < 1 OR `port` > 65535;