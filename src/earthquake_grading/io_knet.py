"""K-NET 形式強震記録の入出力を扱うモジュール。

K-NET ASCII フォーマットのファイルからヘッダ情報を取得し、カウント値を
物理加速度（gal）に変換した波形として読み込む。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, List, Tuple

import numpy as np


@dataclass
class KnetHeader:
    """K-NET 強震記録ファイルのヘッダ情報。

    Args:
        origin_time: 地震発生時刻の文字列表現。
        latitude: 震央緯度。
        longitude: 震央経度。
        depth_km: 震源深さ [km]。
        magnitude: マグニチュード。
        station_code: 観測点コード。
        station_latitude: 観測点緯度。
        station_longitude: 観測点経度。
        station_height_m: 観測点標高 [m]。
        record_time: 記録開始時刻の文字列表現。
        sampling_freq_hz: サンプリング周波数 [Hz]。
        duration_sec: 計測時間 [s]。
        direction: 成分方向（例: ``\"E-W\"``）。
        scale_factor_gal: スケールファクタの分子（gal）。
        scale_factor_count: スケールファクタの分母（カウント値）。
        max_acc_gal: 最大加速度 [gal]。ヘッダに無い場合は ``None``。
        last_correction: 最終校正時刻の文字列表現。
        memo: メモ欄の文字列。空の場合は ``\"\"``。
    """

    origin_time: str
    latitude: float
    longitude: float
    depth_km: float
    magnitude: float
    station_code: str
    station_latitude: float
    station_longitude: float
    station_height_m: float
    record_time: str
    sampling_freq_hz: float
    duration_sec: float
    direction: str
    scale_factor_gal: float
    scale_factor_count: float
    max_acc_gal: float | None
    last_correction: str
    memo: str


@dataclass
class EventWaveforms:
    """1 観測点・1 地震イベントの 3 成分波形。

    Args:
        ew: 東西成分の加速度波形 [gal]。
        ns: 南北成分の加速度波形 [gal]。
        ud: 上下成分の加速度波形 [gal]。
        header_ew: 東西成分ファイルのヘッダ。
        header_ns: 南北成分ファイルのヘッダ。
        header_ud: 上下成分ファイルのヘッダ。
    """

    ew: np.ndarray
    ns: np.ndarray
    ud: np.ndarray
    header_ew: KnetHeader
    header_ns: KnetHeader
    header_ud: KnetHeader

    @property
    def sampling_freq_hz(self) -> float:
        """サンプリング周波数 [Hz] を返す。

        Returns:
            サンプリング周波数 [Hz]。
        """

        return self.header_ew.sampling_freq_hz


def _split_header_line(line: str) -> Tuple[str, str]:
    """K-NET ヘッダ行をラベルと値に分割する。

    K-NET の仕様ではラベルと値の間に複数スペースが入るが、実データでは
    スペース数が固定でない場合もある。そのため、2 つ以上のスペースを
    区切りとして左側をラベル、右側を値として解釈する。

    Args:
        line: ヘッダ行の文字列。

    Returns:
        (ラベル, 値) のタプル。値が存在しない場合は空文字列。
    """

    stripped = line.rstrip("\n")
    # ラベルと値の間の 1 個以上の空白を区切りとする。
    # 末尾まで値が存在しない場合（Origin Time など）はマッチしない。
    match = re.match(r"\s*(\S(?:.*\S)?)\s+(.+\S)\s*$", stripped)
    if match:
        label = match.group(1)
        value = match.group(2)
        return label, value

    # 値が無い行（Origin Time などグローバル情報行）の場合は、そのままラベルのみ返す。
    return stripped.strip(), ""


def _parse_scale_factor(text: str) -> Tuple[float, float]:
    """スケールファクタ文字列を分子・分母に分解する。

    例: ``\"7845(gal)/8223790\"`` -> (7845.0, 8223790.0)

    Args:
        text: ヘッダ中の Scale Factor 行の値。

    Returns:
        (分子[gal], 分母[カウント値]) のタプル。

    Raises:
        ValueError: フォーマットが想定と異なる場合。
    """

    match = re.search(r"([0-9.]+)\(gal\)/([0-9.]+)", text)
    if not match:
        msg = f"Scale Factor の形式が不正です: {text!r}"
        raise ValueError(msg)
    num = float(match.group(1))
    denom = float(match.group(2))
    return num, denom


def _parse_float_from_suffix(value: str, suffix: str) -> float:
    """末尾に単位が付いている値から数値部分を取り出す。

    Args:
        value: 例 ``\"100Hz\"`` のような文字列。
        suffix: 取り除きたい接尾辞（例: ``\"Hz\"``）。

    Returns:
        数値部分を float に変換した値。
    """

    return float(value.replace(suffix, "").strip())


def _parse_optional_float(value: str, default: float = 0.0) -> float:
    """空文字列を許容する float 変換ヘルパ。

    Args:
        value: 変換対象の文字列。
        default: 変換に失敗した場合に返すデフォルト値。

    Returns:
        変換された float 値、またはデフォルト値。
    """

    text = value.strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def parse_knet_header(lines: Iterable[str]) -> KnetHeader:
    """K-NET ファイルの先頭 17 行からヘッダ情報を解析する。

    Args:
        lines: ファイル先頭から 17 行分のイテラブル。

    Returns:
        解析された ``KnetHeader`` インスタンス。
    """

    # K-NET 仕様では 17 行がヘッダ。
    header_lines: List[str] = list(lines)[:17]
    if len(header_lines) < 17:
        msg = "K-NET ヘッダが 17 行未満です。"
        raise ValueError(msg)

    values: dict[str, str] = {}
    for line in header_lines:
        label, value = _split_header_line(line.rstrip("\\n"))
        values[label] = value

    scale_num, scale_denom = _parse_scale_factor(values["Scale Factor"])

    max_acc_gal: float | None = None
    max_acc_value = values.get("Max. Acc. (gal)")
    if max_acc_value:
        try:
            max_acc_gal = float(max_acc_value)
        except ValueError:
            max_acc_gal = None

    return KnetHeader(
        origin_time=values.get("Origin Time", ""),
        latitude=_parse_optional_float(values.get("Lat.", "")),
        longitude=_parse_optional_float(values.get("Long.", "")),
        depth_km=_parse_optional_float(values.get("Depth. (km)", "")),
        magnitude=_parse_optional_float(values.get("Mag.", "")),
        station_code=values.get("Station Code", ""),
        station_latitude=_parse_optional_float(values.get("Station Lat.", "")),
        station_longitude=_parse_optional_float(values.get("Station Long.", "")),
        station_height_m=_parse_optional_float(values.get("Station Height(m)", "")),
        record_time=values.get("Record Time", ""),
        sampling_freq_hz=_parse_float_from_suffix(
            values["Sampling Freq(Hz)"],
            "Hz",
        ),
        duration_sec=_parse_optional_float(values.get("Duration Time(s)", "")),
        direction=values.get("Dir.", ""),
        scale_factor_gal=scale_num,
        scale_factor_count=scale_denom,
        max_acc_gal=max_acc_gal,
        last_correction=values.get("Last Correction", ""),
        memo=values.get("Memo.", ""),
    )


def read_knet_file(path: Path) -> Tuple[KnetHeader, np.ndarray]:
    """K-NET ASCII ファイルを読み込み、ヘッダと加速度波形を返す。

    Args:
        path: 読み込む K-NET ファイルへのパス。

    Returns:
        ヘッダ情報と、物理加速度 [gal] の 1 次元配列のタプル。
    """

    text = path.read_text(encoding="ascii", errors="ignore")
    lines = text.splitlines()
    header = parse_knet_header(lines[:17])

    # 18 行目以降が強震データ（符号付き 7 桁整数）の想定。
    data_lines = lines[17:]
    samples: List[int] = []
    for line in data_lines:
        line = line.strip()
        if not line:
            continue
        for token in line.split():
            try:
                samples.append(int(token))
            except ValueError:
                # 非数値トークンは無視する。
                continue

    if not samples:
        msg = f"波形データが読み込めませんでした: {path}"
        raise ValueError(msg)

    counts = np.asarray(samples, dtype=np.float64)

    # K-NET 仕様では、Max Acc は全長平均値（オフセット）を引いた値から求める。
    # ここでも DC 成分を除去するために平均値を差し引いてからスケーリングする。
    counts_zero_mean = counts - counts.mean()
    scale = header.scale_factor_gal / header.scale_factor_count
    acc_gal = counts_zero_mean * scale

    return header, acc_gal


def load_event_waveforms(event_dir: Path) -> EventWaveforms:
    """イベントディレクトリから 3 成分波形を読み込む。

    Args:
        event_dir: K-NET イベントファイルが置かれたディレクトリ。

    Returns:
        3 成分の加速度波形とヘッダをまとめた ``EventWaveforms``。

    Raises:
        FileNotFoundError: 必要な成分ファイルが存在しない場合。
        ValueError: サンプリング周波数やサンプル数が成分間で一致しない場合。
    """

    ew_path = next(event_dir.glob("*.EW"), None)
    ns_path = next(event_dir.glob("*.NS"), None)
    ud_path = next(event_dir.glob("*.UD"), None)

    if ew_path is None or ns_path is None or ud_path is None:
        msg = f"EW/NS/UD のいずれかのファイルが見つかりません: {event_dir}"
        raise FileNotFoundError(msg)

    header_ew, ew = read_knet_file(ew_path)
    header_ns, ns = read_knet_file(ns_path)
    header_ud, ud = read_knet_file(ud_path)

    fs_values = {
        header_ew.sampling_freq_hz,
        header_ns.sampling_freq_hz,
        header_ud.sampling_freq_hz,
    }
    if len(fs_values) != 1:
        msg = f"サンプリング周波数が成分間で一致しません: {fs_values}"
        raise ValueError(msg)

    n_values = {len(ew), len(ns), len(ud)}
    if len(n_values) != 1:
        msg = f"サンプル数が成分間で一致しません: {n_values}"
        raise ValueError(msg)

    return EventWaveforms(
        ew=ew,
        ns=ns,
        ud=ud,
        header_ew=header_ew,
        header_ns=header_ns,
        header_ud=header_ud,
    )

