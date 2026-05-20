import httpx
from app.core.config import settings
from app.schemas.ai_search import SearchRequest, SearchResultItem, GenerateRequest


class AIService:
    def __init__(self, pinecone_client=None):
        self.pinecone = pinecone_client

    def _get_gemini_embedding(self, text: str) -> list[float] | None:
        """
        Gemini text-embedding-004 API를 사용하여 텍스트에 대한 임베딩 벡터 생성
        """
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
            print("[AIService] Gemini API Key가 설정되지 않았습니다. (더미 임베딩 사용)")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data["embedding"]["values"]
                else:
                    print(f"[AIService] Gemini Embedding API 오류: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[AIService] Gemini Embedding API 예외 발생: {e}")
        
        return None

    def vector_search(self, request: SearchRequest) -> list[SearchResultItem]:
        # 1. 쿼리 텍스트를 벡터 임베딩으로 변환
        query_vector = self._get_gemini_embedding(request.query)

        # 2. Pinecone 클라이언트 및 임베딩 벡터가 유효한 경우 실제 검색 수행
        if self.pinecone is not None and query_vector is not None:
            try:
                # 인덱스 이름에 URL이 포함되어 있을 경우 host 매개변수 사용, 그렇지 않으면 name 매개변수 사용
                if settings.PINECONE_INDEX_NAME.startswith("http"):
                    index = self.pinecone.Index(host=settings.PINECONE_INDEX_NAME)
                else:
                    index = self.pinecone.Index(name=settings.PINECONE_INDEX_NAME)
                
                # 시맨틱 벡터 쿼리 실행
                response = index.query(
                    vector=query_vector,
                    top_k=request.top_k,
                    include_metadata=True,
                    filter=request.filter
                )
                
                matches = response.get("matches", [])
                results = []
                for match in matches:
                    results.append(
                        SearchResultItem(
                            id=match.get("id"),
                            score=match.get("score", 0.0),
                            metadata=match.get("metadata") or {}
                        )
                    )
                print(f"[AIService] Pinecone 벡터 검색 성공: {len(results)}개 결과 반환")
                return results
            except Exception as e:
                print(f"[AIService] Pinecone 검색 실패 (오프라인 폴백 진행): {e}")

        # 3. 오프라인 폴백 처리: 키가 없거나 실패한 경우 더미 결과 반환
        print("[AIService] 오프라인 폴백: 더미 시맨틱 검색 결과를 생성합니다.")
        dummy_results = [
            SearchResultItem(
                id=f"doc_{i}",
                score=0.98 - (i * 0.05),
                metadata={
                    "title": f"Document {i}", 
                    "content": f"이것은 '{request.query}'에 대한 로컬 테스트용 {i}번째 관련 더미 문서 검색 결과입니다."
                }
            )
            for i in range(request.top_k)
        ]
        return dummy_results

    def generate_ai_answer(self, request: GenerateRequest) -> str:
        """
        Gemini 2.0-flash / 1.5-flash model API를 호출하여 컨텍스트 기반 답변 생성
        """
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
            print("[AIService] Gemini API Key가 설정되지 않았습니다. (더미 답변 생성)")
            return self._get_dummy_ai_answer(request)

        # RAG 구조에 맞는 프롬프트 템플릿 구성
        context_str = f"주어진 컨텍스트:\n{request.context}\n\n" if request.context else ""
        full_prompt = (
            f"{context_str}"
            f"질문: {request.prompt}\n\n"
            f"위의 질문에 대해 주어진 컨텍스트에 기반하여 정확하고 친절하게 한국어로 답변해 주세요."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }]
        }

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    answer = data["candidates"][0]["content"]["parts"][0]["text"]
                    print("[AIService] Gemini AI 답변 생성 성공")
                    return answer
                else:
                    # 2.0-flash 모델이 지원되지 않거나 에러 발생 시 1.5-flash로 폴백 시도
                    print(f"[AIService] Gemini 2.0-flash API 오류: {response.status_code}, 1.5-flash로 재시도합니다.")
                    fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
                    response = client.post(fallback_url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        answer = data["candidates"][0]["content"]["parts"][0]["text"]
                        return answer
                    
                    print(f"[AIService] Gemini API 전체 오류: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[AIService] Gemini Generative API 예외 발생: {e}")

        # 네트워크 예외나 에러 시 더미 폴백
        return self._get_dummy_ai_answer(request)

    def _get_dummy_ai_answer(self, request: GenerateRequest) -> str:
        context_str = f"\n주어진 컨텍스트: {request.context}" if request.context else ""
        return f"'{request.prompt}'에 대한 오프라인 폴백 AI 생성 답변입니다.{context_str}"
