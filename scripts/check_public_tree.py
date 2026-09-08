"""扫描 Git 跟踪文件；只报告位置和规则名，不打印疑似密钥。不是完整 DLP。"""
from pathlib import Path
import re
import subprocess
import sys


PATTERNS = {
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "openai-style-key": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    "personal-windows-path": re.compile(r"(?i)[A-Z]:[\\/](?:Users[\\/](?!Public\b)[^\s\\/]+|pycharm[_\\/])"),
}


def inspect(name, content):
    path = Path(name)
    findings = []
    if (set(path.parts) & {"_private_reference", "__pycache__"} or
            path.suffix.lower() in {".pdf", ".caj", ".pem", ".key"} or
            path.name == ".env" or path.name.startswith(".env.")):
        findings.append({"path": name, "rule": "private-file"})
    for number, line in enumerate(content.splitlines(), 1):
        for rule, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append({"path": name, "line": number, "rule": rule})
    return findings


def scan(root):
    names = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    findings = []
    for name in filter(None, names):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            findings.append({"path": name, "rule": "tracked-link"})
        elif path.exists():
            findings.extend(inspect(name, path.read_bytes().decode("utf-8", errors="replace")))
    return findings


if __name__ == "__main__":
    result = scan(Path(__file__).resolve().parents[1])
    for finding in result:
        print(finding)
    print(f"Public-tree findings: {len(result)}")
    sys.exit(1 if result else 0)
