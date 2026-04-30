-- ============================================
-- 工业数据采集管理平台 - 数据库初始化脚本
-- ============================================

-- 创建TDengine数据库和超级表
-- 注意：需要在TDengine中执行

-- CREATE DATABASE iot_data KEEP 365 DAYS 10 BLOCKS 6 WAL_LEVEL 2;
-- USE iot_data;
--
-- CREATE STABLE sensor_data (
--     ts      TIMESTAMP,
--     value   DOUBLE,
--     quality INT
-- ) TAGS (
--     point_code  NCHAR(50),
--     item_code   NCHAR(50),
--     hierarchy   NCHAR(200),
--     unit        NCHAR(20)
-- );

-- ============================================
-- PostgreSQL 初始化数据
-- ============================================

-- 插入默认超级管理员（密码：Admin@123456）
-- 密码hash需要通过程序生成，这里只是占位
-- INSERT INTO users (username, password_hash, real_name, role, status)
-- VALUES ('admin', '$bcrypt$...', '系统管理员', 'superadmin', 'active');

-- 插入默认系统配置
INSERT INTO system_config (config_key, config_value, config_group, value_type, description) VALUES
('resume_enabled', 'true', 'data_receive', 'boolean', '断点续传功能开关'),
('resume_cache_hours', '24', 'data_receive', 'number', 'DTU本地最大缓存时长(小时)'),
('resume_retry_count', '3', 'data_receive', 'number', '补传失败重试次数'),
('resume_dedup_enabled', 'true', 'data_receive', 'boolean', '补传数据去重开关'),
('data_validation_enabled', 'true', 'data_processing', 'boolean', '数据校验功能开关'),
('data_clean_enabled', 'true', 'data_processing', 'boolean', '数据清洗(自动修正)开关'),
('data_raw_backup', 'false', 'data_processing', 'boolean', '是否保留原始数据'),
('heartbeat_enabled', 'true', 'device', 'boolean', '心跳检测功能开关'),
('heartbeat_interval', '60', 'device', 'number', '心跳发送间隔(秒)'),
('heartbeat_timeout', '180', 'device', 'number', '离线判定超时(秒)'),
('offline_alarm_enabled', 'true', 'alarm', 'boolean', '设备离线告警开关'),
('alarm_sound_enabled', 'true', 'alarm', 'boolean', '声音报警开关'),
('alarm_sms_enabled', 'false', 'alarm', 'boolean', '短信通知开关'),
('alarm_phone_enabled', 'false', 'alarm', 'boolean', '电话通知开关'),
('alarm_suppress_minutes', '5', 'alarm', 'number', '告警抑制时间窗口(分钟)'),
('alarm_escalation_enabled', 'true', 'alarm', 'boolean', '告警升级开关'),
('backup_enabled', 'true', 'backup', 'boolean', '自动备份开关'),
('backup_time', '02:00', 'backup', 'string', '每日备份时间'),
('backup_retain_days', '30', 'backup', 'number', '备份保留天数'),
('operation_log_enabled', 'true', 'log', 'boolean', '操作日志开关'),
('comm_log_enabled', 'false', 'log', 'boolean', '通讯日志开关'),
('system_log_level', 'info', 'log', 'string', '系统日志级别')
ON CONFLICT (config_key) DO NOTHING;

-- 插入默认协议模板（Modbus RTU）
INSERT INTO protocol_templates (template_name, description, protocol_type, frame_format, is_builtin) VALUES
('标准Modbus RTU', '标准Modbus RTU协议，支持功能码03/04读取保持/输入寄存器', 'modbus_rtu',
 '{
    "function_code": "03",
    "address_bytes": 1,
    "register_bytes": 2,
    "data_bytes": 2,
    "byte_order": "big_endian",
    "checksum_type": "crc16"
 }'::jsonb, true),
('自定义帧-采集终端', '适用于常见采集终端数据采集的自定义帧格式', 'custom_frame',
 '{
    "header": "AA 55",
    "length_type": "dynamic",
    "length_bytes": 2,
    "length_offset": 2,
    "address_bytes": 2,
    "data_fields": [
        {"name": "pressure", "offset": 6, "length": 2, "type": "uint16", "scale": 0.01, "unit": "MPa", "byte_order": "big_endian"},
        {"name": "temperature", "offset": 8, "length": 2, "type": "int16", "scale": 0.1, "unit": "℃", "byte_order": "big_endian"},
        {"name": "flow", "offset": 10, "length": 4, "type": "uint32", "scale": 0.001, "unit": "m³/h", "byte_order": "big_endian"}
    ],
    "checksum_type": "crc16",
    "checksum_offset": -2,
    "tail": "0D 0A"
 }'::jsonb, true)
ON CONFLICT DO NOTHING;
