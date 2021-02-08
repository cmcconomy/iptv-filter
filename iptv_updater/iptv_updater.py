import requests
import re
import time
from datetime import timedelta
import xml.etree.ElementTree as ET
from django.db import transaction
from django.utils import timezone
from iptv_filter.models import AppConfig, CachedFile, PlaylistChannel, EpgChannel, EpgProgramme

# import the logging library / Get an instance of a logger
import logging
logger = logging.getLogger(__name__)

def update_all():
    update_m3u()
    update_epg()

def update_m3u():
    _retrieve('m3u')
    _update_tables('m3u')
    
def update_epg():
    _retrieve('epg')
    _update_tables('epg')

def update_m3u_scheduled():
    # TODO: Assuming 4am, make configurable.
    next_m3u_loadtime = timezone.now().replace(hour=4,minute=0,second=0,microsecond=0)
    while True:
        while next_m3u_loadtime < timezone.now():
            next_m3u_loadtime = next_m3u_loadtime + timedelta(days=1)

        logging.info(f"Next M3U Load scheduled for {next_m3u_loadtime}")
        time.sleep((next_m3u_loadtime-timezone.now()).total_seconds())
        update_m3u()

def update_epg_scheduled():
    # TODO: Assuming every half hour, make configurable
    next_epg_loadtime = timezone.now().replace(minute=30,second=0,microsecond=0)
    while True:
        # give us plenty of lead time
        while next_epg_loadtime < timezone.now() + timedelta(minutes=35):
            next_epg_loadtime = next_epg_loadtime + timedelta(hours=1)
        
        logging.info(f"Next EPG Load scheduled for {next_epg_loadtime}")
        time.sleep((next_epg_loadtime-timezone.now()).total_seconds())
        update_epg()


# "m3u" and "epg" for now...
def _retrieve(filetype):
    # TODO: What if there is no URL?
    configs = AppConfig.objects.filter(key=filetype+"_url")
    url = configs[0].value

    logging.info(f"Retrieving fresh {filetype} file from {url}")
    r = requests.get(url)
    now = timezone.now()

    try:
        r.raise_for_status()
        CachedFile.objects.update_or_create(file_type=filetype, defaults={'file':r.text.encode(), 'last_updated':now})
        logging.info(f"Received fresh {filetype} file, size {len(r.text.encode())}")
        return True

    except:
        return False

@transaction.atomic
def _update_tables(filetype):
    now = timezone.now()
    # TODO: what if file doesn't exist?
    file = CachedFile.objects.filter(file_type=filetype)[0].file.decode()

    if filetype == 'm3u':
        # TODO: store regex in AppConfig, as well as relative index/position of id, name, etc. in case other providers format this differently.
        infopattern = re.compile('(?i)#EXTINF:-1 tvg-id="(.*?)" tvg-name="(.*?)" tvg-logo="(.*?)" group-title="(.*?)",(.*?)')
        urlpattern = re.compile('(?i)^http')

        existing_channels = dict(PlaylistChannel.objects.values_list('tvg_name', 'first_seen'))
        included_channels = set(PlaylistChannel.objects.filter(included=True).values_list('tvg_name', flat=True))
        PlaylistChannel.objects.all().delete()

        start_perftime = time.perf_counter()
        new_channels = []
        for line in file.splitlines():
            m = infopattern.findall(line)
            if len(m) > 0:
                # This was an #EXTINF line.
                tvg_name = m[0][1]

                if tvg_name in existing_channels:
                    included = tvg_name in included_channels
                    first_seen = existing_channels[tvg_name]
                else:
                    # TODO: Whitelists/blacklists for whether to include newly found channels (movies/tv series probably)
                    included = False
                    first_seen = now

                pc = PlaylistChannel(tvg_id=m[0][0], tvg_name=tvg_name, tvg_logo=m[0][2], group_title=m[0][3], last_updated=now, first_seen=first_seen, included=included)
                # save after we parse the URL on the next line.

            else:
                if urlpattern.match(line):
                    # This is the URL line.
                    pc.stream_url = line
                    # pc.output_representation = _map_m3u_channel(pc)
                    new_channels.append(pc)
        PlaylistChannel.objects.bulk_create(new_channels)
        logging.info(f"Done with Channels in {time.perf_counter()-start_perftime} seconds.")

    elif filetype == 'epg':
        root = ET.fromstring(file)

        included_channel_ids = set(PlaylistChannel.objects.filter(included=True).values_list('tvg_id', flat=True))

        start_perftime = time.perf_counter()
        new_channels=[]
        channels = root.findall('.//channel')
        EpgChannel.objects.all().delete()
        for channel in channels:
            ch_id = channel.get('id')
            if not ch_id or len(ch_id) == 0:
                continue

            for child in channel:
                if child.tag == 'display-name':
                    display_name = child.text
                elif child.tag == 'icon':
                    icon = child.get('src')

            new_channels.append(EpgChannel(channel_id=channel.get('id'), display_name= display_name, icon=icon, included=channel.get('id') in included_channel_ids, last_updated=now))
        EpgChannel.objects.bulk_create(new_channels)
        logging.info(f"Done with EPG Channels in {time.perf_counter()-start_perftime} seconds.")

        start_perftime = time.perf_counter()
        new_programmes=[]
        programmes = root.findall('.//programme')
        EpgProgramme.objects.exclude(last_updated=now).delete()
        for programme in programmes:
            ch_id = programme.get('channel')
            if not ch_id or len(ch_id) == 0:
                continue

            start = programme.get('start')
            stop = programme.get('stop')

            for child in programme:
                if child.tag == 'title':
                    title = child.text or ''
                elif child.tag == 'desc':
                    desc = child.text or ''

            if not desc:
                desc = ''

            new_programmes.append(EpgProgramme(channel=ch_id, start=start, stop=stop, title=title, desc=desc, included=ch_id in included_channel_ids, last_updated=now))
        EpgProgramme.objects.bulk_create(new_programmes)
        logging.info(f"Done with EPG Programmes in {time.perf_counter()-start_perftime} seconds.")

    return True
