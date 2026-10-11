from calendar_automation import repository, service
from config import logger

async def run_daily_lunch_block_check():
    logger.info("Running daily lunch-block check for all enabled orgs")
    settings_list = repository.list_enabled_settings()
    for settings in settings_list:
        try:
            run = await service.check_and_block_lunch(settings)
            logger.info(f"Lunch block for org {settings['organization_id']} -> {run['status']}")
        except Exception as e:
            logger.error(f"Lunch block check failed for org {settings['organization_id']}: {e}")
