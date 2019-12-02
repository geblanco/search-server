FROM python

WORKDIR /usr/app/
COPY /src /usr/app/

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "app.py", "--serve"]
