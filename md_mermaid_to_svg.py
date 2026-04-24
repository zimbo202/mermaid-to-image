#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_puppeteer_chrome() -> str | None:
    """查找 Puppeteer 缓存中的 Chrome 可执行文件路径。"""
    cache_dir = Path.home() / ".cache" / "puppeteer" / "chrome"
    if not cache_dir.exists():
        return None

    # 查找最新版本的 Chrome
    for version_dir in sorted(cache_dir.iterdir(), reverse=True):
        if version_dir.is_dir():
            chrome_path = version_dir / "chrome-linux64" / "chrome"
            if chrome_path.exists():
                return str(chrome_path)
    return None


LINK_BEGIN = "<!-- mermaid-svg-link-begin -->"
LINK_END = "<!-- mermaid-svg-link-end -->"


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    name = name.strip("._-")
    return name or "markdown"


def find_md_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() != ".md":
            raise ValueError(f"输入文件不是 .md 文件: {path}")
        return [path]

    if path.is_dir():
        return sorted(path.rglob("*.md"))

    raise FileNotFoundError(f"路径不存在: {path}")


def is_mermaid_fence_open(line: str):
    stripped = line.strip()
    if stripped.startswith("```mermaid"):
        return "```"
    if stripped.startswith("~~~mermaid"):
        return "~~~"
    return None


def is_fence_close(line: str, fence: str) -> bool:
    return line.strip().startswith(fence)


def remove_existing_svg_link(lines: list[str], start_index: int) -> tuple[int, list[Path]]:
    """
    删除 Mermaid 代码块后面由本工具生成的 SVG 链接块。
    返回新的起始位置，以及旧 SVG 路径列表。
    """
    removed_svg_paths = []

    i = start_index

    while i < len(lines) and lines[i].strip() == "":
        i += 1

    if i < len(lines) and lines[i].strip() == LINK_BEGIN:
        block_start = i
        i += 1

        while i < len(lines) and lines[i].strip() != LINK_END:
            match = re.search(r"\]\(([^)]+\.svg)\)", lines[i])
            if match:
                removed_svg_paths.append(Path(match.group(1)))
            i += 1

        if i < len(lines) and lines[i].strip() == LINK_END:
            i += 1

        while i < len(lines) and lines[i].strip() == "":
            i += 1

        return i, removed_svg_paths

    return start_index, removed_svg_paths


def run_mmdc(mermaid_text: str, output_svg: Path) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "diagram.mmd"
        input_file.write_text(mermaid_text, encoding="utf-8")

        cmd = [
            "mmdc",
            "-i", str(input_file),
            "-o", str(output_svg),
            "-b", "transparent",
        ]

        result = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"mmdc 转换失败: {output_svg}\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )


def process_md_file(md_file: Path) -> None:
    md_file = md_file.resolve()
    md_dir = md_file.parent
    md_stem = sanitize_filename(md_file.stem)

    # 创建与 md 文件同名的文件夹存放 SVG
    svg_dir = md_dir / md_stem
    svg_dir.mkdir(exist_ok=True)

    original_lines = md_file.read_text(encoding="utf-8").splitlines(keepends=True)

    new_lines = []
    used_svg_files = set()
    old_svg_files = set()

    i = 0
    diagram_index = 1
    changed = False

    while i < len(original_lines):
        line = original_lines[i]
        fence = is_mermaid_fence_open(line)

        if not fence:
            new_lines.append(line)
            i += 1
            continue

        # 收集 Mermaid 代码块
        block_lines = [line]
        i += 1

        mermaid_body_lines = []

        while i < len(original_lines):
            block_lines.append(original_lines[i])

            if is_fence_close(original_lines[i], fence):
                i += 1
                break

            mermaid_body_lines.append(original_lines[i])
            i += 1

        new_lines.extend(block_lines)

        # 删除旧链接块
        next_i, removed_paths = remove_existing_svg_link(original_lines, i)
        if next_i != i:
            changed = True

        for p in removed_paths:
            old_svg_files.add((md_dir / p).resolve())

        i = next_i

        # 简化的 SVG 命名：001.svg, 002.svg, ...
        svg_filename = f"{diagram_index:03d}.svg"
        svg_path = svg_dir / svg_filename
        used_svg_files.add(svg_path.resolve())

        mermaid_text = "".join(mermaid_body_lines).strip() + "\n"
        run_mmdc(mermaid_text, svg_path)

        # 链接路径指向子文件夹中的 SVG
        link_block = (
            "\n"
            f"{LINK_BEGIN}\n"
            f"[打开 Mermaid SVG](./{md_stem}/{svg_filename})\n"
            f"{LINK_END}\n"
        )
        new_lines.append(link_block)

        diagram_index += 1
        changed = True

    # 删除旧版本的 SVG 文件（旧的命名格式和新的格式）
    # 1. 清理旧格式的 SVG（直接放在 md 目录下）
    old_generated_pattern = f"{md_stem}_mermaid_*.svg"
    for old_svg in md_dir.glob(old_generated_pattern):
        old_svg_files.add(old_svg.resolve())

    # 2. 清理当前 SVG 目录中不再使用的旧 SVG
    for old_svg in svg_dir.glob("*.svg"):
        old_svg_files.add(old_svg.resolve())

    for old_svg in old_svg_files:
        if old_svg not in used_svg_files and old_svg.exists():
            old_svg.unlink()

    # 如果 SVG 目录为空，则删除目录；否则保留
    if svg_dir.exists() and not any(svg_dir.iterdir()):
        svg_dir.rmdir()

    if changed:
        md_file.write_text("".join(new_lines), encoding="utf-8")
        print(f"已处理: {md_file}")
    else:
        print(f"未发现 Mermaid 图: {md_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 Markdown 文件中的 Mermaid 图转换为 SVG，并在原 Mermaid 图后添加 SVG 链接。"
    )
    parser.add_argument(
        "input",
        help="输入 Markdown 文件，或包含 Markdown 文件的目录",
    )

    args = parser.parse_args()

    if not shutil.which("mmdc"):
        raise RuntimeError("未找到 mmdc 命令，请先安装 @mermaid-js/mermaid-cli。")

    # 如果未设置 PUPPETEER_EXECUTABLE_PATH，尝试自动查找
    if not os.environ.get("PUPPETEER_EXECUTABLE_PATH"):
        chrome_path = find_puppeteer_chrome()
        if chrome_path:
            os.environ["PUPPETEER_EXECUTABLE_PATH"] = chrome_path

    input_path = Path(args.input).resolve()
    md_files = find_md_files(input_path)

    for md_file in md_files:
        process_md_file(md_file)


if __name__ == "__main__":
    main()