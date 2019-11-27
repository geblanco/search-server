FROM python

WORKDIR /usr/app/
COPY /src /usr/app/

RUN pip install -r requirements.txt

CMD python app.py --serve
