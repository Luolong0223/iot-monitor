"""数据校验与清洗引擎

支持校验类型:
- 范围检查 (min/max)
- 突变检测 (滑动窗口 + 标准差)
- 连续零值检测
- 连续重复值检测
- 空值检测
- 时间戳校验
"""
import logging
import math
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger("industrial-monitor")


class ValidationResult:
    """校验结果"""

    def __init__(self):
        self.is_valid = True
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.cleaned_value: Any = None

    def add_error(self, msg: str):
        self.is_valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "warnings": self.warnings,
            "errors": self.errors,
            "cleaned_value": self.cleaned_value,
        }


class DataValidator:
    """数据校验器"""

    def __init__(self):
        # 滑动窗口缓存: {item_id: deque([values...])}
        self._value_windows: Dict[int, deque] = {}
        # 连续零值计数: {item_id: count}
        self._zero_counts: Dict[int, int] = {}
        # 连续重复值计数: {item_id: (last_value, count)}
        self._dup_state: Dict[int, tuple] = {}

    def validate(
        self,
        item_id: int,
        value: Any,
        config: dict,
        timestamp: Optional[datetime] = None,
    ) -> ValidationResult:
        """
        校验单个数据项

        Args:
            item_id: 数据项ID
            value: 数据值
            config: 校验配置
                - data_type: str
                - min_value: float (可选)
                - max_value: float (可选)
                - validation_enabled: bool
                - jump_threshold: float (可选, 突变阈值)
                - jump_window_size: int (默认10)
                - zero_count_limit: int (默认5)
                - dup_count_limit: int (默认10)
            timestamp: 数据时间戳 (可选)

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not config.get("validation_enabled", True):
            result.cleaned_value = value
            return result

        # 1. 空值检测
        if self._check_null(value, result):
            return result

        # 转换为数值
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            result.add_error(f"无法转换为数值: {value}")
            return result

        # 2. 时间戳校验
        if timestamp:
            self._check_timestamp(timestamp, result)

        # 3. 范围检查
        min_val = config.get("min_value")
        max_val = config.get("max_value")
        self._check_range(numeric_value, min_val, max_val, result)

        # 4. 突变检测
        jump_threshold = config.get("jump_threshold")
        if jump_threshold is not None:
            window_size = config.get("jump_window_size", 10)
            self._check_sudden_change(item_id, numeric_value, jump_threshold, window_size, result)

        # 5. 连续零值检测
        zero_limit = config.get("zero_count_limit", 5)
        self._check_consecutive_zeros(item_id, numeric_value, zero_limit, result)

        # 6. 连续重复值检测
        dup_limit = config.get("dup_count_limit", 10)
        self._check_consecutive_duplicates(item_id, numeric_value, dup_limit, result)

        result.cleaned_value = numeric_value
        return result

    def _check_null(self, value: Any, result: ValidationResult) -> bool:
        """空值检测"""
        if value is None:
            result.add_error("数据为空")
            return True
        if isinstance(value, str) and value.strip() == "":
            result.add_error("数据为空字符串")
            return True
        return False

    def _check_timestamp(self, timestamp: datetime, result: ValidationResult):
        """时间戳校验"""
        now = datetime.now(timezone.utc)

        # 时间戳是否在未来
        if timestamp > now:
            result.add_warning("时间戳在未来")

        # 时间戳是否过于久远 (>24小时前)
        delta = now - timestamp
        if delta.total_seconds() > 86400:
            result.add_warning(f"时间戳过旧: {delta.days}天前")

    def _check_range(self, value: float, min_val: Optional[float], max_val: Optional[float], result: ValidationResult):
        """范围检查"""
        if min_val is not None and value < min_val:
            result.add_warning(f"值 {value} 低于量程下限 {min_val}")
        if max_val is not None and value > max_val:
            result.add_warning(f"值 {value} 超过量程上限 {max_val}")

    def _check_sudden_change(
        self, item_id: int, value: float, threshold: float, window_size: int, result: ValidationResult
    ):
        """突变检测: 滑动窗口标准差法"""
        if item_id not in self._value_windows:
            self._value_windows[item_id] = deque(maxlen=window_size)

        window = self._value_windows[item_id]

        if len(window) >= 3:
            # 计算窗口均值和标准差
            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / len(window)
            std = math.sqrt(variance) if variance > 0 else 0

            # 与阈值比较
            if std > 0 and abs(value - mean) > threshold * std:
                result.add_warning(
                    f"突变检测: 当前值 {value}, 窗口均值 {mean:.2f}, "
                    f"标准差 {std:.2f}, 偏移 {abs(value - mean):.2f}"
                )

        window.append(value)

    def _check_consecutive_zeros(self, item_id: int, value: float, limit: int, result: ValidationResult):
        """连续零值检测"""
        if abs(value) < 1e-10:
            self._zero_counts[item_id] = self._zero_counts.get(item_id, 0) + 1
            count = self._zero_counts[item_id]
            if count >= limit:
                result.add_warning(f"连续 {count} 个零值 (阈值: {limit})")
        else:
            self._zero_counts[item_id] = 0

    def _check_consecutive_duplicates(self, item_id: int, value: float, limit: int, result: ValidationResult):
        """连续重复值检测"""
        state = self._dup_state.get(item_id)
        if state and abs(state[0] - value) < 1e-10:
            count = state[1] + 1
            self._dup_state[item_id] = (value, count)
            if count >= limit:
                result.add_warning(f"连续 {count} 个相同值 {value} (阈值: {limit})")
        else:
            self._dup_state[item_id] = (value, 1)

    def reset(self, item_id: int):
        """重置某个数据项的状态"""
        self._value_windows.pop(item_id, None)
        self._zero_counts.pop(item_id, None)
        self._dup_state.pop(item_id, None)

    def reset_all(self):
        """重置所有状态"""
        self._value_windows.clear()
        self._zero_counts.clear()
        self._dup_state.clear()


# 全局单例
_validator_instance: Optional[DataValidator] = None


def get_validator() -> DataValidator:
    """获取全局校验器实例"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DataValidator()
    return _validator_instance


def validate_data_item(item_id: int, value: Any, config: dict, timestamp: Optional[datetime] = None) -> dict:
    """便捷函数：校验数据项"""
    validator = get_validator()
    result = validator.validate(item_id, value, config, timestamp)
    return result.to_dict()
