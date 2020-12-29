import requests
import re
import time
from django.db import transaction
from django.utils import timezone
from iptv_filter.models import AppConfig, CachedFile, PlaylistChannel, PlaylistGroup

# "m3u" and "epg" for now...
def _retrieve(filetype):
	configs = AppConfig.objects.filter(key=filetype+"_url")
	r = requests.get(configs[0].value)

	try:
		r.raise_for_status()
		CachedFile.objects.update_or_create(file_type=filetype, file=r.text.encode())
		return True

	except:
		return False


# @transaction.atomic
def _update_tables(filetype):
	now = timezone.now()
	file = CachedFile.objects.filter(file_type=filetype)[0].file.decode()
	if filetype == 'm3u':
		# TODO: store regex in AppConfig, as well as relative index/position of id, name, etc. in case other providers format this differently.
		infopattern = re.compile('#EXTINF:-1 tvg-id="(.*?)" tvg-name="(.*?)" tvg-logo="(.*?)" group-title="(.*?)",(.*?)')
		urlpattern = re.compile('^http')

		# two passes for faster transaction bulk:
		pgs = []
		start_perftime = time.perf_counter()
		with transaction.atomic():
			for line in file.splitlines():
				m = infopattern.findall(line)
				if len(m) > 0:
					# This was an #EXTINF line.
					pg, created = PlaylistGroup.objects.get_or_create(group_title=m[0][3], defaults={'last_updated':now})

					# result = PlaylistGroup.objects.filter(group_title=m[0][3])
					# if len(result) == 0:
					# 	pg = PlaylistGroup(group_title=m[0][3])
					# else:
					# 	pg = result[0]

					# pg.last_updated = now
					# pg.save()
					pgs.append(pg)

		print(f"Done with Groups in {time.perf_counter()-start_perftime} seconds.")
		PlaylistGroup.objects.exclude(last_updated=now).delete()

		start_perftime = time.perf_counter()
		with transaction.atomic():
			for line in file.splitlines():
				m = infopattern.findall(line)
				if len(m) > 0:
					# This was an #EXTINF line.
					pg = pgs.pop(0)
					pc, created = PlaylistChannel.objects.update_or_create( tvg_id=m[0][0], tvg_name=m[0][1], \
						defaults={'tvg_logo':m[0][2], 'playlist_group':pg, 'last_updated':now})

					# pg = pgs.pop(0)

					# result = PlaylistChannel.objects.filter(tvg_id=m[0][0], tvg_name=m[0][1])
					# if len(result) == 0:
					# 	pc = PlaylistChannel(tvg_id=m[0][0], tvg_name=m[0][1])
					# else:
					# 	pc = result[0]

					# pc.tvg_logo=m[0][2]
					# pc.playlist_group=pg
					# save after we parse the URL on the next line.

				else:
					if urlpattern.match(line):
						# This is the URL line.
						pc.stream_url = line
						# pc.last_updated=now
						pc.save()

		print(f"Done with Channels in {time.perf_counter()-start_perftime} seconds.")
		PlaylistChannel.objects.exclude(last_updated=now).delete()

	# elif filetype == 'epg':

	
@transaction.atomic
def _update_tables2(filetype):
	now = timezone.now()
	file = CachedFile.objects.filter(file_type=filetype)[0].file.decode()
	if filetype == 'm3u':
		# TODO: store regex in AppConfig, as well as relative index/position of id, name, etc. in case other providers format this differently.
		infopattern = re.compile('#EXTINF:-1 tvg-id="(.*?)" tvg-name="(.*?)" tvg-logo="(.*?)" group-title="(.*?)",(.*?)')
		urlpattern = re.compile('^http')
		for line in file.splitlines():
			m = infopattern.findall(line)
			if len(m) > 0:
				# This was an #EXTINF line.
				pg, created = PlaylistGroup.objects.get_or_create(group_title=m[0][3], defaults={'last_updated':now})
				pc, created = PlaylistChannel.objects.update_or_create( tvg_id=m[0][0], tvg_name=m[0][1], \
					defaults={'tvg_logo':m[0][2], 'playlist_group':pg, 'last_updated':now})

			else:
				if urlpattern.match(line):
					# This is the URL line.
					pc.stream_url = line
					pc.save()

	# elif filetype == 'epg':

