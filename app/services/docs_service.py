"""
DocsService: Google Docs API v1 연동 서비스 (GCP 서비스 계정 JSON 키 기반 OAuth2 인증)

동작 흐름:
  1. 환경변수(GOOGLE_SERVICE_ACCOUNT_JSON)에서 서비스 계정 JSON 파싱
  2. google-auth 라이브러리로 OAuth2 액세스 토큰 발급 (Docs + Drive 스코프)
  3. Google Docs API v1 로 빈 문서 생성
  4. 문서 body에 Markdown→Docs 구조화된 요청으로 내용 일괄 삽입 (batchUpdate)
  5. Google Drive API로 "링크 보유 시 누구나 열람" 권한 부여
  6. 프론트엔드에 document_id, document_url 반환
"""

import json
import httpx
from app.core.config import settings


_DOCS_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

_DOCS_API_BASE = "https://docs.googleapis.com/v1/documents"
_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files"


def _get_service_account_info() -> dict:
    """
    환경변수 GOOGLE_SERVICE_ACCOUNT_JSON에서 서비스 계정 자격증명을 파싱해 반환.
    값이 없거나 파싱 실패 시 RuntimeError 발생.
    """
    raw = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON", None)
    if not raw or raw.startswith("your-"):
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON 환경변수가 설정되지 않았습니다. "
            "GCP 서비스 계정 JSON 키를 환경변수에 설정해 주세요."
        )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GOOGLE_SERVICE_ACCOUNT_JSON 파싱 실패: {e}")


def _get_access_token(service_account_info: dict) -> str:
    """
    google-auth 라이브러리를 통해 서비스 계정으로 OAuth2 액세스 토큰을 발급.
    google-auth 미설치 환경에서는 RuntimeError 발생.
    """
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except ImportError:
        raise RuntimeError(
            "google-auth 패키지가 설치되지 않았습니다. "
            "requirements.txt에 google-auth>=2.0.0이 포함되어 있는지 확인해 주세요."
        )

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=_DOCS_SCOPES,
    )
    credentials.refresh(Request())
    return credentials.token


def _markdown_to_docs_requests(markdown_text: str) -> list[dict]:
    """
    Markdown 문자열을 Google Docs batchUpdate requests 배열로 변환.

    지원 변환:
    - `# `  → HEADING_1
    - `## ` → HEADING_2
    - `### `→ HEADING_3
    - `**text**` → bold 텍스트
    - 일반 텍스트 → NORMAL_TEXT

    Google Docs API의 insertText는 역순으로 삽입해야 올바른 순서가 되므로,
    먼저 전체 텍스트를 평문으로 작성한 뒤 스타일 요청을 별도 배열로 구성하는 방식을 사용.
    단순 구현을 위해 평문 삽입 후 제목 스타일만 단락 단위로 적용한다.
    """
    if not markdown_text:
        return []

    requests = []
    lines = markdown_text.split("\n")

    # 전체 텍스트를 단일 삽입 (인덱스 1부터 시작, 0은 문서 헤더)
    full_text = markdown_text + "\n"
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": full_text,
        }
    })

    # 각 단락의 스타일 지정 (heading 레벨)
    # 삽입 후 문자 오프셋을 추적해 단락 범위를 계산
    cursor = 1  # 문서 내 현재 문자 인덱스
    style_requests = []

    for line in lines:
        line_len = len(line) + 1  # +1 for \n

        if line.startswith("### "):
            style_requests.append({
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": cursor,
                        "endIndex": cursor + line_len,
                    },
                    "paragraphStyle": {"namedStyleType": "HEADING_3"},
                    "fields": "namedStyleType",
                }
            })
        elif line.startswith("## "):
            style_requests.append({
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": cursor,
                        "endIndex": cursor + line_len,
                    },
                    "paragraphStyle": {"namedStyleType": "HEADING_2"},
                    "fields": "namedStyleType",
                }
            })
        elif line.startswith("# "):
            style_requests.append({
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": cursor,
                        "endIndex": cursor + line_len,
                    },
                    "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    "fields": "namedStyleType",
                }
            })

        cursor += line_len

    # 스타일 요청은 텍스트 삽입 이후 적용되므로 별도 리턴
    # insertText 이후 순서대로 batchUpdate에 넘겨야 함
    return requests + style_requests


class DocsService:
    """
    Google Docs 문서 생성 서비스.
    GCP 서비스 계정 자격증명을 사용해 Docs API v1 및 Drive API v3를 직접 호출한다.
    """

    def create_document(self, title: str, report_markdown: str) -> dict:
        """
        Google Docs API를 통해 새 문서를 생성하고, 마크다운 내용을 삽입한 뒤
        링크 공유 권한을 부여하고 document_id와 document_url을 반환.

        Args:
            title: 생성할 구글 문서 제목
            report_markdown: 삽입할 마크다운 형식의 보고서 본문

        Returns:
            {
                "document_id": "...",
                "document_url": "https://docs.google.com/document/d/.../edit"
            }

        Raises:
            RuntimeError: 서비스 계정 설정 오류 또는 API 호출 실패
        """
        service_account_info = _get_service_account_info()
        access_token = _get_access_token(service_account_info)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30.0) as client:
            # 1. 빈 문서 생성
            create_resp = client.post(
                _DOCS_API_BASE,
                headers=headers,
                json={"title": title},
            )
            if create_resp.status_code != 200:
                raise RuntimeError(
                    f"Google Docs 문서 생성 실패 (HTTP {create_resp.status_code}): "
                    f"{create_resp.text}"
                )

            doc_data = create_resp.json()
            document_id = doc_data["documentId"]
            print(f"[DocsService] 구글 문서 생성 완료: {document_id}")

            # 2. 마크다운 내용을 구조화된 batchUpdate 요청으로 삽입
            if report_markdown:
                batch_requests = _markdown_to_docs_requests(report_markdown)
                if batch_requests:
                    batch_resp = client.post(
                        f"{_DOCS_API_BASE}/{document_id}:batchUpdate",
                        headers=headers,
                        json={"requests": batch_requests},
                    )
                    if batch_resp.status_code != 200:
                        print(
                            f"[DocsService] batchUpdate 경고 (HTTP {batch_resp.status_code}): "
                            f"{batch_resp.text[:200]}"
                        )
                    else:
                        print(f"[DocsService] 문서 내용 삽입 완료: {document_id}")

            # 3. Google Drive API로 "링크 보유 시 누구나 열람(reader)" 권한 부여
            permission_resp = client.post(
                f"{_DRIVE_API_BASE}/{document_id}/permissions",
                headers=headers,
                json={
                    "type": "anyone",
                    "role": "reader",
                },
            )
            if permission_resp.status_code not in (200, 201):
                print(
                    f"[DocsService] 공유 권한 설정 경고 (HTTP {permission_resp.status_code}): "
                    f"{permission_resp.text[:200]}"
                )
            else:
                print(f"[DocsService] 링크 공유 권한 설정 완료: {document_id}")

        document_url = f"https://docs.google.com/document/d/{document_id}/edit"
        return {
            "document_id": document_id,
            "document_url": document_url,
        }
