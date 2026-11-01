/*
 Navicat Premium Dump SQL

 Source Server         : 172.16.235.50
 Source Server Type    : MySQL
 Source Server Version : 80040 (8.0.40)
 Source Host           : 172.16.235.50:3306
 Source Schema         : ai_service

 Target Server Type    : MySQL
 Target Server Version : 80040 (8.0.40)
 File Encoding         : 65001

 Date: 15/09/2026 14:46:44
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ai_agent
-- ----------------------------
DROP TABLE IF EXISTS `ai_agent`;
CREATE TABLE `ai_agent`  (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `config` json NULL COMMENT '智能体配置',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  `agent_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'ai_agent' COMMENT '智能体类型: ai_agent 或 deepagent',
  `visibility` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'private' COMMENT '可见性: private 或 public',
  `skills` json NULL COMMENT '技能列表',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '智能体助手管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_chat_record
-- ----------------------------
DROP TABLE IF EXISTS `ai_chat_record`;
CREATE TABLE `ai_chat_record`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `chat_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '对话类型: model / kb_chat / deepagent / agent / travel_planner',
  `user_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '用户ID，未提供为空串',
  `session_thread_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '会话线程ID',
  `agent_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '智能体UUID；model/travel_planner 类型为空串',
  `turn_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '会话轮次ID，同一轮次插入新记录时先软删除旧记录',
  `msg_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '消息类型: system / user / reasoning / tool_calls / response / todos',
  `messages` json NOT NULL COMMENT '单条消息内容，如 {\"user\":\"...\",\"time\":\"...\"} / {\"reasoning\":\"...\",\"time\":\"...\"} 等',
  `msg_time` datetime(3) NOT NULL COMMENT '消息事件时间（毫秒精度），用于排序还原对话时序',
  `is_del` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否软删除: 0-否 1-是',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  INDEX `idx_session_time`(`session_thread_id` ASC, `msg_time` ASC) USING BTREE,
  INDEX `idx_create_by_time`(`create_by` ASC, `msg_time` ASC) USING BTREE,
  INDEX `idx_create_time`(`create_time` ASC) USING BTREE,
  INDEX `idx_turn_id`(`turn_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '对话记录统一存储表（一行一条消息）' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_chat_session_summary
-- ----------------------------
DROP TABLE IF EXISTS `ai_chat_session_summary`;
CREATE TABLE `ai_chat_session_summary`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `session_thread_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '会话线程ID（唯一，一个会话一条摘要）',
  `summary` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '会话首个问题的摘要',
  `is_del` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否软删除: 0-否 1-是',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_session_thread_id`(`session_thread_id` ASC) USING BTREE,
  INDEX `idx_create_by_time`(`create_by` ASC, `create_time` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '会话摘要表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_kb_chat
-- ----------------------------
DROP TABLE IF EXISTS `ai_kb_chat`;
CREATE TABLE `ai_kb_chat`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '知识库名称',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  `visibility` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'private' COMMENT ': private  / public ',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 43 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '知识库管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_mcp_server
-- ----------------------------
DROP TABLE IF EXISTS `ai_mcp_server`;
CREATE TABLE `ai_mcp_server`  (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'MCP名称（唯一）',
  `description` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'MCP描述',
  `type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'MCP类型',
  `url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'MCP地址',
  `headers` json NULL COMMENT 'MCP请求头',
  `timeout` int NOT NULL COMMENT '超时时间',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  `visibility` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'private' COMMENT ': private  / public ',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_name`(`name` ASC) USING BTREE,
  INDEX `idx_type`(`type` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = 'MCP服务管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_models
-- ----------------------------
DROP TABLE IF EXISTS `ai_models`;
CREATE TABLE `ai_models`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `model_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '模型标识',
  `platform_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '模型服务编号（关联ai_platform.uuid）',
  `model_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '模型名称',
  `model_type` int NOT NULL COMMENT '模型类型',
  `context_size` int NULL DEFAULT NULL COMMENT '上下文大小（token数量）',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  INDEX `idx_platform`(`platform_id` ASC) USING BTREE,
  INDEX `idx_model_id`(`model_id` ASC) USING BTREE,
  CONSTRAINT `fk_models_platform` FOREIGN KEY (`platform_id`) REFERENCES `ai_platform` (`uuid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 332 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '模型管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_password_history
-- ----------------------------
DROP TABLE IF EXISTS `ai_password_history`;
CREATE TABLE `ai_password_history`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户UUID',
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '密码哈希值',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_user_uuid`(`user_uuid` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 6 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '密码历史记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_permissions
-- ----------------------------
DROP TABLE IF EXISTS `ai_permissions`;
CREATE TABLE `ai_permissions`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `group_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '群组编号（关联ai_user_group.uuid）',
  `entity_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '实体ID',
  `entity_type` int NOT NULL COMMENT '实体类型（0：mcp 1：platform 2：prompt 3：agent 4：kbchat）',
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '权限名称',
  `permission` int NOT NULL COMMENT '权限配置（0：无权限 1：只读 2：读写）',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  `score_threshold` float NULL DEFAULT 0.1 COMMENT '相似度阈值',
  `top_k` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  INDEX `idx_group`(`group_id` ASC) USING BTREE,
  INDEX `idx_entity`(`entity_id` ASC, `entity_type` ASC) USING BTREE,
  CONSTRAINT `fk_permission_group` FOREIGN KEY (`group_id`) REFERENCES `ai_user_group` (`uuid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 79 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户权限表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_physical_node
-- ----------------------------
DROP TABLE IF EXISTS `ai_physical_node`;
CREATE TABLE `ai_physical_node`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '物理节点名称',
  `node_ip` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '物理节点IP',
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户名',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '密码',
  `port` int NULL DEFAULT 22 COMMENT 'SSH端口',
  `timeout` int NULL DEFAULT 60 COMMENT 'SSH超时时间(秒)',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '物理节点配置表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_platform
-- ----------------------------
DROP TABLE IF EXISTS `ai_platform`;
CREATE TABLE `ai_platform`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '模型平台名称',
  `api_key` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '模型平台密钥',
  `no_api_key_required` int NOT NULL COMMENT '是否需要平台密钥（0：否 1：是）',
  `api_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '模型平台地址',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  `visibility` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'private' COMMENT ': private  / public ',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  INDEX `idx_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 64 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '模型平台管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_prompt
-- ----------------------------
DROP TABLE IF EXISTS `ai_prompt`;
CREATE TABLE `ai_prompt`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `text` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '提示词内容',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  `visibility` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'private' COMMENT ': private  / public ',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  FULLTEXT INDEX `ft_text`(`text`) COMMENT '提示词全文索引'
) ENGINE = InnoDB AUTO_INCREMENT = 14 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '提示词表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_skill
-- ----------------------------
DROP TABLE IF EXISTS `ai_skill`;
CREATE TABLE `ai_skill`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '技能名称',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '技能描述',
  `folder_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件夹名称',
  `visibility` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'private' COMMENT '可见性: private 或 public',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `additional_info` json NULL COMMENT '扩展字段',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uq_skill_folder_name_create_by`(`folder_name` ASC, `create_by` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 186 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = 'AI技能管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_system_config
-- ----------------------------
DROP TABLE IF EXISTS `ai_system_config`;
CREATE TABLE `ai_system_config`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '配置键',
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '配置值',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_config_key`(`config_key` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '系统配置表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_thinking_chain
-- ----------------------------
DROP TABLE IF EXISTS `ai_thinking_chain`;
CREATE TABLE `ai_thinking_chain`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `model_config` json NOT NULL COMMENT '模型配置(JSON)',
  `ontology_config` json NOT NULL COMMENT '本体配置(JSON)',
  `chain_of_decision_config` json NOT NULL COMMENT '决策链配置(JSON)',
  `tool_list` json NOT NULL COMMENT '工具列表(JSON)',
  `big_model_config` json NOT NULL COMMENT '大模型配置(JSON)',
  `prompt` json NOT NULL COMMENT '提示词(JSON)',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '思维链配置表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_user
-- ----------------------------
DROP TABLE IF EXISTS `ai_user`;
CREATE TABLE `ai_user`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户名',
  `realname` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '真实姓名',
  `contact` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '联系方式',
  `address` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '家庭住址',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '密码',
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '邮箱',
  `additional_info` json NULL COMMENT '扩展字段',
  `platform_sort` json NULL COMMENT '模型平台排序',
  `preferences` json NULL COMMENT '用户偏好',
  `is_del` int NOT NULL DEFAULT 0 COMMENT '是否逻辑删除（0：否 1：是）',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_username`(`username` ASC) USING BTREE,
  INDEX `idx_realname`(`realname` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 38 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_user_feedback
-- ----------------------------
DROP TABLE IF EXISTS `ai_user_feedback`;
CREATE TABLE `ai_user_feedback`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID（即追溯表中的序号）',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `feedback_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户反馈内容',
  `priority` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '需求优先级（高/中/低）',
  `improvement_plan` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '改进措施/解决方案',
  `source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '需求来源',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '当前进度状态（需求确认/开发中/已上线 等）',
  `progress` decimal(3, 2) NULL DEFAULT 0.00 COMMENT '完成进度（0.00 ~ 1.00）',
  `finish_time` datetime NULL DEFAULT NULL COMMENT '完成时间',
  `verify_result` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '验证结果/用户反馈',
  `remark` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '备注',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  `is_del` int NOT NULL DEFAULT 0 COMMENT '是否删除（0：未删除 1：已删除）',
  `start_time` datetime NULL DEFAULT NULL COMMENT '需求提出时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  INDEX `idx_priority`(`priority` ASC) USING BTREE,
  INDEX `idx_status`(`status` ASC) USING BTREE,
  INDEX `idx_source`(`source` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 30 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户反馈与功能改进追溯表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_user_group
-- ----------------------------
DROP TABLE IF EXISTS `ai_user_group`;
CREATE TABLE `ai_user_group`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '群组名称',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 10 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户群组表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for ai_user_group_relation
-- ----------------------------
DROP TABLE IF EXISTS `ai_user_group_relation`;
CREATE TABLE `ai_user_group_relation`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `user_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户ID（关联ai_user.uuid）',
  `group_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '群组ID（关联ai_user_group.uuid）',
  `additional_info` json NULL COMMENT '扩展字段',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `update_time` datetime NOT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '更新人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_user_group`(`user_id` ASC, `group_id` ASC) USING BTREE COMMENT '用户-群组唯一关联',
  INDEX `idx_user`(`user_id` ASC) USING BTREE,
  INDEX `idx_group`(`group_id` ASC) USING BTREE,
  CONSTRAINT `fk_relation_group` FOREIGN KEY (`group_id`) REFERENCES `ai_user_group` (`uuid`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_relation_user` FOREIGN KEY (`user_id`) REFERENCES `ai_user` (`uuid`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 18 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户群组关联表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- View structure for v_daily_attendance_trend
-- ----------------------------
DROP VIEW IF EXISTS `v_daily_attendance_trend`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `v_daily_attendance_trend` AS select `attendance_summary`.`stat_date` AS `stat_date`,count(distinct `attendance_summary`.`employee_id`) AS `total_employees`,sum(`attendance_summary`.`late_count`) AS `total_late`,sum(`attendance_summary`.`early_count`) AS `total_early`,sum(`attendance_summary`.`missing_count`) AS `total_missing`,count(distinct (case when (`attendance_summary`.`late_count` > 0) then `attendance_summary`.`employee_id` end)) AS `late_employees`,count(distinct (case when (`attendance_summary`.`early_count` > 0) then `attendance_summary`.`employee_id` end)) AS `early_employees`,count(distinct (case when (`attendance_summary`.`missing_count` > 0) then `attendance_summary`.`employee_id` end)) AS `missing_employees` from `attendance_summary` group by `attendance_summary`.`stat_date`;

-- ----------------------------
-- View structure for v_employee_attendance_ranking
-- ----------------------------
DROP VIEW IF EXISTS `v_employee_attendance_ranking`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `v_employee_attendance_ranking` AS select `attendance_monthly`.`employee_id` AS `employee_id`,`attendance_monthly`.`employee_name` AS `employee_name`,`attendance_monthly`.`department` AS `department`,`attendance_monthly`.`stat_year` AS `stat_year`,`attendance_monthly`.`stat_month` AS `stat_month`,`attendance_monthly`.`late_count` AS `late_count`,`attendance_monthly`.`early_count` AS `early_count`,`attendance_monthly`.`missing_count` AS `missing_count`,((`attendance_monthly`.`late_count` + `attendance_monthly`.`early_count`) + `attendance_monthly`.`missing_count`) AS `total_exceptions` from `attendance_monthly`;

-- ----------------------------
-- View structure for v_monthly_attendance_stats
-- ----------------------------
DROP VIEW IF EXISTS `v_monthly_attendance_stats`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `v_monthly_attendance_stats` AS select `a`.`stat_year` AS `stat_year`,`a`.`stat_month` AS `stat_month`,`a`.`department` AS `department`,count(distinct `a`.`employee_id`) AS `employee_count`,sum(`a`.`late_count`) AS `total_late_count`,sum(`a`.`early_count`) AS `total_early_count`,sum(`a`.`missing_count`) AS `total_missing_count`,sum(`a`.`leave_hours`) AS `total_leave_hours`,sum(`a`.`overtime_days`) AS `total_overtime_days`,count(distinct (case when (`a`.`late_count` > 0) then `a`.`employee_id` end)) AS `late_employee_count`,count(distinct (case when (`a`.`early_count` > 0) then `a`.`employee_id` end)) AS `early_employee_count`,count(distinct (case when (`a`.`missing_count` > 0) then `a`.`employee_id` end)) AS `missing_employee_count` from `attendance_monthly` `a` group by `a`.`stat_year`,`a`.`stat_month`,`a`.`department`;

-- ----------------------------
-- Procedure structure for sp_cleanup_etl_logs
-- ----------------------------
DROP PROCEDURE IF EXISTS `sp_cleanup_etl_logs`;
delimiter ;;
CREATE PROCEDURE `sp_cleanup_etl_logs`(IN p_retention_days INT)
BEGIN
    DELETE FROM `etl_job_log`
    WHERE `start_time` < DATE_SUB(NOW(), INTERVAL p_retention_days DAY);
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for sp_generate_monthly_attendance
-- ----------------------------
DROP PROCEDURE IF EXISTS `sp_generate_monthly_attendance`;
delimiter ;;
CREATE PROCEDURE `sp_generate_monthly_attendance`(IN p_year SMALLINT,
    IN p_month TINYINT)
BEGIN
    INSERT INTO `attendance_monthly` (
        `employee_id`, `employee_name`, `department`,
        `stat_year`, `stat_month`,
        `total_work_days`, `actual_work_days`,
        `late_count`, `early_count`, `missing_count`,
        `leave_hours`, `overtime_days`
    )
    SELECT
        `employee_id`,
        `employee_name`,
        `department`,
        YEAR(`stat_date`) AS `stat_year`,
        MONTH(`stat_date`) AS `stat_month`,
        COUNT(DISTINCT CASE WHEN `status` != 'absent' THEN `stat_date` END) AS `total_work_days`,
        COUNT(DISTINCT CASE WHEN `late_count` > 0 OR `early_count` > 0 OR `actual_work_days` > 0 THEN `stat_date` END) AS `actual_work_days`,
        SUM(`late_count`) AS `late_count`,
        SUM(`early_count`) AS `early_count`,
        SUM(`missing_count`) AS `missing_count`,
        SUM(`leave_hours`) AS `leave_hours`,
        SUM(`overtime_days`) AS `overtime_days`
    FROM `attendance_summary`
    WHERE YEAR(`stat_date`) = p_year AND MONTH(`stat_date`) = p_month
    GROUP BY `employee_id`, `employee_name`, `department`, YEAR(`stat_date`), MONTH(`stat_date`)
    ON DUPLICATE KEY UPDATE
        `total_work_days` = VALUES(`total_work_days`),
        `actual_work_days` = VALUES(`actual_work_days`),
        `late_count` = VALUES(`late_count`),
        `early_count` = VALUES(`early_count`),
        `missing_count` = VALUES(`missing_count`),
        `leave_hours` = VALUES(`leave_hours`),
        `overtime_days` = VALUES(`overtime_days`),
        `updated_at` = CURRENT_TIMESTAMP;
END
;;
delimiter ;

SET FOREIGN_KEY_CHECKS = 1;
