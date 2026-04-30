"""TDengine 服务

TDengine 连接管理、数据写入和查询。
使用 taosrest 连接 TDengine REST API。
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("industrial-monitor.tdengine")

# 尝试导入 taosrest
try:
    import taosrest
    HAS_TAOSREST = True
except ImportError:
    HAS_TAOSREST = False
    logger.warning("taosrest 未安装，TDengine功能不可用")


class TDengineService:
    """TDengine 服务"""

    def __init__(self):
        self._conn = None
        self._db_name = settings.TDENGINE_DB
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self):
        """建立连接"""
        if not HAS_TAOSREST:
            logger.error("taosrest 未安装，无法连接 TDengine")
            return

        try:
            self._conn = taosrest.connect(
                url=f"http://{settings.TDENGINE_HOST}:{settings.TDENGINE_PORT}",
            )
            self._init_database()
            self._connected = True
            logger.info(f"TDengine 连接成功: {settings.TDENGINE_HOST}:{settings.TDENGINE_PORT}")
        except Exception as e:
            logger.error(f"TDengine 连接失败: {e}")
            self._connected = False

    def close(self):
        """关闭连接"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._connected = False
            logger.info("TDengine 连接已关闭")

    def _init_database(self):
        """初始化数据库"""
        cursor = self._conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {self._db_name} "
            f"KEEP {settings.TDENGINE_KEEP_DAYS} "
            f"DURATION 30 "
            f"BUFFER 16 "
            f"WAL_LEVEL 1 "
            f"PRECISION 'ms'"
        )
        cursor.execute(f"USE {self._db_name}")

        # 创建超级表
        cursor.execute("""
            CREATE STABLE IF NOT EXISTS sensor_data (
                ts TIMESTAMP,
                value DOUBLE,
                quality INT,
                raw_value DOUBLE
            ) TAGS (
                point_id INT,
                item_id INT,
                item_code BINARY(64),
                point_code BINARY(64)
            )
        """)
        cursor.close()

    def _sanitize_tag(value: str) -> str:
        """清理 TAG 值，防止 SQL 注入"""
        return value.replace("'", "\\'").replace("\\", "\\\\")[:64]

    def ensure_sub_table(self, point_id: int, item_id: int, item_code: str, point_code: str):
        """确保子表存在"""
        table_name = f"d_{point_id}_{item_id}"
        safe_code = self._sanitize_tag(item_code)
        safe_point = self._sanitize_tag(point_code)
        try:
            cursor = self._conn.cursor()
            cursor.execute(f"USE {self._db_name}")
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} USING sensor_data "
                f"TAGS ({point_id}, {item_id}, '{safe_code}', '{safe_point}')"
            )
            cursor.close()
        except Exception as e:
            logger.error(f"创建子表失败 {table_name}: {e}")

    def insert_data(
        self,
        point_id: int,
        item_id: int,
        item_code: str,
        point_code: str,
        value: float,
        timestamp: Optional[datetime] = None,
        quality: int = 0,
        raw_value: Optional[float] = None,
    ):
        """插入传感器数据"""
        if not self._connected:
            logger.warning("TDengine 未连接，跳过数据写入")
            return

        table_name = f"d_{point_id}_{item_id}"
        ts = timestamp or datetime.now(timezone.utc)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        raw = raw_value if raw_value is not None else value

        try:
            cursor = self._conn.cursor()
            cursor.execute(f"USE {self._db_name}")
            # 确保子表存在
            self.ensure_sub_table(point_id, item_id, item_code, point_code)
            cursor.execute(
                f"INSERT INTO {table_name} VALUES "
                f"('{ts_str}', {value}, {quality}, {raw})"
            )
            cursor.close()
        except Exception as e:
            logger.error(f"数据写入失败 {table_name}: {e}")

    def batch_insert(self, records: List[dict]):
        """批量插入数据"""
        if not self._connected or not records:
            return

        # 按子表分组
        table_data: Dict[str, List[str]] = {}
        for rec in records:
            table_name = f"d_{rec['point_id']}_{rec['item_id']}"
            ts = rec.get("timestamp", datetime.now(timezone.utc))
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            value = rec["value"]
            quality = rec.get("quality", 0)
            raw = rec.get("raw_value", value)

            if table_name not in table_data:
                table_data[table_name] = []
            table_data[table_name].append(f"('{ts_str}', {value}, {quality}, {raw})")

            # 确保子表
            self.ensure_sub_table(
                rec["point_id"], rec["item_id"],
                rec.get("item_code", ""), rec.get("point_code", ""),
            )

        try:
            cursor = self._conn.cursor()
            cursor.execute(f"USE {self._db_name}")
            for table_name, values_list in table_data.items():
                sql = f"INSERT INTO {table_name} VALUES " + ", ".join(values_list)
                cursor.execute(sql)
            cursor.close()
            logger.debug(f"批量写入 {len(records)} 条数据")
        except Exception as e:
            logger.error(f"批量写入失败: {e}")

    def query_latest(self, point_id: int, item_id: int) -> Optional[dict]:
        """查询最新值"""
        if not self._connected:
            return None

        table_name = f"d_{point_id}_{item_id}"
        try:
            cursor = self._conn.cursor()
            cursor.execute(f"USE {self._db_name}")
            cursor.execute(
                f"SELECT LAST(ts, value, quality) FROM {table_name}"
            )
            row = cursor.fetchone()
            cursor.close()

            if row and row[0]:
                return {
                    "timestamp": str(row[0]),
                    "value": float(row[1]) if row[1] is not None else None,
                    "quality": int(row[2]) if row[2] is not None else 0,
                }
            return None
        except Exception as e:
            logger.debug(f"查询最新值失败 {table_name}: {e}")
            return None

    def query_latest_batch(self, item_ids: List[dict]) -> List[dict]:
        """批量查询最新值"""
        results = []
        for item_info in item_ids:
            point_id = item_info["point_id"]
            item_id = item_info["item_id"]
            latest = self.query_latest(point_id, item_id)
            results.append({
                "point_id": point_id,
                "item_id": item_id,
                "item_code": item_info.get("item_code", ""),
                "item_name": item_info.get("item_name", ""),
                "unit": item_info.get("unit", ""),
                **(latest or {}),
            })
        return results

    def query_history(
        self,
        point_id: int,
        item_id: int,
        start_time: datetime,
        end_time: datetime,
        aggregation: Optional[str] = None,
        interval: Optional[str] = None,
        limit: int = 10000,
    ) -> List[dict]:
        """查询历史数据"""
        if not self._connected:
            return []

        table_name = f"d_{point_id}_{item_id}"
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor = self._conn.cursor()
            cursor.execute(f"USE {self._db_name}")

            if aggregation and interval:
                # 聚合查询
                agg_func = aggregation.upper()
                if agg_func not in ("AVG", "MAX", "MIN", "SUM", "COUNT", "FIRST", "LAST", "SPREAD"):
                    raise ValueError(f"不支持的聚合函数: {aggregation}")

                sql = (
                    f"SELECT _wstart AS ts, {agg_func}(value) AS value "
                    f"FROM {table_name} "
                    f"WHERE ts >= '{start_str}' AND ts <= '{end_str}' "
                    f"INTERVAL({interval}) "
                    f"LIMIT {limit}"
                )
            else:
                # 原始数据查询
                sql = (
                    f"SELECT ts, value, quality FROM {table_name} "
                    f"WHERE ts >= '{start_str}' AND ts <= '{end_str}' "
                    f"ORDER BY ts DESC "
                    f"LIMIT {limit}"
                )

            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                item = {}
                for col_name, val in zip(columns, row):
                    if col_name == "ts":
                        item["timestamp"] = str(val)
                    elif col_name == "value":
                        item["value"] = float(val) if val is not None else None
                    elif col_name == "quality":
                        item["quality"] = int(val) if val is not None else 0
                    else:
                        item[col_name] = val
                results.append(item)

            return results
        except Exception as e:
            logger.error(f"历史数据查询失败 {table_name}: {e}")
            return []

    def query_statistics(
        self,
        point_id: int,
        item_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[dict]:
        """查询统计数据 (avg/max/min/count)"""
        if not self._connected:
            return None

        table_name = f"d_{point_id}_{item_id}"
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor = self._conn.cursor()
            cursor.execute(f"USE {self._db_name}")
            cursor.execute(
                f"SELECT AVG(value), MAX(value), MIN(value), COUNT(value), "
                f"FIRST(value), LAST(value) "
                f"FROM {table_name} "
                f"WHERE ts >= '{start_str}' AND ts <= '{end_str}'"
            )
            row = cursor.fetchone()
            cursor.close()

            if row:
                return {
                    "avg": round(float(row[0]), 4) if row[0] is not None else None,
                    "max": round(float(row[1]), 4) if row[1] is not None else None,
                    "min": round(float(row[2]), 4) if row[2] is not None else None,
                    "count": int(row[3]) if row[3] is not None else 0,
                    "first": round(float(row[4]), 4) if row[4] is not None else None,
                    "last": round(float(row[5]), 4) if row[5] is not None else None,
                }
            return None
        except Exception as e:
            logger.error(f"统计查询失败 {table_name}: {e}")
            return None

    def export_data(
        self,
        point_id: int,
        item_id: int,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100000,
    ) -> List[dict]:
        """导出数据"""
        return self.query_history(
            point_id, item_id, start_time, end_time,
            aggregation=None, interval=None, limit=limit,
        )

    def cleanup_old_data(self, days: Optional[int] = None):
        """清理过期数据 (TDengine 自动通过 KEEP 参数管理，此方法用于手动触发)"""
        keep_days = days or settings.TDENGINE_KEEP_DAYS
        logger.info(f"TDengine 数据保留天数: {keep_days} (由 KEEP 参数自动管理)")


# 全局单例
_tdengine_service: Optional[TDengineService] = None


def get_tdengine_service() -> TDengineService:
    """获取 TDengine 服务实例"""
    global _tdengine_service
    if _tdengine_service is None:
        _tdengine_service = TDengineService()
    return _tdengine_service
