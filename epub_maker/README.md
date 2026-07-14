# EPUB 메이커

DOCX 원고를 넣으면 디자인을 입힌 표준 EPUB 전자책을 만들어 주는 브라우저 앱.
부크크 같은 자가출판 플랫폼에 등록 가능한 EPUB3 규격을 목표로 한다.

## 실행

launch.bat 더블클릭 (또는 `python -m http.server 8400 --directory epub_maker` 후 http://localhost:8400 접속).
인터넷 연결 불필요.

## 사용법

1. **문서 올리기** — .docx 파일을 끌어다 놓는다. 워드에서 챕터 제목에
   "제목 1" 스타일을 적용해 두면 챕터가 자동으로 나뉜다.
2. **책 정보** — 제목·저자(필수), ISBN·출판사·발행일·소개(선택) 입력.
3. **표지** — 이미지 업로드(권장: 가로 1000px 이상, 세로가 긴 비율) 또는
   제목·저자 기반 자동 생성.
4. **디자인** — 테마 4종 중 선택 후 글꼴·크기·줄 간격·여백 등 조정.
   미리보기에 즉시 반영된다.
5. **EPUB 만들기** — 표준 검사를 통과하면 .epub이 다운로드된다.

## 글꼴 내장

fonts/README.md 참고. KoPub TTF를 fonts/에 넣으면 EPUB에 내장된다.
없으면 "기기 기본 글꼴"로 동작한다.

## 개발

- 테스트: `node --test`
- 샘플 DOCX 생성: `python tests/make_sample_docx.py`
- 최종 확인(선택): [epubcheck](https://github.com/w3c/epubcheck) 설치 후
  `java -jar epubcheck.jar 생성파일.epub`
