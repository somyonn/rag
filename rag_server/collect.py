"""AWS 및 Docker 문서 사이트에서 RAG 임베딩에 유용한 URL을 수집하여 각각의 urls.py 파일에 추가하는 통합 스크립트."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import os
import argparse
from pathlib import Path


def collect_urls_from_aws_docs(base_url: str = "https://docs.aws.amazon.com/", max_urls: int = 50, depth: int = 2) -> list[str]:
    """AWS 문서 사이트에서 URL을 수집."""
    collected_urls = set()
    visited = set()
    
    # RAG에 유용한 문서 패턴
    useful_patterns = [
        "/userguide/",
        "/developerguide/",
        "/latest/userguide/",
        "/latest/developerguide/",
        "/reference/",
        "/tutorial/",
        "/guide/",
        "/concepts/",
        "/getting-started/",
        "/what-is/",
        "/introduction/",
        "/overview/",
        "/welcome.html",
        "/concepts.html",
    ]
    
    # 제외할 패턴 (RAG에 덜 유용한 페이지)
    exclude_patterns = [
        "/blog/",
        "/release-notes/",
        "/download/",
        "/pricing/",
        "/community/",
        "/support/",
        "/legal/",
        "/search",
        "/console/",
        "/cli/",
        "/sdk/",
        "/api/",
        "/toolkit/",
        "?",
        "#",
    ]
    
    # AWS 주요 서비스 시작 URL (실제 문서 페이지에서 시작)
    seed_urls = [
        "https://docs.aws.amazon.com/ec2/latest/userguide/what-is-amazon-ec2.html",
        "https://docs.aws.amazon.com/s3/latest/userguide/Welcome.html",
        "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html",
        "https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html",
        "https://docs.aws.amazon.com/rds/latest/userguide/Welcome.html",
        "https://docs.aws.amazon.com/dynamodb/latest/developerguide/Introduction.html",
        "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html",
        "https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html",
    ]
    
    def extract_links(url: str, current_depth: int):
        if current_depth > depth or url in visited:
            return
        
        visited.add(url)
        try:
            response = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; AWS-Docs-Collector/1.0)"
            })
            if response.status_code != 200:
                return
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 문서 링크 찾기
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                full_url = urljoin(url, href)
                
                # 같은 도메인인지 확인
                parsed_url = urlparse(full_url)
                if parsed_url.netloc != urlparse(base_url).netloc:
                    continue
                
                # 제외 패턴 체크
                if any(exclude in full_url.lower() for exclude in exclude_patterns):
                    continue
                
                # 유용한 패턴 체크
                is_useful = any(pattern in full_url.lower() for pattern in useful_patterns)
                
                # 또는 docs.aws.amazon.com의 특정 서비스 문서 페이지
                path_parts = parsed_url.path.strip("/").split("/")
                if len(path_parts) >= 3 and path_parts[2] in ["userguide", "developerguide", "dg"]:
                    is_useful = True
                
                if is_useful:
                    # 쿼리 파라미터나 앵커 제거
                    clean_url = full_url.split("#")[0].split("?")[0]
                    # 중복 제거 및 최대 개수 제한
                    if clean_url not in collected_urls and len(collected_urls) < max_urls:
                        collected_urls.add(clean_url)
                        if current_depth < depth:
                            extract_links(clean_url, current_depth + 1)
        except Exception as e:
            print(f"  [경고] {url} 처리 중 오류: {e}")
    
    print(f"[수집 시작] AWS 문서 URL 수집")
    
    # 시드 URL들에서 시작
    for seed_url in seed_urls:
        if len(collected_urls) >= max_urls:
            break
        extract_links(seed_url, 0)
    
    # base_url도 시도
    if len(collected_urls) < max_urls:
        extract_links(base_url, 0)
    
    print(f"[수집 완료] {len(collected_urls)}개 URL 발견")
    
    return sorted(list(collected_urls))


def collect_urls_from_docker_docs(base_url: str = "https://docs.docker.com/", max_urls: int = 50, depth: int = 2) -> list[str]:
    """Docker 문서 사이트에서 URL을 수집."""
    collected_urls = set()
    visited = set()
    
    # RAG에 유용한 문서 패턴
    useful_patterns = [
        "/get-started/",
        "/engine/",
        "/compose/",
        "/build/",
        "/desktop/",
        "/reference/",
        "/guides/",
        "/tutorial/",
        "/concepts/",
        "/storage/",
        "/network/",
        "/security/",
        "/config/",
        "/develop/",
        "/admin/",
    ]
    
    # 제외할 패턴 (RAG에 덜 유용한 페이지)
    exclude_patterns = [
        "/blog/",
        "/release-notes/",
        "/download/",
        "/pricing/",
        "/community/",
        "/support/",
        "/legal/",
        "/search",
        "?",
        "#",
    ]
    
    def extract_links(url: str, current_depth: int):
        if current_depth > depth or url in visited:
            return
        
        visited.add(url)
        try:
            response = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Docker-Docs-Collector/1.0)"
            })
            if response.status_code != 200:
                return
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 문서 링크 찾기
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                full_url = urljoin(url, href)
                
                # 같은 도메인인지 확인
                if urlparse(full_url).netloc != urlparse(base_url).netloc:
                    continue
                
                # 제외 패턴 체크
                if any(exclude in full_url.lower() for exclude in exclude_patterns):
                    continue
                
                # 유용한 패턴 체크 또는 docs.docker.com 하위 페이지
                is_useful = (
                    any(pattern in full_url.lower() for pattern in useful_patterns) or
                    "/docs/" in full_url.lower() or
                    full_url.startswith(base_url)
                )
                
                if is_useful:
                    # 쿼리 파라미터나 앵커 제거
                    clean_url = full_url.split("#")[0].split("?")[0]
                    # 중복 제거 및 최대 개수 제한
                    if clean_url not in collected_urls and len(collected_urls) < max_urls:
                        collected_urls.add(clean_url)
                        if current_depth < depth:
                            extract_links(clean_url, current_depth + 1)
        except Exception as e:
            print(f"  [경고] {url} 처리 중 오류: {e}")
    
    print(f"[수집 시작] {base_url}")
    extract_links(base_url, 0)
    print(f"[수집 완료] {len(collected_urls)}개 URL 발견")
    
    return sorted(list(collected_urls))


def update_urls_in_file(file_path: Path, list_name: str, new_urls: list[str], file_display_name: str):
    """지정된 파일의 URL 리스트에 새로운 URL 추가 (중복 제거)."""
    if not file_path.exists():
        print(f"[경고] {file_display_name} 파일을 찾을 수 없습니다: {file_path}")
        return
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 리스트 찾기
        pattern = rf'({list_name}\s*=\s*\[)(.*?)(\])'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            existing_urls = match.group(2)
            # 기존 URL 추출
            existing = re.findall(r'"([^"]+)"', existing_urls)
            
            # 새로운 URL 추가 (중복 제거)
            all_urls = list(set(existing + new_urls))
            all_urls.sort()
            
            # 리스트 재생성
            urls_str = "\n".join([f'    "{url}",' for url in all_urls])
            new_content = f"{match.group(1)}\n{urls_str}\n{match.group(3)}"
            content = content[:match.start()] + new_content + content[match.end():]
        else:
            print(f"[경고] {list_name} 리스트를 {file_display_name}에서 찾을 수 없습니다.")
            return
        
        # 파일 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"[완료] {file_display_name} 파일이 업데이트되었습니다.")
        print(f"  - {list_name}: {len(all_urls)}개 URL (기존: {len(existing)}, 추가: {len(all_urls) - len(existing)})")
        
    except Exception as e:
        print(f"[오류] {file_display_name} 업데이트 실패: {e}")


def update_aws_urls_file(new_urls: list[str]):
    """urls.py 파일에 새로운 AWS URL 추가."""
    # urls.py 업데이트
    main_urls_file = Path(__file__).parent / "urls.py"
    update_urls_in_file(main_urls_file, "AWS_URLS", new_urls, "urls.py")


def update_docker_urls_file(new_urls: list[str]):
    """urls.py 파일에 새로운 Docker URL 추가."""
    # urls.py 업데이트
    main_urls_file = Path(__file__).parent / "urls.py"
    update_urls_in_file(main_urls_file, "DOCKER_URLS", new_urls, "urls.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AWS 및 Docker 문서 사이트에서 URL 수집")
    parser.add_argument(
        "--source",
        type=str,
        choices=["aws", "docker", "all"],
        default="all",
        help="수집할 소스 선택: aws, docker, all (기본값: all)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="수집할 문서 사이트의 기본 URL (소스별 기본값 사용)",
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=50,
        help="최대 수집할 URL 개수 (기본값: 50)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="크롤링 깊이 (기본값: 2)",
    )
    
    args = parser.parse_args()
    
    # AWS URL 수집
    if args.source in ["aws", "all"]:
        aws_base_url = args.base_url or "https://docs.aws.amazon.com/"
        print("\n" + "="*60)
        print("AWS 문서 URL 수집 시작")
        print("="*60)
        aws_urls = collect_urls_from_aws_docs(aws_base_url, args.max_urls, args.depth)
        
        if aws_urls:
            print(f"\n수집된 AWS URL ({len(aws_urls)}개):")
            for url in aws_urls[:20]:  # 처음 20개만 표시
                print(f"  - {url}")
            if len(aws_urls) > 20:
                print(f"  ... 외 {len(aws_urls) - 20}개")
            
            # aws_urls.py 업데이트
            update_aws_urls_file(aws_urls)
        else:
            print("[경고] 수집된 AWS URL이 없습니다.")
    
    # Docker URL 수집
    if args.source in ["docker", "all"]:
        docker_base_url = args.base_url or "https://docs.docker.com/"
        print("\n" + "="*60)
        print("Docker 문서 URL 수집 시작")
        print("="*60)
        docker_urls = collect_urls_from_docker_docs(docker_base_url, args.max_urls, args.depth)
        
        if docker_urls:
            print(f"\n수집된 Docker URL ({len(docker_urls)}개):")
            for url in docker_urls[:20]:  # 처음 20개만 표시
                print(f"  - {url}")
            if len(docker_urls) > 20:
                print(f"  ... 외 {len(docker_urls) - 20}개")
            
            # docker_urls.py 업데이트
            update_docker_urls_file(docker_urls)
        else:
            print("[경고] 수집된 Docker URL이 없습니다.")
    
    print("\n" + "="*60)
    print("URL 수집 완료")
    print("="*60)

