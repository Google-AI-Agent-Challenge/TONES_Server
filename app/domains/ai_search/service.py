import httpx
from app.core.config import settings
from app.domains.ai_search.schemas import SearchRequest, SearchResultItem, GenerateRequest
from app.domains.ai_search.repository import AIRepository

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    from vertexai.language_models import TextEmbeddingModel
    HAS_VERTEX_SDK = True
except ImportError:
    HAS_VERTEX_SDK = False
    class GenerativeModel:
        def __init__(self, *args, **kwargs): pass
        def generate_content(self, *args, **kwargs): pass
    class TextEmbeddingModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs): return cls()
        def get_embeddings(self, *args, **kwargs): pass

_vertex_initialized = False


def _init_vertex_ai():
    global _vertex_initialized
    if not HAS_VERTEX_SDK:
        return False
    if not _vertex_initialized:
        project_id = getattr(settings, "GCP_PROJECT_ID", None)
        region = getattr(settings, "GCP_REGION", "us-central1")
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
        self.repo = AIRepository(db_conn)

    def _get_gemini_embedding(self, text: str) -> list[float] | None:
        if _init_vertex_ai():
            try:
                model = TextEmbeddingModel.from_pretrained("text-embedding-004")
                embeddings = model.get_embeddings([text])
                print("[AIService] Vertex AI Embedding 추출 성공")
                return embeddings[0].values
            except Exception as e:
                print(f"[AIService] Vertex AI Embedding API 호출 실패 (HTTP 폴백 진행): {e}")
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={settings.GEMINI_API_KEY}"
            payload = {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": text}]}, "outputDimensionality": 768}
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(url, json=payload)
                    if response.status_code == 200:
                        return response.json()["embedding"]["values"]
                    else:
                        print(f"[AIService] Gemini HTTP Embedding 에러 (HTTP {response.status_code}): {response.text}")
            except Exception as http_err:
                print(f"[AIService] Gemini HTTP Embedding 예외 발생: {http_err}")
        return None

    def vector_search(self, request: SearchRequest) -> list[SearchResultItem]:
        query_vector = self._get_gemini_embedding(request.query)
        results = self.repo.vector_search(request, query_vector)
        if results:
            return results
        # 오프라인 폴백: 더미 결과 반환
        print("[AIService] 오프라인 폴백: 더미 시맨틱 검색 결과를 생성합니다.")
        return [
            SearchResultItem(
                id=f"doc_{i}",
                score=0.98 - (i * 0.05),
                metadata={"title": f"Document {i}", "content": f"이것은 '{request.query}'에 대한 로컬 테스트용 {i}번째 관련 더미 문서 검색 결과입니다."}
            )
            for i in range(request.top_k)
        ]

    def generate_ai_answer(self, request: GenerateRequest) -> str:
        context_str = f"주어진 컨텍스트:\n{request.context}\n\n" if request.context else ""
        full_prompt = f"{context_str}질문: {request.prompt}\n\n위의 질문에 대해 주어진 컨텍스트에 기반하여 정확하고 친절하게 한국어로 답변해 주세요."
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
                    return model_fb.generate_content(full_prompt).text
                except Exception as fb_err:
                    print(f"[AIService] Vertex AI SDK 생성 전체 실패 (HTTP 폴백 진행): {fb_err}")
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            try:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(url, json={"contents": [{"parts": [{"text": full_prompt}]}]})
                    if response.status_code == 200:
                        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        print(f"[AIService] Gemini HTTP Generative 에러 (HTTP {response.status_code}): {response.text}")
            except Exception as http_err:
                print(f"[AIService] Gemini HTTP Generative 예외 발생: {http_err}")
        return self._get_dummy_ai_answer(request)

    def _get_dummy_ai_answer(self, request: GenerateRequest) -> str:
        context_str = f"\n주어진 컨텍스트: {request.context}" if request.context else ""
        return f"'{request.prompt}'에 대한 오프라인 폴백 AI 생성 답변입니다.{context_str}"

    def upsert_review_vector(self, review_id: str, text: str, metadata: dict) -> bool:
        return True

    def delete_review_vector(self, review_id: str) -> bool:
        return True

    def analyze_review_absa(self, review_text: str) -> dict:
        system_instruction = (
            "당신은 화장품 전문 리뷰 분석 AI 연구원입니다. 주어진 고객 리뷰에서 다음 3대 VOC 속성에 대한 긍정 감성 점수(0.0 ~ 1.0)를 추출해 주세요.\n\n"
            "추출 속성:\n1. 성분/피부고민 진정 및 자극성 점수 (ingredients_skin_concerns_score)\n"
            "2. 제형/발림성/끈적임/밀림 점수 (formulation_spreadability_score)\n"
            "3. 용기/디자인/뚜껑/내부 캡 편의성 점수 (container_design_score)\n\n"
            "또한 전체 감성 판단(overall_sentiment: 'positive', 'neutral', 'negative'), 전체 감성 점수(overall_score: 0.0 ~ 1.0), "
            "핵심 키워드 3~5개(keywords), 부작용/불량 유형(issue_type), 1문장 한국어 요약(ai_summary)을 추출해야 합니다.\n\n"
            "반드시 JSON 형식으로만 응답해야 합니다. JSON 스키마:\n"
            '{"ingredients_skin_concerns_score": float, "formulation_spreadability_score": float, "container_design_score": float, '
            '"overall_sentiment": string, "overall_score": float, "keywords": [string], "issue_type": string, "ai_summary": string}'
        )
        prompt = f"분석할 고객 리뷰:\n\"\"\"\n{review_text}\n\"\"\""
        full_prompt = f"{system_instruction}\n\n{prompt}"
        if _init_vertex_ai():
            for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    model = GenerativeModel(model_name)
                    response = model.generate_content(full_prompt)
                    parsed = self._parse_json(response.text)
                    required_keys = ["ingredients_skin_concerns_score", "formulation_spreadability_score", "container_design_score", "overall_sentiment", "overall_score", "keywords", "issue_type", "ai_summary"]
                    if all(k in parsed for k in required_keys):
                        print(f"[AIService] Vertex AI ABSA 분석 성공 ({model_name})")
                        return parsed
                except Exception as e:
                    print(f"[AIService] Vertex AI ABSA 실패 ({model_name}): {e}")
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            for model_name in ["gemini-2.5-flash", "gemini-flash-latest"]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                try:
                    with httpx.Client(timeout=15.0) as client:
                        response = client.post(url, json={"contents": [{"parts": [{"text": full_prompt}]}]})
                        if response.status_code == 200:
                            resp_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                            return self._parse_json(resp_text)
                        else:
                            print(f"[AIService] Gemini HTTP ABSA 에러 ({model_name}) (HTTP {response.status_code}): {response.text}")
                except Exception as e:
                    print(f"[AIService] Gemini HTTP ABSA 예외 ({model_name}): {e}")
        print("[AIService] API 전체 연결 장애로 최종 로컬 룰 ABSA 엔진 구동")
        return self._local_heuristic_absa(review_text)

    def _parse_json(self, text: str) -> dict:
        import json, re
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
        return json.loads(cleaned.strip())

    def _local_heuristic_absa(self, review_text: str) -> dict:
        pos_words = ["좋", "촉촉", "순하", "대박", "추천", "부드럽", "짱", "만족", "최고"]
        neg_words = ["자극", "아쉽", "불편", "따갑", "트러블", "좁쌀", "붉", "여드름", "밀림", "끈적"]
        pos_count = sum(1 for w in pos_words if w in review_text)
        neg_count = sum(1 for w in neg_words if w in review_text)
        overall_score = 0.8 if pos_count > neg_count else (0.2 if neg_count > pos_count else 0.5)
        sentiment = "positive" if overall_score >= 0.7 else ("negative" if overall_score <= 0.3 else "neutral")
        has_irritation = any(w in review_text for w in ["트러블", "붉", "따갑", "여드름", "자극"])
        ingredients_score = 0.15 if has_irritation else (0.85 if any(w in review_text for w in ["순하", "진정"]) else 0.5)
        has_sticky = ("끈적" in review_text and not any(ok in review_text for ok in ["끈적임 없이", "끈적이지", "끈적임 없는"])) or "밀림" in review_text
        formulation_score = 0.20 if has_sticky else (0.90 if any(w in review_text for w in ["촉촉", "부드럽", "제형"]) else 0.5)
        has_container_issue = any(w in review_text for w in ["불편", "용기", "뚜껑", "집게"])
        container_score = 0.25 if has_container_issue else (0.80 if any(w in review_text for w in ["디자인", "예쁘"]) else 0.5)
        keywords = [w for w in pos_words + neg_words if w in review_text][:5]
        return {
            "ingredients_skin_concerns_score": ingredients_score,
            "formulation_spreadability_score": formulation_score,
            "container_design_score": container_score,
            "overall_sentiment": sentiment,
            "overall_score": overall_score,
            "keywords": keywords if keywords else ["패드"],
            "issue_type": "자극" if has_irritation else "없음",
            "ai_summary": f"리뷰 요약: {review_text[:30]}..."
        }

    def generate_trend_briefing(self, this_week: dict, last_week: dict, product_name: str) -> str:
        t_attr = this_week["attribute_scores"]
        l_attr = last_week["attribute_scores"]
        ing_diff = t_attr["ingredients"] - l_attr["ingredients"]
        form_diff = t_attr["formulation"] - l_attr["formulation"]
        cont_diff = t_attr["container"] - l_attr["container"]
        rating_diff = this_week["average_rating"] - last_week["average_rating"]
        is_stable = all(round(abs(d) * 100, 1) == 0.0 for d in [ing_diff, form_diff, cont_diff])

        system_instruction = (
            "당신은 뷰티 이커머스 대시보드 전문 수석 분석가입니다. "
            "주어진 화장품 제품의 이번 주 통계와 지난 주 통계를 바탕으로, "
            "브랜드 매니저가 즉시 의사결정에 활용할 수 있는 심층 AI 브리핑 리포트를 한국어로 작성해 주세요.\n\n"
            "작성 규칙:\n1. 전체 분량은 750자 이상 1,000자 이하로 작성합니다.\n"
            "2. 아래 4개 섹션을 순서대로 작성합니다: 📈 긍정 / ⚠️ 이슈 / 📊 트렌드 분석 / 🎯 액션 아이템\n"
            "3. 마크다운 기호는 사용하지 말고 순수 텍스트로만 작성합니다.\n"
            "4. 서론 없이 첫 번째 섹션 제목부터 바로 시작합니다."
        )
        if is_stable:
            system_instruction += "\n\n[특별 지시사항] 현재 3대 속성 변동폭이 매우 미미합니다. 변동폭 수치를 넣지 말고, '품질 이슈 없이 견고하고 안정적인 만족도를 유지하고 있습니다'라는 표현을 포함하세요."

        def _fmt_wow(diff: float) -> str:
            pct = round(diff * 100, 1)
            return "변동 없음" if pct == 0.0 else f"{diff:+.4f} ({pct:+.1f}%p)"

        prompt = (
            f"대상 제품명: {product_name}\n\n[이번 주 통계]\n"
            f"- 총 리뷰 수: {this_week['total_reviews']}개\n"
            f"- 평균 평점: {this_week['average_rating']}점 / 5.0\n"
            f"- 긍정 리뷰 수: {this_week['sentiment_breakdown'].get('positive', 0)}개\n"
            f"- 부정 리뷰 수: {this_week['sentiment_breakdown'].get('negative', 0)}개\n"
            f"- 성분/고민 진정 만족도: {t_attr['ingredients']:.4f}\n"
            f"- 제형/발림성 만족도: {t_attr['formulation']:.4f}\n"
            f"- 용기/편의성 만족도: {t_attr['container']:.4f}\n\n[지난 주 대비 변동 폭 (WoW)]\n"
            f"- 평점 변화: {'변동 없음' if rating_diff == 0.0 else f'{rating_diff:+.2f}점'}\n"
            f"- 성분/고민 변동: {_fmt_wow(ing_diff)}\n"
            f"- 제형/발림성 변동: {_fmt_wow(form_diff)}\n"
            f"- 용기/편의성 변동: {_fmt_wow(cont_diff)}"
        )

        if _init_vertex_ai():
            for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    model = GenerativeModel(model_name)
                    briefing = model.generate_content(f"{system_instruction}\n\n{prompt}").text.strip()
                    if briefing:
                        print(f"[AIService] Vertex AI 트렌드 브리핑 생성 완료 ({model_name})")
                        return briefing
                except Exception as e:
                    print(f"[AIService] Vertex AI Briefing 에러 ({model_name}): {e}")
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            try:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(url, json={"contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}]})
                    if response.status_code == 200:
                        briefing = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if briefing:
                            return briefing
                    else:
                        print(f"[AIService] Gemini HTTP Briefing 에러 (HTTP {response.status_code}): {response.text}")
            except Exception as http_err:
                print(f"[AIService] Gemini HTTP Briefing 예외 발생: {http_err}")

        print("[AIService] API 전체 연결 장애로 로컬 트렌드 브리핑 엔진 구동")
        return self._local_trend_briefing_fallback(ing_diff, form_diff, cont_diff, rating_diff, product_name)

    def _local_trend_briefing_fallback(self, ing_diff, form_diff, cont_diff, rating_diff, product_name) -> str:
        is_stable = all(round(abs(d) * 100, 1) == 0.0 for d in [ing_diff, form_diff, cont_diff])
        if is_stable:
            return (
                f"📈 긍정\n이번 주 {product_name}의 3대 핵심 속성(성분·제형·용기) 모두 만족도가 안정적으로 유지되고 있습니다.\n\n"
                f"⚠️ 이슈\n이번 주 분석 기간 동안 유의미한 불만 증가나 품질 저하 이슈는 감지되지 않았습니다.\n\n"
                f"📊 트렌드 분석\n{product_name}의 모든 속성에서 품질 이슈 없이 견고하고 안정적인 만족도를 유지하고 있습니다.\n\n"
                f"🎯 액션 아이템\n현재 안정적인 흐름을 긍정 리뷰 기반 마케팅 콘텐츠로 활용하고, 주간 모니터링을 지속하세요."
            )

        def _dir(diff): return "positive" if diff >= 0.05 else ("negative" if diff <= -0.05 else "neutral")
        positives, negatives = [], []
        if _dir(ing_diff) == "positive": positives.append(f"성분 및 피부 진정 만족도가 전기 대비 {ing_diff*100:+.1f}%p 개선되었습니다.")
        if _dir(ing_diff) == "negative": negatives.append(f"성분 및 자극 관련 불만이 전기 대비 {abs(ing_diff)*100:.1f}%p 증가하였습니다.")
        if _dir(form_diff) == "positive": positives.append(f"제형 발림성 만족도가 {form_diff*100:+.1f}%p 상승하였습니다.")
        if _dir(form_diff) == "negative": negatives.append(f"끈적임·화장 밀림 관련 부정 피드백이 {abs(form_diff)*100:.1f}%p 증가하였습니다.")
        if _dir(cont_diff) == "positive": positives.append(f"용기 편의성 만족도가 {cont_diff*100:+.1f}%p 향상되었습니다.")
        if _dir(cont_diff) == "negative": negatives.append(f"용기 불량 관련 불만이 {abs(cont_diff)*100:.1f}%p 급증하였습니다.")
        positive_text = " ".join(positives) if positives else f"{product_name}의 3대 핵심 속성(성분·제형·용기) 만족도가 전기와 유사한 수준을 유지하고 있어 안정적인 품질 흐름이 관찰됩니다."
        issue_text = " ".join(negatives) + " 해당 속성 VOC를 면밀히 검토하고 대응 방안 마련을 권고합니다." if negatives else "이번 주 특별히 주의가 필요한 하락 지표는 감지되지 않았습니다."
        actions = []
        if _dir(ing_diff) == "negative": actions.append("성분 자극 관련 부정 리뷰를 집중 분류하여 주의 안내를 보완하세요.")
        if _dir(form_diff) == "negative": actions.append("끈적임·밀림 불만 리뷰 유형별 분류 후 사용 가이드를 강화하세요.")
        if _dir(cont_diff) == "negative": actions.append("용기 불량 관련 VOC를 제조사에 공유하고 QC 점검을 요청하세요.")
        if not actions: actions = ["긍정 리뷰 기반 마케팅 콘텐츠를 제작하고 주간 품질 모니터링을 지속하세요."]
        return (
            f"📈 긍정\n{positive_text}\n\n"
            f"⚠️ 이슈\n{issue_text}\n\n"
            f"📊 트렌드 분석\n{product_name}의 성분·제형·용기 속성 변동을 종합 분석한 결과, 전반적 흐름은 {'개선' if len(positives) >= len(negatives) else '주의가 필요한 방향'}으로 나타납니다.\n\n"
            f"🎯 액션 아이템\n{' '.join(actions)}"
        )
