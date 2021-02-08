# iptv-filter

I was sick of trying to parse through 13000+ "Channels" on an IPTV service so I decided to write this and share it.
I've never used Django before (and I'm a python beginner) so I'm sure there is improvement available in the codebase.

# Concept
This application pulls an m3u file and an epg file and stores their components in a database; users tag the groups they wish to subscribe to within that subset and the app serves up an m3u file on the fly composed of the segments that are included.

# Launching iptv-filter
There are two options for running this: Docker, and Plain Python.
In both cases you will setting up the prerequisite libraries and initial backing database via the below commands.

## Docker
### Initialization

* Run `docker-compose build` to build the application
* Edit `docker-compose.yml` and insert your own personal URLs for retrieving the M3U and EPG files.  

### Running

Run the container: `docker-compose up`

## Python

### Linux 

#### Initialization

* Install `python3 python3-pip git` via `apt`/`yum`/whatever package manager
* Clone this repo into a folder
* `cd` into the new folder (`iptv-filter` by default)
* From the root folder, run `pip3 install -r requirements.txt`
* Run `IPTV_SAFE_START=1 python3 manage.py migrate`

#### Running

* `export IPTV_M3U_URL="<your_m3u_url>"`
* `export IPTV_EPG_URL="<your_epg_url>"`
* `python3 manage.py runserver 0:8000 --noreload` (this is what `./run.sh` does)

#### Upgrading

* `IPTV_SAFE_START=1 python3 manage.py makemigrations`
* `IPTV_SAFE_START=1 python3 manage.py migrate`

### Windows

#### Initialization

* Install python 3 via `apt`/`yum`/whatever package manager
* From the root folder, run `pip3 install -r requirements.txt`
* `SET IPTV_SAFE_START=1`
* `python manage.py migrate`
* `SET IPTV_SAFE_START=`

### Running

* `SET IPTV_M3U_URL="<your_m3u_url>"`
* `SET IPTV_EPG_URL="<your_epg_url>"`
* `python manage.py runserver 0:8000 --noreload`

#### Upgrading

* `SET IPTV_SAFE_START=1`
* `python manage.py makemigrations`
* `python manage.py migrate`
* `SET IPTV_SAFE_START=`

# Scheduled retrieval

* When launched, the application will pull the latest m3u and epg files. Depending on your host this could take over 20 minutes.
* The logs will indicate when the M3U file and then the EPG file have completed loading
* Once this is complete, use the API's below.
* M3U are otherwise scheduled to reload at 4AM every day
* EPG are scheduled to be loaded on the half-hour, every hour (1:30, 2:30, ...)

# API URLs

(Assuming you want to access this from the same box, you'll be using 'localhost' as the URL)
The following are the common URLs to use:
* http://localhost:8000/ - RUN THIS FIRST - This page allows you to adjust per-channel subscription. Changes are applied immediately.
* http://localhost:8000/configure - set up the included groups whose channels you will be watching (Hit submit at the bottom of the page). Older interface but useful for managing entire groups at a time.
* http://localhost:8000/m3u - the m3u file your IPTV player should point to
* http://localhost:8000/epg - the epg file your IPTV player should point to

These are utility URLs and probably won't be needed.
* http://localhost:8000/retrieve/m3u - force an immediate m3u retrieval
* http://localhost:8000/retrieve/epg - force an immediate epg retrieval
* http://localhost:8000/update/m3u - force an immediate m3u metadata table update
* http://localhost:8000/update/epg - force an immediate epg metadata table update

