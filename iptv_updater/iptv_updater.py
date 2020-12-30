import requests
import re
import time
import xml.etree.ElementTree as ET
from django.db import transaction
from django.utils import timezone
from iptv_filter.models import AppConfig, CachedFile, PlaylistChannel, PlaylistGroup, EpgChannel, EpgProgramme

# "m3u" and "epg" for now...
def _retrieve(filetype):
	configs = AppConfig.objects.filter(key=filetype+"_url")
	r = requests.get(configs[0].value)
	now = timezone.now()

	try:
		r.raise_for_status()
		CachedFile.objects.update_or_create(file_type=filetype, defaults={'file':r.text.encode(), 'last_updated':now})
		return True

	except:
		return False


def _map_m3u_channel(channel):
	text = f"#EXTINF:-1 tvg-id=\"{channel.tvg_id}\" tvg-name=\"{channel.tvg_name}\" tvg-logo=\"{channel.tvg_logo}\" group-title=\"{channel.playlist_group.group_title}\",{channel.tvg_name}\r\n"
	text += channel.stream_url + "\r\n"
	return text

def _map_epg_channel(channel):
	text =  f'<channel id="{channel.channel_id}">\n'
	text += f'  <display-name>{channel.display_name}</display-name>\n'
	if channel.icon:
		text += f'  <icon src="{channel.icon}"/>\n'
	text += '</channel>'
	return text

def _map_epg_programme(programme):
	text =  f'<programme start="{programme.start}" stop="{programme.stop}" channel="{programme.epg_channel.channel_id}">\n'
	text += f'  <title>{programme.title}</title>\n'
	if programme.desc:
		text += f'  <desc>{channel.desc}</desc>\n'
	text += '</programme>'
	return text

@transaction.atomic
def _update_tables(filetype):
	now = timezone.now()
	# TODO: what if file doesn't exist?
	file = CachedFile.objects.filter(file_type=filetype)[0].file.decode()
	if filetype == 'm3u':
		# TODO: store regex in AppConfig, as well as relative index/position of id, name, etc. in case other providers format this differently.
		infopattern = re.compile('#EXTINF:-1 tvg-id="(.*?)" tvg-name="(.*?)" tvg-logo="(.*?)" group-title="(.*?)",(.*?)')
		urlpattern = re.compile('^http')

		# two passes for faster transaction bulk:
		pgs = []
		start_perftime = time.perf_counter()
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
		i=1
		total=len(pgs)
		for line in file.splitlines():
			if i%1000 == 0:
				print(f'{i}/{total}')
			i += 1

			m = infopattern.findall(line)
			if len(m) > 0:
				# This was an #EXTINF line.
				pg = pgs.pop(0)

				pc, created = PlaylistChannel.objects.update_or_create( tvg_id=m[0][0], tvg_name=m[0][1], \
					defaults={'tvg_logo':m[0][2], 'playlist_group':pg, 'last_updated':now})
				# pc.save()

				# result = PlaylistChannel.objects.filter(tvg_id=m[0][0], tvg_name=m[0][1])
				# if len(result) == 0:
				# 	pc = PlaylistChannel(tvg_id=m[0][0], tvg_name=m[0][1])
				# else:
				# 	pc = result[0]

				# pc.tvg_logo=m[0][2]
				# pc.playlist_group=pg
				# pc.last_updated=now
				# save after we parse the URL on the next line.

			else:
				if urlpattern.match(line):
					# This is the URL line.
					pc.stream_url = line
					pc.output_representation = _map_m3u_channel(pc)
					pc.save()

		print(f"Done with Channels in {time.perf_counter()-start_perftime} seconds.")
		PlaylistChannel.objects.exclude(last_updated=now).delete()

	elif filetype == 'epg':
		root = ET.fromstring(file)
		start_perftime = time.perf_counter()

		channels = root.findall('.//channel')
		for channel in channels:
			ch_id = channel.get('id')
			if not ch_id or len(ch_id) == 0:
				continue

			m3u_chs = PlaylistChannel.objects.filter(tvg_id=ch_id)
			if m3u_chs and len(m3u_chs) == 1:
				m3u_ch = m3u_chs[0]
			else:
				m3u_ch = None

			for child in channel:
				if child.tag == 'display-name':
					display_name = child.text
				elif child.tag == 'icon':
					icon = child.get('src')

			ch, created = EpgChannel.objects.update_or_create(channel_id=channel.get('id'), defaults={'playlist_channel':m3u_ch, 'display_name': display_name, 'icon': icon, 'last_updated':now})
			ch,output_representation = _map_epg_channel(ch)
			ch.save()
		EpgChannel.objects.exclude(last_updated=now).delete()
		print(f"Done with EPG Channels in {time.perf_counter()-start_perftime} seconds.")

		start_perftime = time.perf_counter()
		programmes = root.findall('.//programme')
		for programme in programmes:
			ch_id = programme.get('channel')
			if not ch_id or len(ch_id) == 0:
				continue

			chs = EpgChannel.objects.filter(channel_id=ch_id)
			if chs and len(chs)==1:
				ch = chs[0]
			else:
				ch = None

			start = programme.get('start')
			stop = programme.get('stop')

			for child in programme:
				if child.tag == 'title':
					title = child.text or ''
				elif child.tag == 'desc':
					desc = child.text or ''

			if not desc:
				desc = ''

			# print(f"Insert/creating {ch_id} - '{title}' > '{desc}'")
			pr, created = EpgProgramme.objects.update_or_create(epg_channel=ch, start=start, stop=stop, defaults={'title':title, 'desc':desc, 'last_updated':now})
			pr.output_representation = _map_epg_programme(pr)
			pr.save()
		EpgProgramme.objects.exclude(last_updated=now).delete()
		print(f"Done with EPG Programmes in {time.perf_counter()-start_perftime} seconds.")

	return True










	
