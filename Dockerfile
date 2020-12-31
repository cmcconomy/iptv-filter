FROM python:3
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/
RUN IPTV_SAFE_START=1 python3 manage.py migrate
#RUN chown 1000:1000 db.sqlite3

CMD /code/run.sh
