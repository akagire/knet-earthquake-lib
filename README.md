# earthquake-grading

K-NET 形式の強震記録から気象庁計測震度を算出するためのツール群です。

## セットアップ

### 前提

- Python 3.11 系
- `pyenv` と `pipenv` がインストールされていること

### 手順

```bash
pyenv install 3.11.8           # まだインストールしていない場合の例
pyenv local 3.11.8

pipenv --python 3.11
pipenv install                  # Pipfile に基づいて依存をインストール
```

## 使い方

イベントディレクトリ（例: `events/IWT02020260308220849/`）に対して、計測震度を計算できます。

```bash
pipenv run python -m earthquake_grading.cli events/IWT02020260308220849
```

JSON 形式で結果を得たい場合:

```bash
pipenv run python -m earthquake_grading.cli events/IWT02020260308220849 --output json
```

## 実装方針

- 実装言語や計測震度アルゴリズムの詳細は `adr/0001-jma-intensity-from-knet.md` を参照してください。
- Python のコーディング規約や開発環境方針は `adr/0002-python-coding-style.md` を参照してください。

