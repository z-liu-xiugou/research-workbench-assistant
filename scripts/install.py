"""将唯一的公开 Skill 安装到本地；绝不覆盖已有同名目录。"""
import argparse
from pathlib import Path
import shutil
import sys


def install(destination):
    source = Path(__file__).resolve().parents[1] / "skills" / "research-workbench"
    target = destination.expanduser().resolve() / source.name
    if target.exists():
        raise FileExistsError("已有同名 Skill，请先备份并移走旧目录：" + str(target))
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
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
