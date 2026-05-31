import httpx
from app.core.config import settings
from app.schemas.ai_search import SearchRequest, SearchResultItem, GenerateRequest


class AIService:
    def __init__(self, db_conn=None):
        self.conn = db_conn

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
        GCP 통합 아키텍처 개편에 따른 레거시 어댑터 호환용 빈 메서드.
        (리뷰 데이터와 임베딩은 이제 단일 Cloud SQL PostgreSQL 트랜잭션 내에서 한꺼번에 원자적 저장되므로 이 별도 업로드는 패스합니다.)
        """
        return True

    def delete_review_vector(self, review_id: str) -> bool:
        """
        GCP 통합 아키텍처 개편에 따른 레거시 어댑터 호환용 빈 메서드.
        (Cloud SQL 트랜잭션 롤백 시 DB 레코드와 pgvector 데이터가 자동 동시 롤백되므로 이 별도 삭제는 패스합니다.)
        """
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
        
        # Calculate neg_count, accounting for negated "자극"
        neg_count = 0
        for w in neg_words:
            if w in review_text:
                if w == "자극":
                    idx = review_text.find("자극")
                    context = review_text[idx:idx+15]
                    if "없" in context or "안" in context:
                        continue # "자극 없음"은 부정 키워드로 계산하지 않음
                neg_count += 1
        
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
            
        # Check for irritation/trouble keywords, handling potential negation for "자극"
        has_irritation_issue = False
        for w in ["트러블", "붉", "따갑", "여드름"]:
            if w in review_text:
                has_irritation_issue = True
        
        if "자극" in review_text:
            idx = review_text.find("자극")
            context = review_text[idx:idx+15]
            if "없" in context or "안" in context:
                pass # 자극 없음 -> 부정적 성분 이슈가 아님
            else:
                has_irritation_issue = True

        ingredients_score = 0.5
        formulation_score = 0.5
        container_score = 0.5
        
        if has_irritation_issue:
            ingredients_score = 0.15
        elif any(w in review_text for w in ["순하", "진정"]) or ("자극" in review_text and not has_irritation_issue):
            ingredients_score = 0.85
            
        if any(w in review_text for w in ["끈적", "밀림"]):
            formulation_score = 0.20
        elif any(w in review_text for w in ["촉촉", "부드럽", "제형"]):
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

    def generate_trend_briefing(self, this_week: dict, last_week: dict, product_name: str) -> str:
        """
        Gemini 2.0-flash를 호출하여 수치 변화에 따른 대시보드 탑 1줄 요약 브리핑 생성
        네트워크 오류나 API 미설정 시 로컬 한글 요약 생성 엔진으로 자동 폴백
        """
        t_attr = this_week["attribute_scores"]
        l_attr = last_week["attribute_scores"]
        
        # 1. 주간 비교 변동 폭 산출
        ing_diff = t_attr["ingredients"] - l_attr["ingredients"]
        form_diff = t_attr["formulation"] - l_attr["formulation"]
        cont_diff = t_attr["container"] - l_attr["container"]
        rating_diff = this_week["average_rating"] - last_week["average_rating"]
        
        # 2. API 미설정 시 로컬 룰 엔진 즉시 기동
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
            print("[AIService] Gemini API Key 미설정 (로컬 트렌드 브리핑 엔진 구동)")
            return self._local_trend_briefing_fallback(ing_diff, form_diff, cont_diff, rating_diff, product_name)

        # 3. Gemini RAG-style 브리핑 전용 프롬프트 조립
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

        # Gemini 2.0 Flash -> 1.5 Flash 폴백 처리
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
                        briefing = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if briefing:
                            print(f"[AIService] Gemini 트렌드 브리핑 요약 생성 완료 ({model_name})")
                            return briefing
                    else:
                        print(f"[AIService] Gemini Briefing API 에러 ({model_name}): {response.status_code}")
            except Exception as e:
                print(f"[AIService] Gemini Briefing API 예외 발생 ({model_name}): {e}")

        # 최종 로컬 폴백
        print("[AIService] Gemini API 오류로 인해 로컬 트렌드 브리핑 엔진 폴백 구동")
        return self._local_trend_briefing_fallback(ing_diff, form_diff, cont_diff, rating_diff, product_name)

    def _local_trend_briefing_fallback(self, ing_diff: float, form_diff: float, cont_diff: float, rating_diff: float, product_name: str) -> str:
        """
        오프라인 및 API 키 미설정용 로컬 규칙 기반 한글 트렌드 요약 브리핑 생성
        """
        issues = []
        improvements = []
        
        # 1. 속성별 변화 판별
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

        # 2. 종합 코멘트 조립
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
