FROM manimcommunity/manim:v0.18.1

USER root
RUN pip install fastapi==0.104.1 uvicorn==0.24.0 python-multipart==0.0.6 psutil==5.9.6

WORKDIR /manim

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]