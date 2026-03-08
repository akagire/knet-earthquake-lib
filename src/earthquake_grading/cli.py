"""コマンドラインから計測震度を計算するためのエントリポイント。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .io_knet import EventWaveforms, load_event_waveforms
from .intensity_jma import (
    apply_jma_filter,
    compute_intensity,
    compute_representative_acceleration,
)


def _build_parser() -> argparse.ArgumentParser:
    """CLI 引数パーサを構築する。

    Returns:
        構築済みの ``ArgumentParser``。
    """

    parser = argparse.ArgumentParser(
        description="K-NET 強震記録から気象庁計測震度を計算するツール。",
    )
    parser.add_argument(
        "event_dir",
        type=str,
        help="K-NET イベントファイル（*.EW, *.NS, *.UD）が置かれたディレクトリ。",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="出力形式（text または json）。デフォルトは text。",
    )
    return parser


def _analyze_event(event_dir: Path) -> Dict[str, Any]:
    """イベントディレクトリを解析し、計測震度情報を計算する。

    Args:
        event_dir: イベントディレクトリへのパス。

    Returns:
        駅名・計測震度・震度階級などを含む辞書。
    """

    waveforms: EventWaveforms = load_event_waveforms(event_dir)
    fs = waveforms.sampling_freq_hz

    ew_f = apply_jma_filter(waveforms.ew, fs)
    ns_f = apply_jma_filter(waveforms.ns, fs)
    ud_f = apply_jma_filter(waveforms.ud, fs)

    a_gal = compute_representative_acceleration(
        ew_gal=ew_f,
        ns_gal=ns_f,
        ud_gal=ud_f,
        sampling_freq_hz=fs,
    )
    intensity_value, grade = compute_intensity(a_gal)

    station_code = waveforms.header_ew.station_code

    return {
        "station_code": station_code,
        "sampling_freq_hz": fs,
        "representative_acc_gal": a_gal,
        "intensity": intensity_value,
        "grade": grade,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI エントリポイント。

    Args:
        argv: コマンドライン引数。``None`` の場合は ``sys.argv`` から取得する。

    Returns:
        プロセス終了コード。正常終了時は 0。
    """

    parser = _build_parser()
    args = parser.parse_args(argv)

    event_dir = Path(args.event_dir)
    if not event_dir.is_dir():
        parser.error(f"イベントディレクトリが存在しません: {event_dir}")

    result = _analyze_event(event_dir)

    if args.output == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Station: {result['station_code']}, "
            f"I = {result['intensity']:.2f}, "
            f"Shindo = {result['grade']}, "
            f"a = {result['representative_acc_gal']:.2f} gal",
        )

    return 0


if __name__ == "__main__":  # pragma: no cover - スクリプト実行時のみ
    raise SystemExit(main())

