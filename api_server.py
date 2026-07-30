"""
HIFIVE 자동 실습일지 관리 API 서버
- React Web UI와 auto_diary.py 사이의 브릿지 역할
- CORS 지원 및 static 파일 서빙
- 빌드된 React 정적 파일 서빙 (/web-ui/dist)
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import traceback
import requests
import subprocess
from pathlib import Path
from datetime import datetime

# 기존 모듈 임포트
try:
    import auto_diary
    import sentence_generator
except ImportError:
    # 경로 추가
    sys.path.append(str(Path(__file__).parent))
    import auto_diary
    import sentence_generator

PORT = 5000
SCRIPT_DIR = Path(__file__).parent
DIST_DIR = SCRIPT_DIR / "web-ui" / "dist"

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # CORS 헤더 추가
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        req_path = self.path.split('?')[0]
        # /AutoHifiveReview 접두사 제거 (API 및 정적 파일 호환용)
        if req_path.startswith('/AutoHifiveReview/'):
            req_path_clean = req_path[len('/AutoHifiveReview'):]
            self.path = self.path[len('/AutoHifiveReview'):]
        else:
            req_path_clean = req_path

        if self.path.startswith('/api/'):
            self.handle_api_get()
        else:
            # 정적 파일 서빙 (React 빌드 결과물)
            # 빌드 디렉토리가 있으면 거기서 서빙
            if DIST_DIR.exists():
                local_path = DIST_DIR / req_path_clean.lstrip('/')
                if req_path_clean == '/' or not local_path.exists() or local_path.is_dir():
                    self.path = '/web-ui/dist/index.html'
                else:
                    self.path = f'/web-ui/dist/{req_path_clean.lstrip("/")}'
                super().do_GET()
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html = """
                <html>
                <head><title>HIFIVE Web UI</title></head>
                <body style="font-family: sans-serif; padding: 50px; text-align: center; background: #121214; color: #fff;">
                    <h1>HIFIVE Web UI 서버가 실행 중입니다</h1>
                    <p style="color: #a1a1aa;">React Web UI가 아직 빌드되지 않았습니다.</p>
                    <p style="color: #a1a1aa;">개발 모드에서는 React dev server(http://localhost:5173)를 실행하여 접속해 주세요.</p>
                    <div style="margin-top: 20px; padding: 15px; background: #1e1e24; display: inline-block; border-radius: 8px; text-align: left;">
                        <code>cd web-ui<br/>npm run dev</code>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        req_path = self.path.split('?')[0]
        if req_path.startswith('/AutoHifiveReview/'):
            self.path = self.path[len('/AutoHifiveReview'):]

        if self.path.startswith('/api/'):
            self.handle_api_post()
        else:
            self.send_error(404, "Not Found")


    def read_json_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def handle_api_get(self):
        try:
            if self.path == '/api/config':
                config_path = SCRIPT_DIR / "config.json"
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {}
                self.send_json_response(data)

            elif self.path == '/api/credentials':
                creds_path = SCRIPT_DIR / "credentials.json"
                if creds_path.exists():
                    with open(creds_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # 비밀번호 마스킹 (실제 비밀번호는 응답에서 제외)
                    if "password" in data:
                        data["password_masked"] = "*" * len(data["password"])
                        del data["password"]
                else:
                    data = {}
                self.send_json_response(data)

            elif self.path == '/api/words':
                words = sentence_generator.load_words()
                self.send_json_response(words)

            elif self.path == '/api/logs':
                log_path = SCRIPT_DIR / "diary_log.txt"
                if log_path.exists():
                    with open(log_path, "r", encoding="utf-8") as f:
                        logs = f.read()
                else:
                    logs = "로그 파일이 존재하지 않습니다."
                self.send_json_response({"logs": logs})

            elif self.path == '/api/sentence-test':
                words = sentence_generator.load_words()
                sentences = [sentence_generator.generate_daily_content(words) for _ in range(5)]
                self.send_json_response({"sentences": sentences})

            else:
                self.send_error(404, f"Unknown API endpoint: {self.path}")

        except Exception as e:
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)

    def handle_api_post(self):
        try:
            body = self.read_json_body()

            if self.path == '/api/config':
                config_path = SCRIPT_DIR / "config.json"
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(body, f, ensure_ascii=False, indent=4)
                self.send_json_response({"success": True})

            elif self.path == '/api/credentials':
                creds_path = SCRIPT_DIR / "credentials.json"
                
                # 기존 credentials 로드해서 비밀번호가 변경되지 않았으면 기존 비밀번호 유지
                existing = {}
                if creds_path.exists():
                    try:
                        with open(creds_path, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                    except:
                        pass
                
                user_id = body.get("user_id")
                password = body.get("password")
                
                # 만약 비밀번호가 마스킹된 상태로 전송되었고 기존 비번이 있으면 기존 비번 사용
                if password == "*" * len(password) or not password:
                    password = existing.get("password", "")
                
                save_data = {
                    "user_id": user_id,
                    "password": password,
                    "saved_at": datetime.now().strftime("%Y-%m-%d")
                }
                
                with open(creds_path, "w", encoding="utf-8") as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=4)
                self.send_json_response({"success": True})

            elif self.path == '/api/words':
                words_path = SCRIPT_DIR / "words.json"
                with open(words_path, "w", encoding="utf-8") as f:
                    json.dump(body, f, ensure_ascii=False, indent=4)
                self.send_json_response({"success": True})

            elif self.path == '/api/run-diary':
                dry_run = body.get("dry_run", False)
                target_date_str = body.get("date") # YYYY-MM-DD
                
                # auto_diary.py를 서브프로세스로 실행하여 실시간 출력 확인 또는 직접 실행
                # 직접 실행하고 로그를 캡처하는 방식 사용
                import io
                from contextlib import redirect_stdout
                
                log_stream = io.StringIO()
                
                # 임시 로그 핸들러 추가
                import logging
                root_logger = logging.getLogger()
                temp_handler = logging.StreamHandler(log_stream)
                temp_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
                root_logger.addHandler(temp_handler)
                
                try:
                    if target_date_str:
                        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
                    else:
                        target_date = datetime.now()
                        
                    # 실행
                    auto_diary.run(target_date=target_date, dry_run=dry_run)
                    success = True
                    error_msg = ""
                except Exception as ex:
                    success = False
                    error_msg = str(ex)
                    traceback.print_exc(file=log_stream)
                finally:
                    root_logger.removeHandler(temp_handler)
                
                captured_logs = log_stream.getvalue()
                
                self.send_json_response({
                    "success": success,
                    "logs": captured_logs,
                    "error": error_msg
                })

            elif self.path == '/api/hifive/fetch':
                # HIFIVE API를 호출하여 데이터 가져오기 (CORS 우회 프록시)
                # credentials.json 로드
                creds_path = SCRIPT_DIR / "credentials.json"
                if not creds_path.exists():
                    return self.send_json_response({"success": False, "error": "인증 정보가 없습니다. 로그인 정보를 저장해 주세요."}, 400)
                
                with open(creds_path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
                
                session = requests.Session()
                session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                })
                
                # 로그인
                if not auto_diary.login(session, creds["user_id"], creds["password"]):
                    return self.send_json_response({"success": False, "error": "HIFIVE 로그인에 실패했습니다. 아이디와 비밀번호를 확인해 주세요."}, 401)
                
                # 실습생 정보
                trainee_info = auto_diary.get_trainee_info(session)
                if not trainee_info:
                    return self.send_json_response({"success": False, "error": "등록된 실습 이력이 없습니다."}, 400)
                
                # 기존 일지 목록
                existing = auto_diary.get_existing_entries(session, trainee_info["TRAINEE_SEQ"])
                
                # 개인정보 동의 상태 조회
                agree_status = {}
                try:
                    resp = session.post(f"{auto_diary.BASE_URL}/mobile/selectPersonalInfo.do", data={}, timeout=15)
                    agree_status = resp.json().get("DATA_LIST", {}).get("DATA_LIST", [{}])[0]
                except Exception as e:
                    print(f"개인정보 동의 조회 실패: {e}")
                
                self.send_json_response({
                    "success": True,
                    "trainee_info": trainee_info,
                    "existing_entries": existing,
                    "agree_status": agree_status
                })

            elif self.path == '/api/hifive/save-manual':
                # 실습일지 수동 저장
                trainee_seq = body.get("trainee_seq")
                week_num = int(body.get("week_num"))
                entries = body.get("entries") # [{date, day_name, content, work_flag, start_time, end_time, department}]
                
                creds_path = SCRIPT_DIR / "credentials.json"
                if not creds_path.exists():
                    return self.send_json_response({"success": False, "error": "인증 정보가 없습니다."}, 400)
                
                with open(creds_path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
                
                session = requests.Session()
                session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                })
                
                if not auto_diary.login(session, creds["user_id"], creds["password"]):
                    return self.send_json_response({"success": False, "error": "HIFIVE 로그인 실패"}, 401)
                
                # 저장
                success = auto_diary.save_diary_entry(session, trainee_seq, week_num, entries)
                if success:
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"success": False, "error": "HIFIVE 서버에 일지 저장 중 오류가 발생했습니다."}, 500)

            elif self.path == '/api/hifive/delete':
                # 실습일지 삭제
                trainee_seq = body.get("trainee_seq")
                week_num = str(body.get("week_num"))
                
                creds_path = SCRIPT_DIR / "credentials.json"
                if not creds_path.exists():
                    return self.send_json_response({"success": False, "error": "인증 정보가 없습니다."}, 400)
                
                with open(creds_path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
                
                session = requests.Session()
                session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                })
                
                if not auto_diary.login(session, creds["user_id"], creds["password"]):
                    return self.send_json_response({"success": False, "error": "HIFIVE 로그인 실패"}, 401)
                
                resp = session.post(
                    f"{auto_diary.BASE_URL}/mobile/deleteInvolvedReporting.do",
                    data={"trainee_seq": str(trainee_seq), "save_week": str(week_num)},
                    timeout=15,
                )
                
                result = resp.json()
                if result.get("result") == "y":
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"success": False, "error": result.get("resultMsg", "삭제 실패")}, 500)

            elif self.path == '/api/hifive/agree':
                # 개인정보 동의 저장
                agree1 = body.get("agree_yn1", "Y")
                agree2 = body.get("agree_yn2", "Y")
                
                creds_path = SCRIPT_DIR / "credentials.json"
                if not creds_path.exists():
                    return self.send_json_response({"success": False, "error": "인증 정보가 없습니다."}, 400)
                
                with open(creds_path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
                
                session = requests.Session()
                session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                })
                
                if not auto_diary.login(session, creds["user_id"], creds["password"]):
                    return self.send_json_response({"success": False, "error": "HIFIVE 로그인 실패"}, 401)
                
                resp = session.post(
                    f"{auto_diary.BASE_URL}/mobile/savePersonalInfo.do",
                    data={
                        "personal_info_agree_yn1": agree1,
                        "personal_info_agree_yn2": agree2
                    },
                    timeout=15,
                )
                
                # 응답 검증 (보통 200 OK)
                if resp.status_code == 200:
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"success": False, "error": f"동의 저장 실패: HTTP {resp.status_code}"}, 500)

            else:
                self.send_error(404, f"Unknown API endpoint: {self.path}")

        except Exception as e:
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)

def run_server():
    # 주소 재사용 가능하도록 설정
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), APIHandler) as httpd:
        print(f"HIFIVE 실습일지 API 서버가 포트 {PORT}에서 실행 중입니다...")
        print(f"로컬 웹 UI 접속: http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 종료합니다.")

if __name__ == "__main__":
    run_server()
