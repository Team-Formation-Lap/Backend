FROM python:3.9

WORKDIR /Backend

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 \
 && rm -rf /var/lib/apt/lists/*

# 필요한 패키지 설치
RUN pip install --upgrade pip
COPY requirements.txt /Backend/
RUN pip install -r requirements.txt && pip install gevent
RUN pip install python-dotenv

# 소스 코드 복사
COPY . /Backend/

# Django 프로젝트 실행
EXPOSE 8000
