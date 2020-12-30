from django.apps import AppConfig

# import the logging library / Get an instance of a logger
import logging
import sys


def init_logger():
    logger = logging.getLogger(__name__)

    h = logging.StreamHandler(sys.stdout)
    h.flush = sys.stdout.flush
    logger.addHandler(h)

    return logger

logger = init_logger()

class IptvFilterConfig(AppConfig):
	name = 'iptv_filter'
	
	# Respond to environment variables (for docker-friendly configuration)
	# If you see this run twice(!) you must run 'runserver' with --noreload so a second thread isnt launched for reloading!
	def ready(self):
		import os
		from django.utils import timezone
		from .models import AppConfig as AppConfigModel
		from iptv_updater import iptv_updater

		m3u_url = os.getenv('IPTV_M3U_URL')
		epg_url = os.getenv('IPTV_EPG_URL')

		if m3u_url:
			logging.info("Startup - Setting M3U URL as per environment variable")
			ac = AppConfigModel(key='m3u_url', value=m3u_url, last_updated=timezone.now())
			ac.save()

		if epg_url:
			logging.info("Startup - Setting EPG URL as per environment variable")
			ac = AppConfigModel(key='epg_url', value=epg_url, last_updated=timezone.now())
			ac.save()

		return

		# This may be temporary as I move this to a scheduler (?)
		logging.info("Startup - Retrieving latest M3U file.")
		iptv_updater._retrieve('m3u')
		logging.info("Startup - Retrieving latest EPG file.")
		iptv_updater._retrieve('epg')

		logging.info("Startup - Parsing M3U file.")
		iptv_updater._update_tables('m3u')
		logging.info("Startup - Startup tasks complete.")



