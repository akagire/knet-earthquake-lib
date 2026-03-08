# Python コードスタイルと開発環境方針

Status: Accepted

Relevant PR:


# Context

本リポジトリでは、今後 Python で震度計算ロジックや CLI ツールを実装していく予定がある。  
その際に、開発者ごとにコードスタイルや開発環境の構築方法がばらつくと、以下のような問題が生じる:

- 型の有無がバラバラで、インターフェースの意図が読み取りにくい。
- Docstring のフォーマットが統一されておらず、関数やクラスの仕様が分かりづらい。
- Python バージョンや依存パッケージのインストール方法が統一されておらず、環境差異によるバグや再現性の低下が起こる。

これらを避けるため、Python コードの書き方と、開発環境の基本的な構築方法について、あらかじめ共通方針を定めておく。


## References

- Google Python Style Guide（特に Docstring 部分）
- PEP 484（Type Hints）
- pyenv 公式ドキュメント
- pipenv 公式ドキュメント


# Decision

- **型ヒント（type hint）を必須とする**
  - すべての公開関数・メソッド・クラスの属性について、可能な限り Python の型ヒントを付与する。
  - ローカル変数についても、型推論が難しい箇所や可読性向上に寄与する箇所では積極的に型注釈を付ける。
- **Google style の Docstring を採用する**
  - モジュール・クラス・すべての公開関数／メソッドには Docstring を付与し、Google style の書式で記述する。
  - Docstring には、関数／メソッドの役割、引数、戻り値、例外、必要に応じて使用例を明示する。
- **Python バージョン管理に pyenv を使用し、パッケージ管理に pipenv を使用する**
  - 各開発者は pyenv により指定の Python バージョンをインストールし、本リポジトリ直下で `pyenv local` によりバージョンを固定する。
  - プロジェクトごとの仮想環境と依存パッケージ管理には pipenv を用い、`Pipfile` および `Pipfile.lock` によって依存関係を明示する。


# Reason

## 型ヒントを必須とする理由

- インターフェースの意図が明確になり、関数やメソッドの利用方法が分かりやすくなる。
- 静的解析ツール（mypy など）を導入しやすくなり、型関連のバグを早期に検出できる。
- IDE の補完精度が向上し、開発効率が上がる。

## Google style Docstring を採用する理由

- 引数・戻り値・例外など、関数仕様の要素が明示的なセクションとして整理され、読み手が必要な情報を素早く把握できる。
- Sphinx などのドキュメント生成ツールとの相性が良く、自動ドキュメント化もしやすい。
- すでに広く用いられているフォーマットであり、新規参加者が慣れている可能性が高い。

## pyenv + pipenv を採用する理由

- Python バージョンをリポジトリごとに固定できるため、「手元では動くが他の環境では動かない」といったバージョン差異の問題を軽減できる。
- pipenv により、仮想環境の作成・依存パッケージのインストール・ロックファイル生成が一貫したコマンドで扱える。
- `Pipfile` / `Pipfile.lock` を共有することで、開発者間・ CI 環境間で同一の依存セットを簡単に再現できる。


# Python コード記述ルール

## 型ヒント

- すべての関数・メソッド定義に対して、引数と戻り値の型を明示する。
- 例:

```python
from typing import Iterable, List


def compute_intensities(values: Iterable[float]) -> List[float]:
    """Compute some intensities from input values."""
    return [v * 2.0 for v in values]
```

- クラス属性にも、可能な限り型ヒントを付与する。

```python
from dataclasses import dataclass


@dataclass
class EventMetadata:
    station_code: str
    sampling_freq_hz: float
    duration_sec: float
```

- 型エイリアスや `TypedDict`, `Protocol` なども必要に応じて利用し、ドメイン特有の型を表現する。


## Google style Docstring

- モジュール、クラス、公開関数／メソッドに Docstring を付ける。
- Docstring は三連引用符（`"""`）で囲み、最初の行に概要、その後に空行を挟んで詳細やセクションを記述する。

### 関数・メソッドの Docstring 例

```python
def compute_jma_intensity(a_gal: float) -> float:
    """Compute JMA instrumental intensity from representative acceleration.

    Args:
        a_gal: Representative acceleration in gal.

    Returns:
        Instrumental intensity value rounded to two decimal places.

    Raises:
        ValueError: If a_gal is not positive.
    """
    ...
```

- 主なセクション:
  - `Args:` 引数名、型、意味を列挙。
  - `Returns:` 戻り値の意味と型を説明。
  - `Raises:` 想定される例外と、その発生条件を説明。
  - `Examples:` 必要に応じて簡単な使用例を追加。

### クラスの Docstring 例

```python
class JmaIntensityCalculator:
    """計測震度を計算するクラス。

    周波数領域で気象庁の震度フィルタを適用し、代表加速度と計測震度を計算する。
    """
```

- Docstring の言語は**原則として日本語**とする。既存ライブラリとの整合性などから英語が適切な場合は英語で記述してもよいが、1 つの関数／クラス内では表記を混在させない。


# 開発環境構築ルール（pyenv と pipenv）

## pyenv による Python バージョン管理

- 各開発者は、まず pyenv をインストールし、プロジェクトで利用する Python バージョンをインストールする。
- 本リポジトリで採用する Python バージョン（例: `3.11.x`）を決めたら、リポジトリ直下で次を実行してローカルバージョンを固定する。

```bash
pyenv install 3.11.x  # 未インストールの場合
pyenv local 3.11.x
```

- これにより、このディレクトリ配下で実行される `python` コマンドが指定バージョンに固定される。


## pipenv による仮想環境と依存管理

- 依存パッケージの追加・更新は、すべて pipenv 経由で行う。
- 初回セットアップの例:

```bash
pipenv --python 3.11
pipenv install numpy
pipenv install --dev mypy
```

- 実行時には、`pipenv run` もしくは `pipenv shell` を利用する。

```bash
pipenv run python -m earthquake_grading.cli calc-sindo events/...
```

- `Pipfile` と `Pipfile.lock` をリポジトリにコミットし、依存関係を共有する。
- 既存環境を再現したい場合は、次のコマンドで依存をインストールする。

```bash
pipenv sync --dev
```


# Consequences

- **メリット**
  - 型ヒントと Docstring によってコードの意図が明確になり、レビューや保守が容易になる。
  - pyenv + pipenv により、Python バージョンと依存パッケージの違いによるトラブルが減り、環境再現性が高まる。
  - 将来的に静的解析や自動ドキュメント生成、CI 上での型チェック／テスト実行などを導入しやすくなる。

- **デメリット / コスト**
  - 開発者は型ヒントと Docstring を記述する手間が増える。
  - pyenv と pipenv の初期セットアップが必要になる。
  - 既存のシンプルなスクリプトスタイルに比べると、学習コストがわずかに上がる。

これらのコストは、長期的な保守性とチーム全体の開発効率の向上によって十分に回収できると判断し、本方針を採用する。

