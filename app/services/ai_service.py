import httpx
from app.core.config import settings
from app.schemas.ai_search import SearchRequest, SearchResultItem, GenerateRequest

# GCP Vertex AI SDK 모듈 동적 임포트 준비 (의존성 에러 방지용)
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    from vertexai.language_models import TextEmbeddingModel
    HAS_VERTEX_SDK = True
except ImportError:
    HAS_VERTEX_SDK = False

_vertex_initialized = False


def _init_vertex_ai():
    """
    GCP Vertex AI SDK 환경 초기화.
    비용이 저렴한 us-central1 (아이오와) 리전을 기본값으로 탑재하고, 
    GCP Project ID가 없을 경우 초기화를 우회하여 로컬/과도기 모드로 자동 기동합니다.
    """
    global _vertex_initialized
    if not HAS_VERTEX_SDK:
        return False
        
    if not _vertex_initialized:
        project_id = getattr(settings, "GCP_PROJECT_ID", None)
        region = getattr(settings, "GCP_REGION", "us-central1") # 사용자가 지정한 가성비 최적 us-central1 적용

        if project_id and not project_id.startswith("your-"):
            try:
                vertexai.init(project=project_id, location=region)
                _vertex_initialized = True
                print(f"[AIService] Vertex AI SDK 초기화 성공: {project_id} ({region})")
            except Exception as e:
                print(f"[AIService] Vertex AI SDK 초기화 실패: {e}")
        else:
            print("[AIService] GCP Project ID가 설정되지 않아 Vertex SDK 초기화를 생략합니다.")
            
    return _vertex_initialized


class AIService:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def _get_gemini_embedding(self, text: str) -> list[float] | None:
        """
        GCP Vertex AI Embedding API (text-embedding-004)를 활용한 임베딩 생성.
        SDK 미설정 또는 실패 시, 기존 Generative Language HTTP API 및 로컬 더미 벡터로 삼중 폴백합니다.
        """
        # 1. GCP Vertex AI SDK 적용 시도
        if _init_vertex_ai():
            try:
                model = TextEmbeddingModel.from_pretrained("text-embedding-004")
                embeddings = model.get_embeddings([text])
                print("[AIService] Vertex AI Embedding 추출 성공")
                return embeddings[0].values
            except Exception as e:
                print(f"[AIService] Vertex AI Embedding API 호출 실패 (HTTP 폴백 진행): {e}")

        # 2. 과도기용 HTTP API 호출 폴백
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
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
            except Exception as http_err:
                print(f"[AIService] Gemini HTTP Embedding API 실패: {http_err}")
        
        return None

    def vector_search(self, request: SearchRequest) -> list[SearchResultItem]:
        # 1. 쿼리 텍스트를 벡터 임베딩으로 변환
        query_vector = self._get_gemini_embedding(request.query)

        # 2. GCP Cloud SQL PostgreSQL + pgvector를 활용한 실시간 시맨틱 RAG 검색 수행
        if self.conn is not None and query_vector is not None:
            try:
                cursor = self.conn.cursor()
                vector_str = f"[{','.join(map(str, query_vector))}]"
                
                # 동적 필터 조건 수립 (예: {"product_id": "xxx"})
                where_clauses = ["embedding IS NOT NULL"]
                params = [vector_str]
                
                if request.filter and "product_id" in request.filter:
                    where_clauses.append("product_id = %s")
                    params.append(request.filter["product_id"])
                
                where_str = f"WHERE {' AND '.join(where_clauses)}"
                
                # pgvector 코사인 거리 연산자(<=>) 기반 시맨틱 검색 쿼리 작성 (ASC 정렬 시 유사도가 높은 순)
                sql = f"""
                    SELECT id, review_text, rating, review_date, sentiment, issue_type, ai_summary,
                           (1 - (embedding <=> %s::vector)) AS similarity
                    FROM public.reviews
                    {where_str}
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT %s
                """
                
                params.extend([vector_str, request.top_k])
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                
                results = []
                for row in rows:
                    review_id = str(row[0])
                    review_text = row[1]
                    rating = row[2]
                    review_date = str(row[3])
                    sentiment = str(row[4])
                    issue_type = row[5] or ""
                    ai_summary = row[6] or ""
                    score = float(row[7] or 0.0)
                    
                    results.append(
                        SearchResultItem(
                            id=review_id,
                            score=score,
                            metadata={
                                "review_text": review_text,
                                "rating": rating,
                                "review_date": review_date,
                                "sentiment": sentiment,
                                "issue_type": issue_type,
                                "ai_summary": ai_summary
                            }
                        )
                    )
                
                print(f"[AIService] Cloud SQL pgvector 시맨틱 검색 성공: {len(results)}개 결과 반환")
                return results
                
            except Exception as e:
                print(f"[AIService] Cloud SQL pgvector 시맨틱 검색 실패 (오프라인 폴백 진행): {e}")

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
        GCP Vertex AI GenerativeModel (gemini-2.0-flash)을 통한 맥락 기반 답변 생성.
        장애 및 에러 시, gemini-1.5-flash 모델 폴백 및 기존 HTTP API로 전환됩니다.
        """
        # RAG 구조에 맞는 프롬프트 템플릿 구성
        context_str = f"주어진 컨텍스트:\n{request.context}\n\n" if request.context else ""
        full_prompt = (
            f"{context_str}"
            f"질문: {request.prompt}\n\n"
            f"위의 질문에 대해 주어진 컨텍스트에 기반하여 정확하고 친절하게 한국어로 답변해 주세요."
        )

        # 1. GCP Vertex AI SDK 적용 시도
        if _init_vertex_ai():
            try:
                model = GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(full_prompt)
                print("[AIService] Vertex AI Gemini 2.0-flash 답변 생성 성공")
                return response.text
            except Exception as e:
                print(f"[AIService] Vertex AI Gemini 2.0-flash 실패, 1.5-flash 폴백 실행: {e}")
                try:
                    model_fb = GenerativeModel("gemini-1.5-flash")
                    response_fb = model_fb.generate_content(full_prompt)
                    return response_fb.text
                except Exception as fb_err:
                    print(f"[AIService] Vertex AI SDK 생성 전체 실패 (HTTP 폴백 진행): {fb_err}")

        # 2. 과도기용 HTTP API 호출 폴백
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
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
                        return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as http_err:
                print(f"[AIService] Gemini HTTP Generative API 실패: {http_err}")

        return self._get_dummy_ai_answer(request)

    def _get_dummy_ai_answer(self, request: GenerateRequest) -> str:
        context_str = f"\n주어진 컨텍스트: {request.context}" if request.context else ""
        return f"'{request.prompt}'에 대한 오프라인 폴백 AI 생성 답변입니다.{context_str}"

    def upsert_review_vector(self, review_id: str, text: str, metadata: dict) -> bool:
        """호환성용 빈 메서드 (Cloud SQL pgvector로 완벽 대체되어 무력화)"""
        return True

    def delete_review_vector(self, review_id: str) -> bool:
        """호환성용 빈 메서드 (Cloud SQL pgvector로 완벽 대체되어 무력화)"""
        return True

    def analyze_review_absa(self, review_text: str) -> dict:
        """
        GCP Vertex AI GenerativeModel (gemini-2.0-flash) 기반 화장품 도메인 특화 감성 분석(ABSA) 실행.
        GCP 환경 외에서는 기존 HTTP API 및 로컬 룰 기반 분석기로 순차 자동 폴백하여 연속성을 보장합니다.
        """
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
        full_prompt = f"{system_instruction}\n\n{prompt}"

        # 1. GCP Vertex AI SDK ABSA 분석 실행
        if _init_vertex_ai():
            models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            for model_name in models:
                try:
                    model = GenerativeModel(model_name)
                    response = model.generate_content(full_prompt)
                    resp_text = response.text
                    
                    try:
                        parsed = self._parse_json(resp_text)
                        required_keys = [
                            "ingredients_skin_concerns_score", "formulation_spreadability_score", 
                            "container_design_score", "overall_sentiment", "overall_score", 
                            "keywords", "issue_type", "ai_summary"
                        ]
                        if all(k in parsed for k in required_keys):
                            print(f"[AIService] Vertex AI ABSA 분석 성공 ({model_name})")
                            return parsed
                    except Exception as parse_err:
                        print(f"[AIService] Vertex AI ABSA JSON 파싱 실패 ({model_name}): {parse_err}")
                except Exception as model_err:
                    print(f"[AIService] Vertex AI ABSA 생성 실패 ({model_name}): {model_err}")

        # 2. HTTP API 기반 ABSA 분석 폴백
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            for model_name in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{
                        "parts": [{"text": full_prompt}]
                    }]
                }
                try:
                    with httpx.Client(timeout=15.0) as client:
                        response = client.post(url, json=payload)
                        if response.status_code == 200:
                            data = response.json()
                            resp_text = data["candidates"][0]["content"]["parts"][0]["text"]
                            try:
                                parsed = self._parse_json(resp_text)
                                return parsed
                            except Exception:
                                pass
                except Exception:
                    pass

        # 3. 최하위 로컬 룰 베이스 ABSA 폴백
        print("[AIService] API 전체 연결 장애로 최종 로컬 룰 ABSA 엔진 구동")
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
        """로컬 규칙 기반 더미 ABSA (동일 유지)"""
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
            
        has_irritation_issue = any(w in review_text for w in ["트러블", "붉", "따갑", "여드름", "자극"])

        ingredients_score = 0.5
        formulation_score = 0.5
        container_score = 0.5
        
        if has_irritation_issue:
            ingredients_score = 0.15
        elif any(w in review_text for w in ["순하", "진정"]):
            ingredients_score = 0.85
            
        if any(w in review_text for w in ["끈적", "밀림"]):
            formulation_score = 0.20
        elif any(w in review_text for w in ["촉촉", "부드럽", "제형"]):
            formulation_score = 0.90
            
        if any(w in review_text for w in ["불편", "용기", "뚜껑", "집게"]):
            container_score = 0.25
        elif any(w in review_text for w in ["디자인", "예쁘"]):
            container_score = 0.80
            
        keywords = [w for w in pos_words + neg_words if w in review_text][:5]
        issue_type = "자극" if has_irritation_issue else "없음"
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

    def generate_trend_briefing(self, this_week: dict, last_week: dict, product_name: str) -> str:
        """
        GCP Vertex AI GenerativeModel (gemini-2.0-flash)을 통한 실시간 대시보드 요약 브리핑 생성.
        장애 및 GCP 외 환경에서는 로컬 룰 한글 트렌드 엔진으로 자동 폴백합니다.
        """
        t_attr = this_week["attribute_scores"]
        l_attr = last_week["attribute_scores"]
        
        # 주간 비교 변동 폭 산출
        ing_diff = t_attr["ingredients"] - l_attr["ingredients"]
        form_diff = t_attr["formulation"] - l_attr["formulation"]
        cont_diff = t_attr["container"] - l_attr["container"]
        rating_diff = this_week["average_rating"] - last_week["average_rating"]
        
        # 1. GCP Vertex AI SDK 브리핑 생성 시도
        if _init_vertex_ai():
            system_instruction = (
                "당신은 뷰티 이커머스 대시보드 전문 수석 분석가입니다. 주어진 화장품 제품의 '이번 주' 통계 및 '지난 주' 통계 데이터를 기반으로,\n"
                "고객 만족도 흐름을 분석하여 대시보드 최상단 배너에 노출될 **친절하고 정교한 한국어 1문장 실시간 요약 브리핑 (약 20~40단어)**을 생성해 주세요.\n\n"
                "작성 규칙:\n"
                "1. 수치 변동 폭(예: 성분/자극 만족도 상승 또는 용기 결함 불만 급증 등)을 반드시 강조해야 합니다.\n"
                "2. 친근하지만 전문성 있는 어조를 사용하고, 반드시 한국어 1문장으로만 완성해 주세요. 마크다운 기호(별표 등)는 사용하지 마세요.\n"
                "3. 절대 서론이나 설명 없이 브리핑 문장 하나만 바로 리턴하세요."
            )
            
            prompt = (
                f"대상 제품명: {product_name}\n\n"
                f"[이번 주 통계]\n"
                f"- 총 리뷰 수: {this_week['total_reviews']}개\n"
                f"- 평균 평점: {this_week['average_rating']}점 / 5.0\n"
                f"- 성분/고민 진정 만족도: {t_attr['ingredients']:.4f}\n"
                f"- 제형/발림성 만족도: {t_attr['formulation']:.4f}\n"
                f"- 용기/편의성 만족도: {t_attr['container']:.4f}\n\n"
                f"[지난 주 대비 변동 폭 (WoW)]\n"
                f"- 평점 변화: {rating_diff:+.2f}점\n"
                f"- 성분/고민 변동: {ing_diff:+.4f}\n"
                f"- 제형/발림성 변동: {form_diff:+.4f}\n"
                f"- 용기/편의성 변동: {cont_diff:+.4f}"
            )
            
            models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            for model_name in models:
                try:
                    model = GenerativeModel(model_name)
                    response = model.generate_content(f"{system_instruction}\n\n{prompt}")
                    briefing = response.text.strip()
                    if briefing:
                        print(f"[AIService] Vertex AI 트렌드 브리핑 요약 생성 완료 ({model_name})")
                        return briefing
                except Exception as e:
                    print(f"[AIService] Vertex AI Briefing API 에러 ({model_name}): {e}")

        # 2. HTTP API 기반 브리핑 생성 폴백
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            system_instruction = (
                "당신은 뷰티 이커머스 대시보드 전문 수석 분석가입니다. 주어진 화장품 제품의 '이번 주' 통계 및 '지난 주' 통계 데이터를 기반으로,\n"
                "고객 만족도 흐름을 분석하여 대시보드 최상단 배너에 노출될 **친절하고 정교한 한국어 1문장 실시간 요약 브리핑 (약 20~40단어)**을 생성해 주세요.\n\n"
                "작성 규칙:\n"
                "1. 수치 변동 폭(예: 성분/자극 만족도 상승 또는 용기 결함 불만 급증 등)을 반드시 강조해야 합니다.\n"
                "2. 친근하지만 전문성 있는 어조를 사용하고, 반드시 한국어 1문장으로만 완성해 주세요. 마크다운 기호(별표 등)는 사용하지 마세요.\n"
                "3. 절대 서론이나 설명 없이 브리핑 문장 하나만 바로 리턴하세요."
            )
            prompt = (
                f"대상 제품명: {product_name}\n\n"
                f"[이번 주 통계]\n"
                f"- 총 리뷰 수: {this_week['total_reviews']}개\n"
                f"- 평균 평점: {this_week['average_rating']}점 / 5.0\n"
                f"- 성분/고민 진정 만족도: {t_attr['ingredients']:.4f}\n"
                f"- 제형/발림성 만족도: {t_attr['formulation']:.4f}\n"
                f"- 용기/편의성 만족도: {t_attr['container']:.4f}\n\n"
                f"[지난 주 대비 변동 폭 (WoW)]\n"
                f"- 평점 변화: {rating_diff:+.2f}점\n"
                f"- 성분/고민 변동: {ing_diff:+.4f}\n"
                f"- 제형/발림성 변동: {form_diff:+.4f}\n"
                f"- 용기/편의성 변동: {cont_diff:+.4f}"
            )
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
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
                        briefing = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if briefing:
                            return briefing
            except Exception:
                pass

        # 3. 최하위 로컬 룰 베이스 브리핑 폴백
        print("[AIService] API 전체 연결 장애로 로컬 트렌드 브리핑 엔진 구동")
        return self._local_trend_briefing_fallback(ing_diff, form_diff, cont_diff, rating_diff, product_name)

    def _local_trend_briefing_fallback(self, ing_diff: float, form_diff: float, cont_diff: float, rating_diff: float, product_name: str) -> str:
        """로컬 트렌드 요약 (동일 유지)"""
        issues = []
        improvements = []
        
        if ing_diff <= -0.10:
            issues.append(f"성분 및 피부 고민에 대한 부정 VOC가 {abs(ing_diff)*100:.1f}% 증가")
        elif ing_diff >= 0.10:
            improvements.append(f"성분 순함 및 진정 만족도 수치가 {ing_diff*100:.1f}% 개선")
            
        if form_diff <= -0.10:
            issues.append(f"제형의 끈적임 및 화장 밀림에 대한 아쉬움 의견이 {abs(form_diff)*100:.1f}% 상승")
        elif form_diff >= 0.10:
            improvements.append(f"촉촉하고 산뜻한 발림성 만족도가 {form_diff*100:.1f}% 증가")
            
        if cont_diff <= -0.10:
            issues.append(f"용기 불량, 뚜껑 헛돌기 및 집게 분실 불만이 {abs(cont_diff)*100:.1f}% 급증")
        elif cont_diff >= 0.10:
            improvements.append(f"용기 편의성 및 위생적 디자인 점수가 {cont_diff*100:.1f}% 상승")

        if issues:
            detail_issue = ", ".join(issues)
            return f"🚨 최근 1주일간 {product_name} 제품은 {detail_issue}하여 제품 개선 및 민감 피드백 조율이 요구됩니다."
        elif improvements:
            detail_impr = ", ".join(improvements)
            return f"✨ 최근 1주일간 {product_name} 제품은 {detail_impr}하며 전반적으로 우수한 긍정 트렌드를 유지하고 있습니다."
        else:
            rating_comment = "안정적인 흐름"
            if rating_diff > 0:
                rating_comment = "미세한 평점 상승 추세"
            elif rating_diff < 0:
                rating_comment = "일시적인 미세 평점 하락"
            return f"ℹ️ 최근 1주일간 {product_name} 제품의 통계 분석 결과, 평점이 {rating_comment}를 보이며 3대 핵심 속성 모두 균형 잡힌 만족도를 나타내고 있습니다."
