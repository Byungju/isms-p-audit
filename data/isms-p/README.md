# isms-p

ISMS-P 인증기준 데이터 디렉터리.

```
isms-p/
├── criteria.yaml       # ISMS-P 인증기준 (101개)
└── check-items.yaml    # ISMS-P 세부점검항목 (101개 기준 / 328개 확인사항)
```

- `criteria.yaml` — 인증기준을 `areas → fields → criteria(id/name/text)` 구조로 담는다.
  - 출처: ISMS-P 인증기준 안내서(2023.11.23) / 세부점검항목(2023.10.31).
- `check-items.yaml` — 세부점검항목을 `areas → fields → items(id/name/detail/checks[])` 구조로 담는다.
  - `checks[]`가 각 기준의 "주요 확인사항"에 해당한다.

> 현재는 본인증(2023.10.31) 기준이며, 간편인증(7의2/7의3) 데이터는 포함하지 않는다.
