from django.shortcuts import render
from django.http import HttpResponse
from iptv_filter.models import PlaylistChannel

def index(request):
	return HttpResponse("Hey")

def m3u_api(request):
	included_channels = PlaylistChannel.objects.filter(playlist_group__included = True).exclude(included=False)

	m3u = "#EXTM3U\n"
	for c in included_channels:
		m3u += f"#EXTINF:-1 tvg-id=\"{c.tvg_id}\" tvg-name=\"{c.tvg_name}\" tvg-logo=\"{c.tvg_logo}\" group-title=\"{c.playlist_group.group_title}\",{c.tvg_name}\n"
		m3u += c.stream_url + "\n"		

	return HttpResponse(m3u)
