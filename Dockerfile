FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    sox \
    libcairo2-dev \
    libpango1.0-dev \
    texlive \
    texlive-latex-extra \
    texlive-fonts-extra \
    texlive-latex-recommended \
    texlive-science \
    tipa \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]