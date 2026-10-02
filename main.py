import sys


def main() -> int:
    try:
        from qiangjing.controller import run
    except ImportError:
        sys.stderr.write("还没装界面库。请在项目目录执行：\n  pip install -r requirements.txt\n")
        return 1
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
