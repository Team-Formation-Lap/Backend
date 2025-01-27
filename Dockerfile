# Python 기반 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 로컬 코드 복사
COPY . /app

# 의존성 설치
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 애플리케이션 실행 포트
EXPOSE 8000

# FastAPI 실행 명령
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
