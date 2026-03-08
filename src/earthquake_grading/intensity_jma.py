"""気象庁計測震度の算出ロジックを提供するモジュール。

JMA 公開資料「計測震度の算出方法」に基づき、フィルタ処理・3 成分合成・
代表加速度の決定・計測震度 I および震度階級の算出を行う。
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np


def compute_jma_filter(frequencies_hz: np.ndarray) -> np.ndarray:
    """周波数配列に対応する JMA 総合フィルタ H(f) を計算する。

    Args:
        frequencies_hz: 周波数 [Hz] の 1 次元配列。

    Returns:
        各周波数に対応するフィルタ振幅 H(f) の 1 次元配列。
    """

    f = frequencies_hz.astype(float)

    # ローカットフィルタ
    fl = np.sqrt(1.0 - np.exp(-np.power(f / 0.5, 3.0)))

    # ハイカットフィルタ
    y = 0.1 * f
    y2 = np.power(y, 2.0)
    fh = 1.0 + 0.694 * y2
    fh += 0.241 * np.power(y, 4.0)
    fh += 0.0557 * np.power(y, 6.0)
    fh += 0.009664 * np.power(y, 8.0)
    fh += 0.00134 * np.power(y, 10.0)
    fh += 0.000155 * np.power(y, 12.0)
    fh = np.power(fh, -0.5)

    # 周期効果フィルタ
    ff = np.zeros_like(f)
    nonzero = f > 0.0
    ff[nonzero] = np.power(1.0 / f[nonzero], 0.5)
    ff[~nonzero] = 0.0

    h = fl * fh * ff
    # f = 0 近傍の特異性を避けるため、0 Hz の値は明示的に 0 とする。
    h[f == 0.0] = 0.0
    return h


def apply_jma_filter(acc_gal: np.ndarray, sampling_freq_hz: float) -> np.ndarray:
    """1 成分の加速度波形に JMA フィルタを適用する。

    Args:
        acc_gal: 加速度波形 [gal] の 1 次元配列。
        sampling_freq_hz: サンプリング周波数 [Hz]。

    Returns:
        フィルタ適用後の加速度波形 [gal] の 1 次元配列。
    """

    n = acc_gal.shape[0]
    # 実数 FFT の周波数ビン
    freqs = np.fft.rfftfreq(n, d=1.0 / sampling_freq_hz)
    h = compute_jma_filter(freqs)
    spec = np.fft.rfft(acc_gal)
    spec_filtered = spec * h
    filtered = np.fft.irfft(spec_filtered, n=n)
    return filtered


def compute_representative_acceleration(
    ew_gal: np.ndarray,
    ns_gal: np.ndarray,
    ud_gal: np.ndarray,
    sampling_freq_hz: float,
) -> float:
    """3 成分合成波形から代表加速度 a を求める。

    ベクトル合成波形 v(t) の絶対値が a 以上となる時間の合計が 0.3 秒となるような
    a を、離散サンプリング波形を用いて近似的に求める。

    Args:
        ew_gal: 東西成分の加速度波形 [gal]。
        ns_gal: 南北成分の加速度波形 [gal]。
        ud_gal: 上下成分の加速度波形 [gal]。
        sampling_freq_hz: サンプリング周波数 [Hz]。

    Returns:
        代表加速度 a [gal]。
    """

    if not (ew_gal.shape == ns_gal.shape == ud_gal.shape):
        msg = (
            "3 成分のサンプル数が一致していません: "
            f"EW={ew_gal.shape}, NS={ns_gal.shape}, UD={ud_gal.shape}"
        )
        raise ValueError(msg)

    # 3 成分ベクトル合成
    v = np.sqrt(ew_gal**2 + ns_gal**2 + ud_gal**2)

    n_samples = v.shape[0]
    k = int(round(0.3 * sampling_freq_hz))
    if k < 1:
        k = 1
    if k > n_samples:
        k = n_samples

    # 降順ソートして K 番目の値を代表値 a とみなす。
    sorted_v = np.sort(v)[::-1]
    a_gal = float(sorted_v[k - 1])
    return a_gal


def _round_intensity(value: float) -> float:
    """計測震度 I の丸め処理を行う。

    小数第 3 位を四捨五入し、小数第 2 位で切り捨てる。

    Args:
        value: 丸め前の計測震度 I。

    Returns:
        丸め後の計測震度 I。
    """

    tmp = round(value, 3)
    return math.floor(tmp * 100.0) / 100.0


def _grade_from_intensity(i_value: float) -> str:
    """計測震度から震度階級を求める。

    Args:
        i_value: 計測震度（丸め後）。

    Returns:
        震度階級（例: ``\"3\"``, ``\"5弱\"``）。
    """

    if i_value < 0.5:
        return "0"
    if i_value < 1.5:
        return "1"
    if i_value < 2.5:
        return "2"
    if i_value < 3.5:
        return "3"
    if i_value < 4.5:
        return "4"
    if i_value < 5.0:
        return "5弱"
    if i_value < 5.5:
        return "5強"
    if i_value < 6.0:
        return "6弱"
    if i_value < 6.5:
        return "6強"
    return "7"


def compute_intensity(a_gal: float) -> Tuple[float, str]:
    """代表加速度から計測震度と震度階級を計算する。

    Args:
        a_gal: 代表加速度 a [gal]。

    Returns:
        計測震度（小数第 2 位まで）と震度階級文字列のタプル。

    Raises:
        ValueError: a_gal が正でない場合。
    """

    if a_gal <= 0.0:
        msg = f"代表加速度 a_gal は正である必要があります: {a_gal}"
        raise ValueError(msg)

    # I = 2 log10(a) + 0.94
    i_raw = 2.0 * math.log10(a_gal) + 0.94
    i_rounded = _round_intensity(i_raw)
    grade = _grade_from_intensity(i_rounded)
    return i_rounded, grade

