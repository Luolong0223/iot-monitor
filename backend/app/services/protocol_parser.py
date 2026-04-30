"""协议解析引擎

支持解析类型:
- fixed_offset: 固定偏移量解析
- modbus_rtu: Modbus RTU协议
- modbus_tcp: Modbus TCP协议
- custom_frame: 自定义帧格式
- json: JSON格式数据
- csv: CSV格式数据
"""
import json
import struct
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("industrial-monitor")


class ProtocolParser:
    """协议解析器"""

    def parse(self, protocol_type: str, frame_format: dict, hex_data: str) -> dict:
        """
        解析入口

        Args:
            protocol_type: 协议类型
            frame_format: 帧格式配置JSON
            hex_data: 十六进制字符串报文

        Returns:
            解析结果字典
        """
        raw_hex_clean = hex_data.replace(" ", "").replace("\n", "")
        # 校验十六进制字符串
        if not raw_hex_clean or len(raw_hex_clean) % 2 != 0:
            raise ValueError(f"无效的十六进制数据: 长度 {len(raw_hex_clean)}")
        try:
            raw_bytes = bytes.fromhex(raw_hex_clean)
        except ValueError:
            raise ValueError(f"十六进制数据包含非法字符: {raw_hex_clean[:50]}...")

        dispatch = {
            "fixed_offset": self._parse_fixed_offset,
            "modbus_rtu": self._parse_modbus_rtu,
            "modbus_tcp": self._parse_modbus_tcp,
            "custom_frame": self._parse_custom_frame,
            "json": self._parse_json,
            "csv": self._parse_csv,
        }

        parser_fn = dispatch.get(protocol_type)
        if not parser_fn:
            raise ValueError(f"不支持的协议类型: {protocol_type}")

        return parser_fn(frame_format, raw_bytes, hex_data)

    # ============ CRC 校验 ============

    @staticmethod
    def crc16(data: bytes) -> int:
        """CRC16/Modbus 校验"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    @staticmethod
    def crc32(data: bytes) -> int:
        """CRC32 校验"""
        import binascii
        return binascii.crc32(data) & 0xFFFFFFFF

    # ============ 字节序转换 ============

    @staticmethod
    def bytes_to_value(data: bytes, data_type: str, byte_order: str = "big_endian") -> Any:
        """字节数据转换为数值"""
        if byte_order == "little_endian":
            data = data[::-1]

        type_map = {
            "int8": ("b", 1),
            "uint8": ("B", 1),
            "int16": (">h", 2),
            "uint16": (">H", 2),
            "int32": (">i", 4),
            "uint32": (">I", 4),
            "float32": (">f", 4),
            "float64": (">d", 8),
        }

        fmt_info = type_map.get(data_type)
        if not fmt_info:
            raise ValueError(f"不支持的数据类型: {data_type}")

        fmt, size = fmt_info
        if len(data) < size:
            raise ValueError(f"数据长度不足: 需要 {size} 字节，实际 {len(data)} 字节")

        return struct.unpack(fmt, data[:size])[0]

    # ============ 数据转换 ============

    @staticmethod
    def apply_conversion(value: float, scale: float = 1.0, offset: float = 0.0) -> float:
        """应用换算: value * scale + offset"""
        return value * scale + offset

    # ============ fixed_offset 解析 ============

    def _parse_fixed_offset(self, frame_format: dict, raw_bytes: bytes, hex_data: str) -> dict:
        """
        固定偏移量解析

        frame_format 示例:
        {
            "items": [
                {
                    "name": "methane",
                    "offset": 0,
                    "length": 2,
                    "data_type": "uint16",
                    "byte_order": "big_endian",
                    "scale": 0.1,
                    "offset_value": 0
                }
            ],
            "checksum": {"type": "crc16", "offset": -2}
        }
        """
        items_config = frame_format.get("items", [])
        checksum_config = frame_format.get("checksum")

        # 校验
        if checksum_config:
            self._verify_checksum(raw_bytes, checksum_config)

        values = {}
        for item_conf in items_config:
            name = item_conf["name"]
            offset = item_conf["offset"]
            length = item_conf.get("length", 2)
            data_type = item_conf.get("data_type", "uint16")
            byte_order = item_conf.get("byte_order", "big_endian")
            scale = item_conf.get("scale", 1.0)
            offset_value = item_conf.get("offset_value", 0.0)

            if offset + length > len(raw_bytes):
                raise ValueError(f"数据项 '{name}' 偏移越界: offset={offset}, length={length}, frame_len={len(raw_bytes)}")

            raw_val = self.bytes_to_value(raw_bytes[offset:offset + length], data_type, byte_order)
            converted = self.apply_conversion(float(raw_val), scale, offset_value)
            values[name] = round(converted, 6)

        return {
            "protocol_type": "fixed_offset",
            "raw_hex": hex_data,
            "frame_length": len(raw_bytes),
            "values": values,
            "checksum_valid": True if checksum_config else None,
        }

    # ============ modbus_rtu 解析 ============

    def _parse_modbus_rtu(self, frame_format: dict, raw_bytes: bytes, hex_data: str) -> dict:
        """
        Modbus RTU 解析

        frame_format 示例:
        {
            "slave_id": 1,
            "function_code": 3,
            "registers": [
                {
                    "name": "methane",
                    "address": 0,
                    "count": 1,
                    "data_type": "uint16",
                    "scale": 0.1,
                    "offset_value": 0
                }
            ]
        }
        """
        if len(raw_bytes) < 5:
            raise ValueError("Modbus RTU 帧长度不足")

        # CRC校验 (最后两字节)
        data_part = raw_bytes[:-2]
        received_crc = struct.unpack("<H", raw_bytes[-2:])[0]
        calculated_crc = self.crc16(data_part)
        crc_valid = received_crc == calculated_crc

        slave_id = raw_bytes[0]
        function_code = raw_bytes[1]
        byte_count = raw_bytes[2] if len(raw_bytes) > 2 else 0
        register_data = raw_bytes[3:3 + byte_count] if byte_count > 0 else b""

        registers_config = frame_format.get("registers", [])
        values = {}

        for reg_conf in registers_config:
            name = reg_conf["name"]
            address = reg_conf.get("address", 0)
            count = reg_conf.get("count", 1)
            data_type = reg_conf.get("data_type", "uint16")
            scale = reg_conf.get("scale", 1.0)
            offset_value = reg_conf.get("offset_value", 0.0)
            byte_order = reg_conf.get("byte_order", "big_endian")

            byte_offset = address * 2
            byte_length = count * 2

            if byte_offset + byte_length > len(register_data):
                raise ValueError(f"寄存器 '{name}' 地址越界")

            reg_bytes = register_data[byte_offset:byte_offset + byte_length]
            raw_val = self.bytes_to_value(reg_bytes, data_type, byte_order)
            converted = self.apply_conversion(float(raw_val), scale, offset_value)
            values[name] = round(converted, 6)

        return {
            "protocol_type": "modbus_rtu",
            "raw_hex": hex_data,
            "frame_length": len(raw_bytes),
            "slave_id": slave_id,
            "function_code": function_code,
            "byte_count": byte_count,
            "checksum_valid": crc_valid,
            "values": values,
        }

    # ============ modbus_tcp 解析 ============

    def _parse_modbus_tcp(self, frame_format: dict, raw_bytes: bytes, hex_data: str) -> dict:
        """
        Modbus TCP 解析

        frame_format 示例:
        {
            "unit_id": 1,
            "registers": [...]
        }
        """
        if len(raw_bytes) < 7:
            raise ValueError("Modbus TCP 帧长度不足")

        # MBAP Header
        transaction_id = struct.unpack(">H", raw_bytes[0:2])[0]
        protocol_id = struct.unpack(">H", raw_bytes[2:4])[0]
        length = struct.unpack(">H", raw_bytes[4:6])[0]
        unit_id = raw_bytes[6]
        function_code = raw_bytes[7] if len(raw_bytes) > 7 else 0

        register_data = raw_bytes[8:]
        registers_config = frame_format.get("registers", [])
        values = {}

        for reg_conf in registers_config:
            name = reg_conf["name"]
            address = reg_conf.get("address", 0)
            count = reg_conf.get("count", 1)
            data_type = reg_conf.get("data_type", "uint16")
            scale = reg_conf.get("scale", 1.0)
            offset_value = reg_conf.get("offset_value", 0.0)
            byte_order = reg_conf.get("byte_order", "big_endian")

            byte_offset = address * 2
            byte_length = count * 2

            if byte_offset + byte_length > len(register_data):
                raise ValueError(f"寄存器 '{name}' 地址越界")

            reg_bytes = register_data[byte_offset:byte_offset + byte_length]
            raw_val = self.bytes_to_value(reg_bytes, data_type, byte_order)
            converted = self.apply_conversion(float(raw_val), scale, offset_value)
            values[name] = round(converted, 6)

        return {
            "protocol_type": "modbus_tcp",
            "raw_hex": hex_data,
            "frame_length": len(raw_bytes),
            "transaction_id": transaction_id,
            "unit_id": unit_id,
            "function_code": function_code,
            "values": values,
        }

    # ============ custom_frame 解析 ============

    def _parse_custom_frame(self, frame_format: dict, raw_bytes: bytes, hex_data: str) -> dict:
        """
        自定义帧格式解析

        frame_format 示例:
        {
            "header": {"offset": 0, "length": 2, "value": "AA55"},
            "length_field": {"offset": 2, "length": 1},
            "data_items": [
                {
                    "name": "temperature",
                    "offset": 4,
                    "length": 2,
                    "data_type": "int16",
                    "byte_order": "big_endian",
                    "scale": 0.1,
                    "offset_value": 0
                }
            ],
            "checksum": {"type": "crc16", "offset": -2}
        }
        """
        # 帧头校验
        header_config = frame_format.get("header")
        if header_config:
            h_offset = header_config.get("offset", 0)
            h_length = header_config.get("length", 2)
            expected = bytes.fromhex(header_config["value"])
            actual = raw_bytes[h_offset:h_offset + h_length]
            if actual != expected:
                raise ValueError(f"帧头不匹配: 期望 {expected.hex()}, 实际 {actual.hex()}")

        # 校验和
        checksum_config = frame_format.get("checksum")
        if checksum_config:
            self._verify_checksum(raw_bytes, checksum_config)

        # 解析数据项
        data_items = frame_format.get("data_items", [])
        values = {}

        for item_conf in data_items:
            name = item_conf["name"]
            offset = item_conf["offset"]
            length = item_conf.get("length", 2)
            data_type = item_conf.get("data_type", "uint16")
            byte_order = item_conf.get("byte_order", "big_endian")
            scale = item_conf.get("scale", 1.0)
            offset_value = item_conf.get("offset_value", 0.0)

            if offset + length > len(raw_bytes):
                raise ValueError(f"数据项 '{name}' 偏移越界")

            raw_val = self.bytes_to_value(raw_bytes[offset:offset + length], data_type, byte_order)
            converted = self.apply_conversion(float(raw_val), scale, offset_value)
            values[name] = round(converted, 6)

        return {
            "protocol_type": "custom_frame",
            "raw_hex": hex_data,
            "frame_length": len(raw_bytes),
            "checksum_valid": True if checksum_config else None,
            "values": values,
        }

    # ============ json 解析 ============

    def _parse_json(self, frame_format: dict, raw_bytes: bytes, hex_data: str) -> dict:
        """
        JSON格式数据解析

        frame_format 示例:
        {
            "encoding": "utf-8",
            "field_mapping": [
                {"json_path": "data.temperature", "name": "temperature", "scale": 1.0, "offset_value": 0.0}
            ]
        }
        """
        encoding = frame_format.get("encoding", "utf-8")
        try:
            text = raw_bytes.decode(encoding)
            data = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"JSON解析失败: {str(e)}")

        field_mapping = frame_format.get("field_mapping", [])
        values = {}

        if field_mapping:
            for mapping in field_mapping:
                json_path = mapping["json_path"]
                name = mapping.get("name", json_path)
                scale = mapping.get("scale", 1.0)
                offset_value = mapping.get("offset_value", 0.0)

                # 支持嵌套路径 a.b.c
                val = data
                for key in json_path.split("."):
                    if isinstance(val, dict) and key in val:
                        val = val[key]
                    else:
                        val = None
                        break

                if val is not None:
                    values[name] = round(self.apply_conversion(float(val), scale, offset_value), 6)
        else:
            # 无映射则返回原始数据
            values = data

        return {
            "protocol_type": "json",
            "raw_hex": hex_data,
            "values": values,
        }

    # ============ csv 解析 ============

    def _parse_csv(self, frame_format: dict, raw_bytes: bytes, hex_data: str) -> dict:
        """
        CSV格式数据解析

        frame_format 示例:
        {
            "encoding": "utf-8",
            "delimiter": ",",
            "header_row": true,
            "field_mapping": [
                {"column_index": 0, "name": "methane", "scale": 1.0, "offset_value": 0.0}
            ]
        }
        """
        encoding = frame_format.get("encoding", "utf-8")
        delimiter = frame_format.get("delimiter", ",")

        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError as e:
            raise ValueError(f"CSV编码解码失败: {str(e)}")

        lines = text.strip().split("\n")
        if not lines:
            raise ValueError("CSV数据为空")

        header_row = frame_format.get("header_row", True)
        data_start = 1 if header_row else 0
        headers = lines[0].split(delimiter) if header_row else []

        field_mapping = frame_format.get("field_mapping", [])
        results = []

        for line in lines[data_start:]:
            fields = line.strip().split(delimiter)
            row_values = {}

            for mapping in field_mapping:
                col_idx = mapping.get("column_index", 0)
                name = mapping.get("name", f"col_{col_idx}")
                scale = mapping.get("scale", 1.0)
                offset_value = mapping.get("offset_value", 0.0)

                if col_idx < len(fields):
                    try:
                        raw_val = float(fields[col_idx])
                        row_values[name] = round(self.apply_conversion(raw_val, scale, offset_value), 6)
                    except ValueError:
                        row_values[name] = fields[col_idx]

            results.append(row_values)

        return {
            "protocol_type": "csv",
            "raw_hex": hex_data,
            "row_count": len(results),
            "values": results[0] if len(results) == 1 else results,
        }

    # ============ 内部工具 ============

    def _verify_checksum(self, raw_bytes: bytes, checksum_config: dict):
        """校验和验证"""
        checksum_type = checksum_config.get("type", "crc16")
        offset = checksum_config.get("offset", -2)

        if offset < 0:
            offset = len(raw_bytes) + offset

        data_part = raw_bytes[:offset]
        checksum_bytes = raw_bytes[offset:]

        if checksum_type == "crc16":
            if len(checksum_bytes) < 2:
                raise ValueError("CRC16校验字节不足")
            received = struct.unpack("<H", checksum_bytes[:2])[0]
            calculated = self.crc16(data_part)
            if received != calculated:
                raise ValueError(f"CRC16校验失败: 期望 {calculated:#06x}, 收到 {received:#06x}")
        elif checksum_type == "crc32":
            if len(checksum_bytes) < 4:
                raise ValueError("CRC32校验字节不足")
            received = struct.unpack("<I", checksum_bytes[:4])[0]
            calculated = self.crc32(data_part)
            if received != calculated:
                raise ValueError(f"CRC32校验失败: 期望 {calculated:#010x}, 收到 {received:#010x}")
        elif checksum_type == "sum8":
            received = checksum_bytes[0]
            calculated = sum(data_part) & 0xFF
            if received != calculated:
                raise ValueError(f"Sum8校验失败: 期望 {calculated:#04x}, 收到 {received:#04x}")
        else:
            raise ValueError(f"不支持的校验类型: {checksum_type}")


def parse_protocol_data(protocol_type: str, frame_format: dict, hex_data: str) -> dict:
    """便捷函数：解析协议数据"""
    parser = ProtocolParser()
    return parser.parse(protocol_type, frame_format, hex_data)
