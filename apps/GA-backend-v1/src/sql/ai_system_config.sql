SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

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
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '系统配置表' ROW_FORMAT = DYNAMIC;

-- 插入默认配置
INSERT INTO `ai_system_config` (`config_key`, `config_value`, `update_time`, `update_by`) VALUES
('score_threshold', '0.1', NOW(), 'admin'),
('top_k', '3', NOW(), 'admin');

SET FOREIGN_KEY_CHECKS = 1;