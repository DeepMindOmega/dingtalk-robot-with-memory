#!/usr/bin/env python3
"""
将 OpenCode 经验总结导入到智能记忆系统
"""

import os
import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.memory.memory_manager import MemoryManager
from src.storage.db_init import init_database


def parse_experience_file(file_path):
    """
    解析经验文件，提取关键信息

    Returns:
        dict: {title, content, category, tags}
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(file_path)

    # 提取标题（第一个 # 标题）
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else filename.replace(".md", "")

    # 提取概述部分
    overview_match = re.search(r"##\s*概述\s*\n(.*?)(?=---|\n##)", content, re.DOTALL)
    overview = overview_match.group(1).strip() if overview_match else ""

    # 提取失败经验
    failures_match = re.search(
        r"##\s*🔴\s*失败经验\s*\n(.*?)(?=##)", content, re.DOTALL
    )
    failures = failures_match.group(1).strip() if failures_match else ""

    # 提取成功经验
    successes_match = re.search(
        r"##\s*🟢\s*成功经验\s*\n(.*?)(?=##|$)", content, re.DOTALL
    )
    successes = successes_match.group(1).strip() if successes_match else ""

    # 提取其他部分
    other_sections = []
    for match in re.finditer(r"##\s+(.+?)\s*\n(.*?)(?=##|$)", content, re.DOTALL):
        section_title = match.group(1).strip()
        section_content = match.group(2).strip()
        if section_title not in ["概述", "🔴 失败经验", "🟢 成功经验"]:
            other_sections.append(f"\n### {section_title}\n{section_content}")

    # 构建内容
    content_parts = []
    if overview:
        content_parts.append(f"## 概述\n{overview}")
    if failures:
        content_parts.append(f"\n## 失败经验\n{failures}")
    if successes:
        content_parts.append(f"\n## 成功经验\n{successes}")
    if other_sections:
        content_parts.append("\n".join(other_sections))

    full_content = "\n".join(content_parts)

    # 根据文件名和内容确定分类
    if "失败" in filename or "失败" in content:
        category = "failure_lesson"
    elif "成功" in filename or "成功" in content:
        category = "success_case"
    elif "模型" in filename or "配置" in filename or "优化" in filename:
        category = "skill_growth"
    else:
        category = "general"

    # 提取标签
    tags = []
    if "DingTalk" in filename or "钉钉" in content:
        tags.append("dingtalk")
    if "OpenCode" in filename or "OpenCode" in content:
        tags.append("opencode")
    if "API" in content:
        tags.append("api")
    if "配置" in filename or "配置" in content:
        tags.append("config")
    if "安全" in filename or "安全" in content:
        tags.append("security")
    if "机器人" in filename:
        tags.append("bot")
    if "模型" in filename:
        tags.append("model")

    return {
        "title": title,
        "content": full_content,
        "category": category,
        "tags": tags,
        "source": "opencode_experience",
        "file_path": file_path,
    }


def import_experiences_from_directory(directory):
    """
    从目录导入所有经验文件

    Args:
        directory: 包含经验文件的目录路径

    Returns:
        tuple: (成功导入数, 失败数, 总数)
    """
    if not os.path.exists(directory):
        print(f"目录不存在: {directory}")
        return (0, 0, 0)

    md_files = [
        f for f in os.listdir(directory) if f.endswith(".md") and not f.startswith(".")
    ]
    total_files = len(md_files)

    print(f"找到 {total_files} 个 Markdown 文件")

    success_count = 0
    failed_count = 0

    for filename in sorted(md_files):
        file_path = os.path.join(directory, filename)
        print(f"\n处理文件: {filename}")

        try:
            experience = parse_experience_file(file_path)

            # 导入到数据库
            memory_manager = MemoryManager()
            memory_id = memory_manager.store_long_term(
                memory_type="long_term",
                title=experience["title"],
                content=experience["content"],
                tags=experience["tags"],
                source=experience["source"],
                ttl_days=365,  # 1年过期
            )

            print(f"  ✓ 导入成功 (ID: {memory_id})")
            print(f"    分类: {experience['category']}")
            print(f"    标签: {', '.join(experience['tags'])}")

            success_count += 1

        except Exception as e:
            print(f"  ✗ 导入失败: {e}")
            failed_count += 1

    return (success_count, failed_count, total_files)


def main():
    """主函数"""
    print("=" * 80)
    print("OpenCode 经验总结导入工具")
    print("=" * 80)

    # 初始化数据库
    db_path = "/home/admin/intelligent-memory-system/data/intelligent_memory.db"
    print(f"\n初始化数据库: {db_path}")
    init_database(db_path)
    print("✓ 数据库初始化完成")

    # 导入 clawdbot-experience-summary 目录
    experience_dir = "/home/admin/clawdbot-experience-summary"
    print(f"\n导入目录: {experience_dir}")

    success, failed, total = import_experiences_from_directory(experience_dir)

    # 打印总结
    print("\n" + "=" * 80)
    print("导入完成")
    print("=" * 80)
    print(f"总文件数: {total}")
    print(f"成功导入: {success}")
    print(f"导入失败: {failed}")
    print(f"成功率: {(success / total * 100) if total > 0 else 0:.1f}%")

    # 获取统计信息
    try:
        memory_manager = MemoryManager()
        stats = memory_manager.get_statistics()
        print(f"\n当前系统统计:")
        print(f"  总记忆数: {stats['total']}")
        print(f"  按类型分布: {stats['by_type']}")
        print(f"  平均分数: {stats['average_score']:.2f}")
    except Exception as e:
        print(f"\n获取统计信息失败: {e}")


if __name__ == "__main__":
    main()
