/*
 Navicat Premium Dump SQL

 Source Server         : 192.168.1.203
 Source Server Type    : MySQL
 Source Server Version : 80300 (8.3.0)
 Source Host           : 192.168.1.203:3306
 Source Schema         : ai_service

 Target Server Type    : MySQL
 Target Server Version : 80300 (8.3.0)
 File Encoding         : 65001

 Date: 26/05/2026 15:34:06
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

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
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT = '密码历史记录表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
