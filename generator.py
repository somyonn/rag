"""RAG Generator 구현.

검색된 문서를 기반으로 LLM을 사용하여 답변을 생성합니다.
"""

import os
from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
# LLM 선택 (환경 변수로 설정 가능)
# HuggingFace Inference API는 일부 모델만 지원하므로 OpenAI를 기본값으로 사용
LLM_TYPE = os.getenv("LLM_TYPE", "openai")  # "huggingface" or "openai"

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def get_llm(llm_type: str = None):
    """LLM 인스턴스를 생성하고 반환.
    
    Args:
        llm_type: LLM 타입 ("huggingface" or "openai")
        
    Returns:
        LLM 인스턴스
    """
    if llm_type is None:
        llm_type = LLM_TYPE
    
    if llm_type == "huggingface":
        try:
            # 먼저 HuggingFace Inference API 시도
            huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
            if huggingface_api_token:
                try:
                    from langchain_huggingface import HuggingFaceEndpoint
                    
                    # HuggingFace Inference API는 일부 모델만 지원합니다
                    # Inference API에서 확실히 작동하는 모델을 사용하거나
                    # OpenAI를 사용하는 것을 권장합니다
                    model_name = os.getenv("HUGGINGFACE_MODEL")
                    
                    if not model_name:
                        print("[경고] HUGGINGFACE_MODEL이 설정되지 않았습니다.")
                        print("[권장] HuggingFace Inference API는 일부 모델만 지원합니다.")
                        print("[권장] OpenAI를 사용하는 것을 권장합니다: --llm-type openai")
                        print("\n[예시] HuggingFace 모델 사용 시:")
                        print("  export HUGGINGFACE_MODEL='mistralai/Mistral-7B-Instruct-v0.2'")
                        return None
                    
                    # HuggingFaceEndpoint 사용
                    return HuggingFaceEndpoint(
                        repo_id=model_name,
                        huggingfacehub_api_token=huggingface_api_token,
                        temperature=0.7,
                        max_new_tokens=512,
                    )
                except ImportError:
                    print("[오류] langchain_huggingface가 설치되지 않았습니다.")
                    print("[해결] pip install langchain-huggingface 명령으로 설치하세요.")
                    return None
                except Exception as e:
                    print(f"[오류] HuggingFace API 초기화 실패: {e}")
                    print("[해결] HUGGINGFACE_API_TOKEN 환경 변수가 올바르게 설정되어 있는지 확인하세요.")
                    print("[해결] 또는 OpenAI를 사용하려면 --llm-type openai 옵션을 사용하세요.")
                    return None
            else:
                print("[오류] HUGGINGFACE_API_TOKEN 환경 변수가 설정되지 않았습니다.")
                print("[해결] export HUGGINGFACE_API_TOKEN='your_token' 명령으로 설정하세요.")
                print("[해결] 또는 OpenAI를 사용하려면 --llm-type openai 옵션을 사용하세요.")
                return None
        except Exception as e:
            print(f"[경고] HuggingFace LLM 초기화 실패: {e}")
            return None
    
    elif llm_type == "openai":
        try:
            from langchain_openai import ChatOpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            
            model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            return ChatOpenAI(
                model=model_name,
                temperature=0.7,
                api_key=api_key,
            )
        except ImportError:
            print("[경고] langchain_openai가 설치되지 않았습니다.")
            return None
        except ValueError as e:
            print(f"[오류] {e}")
            return None
    
    else:
        raise ValueError(f"지원하지 않는 LLM 타입: {llm_type}")


def create_prompt_template() -> ChatPromptTemplate:
    """RAG용 프롬프트 템플릿 생성."""
    
    template = """다음 문서들을 참고하여 질문에 답변해주세요. 
문서에 없는 내용은 추측하지 말고, 문서에 있는 정보만을 기반으로 답변하세요.

문서들:
{context}

질문: {question}

답변:"""
    
    return PromptTemplate.from_template(template)


def format_documents(docs: List[Document]) -> str:
    """문서 리스트를 문자열로 포맷팅.
    
    Args:
        docs: Document 리스트
        
    Returns:
        포맷팅된 문서 문자열
    """
    formatted = []
    for i, doc in enumerate(docs, 1):
        url = doc.metadata.get("url") or doc.metadata.get("source", "")
        title = doc.metadata.get("title", "")
        
        doc_str = f"[문서 {i}]"
        if title:
            doc_str += f" 제목: {title}"
        if url:
            doc_str += f"\nURL: {url}"
        doc_str += f"\n내용: {doc.page_content}\n"
        
        formatted.append(doc_str)
    
    return "\n".join(formatted)


class RAGGenerator:
    """RAG Generator 클래스.
    
    검색된 문서를 기반으로 LLM을 사용하여 답변을 생성합니다.
    """
    
    def __init__(
        self,
        llm=None,
        llm_type: str = None,
        prompt_template: Optional[PromptTemplate] = None,
        verbose: bool = False,
    ):
        """Generator 초기화.
        
        Args:
            llm: LLM 인스턴스 (None이면 자동으로 생성)
            llm_type: LLM 타입 ("huggingface" or "openai")
            prompt_template: 커스텀 프롬프트 템플릿
            verbose: 상세 출력 여부
        """
        self.verbose = verbose
        
        # LLM 초기화
        if llm is None:
            self.llm = get_llm(llm_type)
            if self.llm is None:
                raise RuntimeError("LLM을 초기화할 수 없습니다. 설정을 확인하세요.")
        else:
            self.llm = llm
        
        # 프롬프트 템플릿 초기화
        if prompt_template is None:
            self.prompt_template = create_prompt_template()
        else:
            self.prompt_template = prompt_template
        
        # 체인 구성은 generate 메서드에서 동적으로 구성
    
    def generate(
        self,
        question: str,
        documents: List[Document],
    ) -> str:
        """질문에 대한 답변을 생성.
        
        Args:
            question: 질문
            documents: 검색된 문서 리스트
            
        Returns:
            생성된 답변
        """
        if self.verbose:
            print(f"\n[Generator] 질문: {question}")
            print(f"[Generator] 참고 문서 수: {len(documents)}")
        
        if not documents:
            return "검색된 관련 문서가 없어 답변을 생성할 수 없습니다."
        
        try:
            # 문서 포맷팅
            context = format_documents(documents)
            
            # 프롬프트 생성
            prompt = self.prompt_template.format(context=context, question=question)
            
            # LLM 호출
            # HuggingFaceEndpoint는 일반 LLM이므로 문자열을 직접 전달
            from langchain_core.language_models.chat_models import BaseChatModel
            if isinstance(self.llm, BaseChatModel):
                # ChatModel인 경우
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=prompt)]
                response = self.llm.invoke(messages)
                if hasattr(response, 'content'):
                    answer = response.content
                else:
                    answer = str(response)
            else:
                # 일반 LLM인 경우 (HuggingFaceEndpoint 등)
                answer = self.llm.invoke(prompt)
                if hasattr(answer, 'content'):
                    answer = answer.content
                else:
                    answer = str(answer)
            
            if self.verbose:
                print(f"[Generator] 답변 생성 완료")
            
            return answer.strip()
        except Exception as e:
            error_msg = f"답변 생성 중 오류 발생: {e}"
            if self.verbose:
                print(f"[Generator] {error_msg}")
                import traceback
                traceback.print_exc()
            return error_msg
    
    async def agenerate(
        self,
        question: str,
        documents: List[Document],
    ) -> str:
        """비동기 버전의 답변 생성."""
        if self.verbose:
            print(f"\n[Generator] 질문: {question}")
            print(f"[Generator] 참고 문서 수: {len(documents)}")
        
        if not documents:
            return "검색된 관련 문서가 없어 답변을 생성할 수 없습니다."
        
        try:
            # 문서 포맷팅
            context = format_documents(documents)
            
            # 프롬프트 생성
            prompt = self.prompt_template.format(context=context, question=question)
            
            # LLM 호출 (비동기)
            from langchain_core.language_models.chat_models import BaseChatModel
            if isinstance(self.llm, BaseChatModel):
                # ChatModel인 경우
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=prompt)]
                if hasattr(self.llm, 'ainvoke'):
                    response = await self.llm.ainvoke(messages)
                else:
                    response = self.llm.invoke(messages)
                if hasattr(response, 'content'):
                    answer = response.content
                else:
                    answer = str(response)
            else:
                # 일반 LLM인 경우 (HuggingFaceEndpoint 등)
                if hasattr(self.llm, 'ainvoke'):
                    answer = await self.llm.ainvoke(prompt)
                else:
                    answer = self.llm.invoke(prompt)
                if hasattr(answer, 'content'):
                    answer = answer.content
                else:
                    answer = str(answer)
            
            if self.verbose:
                print(f"[Generator] 답변 생성 완료")
            
            return answer.strip()
        except Exception as e:
            error_msg = f"답변 생성 중 오류 발생: {e}"
            if self.verbose:
                print(f"[Generator] {error_msg}")
                import traceback
                traceback.print_exc()
            return error_msg


def get_generator(
    llm_type: str = None,
    verbose: bool = False,
) -> RAGGenerator:
    """Generator 인스턴스를 생성하고 반환.
    
    Args:
        llm_type: LLM 타입 ("huggingface" or "openai")
        verbose: 상세 출력 여부
        
    Returns:
        RAGGenerator 인스턴스
    """
    return RAGGenerator(llm_type=llm_type, verbose=verbose)

