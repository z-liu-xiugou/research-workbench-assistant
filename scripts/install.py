"""将唯一的公开 Skill 安装到本地；绝不覆盖已有同名目录。"""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile
import os


def install(destination):
    source = Path(__file__).resolve().parents[1] / "skills" / "research-workbench"
    target = destination.expanduser().resolve() / source.name
    if os.path.lexists(target):
        raise FileExistsError("已有同名 Skill，请先备份并移走旧目录：" + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    # 独占锁让本安装器的并发调用不能同时发布同名技能。
    lock = target.parent / ("." + source.name + ".install.lock")
    with lock.open("x", encoding="utf-8"):
        pass
    try:
        with tempfile.TemporaryDirectory(prefix=".research-workbench-install-", dir=target.parent) as staging:
            staged = Path(staging) / source.name
            shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            if os.path.lexists(target):
                raise FileExistsError("安装期间出现同名目录，已停止：" + str(target))
            staged.rename(target)
    finally:
        lock.unlink()
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path.home() / ".agents" / "skills",
                        help="技能父目录；默认用户级 .agents/skills")
    args = parser.parse_args()
    try:
        print("已安装：" + str(install(args.dest)))
        print("在 Codex 中使用 $research-workbench；未发现时重启 Codex。")
    except OSError as error:
        print("安装失败：" + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
