import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from urls import (
    AWS_URLS,
    DOCKER_URLS,
    GCP_URLS,
    KUBERNETES_URLS,
    DEFAULT_URLS,
)

# 설정
PERSIST_DIRECTORY = "./chroma_db"

EMBEDDINGS_MODEL = HuggingFaceEmbeddings(
    model_name='jhgan/ko-sroberta-nli',
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True},
)


def detect_source_type(url: str) -> str:
    """URL을 분석하여 소스 타입을 감지 (aws, docker, 기타)."""
    if "docs.aws.amazon.com" in url:
        return "aws"
    elif "docs.docker.com" in url:
        return "docker"
    else:
        return "other"


def extract_main_content(html: str, url: str, source_type: str = None) -> tuple[str, str]:
    """문서에서 본문만 추출 (AWS, Docker 등 다양한 문서 지원)."""
    if source_type is None:
        source_type = detect_source_type(url)
    
    soup = BeautifulSoup(html, "html.parser")
    
    # 소스 타입별 본문 영역 선택자
    if source_type == "aws":
        main_selectors = [
            "#main-content",
            ".main-content",
            "#content",
            ".content",
            ".awsdocs-content",
            "#awsdocs-content",
            "#awsdocs-main-column",
            ".awsdocs-main-column",
            "#main-col-body",
            ".main-col-body",
            "div[role='main']",
            "main",
            "article",
            "#bodyContents",
            ".bodyContents",
        ]
    elif source_type == "docker":
        main_selectors = [
            ".docs-content",
            "#docs-content",
            ".article-content",
            "#article-content",
            "article.docs-article",
            "main article",
            "article",
            "main",
        ]
    else:
        main_selectors = [
            "main",
            "article",
            ".content",
            "#content",
            ".documentation",
            "#documentation",
        ]
    
    main_content = None
    for selector in main_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    if not main_content:
        # 본문 영역을 찾지 못한 경우 body에서 불필요한 요소 제거
        main_content = soup.find("body")
        if main_content:
            # 공통 불필요 요소 제거
            for tag in main_content.find_all(["nav", "header", "footer", "aside", "script", "style", "noscript"]):
                tag.decompose()
    
    if main_content:
        # 코드 블록 제거 (pre, code 태그)
        for code_tag in main_content.find_all(["pre", "code"]):
            code_tag.decompose()
        
        # AWS 문서 특정 불필요 요소 제거
        if source_type == "aws":
            unwanted_selectors = [
                '[id*="feedback"]',
                '[class*="feedback"]',
                '[id*="help"]',
                '[class*="help"]',
                '[id*="convention"]',
                '[class*="convention"]',
                '[id*="did-this-page"]',
                '[class*="did-this-page"]',
                '.awsdocs-breadcrumb',
                '#awsdocs-breadcrumb',
                '[class*="code"]',
                '[id*="code"]',
                '.highlight',
                '.syntaxhighlighter',
            ]
            for selector in unwanted_selectors:
                for tag in main_content.select(selector):
                    tag.decompose()
        
        # 텍스트 추출
        text = main_content.get_text(separator="\n", strip=True)
        
        # AWS 문서의 JavaScript 관련 메시지 제거
        if source_type == "aws":
            js_messages = [
                "To use the Amazon Web Services Documentation, Javascript must be enabled",
                "Please refer to your browser's Help pages for instructions",
            ]
            for msg in js_messages:
                text = text.replace(msg, "")
        
        # 코드 블록 패턴 제거 (남아있을 수 있는 코드 블록)
        # 코드 블록 패턴 제거 (```로 감싸진 부분)
        text = re.sub(r'```[\s\S]*?```', '', text)
        # 인라인 코드 패턴 제거 (남아있는 경우)
        text = re.sub(r'`[^`]+`', '', text)
    else:
        text = soup.get_text(separator="\n", strip=True)
        # 코드 블록 제거
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)
    
    # 제목 추출
    title = None
    if soup.title:
        title = soup.title.string.strip() if soup.title.string else None
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    if not title:
        default_title = {
            "aws": "AWS Documentation",
            "docker": "Docker Documentation",
        }.get(source_type, "Documentation")
        title = urlparse(url).path.split("/")[-1] or default_title
    
    return text, title


def is_navigation_chunk(text: str, source_type: str = None) -> bool:
    """네비게이션 바나 불필요한 조각인지 판단."""
    if not text or len(text.strip()) < 10:
        return True
    
    lines = text.strip().split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    if len(non_empty_lines) == 0:
        return True
    
    # 줄바꿈 비율이 비정상적으로 높은 경우 (짧은 텍스트에 줄바꿈이 많음)
    text_length = len(text)
    newline_count = text.count('\n')
    if text_length > 0:
        newline_ratio = newline_count / text_length
        # 텍스트 길이 대비 줄바꿈 비율이 0.3 이상이면 의심 (예: 100자에 30개 이상 줄바꿈)
        if newline_ratio > 0.3:
            return True
    
    # 평균 라인 길이가 너무 짧은 경우 (네비게이션은 보통 짧은 단어들)
    avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines) if non_empty_lines else 0
    if avg_line_length < 15 and len(non_empty_lines) > 5:
        return True
    
    # 소스 타입별 네비게이션 관련 키워드
    if source_type == "aws":
        nav_keywords = [
            "back", "ask ai", "contact support", "get started", "guides", 
            "manuals", "reference", "start typing to search", "menu",
            "navigation", "sidebar", "toc", "table of contents",
            "browse by section", "overview", "quickstart", "explore",
            "release notes", "aws console", "aws cli", "aws sdk",
            "pricing", "support", "documentation", "aws services",
            "did this page help you", "document conventions",
            "get started tutorial", "thanks for letting us know",
            "javascript must be enabled", "browser's help pages"
        ]
    elif source_type == "docker":
        nav_keywords = [
            "back", "ask ai", "contact support", "get started", "guides", 
            "manuals", "reference", "start typing to search", "menu",
            "navigation", "sidebar", "toc", "table of contents",
            "browse by section", "overview", "quickstart", "explore",
            "release notes", "take the survey", "opt into", "raffle",
            "docker swag", "browse", "section", "desktop", "hardened",
            "mcp catalog", "toolkit", "engine", "install"
        ]
    else:
        nav_keywords = [
            "back", "ask ai", "contact support", "get started", "guides", 
            "manuals", "reference", "start typing to search", "menu",
            "navigation", "sidebar", "toc", "table of contents"
        ]
    
    text_lower = text.lower()
    keyword_count = sum(1 for keyword in nav_keywords if keyword in text_lower)
    if keyword_count >= 3:  # 3개 이상의 네비게이션 키워드가 있으면
        return True
    
    return False


def crawl_single_url(url: str, source_type: str = None) -> list[Document]:
    """단일 URL을 크롤링하여 Document 리스트로 반환."""
    if source_type is None:
        source_type = detect_source_type(url)
    
    print(f"[크롤링] {url}")
    
    try:
        # User-Agent 설정
        user_agents = {
            "aws": "Mozilla/5.0 (compatible; AWS-Docs-Crawler/1.0)",
            "docker": "Mozilla/5.0 (compatible; Docker-Docs-Crawler/1.0)",
        }
        user_agent = user_agents.get(source_type, "Mozilla/5.0 (compatible; Docs-Crawler/1.0)")
        
        # HTTP 요청으로 페이지 가져오기
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": user_agent},
            allow_redirects=True
        )
        response.raise_for_status()
        
        # AWS 문서의 Meta refresh 리다이렉트 처리
        if source_type == "aws":
            soup = BeautifulSoup(response.text, "html.parser")
            meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
            if meta_refresh:
                content = meta_refresh.get("content", "")
                if "URL=" in content:
                    redirect_path = content.split("URL=")[1]
                    redirect_url = urljoin(url, redirect_path)
                    print(f"  [리다이렉트] {redirect_url}로 이동")
                    # 리다이렉트된 페이지 다시 요청
                    response = requests.get(
                        redirect_url,
                        timeout=30,
                        headers={"User-Agent": user_agent}
                    )
                    response.raise_for_status()
                    url = redirect_url  # 실제 크롤링된 URL로 업데이트
        
        # 본문 추출
        text, title = extract_main_content(response.text, url, source_type)
        
        if not text or len(text.strip()) < 50:
            print(f"  [경고] 추출된 텍스트가 너무 짧습니다: {len(text.strip())}자")
            return []
        
        print(f"  [성공] 제목: {title}")
        print(f"  [성공] 텍스트 길이: {len(text)}자")
        
        return [
            Document(
                page_content=text,
                metadata={
                    "title": title,
                    "url": url,
                    "source": url,
                    "source_type": source_type,
                }
            )
        ]
        
    except requests.exceptions.RequestException as e:
        print(f"  [오류] HTTP 요청 실패: {e}")
        return []
    except Exception as e:
        print(f"  [오류] 크롤링 중 오류 발생: {e}")
        return []


def crawl_and_update_db(
    urls: list[str] = None,
    persist_directory: str = PERSIST_DIRECTORY,
    rebuild: bool = False,
    source_type: str = None,
):
    """URL 리스트를 크롤링하고 Chroma DB를 갱신."""
    if urls is None:
        urls = DEFAULT_URLS
    
    # 소스 타입이 지정되지 않았으면 첫 번째 URL로부터 감지
    if source_type is None and urls:
        source_type = detect_source_type(urls[0])
    
    # 소스 타입별 메시지
    source_messages = {
        "aws": "AWS 문서 크롤링 및 데이터베이스 갱신 시작",
        "docker": "Docker 문서 크롤링 및 데이터베이스 갱신 시작",
    }
    message = source_messages.get(source_type, "크롤링 및 데이터베이스 갱신 시작")

    print("\n" + "=" * 50)
    print(message)
    print("=" * 50)
    print(f"크롤링할 URL 수: {len(urls)}\n")

    # 크롤링
    all_docs = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] ", end="")
        url_source_type = detect_source_type(url)
        docs = crawl_single_url(url, url_source_type)
        all_docs.extend(docs)
        print()

    if not all_docs:
        print("[경고] 크롤링된 문서가 없습니다.")
        return

    print(f"\n[크롤링 완료] 총 {len(all_docs)}개 문서를 로드했습니다.")

    # 문서 분할
    print(f"\n[문서 분할 중] {len(all_docs)}개 문서를 청크로 분할합니다...")
    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator='',
        chunk_size=600,
        chunk_overlap=200,
        encoding_name='cl100k_base'
    )
    split_docs = text_splitter.split_documents(all_docs)
    print(f"[분할 완료] {len(split_docs)}개 청크로 분할되었습니다.")
    
    # 네비게이션 바나 불필요한 조각 필터링
    print(f"\n[필터링 중] 네비게이션 바 및 불필요한 조각 제거...")
    filtered_docs = []
    filtered_count = 0
    for doc in split_docs:
        doc_source_type = doc.metadata.get("source_type", source_type)
        if not is_navigation_chunk(doc.page_content, doc_source_type):
            filtered_docs.append(doc)
        else:
            filtered_count += 1
    split_docs = filtered_docs
    print(f"[필터링 완료] {filtered_count}개 조각을 제거했습니다. 남은 조각: {len(split_docs)}개")

    # Chroma DB에 저장 (항상 기존 DB를 삭제하고 새로 생성)
    # 로컬 모드
    print(f"\n[DB 저장 중] {persist_directory}에 저장합니다...")
    if os.path.exists(persist_directory):
        import shutil
        shutil.rmtree(persist_directory)
        print(f"[기존 DB 삭제] {persist_directory}를 삭제했습니다.")
    
    vectorstore = Chroma.from_documents(
        documents=split_docs,
        embedding=EMBEDDINGS_MODEL,
        persist_directory=persist_directory,
    )
    
    print(f"[DB 저장 완료] {len(split_docs)}개 청크가 저장되었습니다.")
    
    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="문서 크롤링 및 DB 갱신")
    parser.add_argument(
        "--urls",
        nargs="+",
        default=None,
        help="크롤링할 URL들 (직접 URL 지정)",
    )
    parser.add_argument(
        "--aws",
        action="store_true",
        help="AWS 문서만 크롤링",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Docker 문서만 크롤링",
    )
    parser.add_argument(
        "--gcp",
        action="store_true",
        help="GCP 문서만 크롤링",
    )
    parser.add_argument(
        "--kubernetes",
        action="store_true",
        help="Kubernetes 문서만 크롤링",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="기존 DB를 삭제하고 새로 생성",
    )

    args = parser.parse_args()

    # URL 선택 및 소스 타입 결정
    source_type = None
    
    if args.urls:
        # 직접 URL 지정
        urls = args.urls
        if urls:
            source_type = detect_source_type(urls[0])
    elif args.aws:
        # AWS만
        urls = AWS_URLS
        source_type = "aws"
    elif args.docker:
        # Docker만
        urls = DOCKER_URLS
        source_type = "docker"
    elif args.gcp:
        # GCP만
        urls = GCP_URLS
        source_type = "other"
    elif args.kubernetes:
        # Kubernetes만
        urls = KUBERNETES_URLS
        source_type = "other"
    else:
        # 기본값: 모든 문서 (AWS + Docker + GCP + Kubernetes)
        urls = DEFAULT_URLS
        source_type = None

    crawl_and_update_db(
        urls=urls,
        persist_directory=PERSIST_DIRECTORY,
        rebuild=args.rebuild,
        source_type=source_type,
    )
