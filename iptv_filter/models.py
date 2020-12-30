from django.db import models

# this will be configs like the URL to pull from, how often to refresh etc
class AppConfig(models.Model):
	key = models.CharField(max_length=50)
	value = models.TextField(max_length=100)
	last_updated = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return '[' + self.key + ': ' + self.value + ']' 

# Maybe we will just embed this in the channels view...
# class FilterConfig(models.Model):
	# details = models.JSONField()

class PlaylistGroup(models.Model):
	group_title = models.CharField(max_length=50)
	included = models.BooleanField(default=False, db_index=True) #None/False = no, True = yes; individual PlaylistChannels underneath can override.
	last_updated = models.DateTimeField(null=True,blank=True, db_index=True)

class PlaylistChannel(models.Model):
	playlist_group = models.ForeignKey('PlaylistGroup',on_delete=models.CASCADE)
	tvg_id = models.CharField(max_length=50)
	tvg_name = models.CharField(max_length=100)
	tvg_logo = models.TextField() #this is sometimes an embedded image, which is large.
	stream_url = models.URLField()
	last_updated = models.DateTimeField(null=True,blank=True, db_index=True)
	included = models.BooleanField(default=None,null=True, db_index=True) #None = inherit from PlaylistGroup, False = force no, True = force yes.
	constraints = [
		models.UniqueConstraint(fields=['tvg_id','tvg_name'],name="unique key for PlaylistChannel")
	]
	output_representation = models.TextField()

class EpgChannel(models.Model):
	playlist_channel = models.ForeignKey('PlaylistChannel', null=True, on_delete=models.SET_NULL) # Optional link to m3u sibling.
	channel_id = models.CharField(max_length=50)
	display_name = models.CharField(max_length=50)
	icon = models.TextField(null=True)
	last_updated = models.DateTimeField(null=True,blank=True, db_index=True)
	output_representation = models.TextField()

class EpgProgramme(models.Model):
	epg_channel = models.ForeignKey('EpgChannel',on_delete=models.CASCADE)
	start = models.CharField(max_length=20)
	stop = models.CharField(max_length=20)
	title = models.CharField(max_length=100)
	desc = models.TextField(blank=True)
	last_updated = models.DateTimeField(null=True,blank=True, db_index=True)
	output_representation = models.TextField()

class CachedFile(models.Model):
	file_type = models.TextField(max_length=5)
	file = models.BinaryField()
	last_updated = models.DateTimeField(null=True,blank=True, db_index=True)

