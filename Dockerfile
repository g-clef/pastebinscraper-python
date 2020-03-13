FROM python:3
ADD pastebinscrapev2.py /
ADD requirements.txt /
ADD pastebinscrapev2.conf /
RUN pip3 install -r requirements.txt
CMD ["python", "./pastebinscrapev2.py"]
