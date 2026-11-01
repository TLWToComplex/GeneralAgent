-- GeneralAgent V2 · 用户登录相关表结构（全新部署用）
-- 列定义、索引、注释均取自老项目 src/sql/ai_user.sql 与 src/sql/ai_password_history.sql，
-- 以保证 V2 可以复用既有 ai_user 数据（密码为 Werkzeug 哈希，V2 使用同一算法校验）。
-- 与老项目 dump 的唯一差别：改为 CREATE TABLE IF NOT EXISTS，避免误删线上数据。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 用户管理表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `ai_user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户名',
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `realname` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '真实姓名',
  `contact` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '联系方式',
  `address` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '家庭住址',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '密码',
  `additional_info` json NULL COMMENT '扩展字段',
  `platform_sort` json NULL COMMENT '模型平台排序',
  `preferences` json NULL COMMENT '用户偏好',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  `is_del` int NOT NULL DEFAULT 0 COMMENT '是否删除（0：未删除 1：已删除）',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  UNIQUE INDEX `uk_username`(`username` ASC) USING BTREE,
  INDEX `idx_realname`(`realname` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户管理表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- 密码历史记录表（禁止复用近 5 次历史密码）
-- ----------------------------
CREATE TABLE IF NOT EXISTS `ai_password_history` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户UUID',
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '密码哈希值',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_user_uuid`(`user_uuid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '密码历史记录表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;