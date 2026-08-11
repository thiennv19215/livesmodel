# LivestreamAgent AI

Ứng dụng development gồm FastAPI backend và React/Vite frontend, chạy cục bộ trên Windows.

## Chạy dev app

Cách nhanh nhất: nhấp đúp `START_DEV.bat` hoặc chạy:

```powershell
npm run dev
```

Launcher sẽ:

1. chạy FastAPI hot reload tại `127.0.0.1:8000`;
2. chạy Vite hot reload tại `127.0.0.1:3000`;
3. chờ health check thành công;
4. mở giao diện trong cửa sổ Chrome/Edge app-mode;
5. ghi log và PID vào `.dev/`.

Các địa chỉ dùng để test:

- App: <http://127.0.0.1:3000>
- API Swagger: <http://127.0.0.1:8000/docs>
- Scene dành cho OBS Browser Source: <http://127.0.0.1:8000/static/scene/index.html>

Dừng toàn bộ tiến trình do launcher tạo:

```powershell
npm run dev:stop
```

Hoặc nhấp đúp `STOP_DEV.bat`.

## Cài dependency lần đầu

```powershell
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

## Kiểm tra

```powershell
npm test
npm run lint
npm run build
```

## Chạy bản production local

```powershell
npm run build
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Sau khi build, backend phục vụ cả API, WebSocket và giao diện tại <http://127.0.0.1:8000>.

AI provider cần API key nếu dùng OpenAI/OpenRouter. Edge TTS, TikTok Live và nguồn HLS bên ngoài cần kết nối Internet.
