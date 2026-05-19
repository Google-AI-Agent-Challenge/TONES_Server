from app.schemas.ai_search import SearchRequest, SearchResultItem, GenerateRequest


class AIService:
    def __init__(self, pinecone_client=None):
        self.pinecone = pinecone_client

    def vector_search(self, request: SearchRequest):
        # 실제 Pinecone 연동 예시:
        # index = self.pinecone.Index(settings.PINECONE_INDEX_NAME)
        # response = index.query(vector=[...], top_k=request.top_k, filter=request.filter)
        
        # 로컬 테스트용 더미 결과 생성
        dummy_results = [
            SearchResultItem(
                id=f"doc_{i}",
                score=0.98 - (i * 0.05),
                metadata={"title": f"Document {i}", "content": f"이것은 '{request.query}'에 대한 {i}번째 관련 문서 검색 결과입니다."}
            )
            for i in range(request.top_k)
        ]
        return dummy_results

    def generate_ai_answer(self, request: GenerateRequest) -> str:
        # LLM(예: OpenAI, Gemini 등) 연동 로직
        context_str = f"\n주어진 컨텍스트: {request.context}" if request.context else ""
        return f"'{request.prompt}'에 대한 AI 생성 답변입니다.{context_str}"
