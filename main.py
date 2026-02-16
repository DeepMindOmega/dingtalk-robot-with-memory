#!/usr/bin/env python3
"""
Main entry point for Intelligent Memory System
Demonstrates Phase 1 functionality
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from scheduler.task_scheduler import TaskScheduler
from extractor.experience_extractor import ExperienceExtractor
from enhancer.agent_enhancer import AgentEnhancer
from storage.logging_config import setup_logging
from storage.db_init import get_connection

logger = setup_logging(log_level=20)


def nightly_extraction_job():
    """Simulated nightly extraction job."""
    logger.info("Starting nightly extraction job...")

    extractor = ExperienceExtractor()

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(data_dir, filename)
            logger.info(f"Processing: {filename}")
            saved_paths = extractor.extract_and_save(file_path)
            logger.info(f"Extracted {len(saved_paths)} experiences from {filename}")

    logger.info("Nightly extraction job completed")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Intelligent Memory System - Phase 1 Demo")
    logger.info("=" * 60)

    scheduler = TaskScheduler()
    scheduler.register_task_function("nightly_extraction", nightly_extraction_job)

    logger.info("\n1. Registering nightly job (23:00 daily)...")
    task_id = scheduler.add_task(
        task_type="nightly_extraction",
        priority="critical",
        schedule="0 23 * * *",
    )
    logger.info(f"   Task ID: {task_id}")

    logger.info("\n2. Checking agent performance...")
    enhancer = AgentEnhancer()
    config_suggestion = enhancer.suggest_model_config("extraction")
    logger.info(f"   Model config for extraction: {config_suggestion}")

    logger.info("\n3. Creating sample data for demonstration...")

    sample_data = {
        "title": "Demo Success Case",
        "content": "Successfully implemented the intelligent memory system with Phase 1 components. All tests passed and the system is ready for Phase 2.",
        "tags": ["memory", "extraction", "scheduling"],
    }

    import json

    sample_file = os.path.join(os.path.dirname(__file__), "data", "sample.json")
    os.makedirs(os.path.dirname(sample_file), exist_ok=True)

    with open(sample_file, "w") as f:
        json.dump([sample_data], f)

    logger.info(f"   Created: {sample_file}")

    logger.info("\n4. Running manual extraction...")
    extractor = ExperienceExtractor()
    saved_paths = extractor.extract_and_save(sample_file)

    for path in saved_paths:
        logger.info(f"   Saved: {os.path.basename(path)}")

    logger.info("\n5. Querying database...")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    task_count = cursor.fetchone()[0]
    logger.info(f"   Total tasks in database: {task_count}")
    conn.close()

    logger.info("\n6. Getting all tasks...")
    all_tasks = scheduler.get_all_tasks()
    for task in all_tasks[:5]:
        logger.info(f"   Task {task['id']}: {task['task_type']} ({task['priority']})")

    logger.info("\n" + "=" * 60)
    logger.info("Phase 1 Demo Complete!")
    logger.info("=" * 60)

    logger.info("\nNext Steps:")
    logger.info("- Run: python3 -m pytest tests/ -v (verify all tests pass)")
    logger.info("- Run: python3 test_integration.py (verify integration)")
    logger.info("- Review: README.md (architecture and usage)")
    logger.info("- Start: scheduler.start() (to enable cron scheduling)")
    logger.info("=" * 60)

    logger.info("\nNote: Scheduler not started in demo mode.")
    logger.info("To start the scheduler and enable cron jobs, call scheduler.start()")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
