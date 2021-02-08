from django.db import models

# this will be configs like the URL to pull from, how often to refresh etc
class AppConfig(models.Model):
    key = models.CharField(max_length=50)
    value = models.TextField(max_length=100)
    last_updated = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '[' + self.key + ': ' + self.value + ']' 

# Some notes about this model:
# - no foreign keys so we can do fast bulk inserts when we import source files
# - expectation is for app to manage changes to inclusion across the 3 types 

class PlaylistChannel(models.Model):
    tvg_id = models.CharField(max_length=50)
    tvg_name = models.CharField(max_length=100, db_index=True)
    tvg_logo = models.TextField() #this is sometimes an embedded image, which is large.
    stream_url = models.URLField()
    first_seen = models.DateTimeField(null=True,blank=True, db_index=True)
    last_updated = models.DateTimeField(null=True,blank=True, db_index=True)
    included = models.BooleanField(default=None,null=True, db_index=True) #None = inherit from PlaylistGroup, False = force no, True = force yes.
    constraints = [
        models.UniqueConstraint(fields=['tvg_name'],name="unique name for PlaylistChannel")
    ]
    group_title = models.CharField(max_length=50)

    def __str__(self):
        text = f"#EXTINF:-1 tvg-id=\"{self.tvg_id}\" tvg-name=\"{self.tvg_name}\" tvg-logo=\"{self.tvg_logo}\" group-title=\"{self.group_title}\",{self.tvg_name}\r\n"
        text += self.stream_url
        return text

class EpgChannel(models.Model):
    channel_id = models.CharField(max_length=50, db_index=True)
    display_name = models.CharField(max_length=50)
    icon = models.TextField(null=True)
    last_updated = models.DateTimeField(null=True,blank=True, db_index=True)
    included = models.BooleanField(default=None,null=True, db_index=True) #None = inherit from PlaylistGroup, False = force no, True = force yes.
    def __str__(self):
        text =  f'<channel id="{self.channel_id}">\n'
        text += f'  <display-name>{self.display_name}</display-name>\n'
        if self.icon:
            text += f'  <icon src="{self.icon}"/>\n'
        text += '</channel>'
        return text

class EpgProgramme(models.Model):
    start = models.CharField(max_length=20)
    stop = models.CharField(max_length=20)
    title = models.CharField(max_length=100)
    desc = models.TextField(blank=True)
    channel = models.CharField(max_length=50, db_index=True)
    last_updated = models.DateTimeField(null=True,blank=True, db_index=True)
    included = models.BooleanField(default=None,null=True, db_index=True) #None = inherit from PlaylistGroup, False = force no, True = force yes.
    def __str__(self):
        text =  f'<programme start="{self.start}" stop="{self.stop}" channel="{self.channel}">\n'
        text += f'  <title>{self.title}</title>\n'
        if self.desc:
            text += f'  <desc>{self.desc}</desc>\n'
        text += '</programme>'
        return text

class CachedFile(models.Model):
    file_type = models.TextField(max_length=5)
    file = models.BinaryField()
    last_updated = models.DateTimeField(null=True,blank=True, db_index=True)
