import copy
import time
import xml.etree.ElementTree as ET
from django.shortcuts import render
from django.http import HttpResponse
from iptv_filter.models import PlaylistChannel, CachedFile, EpgChannel, EpgProgramme
from iptv_updater import iptv_updater

# import the logging library / Get an instance of a logger
import logging
logger = logging.getLogger(__name__)


def index(request):
	return HttpResponse("Hey")

def m3u_api(request):
	logger.info("Received m3u API call")
	included_channels = PlaylistChannel.objects.filter(playlist_group__included = True).exclude(included=False)
	# TODO: Doesn't include specific channels where parent excluded

	m3u = "#EXTM3U\r\n"
	for c in included_channels:
		m3u += f"#EXTINF:-1 tvg-id=\"{c.tvg_id}\" tvg-name=\"{c.tvg_name}\" tvg-logo=\"{c.tvg_logo}\" group-title=\"{c.playlist_group.group_title}\",{c.tvg_name}\r\n"
		m3u += c.stream_url + "\r\n"		

	logger.info("Responded to m3u API call")
	return HttpResponse(m3u)

def epg_old_api(request):
	epg = ET.Element('tv')

	file = CachedFile.objects.filter(file_type='epg')[0].file.decode()
	# return HttpResponse(file)
	root = ET.fromstring(file)
	tvg_ids = list(set(PlaylistChannel.objects.filter(playlist_group__included = True).exclude(included=False).values_list('tvg_id', flat=True)))
	for tvg_id in tvg_ids:
		channels = root.findall(f".//channel[@id='{tvg_id}']")
		if len(channels) > 0:
			epg.insert(0,copy.deepcopy(channels[0]))
			programmes = root.findall(f".//programme[@channel='{tvg_id}']")
			for p in programmes:
				epg.insert(0,copy.deepcopy(p))

	final_xml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
"""
	final_xml += ET.tostring(epg, encoding='unicode')

	logger.info("Responded to epg API call")
	return HttpResponse(final_xml)


def epg_api(request):
	logger.info("Received epg API call")
	epg = ET.Element('tv')

	start_perftime = time.perf_counter()
	included_channels = EpgChannel.objects.filter(playlist_channel__playlist_group__included = True).exclude(playlist_channel__included=False)
	# TODO: Doesn't include specific channels where parent excluded
	for ic in included_channels:
		channel = ET.SubElement(epg, 'channel', attrib={'id':ic.channel_id})
		display_name = ET.SubElement(channel,'display-name')
		display_name.text = ic.display_name
		if ic.icon:
			attrib={'src':ic.icon}
		else:
			attrib={}
		ET.SubElement(channel,'icon', attrib=attrib)
	print(f"Done with EPG Channels in {time.perf_counter()-start_perftime} seconds.")

	start_perftime = time.perf_counter()
	included_programmes = EpgProgramme.objects.filter(epg_channel__playlist_channel__playlist_group__included = True).exclude(epg_channel__playlist_channel__included=False)
	print(f"> Found {len(included_programmes)} EPG Channels in {time.perf_counter()-start_perftime} seconds.")
	# TODO: Doesn't include specific channels where parent excluded
	for ip in included_programmes:
		programme = ET.SubElement(epg, 'programme', attrib={'start':ip.start, 'stop':ip.stop, 'channel':ip.epg_channel.channel_id})
		title = ET.SubElement(programme,'title')
		if ip.title:
			title.text = ip.title
		desc = ET.SubElement(programme,'desc')
		if ip.desc:
			desc.text = ip.desc
	print(f"Done with EPG Programmes in {time.perf_counter()-start_perftime} seconds.")

	final_xml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
"""
	final_xml += ET.tostring(epg, encoding='unicode')

	logger.info("Responded to epg API call")
	return HttpResponse(final_xml)


def aaepg_api(request):
	logger.info("Received epg API call")
	epg = ET.Element('tv')

	included_channels = EpgChannel.objects.filter(playlist_channel__playlist_group__included = True).exclude(playlist_channel__included=False)
	# TODO: Doesn't include specific channels where parent excluded
	for ic in included_channels:
		channel = ET.SubElement(epg, 'channel', attrib={'id':ic.channel_id})
		display_name = ET.SubElement(channel,'display-name')
		display_name.text = ic.display_name
		if ic.icon:
			attrib={'src':ic.icon}
		else:
			attrib={}
		ET.SubElement(channel,'icon', attrib=attrib)

	included_programmes = EpgProgramme.objects.filter(epg_channel__playlist_channel__playlist_group__included = True).exclude(epg_channel__playlist_channel__included=False)
	# TODO: Doesn't include specific channels where parent excluded
	for ip in included_programmes:
		programme = ET.SubElement(epg, 'programme', attrib={'start':ip.start, 'stop':ip.stop, 'channel':ip.epg_channel.channel_id})
		title = ET.SubElement(programme,'title')
		if ip.title:
			title.text = ip.title
		desc = ET.SubElement(programme,'desc')
		if ip.desc:
			desc.text = ip.desc

	final_xml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
"""
	final_xml += ET.tostring(epg, encoding='unicode')

	logger.info("Responded to epg API call")
	return HttpResponse(final_xml)

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

