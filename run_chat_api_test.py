import httpx

def test_chat_api():
    login_url = "http://localhost:8080/api/auth/login"
    chat_url = "http://localhost:8080/api/ai/chat"
    
    # 1. 로그인하여 토큰 획득
    login_payload = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    print("[1] 로그인 시도 중...")
    resp = httpx.post(login_url, json=login_payload, timeout=10.0)
    if resp.status_code != 200:
        print(f"로그인 실패: {resp.status_code} - {resp.text}")
        return
        
    token = resp.json()["access_token"]
    print(f"로그인 성공! 토큰 획득 완료.")
    
    # 2. chat API 호출 (product_id="all" 전송)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    chat_payload = {
        "message": "이번달 당근 패드 트러블 부정 리뷰 분석해줘",
        "product_id": "all"
    }
    
    print("\n[2] /api/ai/chat API 호출 중 (product_id='all' 전송)...")
    chat_resp = httpx.post(chat_url, json=chat_payload, headers=headers, timeout=60.0)
    
    print(f"응답 코드: {chat_resp.status_code}")
    if chat_resp.status_code == 200:
        data = chat_resp.json()
        print("\n[성공] AI 어시스턴트 응답 수신 성공:")
        print(data.get("answer"))
        print("\n참조된 리뷰 개수:", len(data.get("referenced_reviews", [])))
    else:
        print(f"[실패] API 에러 발생: {chat_resp.text}")

if __name__ == "__main__":
    test_chat_api()
