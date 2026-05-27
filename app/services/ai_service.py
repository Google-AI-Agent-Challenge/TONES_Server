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

    def upsert_review_vector(self, review_id: str, text: str, metadata: dict) -> bool:
        """
        리뷰 텍스트를 임베딩 벡터로 변환하여 Pinecone 벡터 DB에 업로드
        """
        vector = self._get_gemini_embedding(text)
        if vector is None:
            # 768차원 더미 벡터 생성 (로컬/오프라인 테스트용)
            print(f"[AIService] 임베딩 호출 실패, 로컬 768차원 더미 벡터 사용: {review_id}")
            # 테스트 및 오프라인 환경용 768차원 더미 리스트
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
                vector = [0.01] * 768

        if self.pinecone is not None and vector is not None:
            try:
                if settings.PINECONE_INDEX_NAME.startswith("http"):
                    index = self.pinecone.Index(host=settings.PINECONE_INDEX_NAME)
                else:
                    index = self.pinecone.Index(name=settings.PINECONE_INDEX_NAME)
                
                # Pinecone upsert
                index.upsert(vectors=[(review_id, vector, metadata)])
                print(f"[AIService] Pinecone 적재 성공: {review_id}")
                return True
            except Exception as e:
                print(f"[AIService] Pinecone 적재 실패: {e}")
                return False
        else:
            print(f"[AIService] Pinecone 미설정/오프라인 모드, 적재 건너뜀 (더미 성공 처리): {review_id}")
            return True

    def delete_review_vector(self, review_id: str) -> bool:
        """
        데이터 일관성 보장을 위해 Pinecone에서 벡터 삭제 (롤백 정책용)
        """
        if self.pinecone is not None:
            try:
                if settings.PINECONE_INDEX_NAME.startswith("http"):
                    index = self.pinecone.Index(host=settings.PINECONE_INDEX_NAME)
                else:
                    index = self.pinecone.Index(name=settings.PINECONE_INDEX_NAME)
                
                index.delete(ids=[review_id])
                print(f"[AIService] Pinecone 벡터 롤백(삭제) 성공: {review_id}")
                return True
            except Exception as e:
                print(f"[AIService] Pinecone 벡터 삭제 실패: {e}")
                return False
        else:
            print(f"[AIService] Pinecone 미설정/오프라인 모드, 삭제 건너뜀: {review_id}")
            return True

    def analyze_review_absa(self, review_text: str) -> dict:
        """
        Gemini 2.0-flash 기반의 화장품 전문 다중 속성 감성 분석 (ABSA) 실행
        API 제한이나 예외 발생 시 Gemini 1.5-flash로 폴백하며, 최종적으로 로컬 룰 엔진 작동
        """
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
            print("[AIService] Gemini API Key 미설정 (로컬 룰 ABSA 엔진 구동)")
            return self._local_heuristic_absa(review_text)

        system_instruction = (
            "당신은 화장품 전문 리뷰 분석 AI 연구원입니다. 주어진 고객 리뷰에서 다음 3대 VOC 속성에 대한 긍정 감성 점수(0.0 ~ 1.0, 1.0에 가까울수록 매우 긍정, 0.0에 가까울수록 매우 부정, 0.5는 중립) 및 메타데이터를 추출해 주세요.\n\n"
            "추출 속성:\n"
            "1. 성분/피부고민 진정 및 자극성 점수 (ingredients_skin_concerns_score)\n"
            "2. 제형/발림성/끈적임/밀림 점수 (formulation_spreadability_score)\n"
            "3. 용기/디자인/뚜껑/내부 캡 편의성 점수 (container_design_score)\n\n"
            "또한 전체 감성 판단(overall_sentiment: 'positive', 'neutral', 'negative'), 전체 감성 점수(overall_score: 0.0 ~ 1.0), 리뷰의 핵심 키워드 3~5개(keywords: array of strings), 부작용/불량 유형(issue_type: '트러블', '자극', '용기불량', '없음' 중 적절한 값), 그리고 1문장 한국어 요약(ai_summary)을 추출해야 합니다.\n\n"
            "반드시 JSON 형식으로만 응답해야 하며, 다른 어떤 마크다운 설명이나 텍스트도 포함해서는 안 됩니다. JSON 스키마는 다음과 같습니다:\n"
            "{\n"
            "  \"ingredients_skin_concerns_score\": float,\n"
            "  \"formulation_spreadability_score\": float,\n"
            "  \"container_design_score\": float,\n"
            "  \"overall_sentiment\": string,\n"
            "  \"overall_score\": float,\n"
            "  \"keywords\": [string],\n"
            "  \"issue_type\": string,\n"
            "  \"ai_summary\": string\n"
            "}"
        )

        prompt = f"분석할 고객 리뷰:\n\"\"\"\n{review_text}\n\"\"\""

        # 모델 후보군 설정 (Gemini 2.0 Flash -> 1.5 Flash)
        models = ["gemini-2.0-flash", "gemini-1.5-flash"]
        
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [{"text": f"{system_instruction}\n\n{prompt}"}]
                }]
            }
            
            try:
                with httpx.Client(timeout=15.0) as client:
                    response = client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        resp_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        
                        # JSON 파싱 시도
                        try:
                            parsed = self._parse_json(resp_text)
                            # 필수 키 유효성 검증
                            required_keys = [
                                "ingredients_skin_concerns_score", "formulation_spreadability_score", 
                                "container_design_score", "overall_sentiment", "overall_score", 
                                "keywords", "issue_type", "ai_summary"
                            ]
                            if all(k in parsed for k in required_keys):
                                print(f"[AIService] Gemini ABSA 분석 완료 ({model_name})")
                                return parsed
                        except Exception as parse_err:
                            print(f"[AIService] JSON 파싱 에러 ({model_name}): {parse_err}. 응답: {resp_text}")
                    else:
                        print(f"[AIService] Gemini ABSA API 에러 ({model_name}): {response.status_code} - {response.text}")
            except Exception as e:
                print(f"[AIService] Gemini ABSA API 예외 발생 ({model_name}): {e}")

        # 모든 모델 실패 또는 파싱 오류 시 최종 로컬 폴백
        print("[AIService] Gemini API 실패로 인해 최종 로컬 룰 ABSA 엔진 폴백 구동")
        return self._local_heuristic_absa(review_text)

    def _parse_json(self, text: str) -> dict:
        import json
        import re
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
        cleaned = cleaned.strip()
        return json.loads(cleaned)

    def _local_heuristic_absa(self, review_text: str) -> dict:
        """
        Gemini API 실패 또는 오프라인 환경용 로컬 규칙 기반 더미 ABSA 연산
        """
        pos_words = ["좋", "촉촉", "순하", "대박", "추천", "부드럽", "짱", "만족", "최고"]
        neg_words = ["자극", "아쉽", "불편", "따갑", "트러블", "좁쌀", "붉", "여드름", "밀림", "끈적"]
        
        pos_count = sum(1 for w in pos_words if w in review_text)
        neg_count = sum(1 for w in neg_words if w in review_text)
        
        overall_score = 0.5
        if pos_count > neg_count:
            overall_score = 0.8
        elif neg_count > pos_count:
            overall_score = 0.2
            
        sentiment = "neutral"
        if overall_score >= 0.7:
            sentiment = "positive"
        elif overall_score <= 0.3:
            sentiment = "negative"
            
        ingredients_score = 0.5
        formulation_score = 0.5
        container_score = 0.5
        
        if any(w in review_text for w in ["자극", "트러블", "붉", "따갑", "여드름"]):
            ingredients_score = 0.15
        elif any(w in review_text for w in ["순하", "진정"]):
            ingredients_score = 0.85
            
        if any(w in review_text for w in ["끈적", "밀림", "제형"]):
            formulation_score = 0.20
        elif any(w in review_text for w in ["촉촉", "부드럽"]):
            formulation_score = 0.90
            
        if any(w in review_text for w in ["불편", "용기", "뚜껑", "집게"]):
            container_score = 0.25
        elif any(w in review_text for w in ["디자인", "예쁘"]):
            container_score = 0.80
            
        keywords = []
        for w in pos_words + neg_words:
            if w in review_text and len(keywords) < 5:
                keywords.append(w)
                
        issues = []
        if ingredients_score < 0.3:
            issues.append("자극")
        if formulation_score < 0.3:
            issues.append("제형불만")
        if container_score < 0.3:
            issues.append("용기불편")
            
        issue_type = ", ".join(issues) if issues else "없음"
        summary = f"리뷰 요약: {review_text[:30]}..."
        
        return {
            "ingredients_skin_concerns_score": ingredients_score,
            "formulation_spreadability_score": formulation_score,
            "container_design_score": container_score,
            "overall_sentiment": sentiment,
            "overall_score": overall_score,
            "keywords": keywords if keywords else ["패드"],
            "issue_type": issue_type,
            "ai_summary": summary
        }

