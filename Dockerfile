# 베이스 이미지 정의
FROM python:3.9

# 작업 디렉토리 생성 및 설정
WORKDIR /Backend

# 필요한 패키지 설치
RUN pip install --upgrade pip
COPY requirements.txt /Backend/
RUN pip install -r requirements.txt && pip install gevent
RUN pip install python-dotenv

# 소스 코드 복사
COPY . /Backend/

# Django 프로젝트 실행
EXPOSE 8000

