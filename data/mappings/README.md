# mappings

항목 간 매핑 데이터 디렉터리.

```
mappings/
└── isms-p-to-linux.yaml   # ISMS-P 인증기준 → KISA Linux 점검항목 매핑
```

- `isms-p-to-linux.yaml` — ISMS-P 인증기준과 KISA Linux/Unix 점검항목의 연관 관계를 담는다.
  - `mappings[]`의 각 항목은 `isms_p_criterion`과 `kisa_items[]`로 구성된다.

> 주의: 이 매핑은 프로젝트의 **해석**이며, 원본 문서 간 명시적 1:1 매핑은 아니다.
> KISA 점검 결과(PASS/FAIL)가 곧 ISMS-P 인증기준 충족을 의미하지 않는다.

> 향후 Check↔KISA 관계를 관리하는 매핑(`kisa-to-check`)도 이 디렉터리에 추가될 예정이다.
> (`docs/design/check-specification.md` 참고)
