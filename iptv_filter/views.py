import copy
import time
import json
import xml.etree.ElementTree as ET
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Count
from django.core import serializers
from iptv_filter.models import PlaylistChannel, CachedFile, EpgChannel, EpgProgramme, AppConfig
from iptv_updater import iptv_updater
from django.utils import timezone
from django.utils.dateparse import parse_datetime


# import the logging library / Get an instance of a logger
import logging
logger = logging.getLogger(__name__)

def playlistChannel2json(pc, last_visit):
    if 'first_seen' in pc:
        new = pc['first_seen'] > last_visit
    else:
        new = True

    return {
        'pk': pc['pk'],
        'group_title': pc['group_title'],
        'tvg_id': pc['tvg_id'],
        'tvg_name' : pc['tvg_name'],
        'included' : pc['included'],
        'new' : new
    }

def channel_api(request, id=-1):
    print(request.method)
    if request.method == 'GET':
        ac_lv = AppConfig.objects.filter(key='last_visit')
        if len(ac_lv) > 0:
            last_visit = parse_datetime(ac_lv[0].value)
        else:
            last_visit = timezone.now()

        objs = PlaylistChannel.objects.all().values('pk','group_title','tvg_id','tvg_name', 'included', 'first_seen')
        payload = json.dumps(list(map(lambda obj: playlistChannel2json(obj,last_visit), objs)))

        AppConfig.objects.update_or_create(key='last_visit', defaults={'value':timezone.now(), 'last_updated':timezone.now()})

        return HttpResponse(payload)

    # I wanted this to be a PUT but Django doesnt support it??
    elif request.method == 'POST':
        if id != -1:
            chs = PlaylistChannel.objects.filter(pk=id)
            if len(chs) == 1:
                ch = chs[0]
                changeset = json.loads(request.body)
                ch.included = changeset['included']
                ch.save()

        # TODO: Throw+catch exceptions (eg. bad key) and respond appropriately
        # TODO: Error class for consistent json responses?
        return HttpResponse(json.dumps({'result':'success'}))

def index(request):
    return render(request, 'iptv_filter/index.html')

def m3u_api(request):
    logger.info("Received m3u API call")
    included_channels = PlaylistChannel.objects.filter(included = True)

    m3u = "#EXTM3U\r\n"
    for c in included_channels:
        m3u += str(c) + "\r\n"

    logger.info("Responded to m3u API call")
    return HttpResponse(m3u)

def epg_api(request):
    logger.info("Received epg API call")
    epg = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv>
"""
    included_channels = EpgChannel.objects.filter(included = True)
    for c in included_channels:
        epg += str(c).replace('&', '&amp;') + "\r\n"

    included_programmes = EpgProgramme.objects.filter(included = True)
    for p in included_programmes:
        epg += str(p).replace('&', '&amp;') + "\r\n"

    epg += "</tv>"
    logger.info("Responded to epg API call")
    return HttpResponse(epg, content_type="text/xml")

def configure(request):
    if request.method == 'GET':
        group_includes = list(PlaylistChannel.objects.order_by('group_title').distinct().values('group_title','included'))
        
        gcs = PlaylistChannel.objects.all().values('group_title').annotate(count=Count('id'))
        group_counts = {}
        for gc in gcs:
            group_counts[gc['group_title']] = gc['count']

        prev_gi = None
        gi_to_remove=[]
        for gi in group_includes:
            gi['label'] = f"{gi['group_title']} ({group_counts[gi['group_title']]} channels)"

            if prev_gi is None:
                prev_gi = gi
                continue

            if gi.get('group_title') == prev_gi.get('group_title'):
                if prev_gi.get('included'):
                    gi_to_remove.append(gi)
                else:
                    gi_to_remove.append(prev_gi)

            prev_gi = gi

        for extra_gi in gi_to_remove:
            group_includes.remove(extra_gi)

        return render(request, 'iptv_filter/select_groups.html', {'group_includes':group_includes})

    elif request.method == 'POST':
        start_perftime = time.perf_counter()

        PlaylistChannel.objects.all().update(included=False)
        EpgChannel.objects.all().update(included=False)
        EpgProgramme.objects.all().update(included=False)

        for group_name in request.POST:
            if group_name == 'csrfmiddlewaretoken':
                continue

            logger.info(f'About to include items for group "{group_name}"')
            channels_by_group = PlaylistChannel.objects.filter(group_title=group_name)
            channels_by_group.update(included=True)

            for channel in list(set(channels_by_group.values_list('tvg_id', flat=True))):
                EpgChannel.objects.filter(channel_id=channel).update(included=True)
                EpgProgramme.objects.filter(channel=channel).update(included=True)

        return HttpResponse(f'Updated channels in {time.perf_counter()-start_perftime} seconds.')


# ---------------------------------------------
# These are to allow forcing an action.

def _retrieve_m3u(request):
    start_perftime = time.perf_counter()
    iptv_updater._retrieve('m3u')
    return HttpResponse(f'Completed in {time.perf_counter()-start_perftime} seconds.')

def _retrieve_epg(request):
    start_perftime = time.perf_counter()
    iptv_updater._retrieve('epg')
    return HttpResponse(f'Completed in {time.perf_counter()-start_perftime} seconds.')

def _update_m3u_tables(request):
    start_perftime = time.perf_counter()
    iptv_updater._update_tables('m3u')
    return HttpResponse(f'Completed in {time.perf_counter()-start_perftime} seconds.')

def _update_epg_tables(request):
    start_perftime = time.perf_counter()
    iptv_updater._update_tables('epg')
    return HttpResponse(f'Completed in {time.perf_counter()-start_perftime} seconds.')