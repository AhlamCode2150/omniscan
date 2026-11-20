FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-osd libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    OMNISCAN_DATA_DIR=/home/user/data OMNISCAN_MODEL_DIR=/home/user/models \
    OMNISCAN_CORS=* TESSERACT_CMD=/usr/bin/tesseract TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
WORKDIR /home/user/app
COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY --chown=user backend backend
RUN python -c "from rapidocr import RapidOCR; RapidOCR()" || true
WORKDIR /home/user/app/backend
EXPOSE 7860
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","7860"]
