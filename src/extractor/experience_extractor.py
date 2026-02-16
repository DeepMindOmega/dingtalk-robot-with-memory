"""
Experience Extractor implementation
"""

import json
import os
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ExperienceExtractor:
    """
    Extract experiences from various data sources.
    Supports JSON session files, text log files, and Markdown documents.
    """

    def __init__(self, output_dir: str = None):
        """
        Initialize experience extractor.

        Args:
            output_dir: Directory to save extracted experiences.
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "memories")
            output_dir = os.path.abspath(output_dir)

        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.categories = [
            "success_case",
            "failure_lesson",
            "skill_growth",
            "user_preference",
        ]

        for category in self.categories:
            category_dir = os.path.join(self.output_dir, f"{category}s")
            os.makedirs(category_dir, exist_ok=True)

        logger.info(
            f"ExperienceExtractor initialized with output_dir: {self.output_dir}"
        )

    def extract_from_json(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract experiences from JSON session file.

        Args:
            file_path: Path to JSON session file

        Returns:
            List of extracted experiences
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []

        experiences = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    exp = self._parse_json_item(item)
                    if exp:
                        experiences.append(exp)
            elif isinstance(data, dict):
                exp = self._parse_json_item(data)
                if exp:
                    experiences.append(exp)

            logger.info(f"Extracted {len(experiences)} experiences from {file_path}")
        except Exception as e:
            logger.error(f"Failed to extract from {file_path}: {e}")

        return experiences

    def extract_from_text(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract experiences from text log file.

        Args:
            file_path: Path to text log file

        Returns:
            List of extracted experiences
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []

        experiences = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = self._split_text_sections(content)
            for section in sections:
                exp = self._parse_text_section(section)
                if exp:
                    experiences.append(exp)

            logger.info(f"Extracted {len(experiences)} experiences from {file_path}")
        except Exception as e:
            logger.error(f"Failed to extract from {file_path}: {e}")

        return experiences

    def extract_from_markdown(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract experiences from Markdown document.

        Args:
            file_path: Path to Markdown document

        Returns:
            List of extracted experiences
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []

        experiences = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = re.split(r"^#{1,2}\s+", content, flags=re.MULTILINE)
            for section in sections:
                if not section.strip():
                    continue
                exp = self._parse_markdown_section(section)
                if exp:
                    experiences.append(exp)

            logger.info(f"Extracted {len(experiences)} experiences from {file_path}")
        except Exception as e:
            logger.error(f"Failed to extract from {file_path}: {e}")

        return experiences

    def _parse_json_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single JSON item into an experience.

        Args:
            item: JSON item dict

        Returns:
            Experience dict or None
        """
        if not isinstance(item, dict):
            return None

        title = item.get("title") or item.get("subject") or "Untitled"
        content = item.get("content") or item.get("description") or item.get("body", "")
        category = self._categorize_experience(content)

        if not content:
            return None

        return {
            "type": category,
            "title": title,
            "content": content,
            "source": "json",
            "tags": item.get("tags", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _split_text_sections(self, content: str) -> List[str]:
        """
        Split text content into sections.

        Args:
            content: Text content

        Returns:
            List of sections
        """
        sections = []
        current_section = []

        lines = content.split("\n")
        for line in lines:
            if line.strip() and not line.startswith("#"):
                current_section.append(line)
            elif current_section:
                sections.append("\n".join(current_section))
                current_section = []

        if current_section:
            sections.append("\n".join(current_section))

        return sections

    def _parse_text_section(self, section: str) -> Optional[Dict[str, Any]]:
        """
        Parse a text section into an experience.

        Args:
            section: Text section

        Returns:
            Experience dict or None
        """
        if len(section) < 50:
            return None

        lines = section.strip().split("\n")
        title = lines[0][:100] if lines else "Untitled"
        content = section

        category = self._categorize_experience(content)

        return {
            "type": category,
            "title": title,
            "content": content,
            "source": "text_log",
            "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _parse_markdown_section(self, section: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Markdown section into an experience.

        Args:
            section: Markdown section

        Returns:
            Experience dict or None
        """
        if len(section) < 50:
            return None

        lines = section.strip().split("\n")
        title = lines[0][:100] if lines else "Untitled"

        content = "\n".join(lines[1:]) if len(lines) > 1 else section

        category = self._categorize_experience(content)

        tags = []
        for line in lines:
            if line.startswith("Tags:") or line.startswith("标签:"):
                tag_text = line.split(":", 1)[1].strip()
                tags = [tag.strip() for tag in tag_text.split(",")]

        return {
            "type": category,
            "title": title,
            "content": content,
            "source": "markdown",
            "tags": tags,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _categorize_experience(self, content: str) -> str:
        """
        Categorize an experience based on content.

        Args:
            content: Experience content

        Returns:
            Category string
        """
        content_lower = content.lower()

        success_keywords = [
            "success",
            "成功",
            "完成",
            "worked",
            "solved",
            "solved",
            "effective",
        ]
        failure_keywords = [
            "error",
            "失败",
            "failed",
            "issue",
            "problem",
            "bug",
            "错误",
        ]
        skill_keywords = [
            "learned",
            "学习",
            "skill",
            "技能",
            "improvement",
            "提升",
            "growth",
            "growth",
        ]
        preference_keywords = ["prefer", "偏好", "style", "风格", "习惯", "habit"]

        success_score = sum(1 for kw in success_keywords if kw in content_lower)
        failure_score = sum(1 for kw in failure_keywords if kw in content_lower)
        skill_score = sum(1 for kw in skill_keywords if kw in content_lower)
        preference_score = sum(1 for kw in preference_keywords if kw in content_lower)

        scores = {
            "success_case": success_score,
            "failure_lesson": failure_score,
            "skill_growth": skill_score,
            "user_preference": preference_score,
        }

        max_category = max(scores, key=scores.get)

        if scores[max_category] == 0:
            return "success_case"

        return max_category

    def save_experience(self, experience: Dict[str, Any]) -> str:
        """
        Save an experience to file.

        Args:
            experience: Experience dict

        Returns:
            Path to saved file
        """
        category = experience["type"]
        title = experience["title"]

        safe_title = re.sub(r"[^\w\s-]", "", title).strip()
        safe_title = re.sub(r"[-\s]+", "_", safe_title)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_title}.md"

        category_dir = os.path.join(self.output_dir, f"{category}s")
        file_path = os.path.join(category_dir, filename)

        content = f"# {title}\n\n"
        content += f"**Type**: {category}\n"
        content += f"**Source**: {experience['source']}\n"
        content += f"**Created**: {experience['created_at']}\n\n"

        if experience.get("tags"):
            content += f"**Tags**: {', '.join(experience['tags'])}\n\n"

        content += "---\n\n"
        content += experience["content"]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Saved experience: {file_path}")
        return file_path

    def extract_and_save(self, file_path: str) -> List[str]:
        """
        Extract experiences from file and save to disk.

        Args:
            file_path: Path to input file

        Returns:
            List of saved file paths
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            experiences = self.extract_from_json(file_path)
        elif ext in [".txt", ".log"]:
            experiences = self.extract_from_text(file_path)
        elif ext == ".md":
            experiences = self.extract_from_markdown(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return []

        saved_paths = []
        for exp in experiences:
            try:
                path = self.save_experience(exp)
                saved_paths.append(path)
            except Exception as e:
                logger.error(f"Failed to save experience: {e}")

        return saved_paths
