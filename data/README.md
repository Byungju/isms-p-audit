# data

ISMS-P / KISA / 기술 점검 데이터 모델 디렉터리.

```
data/
├── isms-p/            # ISMS-P 인증기준·세부점검항목 데이터
├── kisa/              # KISA 기술적 취약점 점검항목 데이터 (원본 SSOT)
├── checks/            # Technical Check 정의 (Check Specification)
└── mappings/          # 항목 간 매핑 데이터
```

계층 관계:

```
ISMS-P 인증기준 / KISA 원본 (data/isms-p, data/kisa)  ← 사실(SSOT)
        │
Technical Check (data/checks)                          ← 해석(판정 조건)
        │
Mapping (data/mappings)                                ← 항목 간 연결
```

- `data/kisa/`는 원본에서 추출한 사실이며 수정하지 않는다.
- `data/checks/`는 `docs/design/check-specification.md` 설계를 따른 Technical Check 정의다.
- 각 디렉터리의 상세 내용은 하위 README를 참고한다.
