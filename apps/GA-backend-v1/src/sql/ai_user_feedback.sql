/*
 Source Server Type    : MySQL
 Source Server Version : 80300 (8.3.0)
 Target Schema         : ai_service
 File Encoding         : 65001

 表说明：用户反馈与功能改进追溯表
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ai_user_feedback
-- ----------------------------
DROP TABLE IF EXISTS `ai_user_feedback`;
CREATE TABLE `ai_user_feedback`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID（即追溯表中的序号）',
  `uuid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '唯一ID',
  `feedback_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户反馈内容',
  `priority` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '需求优先级（高/中/低）',
  `improvement_plan` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '改进措施/解决方案',
  `source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '需求来源',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '当前进度状态（需求确认/开发中/已上线 等）',
  `progress` decimal(3, 2) NULL DEFAULT 0.00 COMMENT '完成进度（0.00 ~ 1.00）',
  `start_time` datetime NULL DEFAULT NULL COMMENT '需求提出时间',
  `finish_time` datetime NULL DEFAULT NULL COMMENT '完成时间',
  `verify_result` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '验证结果/用户反馈',
  `remark` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '备注',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  `is_del` int NOT NULL DEFAULT 0 COMMENT '是否删除（0：未删除 1：已删除）',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_uuid`(`uuid` ASC) USING BTREE,
  INDEX `idx_priority`(`priority` ASC) USING BTREE,
  INDEX `idx_status`(`status` ASC) USING BTREE,
  INDEX `idx_source`(`source` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户反馈与功能改进追溯表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
