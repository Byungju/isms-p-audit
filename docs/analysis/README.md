# analysis

원본 소스 문서(`docs/sources/`)의 분석 결과를 담는 디렉터리.

```
analysis/
├── source-overview.md          # 각 원본 문서의 목적·구성·활용 목적
├── document-relationship.md    # 5개 원본 문서 간 관계 분석
├── linux-overview.md           # Linux/Unix 서버 관련 내용 정리
├── linux-check-items.md        # Linux/Unix 점검 항목 표준 목록 (U-01~U-67)
└── data-model-review.md        # data/ YAML 데이터 모델 리뷰
```

각 문서의 초점:

- `source-overview.md` — 각 원본 문서가 무엇인지 파악하기 위한 개요.
- `document-relationship.md` — ISMS-P 계열과 KISA 계열이 어떻게 다른지, 문서 간 관계가 실제 구조와 어떻게 다른지 확인.
- `linux-overview.md` — Linux/Unix 서버와 관련된 ISMS-P 인증기준·KISA 점검항목·자동화 가능성 정리.
- `linux-check-items.md` — KISA U-01~U-67 전체를 ID·PASS/FAIL·ISMS-P 매핑·자동화 등급으로 정리한 표준 목록.
- `data-model-review.md` — `data/` 디렉터리의 YAML 데이터 모델의 중복·SSOT·확장성 문제를 검토.

> 분석 문서는 원본의 사실과 프로젝트의 해석을 구분하여 기록한다.
